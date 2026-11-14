"""Hermetic output and CI handoff checks for the opt-in cross-browser runner."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tools import run_cross_browser_compatibility as runner

SHA = "0123456789abcdef0123456789abcdef01234567"


def test_default_run_has_new_pinned_junit_and_traces_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_checkout_revision", lambda: SHA[:12])
    executed: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in env.items())
        executed.append((command, env))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.main(["--engine", "firefox"]) == 0
    assert len(executed) == 1
    command, env = executed[0]
    directory = env["INFINITYDB_CROSS_BROWSER_ARTIFACT_DIR"]
    assert re.fullmatch(
        r"local/validation/project-infrastructure/cross-browser/"
        r"\d{8}T\d{12}Z-0123456789ab/firefox",
        directory,
    )
    assert (tmp_path / directory).is_dir()
    assert env["INFINITYDB_CROSS_BROWSER_ENGINE"] == "firefox"
    assert command[:4] == [runner.sys.executable, "-m", "pytest", "-q"]
    assert "tests/test_cross_browser_compatibility.py" in command
    assert f"--junitxml={directory}/junit.xml" in command
    assert "local/cross-browser-compatibility" not in " ".join(command)


def test_explicit_output_dir_preserves_failure_status_and_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    output = Path("local/validation/project-infrastructure/cross-browser/test-sha/chromium")
    received: list[dict[str, str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        env = kwargs["env"]
        assert isinstance(env, dict)
        received.append(env)
        directory = tmp_path / output
        (directory / "junit.xml").write_text("<testsuite/>", encoding="utf-8")
        (directory / "chromium-rule-390.zip").write_bytes(b"trace")
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.main(["--engine", "chromium", "--output-dir", str(output)]) == 7
    assert received[0]["INFINITYDB_CROSS_BROWSER_ARTIFACT_DIR"] == output.as_posix()
    assert (tmp_path / output / "junit.xml").read_text(encoding="utf-8") == "<testsuite/>"
    assert (tmp_path / output / "chromium-rule-390.zip").read_bytes() == b"trace"


def test_existing_report_dir_refused_before_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    output = Path("local/validation/project-infrastructure/cross-browser/run/chromium")
    target = tmp_path / output
    target.mkdir(parents=True)
    (target / "junit.xml").write_bytes(b"previous run")

    def unexpected_run(*args: object, **kwargs: object) -> object:
        pytest.fail("Should refuse an existing output directory before pytest")

    monkeypatch.setattr(runner.subprocess, "run", unexpected_run)
    with pytest.raises(SystemExit) as exc:
        runner.main(["--engine", "chromium", "--output-dir", str(output)])
    assert exc.value.code == 2
    assert "Cannot reserve cross-browser evidence directory" in capsys.readouterr().err
    assert (target / "junit.xml").read_bytes() == b"previous run"


@pytest.mark.parametrize(
    "requested",
    [
        Path("data/generated"),
        Path("local/cross-browser-compatibility"),
        Path("local/validation-other/run"),
        Path("../outside"),
    ],
)
def test_output_directory_cannot_escape_local_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requested: Path,
) -> None:
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="beneath repository local/validation"):
        runner._reserve_output_dir("webkit", requested)
    assert not (tmp_path / requested).exists()


def test_hosted_ci_uploads_new_report_tree_even_after_failure() -> None:
    workflow = (
        runner.ROOT / ".github/workflows/cross-browser-compatibility.yml"
    ).read_text(encoding="utf-8")
    assert "if: always()" in workflow
    assert f"path: {runner.REPORT_BASE.as_posix()}/" in workflow
    assert "python -m tools.run_cross_browser_compatibility --engine" in workflow


def test_bad_git_revision_rejected_before_creating_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "ROOT", tmp_path)

    def bad_git(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git"], 0, stdout="not-a-sha")

    monkeypatch.setattr(runner.subprocess, "run", bad_git)
    with pytest.raises(ValueError, match="exact Git revision"):
        runner._reserve_output_dir("msedge")
    assert not (tmp_path / runner.REPORT_BASE).exists()
