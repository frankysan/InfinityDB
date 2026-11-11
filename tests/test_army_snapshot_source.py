"""Offline Army snapshot verification independent of the network downloader."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

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


def test_downloader_preserves_offline_reader_imports() -> None:
    from tools import download_army_json

    assert download_army_json.resolve_army_snapshot is resolve_army_snapshot
    assert download_army_json.snapshot_source_revision_counts is snapshot_source_revision_counts
    assert download_army_json.ApiDownloadError is ApiDownloadError
