#!/usr/bin/env python3
"""Run InfinityDB development checks through one consistent entry point."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

STAGE_ORDER = ("test", "lint", "build")
PROFILES = {
    "code": ("test", "lint"),
    "data": ("build",),
    "all": STAGE_ORDER,
}
DEFAULT_LINT_TARGETS = (
    "src/infinity_db",
    "src/infinity_army_data",
    "tests",
    "tools/run_checks.py",
)
EXIT_OK = 0
EXIT_STAGE_FAILURE = 1
EXIT_RUNNER_ERROR = 2
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    returncode: int | None
    duration: float


class Reporter:
    """Write identical check output to the console and an optional report file."""

    def __init__(self, report_path: Path | None = None) -> None:
        self._file: TextIO | None = None
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = report_path.open("w", encoding="utf-8", newline="")

    def write(self, text: str = "", *, end: str = "\n") -> None:
        rendered = text + end
        sys.stdout.write(rendered)
        sys.stdout.flush()
        if self._file is not None:
            self._file.write(rendered)
            self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> Reporter:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run InfinityDB tests, linting, and data-build validation.",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--stage",
        action="append",
        choices=STAGE_ORDER,
        help="Run one stage; repeat to select multiple stages.",
    )
    selection.add_argument(
        "--profile",
        choices=tuple(PROFILES),
        help="Run a named stage profile.",
    )
    selection.add_argument(
        "--all",
        action="store_true",
        help="Run all stages (equivalent to --profile all).",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help=(
            "Optional pytest/Ruff targets. Test targets should be pytest-compatible "
            "paths or node IDs; build ignores these targets."
        ),
    )
    parser.add_argument(
        "--build-source",
        type=Path,
        help="Optional Army source directory/ZIP passed only to the build stage.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Also write the complete console transcript to this UTF-8 text file.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failed or errored stage.",
    )
    return parser


def selected_stage_names(args: argparse.Namespace) -> tuple[str, ...]:
    if args.all:
        return STAGE_ORDER
    if args.profile:
        return PROFILES[args.profile]
    requested = set(args.stage or ())
    return tuple(name for name in STAGE_ORDER if name in requested)


def stage_definitions(
    stage_names: tuple[str, ...],
    targets: list[str],
    *,
    build_source: Path | None,
) -> list[Stage]:
    python = sys.executable
    stages: list[Stage] = []
    for name in stage_names:
        if name == "test":
            command = [python, "-m", "pytest"]
            if targets:
                command.extend(targets)
            command.append("-q")
        elif name == "lint":
            command = [python, "-m", "ruff", "check"]
            command.extend(targets or DEFAULT_LINT_TARGETS)
        elif name == "build":
            command = [python, "-m", "infinity_db", "build"]
            if build_source is not None:
                command.append(str(build_source))
            command.append("--compact")
        else:  # pragma: no cover - guarded by argparse/selected_stage_names
            raise ValueError(f"Unknown stage: {name}")
        stages.append(Stage(name=name, command=tuple(command)))
    return stages


def format_command(command: tuple[str, ...]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def git_value(*args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *args),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=REPO_ROOT,
        )
    except OSError:
        return "unknown"
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else "unknown"


def run_stage(stage: Stage, reporter: Reporter) -> StageResult:
    reporter.write()
    reporter.write(f"[{stage.name.upper()}]")
    reporter.write(f"Command: {format_command(stage.command)}")
    reporter.write()

    started = time.perf_counter()
    try:
        process = subprocess.Popen(
            stage.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
            cwd=REPO_ROOT,
        )
    except OSError as exc:
        duration = time.perf_counter() - started
        reporter.write(f"ERROR: could not start command: {exc}")
        reporter.write()
        reporter.write("Result: ERROR")
        reporter.write(f"Duration: {duration:.2f} s")
        return StageResult(stage.name, "ERROR", None, duration)

    assert process.stdout is not None
    for line in process.stdout:
        reporter.write(line, end="")
    returncode = process.wait()
    duration = time.perf_counter() - started
    status = "PASS" if returncode == 0 else "FAIL"
    reporter.write()
    reporter.write(f"Result: {status}")
    reporter.write(f"Duration: {duration:.2f} s")
    return StageResult(stage.name, status, returncode, duration)


def write_header(reporter: Reporter, stages: list[Stage], targets: list[str]) -> None:
    reporter.write("InfinityDB check run")
    reporter.write(f"Started: {datetime.now().astimezone().isoformat(timespec='seconds')}")
    reporter.write(f"Branch: {git_value('branch', '--show-current')}")
    reporter.write(f"Commit: {git_value('rev-parse', 'HEAD')}")
    reporter.write(f"Stages: {', '.join(stage.name for stage in stages)}")
    if targets:
        reporter.write(f"Targets: {', '.join(targets)}")


def write_summary(reporter: Reporter, results: list[StageResult]) -> None:
    reporter.write()
    reporter.write("SUMMARY")
    for result in results:
        reporter.write(f"{result.name:<8} {result.status}")
    overall = "PASS" if results and all(result.status == "PASS" for result in results) else "FAIL"
    reporter.write()
    reporter.write(f"Overall: {overall}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        stage_names = selected_stage_names(args)
        stages = stage_definitions(
            stage_names,
            args.targets,
            build_source=args.build_source,
        )
        if args.build_source is not None and "build" not in stage_names:
            build_parser().error("--build-source requires the build stage")
    except SystemExit as exc:
        return int(exc.code)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_RUNNER_ERROR

    try:
        with Reporter(args.report) as reporter:
            write_header(reporter, stages, args.targets)
            if args.targets and "build" in stage_names:
                reporter.write(
                    "Note: positional targets apply to pytest/Ruff only; build uses --build-source."
                )
            results: list[StageResult] = []
            for stage in stages:
                result = run_stage(stage, reporter)
                results.append(result)
                if args.fail_fast and result.status != "PASS":
                    break
            write_summary(reporter, results)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_RUNNER_ERROR

    if any(result.status == "ERROR" for result in results):
        return EXIT_RUNNER_ERROR
    if any(result.status == "FAIL" for result in results):
        return EXIT_STAGE_FAILURE
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
