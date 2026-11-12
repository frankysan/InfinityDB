#!/usr/bin/env python3
"""Run InfinityDB development checks through one consistent entry point."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shlex
import shutil
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
    from tools.browser_test_host_profile import linux_four_slots_enabled
    from tools.test_sections import load_test_sections
except ModuleNotFoundError:  # Direct execution as tools/run_checks.py.
    from asset_validation import (  # type: ignore[no-redef]
        ASSET_MODES,
        AssetModeSelection,
        select_asset_mode,
    )
    from browser_test_host_profile import linux_four_slots_enabled  # type: ignore[no-redef]
    from test_sections import load_test_sections  # type: ignore[no-redef]

STAGE_ORDER = ("test", "lint", "docs", "type", "build", "rules", "preflight")
PROFILES = {
    "code": ("test", "lint", "type"),
    "data": ("build", "rules"),
    "all": STAGE_ORDER,
}
DEFAULT_TEST_WORKERS = "auto"
DEFAULT_TEST_DISTRIBUTION = "worksteal"
TEST_DISTRIBUTIONS = ("worksteal", "loadgroup", "browserlanes")
TEST_SECTIONS = load_test_sections()
TEST_SECTION_NAMES = tuple(TEST_SECTIONS)
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
PUBLICATION_MANIFEST = REPO_ROOT / "data" / "manifests" / "symbol-publication.json"
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
            validate_report_destination(report_path)
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
        description=(
            "Run InfinityDB tests, linting, Markdown checks, "
            "type checks, and database builds."
        ),
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
        help="Run all stages, including isolated preflight (may download Python packages).",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help=(
            "Optional pytest/Ruff targets. Test targets should be pytest-compatible "
            "paths or node IDs; docs/type/build/rules stages ignore these targets."
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
            "Graphical asset policy for test/preflight stages: off runs hermetic "
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
            "worker selection. Test/preflight stages default to auto; use 0 for serial execution."
        ),
    )
    parser.add_argument(
        "--test-dist",
        choices=TEST_DISTRIBUTIONS,
        default=None,
        help=(
            "pytest-xdist scheduling strategy; defaults to worksteal. "
            "Use loadgroup for browser modules or browserlanes to consolidate "
            "Chromium acceptance into two opt-in worker groups."
        ),
    )
    parser.add_argument(
        "--split-scenario-faq", action="store_true",
        help="Split Scenario FAQ across two groups in four-lane browserlanes mode.",
    )
    parser.add_argument(
        "--reuse-browser", action="store_true",
        help="Reuse one capacity-owned Chrome across group B in four-lane browserlanes mode.",
    )
    parser.add_argument(
        "--browser-metrics", action="store_true",
        help="Write per-worker Chromium slot wait/hold JSONL to ignored local/benchmarks.",
    )
    parser.add_argument(
        "--skip-summary", action=argparse.BooleanOptionalAction, default=None,
        help=(
            "Group actual pytest skip reasons by count; defaults on for unfiltered "
            "full test suites. Use --no-skip-summary to suppress this report."
        ),
    )
    parser.add_argument(
        "--skip-details", action="store_true",
        help="Also print each skipped test ID and reason for cross-host comparisons.",
    )
    parser.add_argument(
        "--browser-slot-count", type=int, choices=(2, 3, 4), default=2,
        help="Experimental maximum concurrent Chromium tests (default: 2).",
    )
    parser.add_argument(
        "--browser-lane-count", type=int, choices=(2, 3, 4), default=2,
        help="Experimental number of grouped Chromium workers (default: 2).",
    )
    parser.add_argument(
        "--test-section",
        action="append",
        choices=TEST_SECTION_NAMES,
        help=(
            "Run one maintained pytest section; repeat to combine sections. "
            "Available sections: " + ", ".join(TEST_SECTION_NAMES) + "."
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
        "--source-occupancy-gate",
        action="store_true",
        help=(
            "Before the rules stage, require a verified paired Army raw database "
            "with no populated unrepresented source fields (1.0 release review)."
        ),
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failed or errored stage.",
    )
    return parser


_BROWSER_PROFILE_OVERRIDES = frozenset({
    "--test-workers", "--test-dist", "--browser-slot-count",
    "--browser-lane-count", "--split-scenario-faq", "--reuse-browser",
})


def apply_host_browser_test_defaults(
    args: argparse.Namespace,
    argv: list[str],
    *,
    profile_enabled: bool,
) -> bool:
    """Use the tested Linux profile only with an otherwise unmodified test setup.

    Explicit scheduling/capacity flags always retain their normal semantics.
    """
    if not profile_enabled or any(
        token.split("=", 1)[0] in _BROWSER_PROFILE_OVERRIDES
        for token in argv
    ):
        return False
    args.test_workers = "8"
    args.test_dist = "browserlanes"
    args.browser_slot_count = 4
    args.browser_lane_count = 4
    args.split_scenario_faq = True
    return True


def normalize_report_target_args(argv: list[str]) -> list[str]:
    """Keep a pytest target after bare --report from becoming an output path.

    --report PATH remains supported for explicit report destinations such as
    reports/checks.txt; --report=PATH is unambiguous for other filenames.
    """
    tokens = list(argv)
    for i, token in enumerate(tokens[:-1]):
        if token != "--report":
            continue
        following = tokens[i + 1]
        if following.startswith("-"):
            continue
        candidate = following.replace("\\", "/")
        if (candidate.endswith(".py") or "::" in candidate
                or candidate == "tests" or candidate.startswith("tests/")):
            tokens.pop(i)
            tokens.append("--report")
            break
    return tokens


def validate_report_destination(path: Path) -> None:
    """Never truncate a source file or any Git-tracked file as a check log."""
    if path.suffix.lower() in {
        ".py", ".pyi", ".md", ".json", ".toml", ".yaml", ".yml",
        ".js", ".ts", ".css", ".html", ".svg", ".db", ".sqlite",
    }:
        raise ValueError(f"Refusing to write a check report into a source/data file: {path}")
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return
    try:
        tracked = subprocess.run(
            ("git", "ls-files", "--error-unmatch", "--", relative.as_posix()),
            cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError as exc:
        raise ValueError(f"Cannot verify whether report destination is tracked: {path}") from exc
    if tracked.returncode == 0:
        raise ValueError(f"Refusing to overwrite Git-tracked file with report: {path}")
    if tracked.returncode != 1:
        raise ValueError(f"Cannot verify whether report destination is tracked: {path}")


def selected_stage_names(args: argparse.Namespace) -> tuple[str, ...]:
    if args.all:
        return STAGE_ORDER
    if args.profile:
        return PROFILES[args.profile]
    requested = set(args.stage or ())
    return tuple(name for name in STAGE_ORDER if name in requested)


def should_summarize_skips(
    stage_names: tuple[str, ...],
    targets: list[str],
    sections: tuple[str, ...],
    choice: bool | None,
) -> bool:
    """Keep targeted/preflight reporting opt-in, but audit full-suite skips."""
    if choice is not None:
        return choice
    return "test" in stage_names and not targets and not sections


def stage_definitions(
    stage_names: tuple[str, ...],
    targets: list[str],
    *,
    build_source: Path | None,
    include_full_assets: bool = False,
    test_workers: str = DEFAULT_TEST_WORKERS,
    test_distribution: str = DEFAULT_TEST_DISTRIBUTION,
    test_sections: tuple[str, ...] = (),
    browser_slot_count: int = 2,
    browser_lane_count: int = 2,
    split_scenario_faq: bool = False,
    reuse_browser: bool = False,
    skip_summary: bool = False,
    skip_details: bool = False,
) -> list[Stage]:
    python = sys.executable
    stages: list[Stage] = []
    for name in stage_names:
        if name in {"test", "preflight"}:
            command = (
                [python, "-m", "pytest"] if name == "test" else
                [python, str(REPO_ROOT / "tools" / "ci_preflight.py"), "--isolated",
                 "--assets", "required" if include_full_assets else "off", "--"]
            )
            if test_workers != "0":
                distribution = (
                    "loadgroup" if test_distribution == "browserlanes" else test_distribution
                )
                command.extend(("-n", test_workers, "--dist", distribution))
                if test_distribution == "browserlanes":
                    command.append("--browser-lanes")
                    if split_scenario_faq:
                        command.append("--split-scenario-faq")
                    if reuse_browser:
                        command.append("--reuse-browser")
            if browser_slot_count != 2:
                command.extend(("--browser-slot-count", str(browser_slot_count)))
            if browser_lane_count != 2:
                command.extend(("--browser-lane-count", str(browser_lane_count)))
            if targets and name == "test":
                command.extend(targets)
            asset_marker = (
                "full_assets or not full_assets" if include_full_assets else "not full_assets"
            )
            if test_sections and name == "test":
                section_marker = " or ".join(
                    TEST_SECTIONS[section].marker for section in test_sections
                )
                marker = f"({asset_marker}) and ({section_marker})"
            else:
                marker = asset_marker
            if skip_summary:
                command.append("--infinitydb-skip-summary")
            if skip_details and name == "test":
                command.append("--infinitydb-skip-details")
            command.extend(("-m", marker, "-q"))
        elif name == "lint":
            command = [python, "-m", "ruff", "check"]
            command.extend(targets or DEFAULT_LINT_TARGETS)
        elif name == "docs":
            # npm run only invokes the locally pinned dependency; it does not
            # install packages or contact the registry. Bootstrap with npm ci.
            command = [shutil.which("npm") or "npm", "run", "lint:docs"]
        elif name == "type":
            command = [python, "-m", "pyright", "--pythonpath", python]
        elif name == "build":
            command = [python, "-m", "infinity_army_data", "build"]
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
                str(Path(tempfile.mkdtemp(prefix="infinitydb-check-rules-")) / "rules_n5.db"),
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


def run_stage(
    stage: Stage, reporter: Reporter, *, source_occupancy_gate: bool = False,
    browser_metrics_directory: Path | None = None,
) -> StageResult:
    reporter.write()
    reporter.write(f"[{stage.name.upper()}]")
    reporter.write()

    started = time.perf_counter()
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(MODULE_ROOT)
        if not pythonpath
        else str(MODULE_ROOT) + (os.pathsep + pythonpath)
    )
    commands: list[tuple[str, ...]] = []
    if stage.name == "rules":
        if source_occupancy_gate:
            commands.append((
                sys.executable, "-m", "tools.audit_source_presentation",
                "data/generated/army.db", "--require-no-occupied-gaps",
            ))
        commands.append((
            sys.executable, "-m", "tools.audit_rules_interactions",
            "--check-output", "docs/rules-interaction-checklist.md",
            "--require-release", "1.0.0",
        ))
    commands.append(stage.command)
    if stage.name == "build":
        # The small portable fixture need not match the full symbol publication.
        # Exercise the application-only exporter after the source pipeline.
        # Paired raw export remains an explicit legacy compatibility test.
        output = Path(stage.command[stage.command.index("--output-dir") + 1])
        commands.append((
            sys.executable, "-m", "infinity_db", "export",
            str(output / "normalized.json"), str(output / "army.db"),
        ))
    if stage.name == "docs":
        commands.append((sys.executable, "-m", "tools.check_doc_links"))
        commands.append((sys.executable, "-m", "tools.check_v1_backlog"))
    for command in commands:
        reporter.write(f"Command: {format_command(command)}")
        reporter.write()
        # Python's perf_counter shares a system-wide clock across processes.
        # Pass the timestamp immediately before spawning pytest so its xdist
        # plugin can report interpreter and pytest startup separately.
        command_env = dict(env)
        if stage.name == "test":
            command_env["INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER"] = repr(time.perf_counter())
            if browser_metrics_directory is not None:
                command_env["INFINITYDB_BROWSER_METRICS_DIRECTORY"] = str(browser_metrics_directory)
                reporter.write(
                    f"Chromium metrics: {browser_metrics_directory.relative_to(REPO_ROOT)}"
                )
        else:
            command_env.pop("INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER", None)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
                cwd=REPO_ROOT,
                env=command_env,
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
        if returncode != 0:
            break
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
        effective_argv = normalize_report_target_args(
            sys.argv[1:] if argv is None else argv
        )
        args = build_parser().parse_args(effective_argv)
        stage_names = selected_stage_names(args)
        if "test" in stage_names and "preflight" not in stage_names:
            apply_host_browser_test_defaults(
                args, effective_argv,
                profile_enabled=linux_four_slots_enabled(REPO_ROOT),
            )
        runs_pytest = bool({"test", "preflight"} & set(stage_names))
        if args.build_source is not None and "build" not in stage_names:
            build_parser().error("--build-source requires the build stage")
        if args.test_workers is not None and not runs_pytest:
            build_parser().error("--test-workers requires the test or preflight stage")
        if args.test_dist is not None and not runs_pytest:
            build_parser().error("--test-dist requires the test or preflight stage")
        if args.test_section and "test" not in stage_names:
            build_parser().error("--test-section requires the test stage")
        if args.split_scenario_faq and (
            "test" not in stage_names or args.test_dist != "browserlanes"
            or args.browser_lane_count != 4 or args.test_workers == "0"
        ):
            build_parser().error(
                "--split-scenario-faq requires --stage test, --test-dist browserlanes, "
                "--browser-lane-count 4 and parallel workers"
            )
        if args.reuse_browser and (
            "test" not in stage_names or args.test_dist != "browserlanes"
            or args.browser_lane_count != 4 or args.browser_slot_count != 4
            or args.test_workers == "0"
        ):
            build_parser().error(
                "--reuse-browser requires --stage test, --test-dist browserlanes, "
                "--browser-lane-count 4, --browser-slot-count 4 and parallel workers"
            )
        if args.browser_metrics and "test" not in stage_names:
            build_parser().error("--browser-metrics requires the test stage")
        if args.skip_summary is not None and not runs_pytest:
            build_parser().error("--skip-summary requires the test or preflight stage")
        if args.skip_details and "test" not in stage_names:
            build_parser().error("--skip-details requires the test stage")
        if (
            (args.browser_slot_count != 2 or args.browser_lane_count != 2)
            and "test" not in stage_names
        ):
            build_parser().error("browser slot/lane counts require the test stage")
        if (
            args.browser_lane_count != 2
            and (args.test_dist or DEFAULT_TEST_DISTRIBUTION) != "browserlanes"
        ):
            build_parser().error("--browser-lane-count requires --test-dist browserlanes")
        if args.browser_lane_count > 2 and args.test_workers == "0":
            build_parser().error("multiple browser lanes require pytest-xdist workers")
        if args.source_occupancy_gate and "rules" not in stage_names:
            build_parser().error("--source-occupancy-gate requires the rules stage")
        test_workers = (
            args.test_workers
            if args.test_workers is not None
            else (DEFAULT_TEST_WORKERS if runs_pytest else "0")
        )
        if test_workers != "auto":
            try:
                worker_count = int(test_workers)
            except ValueError:
                build_parser().error("--test-workers must be 0, auto, or a positive integer")
            if worker_count < 0:
                build_parser().error("--test-workers must be 0, auto, or a positive integer")
            test_workers = str(worker_count)
        if ("test" in stage_names and test_workers != "0"
                and importlib.util.find_spec("xdist") is None):
            raise ValueError(
                "pytest-xdist is required for parallel test execution; "
                "install the project dev dependencies"
            )
        asset_selection = (
            select_asset_mode(
                args.assets,
                STATIC_ROOT,
                publication_manifest=PUBLICATION_MANIFEST,
            )
            if runs_pytest
            else None
        )
        test_sections = tuple(dict.fromkeys(args.test_section or ()))
        stages = stage_definitions(
            stage_names,
            args.targets,
            build_source=args.build_source,
            include_full_assets=bool(
                asset_selection is not None and asset_selection.include_full_assets
            ),
            test_workers=test_workers,
            test_distribution=args.test_dist or DEFAULT_TEST_DISTRIBUTION,
            test_sections=test_sections,
            browser_slot_count=args.browser_slot_count,
            browser_lane_count=args.browser_lane_count,
            split_scenario_faq=args.split_scenario_faq,
            reuse_browser=args.reuse_browser,
            skip_summary=should_summarize_skips(
                stage_names, args.targets, test_sections, args.skip_summary,
            ),
            skip_details=args.skip_details,
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
            if args.targets and (
                {"docs", "type", "build", "rules", "preflight"} & set(stage_names)
            ):
                reporter.write(
                    "Note: positional targets apply to pytest/Ruff only; "
                    "docs checks repository Markdown, type uses Pyright, "
                    "build uses --build-source, rules uses curated defaults, "
                    "and preflight tests the full indexed suite."
                )
            results: list[StageResult] = []
            for stage in stages:
                failed = [result.name for result in results if result.status in {"FAIL", "ERROR"}]
                if stage.name == "preflight" and failed:
                    reporter.write()
                    reporter.write("[PREFLIGHT]")
                    reporter.write(f"Skipped: earlier stages failed: {', '.join(failed)}")
                    result = StageResult(stage.name, "SKIP", None, 0.0)
                else:
                    if args.browser_metrics and stage.name == "test":
                        metrics_dir = (
                            REPO_ROOT / "local" / "benchmarks"
                            / f"chromium-{started_at:%Y%m%d-%H%M%S}-{os.getpid()}"
                        )
                        result = run_stage(
                            stage, reporter, browser_metrics_directory=metrics_dir,
                        )
                    else:
                        result = run_stage(
                            stage, reporter,
                            source_occupancy_gate=(
                                args.source_occupancy_gate and stage.name == "rules"
                            ),
                        )
                results.append(result)
                if args.fail_fast and result.status != "PASS":
                    break
            write_summary(reporter, results)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_RUNNER_ERROR

    if any(result.status == "ERROR" for result in results):
        return EXIT_RUNNER_ERROR
    if any(result.status == "FAIL" for result in results):
        return EXIT_STAGE_FAILURE
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
