"""Focused checks for non-replacing ignored-source family copies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.data.copy_legacy_sources import candidates, copy_family


def _army_fixture(root: Path, name: str = "JSON 20260929-114335") -> tuple[Path, Path]:
    archive = root / "data/raw" / f"{name}.zip"
    manifest = root / "data/manifests/snapshots" / f"{name}.json"
    archive.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b"immutable sample snapshot")
    manifest.write_text(json.dumps({
        "snapshot": {
            "archive": {
                "name": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            },
        },
    }), encoding="utf-8")
    return archive, manifest


def test_army_copy_retains_source_and_matching_provenance(tmp_path: Path) -> None:
    archive, manifest = _army_fixture(tmp_path)
    assert copy_family(tmp_path, "army", apply=False) == (2, 0, 0)
    assert not (tmp_path / "local").exists()
    assert copy_family(tmp_path, "army", apply=True) == (2, 2, 0)
    assert copy_family(tmp_path, "army", apply=True) == (2, 0, 0)
    assert (tmp_path / "local/data/raw/army" / archive.name).read_bytes() == archive.read_bytes()
    assert (
        tmp_path / "local/data/manifests/snapshots" / manifest.name
    ).read_bytes() == manifest.read_bytes()


def test_conflict_refused_before_any_copies(tmp_path: Path) -> None:
    _army_fixture(tmp_path)
    destination = tmp_path / "local/data/raw/army/JSON 20260929-114335.zip"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"do not replace")
    with pytest.raises(ValueError, match="Conflicting destination"):
        copy_family(tmp_path, "army", apply=True)
    assert destination.read_bytes() == b"do not replace"
    assert not (tmp_path / "local/data/manifests").exists()


def test_wrong_archive_sha_refused(tmp_path: Path) -> None:
    _, manifest = _army_fixture(tmp_path)
    record = json.loads(manifest.read_text(encoding="utf-8"))
    record["snapshot"]["archive"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="Archive and provenance disagree"):
        candidates(tmp_path, "army")
    assert not (tmp_path / "local").exists()


def test_unpaired_legacy_archive_is_copied_without_fake_manifest(tmp_path: Path) -> None:
    archive = tmp_path / "data/raw/JSON 20260910-204106.zip"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"early snapshot")
    assert copy_family(tmp_path, "army", apply=True) == (1, 1, 1)
    assert (tmp_path / "local/data/raw/army" / archive.name).read_bytes() == archive.read_bytes()


def test_pdf_family_keeps_nested_paths_without_other_files(tmp_path: Path) -> None:
    folder = tmp_path / "data/pdf/legacy/mission-pack"
    folder.mkdir(parents=True)
    (folder / "mission.pdf").write_bytes(b"pdf bytes")
    (folder / "desktop.ini").write_text("ignored", encoding="utf-8")
    assert copy_family(tmp_path, "pdf", apply=True) == (1, 1, 0)
    assert (
        tmp_path / "local/data/pdf/legacy/mission-pack/mission.pdf"
    ).read_bytes() == b"pdf bytes"
    assert not (tmp_path / "local/data/pdf/legacy/mission-pack/desktop.ini").exists()
