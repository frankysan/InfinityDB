"""Compare repeated full source verification with build-local receipt reuse."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

from infinity_db.database.normalized_source import (
    attest_normalized_source,
    verified_normalized_generation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("army", type=Path)
    parser.add_argument("normalized", type=Path)
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
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
