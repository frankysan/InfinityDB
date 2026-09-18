"""Versioned acquisition state for Army symbol builds."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from infinity_db.snapshot_provenance import portable_project_path, sha256_file

SYMBOL_BUILD_FORMAT = "InfinityDB army symbol build"
SYMBOL_BUILD_VERSION = 2
REFERENCE_KINDS = frozenset({"unit-profile", "faction", "resume-audit", "static"})
SOURCE_METHODS = frozenset({"network"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class SymbolManifestError(ValueError):
    """The symbol-build manifest is invalid."""


def artifact_record(path: Path, *, project_root: Path) -> dict[str, str]:
    """Return a portable identity record for one immutable artifact."""
    record = {"name": path.name, "sha256": sha256_file(path)}
    if portable := portable_project_path(path, project_root=project_root):
        record["path"] = portable
    return record


def build_symbol_manifest(
    *,
    army_artifact: Path,
    symbol_artifact: Path,
    acquired_at: datetime,
    army_acquired_at: datetime,
    army_language: str,
    army_source_url: str,
    source_document_count: int,
    source_revisions: dict[str, int],
    assets: list[dict[str, Any]],
    references: list[dict[str, Any]],
    audit: dict[str, int],
    project_root: Path,
) -> dict[str, Any]:
    """Build and validate the acquisition-only version-2 symbol manifest."""
    document = {
        "format": SYMBOL_BUILD_FORMAT,
        "formatVersion": SYMBOL_BUILD_VERSION,
        "snapshot": {
            "armyArtifact": artifact_record(army_artifact, project_root=project_root),
            "armySource": {
                "acquiredAt": army_acquired_at.isoformat(timespec="seconds"),
                "language": army_language,
                "url": army_source_url,
                "documentCount": source_document_count,
                "sourceRevisions": dict(sorted(source_revisions.items())),
            },
            "symbolArtifact": artifact_record(symbol_artifact, project_root=project_root),
            "acquiredAt": acquired_at.isoformat(timespec="seconds"),
        },
        "assets": sorted(assets, key=lambda item: item["url"]),
        "references": sorted(
            references,
            key=lambda item: (
                item["sourceDocument"],
                item["jsonPath"],
                item["kind"],
                item["assetUrl"],
            ),
        ),
        "audit": dict(sorted(audit.items())),
    }
    validate_symbol_manifest(document)
    return document


def write_symbol_manifest(document: dict[str, Any], path: Path) -> Path:
    """Atomically replace the generated current symbol-build manifest."""
    validate_symbol_manifest(document)
    payload = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return path


def load_symbol_manifest(path: Path) -> dict[str, Any]:
    """Load and validate one generated symbol-build manifest."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SymbolManifestError(f"Could not load symbol manifest {path}: {exc}") from exc
    validate_symbol_manifest(document)
    return document


def validate_symbol_manifest(document: Any) -> None:
    """Validate the acquisition-only version-2 symbol-build contract."""
    root = _object(document, "symbol manifest")
    _only_keys(
        root,
        {"format", "formatVersion", "snapshot", "assets", "references", "audit"},
        "symbol manifest",
    )
    if root.get("format") != SYMBOL_BUILD_FORMAT:
        raise SymbolManifestError(f"symbol manifest.format must be {SYMBOL_BUILD_FORMAT!r}")
    if root.get("formatVersion") != SYMBOL_BUILD_VERSION:
        raise SymbolManifestError(
            f"symbol manifest.formatVersion must be {SYMBOL_BUILD_VERSION}"
        )

    snapshot = _object(root.get("snapshot"), "symbol manifest.snapshot")
    _only_keys(
        snapshot,
        {"armyArtifact", "armySource", "symbolArtifact", "acquiredAt"},
        "symbol manifest.snapshot",
    )
    _artifact(snapshot.get("armyArtifact"), "symbol manifest.snapshot.armyArtifact")
    _artifact(snapshot.get("symbolArtifact"), "symbol manifest.snapshot.symbolArtifact")
    _aware_datetime(snapshot.get("acquiredAt"), "symbol manifest.snapshot.acquiredAt")
    _army_source(snapshot.get("armySource"), "symbol manifest.snapshot.armySource")

    assets = root.get("assets")
    if not isinstance(assets, list):
        raise SymbolManifestError("symbol manifest.assets must be an array")
    asset_urls: set[str] = set()
    archive_paths: set[str] = set()
    for index, asset in enumerate(assets):
        context = f"symbol manifest.assets[{index}]"
        row = _object(asset, context)
        _only_keys(
            row,
            {"url", "sourceFilename", "archivePath", "sha256", "sourceMethod"},
            context,
        )
        url = _string(row.get("url"), f"{context}.url")
        if url in asset_urls:
            raise SymbolManifestError(f"{context}.url is duplicated: {url}")
        asset_urls.add(url)
        _string(row.get("sourceFilename"), f"{context}.sourceFilename")
        archive_path = _portable_path(row.get("archivePath"), f"{context}.archivePath")
        if archive_path in archive_paths:
            raise SymbolManifestError(
                f"{context}.archivePath is duplicated: {archive_path}"
            )
        archive_paths.add(archive_path)
        _sha256(row.get("sha256"), f"{context}.sha256")
        method = _string(row.get("sourceMethod"), f"{context}.sourceMethod")
        if method not in SOURCE_METHODS:
            raise SymbolManifestError(
                f"{context}.sourceMethod must be one of: {', '.join(sorted(SOURCE_METHODS))}"
            )

    references = root.get("references")
    if not isinstance(references, list):
        raise SymbolManifestError("symbol manifest.references must be an array")
    for index, reference in enumerate(references):
        context = f"symbol manifest.references[{index}]"
        row = _object(reference, context)
        allowed = {
            "kind",
            "authoritative",
            "sourceDocument",
            "jsonPath",
            "assetUrl",
            "armyId",
            "armySlug",
            "unitId",
            "unitSlug",
            "profileName",
            "factionId",
            "factionSlug",
            "staticKey",
            "staticCategory",
            "label",
        }
        _only_keys(row, allowed, context)
        kind = _string(row.get("kind"), f"{context}.kind")
        if kind not in REFERENCE_KINDS:
            raise SymbolManifestError(
                f"{context}.kind must be one of: {', '.join(sorted(REFERENCE_KINDS))}"
            )
        if type(row.get("authoritative")) is not bool:
            raise SymbolManifestError(f"{context}.authoritative must be boolean")
        _string(row.get("sourceDocument"), f"{context}.sourceDocument")
        _string(row.get("jsonPath"), f"{context}.jsonPath")
        asset_url = _string(row.get("assetUrl"), f"{context}.assetUrl")
        if row["authoritative"] and asset_url not in asset_urls:
            raise SymbolManifestError(
                f"{context}.assetUrl does not identify a downloaded asset: {asset_url}"
            )
        for field in ("armyId", "unitId", "factionId"):
            if field in row and type(row[field]) is not int:
                raise SymbolManifestError(f"{context}.{field} must be an integer")
        for field in (
            "armySlug",
            "unitSlug",
            "profileName",
            "factionSlug",
            "staticKey",
            "staticCategory",
            "label",
        ):
            if field in row:
                _string(row[field], f"{context}.{field}")

    audit = _object(root.get("audit"), "symbol manifest.audit")
    required_audit = {
        "unitProfileReferenceCount",
        "uniqueUnitUrlCount",
        "factionReferenceCount",
        "uniqueFactionUrlCount",
        "semanticReferenceCount",
        "uniqueSemanticUrlCount",
        "resumeReferenceCount",
        "uniqueResumeUrlCount",
        "staticReferenceCount",
        "recursiveReferenceCount",
        "uniqueRecursiveUrlCount",
        "uniqueDownloadedUrlCount",
        "unknownReferenceCount",
    }
    _only_keys(audit, required_audit, "symbol manifest.audit")
    missing = required_audit - set(audit)
    if missing:
        raise SymbolManifestError(
            "symbol manifest.audit is missing field(s): " + ", ".join(sorted(missing))
        )
    for field in sorted(required_audit):
        value = audit[field]
        if type(value) is not int or value < 0:
            raise SymbolManifestError(
                f"symbol manifest.audit.{field} must be a non-negative integer"
            )
    if audit["uniqueDownloadedUrlCount"] != len(asset_urls):
        raise SymbolManifestError(
            "symbol manifest.audit.uniqueDownloadedUrlCount must equal the asset count"
        )
    if audit["unknownReferenceCount"] != 0:
        raise SymbolManifestError(
            "symbol manifest.audit.unknownReferenceCount must be zero for a published manifest"
        )



def _army_source(value: Any, context: str) -> None:
    record = _object(value, context)
    _only_keys(
        record,
        {"acquiredAt", "language", "url", "documentCount", "sourceRevisions"},
        context,
    )
    _aware_datetime(record.get("acquiredAt"), f"{context}.acquiredAt")
    _string(record.get("language"), f"{context}.language")
    _string(record.get("url"), f"{context}.url")

    document_count = record.get("documentCount")
    if type(document_count) is not int or document_count < 1:
        raise SymbolManifestError(f"{context}.documentCount must be a positive integer")

    revisions = _object(record.get("sourceRevisions"), f"{context}.sourceRevisions")
    revision_documents = 0
    for version, count in revisions.items():
        _string(version, f"{context}.sourceRevisions key")
        if type(count) is not int or count < 1:
            raise SymbolManifestError(
                f"{context}.sourceRevisions[{version!r}] must be a positive integer"
            )
        revision_documents += count
    if revision_documents + 1 != document_count:
        raise SymbolManifestError(
            f"{context}.sourceRevisions must account for every non-metadata Army document"
        )


def _aware_datetime(value: Any, context: str) -> datetime:
    text = _string(value, context)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SymbolManifestError(f"{context} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SymbolManifestError(f"{context} must include a timezone offset")
    return parsed


def _artifact(value: Any, context: str) -> None:
    record = _object(value, context)
    _only_keys(record, {"name", "path", "sha256"}, context)
    _string(record.get("name"), f"{context}.name")
    _sha256(record.get("sha256"), f"{context}.sha256")
    if "path" in record:
        _portable_path(record["path"], f"{context}.path")


def _portable_path(value: Any, context: str) -> str:
    text = _string(value, context)
    path = PurePosixPath(text)
    if "\\" in text or path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:/", text):
        raise SymbolManifestError(f"{context} must be a portable relative POSIX path")
    return text


def _sha256(value: Any, context: str) -> str:
    text = _string(value, context)
    if not _SHA256_RE.fullmatch(text):
        raise SymbolManifestError(f"{context} must be a lowercase SHA-256 digest")
    return text


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SymbolManifestError(f"{context} must be a non-empty string")
    return value


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SymbolManifestError(f"{context} must be an object")
    return value


def _only_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise SymbolManifestError(
            f"{context} has unknown field(s): {', '.join(sorted(unknown))}"
        )
