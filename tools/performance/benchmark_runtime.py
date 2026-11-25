#!/usr/bin/env python3
"""Benchmark representative InfinityDB repository read paths against one database."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import sys
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
    setup: Callable[[Database], object] | None = None


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


def _cold_sample(case: BenchmarkCase, path: Path) -> float:
    if case.setup is None:
        return _time(lambda: case.action(Database(path)))
    database = Database(path)
    case.setup(database)
    return _time(lambda: case.action(database))


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
        BenchmarkCase(
            "units-counts", lambda db: db.list_units(limit=50, include_usage_counts=True)
        ),
        BenchmarkCase(
            "units-counts-numeric",
            lambda db: db.list_units(
                points_min=10, points_max=35, limit=50, include_usage_counts=True,
            ),
        ),
        BenchmarkCase("traits", lambda db: db.list_traits()),
        BenchmarkCase(
            "units-scoped-initial-full",
            lambda db: db.list_units(
                matching_scope="profile", limit=50, include_usage_counts=True,
            ),
        ),
        BenchmarkCase(
            "units-scoped-initial-prospective",
            lambda db: db.list_units(
                matching_scope="profile", limit=50, include_usage_counts=True,
                include_raw_usage_counts=False,
            ),
        ),
    ]
    if armies:
        army_id = armies[0]["id"]
        cases.append(
            BenchmarkCase(
                "units-by-army",
                lambda db, value=army_id: db.list_units(army_id=value, limit=50),
            )
        )
        cases.append(
            BenchmarkCase(
                "units-counts-by-army",
                lambda db, value=army_id: db.list_units(
                    army_id=value, limit=50, include_usage_counts=True,
                ),
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
        if catalog == "skills" and len(items) >= 2:
            ids = tuple(
                item["id"] for item in sorted(
                    items, key=lambda item: item.get("use_count", 0), reverse=True,
                )[:2]
            )
            cases.append(
                BenchmarkCase(
                    "units-counts-multiselect",
                    lambda db, value=ids: db.list_units(
                        skill_id=value, limit=50, include_usage_counts=True,
                    ),
                )
            )
            # Exercise the explicitly scoped AND/count paths, not just the legacy
            # multi-selection endpoint. Prefer a realistic cross-skill query.
            by_slug = {str(item.get("slug")): item["id"] for item in items}
            scoped_ids = (
                (by_slug["berserk"], by_slug["engineer"])
                if {"berserk", "engineer"} <= by_slug.keys()
                else ids
            )
            for scope in ("profile", "loadout", "unit"):
                cases.append(
                    BenchmarkCase(
                        f"units-scoped-{scope}-counts",
                        lambda db, values=scoped_ids, mode=scope: db.list_units(
                            skill_id=values, and_filters=("skill",),
                            matching_scope=mode, limit=50, include_usage_counts=True,
                        ),
                    )
                )
            cases.append(
                BenchmarkCase(
                    "units-scoped-loadout-numeric-counts",
                    lambda db, values=scoped_ids: db.list_units(
                        skill_id=values, and_filters=("skill",),
                        matching_scope="loadout", points_min=10, points_max=35,
                        limit=50, include_usage_counts=True,
                    ),
                )
            )
            for scope in ("profile", "loadout", "unit"):
                cases.append(
                    BenchmarkCase(
                        f"units-scoped-{scope}-after-index",
                        lambda db, values=scoped_ids, mode=scope: db.list_units(
                            skill_id=values, and_filters=("skill",),
                            matching_scope=mode, limit=50, include_usage_counts=True,
                        ),
                        setup=lambda db, value=scoped_ids[0], mode=scope: db.list_units(
                            skill_id=value, matching_scope=mode,
                            limit=50, include_usage_counts=True,
                        ),
                    )
                )
            for scope in ("profile", "loadout", "unit"):
                cases.append(
                    BenchmarkCase(
                        f"units-prospective-{scope}-after-index",
                        lambda db, values=scoped_ids, mode=scope: db.list_units(
                            skill_id=values, and_filters=("skill",),
                            matching_scope=mode, limit=50, include_usage_counts=True,
                            include_raw_usage_counts=False,
                        ),
                        setup=lambda db, value=scoped_ids[0], mode=scope: db.list_units(
                            skill_id=value, matching_scope=mode, limit=50,
                            include_usage_counts=True, include_raw_usage_counts=False,
                        ),
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
    case_names: Sequence[str] = (),
) -> dict[str, Any]:
    database = Database(path)
    database.validate()
    cases = discover_cases(database)
    if case_names:
        unknown = set(case_names) - {case.name for case in cases}
        if unknown:
            raise ValueError(f"Unknown benchmark cases: {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case.name in case_names]
    results = []
    for case in cases:
        cold_samples = [_cold_sample(case, path) for _ in range(cold_iterations)]
        warm_database = Database(path)
        if case.setup is not None:
            case.setup(warm_database)
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
    parser.add_argument("database", type=Path, help="Path to a built army.db snapshot.")
    parser.add_argument("--cold-iterations", type=int, default=20)
    parser.add_argument("--warm-iterations", type=int, default=200)
    parser.add_argument("--case", action="append", default=[], help="Run only this named case.")
    parser.add_argument("--profile", action="store_true", help="Profile each selected case.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cold_iterations < 1 or args.warm_iterations < 1:
        raise SystemExit("iteration counts must be positive")
    try:
        if args.profile:
            import cProfile
            import pstats

            if not args.case or args.json:
                raise ValueError("--profile requires --case and cannot be combined with --json")
            cases = {case.name: case for case in discover_cases(Database(args.database))}
            for name in args.case:
                if name not in cases:
                    raise ValueError(f"Unknown benchmark case: {name}")
                print(f"Profile: {name}", flush=True)
                profiler = cProfile.Profile()
                database = Database(args.database)
                setup = cases[name].setup
                if setup is not None:
                    setup(database)
                profiler.runcall(cases[name].action, database)
                pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(25)
            return 0
        report = benchmark_database(
            args.database,
            cold_iterations=args.cold_iterations,
            warm_iterations=args.warm_iterations,
            case_names=args.case,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
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
