"""Offline Army snapshot verification independent of the network downloader."""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from infinity_db.army_snapshot_source import verify_pinned_army_build_source
from infinity_db.snapshot_provenance import SnapshotProvenanceError, write_snapshot_manifest
from tools.army_snapshot_source import (
    ApiDownloadError,
    resolve_army_snapshot,
    snapshot_source_revision_counts,
)


def _snapshot(
    tmp_path: Path,
    *,
    revision: str = "7.26246.158",
    document_count: int = 2,
    include_metadata: bool = True,
    changed_on: date = date(2026, 9, 3),
) -> tuple[Path, Path]:
    archive = tmp_path / "JSON 20260917-120000.zip"
    with zipfile.ZipFile(archive, "w") as result:
        if include_metadata:
            result.writestr("metadata.json", json.dumps({"factions": []}))
        result.writestr(
            "101-panoceania.json",
            json.dumps({"version": revision, "units": []}),
        )
    manifest = write_snapshot_manifest(
        archive,
        tmp_path / "manifests",
        snapshot_type="army",
        acquired_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        language="en",
        source_data_changed_on=changed_on,
        document_count=document_count,
        project_root=tmp_path,
    )
    return archive, manifest


@pytest.mark.parametrize("destination", ("data/raw", "local/data/raw/army"))
def test_explicit_pinned_source_accepts_both_layouts_without_manifest_rewrite(
    tmp_path: Path, destination: str,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    selected = tmp_path / destination / archive.name
    selected.parent.mkdir(parents=True)
    shutil.copyfile(archive, selected)
    assert verify_pinned_army_build_source(selected, manifest).archive == selected
    assert not list((tmp_path / destination).glob("metadata.json"))


def test_explicit_pinned_source_accepts_identical_metadata_sidecar(
    tmp_path: Path,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    with zipfile.ZipFile(archive) as source:
        archive.with_name("metadata.json").write_bytes(source.read("metadata.json"))
    assert verify_pinned_army_build_source(archive, manifest).manifest == manifest


def test_explicit_pinned_source_rejects_divergent_metadata_sidecar(
    tmp_path: Path,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    archive.with_name("metadata.json").write_text(
        '{"factions":[{"id":50,"name":"Other"}]}', encoding="utf-8",
    )
    with pytest.raises(ApiDownloadError, match="Ambiguous Army metadata"):
        verify_pinned_army_build_source(archive, manifest)


def test_explicit_pinned_source_rejects_sidecar_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    sidecar = archive.with_name("metadata.json")
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink",
        lambda path: path == sidecar or original_is_symlink(path),
    )
    with pytest.raises(ApiDownloadError, match="symlink"):
        verify_pinned_army_build_source(archive, manifest)


def test_explicit_pinned_source_rejects_archive_or_manifest_renaming(
    tmp_path: Path,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    alternative = tmp_path / "JSON 20260918-120000.zip"
    shutil.copyfile(archive, alternative)
    with pytest.raises(ApiDownloadError, match="same archive basename"):
        verify_pinned_army_build_source(alternative, manifest)


def test_explicit_pinned_source_rejects_missing_manifest(
    tmp_path: Path,
) -> None:
    archive, _ = _snapshot(tmp_path)
    with pytest.raises(ApiDownloadError, match="provenance is required"):
        verify_pinned_army_build_source(archive, tmp_path / "missing.json")


def test_explicit_pinned_source_rejects_missing_snapshot_member(
    tmp_path: Path,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("unexpected.json", "{}")
    with pytest.raises(SnapshotProvenanceError, match="SHA-256 mismatch"):
        verify_pinned_army_build_source(archive, manifest)



def test_explicit_pinned_build_requires_v3_not_legacy_provenance(
    tmp_path: Path,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["formatVersion"] = 2
    document["source"].pop("dataChangedOn")
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ApiDownloadError, match="version-3"):
        verify_pinned_army_build_source(archive, manifest)


def test_explicit_pinned_build_rejects_non_english_army_manifest(
    tmp_path: Path,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["source"]["language"] = "es"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ApiDownloadError, match="expected 'en'"):
        verify_pinned_army_build_source(archive, manifest)


def test_explicit_pinned_build_rejects_manifest_recorded_archive_name(
    tmp_path: Path,
) -> None:
    archive, manifest = _snapshot(tmp_path)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["snapshot"]["archive"]["name"] = "different.zip"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ApiDownloadError, match="same archive basename"):
        verify_pinned_army_build_source(archive, manifest)

def test_offline_army_reader_accepts_pinned_snapshot(tmp_path: Path) -> None:
    archive, manifest = _snapshot(tmp_path)
    assert snapshot_source_revision_counts(archive) == {"7.26246.158": 1}
    result = resolve_army_snapshot(
        archive, manifest_directory=manifest.parent, expected_language="en",
    )
    assert (result.archive, result.manifest) == (archive, manifest)
    assert result.source_revisions == {"7.26246.158": 1}
    assert result.document_count == 2
    assert result.acquired_at == datetime(2026, 9, 17, 12, 0, tzinfo=UTC)


def test_offline_army_reader_checks_manifest_document_count(tmp_path: Path) -> None:
    archive, manifest = _snapshot(tmp_path, document_count=3)
    with pytest.raises(ApiDownloadError, match="documentCount does not match"):
        resolve_army_snapshot(archive, manifest_directory=manifest.parent)


def test_offline_army_reader_rejects_unknown_revision(tmp_path: Path) -> None:
    archive, manifest = _snapshot(tmp_path, revision="unknown")
    with pytest.raises(ApiDownloadError, match="supported encoded date"):
        resolve_army_snapshot(archive, manifest_directory=manifest.parent)


def test_offline_army_reader_checks_revision_date(tmp_path: Path) -> None:
    archive, manifest = _snapshot(tmp_path, changed_on=date(2026, 9, 4))
    with pytest.raises(ApiDownloadError, match="dataChangedOn does not match"):
        resolve_army_snapshot(archive, manifest_directory=manifest.parent)


def test_offline_army_reader_requires_metadata(tmp_path: Path) -> None:
    archive, _ = _snapshot(tmp_path, include_metadata=False)
    with pytest.raises(ApiDownloadError, match="missing metadata.json"):
        snapshot_source_revision_counts(archive)


def test_offline_army_reader_rejects_archive_mutation(tmp_path: Path) -> None:
    archive, manifest = _snapshot(tmp_path)
    with zipfile.ZipFile(archive, "a") as result:
        result.writestr("changed.txt", "source bytes were modified")
    with pytest.raises(SnapshotProvenanceError, match="SHA-256 mismatch"):
        resolve_army_snapshot(archive, manifest_directory=manifest.parent)


