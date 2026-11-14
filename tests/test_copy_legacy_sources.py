"""Focused checks for non-replacing ignored-source family copies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.data.copy_legacy_sources import candidates, copy_family, retire_family


def _army_fixture(root: Path, name: str = "JSON 20260929-114335") -> tuple[Path, Path]:
    archive = root / "data/raw" / f"{name}.zip"
    manifest = root / "data/manifests/snapshots" / f"{name}.json"
    archive.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b"immutable sample snapshot")
    manifest.write_text(json.dumps({
        "snapshot": {
            "type": "army",
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

def test_symbol_archives_copy_with_legacy_provenance_unchanged(tmp_path: Path) -> None:
    name = "SYMBOLS 20260919-131535"
    archive = tmp_path / "data/raw/symbols" / f"{name}.zip"
    manifest = tmp_path / "data/manifests/snapshots" / f"{name}.json"
    archive.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    archive.write_bytes(b"immutable raw SVG collection")
    manifest.write_text(json.dumps({
        "format": "InfinityDB snapshot provenance",
        "formatVersion": 1,
        "snapshot": {
            "type": "symbols",
            "archive": {
                "name": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            },
        },
    }), encoding="utf-8")

    assert copy_family(tmp_path, "symbols", apply=False) == (2, 0, 0)
    assert copy_family(tmp_path, "symbols", apply=True) == (2, 2, 0)
    assert copy_family(tmp_path, "symbols", apply=True) == (2, 0, 0)
    assert (
        tmp_path / "local/data/raw/symbols" / archive.name
    ).read_bytes() == archive.read_bytes()
    assert (
        tmp_path / "local/data/manifests/snapshots" / manifest.name
    ).read_bytes() == manifest.read_bytes()


def test_source_family_must_match_manifest_type(tmp_path: Path) -> None:
    archive, manifest = _army_fixture(tmp_path)
    record = json.loads(manifest.read_text(encoding="utf-8"))
    record["snapshot"]["type"] = "symbols"
    manifest.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="Archive and provenance disagree"):
        candidates(tmp_path, "army")
    assert archive.exists()
    assert not (tmp_path / "local").exists()


def test_retirement_only_removes_verified_duplicates(tmp_path: Path) -> None:
    archive, manifest = _army_fixture(tmp_path)
    copy_family(tmp_path, "army", apply=True)
    assert retire_family(tmp_path, "army", apply=False) == 2
    assert archive.exists() and manifest.exists()
    assert retire_family(tmp_path, "army", apply=True) == 2
    assert not archive.exists() and not manifest.exists()
    assert (tmp_path / "local/data/raw/army" / archive.name).is_file()
    assert (tmp_path / "local/data/manifests/snapshots" / manifest.name).is_file()


def test_retirement_fails_before_deleting_if_one_copy_differs(tmp_path: Path) -> None:
    archive, manifest = _army_fixture(tmp_path)
    copy_family(tmp_path, "army", apply=True)
    (tmp_path / "local/data/manifests/snapshots" / manifest.name).write_text(
        "mismatched", encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unverified destination"):
        retire_family(tmp_path, "army", apply=True)
    assert archive.exists() and manifest.exists()


def test_pdf_retirement_is_not_part_of_archive_cleanup(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="PDF retirement"):
        retire_family(tmp_path, "pdf", apply=True)
