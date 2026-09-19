from __future__ import annotations

import importlib.util
import io
import sys
from datetime import datetime
from pathlib import Path

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


def test_stage_selection_uses_canonical_order() -> None:
    args = run_checks.build_parser().parse_args(
        ["--stage", "lint", "--stage", "test", "tests/test_cli.py"]
    )

    assert run_checks.selected_stage_names(args) == ("test", "lint")


def test_all_profile_includes_code_and_data_stages() -> None:
    args = run_checks.build_parser().parse_args(["--profile", "all"])

    assert run_checks.selected_stage_names(args) == ("test", "lint", "type", "build", "rules")


def test_data_profile_builds_army_and_rules_databases() -> None:
    args = run_checks.build_parser().parse_args(["--profile", "data"])

    assert run_checks.selected_stage_names(args) == ("build", "rules")


def test_stage_commands_use_current_python_and_forward_targets() -> None:
    stages = run_checks.stage_definitions(
        ("test", "lint", "type", "build", "rules"),
        ["tests/test_cli.py"],
        build_source=Path("data/raw/example.zip"),
    )

    assert stages[0].command == (
        sys.executable,
        "-m",
        "pytest",
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
    assert stages[2].command == (
        sys.executable,
        "-m",
        "pyright",
    )
    assert stages[3].command == (
        sys.executable,
        "-m",
        "infinity_db",
        "build",
        str(Path("data/raw/example.zip")),
        "--output-dir",
        stages[3].command[6],
        "--compact",
    )
    assert Path(stages[3].command[6]).parent != Path("data/generated")
    assert stages[4].command == (
        sys.executable,
        "-m",
        "infinity_db",
        "build-rules",
        "--output",
        stages[4].command[5],
    )
    assert Path(stages[4].command[5]).parent != Path("data/generated")


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
        "-m",
        "full_assets or not full_assets",
        "-q",
    )


def test_asset_mode_defaults_to_auto() -> None:
    args = run_checks.build_parser().parse_args(["--stage", "test"])

    assert args.assets == "auto"


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

    assert stage.command == (sys.executable, "-m", "pyright")


def test_report_without_path_uses_timestamped_repository_filename() -> None:
    args = run_checks.build_parser().parse_args(["--profile", "code", "--report"])
    started_at = datetime.fromisoformat("2026-09-17T14:05:06+02:00")

    assert args.report is True
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


def test_build_source_without_build_stage_is_configuration_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run_checks.main(["--stage", "lint", "--build-source", "snapshot.zip"])

    assert result == run_checks.EXIT_RUNNER_ERROR
    assert "--build-source requires the build stage" in capsys.readouterr().err


def test_fixture_build_stage_never_replaces_runtime_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_database = tmp_path / "data" / "generated" / "infinity.db"
    runtime_database.parent.mkdir(parents=True)
    runtime_database.write_bytes(b"real-production-database")
    fixture = Path(__file__).resolve().parent / "fixtures" / "deployment-smoke"
    monkeypatch.setattr(run_checks, "REPO_ROOT", tmp_path)

    assert run_checks.main(["--stage", "build", "--build-source", str(fixture)]) == 0
    assert runtime_database.read_bytes() == b"real-production-database"
