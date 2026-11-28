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


@pytest.mark.parametrize("skip_history", [False, True])
def test_rebuild_can_reuse_the_published_source(
    monkeypatch: pytest.MonkeyPatch, skip_history: bool,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        rebuild_runtime_set, "recorded_source_paths",
        lambda directory: (Path("pinned.zip"), Path("pinned.json")),
    )
    monkeypatch.setattr(
        rebuild_runtime_set, "infinity_db_main",
        lambda argv: calls.append(argv) or 0,
    )
    flags = ["--no-unit-history"] if skip_history else []
    assert rebuild_runtime_set.main(["--use-recorded-source", *flags]) == 0
    assert calls == [[
        "build", "pinned.zip", "--snapshot-manifest", "pinned.json",
        "--db-dir", str(Path("data/generated")), "--compact",
        *flags,
    ]]
    with pytest.raises(SystemExit):
        rebuild_runtime_set.main([
            "--use-recorded-source", "--manifest", "something.json",
        ])


def test_recorded_source_refuses_missing_or_changed_archives(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from hashlib import sha256

    monkeypatch.chdir(tmp_path)
    archive = Path("local/data/raw/army/recorded.zip")
    manifest = Path("local/data/manifests/snapshots/recorded.json")
    archive.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    archive.write_bytes(b"original")
    manifest.write_text("{}", encoding="utf-8")
    expected = sha256(b"original").hexdigest()
    monkeypatch.setattr(
        rebuild_runtime_set, "_metadata",
        lambda path: {rebuild_runtime_set.BUILD_PROVENANCE_KEY: {}},
    )
    monkeypatch.setattr(
        rebuild_runtime_set, "validate_build_record",
        lambda record, family: {
            "manifest": {"source": {
                "archiveName": archive.name, "archiveSha256": expected,
            }},
        },
    )
    assert rebuild_runtime_set.recorded_source_paths(Path("data/generated")) == (
        archive, manifest,
    )
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="missing or differs"):
        rebuild_runtime_set.recorded_source_paths(Path("data/generated"))
