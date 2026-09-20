#!/usr/bin/env python3
"""Compare two InfinityDB runtime benchmark JSON reports."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BENCHMARK_FORMAT = "InfinityDB runtime benchmark"
BENCHMARK_FORMAT_VERSION = 1


FORMAT = "InfinityDB runtime benchmark comparison"
FORMAT_VERSION = 1
STATISTICS = ("medianMs", "p95Ms")
TEMPERATURES = ("cold", "warm")


class BenchmarkComparisonError(ValueError):
    """Raised when benchmark reports cannot be compared safely."""


def _load_report(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkComparisonError(f"Could not read benchmark report {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise BenchmarkComparisonError(f"Benchmark report {path} must contain a JSON object")
    if document.get("format") != BENCHMARK_FORMAT:
        raise BenchmarkComparisonError(f"Benchmark report {path} has an unsupported format")
    if document.get("formatVersion") != BENCHMARK_FORMAT_VERSION:
        raise BenchmarkComparisonError(
            f"Benchmark report {path} has unsupported format version "
            f"{document.get('formatVersion')!r}"
        )
    return document


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BenchmarkComparisonError(f"{context} must be a finite number")
    return float(value)


def _positive_int(value: object, context: str) -> int:
    if type(value) is not int or value < 1:
        raise BenchmarkComparisonError(f"{context} must be a positive integer")
    return value


def _case_map(report: Mapping[str, Any], context: str) -> dict[str, Mapping[str, Any]]:
    raw_cases = report.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise BenchmarkComparisonError(f"{context}.cases must be a non-empty array")
    cases: dict[str, Mapping[str, Any]] = {}
    for index, raw_case in enumerate(raw_cases):
        case_context = f"{context}.cases[{index}]"
        if not isinstance(raw_case, dict):
            raise BenchmarkComparisonError(f"{case_context} must be an object")
        name = raw_case.get("name")
        if not isinstance(name, str) or not name:
            raise BenchmarkComparisonError(f"{case_context}.name must be a non-empty string")
        if name in cases:
            raise BenchmarkComparisonError(f"{context}.cases contains duplicate case {name!r}")
        for temperature in TEMPERATURES:
            summary = raw_case.get(temperature)
            if not isinstance(summary, dict):
                raise BenchmarkComparisonError(
                    f"{case_context}.{temperature} must be an object"
                )
            for statistic in STATISTICS:
                _number(summary.get(statistic), f"{case_context}.{temperature}.{statistic}")
        cases[name] = raw_case
    return cases


def _delta(before: float, after: float) -> dict[str, float | None]:
    difference = after - before
    percent = None if before == 0 else difference / before * 100
    return {
        "beforeMs": before,
        "afterMs": after,
        "deltaMs": difference,
        "deltaPercent": percent,
    }


def compare_reports(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    before_source: str,
    after_source: str,
) -> dict[str, Any]:
    """Return a deterministic comparison of two compatible benchmark reports."""
    before_cold = _positive_int(before.get("coldIterations"), "before.coldIterations")
    after_cold = _positive_int(after.get("coldIterations"), "after.coldIterations")
    before_warm = _positive_int(before.get("warmIterations"), "before.warmIterations")
    after_warm = _positive_int(after.get("warmIterations"), "after.warmIterations")
    if (before_cold, before_warm) != (after_cold, after_warm):
        raise BenchmarkComparisonError(
            "Benchmark reports use different iteration counts; rerun them with matching settings"
        )

    before_cases = _case_map(before, "before")
    after_cases = _case_map(after, "after")
    if set(before_cases) != set(after_cases):
        missing_after = sorted(set(before_cases) - set(after_cases))
        missing_before = sorted(set(after_cases) - set(before_cases))
        details = []
        if missing_after:
            details.append("missing from after: " + ", ".join(missing_after))
        if missing_before:
            details.append("missing from before: " + ", ".join(missing_before))
        raise BenchmarkComparisonError(
            "Benchmark reports contain different cases (" + "; ".join(details) + ")"
        )

    before_bytes = _positive_int(before.get("databaseBytes"), "before.databaseBytes")
    after_bytes = _positive_int(after.get("databaseBytes"), "after.databaseBytes")
    size_delta = after_bytes - before_bytes
    size_percent = size_delta / before_bytes * 100

    cases = []
    for name in before_cases:
        before_case = before_cases[name]
        after_case = after_cases[name]
        comparison: dict[str, Any] = {"name": name}
        for temperature in TEMPERATURES:
            before_summary = before_case[temperature]
            after_summary = after_case[temperature]
            comparison[temperature] = {
                statistic: _delta(
                    _number(
                        before_summary[statistic],
                        f"before.{name}.{temperature}.{statistic}",
                    ),
                    _number(
                        after_summary[statistic],
                        f"after.{name}.{temperature}.{statistic}",
                    ),
                )
                for statistic in STATISTICS
            }
        cases.append(comparison)

    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "before": {
            "source": before_source,
            "database": before.get("database"),
            "databaseBytes": before_bytes,
        },
        "after": {
            "source": after_source,
            "database": after.get("database"),
            "databaseBytes": after_bytes,
        },
        "coldIterations": before_cold,
        "warmIterations": before_warm,
        "databaseSize": {
            "deltaBytes": size_delta,
            "deltaPercent": size_percent,
        },
        "cases": cases,
    }


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+7.2f}%"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path, help="Pre-change benchmark JSON report.")
    parser.add_argument("after", type=Path, help="Post-change benchmark JSON report.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        before = _load_report(args.before)
        after = _load_report(args.after)
        report = compare_reports(
            before,
            after,
            before_source=str(args.before),
            after_source=str(args.after),
        )
    except BenchmarkComparisonError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    size = report["databaseSize"]
    print(f"Runtime benchmark comparison: {args.before} -> {args.after}")
    print(
        "Database size: "
        f"{report['before']['databaseBytes']:,} -> {report['after']['databaseBytes']:,} bytes "
        f"({size['deltaBytes']:+,}; {size['deltaPercent']:+.2f}%)"
    )
    print(
        f"Samples: {report['coldIterations']} cold / "
        f"{report['warmIterations']} warm per case"
    )
    print("Negative timing deltas are faster; positive timing deltas are slower.")
    for case in report["cases"]:
        cold = case["cold"]
        warm = case["warm"]
        print(
            f"{case['name']:<20} "
            f"cold p50 {_percent(cold['medianMs']['deltaPercent'])}  "
            f"p95 {_percent(cold['p95Ms']['deltaPercent'])} | "
            f"warm p50 {_percent(warm['medianMs']['deltaPercent'])}  "
            f"p95 {_percent(warm['p95Ms']['deltaPercent'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
