"""Measure normalized-source verification and initial export validation costs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from statistics import median
from time import perf_counter

from infinity_db.build_provenance import file_sha256
from infinity_db.database.normalized_source import (
    attest_normalized_source,
    verified_normalized_generation,
)


def initial_export_timings(path: Path, iterations: int) -> dict:
    """Measure individual CPU/I/O passes without writing any artifacts."""
    from infinity_army_data.normalize import validate_normalized
    from infinity_db.database.importer import json_text, validate_input
    from infinity_db.source_anomalies import (
        load_source_anomaly_baseline,
        source_anomaly_baseline_applies,
        validate_normalized_source_anomalies,
    )

    def load() -> dict:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    document = load()

    def audit() -> None:
        baseline = load_source_anomaly_baseline()
        if source_anomaly_baseline_applies(document, baseline):
            validate_normalized_source_anomalies(document, baseline)

    operations: dict[str, Callable[[], object]] = {
        "parse": load,
        "anomalyAudit": audit,
        "strictSerialization": lambda: json_text(document),
        "normalizedRelationships": lambda: validate_normalized(document),
        "fullExportValidation": lambda: validate_input(document),
    }
    samples: dict[str, list[float]] = {name: [] for name in operations}
    for _ in range(iterations):
        for name, operation in operations.items():
            start = perf_counter()
            operation()
            samples[name].append(perf_counter() - start)
    return {
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "normalizedBytes": path.stat().st_size,
        "normalizedSha256": file_sha256(path),
        "anomalyBaselineApplies": source_anomaly_baseline_applies(
            document, load_source_anomaly_baseline(),
        ),
        "iterations": iterations,
        "seconds": samples,
        "medianSeconds": {name: median(values) for name, values in samples.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "army", type=Path, help="Matched Army export (unused with --initial-export)",
    )
    parser.add_argument("normalized", type=Path)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument(
        "--initial-export", action="store_true",
        help="Measure JSON parsing and validation passes instead of overlay verification",
    )
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    if args.initial_export:
        print(json.dumps(initial_export_timings(args.normalized, args.iterations), indent=2))
        return 0
    full, reused = [], []
    receipt = attest_normalized_source(args.army, args.normalized)
    expected = receipt.generation
    for _ in range(args.iterations):
        start = perf_counter()
        baseline = [verified_normalized_generation(args.army, args.normalized) for _ in range(5)]
        full.append(perf_counter() - start)
        start = perf_counter()
        receipt = attest_normalized_source(args.army, args.normalized)
        optimized = [verified_normalized_generation(args.army, receipt) for _ in range(5)]
        reused.append(perf_counter() - start)
        if baseline != [expected] * 5 or optimized != baseline:
            raise ValueError("Source verification generations differ")
    print(json.dumps({
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "normalizedBytes": args.normalized.stat().st_size,
        "normalizedSha256": receipt.source_sha256,
        "exportGeneration": expected,
        "iterations": args.iterations,
        "fullSeconds": full,
        "receiptSeconds": reused,
        "fullMedianSeconds": median(full),
        "receiptMedianSeconds": median(reused),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
