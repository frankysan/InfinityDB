"""Summarize host CPU/RAM samples over a bounded, exact test window.

Read an ignored JSONL capture created by tools.sample_test_host_resources.
CPU percentages apply to the *preceding* sample interval. Report overlap-
weighted means and reject incomplete test-window coverage.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tools.sample_test_host_resources import ROOT, resolve_output


def _timestamp(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid offset-aware timestamp: {value}") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("A timezone offset is required")
    return timestamp.astimezone(UTC)


def _percentage(value: object, *, nullable: bool = False) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected numeric host percentage")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise ValueError("Host percentage outside 0..100")
    return number


def read_capture(path: Path) -> tuple[datetime, list[dict[str, float | None]]]:
    """Fail closed for incomplete/malformed samples instead of inferring idle load."""
    try:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read complete resource capture: {exc}") from exc
    if len(records) < 4 or not all(isinstance(row, dict) for row in records):
        raise ValueError("Resource capture needs metadata, samples and a summary")
    header, *body = records
    summary = body.pop()
    if header.get("kind") != "metadata" or header.get("schema") != 1:
        raise ValueError("Invalid resource capture header")
    if summary.get("kind") != "summary" or type(summary.get("samples")) is not int:
        raise ValueError("Missing finished resource capture summary")
    if summary["samples"] != len(body):
        raise ValueError("Resource capture sample count does not match its summary")
    if len(body) < 2:
        raise ValueError("Resource capture needs at least two samples")
    try:
        started = _timestamp(header["startedUtc"])
        samples: list[dict[str, float | None]] = []
        previous_elapsed = -1.0
        for index, row in enumerate(body):
            if row.get("kind") != "sample":
                raise ValueError("Unexpected resource record")
            value = row["elapsedSeconds"]
            if type(value) not in (int, float) or not math.isfinite(float(value)):
                raise ValueError("Invalid sample timestamp")
            elapsed = float(value)
            if elapsed < 0 or elapsed <= previous_elapsed:
                raise ValueError("Resource timestamps must be strictly increasing")
            cpu = _percentage(row.get("cpuBusyPercent"), nullable=index == 0)
            memory = _percentage(row.get("memoryUsedPercent"))
            samples.append({"elapsed": elapsed, "cpu": cpu, "memory": memory})
            previous_elapsed = elapsed
        if samples[0]["cpu"] is not None:
            raise ValueError("First CPU sample must not have a prior interval")
    except (KeyError, TypeError) as exc:
        raise ValueError("Malformed resource record") from exc
    return started, samples


def summarize_test_window(
    capture: Path, *, test_start: datetime, duration_seconds: float,
) -> dict[str, Any]:
    if (
        not math.isfinite(duration_seconds)
        or not 1 <= duration_seconds <= 1800
        or test_start.tzinfo is None or test_start.utcoffset() is None
    ):
        raise ValueError("An offset-aware start and 1..1800s duration are required")
    started, samples = read_capture(capture)
    begin = (test_start.astimezone(UTC) - started).total_seconds()
    finish = begin + duration_seconds
    cpu_weighted = 0.0
    memory_weighted = 0.0
    covered = 0.0
    intervals = 0
    cpu_peak = 0.0
    memory_peak = 0.0
    for previous, current in zip(samples, samples[1:], strict=False):
        previous_elapsed, current_elapsed = previous["elapsed"], current["elapsed"]
        if previous_elapsed is None or current_elapsed is None:
            raise ValueError("Missing resource sample timestamp")
        lo = max(begin, previous_elapsed)
        hi = min(finish, current_elapsed)
        if hi <= lo:
            continue
        cpu, memory = current["cpu"], current["memory"]
        if cpu is None or memory is None:
            raise ValueError("Missing CPU or memory metric inside test interval")
        overlap = hi - lo
        cpu_weighted += cpu * overlap
        memory_weighted += memory * overlap
        covered += overlap
        intervals += 1
        cpu_peak = max(cpu_peak, cpu)
        memory_peak = max(memory_peak, memory)
    coverage = covered / duration_seconds
    if coverage < 0.99:
        raise ValueError(
            f"Resource sample coverage is incomplete ({coverage * 100:.2f}%)"
        )
    return {
        "testStartUtc": test_start.astimezone(UTC).isoformat(),
        "testEndUtc": (
            test_start.astimezone(UTC) + timedelta(seconds=duration_seconds)
        ).isoformat(),
        "testDurationSeconds": duration_seconds,
        "intervals": intervals,
        "coveredSeconds": round(covered, 3),
        "coveragePercent": round(min(100.0, coverage * 100), 2),
        "cpuAveragePercent": round(cpu_weighted / covered, 2),
        "cpuPeakPercent": round(cpu_peak, 2),
        "memoryAveragePercent": round(memory_weighted / covered, 2),
        "memoryPeakPercent": round(memory_peak, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--test-start", required=True, help="Offset-aware ISO-8601 time")
    parser.add_argument("--duration-seconds", type=float, required=True)
    args = parser.parse_args()
    try:
        capture = resolve_output(args.input, root=ROOT)
        summary = summarize_test_window(
            capture, test_start=_timestamp(args.test_start),
            duration_seconds=args.duration_seconds,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
