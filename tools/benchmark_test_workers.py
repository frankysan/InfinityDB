#!/usr/bin/env python3
"""Benchmark pytest-xdist worker counts through the normal InfinityDB check runner."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from tools.run_checks import REPO_ROOT, TEST_SECTION_NAMES, git_value
except ModuleNotFoundError:  # Direct execution as tools/benchmark_test_workers.py.
    from run_checks import REPO_ROOT, TEST_SECTION_NAMES, git_value  # type: ignore[no-redef]

DEFAULT_WORKERS = ("0", "4", "6", "8", "auto")
REPORT_DIRECTORY = REPO_ROOT / "reports"
EXIT_OK = 0
EXIT_BENCHMARK_FAILURE = 1
EXIT_USAGE_ERROR = 2


@dataclass(frozen=True)
class BenchmarkRun:
    workers: str
    repetition: int
    status: str
    returncode: int
    duration_seconds: float


@dataclass(frozen=True)
class WorkerSummary:
    workers: str
    passed_runs: int
    failed_runs: int
    median_seconds: float | None
    minimum_seconds: float | None
    maximum_seconds: float | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark InfinityDB pytest-xdist worker counts through tools/run_checks.py."
        )
    )
    parser.add_argument(
        "--workers",
        nargs="+",
        default=list(DEFAULT_WORKERS),
        metavar="N|auto",
        help=(
            "Worker counts to compare. 0 is serial; auto delegates to pytest-xdist. "
            f"Default: {', '.join(DEFAULT_WORKERS)}."
        ),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help=(
            "Number of runs per worker count. Repeated runs rotate candidates through benchmark "
            "positions and reverse each complete rotation cycle to reduce systematic warm-cache "
            "bias. Default: 1."
        ),
    )
    parser.add_argument(
        "--test-section",
        action="append",
        choices=TEST_SECTION_NAMES,
        help="Benchmark one maintained test section; repeat to combine sections.",
    )
    parser.add_argument(
        "--assets",
        choices=("off", "auto", "required"),
        default="off",
        help="Asset policy passed to the check runner. Default: off for stable comparisons.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional JSON report path. Defaults to reports/TEST-WORKERS <timestamp>.json.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional pytest-compatible paths or node IDs passed through to run_checks.py.",
    )
    return parser


def normalize_workers(values: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        if value == "auto":
            candidate = value
        else:
            try:
                count = int(value)
            except ValueError as exc:
                raise ValueError("workers must be auto or a non-negative integer") from exc
            if count < 0:
                raise ValueError("workers must be auto or a non-negative integer")
            candidate = str(count)
        if candidate not in normalized:
            normalized.append(candidate)
    if not normalized:
        raise ValueError("at least one worker value is required")
    return tuple(normalized)


def benchmark_order(workers: tuple[str, ...], repeat: int) -> tuple[tuple[int, str], ...]:
    """Return deterministic runs with candidates balanced across benchmark positions."""

    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    scheduled: list[tuple[int, str]] = []
    candidate_count = len(workers)
    for repetition_index in range(repeat):
        cycle, offset = divmod(repetition_index, candidate_count)
        base = workers if cycle % 2 == 0 else tuple(reversed(workers))
        ordered = base[offset:] + base[:offset]
        repetition = repetition_index + 1
        scheduled.extend((repetition, worker) for worker in ordered)
    return tuple(scheduled)


def validate_parallel_support(workers: tuple[str, ...]) -> None:
    if any(worker != "0" for worker in workers) and importlib.util.find_spec("xdist") is None:
        raise ValueError(
            "pytest-xdist is required to benchmark parallel worker counts; "
            "install the project dev dependencies"
        )


def benchmark_command(
    workers: str,
    *,
    sections: tuple[str, ...] = (),
    assets: str = "off",
    targets: tuple[str, ...] = (),
) -> tuple[str, ...]:
    command = [
        sys.executable,
        str(REPO_ROOT / "tools" / "run_checks.py"),
        "--stage",
        "test",
        "--assets",
        assets,
        "--test-workers",
        workers,
    ]
    for section in sections:
        command.extend(("--test-section", section))
    command.extend(targets)
    return tuple(command)


def run_once(
    workers: str,
    repetition: int,
    *,
    sections: tuple[str, ...],
    assets: str,
    targets: tuple[str, ...],
) -> tuple[BenchmarkRun, str]:
    command = benchmark_command(
        workers,
        sections=sections,
        assets=assets,
        targets=targets,
    )
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    duration = time.perf_counter() - started
    return (
        BenchmarkRun(
            workers=workers,
            repetition=repetition,
            status="PASS" if completed.returncode == 0 else "FAIL",
            returncode=completed.returncode,
            duration_seconds=duration,
        ),
        completed.stdout,
    )


def summarize_runs(
    workers: tuple[str, ...], runs: list[BenchmarkRun]
) -> tuple[WorkerSummary, ...]:
    summaries: list[WorkerSummary] = []
    for worker in workers:
        worker_runs = [run for run in runs if run.workers == worker]
        passed = [run.duration_seconds for run in worker_runs if run.status == "PASS"]
        failures = len(worker_runs) - len(passed)
        summaries.append(
            WorkerSummary(
                workers=worker,
                passed_runs=len(passed),
                failed_runs=failures,
                median_seconds=statistics.median(passed) if passed else None,
                minimum_seconds=min(passed) if passed else None,
                maximum_seconds=max(passed) if passed else None,
            )
        )
    return tuple(summaries)


def fastest_complete_summary(
    summaries: tuple[WorkerSummary, ...], repeat: int
) -> WorkerSummary | None:
    complete = [
        summary
        for summary in summaries
        if summary.failed_runs == 0
        and summary.passed_runs == repeat
        and summary.median_seconds is not None
    ]
    return min(complete, key=lambda summary: summary.median_seconds or float("inf"), default=None)


def report_path_for(started_at: datetime, requested: Path | None) -> Path:
    if requested is not None:
        return requested
    timestamp = started_at.strftime("%Y%m%d-%H%M%S")
    return REPORT_DIRECTORY / f"TEST-WORKERS {timestamp}.json"


def report_document(
    *,
    started_at: datetime,
    workers: tuple[str, ...],
    repeat: int,
    sections: tuple[str, ...],
    assets: str,
    targets: tuple[str, ...],
    runs: list[BenchmarkRun],
    summaries: tuple[WorkerSummary, ...],
) -> dict[str, Any]:
    fastest = fastest_complete_summary(summaries, repeat)
    return {
        "version": 1,
        "startedAt": started_at.isoformat(timespec="seconds"),
        "branch": git_value("branch", "--show-current"),
        "commit": git_value("rev-parse", "HEAD"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "logicalCpuCount": os.cpu_count(),
        "assets": assets,
        "sections": list(sections),
        "targets": list(targets),
        "repeat": repeat,
        "workers": list(workers),
        "runs": [asdict(run) for run in runs],
        "summaries": [asdict(summary) for summary in summaries],
        "fastestCompleteWorkers": fastest.workers if fastest is not None else None,
    }


def write_report(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        workers = normalize_workers(args.workers)
        if args.repeat < 1:
            parser.error("--repeat must be at least 1")
        sections = tuple(dict.fromkeys(args.test_section or ()))
        targets = tuple(args.targets)
        validate_parallel_support(workers)
        schedule = benchmark_order(workers, args.repeat)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE_ERROR
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    started_at = datetime.now().astimezone()
    runs: list[BenchmarkRun] = []
    failure_output: list[tuple[BenchmarkRun, str]] = []
    total = len(schedule)
    print(
        "Benchmarking test workers: "
        + ", ".join(workers)
        + f"; repeat={args.repeat}; assets={args.assets}"
    )
    if sections:
        print("Sections: " + ", ".join(sections))
    if targets:
        print("Targets: " + ", ".join(targets))

    for index, (repetition, worker) in enumerate(schedule, start=1):
        print(
            f"[{index}/{total}] workers={worker} repetition={repetition} ... ",
            end="",
            flush=True,
        )
        run, output = run_once(
            worker,
            repetition,
            sections=sections,
            assets=args.assets,
            targets=targets,
        )
        runs.append(run)
        print(f"{run.status} {run.duration_seconds:.2f} s")
        if run.status != "PASS":
            failure_output.append((run, output))

    summaries = summarize_runs(workers, runs)
    print("\nMedian wall time")
    for summary in summaries:
        if summary.median_seconds is None:
            timing = "no passing runs"
        else:
            timing = (
                f"{summary.median_seconds:.2f} s "
                f"(min {summary.minimum_seconds:.2f}, max {summary.maximum_seconds:.2f})"
            )
        print(
            f"  workers={summary.workers:<4} {timing}; "
            f"pass={summary.passed_runs} fail={summary.failed_runs}"
        )

    fastest = fastest_complete_summary(summaries, args.repeat)
    if fastest is not None and fastest.median_seconds is not None:
        print(
            f"\nFastest complete configuration: workers={fastest.workers} "
            f"({fastest.median_seconds:.2f} s median)"
        )

    report_path = report_path_for(started_at, args.report)
    document = report_document(
        started_at=started_at,
        workers=workers,
        repeat=args.repeat,
        sections=sections,
        assets=args.assets,
        targets=targets,
        runs=runs,
        summaries=summaries,
    )
    try:
        write_report(report_path, document)
    except OSError as exc:
        print(f"ERROR: could not write benchmark report: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    print(f"Report: {report_path}")

    for run, output in failure_output:
        print(
            f"\n--- failure output: workers={run.workers} repetition={run.repetition} ---",
            file=sys.stderr,
        )
        print(output.rstrip(), file=sys.stderr)

    return EXIT_BENCHMARK_FAILURE if failure_output else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
