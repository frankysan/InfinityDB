from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import (
    SNAPSHOT_MANIFEST_FORMAT,
    SNAPSHOT_MANIFEST_VERSION,
    SNAPSHOT_NOTE_FORMAT,
    SNAPSHOT_NOTE_VERSION,
    SnapshotProvenanceError,
    load_snapshot_manifest,
    portable_project_path,
    sha256_file,
    snapshot_content_sha256,
    validate_snapshot_note,
    write_snapshot_manifest,
)

ACQUIRED_AT = datetime(2026, 9, 17, 16, 20, 30, tzinfo=UTC)


def _write_archive(path: Path, body: bytes, *, member: str = "payload.bin") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    info = zipfile.ZipInfo(member, date_time=(2020, 1, 1, 0, 0, 0))
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as output:
        output.writestr(info, body)


@pytest.mark.parametrize(
    ("snapshot_type", "source_url", "language"),
    [
        ("army", "https://api.corvusbelli.com/army", "en"),
        ("wiki", "https://infinitythewiki.com/", None),
        ("symbols", "https://assets.corvusbelli.net/army/img/logo/units/", None),
    ],
)
def test_write_snapshot_manifest_for_all_snapshot_types(
    tmp_path: Path,
    snapshot_type: str,
    source_url: str,
    language: str | None,
) -> None:
    archive = tmp_path / "data" / "raw" / f"{snapshot_type}.zip"
    _write_archive(archive, f"{snapshot_type}-archive".encode())

    path = write_snapshot_manifest(
        archive,
        tmp_path / "data" / "manifests" / "snapshots",
        snapshot_type=snapshot_type,
        acquired_at=ACQUIRED_AT,
        source_url=source_url,
        document_count=3,
        project_root=tmp_path,
        language=language,
    )

    document = load_snapshot_manifest(path, archive=archive)
    assert path.name == f"{archive.stem}.json"
    assert document["format"] == SNAPSHOT_MANIFEST_FORMAT
    assert document["formatVersion"] == SNAPSHOT_MANIFEST_VERSION
    assert document["snapshot"] == {
        "acquiredAt": "2026-09-17T16:20:30+00:00",
        "archive": {
            "name": f"{snapshot_type}.zip",
            "path": f"data/raw/{snapshot_type}.zip",
            "sha256": sha256_file(archive),
        },
        "contentSha256": snapshot_content_sha256(archive),
        "documentCount": 3,
        "type": snapshot_type,
    }
    expected_source = {"url": source_url}
    if language is not None:
        expected_source["language"] = language
    assert document["source"] == expected_source

    payload = path.read_text(encoding="utf-8")
    assert payload.endswith("\n")
    assert payload == json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def test_symbol_manifest_can_bind_to_input_artifact(tmp_path: Path) -> None:
    source = tmp_path / "data" / "raw" / "JSON 20260917-120000.zip"
    archive = tmp_path / "data" / "raw" / "symbols" / "SYMBOLS 20260917-130000.zip"
    _write_archive(source, b"army")
    _write_archive(archive, b"symbols")

    path = write_snapshot_manifest(
        archive,
        tmp_path / "data" / "manifests" / "snapshots",
        snapshot_type="symbols",
        acquired_at=ACQUIRED_AT,
        source_url="https://assets.corvusbelli.net/army/img/logo/units/",
        document_count=2,
        project_root=tmp_path,
        input_artifact=source,
    )

    document = load_snapshot_manifest(path, archive=archive)
    assert document["inputArtifact"] == {
        "name": source.name,
        "path": "data/raw/JSON 20260917-120000.zip",
        "sha256": sha256_file(source),
    }


def test_manifest_load_rejects_changed_archive(tmp_path: Path) -> None:
    archive = tmp_path / "snapshot.zip"
    _write_archive(archive, b"first")
    path = write_snapshot_manifest(
        archive,
        tmp_path / "manifests",
        snapshot_type="army",
        acquired_at=ACQUIRED_AT,
        source_url="https://api.corvusbelli.com/army",
        document_count=1,
        project_root=tmp_path,
    )
    _write_archive(archive, b"changed")

    with pytest.raises(SnapshotProvenanceError, match="SHA-256 mismatch"):
        load_snapshot_manifest(path, archive=archive)


def test_manifest_archive_label_is_not_authoritative_identity(tmp_path: Path) -> None:
    archive = tmp_path / "JSON 20260917-120000.zip"
    _write_archive(archive, b"snapshot")
    path = write_snapshot_manifest(
        archive,
        tmp_path / "manifests",
        snapshot_type="army",
        acquired_at=ACQUIRED_AT,
        source_url="https://api.corvusbelli.com/army",
        document_count=1,
        project_root=tmp_path,
    )
    renamed = archive.with_name("renamed.zip")
    archive.rename(renamed)

    document = load_snapshot_manifest(path, archive=renamed)
    assert document["snapshot"]["archive"]["name"] == "JSON 20260917-120000.zip"
    assert document["snapshot"]["archive"]["sha256"] == sha256_file(renamed)


def test_manifest_is_archive_labeled_and_not_rewritten_with_different_provenance(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "snapshot.zip"
    _write_archive(archive, b"same archive")
    manifest_directory = tmp_path / "manifests"
    first = write_snapshot_manifest(
        archive,
        manifest_directory,
        snapshot_type="army",
        acquired_at=ACQUIRED_AT,
        source_url="https://api.corvusbelli.com/army",
        document_count=1,
        project_root=tmp_path,
    )

    assert (
        write_snapshot_manifest(
            archive,
            manifest_directory,
            snapshot_type="army",
            acquired_at=ACQUIRED_AT,
            source_url="https://api.corvusbelli.com/army",
            document_count=1,
            project_root=tmp_path,
        )
        == first
    )

    with pytest.raises(SnapshotProvenanceError, match="different content"):
        write_snapshot_manifest(
            archive,
            manifest_directory,
            snapshot_type="army",
            acquired_at=datetime(2026, 9, 17, 16, 21, 30, tzinfo=UTC),
            source_url="https://api.corvusbelli.com/army",
            document_count=1,
            project_root=tmp_path,
        )


def test_external_paths_are_not_persisted_as_machine_specific_paths(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.zip"
    assert portable_project_path(outside, project_root=tmp_path) is None


def test_snapshot_note_contract_binds_to_snapshot_manifest(tmp_path: Path) -> None:
    archive = tmp_path / "WIKI 20260917-120000.zip"
    _write_archive(archive, b"wiki snapshot")
    manifest_path = write_snapshot_manifest(
        archive,
        tmp_path / "manifests",
        snapshot_type="wiki",
        acquired_at=ACQUIRED_AT,
        source_url="https://infinitythewiki.com/",
        document_count=1,
        project_root=tmp_path,
    )
    snapshot_sha256 = load_snapshot_manifest(manifest_path)["snapshot"]["archive"]["sha256"]
    document = {
        "format": SNAPSHOT_NOTE_FORMAT,
        "formatVersion": SNAPSHOT_NOTE_VERSION,
        "snapshotSha256": snapshot_sha256,
        "description": "First reviewed snapshot after the September rules update.",
        "compareToSha256": "b" * 64,
        "notableChanges": ["Added one unit.", "Updated one weapon profile."],
    }

    validate_snapshot_note(document, snapshot_sha256=snapshot_sha256)

    with pytest.raises(SnapshotProvenanceError, match="references"):
        validate_snapshot_note(document, snapshot_sha256="c" * 64)


def test_snapshot_note_rejects_unknown_fields_and_self_comparison() -> None:
    document = {
        "format": SNAPSHOT_NOTE_FORMAT,
        "formatVersion": SNAPSHOT_NOTE_VERSION,
        "snapshotSha256": "a" * 64,
        "description": "Snapshot notes.",
        "compareToSha256": "a" * 64,
        "notableChanges": [],
    }
    with pytest.raises(SnapshotProvenanceError, match="different snapshot"):
        validate_snapshot_note(document)

    document.pop("compareToSha256")
    document["unexpected"] = True
    with pytest.raises(SnapshotProvenanceError, match="unknown field"):
        validate_snapshot_note(document)


def test_identical_archive_bytes_can_have_distinct_acquisition_records(tmp_path: Path) -> None:
    first_archive = tmp_path / "JSON 20260917-120000.zip"
    second_archive = tmp_path / "JSON 20260917-130000.zip"
    _write_archive(first_archive, b"same snapshot")
    _write_archive(second_archive, b"same snapshot")
    manifests = tmp_path / "manifests"

    first = write_snapshot_manifest(
        first_archive,
        manifests,
        snapshot_type="army",
        acquired_at=ACQUIRED_AT,
        source_url="https://api.corvusbelli.com/army",
        document_count=1,
        project_root=tmp_path,
    )
    second = write_snapshot_manifest(
        second_archive,
        manifests,
        snapshot_type="army",
        acquired_at=datetime(2026, 9, 17, 17, 20, 30, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        document_count=1,
        project_root=tmp_path,
    )

    assert first != second
    assert load_snapshot_manifest(first)["snapshot"]["archive"]["sha256"] == sha256_file(
        second_archive
    )
    assert load_snapshot_manifest(second)["snapshot"]["archive"]["sha256"] == sha256_file(
        first_archive
    )


def test_manifest_loader_accepts_legacy_v1_without_content_hash(tmp_path: Path) -> None:
    archive = tmp_path / "legacy.zip"
    _write_archive(archive, b"legacy")
    manifest = tmp_path / "legacy.json"
    manifest.write_text(
        json.dumps(
            {
                "format": SNAPSHOT_MANIFEST_FORMAT,
                "formatVersion": 1,
                "snapshot": {
                    "type": "army",
                    "archive": {"name": archive.name, "sha256": sha256_file(archive)},
                    "acquiredAt": "2026-09-17T16:20:30+00:00",
                    "documentCount": 1,
                },
                "source": {"url": "https://api.corvusbelli.com/army", "language": "en"},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    document = load_snapshot_manifest(manifest, archive=archive)

    assert document["formatVersion"] == 1
    assert "contentSha256" not in document["snapshot"]


def test_manifest_load_rejects_wrong_content_hash(tmp_path: Path) -> None:
    archive = tmp_path / "snapshot.zip"
    _write_archive(archive, b"snapshot")
    path = write_snapshot_manifest(
        archive,
        tmp_path / "manifests",
        snapshot_type="army",
        acquired_at=ACQUIRED_AT,
        source_url="https://api.corvusbelli.com/army",
        document_count=1,
        project_root=tmp_path,
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    document["snapshot"]["contentSha256"] = "0" * 64
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(SnapshotProvenanceError, match="content SHA-256 mismatch"):
        load_snapshot_manifest(path, archive=archive)
