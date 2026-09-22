#!/usr/bin/env python3
"""Run InfinityDB development checks through one consistent entry point."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

try:
    from tools.asset_validation import (
        ASSET_MODES,
        AssetModeSelection,
        select_asset_mode,
    )
except ModuleNotFoundError:  # Direct execution as tools/run_checks.py.
    from asset_validation import (  # type: ignore[no-redef]
        ASSET_MODES,
        AssetModeSelection,
        select_asset_mode,
    )

STAGE_ORDER = ("test", "lint", "type", "build", "rules")
PROFILES = {
    "code": ("test", "lint", "type"),
    "data": ("build", "rules"),
    "all": STAGE_ORDER,
}
DEFAULT_TEST_WORKERS = "auto"
DEFAULT_LINT_TARGETS = (
    "src/infinity_db",
    "src/infinity_army_data",
    "tests",
    "tools",
)
EXIT_OK = 0
EXIT_STAGE_FAILURE = 1
EXIT_RUNNER_ERROR = 2
REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIRECTORY = REPO_ROOT / "reports"
STATIC_ROOT = REPO_ROOT / "src" / "infinity_db" / "web" / "static"
MODULE_ROOT = Path(__file__).resolve().parents[1] / "src"


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
        description="Run InfinityDB tests, linting, type checks, and database-build validation.",
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
            "paths or node IDs; build/rules stages ignore these targets."
        ),
    )
    parser.add_argument(
        "--build-source",
        type=Path,
        help="Optional Army source directory/ZIP passed only to the build stage.",
    )
    parser.add_argument(
        "--assets",
        choices=ASSET_MODES,
        default="auto",
        help=(
            "Third-party graphical asset policy for the test stage: off runs hermetic "
            "tests only; auto uses a complete validated local set when available; "
            "required fails unless that complete set is available."
        ),
    )
    parser.add_argument(
        "--test-workers",
        default=None,
        metavar="N|auto",
        help=(
            "Run pytest through pytest-xdist with N workers or automatic CPU-based "
            "worker selection. Test stages default to auto; use 0 for serial execution."
        ),
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const=True,
        default=False,
        metavar="PATH",
        help=(
            "Also write the complete console transcript to a UTF-8 text file. "
            "With no PATH, use reports/CHECKS YYYYMMDD-HHMMSS.txt."
        ),
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
    include_full_assets: bool = False,
    test_workers: str = DEFAULT_TEST_WORKERS,
) -> list[Stage]:
    python = sys.executable
    stages: list[Stage] = []
    for name in stage_names:
        if name == "test":
            command = [python, "-m", "pytest"]
            if test_workers != "0":
                command.extend(("-n", test_workers, "--dist", "worksteal"))
            if targets:
                command.extend(targets)
            marker = "full_assets or not full_assets" if include_full_assets else "not full_assets"
            command.extend(("-m", marker, "-q"))
        elif name == "lint":
            command = [python, "-m", "ruff", "check"]
            command.extend(targets or DEFAULT_LINT_TARGETS)
        elif name == "type":
            command = [python, "-m", "pyright"]
        elif name == "build":
            command = [python, "-m", "infinity_db", "build"]
            if build_source is not None:
                command.append(str(build_source))
            command.extend(
                ("--output-dir", tempfile.mkdtemp(prefix="infinitydb-check-build-"), "--compact")
            )
        elif name == "rules":
            command = [
                python,
                "-m",
                "infinity_db",
                "build-rules",
                "--output",
                str(Path(tempfile.mkdtemp(prefix="infinitydb-check-rules-")) / "rules.db"),
            ]
        else:  # pragma: no cover - guarded by argparse/selected_stage_names
            raise ValueError(f"Unknown stage: {name}")
        stages.append(Stage(name=name, command=tuple(command)))
    return stages


def resolve_report_path(report: bool | str, started_at: datetime) -> Path | None:
    """Resolve an optional report argument to an explicit output path."""
    if report is False:
        return None
    if report is True:
        timestamp = started_at.strftime("%Y%m%d-%H%M%S")
        return REPORT_DIRECTORY / f"CHECKS {timestamp}.txt"
    return Path(report)


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
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(MODULE_ROOT)
        if not pythonpath
        else str(MODULE_ROOT) + (os.pathsep + pythonpath)
    )
    try:
        process = subprocess.Popen(
            stage.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
            cwd=REPO_ROOT,
            env=env,
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


def write_header(
    reporter: Reporter,
    stages: list[Stage],
    targets: list[str],
    started_at: datetime,
    asset_selection: AssetModeSelection | None,
) -> None:
    reporter.write("InfinityDB check run")
    reporter.write(f"Started: {started_at.isoformat(timespec='seconds')}")
    reporter.write(f"Branch: {git_value('branch', '--show-current')}")
    reporter.write(f"Commit: {git_value('rev-parse', 'HEAD')}")
    reporter.write(f"Stages: {', '.join(stage.name for stage in stages)}")
    if asset_selection is not None:
        reporter.write(f"Assets: {asset_selection.description()}")
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
        if args.build_source is not None and "build" not in stage_names:
            build_parser().error("--build-source requires the build stage")
        if args.test_workers is not None and "test" not in stage_names:
            build_parser().error("--test-workers requires the test stage")
        test_workers = (
            args.test_workers
            if args.test_workers is not None
            else (DEFAULT_TEST_WORKERS if "test" in stage_names else "0")
        )
        if test_workers != "auto":
            try:
                worker_count = int(test_workers)
            except ValueError:
                build_parser().error("--test-workers must be 0, auto, or a positive integer")
            if worker_count < 0:
                build_parser().error("--test-workers must be 0, auto, or a positive integer")
            test_workers = str(worker_count)
        if test_workers != "0" and importlib.util.find_spec("xdist") is None:
            raise ValueError(
                "pytest-xdist is required for parallel test execution; "
                "install the project dev dependencies"
            )
        asset_selection = (
            select_asset_mode(args.assets, STATIC_ROOT) if "test" in stage_names else None
        )
        stages = stage_definitions(
            stage_names,
            args.targets,
            build_source=args.build_source,
            include_full_assets=bool(
                asset_selection is not None and asset_selection.include_full_assets
            ),
            test_workers=test_workers,
        )
    except SystemExit as exc:
        exit_code = exc.code
        return exit_code if isinstance(exit_code, int) else EXIT_RUNNER_ERROR
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_RUNNER_ERROR

    started_at = datetime.now().astimezone()
    report_path = resolve_report_path(args.report, started_at)
    try:
        with Reporter(report_path) as reporter:
            write_header(reporter, stages, args.targets, started_at, asset_selection)
            if args.targets and ({"type", "build", "rules"} & set(stage_names)):
                reporter.write(
                    "Note: positional targets apply to pytest/Ruff only; "
                    "type uses project Pyright configuration, build uses --build-source, "
                    "and rules uses curated defaults."
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
