"""Read-only verification of immutable Army ZIP snapshots for local tooling.

The archive resolver belongs to InfinityDB's offline consumer, not to
the optional network-acquisition producer.
"""

from __future__ import annotations

import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from infinity_army_data.merge import decode_document
from infinity_army_data.source_version import latest_army_source_change_date
from infinity_db.snapshot_provenance import load_snapshot_manifest


class ApiDownloadError(ValueError):
    """The Army API returned data that cannot be saved as an input snapshot."""


class ArmySnapshotResult(NamedTuple):
    """Identity and observed source revisions for one published Army snapshot."""

    archive: Path
    manifest: Path
    acquired_at: datetime
    language: str
    source_url: str
    document_count: int
    source_revisions: dict[str, int]


def snapshot_source_revision_counts(archive: Path) -> dict[str, int]:
    """Read per-document Army source revision counts from one immutable ZIP snapshot."""
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise ApiDownloadError(f"Army snapshot must be a ZIP archive: {archive}")
    revisions: Counter[str] = Counter()
    with zipfile.ZipFile(archive) as source:
        names = [
            name
            for name in source.namelist()
            if not name.endswith("/") and name.lower().endswith(".json")
        ]
        if "metadata.json" not in names:
            raise ApiDownloadError("Army snapshot is missing metadata.json")
        for name in sorted(names):
            if name == "metadata.json":
                continue
            try:
                document = decode_document(source.read(name), name)
            except ValueError as exc:
                raise ApiDownloadError(f"Invalid Army source document {name}: {exc}") from exc
            revisions[str(document.get("version"))] += 1
    return dict(sorted(revisions.items()))



def resolve_army_snapshot(
    archive: Path,
    *,
    manifest_directory: Path,
    manifest: Path | None = None,
    expected_language: str | None = None,
) -> ArmySnapshotResult:
    """Verify one immutable Army ZIP and resolve its generated acquisition provenance."""
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise ApiDownloadError(f"Army snapshot must be a ZIP archive: {archive}")

    manifest_path = manifest or manifest_directory / f"{archive.stem}.json"
    if not manifest_path.is_file():
        raise ApiDownloadError(
            "Army snapshot provenance is required; expected manifest at "
            f"{manifest_path}"
        )

    document = load_snapshot_manifest(manifest_path, archive=archive)
    snapshot = document["snapshot"]
    if snapshot["type"] != "army":
        raise ApiDownloadError(
            f"Snapshot manifest {manifest_path} describes {snapshot['type']!r}, not 'army'"
        )

    source = document["source"]
    language = source.get("language")
    if not isinstance(language, str) or not language:
        raise ApiDownloadError(f"Army snapshot manifest {manifest_path} has no source language")
    if expected_language is not None and language != expected_language:
        raise ApiDownloadError(
            f"Army snapshot language is {language!r}, expected {expected_language!r}"
        )

    revisions = snapshot_source_revision_counts(archive)
    source_data_changed_on = latest_army_source_change_date(revisions)
    if source_data_changed_on is None:
        raise ApiDownloadError(
            "Army source revisions do not use the supported encoded date format"
        )
    manifest_changed_on = source.get("dataChangedOn")
    if (
        manifest_changed_on is not None
        and manifest_changed_on != source_data_changed_on.isoformat()
    ):
        raise ApiDownloadError(
            "Army snapshot source.dataChangedOn does not match source revisions: "
            f"{manifest_changed_on!r} != {source_data_changed_on.isoformat()!r}"
        )
    expected_documents = sum(revisions.values()) + 1
    if snapshot["documentCount"] != expected_documents:
        raise ApiDownloadError(
            "Army snapshot provenance documentCount does not match archive contents: "
            f"{snapshot['documentCount']} != {expected_documents}"
        )

    return ArmySnapshotResult(
        archive=archive,
        manifest=manifest_path,
        acquired_at=datetime.fromisoformat(snapshot["acquiredAt"]),
        language=language,
        source_url=source["url"],
        document_count=snapshot["documentCount"],
        source_revisions=revisions,
    )
