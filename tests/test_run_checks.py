from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_run_checks():
    path = Path(__file__).resolve().parents[1] / "tools" / "run_checks.py"
    spec = importlib.util.spec_from_file_location("infinitydb_run_checks", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_checks = load_run_checks()


def load_ci_preflight():
    path = Path(__file__).resolve().parents[1] / "tools" / "ci_preflight.py"
    spec = importlib.util.spec_from_file_location("infinitydb_ci_preflight", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ci_preflight = load_ci_preflight()


def test_stage_selection_uses_canonical_order() -> None:
    args = run_checks.build_parser().parse_args(
        ["--stage", "lint", "--stage", "test", "tests/test_cli.py"]
    )

    assert run_checks.selected_stage_names(args) == ("test", "lint")


def test_all_profile_includes_code_and_data_stages() -> None:
    args = run_checks.build_parser().parse_args(["--profile", "all"])

    assert run_checks.selected_stage_names(args) == (
        "test", "lint", "docs", "type", "build", "rules", "preflight"
    )


def test_code_profile_remains_python_only() -> None:
    args = run_checks.build_parser().parse_args(["--profile", "code"])
    assert run_checks.selected_stage_names(args) == ("test", "lint", "type")


def test_data_profile_builds_army_and_rules_databases() -> None:
    args = run_checks.build_parser().parse_args(["--profile", "data"])

    assert run_checks.selected_stage_names(args) == ("build", "rules")


def test_stage_commands_use_current_python_and_forward_targets() -> None:
    stages = run_checks.stage_definitions(
        ("test", "lint", "docs", "type", "build", "rules"),
        ["tests/test_cli.py"],
        build_source=Path("data/raw/example.zip"),
    )

    assert stages[0].command == (
        sys.executable,
        "-m",
        "pytest",
        "-n",
        "auto",
        "--dist",
        "worksteal",
        "tests/test_cli.py",
        "-m",
        "not full_assets",
        "-q",
    )
    assert stages[1].command == (
        sys.executable,
        "-m",
        "ruff",
        "check",
        "tests/test_cli.py",
    )
    assert Path(stages[2].command[0]).name.lower().startswith("npm")
    assert stages[2].command[1:] == ("run", "lint:docs")
    assert stages[3].command == (
        sys.executable,
        "-m",
        "pyright",
        "--pythonpath",
        sys.executable,
    )
    assert stages[4].command == (
        sys.executable,
        "-m",
        "infinity_army_data",
        "build",
        str(Path("data/raw/example.zip")),
        "--output-dir",
        stages[4].command[6],
        "--compact",
    )
    assert Path(stages[4].command[6]).parent != Path("data/generated")
    assert stages[5].command == (
        sys.executable,
        "-m",
        "infinity_db",
        "build-rules",
        "--output",
        stages[5].command[5],
    )
    assert Path(stages[5].command[5]).parent != Path("data/generated")


def test_docs_stage_uses_locked_local_cli_and_ignores_pytest_targets() -> None:
    [stage] = run_checks.stage_definitions(
        ("docs",), ["tests/test_run_checks.py"], build_source=None
    )
    assert stage.name == "docs"
    assert Path(stage.command[0]).name.lower().startswith("npm")
    assert stage.command[1:] == ("run", "lint:docs")
    assert "npx" not in stage.command


def test_test_stage_can_include_full_asset_tests() -> None:
    [stage] = run_checks.stage_definitions(
        ("test",),
        [],
        build_source=None,
        include_full_assets=True,
    )

    assert stage.command == (
        sys.executable,
        "-m",
        "pytest",
        "-n",
        "auto",
        "--dist",
        "worksteal",
        "-m",
        "full_assets or not full_assets",
        "-q",
    )


def test_asset_mode_defaults_to_auto() -> None:
    args = run_checks.build_parser().parse_args(["--stage", "test"])

    assert args.assets == "auto"


def test_test_workers_default_is_resolved_by_the_test_stage() -> None:
    args = run_checks.build_parser().parse_args(["--stage", "test"])

    assert args.test_workers is None
    assert run_checks.DEFAULT_TEST_WORKERS == "auto"


def test_test_stage_can_enable_xdist_workers() -> None:
    [stage] = run_checks.stage_definitions(
        ("test",),
        [],
        build_source=None,
        test_workers="4",
    )

    assert stage.command == (
        sys.executable,
        "-m",
        "pytest",
        "-n",
        "4",
        "--dist",
        "worksteal",
        "-m",
        "not full_assets",
        "-q",
    )


def test_skip_summary_is_opt_in_for_test_and_isolated_preflight() -> None:
    stages = run_checks.stage_definitions(
        ("test", "preflight"), [], build_source=None, test_workers="2",
        skip_summary=True,
    )
    assert all("--infinitydb-skip-summary" in stage.command for stage in stages)
    defaults = run_checks.stage_definitions(
        ("test", "preflight"), [], build_source=None, test_workers="2",
    )
    assert all("--infinitydb-skip-summary" not in stage.command for stage in defaults)


@pytest.mark.parametrize(
    ("stages", "targets", "sections", "choice", "expected"),
    (
        (("test",), [], (), None, True),
        (("test",), ["tests/test_army_snapshot_source.py"], (), None, False),
        (("test",), [], ("browser",), None, False),
        (("preflight",), [], (), None, False),
        (("test", "preflight"), [], (), None, True),
        (("test",), [], (), False, False),
        (("test",), ["tests/test_army_snapshot_source.py"], (), True, True),
    ),
)
def test_skip_summary_auto_enables_only_unfiltered_full_suite(
    stages: tuple[str, ...], targets: list[str], sections: tuple[str, ...],
    choice: bool | None, expected: bool,
) -> None:
    assert run_checks.should_summarize_skips(stages, targets, sections, choice) is expected


def test_skip_summary_cli_supports_explicit_opt_out() -> None:
    parser = run_checks.build_parser()
    assert parser.parse_args(["--stage", "test"]).skip_summary is None
    assert parser.parse_args(["--stage", "test", "--skip-summary"]).skip_summary is True
    assert parser.parse_args(["--stage", "test", "--no-skip-summary"]).skip_summary is False


def test_skip_summary_rejects_non_pytest_stage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_checks.main(["--stage", "lint", "--skip-summary"]) == (
        run_checks.EXIT_RUNNER_ERROR
    )
    assert "--skip-summary requires the test or preflight stage" in capsys.readouterr().err


def test_skip_details_are_opt_in_and_identify_each_skipped_test(
    capsys: pytest.CaptureFixture[str],
) -> None:
    [stage] = run_checks.stage_definitions(
        ("test",), [], build_source=None, skip_details=True,
    )
    assert "--infinitydb-skip-details" in stage.command
    [default_stage] = run_checks.stage_definitions(
        ("test",), [], build_source=None,
    )
    assert "--infinitydb-skip-details" not in default_stage.command
    [preflight] = run_checks.stage_definitions(
        ("preflight",), [], build_source=None, skip_details=True,
    )
    assert "--infinitydb-skip-details" not in preflight.command
    assert run_checks.main(["--stage", "docs", "--skip-details"]) == (
        run_checks.EXIT_RUNNER_ERROR
    )
    assert "--skip-details requires the test stage" in capsys.readouterr().err


def test_test_stage_can_group_browser_modules_without_changing_default() -> None:
    [stage] = run_checks.stage_definitions(
        ("test",), [], build_source=None,
        test_workers="4", test_distribution="loadgroup",
    )
    assert stage.command[3:7] == ("-n", "4", "--dist", "loadgroup")


def test_test_stage_can_schedule_two_browser_lanes() -> None:
    [stage] = run_checks.stage_definitions(
        ("test",), [], build_source=None,
        test_workers="8", test_distribution="browserlanes",
    )
    assert stage.command[3:8] == (
        "-n", "8", "--dist", "loadgroup", "--browser-lanes",
    )
    assert stage.command[8:] == ("-m", "not full_assets", "-q")


@pytest.mark.parametrize("stage_name", ("test", "preflight"))
def test_test_and_preflight_preserve_explicit_chromium_capacity(stage_name: str) -> None:
    [stage] = run_checks.stage_definitions(
        (stage_name,), [], build_source=None,
        test_workers="8", test_distribution="browserlanes",
        browser_slot_count=4, browser_lane_count=3,
    )
    start = stage.command.index("-n")
    assert stage.command[start:start + 9] == (
        "-n", "8", "--dist", "loadgroup", "--browser-lanes",
        "--browser-slot-count", "4", "--browser-lane-count", "3",
    )


def test_browser_reuse_opt_in_only_adds_flag_for_four_lane_benchmark() -> None:
    [pooled] = run_checks.stage_definitions(
        ("test",), [], build_source=None,
        test_workers="8", test_distribution="browserlanes",
        browser_slot_count=4, browser_lane_count=4, reuse_browser=True,
    )
    assert "--reuse-browser" in pooled.command
    [regular] = run_checks.stage_definitions(
        ("test",), [], build_source=None,
        test_workers="8", test_distribution="browserlanes",
        browser_slot_count=4, browser_lane_count=4,
    )
    assert "--reuse-browser" not in regular.command


@pytest.mark.parametrize("args", [
    ["--stage", "test", "--reuse-browser"],
    ["--stage", "test", "--test-dist", "browserlanes",
     "--browser-slot-count", "4", "--reuse-browser"],
    ["--stage", "test", "--test-dist", "browserlanes",
     "--browser-lane-count", "4", "--reuse-browser"],
    ["--stage", "test", "--test-dist", "browserlanes",
     "--browser-lane-count", "4", "--browser-slot-count", "4",
     "--test-workers", "0", "--reuse-browser"],
])
def test_browser_reuse_rejects_unsafe_modes(
    args: list[str], capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_checks.main(args) == run_checks.EXIT_RUNNER_ERROR
    assert "--reuse-browser requires" in capsys.readouterr().err


@pytest.mark.parametrize("stage_name", ("test", "preflight"))
def test_four_lane_scenario_split_is_explicit_opt_in(stage_name: str) -> None:
    [stage] = run_checks.stage_definitions(
        (stage_name,), [], build_source=None,
        test_workers="8", test_distribution="browserlanes",
        browser_slot_count=4, browser_lane_count=4,
        split_scenario_faq=True,
    )
    start = stage.command.index("-n")
    assert stage.command[start:start + 10] == (
        "-n", "8", "--dist", "loadgroup", "--browser-lanes",
        "--split-scenario-faq", "--browser-slot-count", "4",
        "--browser-lane-count", "4",
    )
    [ordinary] = run_checks.stage_definitions(
        ("test",), [], build_source=None, test_distribution="browserlanes",
        browser_slot_count=4, browser_lane_count=4,
    )
    assert "--split-scenario-faq" not in ordinary.command


@pytest.mark.parametrize("args", [
    ["--stage", "test", "--split-scenario-faq"],
    ["--stage", "test", "--test-dist", "browserlanes", "--split-scenario-faq"],
    ["--stage", "lint", "--split-scenario-faq"],
])
def test_scenario_split_rejects_invalid_modes(
    args: list[str], capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_checks.main(args) == run_checks.EXIT_RUNNER_ERROR
    assert "--split-scenario-faq requires" in capsys.readouterr().err


def test_nondefault_browser_lanes_require_browserlane_scheduler(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_checks.main([
        "--stage", "test", "--browser-lane-count", "3",
    ]) == run_checks.EXIT_RUNNER_ERROR
    assert "--test-dist browserlanes" in capsys.readouterr().err


def test_test_distribution_requires_test_or_preflight_stage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run_checks.main(["--stage", "lint", "--test-dist", "loadgroup"])
    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "--test-dist requires the test or preflight stage" in capsys.readouterr().err


def test_test_stage_can_force_serial_execution() -> None:
    [stage] = run_checks.stage_definitions(
        ("test",),
        [],
        build_source=None,
        test_workers="0",
    )

    assert stage.command == (
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "not full_assets",
        "-q",
    )


def test_test_stage_can_select_one_maintained_section() -> None:
    [stage] = run_checks.stage_definitions(
        ("test",),
        [],
        build_source=None,
        test_workers="0",
        test_sections=("web",),
    )

    assert stage.command == (
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "(not full_assets) and (section_web)",
        "-q",
    )


def test_test_stage_can_combine_maintained_sections_and_assets() -> None:
    [stage] = run_checks.stage_definitions(
        ("test",),
        [],
        build_source=None,
        include_full_assets=True,
        test_workers="0",
        test_sections=("model", "assets"),
    )

    assert stage.command == (
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "(full_assets or not full_assets) and (section_model or section_assets)",
        "-q",
    )


def test_test_workers_require_test_or_preflight_stage(capsys: pytest.CaptureFixture[str]) -> None:
    result = run_checks.main(["--stage", "lint", "--test-workers", "2"])

    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "--test-workers requires the test or preflight stage" in capsys.readouterr().err


def test_test_sections_require_test_stage(capsys: pytest.CaptureFixture[str]) -> None:
    result = run_checks.main(["--stage", "lint", "--test-section", "web"])

    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "--test-section requires the test stage" in capsys.readouterr().err


def test_default_parallel_test_workers_require_xdist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_checks.importlib.util, "find_spec", lambda name: None)

    result = run_checks.main(["--stage", "test", "--assets", "off"])

    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "pytest-xdist is required" in capsys.readouterr().err


def test_parallel_test_workers_require_xdist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_checks.importlib.util, "find_spec", lambda name: None)

    result = run_checks.main(["--stage", "test", "--assets", "off", "--test-workers", "2"])

    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "pytest-xdist is required" in capsys.readouterr().err


def test_lint_stage_uses_project_defaults_without_targets() -> None:
    [stage] = run_checks.stage_definitions(("lint",), [], build_source=None)

    assert stage.command == (
        sys.executable,
        "-m",
        "ruff",
        "check",
        *run_checks.DEFAULT_LINT_TARGETS,
    )


def test_default_lint_targets_cover_complete_tools_tree() -> None:
    assert "tools" in run_checks.DEFAULT_LINT_TARGETS
    assert not any(target.startswith("tools/") for target in run_checks.DEFAULT_LINT_TARGETS)


def test_type_stage_uses_project_pyright_configuration() -> None:
    [stage] = run_checks.stage_definitions(("type",), [], build_source=None)

    assert stage.command == (sys.executable, "-m", "pyright", "--pythonpath", sys.executable)


def test_report_without_path_uses_timestamped_repository_filename() -> None:
    args = run_checks.build_parser().parse_args(["--profile", "code", "--report"])
    started_at = datetime.fromisoformat("2026-09-17T14:05:06+02:00")

    assert args.report is True
    assert run_checks.REPORT_DIRECTORY == run_checks.REPO_ROOT / "local/reports/checks"
    assert run_checks.resolve_report_path(args.report, started_at) == (
        run_checks.REPORT_DIRECTORY / "CHECKS 20260917-140506.txt"
    )


def test_explicit_report_path_is_preserved() -> None:
    args = run_checks.build_parser().parse_args(
        ["--profile", "code", "--report", "custom/check-output.txt"]
    )
    started_at = datetime.fromisoformat("2026-09-17T14:05:06+02:00")

    assert run_checks.resolve_report_path(args.report, started_at) == Path(
        "custom/check-output.txt"
    )


def test_bare_report_before_pytest_target_preserves_target() -> None:
    argv = ["--stage", "test", "--report", "tests/test_verify_scenario_faq_browser.py"]
    parsed = run_checks.build_parser().parse_args(
        run_checks.normalize_report_target_args(argv)
    )
    assert parsed.report is True
    assert parsed.targets == ["tests/test_verify_scenario_faq_browser.py"]


def test_explicit_report_filename_still_parses_as_destination() -> None:
    argv = ["--stage", "test", "--report", "reports/my-check.txt"]
    parsed = run_checks.build_parser().parse_args(
        run_checks.normalize_report_target_args(argv)
    )
    assert parsed.report == "reports/my-check.txt"
    assert parsed.targets == []


def test_source_file_cannot_be_used_as_report_destination(tmp_path: Path) -> None:
    source = tmp_path / "test_example.py"
    source.write_text("original", encoding="utf-8")
    with pytest.raises(ValueError, match="source/data file"):
        run_checks.Reporter(source)
    assert source.read_text(encoding="utf-8") == "original"


def test_git_tracked_file_cannot_be_used_as_report_destination() -> None:
    # The isolated CI preflight exports tracked files without .git metadata.
    # Both a confirmed tracked path and an unverifiable path must fail closed.
    with pytest.raises(
        ValueError, match="Git-tracked|Cannot verify whether report destination is tracked",
    ):
        run_checks.validate_report_destination(run_checks.REPO_ROOT / "LICENSE")


def test_report_destination_refuses_when_git_cannot_verify_tracking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run_checks.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=128),
    )
    with pytest.raises(ValueError, match="Cannot verify whether report destination is tracked"):
        run_checks.validate_report_destination(run_checks.REPO_ROOT / "LICENSE")


def test_reporter_tees_output_to_console_and_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_path = tmp_path / "reports" / "checks.txt"

    with run_checks.Reporter(report_path) as reporter:
        reporter.write("hello")
        reporter.write("world", end="")

    assert capsys.readouterr().out == "hello\nworld"
    assert report_path.read_text(encoding="utf-8") == "hello\nworld"


def test_reporter_refuses_existing_transcript_without_truncation(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "reports" / "checks.txt"
    report_path.parent.mkdir()
    before = b"Retained test evidence from an earlier run\n"
    report_path.write_bytes(before)

    with pytest.raises(FileExistsError, match="already exists"):
        run_checks.Reporter(report_path)
    assert report_path.read_bytes() == before


def test_reporter_refuses_output_symlink_before_file_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = tmp_path / "reports" / "dangling.txt"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink",
        lambda path: path == report_path or original_is_symlink(path),
    )
    with pytest.raises(ValueError, match="symlink"):
        run_checks.Reporter(report_path)
    assert not report_path.exists()


def test_reporter_refuses_late_collision_after_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = tmp_path / "reports" / "late.txt"
    prior = b"another check run claimed the transcript\n"
    original_open = Path.open

    def competing_open(
        path: Path, mode: str = "r", buffering: int = -1,
        encoding: str | None = None, errors: str | None = None,
        newline: str | None = None,
    ):
        if path == report_path and mode == "x":
            path.write_bytes(prior)
        return original_open(
            path, mode, buffering=buffering,
            encoding=encoding, errors=errors, newline=newline,
        )

    monkeypatch.setattr(Path, "open", competing_open)
    with pytest.raises(FileExistsError):
        run_checks.Reporter(report_path)
    assert report_path.read_bytes() == prior


def test_run_checks_collision_blocks_stages_and_returns_runner_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_path = tmp_path / "reports" / "accepted.txt"
    report_path.parent.mkdir()
    prior = b"Earlier acceptance transcript\n"
    report_path.write_bytes(prior)
    monkeypatch.setattr(
        run_checks, "run_stage",
        lambda *_args, **_kwargs: pytest.fail("Collision must block all stages"),
    )
    assert run_checks.main([
        "--stage", "lint", "--report", str(report_path),
    ]) == run_checks.EXIT_RUNNER_ERROR
    assert "already exists" in capsys.readouterr().err
    assert report_path.read_bytes() == prior


def test_default_check_transcript_filename_refuses_same_second_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = datetime.fromisoformat("2026-11-13T10:00:00+01:00")
    monkeypatch.setattr(run_checks, "REPORT_DIRECTORY", tmp_path)
    report_path = run_checks.resolve_report_path(True, started)
    assert report_path is not None
    with run_checks.Reporter(report_path) as reporter:
        reporter.write("first invocation")
    before = report_path.read_bytes()
    with pytest.raises(FileExistsError):
        run_checks.Reporter(run_checks.resolve_report_path(True, started))
    assert report_path.read_bytes() == before


def test_run_stage_streams_output_and_reports_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeProcess:
        stdout = io.StringIO("first line\nsecond line\n")

        def wait(self) -> int:
            return 7

    monkeypatch.setattr(run_checks.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    with run_checks.Reporter() as reporter:
        result = run_checks.run_stage(
            run_checks.Stage("test", ("python", "-m", "pytest")),
            reporter,
        )

    assert result.status == "FAIL"
    assert result.returncode == 7
    output = capsys.readouterr().out
    assert "first line" in output
    assert "second line" in output
    assert "Result: FAIL" in output


def test_test_stage_passes_launch_clock_only_to_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environments: list[dict[str, str]] = []

    class FakeProcess:
        stdout = io.StringIO("ok\n")

        def wait(self) -> int:
            return 0

    def fake_popen(command, **kwargs):
        environments.append(kwargs["env"])
        return FakeProcess()

    monkeypatch.setenv("INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER", "stale")
    monkeypatch.setattr(run_checks.subprocess, "Popen", fake_popen)
    with run_checks.Reporter() as reporter:
        assert run_checks.run_stage(
            run_checks.Stage("test", (sys.executable, "-m", "pytest")), reporter,
        ).status == "PASS"
        assert run_checks.run_stage(
            run_checks.Stage("lint", (sys.executable, "-m", "ruff")), reporter,
        ).status == "PASS"

    assert float(environments[0]["INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER"]) > 0
    assert environments[0]["INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER"] != "stale"
    assert "INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER" not in environments[1]


def test_docs_stage_runs_markdownlint_before_local_link_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        stdout = io.StringIO("validated\n")

        def wait(self) -> int:
            return 0

    def fake_popen(command, **kwargs):
        commands.append(tuple(command))
        return FakeProcess()

    monkeypatch.setattr(run_checks.subprocess, "Popen", fake_popen)
    with run_checks.Reporter() as reporter:
        result = run_checks.run_stage(
            run_checks.Stage("docs", ("npm", "run", "lint:docs")),
            reporter,
        )

    assert result.status == "PASS"
    assert commands == [
        ("npm", "run", "lint:docs"),
        (sys.executable, "-m", "tools.check_doc_links"),
        (sys.executable, "-m", "tools.check_v1_backlog"),
    ]


def test_docs_stage_fails_after_static_backlog_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        stdout = io.StringIO("validated\n")

        def __init__(self, code: int) -> None:
            self.code = code

        def wait(self) -> int:
            return self.code

    def fake_popen(command, **kwargs):
        commands.append(tuple(command))
        return FakeProcess(1 if command[-1] == "tools.check_v1_backlog" else 0)

    monkeypatch.setattr(run_checks.subprocess, "Popen", fake_popen)
    with run_checks.Reporter() as reporter:
        result = run_checks.run_stage(
            run_checks.Stage("docs", ("npm", "run", "lint:docs")), reporter,
        )
    assert result.status == "FAIL"
    assert result.returncode == 1
    assert len(commands) == 3
    assert commands[-1] == (sys.executable, "-m", "tools.check_v1_backlog")


def test_rules_stage_runs_interaction_audit_before_database_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        stdout = io.StringIO("validated\n")

        def wait(self) -> int:
            return 0

    def fake_popen(command, **kwargs):
        commands.append(tuple(command))
        return FakeProcess()

    monkeypatch.setattr(run_checks.subprocess, "Popen", fake_popen)
    with run_checks.Reporter() as reporter:
        result = run_checks.run_stage(
            run_checks.Stage("rules", (sys.executable, "-m", "infinity_db", "build-rules")),
            reporter,
        )

    assert result.status == "PASS"
    assert commands[0] == (
        sys.executable, "-m", "tools.audit_rules_interactions",
        "--check-output", "docs/rules-interaction-checklist.md",
        "--require-release", "1.0.0",
    )
    assert commands[1] == (sys.executable, "-m", "infinity_db", "build-rules")


def test_source_occupancy_gate_requires_rules_stage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run_checks.main(["--stage", "lint", "--source-occupancy-gate"])

    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "--source-occupancy-gate requires the rules stage" in capsys.readouterr().err


def test_opt_in_source_occupancy_gate_runs_before_rules_review_and_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        stdout = io.StringIO("validated\n")

        def wait(self) -> int:
            return 0

    def fake_popen(command, **kwargs):
        commands.append(tuple(command))
        return FakeProcess()

    monkeypatch.setattr(run_checks.subprocess, "Popen", fake_popen)
    with run_checks.Reporter() as reporter:
        result = run_checks.run_stage(
            run_checks.Stage("rules", (sys.executable, "-m", "infinity_db", "build-rules")),
            reporter,
            source_occupancy_gate=True,
        )

    assert result.status == "PASS"
    assert commands == [
        (
            sys.executable, "-m", "tools.audit_source_presentation",
            "data/generated/army.db", "--require-no-occupied-gaps",
        ),
        (
            sys.executable, "-m", "tools.audit_rules_interactions",
            "--check-output", "docs/rules-interaction-checklist.md",
            "--require-release", "1.0.0",
        ),
        (sys.executable, "-m", "infinity_db", "build-rules"),
    ]


def test_source_occupancy_cli_flag_reaches_rules_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoked: list[tuple[str, bool]] = []

    def fake_run_stage(stage, reporter, *, source_occupancy_gate=False):
        invoked.append((stage.name, source_occupancy_gate))
        return run_checks.StageResult(stage.name, "PASS", 0, 0.0)

    monkeypatch.setattr(run_checks, "run_stage", fake_run_stage)
    assert run_checks.main(["--stage", "rules", "--source-occupancy-gate"]) == 0
    assert invoked == [("rules", True)]

    invoked.clear()
    assert run_checks.main(["--stage", "rules"]) == 0
    assert invoked == [("rules", False)]


def test_source_occupancy_failure_blocks_rules_review_and_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        stdout = io.StringIO("Source-field gate: FAIL (paired raw source database unavailable)\n")

        def wait(self) -> int:
            return 1

    def fake_popen(command, **kwargs):
        commands.append(tuple(command))
        return FakeProcess()

    monkeypatch.setattr(run_checks.subprocess, "Popen", fake_popen)
    with run_checks.Reporter() as reporter:
        result = run_checks.run_stage(
            run_checks.Stage("rules", (sys.executable, "-m", "infinity_db", "build-rules")),
            reporter,
            source_occupancy_gate=True,
        )

    assert result.status == "FAIL"
    assert result.returncode == 1
    assert len(commands) == 1
    assert commands[0][2] == "tools.audit_source_presentation"


def test_rules_stage_stops_before_build_when_review_audit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        stdout = io.StringIO("Interaction-review coverage mismatch; missing=['test']\n")

        def wait(self) -> int:
            return 2

    def fake_popen(command, **kwargs):
        commands.append(tuple(command))
        return FakeProcess()

    monkeypatch.setattr(run_checks.subprocess, "Popen", fake_popen)
    with run_checks.Reporter() as reporter:
        result = run_checks.run_stage(
            run_checks.Stage("rules", (sys.executable, "-m", "infinity_db", "build-rules")),
            reporter,
        )

    assert result.status == "FAIL"
    assert result.returncode == 2
    assert len(commands) == 1
    assert commands[0][2] == "tools.audit_rules_interactions"


def test_build_source_without_build_stage_is_configuration_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run_checks.main(["--stage", "lint", "--build-source", "snapshot.zip"])

    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "--build-source requires the build stage" in capsys.readouterr().err


def _git_preflight_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "checkout"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    source = root / "src" / "demo" / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("staged = True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    monkeypatch.setattr(ci_preflight, "REPO_ROOT", root)
    return root, source


def test_ci_preflight_exports_index_not_unstaged_working_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _root, source = _git_preflight_fixture(tmp_path, monkeypatch)
    source.write_text("unstaged = True\n", encoding="utf-8")
    output = tmp_path / "export"
    assert ci_preflight.export_tracked(output) == 1
    assert (output / "src/demo/__init__.py").read_text(encoding="utf-8") == (
        "staged = True\n"
    )
    assert ci_preflight.untracked_files() == []


def test_ci_preflight_reports_nonignored_untracked_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _git_preflight_fixture(tmp_path, monkeypatch)
    (root / "not-in-ci.py").write_text("surprise\n", encoding="utf-8")
    (root / ".gitignore").write_text("ignored.log\n", encoding="utf-8")
    (root / "ignored.log").write_text("ignored\n", encoding="utf-8")
    assert ci_preflight.untracked_files() == [".gitignore", "not-in-ci.py"]


def test_ci_preflight_preserves_executable_index_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _git_preflight_fixture(tmp_path, monkeypatch)
    subprocess.run(
        ["git", "update-index", "--chmod=+x", "src/demo/__init__.py"],
        cwd=root, check=True,
    )
    assert ci_preflight.tracked_entries() == [
        ("src/demo/__init__.py", "100755"),
    ]
    output = tmp_path / "export"
    ci_preflight.export_tracked(output)
    if os.name != "nt":
        assert (output / "src/demo/__init__.py").stat().st_mode & 0o111


@pytest.mark.skipif(os.name == "nt", reason="Windows symlink privilege depends on host policy")
def test_ci_preflight_recreates_git_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _git_preflight_fixture(tmp_path, monkeypatch)
    shortcut = root / "src" / "demo" / "link.py"
    shortcut.symlink_to("__init__.py")
    subprocess.run(["git", "add", "src/demo/link.py"], cwd=root, check=True)
    output = tmp_path / "export"
    assert ci_preflight.export_tracked(output) == 2
    restored = output / "src/demo/link.py"
    assert restored.is_symlink()
    assert os.readlink(restored) == "__init__.py"


def _fake_preflight_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wheel_members: list[str],
):
    export = tmp_path / "export"
    source = export / "src" / "infinity_db"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("", encoding="utf-8")
    logo = source / "web" / "static" / "logo"
    logo.mkdir(parents=True)
    (logo / "design.svg").write_text("design", encoding="utf-8")
    config = export / "config" / "catalogs"
    config.mkdir(parents=True)
    (config / "catalog.json").write_text("{}", encoding="utf-8")
    (export / "pyproject.toml").write_text(
        '[tool.setuptools.data-files]\n'
        '"share/infinity-db/config/catalogs" = ["config/catalogs/catalog.json"]\n',
        encoding="utf-8",
    )
    wheel_dir = tmp_path / "wheels"
    wheel_dir.mkdir()
    with zipfile.ZipFile(wheel_dir / "infinity_db-0.1-py3-none-any.whl", "w") as zipfile_:
        for member in wheel_members:
            zipfile_.writestr(member, "data")
    monkeypatch.setattr(
        ci_preflight, "tracked_files",
        lambda: [
            "src/infinity_db/__init__.py",
            "src/infinity_db/web/static/logo/design.svg",
            "config/catalogs/catalog.json",
        ],
    )
    monkeypatch.setattr(
        ci_preflight.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    return export, wheel_dir


@pytest.mark.parametrize("include_assets", [False, True])
def test_ci_preflight_stage_runs_isolated_full_index_despite_local_targets(
    include_assets: bool,
) -> None:
    [stage] = run_checks.stage_definitions(
        ("preflight",), ["tests/test_run_checks.py"], build_source=None,
        include_full_assets=include_assets,
    )
    assert stage.name == "preflight"
    assert stage.command == (
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "tools" / "ci_preflight.py"),
        "--isolated", "--assets", "required" if include_assets else "off",
        "--", "-n", "auto", "--dist", "worksteal",
        "-m", "full_assets or not full_assets" if include_assets else "not full_assets", "-q",
    )


@pytest.mark.parametrize("selection", [["--all"], ["--profile", "all"]])
def test_full_run_includes_isolated_preflight_after_successful_checks(
    monkeypatch: pytest.MonkeyPatch, selection: list[str],
) -> None:
    invoked = []

    def run(stage, _reporter, **_kwargs):
        invoked.append(stage)
        return run_checks.StageResult(stage.name, "PASS", 0, 0.0)

    monkeypatch.setattr(run_checks, "run_stage", run)
    assert run_checks.main([
        *selection, "--assets", "off", "--test-workers", "0",
        "--test-section", "web", "tests/test_web.py",
    ]) == 0
    assert [stage.name for stage in invoked] == list(run_checks.STAGE_ORDER)
    assert invoked[-1].command[2:] == (
        "--isolated", "--assets", "off", "--", "-m", "not full_assets", "-q",
    )
    assert "tests/test_web.py" in invoked[0].command
    assert "section_web" in invoked[0].command[-2]


@pytest.mark.parametrize("failed_stage", run_checks.STAGE_ORDER[:-1])
@pytest.mark.parametrize("status", ["FAIL", "ERROR"])
def test_full_run_skips_preflight_after_any_previous_failure_but_finishes_other_checks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    failed_stage: str, status: str,
) -> None:
    invoked = []

    def run(stage, _reporter, **_kwargs):
        invoked.append(stage.name)
        if stage.name == failed_stage:
            return run_checks.StageResult(stage.name, status, 1, 0.0)
        return run_checks.StageResult(stage.name, "PASS", 0, 0.0)

    monkeypatch.setattr(run_checks, "run_stage", run)
    expected = run_checks.EXIT_STAGE_FAILURE if status == "FAIL" else run_checks.EXIT_RUNNER_ERROR
    assert run_checks.main(["--all", "--assets", "off", "--test-workers", "0"]) == expected
    assert invoked == list(run_checks.STAGE_ORDER[:-1])
    output = capsys.readouterr().out
    assert f"Skipped: earlier stages failed: {failed_stage}" in output
    assert "preflight SKIP" in output
    assert "Overall: FAIL" in output


def test_full_run_fail_fast_still_stops_before_remaining_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoked = []

    def run(stage, _reporter, **_kwargs):
        invoked.append(stage.name)
        return run_checks.StageResult(stage.name, "FAIL", 1, 0.0)

    monkeypatch.setattr(run_checks, "run_stage", run)
    assert run_checks.main([
        "--all", "--assets", "off", "--test-workers", "0", "--fail-fast",
    ]) == run_checks.EXIT_STAGE_FAILURE
    assert invoked == ["test"]


@pytest.mark.parametrize("workers,distribution", [
    ("0", "worksteal"), ("2", "loadgroup"), ("auto", "browserlanes"),
])
def test_standalone_preflight_forwards_worker_and_distribution_choices(
    monkeypatch: pytest.MonkeyPatch, workers: str, distribution: str,
) -> None:
    invoked = []

    def run(stage, _reporter, **_kwargs):
        invoked.append(stage.command)
        return run_checks.StageResult(stage.name, "PASS", 0, 0.0)

    monkeypatch.setattr(run_checks, "run_stage", run)
    # The fresh environment supplies xdist; a host installation is unnecessary.
    monkeypatch.setattr(run_checks.importlib.util, "find_spec", lambda _name: None)
    assert run_checks.main([
        "--stage", "preflight", "--assets", "off",
        "--test-workers", workers, "--test-dist", distribution,
    ]) == 0
    [command] = invoked
    assert command[2:6] == ("--isolated", "--assets", "off", "--")
    if workers == "0":
        assert "-n" not in command
    else:
        assert command[command.index("-n") + 1] == workers
        assert command[command.index("--dist") + 1] == (
            "loadgroup" if distribution == "browserlanes" else distribution
        )
    assert ("--browser-lanes" in command) is (distribution == "browserlanes")
    assert command[-3:] == ("-m", "not full_assets", "-q")


def test_ci_preflight_rejects_unresolved_index_and_gitlink_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = (
        (b"100644 " + b"0" * 40 + b" 2\tsrc/demo.py\0", "unresolved index entry"),
        (b"160000 " + b"0" * 40 + b" 0\tsrc/submodule\0", "unsupported Git index mode"),
    )
    for output, reason in entries:
        monkeypatch.setattr(ci_preflight, "_git", lambda *_args, data=output: data)
        with pytest.raises(ValueError, match=reason):
            ci_preflight.export_tracked(tmp_path / "export")


def test_ci_preflight_wheel_rejects_multiple_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    export, wheels = _fake_preflight_wheel(
        tmp_path, monkeypatch,
        ["infinity_db/__init__.py"],
    )
    with zipfile.ZipFile(wheels / "another-0.1-py3-none-any.whl", "w") as archive:
        archive.writestr("another/__init__.py", "")
    assert ci_preflight.audit_wheel(export, wheels) == [
        "expected one wheel, found 2",
    ]


def test_ci_preflight_wheel_checks_package_and_configured_shared_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    export, wheels = _fake_preflight_wheel(
        tmp_path, monkeypatch,
        [
            "infinity_db/__init__.py",
            "infinity_db-0.1.data/data/share/infinity-db/config/catalogs/catalog.json",
        ],
    )
    assert ci_preflight.audit_wheel(export, wheels) == []


def test_ci_preflight_wheel_rejects_missing_configured_data_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    export, wheels = _fake_preflight_wheel(
        tmp_path, monkeypatch, ["infinity_db/__init__.py"],
    )
    assert ci_preflight.audit_wheel(export, wheels) == [
        "configured data file not shipped in wheel: share/infinity-db/config/catalogs/catalog.json",
    ]


def test_ci_preflight_wheel_rejects_missing_python_package_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    export, wheels = _fake_preflight_wheel(
        tmp_path, monkeypatch,
        ["infinity_db-0.1.data/data/share/infinity-db/config/catalogs/catalog.json"],
    )
    assert ci_preflight.audit_wheel(export, wheels) == [
        "tracked source file not shipped in wheel: infinity_db/__init__.py",
    ]


@pytest.mark.parametrize(
    ("relative_path", "content"),
    [
        ("namespace_pkg/module.py", "value = 1\n"),
        ("standalone_module.py", "value = 1\n"),
    ],
)
def test_ci_preflight_wheel_rejects_unshipped_sources_without_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
    content: str,
) -> None:
    export, wheels = _fake_preflight_wheel(
        tmp_path, monkeypatch,
        [
            "infinity_db/__init__.py",
            "infinity_db-0.1.data/data/share/infinity-db/config/catalogs/catalog.json",
        ],
    )
    source = export / "src" / relative_path
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(content, encoding="utf-8")
    monkeypatch.setattr(
        ci_preflight, "tracked_files",
        lambda: [
            "src/infinity_db/__init__.py",
            "src/infinity_db/web/static/logo/design.svg",
            f"src/{relative_path}",
            "config/catalogs/catalog.json",
        ],
    )
    assert ci_preflight.audit_wheel(export, wheels) == [
        f"tracked source file not shipped in wheel: {relative_path}",
    ]


def test_ci_preflight_wheel_rejects_configured_untracked_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    export, wheels = _fake_preflight_wheel(
        tmp_path, monkeypatch,
        [
            "infinity_db/__init__.py",
            "infinity_db-0.1.data/data/share/infinity-db/config/catalogs/catalog.json",
        ],
    )
    monkeypatch.setattr(
        ci_preflight, "tracked_files",
        lambda: ["src/infinity_db/__init__.py"],
    )
    assert ci_preflight.audit_wheel(export, wheels) == [
        "configured data file absent from Git index: config/catalogs/catalog.json",
    ]


def test_ci_preflight_main_enforces_untracked_check_even_without_build_or_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(ci_preflight, "untracked_files", lambda: ["missing.py"])
    monkeypatch.setattr(ci_preflight, "export_tracked", lambda _path: 2)
    assert ci_preflight.main(["--skip-wheel", "--skip-pytest"]) == 1
    assert "untracked files" in capsys.readouterr().out
    assert ci_preflight.main(["--skip-wheel", "--skip-pytest", "--allow-untracked"]) == 0


def test_ci_preflight_main_propagates_clean_export_pytest_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ci_preflight, "untracked_files", lambda: [])
    monkeypatch.setattr(ci_preflight, "export_tracked", lambda _path: 2)
    calls = []
    def fake_check(export, environment, pytest_args, **_kwargs):
        calls.append((export, environment, pytest_args))
        return ["pytest failed in clean export (exit 2)"]

    monkeypatch.setattr(ci_preflight, "check_export", fake_check)
    assert ci_preflight.main(["--skip-wheel", "--", "-k", "smoke"]) == 1
    assert calls[0][1:] == (None, ["-k", "smoke"])


def test_isolated_preflight_rejects_skipping_its_tests() -> None:
    with pytest.raises(SystemExit) as exc:
        ci_preflight.main(["--isolated", "--skip-pytest"])
    assert exc.value.code == 2


def test_isolated_preflight_checks_only_declared_environment_and_preserves_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "developer-packages")
    monkeypatch.setenv("PYTHONHOME", "developer-python")
    monkeypatch.setenv("GIT_INDEX_FILE", "developer-index")
    monkeypatch.setenv("PYTEST_ADDOPTS", "--ignore=tests")
    calls = []

    def run(command, *, cwd, env):
        assert cwd == tmp_path / "checkout"
        assert not {"PYTHONHOME", "GIT_INDEX_FILE", "PYTEST_ADDOPTS"} & env.keys()
        if command[2] == "infinity_db":
            assert env["PYTHONPATH"] == str(tmp_path / "checkout/src")
        else:
            assert "PYTHONPATH" not in env
        calls.append(command)
        return SimpleNamespace(returncode=1 if command[2] in {"pytest", "pyright"} else 0)

    monkeypatch.setattr(ci_preflight.subprocess, "run", run)
    assert ci_preflight.check_export(tmp_path / "checkout", tmp_path / "venv", ["-n", "2"]) == [
        "pytest failed in clean export (exit 1)",
        "Pyright failed in isolated export (exit 1)",
    ]
    assert calls[1][1:] == ["-m", "pip", "install", "-e", ".[dev,symbols]"]
    assert calls[1][0] != sys.executable
    assert calls[2][1:] == [
        "-m", "infinity_db", "database-health", "--db-dir", "data/generated",
    ]
    assert calls[3][1:] == ["-m", "tools.verify_deployment_assets"]
    assert calls[4][1:] == ["-m", "tools.run_checks", "--stage", "lint"]
    assert calls[5][1:] == [
        "-m", "pytest", "-q", "-m", "full_assets or not full_assets", "-n", "2",
    ]
    assert calls[6][1:] == ["-m", "pyright", "--pythonpath", calls[1][0]]


@pytest.mark.parametrize("module,message", [
    ("tools.verify_deployment_assets", "indexed deployment-artifact verification failed"),
    ("tools.run_checks", "Ruff failed in isolated export"),
])
def test_indexed_artifact_and_lint_failures_propagate_even_with_svg_checks_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: str, message: str,
) -> None:
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1 if command[2] == module else 0)

    monkeypatch.setattr(ci_preflight.subprocess, "run", run)
    assert ci_preflight.check_export(
        tmp_path, tmp_path / "venv", [], include_full_assets=False,
    ) == [message]
    assert calls[3][-1] == "--skip-svg"
    assert calls[5][-2:] == ["-m", "not full_assets"]


@pytest.mark.parametrize("wheel_fails", [False, True])
def test_isolated_preflight_runs_built_wheel_smoke_only_after_successful_wheel_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    wheel_fails: bool,
) -> None:
    def audit(_export, wheels):
        wheels.mkdir()
        (wheels / "demo.whl").write_bytes(b"wheel fixture")
        return ["wheel content missing"] if wheel_fails else []

    monkeypatch.setattr(ci_preflight, "audit_wheel", audit)
    monkeypatch.setattr(ci_preflight, "untracked_files", lambda: [])
    monkeypatch.setattr(ci_preflight, "export_tracked", lambda _path: 1)
    monkeypatch.setattr(ci_preflight, "check_export", lambda *_args, **_kwargs: [])
    calls = []
    monkeypatch.setattr(ci_preflight.subprocess, "run", lambda command, **_kwargs: (
        calls.append(command) or SimpleNamespace(returncode=1)
    ))
    assert ci_preflight.main(["--isolated", "--assets", "off"]) == 1
    output = capsys.readouterr().out
    if wheel_fails:
        assert not calls
        assert "Installed-wheel smoke skipped" in output
    else:
        assert len(calls) == 1
        assert calls[0][-2:] == ["--assets", "off"]
        assert "installed-wheel CLI/runtime smoke failed" in output


@pytest.mark.parametrize("failed_step", ["venv", "pip", "infinity_db"])
def test_isolated_preflight_stops_when_environment_or_database_set_is_unusable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_step: str,
) -> None:
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1 if command[2] == failed_step else 0)

    monkeypatch.setattr(ci_preflight.subprocess, "run", run)
    problems = ci_preflight.check_export(tmp_path / "checkout", tmp_path / "venv", [])
    assert len(problems) == 1
    assert all(command[2] not in {"pytest", "pyright"} for command in calls)


def test_preflight_validates_selected_set_before_using_current_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setattr(ci_preflight.subprocess, "run", lambda command, **_kwargs: (
        calls.append(command) or SimpleNamespace(returncode=0)
    ))
    assert ci_preflight.check_export(tmp_path, None, ["--collect-only"]) == []
    assert [command[2] for command in calls] == ["infinity_db", "pytest"]
    assert calls[-1][0] == sys.executable


def test_local_source_guard_skips_missing_but_not_present_invalid_bytes(
    tmp_path: Path, require_source_files,
) -> None:
    source = tmp_path / "local-source.pdf"
    with pytest.raises(pytest.skip.Exception, match="Ignored local source files unavailable"):
        require_source_files(source)
    source.write_bytes(b"malformed source still requires validation")
    require_source_files(source)


def test_fixture_build_stage_never_replaces_runtime_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_database = tmp_path / "data" / "generated" / "army.db"
    runtime_database.parent.mkdir(parents=True)
    runtime_database.write_bytes(b"real-production-database")
    fixture = Path(__file__).resolve().parent / "fixtures" / "deployment-smoke"
    monkeypatch.setattr(run_checks, "REPO_ROOT", tmp_path)

    assert run_checks.main(["--stage", "build", "--build-source", str(fixture)]) == 0
    assert runtime_database.read_bytes() == b"real-production-database"
