"""Portable source-pair import from independent acquisition producers."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import build_snapshot_manifest
from tools.data.import_acquisition_snapshot import import_snapshot


def _pair(tmp_path: Path, family: str) -> tuple[Path, Path, Path]:
    root = tmp_path / "InfinityDB"
    root.mkdir()
    producer_name = (
        "InfinityDB-army-acquisition" if family == "army"
        else "InfinityDB-wiki-acquisition"
    )
    name = (
        "JSON 20260929-114335" if family == "army"
        else "WIKI-en 20260929-114335"
    )
    producer = tmp_path / producer_name
    family_dir = "raw/army" if family == "army" else "wiki"
    archive = producer / "local/data" / family_dir / f"{name}.zip"
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("source.txt", "immutable acquisition")
    manifest_path = producer / "local/data/manifests/snapshots" / f"{name}.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = build_snapshot_manifest(
        archive,
        snapshot_type=family,
        acquired_at=datetime(2026, 9, 29, tzinfo=UTC),
        source_url="https://example.test/source",
        document_count=1, project_root=producer, language="en",
        source_data_changed_on=date(2026, 9, 3) if family == "army" else None,
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return root, archive, manifest_path


@pytest.mark.parametrize("family", ["army", "wiki"])
def test_copy_pair_preserves_bytes_and_is_idempotent(tmp_path: Path, family: str) -> None:
    root, archive, manifest = _pair(tmp_path, family)
    name = archive.stem
    output_archive = root / "local/data" / (
        "raw/army" if family == "army" else "wiki"
    ) / archive.name
    output_manifest = root / "local/data/manifests/snapshots" / manifest.name

    assert "would copy 2" in import_snapshot(root, family, name, apply=False)
    assert not (root / "local").exists()
    assert "copied 2" in import_snapshot(root, family, name, apply=True)
    assert output_archive.read_bytes() == archive.read_bytes()
    assert output_manifest.read_bytes() == manifest.read_bytes()
    assert "copied 0" in import_snapshot(root, family, name, apply=True)


def test_conflicting_copy_refused_without_changing_sources(tmp_path: Path) -> None:
    root, archive, manifest = _pair(tmp_path, "army")
    destination = root / "local/data/raw/army" / archive.name
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing other bytes")
    with pytest.raises(ValueError, match="conflicts"):
        import_snapshot(root, "army", archive.stem, apply=True)
    assert destination.read_bytes() == b"existing other bytes"
    assert not (root / "local/data/manifests").exists()
    assert archive.is_file() and manifest.is_file()


def test_invalid_manifest_and_unsafe_names_refused(tmp_path: Path) -> None:
    root, archive, manifest = _pair(tmp_path, "wiki")
    for name in ("../WIKI-en", "WIKI-en/no", "JSON 20260929-114335"):
        with pytest.raises(ValueError):
            import_snapshot(root, "wiki", name, apply=True)
    record = json.loads(manifest.read_text(encoding="utf-8"))
    record["snapshot"]["archive"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        import_snapshot(root, "wiki", archive.stem, apply=True)
    assert not (root / "local").exists()
