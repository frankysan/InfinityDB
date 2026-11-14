"""Offline, source-pinned Army snapshot selection for explicit builds and tools.

The selected archive and manifest are independent inputs; a recorded producer
path is informational, never an instruction to find another local archive.
"""
from __future__ import annotations

import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from infinity_army_data.merge import decode_document
from infinity_army_data.source_version import latest_army_source_change_date

from .snapshot_provenance import load_snapshot_manifest


class ApiDownloadError(ValueError):
    """A selected Army source is not an accepted immutable snapshot."""


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
    """Read per-document Army source revision counts from an immutable ZIP."""
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise ApiDownloadError(f"Army snapshot must be a ZIP archive: {archive}")
    revisions: Counter[str] = Counter()
    with zipfile.ZipFile(archive) as source:
        names = [
            name for name in source.namelist()
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
    require_version_3: bool = False,
) -> ArmySnapshotResult:
    """Verify a selected Army ZIP and its exact archive-labeled provenance."""
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise ApiDownloadError(f"Army snapshot must be a ZIP archive: {archive}")

    manifest_path = (
        manifest if manifest is not None
        else manifest_directory / f"{archive.stem}.json"
    )
    if not manifest_path.is_file():
        raise ApiDownloadError(
            "Army snapshot provenance is required; expected manifest at "
            f"{manifest_path}"
        )

    document = load_snapshot_manifest(manifest_path, archive=archive)
    if require_version_3 and document["formatVersion"] != 3:
        raise ApiDownloadError("Pinned Army build requires version-3 snapshot provenance")
    snapshot = document["snapshot"]
    if snapshot["type"] != "army":
        raise ApiDownloadError(
            f"Snapshot manifest {manifest_path} describes {snapshot['type']!r}, not 'army'"
        )
    if snapshot["archive"]["name"] != archive.name or manifest_path.stem != archive.stem:
        raise ApiDownloadError(
            "Army snapshot manifest and selected ZIP must have the same archive basename"
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
            f"{manifest_changed_on!r} != {source_data_changed_on.isoformat()}"
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


def verify_pinned_army_build_source(archive: Path, manifest: Path) -> ArmySnapshotResult:
    """Require v3 provenance and the ZIP's own metadata, with no silent fallback."""
    result = resolve_army_snapshot(
        archive, manifest_directory=manifest.parent, manifest=manifest,
        expected_language="en", require_version_3=True,
    )

    with zipfile.ZipFile(archive) as source:
        metadata = source.read("metadata.json")
    sidecar = archive.with_name("metadata.json")
    if sidecar.is_symlink():
        raise ApiDownloadError(f"Ambiguous Army metadata sidecar symlink: {sidecar}")
    if sidecar.exists():
        if not sidecar.is_file() or sidecar.read_bytes() != metadata:
            raise ApiDownloadError(
                "Ambiguous Army metadata: sidecar metadata.json differs from selected ZIP"
            )
    return result
