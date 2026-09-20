#!/usr/bin/env python3
"""Benchmark representative InfinityDB repository read paths against one database."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infinity_db.database import Database

FORMAT = "InfinityDB runtime benchmark"
FORMAT_VERSION = 1


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    action: Callable[[Database], object]


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("cannot calculate a percentile of an empty sample")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def _summary(samples: Sequence[float]) -> dict[str, float]:
    milliseconds = [sample * 1000 for sample in samples]
    return {
        "medianMs": statistics.median(milliseconds),
        "p95Ms": _percentile(milliseconds, 0.95),
        "meanMs": statistics.fmean(milliseconds),
        "minMs": min(milliseconds),
        "maxMs": max(milliseconds),
    }


def _time(action: Callable[[], object]) -> float:
    started = time.perf_counter()
    action()
    return time.perf_counter() - started


def _catalog_detail_action(catalog: str, item_id: int) -> Callable[[Database], object]:
    if catalog == "skills":
        return lambda database: database.get_skill(item_id)
    return lambda database: database.get_catalog_item(catalog, item_id)


def discover_cases(database: Database) -> list[BenchmarkCase]:
    """Build representative cases from identities present in the supplied snapshot."""
    armies = [army for army in database.list_armies() if army.get("playable")]
    units = database.list_units(limit=1).get("items", [])
    unit = units[0] if units else None

    cases = [
        BenchmarkCase("armies", lambda db: db.list_armies()),
        BenchmarkCase("units", lambda db: db.list_units(limit=50)),
        BenchmarkCase("traits", lambda db: db.list_traits()),
    ]
    if armies:
        army_id = armies[0]["id"]
        cases.append(
            BenchmarkCase(
                "units-by-army",
                lambda db, value=army_id: db.list_units(army_id=value, limit=50),
            )
        )
    if unit is not None:
        unit_id = unit["id"]
        unit_name = str(unit.get("name") or "")
        cases.append(BenchmarkCase("unit-detail", lambda db, value=unit_id: db.get_unit(value)))
        if unit_name:
            search = unit_name[: max(1, min(6, len(unit_name)))]
            cases.append(
                BenchmarkCase(
                    "unit-search",
                    lambda db, value=search: db.list_units(search=value, limit=50),
                )
            )

    for catalog in ("skills", "equipment", "weapons"):
        items = database.list_catalog_items(catalog)
        cases.append(
            BenchmarkCase(
                f"{catalog}-catalog",
                lambda db, value=catalog: db.list_catalog_items(value),
            )
        )
        if items:
            item_id = items[0]["id"]
            cases.append(
                BenchmarkCase(
                    f"{catalog}-detail",
                    _catalog_detail_action(catalog, item_id),
                )
            )

    traits = database.list_traits()
    if traits:
        trait_id = traits[0]["id"]
        cases.append(BenchmarkCase("trait-detail", lambda db, value=trait_id: db.get_trait(value)))
    return cases


def benchmark_database(
    path: Path,
    *,
    cold_iterations: int,
    warm_iterations: int,
) -> dict[str, Any]:
    database = Database(path)
    database.validate()
    cases = discover_cases(database)
    results = []
    for case in cases:
        cold_samples = [
            _time(lambda action=case.action: action(Database(path)))
            for _ in range(cold_iterations)
        ]
        warm_database = Database(path)
        case.action(warm_database)
        warm_samples = [
            _time(lambda action=case.action, db=warm_database: action(db))
            for _ in range(warm_iterations)
        ]
        results.append(
            {
                "name": case.name,
                "cold": _summary(cold_samples),
                "warm": _summary(warm_samples),
            }
        )
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "database": str(path),
        "databaseBytes": path.stat().st_size,
        "coldIterations": cold_iterations,
        "warmIterations": warm_iterations,
        "cases": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Path to a built infinity.db snapshot.")
    parser.add_argument("--cold-iterations", type=int, default=20)
    parser.add_argument("--warm-iterations", type=int, default=200)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cold_iterations < 1 or args.warm_iterations < 1:
        raise SystemExit("iteration counts must be positive")
    report = benchmark_database(
        args.database,
        cold_iterations=args.cold_iterations,
        warm_iterations=args.warm_iterations,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    print(f"Runtime benchmark: {report['database']}")
    print(f"Database size: {report['databaseBytes']:,} bytes")
    print(
        f"Samples: {report['coldIterations']} cold / "
        f"{report['warmIterations']} warm per case"
    )
    for case in report["cases"]:
        cold = case["cold"]
        warm = case["warm"]
        print(
            f"{case['name']:<20} "
            f"cold p50 {cold['medianMs']:8.3f} ms  p95 {cold['p95Ms']:8.3f} ms | "
            f"warm p50 {warm['medianMs']:8.3f} ms  p95 {warm['p95Ms']:8.3f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
