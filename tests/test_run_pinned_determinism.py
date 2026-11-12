"""Hermetic contract tests for the isolated determinism Docker runner."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools import run_pinned_determinism as runner


def test_report_path_is_confined_to_local(tmp_path: Path) -> None:
    folder, target = runner._local_report_path(
        tmp_path, Path("local/reports/determinism.json"),
    )
    assert folder == tmp_path / "local/reports"
    assert target == folder / "determinism.json"
    with pytest.raises(ValueError, match="beneath repository local"):
        runner._local_report_path(tmp_path, Path("../outside.json"))
    with pytest.raises(ValueError, match="beneath repository local"):
        runner._local_report_path(tmp_path, Path("data/generated/army.db"))


def test_manifest_container_readonly_checkout_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    def run(*args: str, timeout: int = 900) -> str:
        commands.append(args)
        assert timeout == 1800
        output = tmp_path / "local/reports/determinism.json"
        output.write_text('{"formatVersion":2}', encoding="utf-8")
        return "Determinism manifest generated"

    monkeypatch.setattr(runner, "_docker_command", run)
    runner._run_manifest(tmp_path, Path("local/reports/determinism.json"))
    assert len(commands) == 1
    command = commands[0]
    assert command[:2] == ("run", "--rm")
    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert command[command.index("--platform") + 1] == "linux/amd64"
    mounts = [
        value
        for index, value in enumerate(command)
        if index and command[index - 1] == "--mount"
    ]
    assert f"type=bind,source={tmp_path},target=/workspace,readonly" in mounts
    assert f"type=bind,source={tmp_path / 'local/reports'},target=/output" in mounts
    assert runner.IMAGE in command
    assert command[-5:] == (
        "python", "-m", "tools.build_determinism_manifest",
        "--output", "/output/determinism.json",
    )


def test_manifest_does_not_allow_absolute_outside_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        runner._local_report_path(tmp_path, Path(os.path.abspath(os.sep)))


def test_image_probe_reports_digest_and_container_toolchain(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    recorded: list[tuple[str, ...]] = []

    def fake(*args: str, timeout: int = 900) -> str:
        recorded.append(args)
        if args[:2] == ("image", "inspect"):
            return '["python@sha256:abc"]' if ".RepoDigests" in args[3] else "sha256:xyz"
        if args[:2] == ("run", "--rm"):
            return "git version 2" if "git" in args else "Python 3.11.18 SQLite 3.40 zlib 1.2"
        return "pulled"

    monkeypatch.setattr(runner, "_docker_command", fake)
    runner._image_probe()
    assert len(recorded) == 5
    output = capsys.readouterr().out
    assert "python@sha256:abc" in output
    assert "Python 3.11.18" in output
