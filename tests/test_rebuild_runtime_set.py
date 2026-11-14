"""CLI delegation for the explicit complete runtime build wrapper."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.data import rebuild_runtime_set


def test_rebuild_passes_selected_pair_to_existing_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        rebuild_runtime_set, "infinity_db_main",
        lambda argv: calls.append(argv) or 0,
    )
    assert rebuild_runtime_set.main([
        "--source", "local/data/raw/army/JSON 20260929-114335.zip",
        "--manifest", "local/data/manifests/snapshots/JSON 20260929-114335.json",
    ]) == 0
    assert calls == [[
        "build", str(Path("local/data/raw/army/JSON 20260929-114335.zip")),
        "--snapshot-manifest",
        str(Path("local/data/manifests/snapshots/JSON 20260929-114335.json")),
        "--db-dir", str(Path("data/generated")), "--compact",
    ]]


def test_rebuild_requires_explicit_pair_and_allows_alternate_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(SystemExit):
        rebuild_runtime_set.main(["--source", "army.zip"])
    calls: list[list[str]] = []
    monkeypatch.setattr(
        rebuild_runtime_set, "infinity_db_main",
        lambda argv: calls.append(argv) or 0,
    )
    assert rebuild_runtime_set.main([
        "--source", "army.zip", "--manifest", "army.json",
        "--db-dir", "local/work/build/test-set",
    ]) == 0
    assert calls[-1][-3:] == ["--db-dir", str(Path("local/work/build/test-set")), "--compact"]
    assert Path(calls[-1][1]).name == "army.zip"
