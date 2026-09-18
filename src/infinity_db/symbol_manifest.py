"""Versioned generated state for Army symbol builds."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from infinity_db.snapshot_provenance import portable_project_path, sha256_file

SYMBOL_BUILD_FORMAT = "InfinityDB army symbol build"
SYMBOL_BUILD_ACQUISITION_VERSION = 2
SYMBOL_BUILD_PREFLIGHT_VERSION = 3
SYMBOL_BUILD_FONT_AUDIT_VERSION = 4
SYMBOL_BUILD_DUPLICATE_VERSION = 5
SYMBOL_BUILD_TEXT_CONVERSION_VERSION = 6
SYMBOL_BUILD_COMPRESSION_VERSION = 7
SYMBOL_BUILD_VERSION = 8
REFERENCE_KINDS = frozenset({"unit-profile", "faction", "resume-audit", "static"})
SOURCE_METHODS = frozenset({"override", "cache", "network"})
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
    """Build and validate acquisition-only version-2 symbol state."""
    document = {
        "format": SYMBOL_BUILD_FORMAT,
        "formatVersion": SYMBOL_BUILD_ACQUISITION_VERSION,
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


def add_svg_preflight(
    document: dict[str, Any],
    *,
    status: str,
    summary: dict[str, int],
    report: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Promote acquisition state to version 3 with deterministic SVG preflight state."""
    validate_symbol_manifest(document)
    if status not in {"passed", "failed"}:
        raise SymbolManifestError("SVG preflight status must be 'passed' or 'failed'")
    promoted = json.loads(json.dumps(document))
    promoted["formatVersion"] = SYMBOL_BUILD_PREFLIGHT_VERSION
    promoted["processing"] = {
        "svgPreflight": {
            "status": status,
            "summary": dict(sorted(summary.items())),
            "report": artifact_record(report, project_root=project_root),
        }
    }
    validate_symbol_manifest(promoted)
    return promoted


def add_font_audit(
    document: dict[str, Any],
    *,
    status: str,
    summary: dict[str, int],
    report: Path,
    aliases: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Promote preflight state to version 4 with installed-font audit state."""
    validate_symbol_manifest(document)
    if document.get("formatVersion") != SYMBOL_BUILD_PREFLIGHT_VERSION:
        raise SymbolManifestError(
            f"Font audit requires version-{SYMBOL_BUILD_PREFLIGHT_VERSION} SVG preflight state"
        )
    if status not in {"passed", "failed"}:
        raise SymbolManifestError("Font audit status must be 'passed' or 'failed'")
    promoted = json.loads(json.dumps(document))
    promoted["formatVersion"] = SYMBOL_BUILD_FONT_AUDIT_VERSION
    promoted["processing"]["fontAudit"] = {
        "status": status,
        "summary": dict(sorted(summary.items())),
        "report": artifact_record(report, project_root=project_root),
        "aliases": artifact_record(aliases, project_root=project_root),
    }
    validate_symbol_manifest(promoted)
    return promoted


def add_duplicate_detection(
    document: dict[str, Any],
    *,
    summary: dict[str, int],
    canonical_by_archive_path: dict[str, str],
    groups_report: Path,
    errors_report: Path,
    summary_report: Path,
    renderer: str,
    renderer_version: str,
    render_size: int,
    jobs: int,
    project_root: Path,
) -> dict[str, Any]:
    """Promote font-audited state to version 5 with duplicate/canonical state."""
    validate_symbol_manifest(document)
    if document.get("formatVersion") != SYMBOL_BUILD_FONT_AUDIT_VERSION:
        raise SymbolManifestError(
            "Duplicate detection requires version-"
            f"{SYMBOL_BUILD_FONT_AUDIT_VERSION} font-audited state"
        )
    if document["processing"]["fontAudit"]["status"] != "passed":
        raise SymbolManifestError("Duplicate detection requires a passed font audit")
    if render_size < 1:
        raise SymbolManifestError("Duplicate render size must be at least 1")
    if jobs < 1:
        raise SymbolManifestError("Duplicate render jobs must be at least 1")

    renderer_record: dict[str, Any] = {
        "name": renderer,
        "renderSize": render_size,
        "jobs": jobs,
    }
    if renderer_version:
        renderer_record["version"] = renderer_version

    promoted = json.loads(json.dumps(document))
    promoted["formatVersion"] = SYMBOL_BUILD_DUPLICATE_VERSION
    promoted["processing"]["duplicateDetection"] = {
        "status": "passed",
        "summary": dict(sorted(summary.items())),
        "renderer": renderer_record,
        "canonicalByArchivePath": dict(sorted(canonical_by_archive_path.items())),
        "groupsReport": artifact_record(groups_report, project_root=project_root),
        "errorsReport": artifact_record(errors_report, project_root=project_root),
        "summaryReport": artifact_record(summary_report, project_root=project_root),
    }
    validate_symbol_manifest(promoted)
    return promoted


def add_text_conversion(
    document: dict[str, Any],
    *,
    status: str,
    summary: dict[str, int],
    report: Path,
    summary_report: Path,
    converter: str,
    converter_version: str,
    jobs: int,
    project_root: Path,
) -> dict[str, Any]:
    """Promote duplicate-detected state to version 6 with text conversion state."""
    validate_symbol_manifest(document)
    if document.get("formatVersion") not in {
        SYMBOL_BUILD_DUPLICATE_VERSION,
        SYMBOL_BUILD_TEXT_CONVERSION_VERSION,
        SYMBOL_BUILD_COMPRESSION_VERSION,
        SYMBOL_BUILD_VERSION,
    }:
        raise SymbolManifestError(
            "Text conversion requires version-"
            f"{SYMBOL_BUILD_DUPLICATE_VERSION}, version-"
            f"{SYMBOL_BUILD_TEXT_CONVERSION_VERSION}, or version-{SYMBOL_BUILD_VERSION} "
            "duplicate-detected state"
        )
    if document["processing"]["duplicateDetection"]["status"] != "passed":
        raise SymbolManifestError("Text conversion requires passed duplicate detection")
    if status not in {"passed", "failed"}:
        raise SymbolManifestError("Text conversion status must be 'passed' or 'failed'")
    if jobs < 1:
        raise SymbolManifestError("Text conversion jobs must be at least 1")

    converter_record: dict[str, Any] = {"name": converter, "jobs": jobs}
    if converter_version:
        converter_record["version"] = converter_version

    promoted = json.loads(json.dumps(document))
    promoted["formatVersion"] = SYMBOL_BUILD_TEXT_CONVERSION_VERSION
    promoted["processing"].pop("compression", None)
    promoted["processing"].pop("publication", None)
    promoted["processing"]["textConversion"] = {
        "status": status,
        "summary": dict(sorted(summary.items())),
        "converter": converter_record,
        "report": artifact_record(report, project_root=project_root),
        "summaryReport": artifact_record(summary_report, project_root=project_root),
    }
    validate_symbol_manifest(promoted)
    return promoted


def add_compression(
    document: dict[str, Any],
    *,
    status: str,
    summary: dict[str, int],
    report: Path,
    candidates_report: Path,
    run_report: Path,
    profile: str,
    renderer: str,
    target_sizes: list[int],
    dprs: list[float],
    balanced_precisions: list[int],
    max_rms: float,
    max_changed_fraction: float,
    pixel_diff_threshold: int,
    jobs: int,
    project_root: Path,
) -> dict[str, Any]:
    """Promote text-converted state to version 7 with compression state."""
    validate_symbol_manifest(document)
    if document.get("formatVersion") not in {
        SYMBOL_BUILD_TEXT_CONVERSION_VERSION,
        SYMBOL_BUILD_COMPRESSION_VERSION,
        SYMBOL_BUILD_VERSION,
    }:
        raise SymbolManifestError(
            "Compression requires version-"
            f"{SYMBOL_BUILD_TEXT_CONVERSION_VERSION}, version-"
            f"{SYMBOL_BUILD_COMPRESSION_VERSION}, or version-{SYMBOL_BUILD_VERSION} "
            "text-converted state"
        )
    if document["processing"]["textConversion"]["status"] != "passed":
        raise SymbolManifestError("Compression requires passed text conversion")
    if status != "passed":
        raise SymbolManifestError("Compression status must be 'passed'")
    if jobs < 1:
        raise SymbolManifestError("Compression jobs must be at least 1")

    promoted = json.loads(json.dumps(document))
    promoted["formatVersion"] = SYMBOL_BUILD_COMPRESSION_VERSION
    promoted["processing"].pop("publication", None)
    promoted["processing"]["compression"] = {
        "status": status,
        "summary": dict(sorted(summary.items())),
        "profile": profile,
        "settings": {
            "renderer": renderer,
            "targetSizesCssPx": list(target_sizes),
            "dprs": list(dprs),
            "balancedPrecisions": list(balanced_precisions),
            "maxRms": max_rms,
            "maxChangedFraction": max_changed_fraction,
            "pixelDiffThreshold": pixel_diff_threshold,
            "jobs": jobs,
        },
        "report": artifact_record(report, project_root=project_root),
        "candidatesReport": artifact_record(
            candidates_report, project_root=project_root
        ),
        "runReport": artifact_record(run_report, project_root=project_root),
    }
    validate_symbol_manifest(promoted)
    return promoted


def add_publication(
    document: dict[str, Any],
    *,
    summary: dict[str, int],
    mapping_report: Path,
    army_map: Path,
    unit_map: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Promote compressed version-7 state to version 8 publication state."""
    validate_symbol_manifest(document)
    if document.get("formatVersion") not in {
        SYMBOL_BUILD_COMPRESSION_VERSION,
        SYMBOL_BUILD_VERSION,
    }:
        raise SymbolManifestError(
            "Publication requires version-"
            f"{SYMBOL_BUILD_COMPRESSION_VERSION} compressed state"
        )
    if document["processing"]["compression"]["status"] != "passed":
        raise SymbolManifestError("Publication requires passed compression")

    promoted = json.loads(json.dumps(document))
    promoted["formatVersion"] = SYMBOL_BUILD_VERSION
    promoted["processing"]["publication"] = {
        "status": "passed",
        "summary": dict(sorted(summary.items())),
        "mappingReport": artifact_record(mapping_report, project_root=project_root),
        "armyMap": artifact_record(army_map, project_root=project_root),
        "unitMap": artifact_record(unit_map, project_root=project_root),
    }
    validate_symbol_manifest(promoted)
    return promoted

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
    """Validate acquisition v2 through published v8 symbol state."""
    root = _object(document, "symbol manifest")
    version = root.get("formatVersion")
    supported_versions = {
        SYMBOL_BUILD_ACQUISITION_VERSION,
        SYMBOL_BUILD_PREFLIGHT_VERSION,
        SYMBOL_BUILD_FONT_AUDIT_VERSION,
        SYMBOL_BUILD_DUPLICATE_VERSION,
        SYMBOL_BUILD_TEXT_CONVERSION_VERSION,
        SYMBOL_BUILD_COMPRESSION_VERSION,
        SYMBOL_BUILD_VERSION,
    }
    if version not in supported_versions:
        raise SymbolManifestError(
            "symbol manifest.formatVersion must be one of: "
            + ", ".join(str(item) for item in sorted(supported_versions))
        )
    allowed = {"format", "formatVersion", "snapshot", "assets", "references", "audit"}
    if version >= SYMBOL_BUILD_PREFLIGHT_VERSION:
        allowed.add("processing")
    _only_keys(root, allowed, "symbol manifest")
    if root.get("format") != SYMBOL_BUILD_FORMAT:
        raise SymbolManifestError(f"symbol manifest.format must be {SYMBOL_BUILD_FORMAT!r}")

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

    if version >= SYMBOL_BUILD_PREFLIGHT_VERSION:
        _processing(
            root.get("processing"),
            archive_paths,
            version,
            "symbol manifest.processing",
        )


def _processing(value: Any, archive_paths: set[str], version: int, context: str) -> None:
    record = _object(value, context)
    asset_count = len(archive_paths)
    allowed = {"svgPreflight"}
    if version >= SYMBOL_BUILD_FONT_AUDIT_VERSION:
        allowed.add("fontAudit")
    if version >= SYMBOL_BUILD_DUPLICATE_VERSION:
        allowed.add("duplicateDetection")
    if version >= SYMBOL_BUILD_TEXT_CONVERSION_VERSION:
        allowed.add("textConversion")
    if version >= SYMBOL_BUILD_COMPRESSION_VERSION:
        allowed.add("compression")
    if version == SYMBOL_BUILD_VERSION:
        allowed.add("publication")
    _only_keys(record, allowed, context)
    preflight = _object(record.get("svgPreflight"), f"{context}.svgPreflight")
    _only_keys(preflight, {"status", "summary", "report"}, f"{context}.svgPreflight")
    status = _string(preflight.get("status"), f"{context}.svgPreflight.status")
    if status not in {"passed", "failed"}:
        raise SymbolManifestError(
            f"{context}.svgPreflight.status must be 'passed' or 'failed'"
        )

    summary = _object(preflight.get("summary"), f"{context}.svgPreflight.summary")
    fields = {
        "svgCount",
        "parseErrorCount",
        "activeTextAssetCount",
        "noActiveTextAssetCount",
        "fontDeclaredAssetCount",
        "uniqueDeclaredFontCount",
    }
    _only_keys(summary, fields, f"{context}.svgPreflight.summary")
    missing = fields - set(summary)
    if missing:
        raise SymbolManifestError(
            f"{context}.svgPreflight.summary is missing field(s): "
            + ", ".join(sorted(missing))
        )
    for field in sorted(fields):
        count = summary[field]
        if type(count) is not int or count < 0:
            raise SymbolManifestError(
                f"{context}.svgPreflight.summary.{field} must be a non-negative integer"
            )
    if summary["svgCount"] != asset_count:
        raise SymbolManifestError(
            f"{context}.svgPreflight.summary.svgCount must equal the asset count"
        )
    if summary["fontDeclaredAssetCount"] > asset_count:
        raise SymbolManifestError(
            f"{context}.svgPreflight.summary.fontDeclaredAssetCount cannot exceed asset count"
        )
    classified = (
        summary["parseErrorCount"]
        + summary["activeTextAssetCount"]
        + summary["noActiveTextAssetCount"]
    )
    if classified != asset_count:
        raise SymbolManifestError(
            f"{context}.svgPreflight summary classifications must account for every asset"
        )
    expected_status = "passed" if summary["parseErrorCount"] == 0 else "failed"
    if status != expected_status:
        raise SymbolManifestError(
            f"{context}.svgPreflight.status must be {expected_status!r} for this summary"
        )
    _artifact(preflight.get("report"), f"{context}.svgPreflight.report")

    if version == SYMBOL_BUILD_PREFLIGHT_VERSION:
        return
    if status != "passed":
        raise SymbolManifestError(
            f"{context}.svgPreflight.status must be 'passed' before font audit state"
        )

    font_audit = _object(record.get("fontAudit"), f"{context}.fontAudit")
    _only_keys(
        font_audit,
        {"status", "summary", "report", "aliases"},
        f"{context}.fontAudit",
    )
    font_status = _string(font_audit.get("status"), f"{context}.fontAudit.status")
    if font_status not in {"passed", "failed"}:
        raise SymbolManifestError(
            f"{context}.fontAudit.status must be 'passed' or 'failed'"
        )

    font_summary = _object(
        font_audit.get("summary"), f"{context}.fontAudit.summary"
    )
    font_fields = {
        "svgCount",
        "fontAvailableAssetCount",
        "fontMissingAssetCount",
        "noActiveTextAssetCount",
        "implicitDefaultAssetCount",
        "effectiveFontReferenceCount",
        "availableFontReferenceCount",
        "missingFontReferenceCount",
        "ambiguousFontReferenceCount",
        "genericFontReferenceCount",
        "normalizedAliasReferenceCount",
        "unusedDeclarationCount",
    }
    _only_keys(font_summary, font_fields, f"{context}.fontAudit.summary")
    missing_font_fields = font_fields - set(font_summary)
    if missing_font_fields:
        raise SymbolManifestError(
            f"{context}.fontAudit.summary is missing field(s): "
            + ", ".join(sorted(missing_font_fields))
        )
    for field in sorted(font_fields):
        count = font_summary[field]
        if type(count) is not int or count < 0:
            raise SymbolManifestError(
                f"{context}.fontAudit.summary.{field} must be a non-negative integer"
            )
    if font_summary["svgCount"] != asset_count:
        raise SymbolManifestError(
            f"{context}.fontAudit.summary.svgCount must equal the asset count"
        )
    classified = (
        font_summary["fontAvailableAssetCount"]
        + font_summary["fontMissingAssetCount"]
        + font_summary["noActiveTextAssetCount"]
    )
    if classified != asset_count:
        raise SymbolManifestError(
            f"{context}.fontAudit summary classifications must account for every asset"
        )
    if font_summary["implicitDefaultAssetCount"] > font_summary["fontAvailableAssetCount"]:
        raise SymbolManifestError(
            f"{context}.fontAudit.summary.implicitDefaultAssetCount cannot exceed "
            "fontAvailableAssetCount"
        )
    reference_classified = (
        font_summary["availableFontReferenceCount"]
        + font_summary["missingFontReferenceCount"]
        + font_summary["ambiguousFontReferenceCount"]
        + font_summary["genericFontReferenceCount"]
    )
    if reference_classified != font_summary["effectiveFontReferenceCount"]:
        raise SymbolManifestError(
            f"{context}.fontAudit reference classifications must account for every "
            "effective font reference"
        )
    if (
        font_summary["normalizedAliasReferenceCount"]
        > font_summary["availableFontReferenceCount"]
    ):
        raise SymbolManifestError(
            f"{context}.fontAudit.summary.normalizedAliasReferenceCount cannot exceed "
            "availableFontReferenceCount"
        )
    expected_font_status = (
        "passed" if font_summary["fontMissingAssetCount"] == 0 else "failed"
    )
    if font_status != expected_font_status:
        raise SymbolManifestError(
            f"{context}.fontAudit.status must be {expected_font_status!r} for this summary"
        )
    _artifact(font_audit.get("report"), f"{context}.fontAudit.report")
    _artifact(font_audit.get("aliases"), f"{context}.fontAudit.aliases")

    if version == SYMBOL_BUILD_FONT_AUDIT_VERSION:
        return
    if font_status != "passed":
        raise SymbolManifestError(
            f"{context}.fontAudit.status must be 'passed' before duplicate detection state"
        )
    _duplicate_detection(
        record.get("duplicateDetection"),
        archive_paths,
        f"{context}.duplicateDetection",
    )
    if version == SYMBOL_BUILD_DUPLICATE_VERSION:
        return
    _text_conversion(
        record.get("textConversion"),
        record["duplicateDetection"]["summary"]["canonicalAssetCount"],
        f"{context}.textConversion",
    )
    if version == SYMBOL_BUILD_TEXT_CONVERSION_VERSION:
        return
    _compression(
        record.get("compression"),
        record["duplicateDetection"]["summary"]["canonicalAssetCount"],
        f"{context}.compression",
    )
    if version == SYMBOL_BUILD_COMPRESSION_VERSION:
        return
    _publication(
        record.get("publication"),
        asset_count,
        record["duplicateDetection"]["summary"]["canonicalAssetCount"],
        f"{context}.publication",
    )


def _text_conversion(
    value: Any,
    canonical_asset_count: int,
    context: str,
) -> None:
    record = _object(value, context)
    _only_keys(
        record,
        {"status", "summary", "converter", "report", "summaryReport"},
        context,
    )
    status = _string(record.get("status"), f"{context}.status")
    if status not in {"passed", "failed"}:
        raise SymbolManifestError(f"{context}.status must be 'passed' or 'failed'")

    summary = _object(record.get("summary"), f"{context}.summary")
    fields = {
        "canonicalAssetCount",
        "conversionCandidateCount",
        "convertedAssetCount",
        "carriedForwardAssetCount",
        "failedAssetCount",
    }
    _only_keys(summary, fields, f"{context}.summary")
    missing = fields - set(summary)
    if missing:
        raise SymbolManifestError(
            f"{context}.summary is missing field(s): " + ", ".join(sorted(missing))
        )
    for field in sorted(fields):
        count = summary[field]
        if type(count) is not int or count < 0:
            raise SymbolManifestError(
                f"{context}.summary.{field} must be a non-negative integer"
            )
    if summary["canonicalAssetCount"] != canonical_asset_count:
        raise SymbolManifestError(
            f"{context}.summary.canonicalAssetCount must equal duplicate canonical count"
        )
    if (
        summary["conversionCandidateCount"] + summary["carriedForwardAssetCount"]
        != canonical_asset_count
    ):
        raise SymbolManifestError(
            f"{context} candidate/carried-forward counts must account for every canonical asset"
        )
    if (
        summary["convertedAssetCount"] + summary["failedAssetCount"]
        != summary["conversionCandidateCount"]
    ):
        raise SymbolManifestError(
            f"{context} converted/failed counts must account for every conversion candidate"
        )
    expected_status = "passed" if summary["failedAssetCount"] == 0 else "failed"
    if status != expected_status:
        raise SymbolManifestError(
            f"{context}.status must be {expected_status!r} for this summary"
        )

    converter = _object(record.get("converter"), f"{context}.converter")
    _only_keys(converter, {"name", "version", "jobs"}, f"{context}.converter")
    _string(converter.get("name"), f"{context}.converter.name")
    if "version" in converter:
        _string(converter["version"], f"{context}.converter.version")
    jobs = converter.get("jobs")
    if type(jobs) is not int or jobs < 1:
        raise SymbolManifestError(f"{context}.converter.jobs must be a positive integer")

    _artifact(record.get("report"), f"{context}.report")
    _artifact(record.get("summaryReport"), f"{context}.summaryReport")


def _compression(value: Any, canonical_asset_count: int, context: str) -> None:
    record = _object(value, context)
    _only_keys(
        record,
        {
            "status",
            "summary",
            "profile",
            "settings",
            "report",
            "candidatesReport",
            "runReport",
        },
        context,
    )
    status = _string(record.get("status"), f"{context}.status")
    if status != "passed":
        raise SymbolManifestError(f"{context}.status must be 'passed'")

    summary = _object(record.get("summary"), f"{context}.summary")
    fields = {
        "assetCount",
        "compressedAssetCount",
        "retainedAssetCount",
        "sourceBytes",
        "outputBytes",
        "reclaimedBytes",
    }
    _only_keys(summary, fields, f"{context}.summary")
    missing = fields - set(summary)
    if missing:
        raise SymbolManifestError(
            f"{context}.summary is missing field(s): " + ", ".join(sorted(missing))
        )
    for field in sorted(fields):
        count = summary[field]
        if type(count) is not int or count < 0:
            raise SymbolManifestError(
                f"{context}.summary.{field} must be a non-negative integer"
            )
    if summary["assetCount"] != canonical_asset_count:
        raise SymbolManifestError(
            f"{context}.summary.assetCount must equal duplicate canonical count"
        )
    if summary["compressedAssetCount"] + summary["retainedAssetCount"] != canonical_asset_count:
        raise SymbolManifestError(
            f"{context} compressed/retained counts must account for every canonical asset"
        )
    if summary["outputBytes"] > summary["sourceBytes"]:
        raise SymbolManifestError(f"{context}.summary.outputBytes cannot exceed sourceBytes")
    if summary["reclaimedBytes"] != summary["sourceBytes"] - summary["outputBytes"]:
        raise SymbolManifestError(
            f"{context}.summary.reclaimedBytes must equal sourceBytes - outputBytes"
        )
    expected_status = "passed"
    if status != expected_status:
        raise SymbolManifestError(
            f"{context}.status must be {expected_status!r} for a complete compression state"
        )

    profile = _string(record.get("profile"), f"{context}.profile")
    if profile != "balanced":
        raise SymbolManifestError(f"{context}.profile must be 'balanced'")

    settings = _object(record.get("settings"), f"{context}.settings")
    _only_keys(
        settings,
        {
            "renderer",
            "targetSizesCssPx",
            "dprs",
            "balancedPrecisions",
            "maxRms",
            "maxChangedFraction",
            "pixelDiffThreshold",
            "jobs",
        },
        f"{context}.settings",
    )
    _string(settings.get("renderer"), f"{context}.settings.renderer")
    for field in ("targetSizesCssPx", "balancedPrecisions"):
        values = settings.get(field)
        if not isinstance(values, list) or not values:
            raise SymbolManifestError(f"{context}.settings.{field} must be a non-empty array")
        if any(type(item) is not int or item < 1 for item in values):
            raise SymbolManifestError(
                f"{context}.settings.{field} values must be positive integers"
            )
    dprs = settings.get("dprs")
    if not isinstance(dprs, list) or not dprs or any(
        type(item) not in {int, float} or item <= 0 for item in dprs
    ):
        raise SymbolManifestError(
            f"{context}.settings.dprs must contain positive numbers"
        )
    for field in ("maxRms", "maxChangedFraction"):
        number = settings.get(field)
        if not isinstance(number, (int, float)) or isinstance(number, bool) or number < 0:
            raise SymbolManifestError(f"{context}.settings.{field} must be non-negative")
    threshold = settings.get("pixelDiffThreshold")
    if type(threshold) is not int or not 0 <= threshold <= 255:
        raise SymbolManifestError(
            f"{context}.settings.pixelDiffThreshold must be an integer from 0 to 255"
        )
    jobs = settings.get("jobs")
    if type(jobs) is not int or jobs < 1:
        raise SymbolManifestError(f"{context}.settings.jobs must be a positive integer")

    _artifact(record.get("report"), f"{context}.report")
    _artifact(record.get("candidatesReport"), f"{context}.candidatesReport")
    _artifact(record.get("runReport"), f"{context}.runReport")


def _publication(
    value: Any,
    source_asset_count: int,
    canonical_asset_count: int,
    context: str,
) -> None:
    record = _object(value, context)
    _only_keys(
        record,
        {"status", "summary", "mappingReport", "armyMap", "unitMap"},
        context,
    )
    status = _string(record.get("status"), f"{context}.status")
    if status != "passed":
        raise SymbolManifestError(f"{context}.status must be 'passed'")

    summary = _object(record.get("summary"), f"{context}.summary")
    fields = {
        "sourceAssetCount",
        "canonicalAssetCount",
        "publishedAssetCount",
        "factionMappingCount",
        "unitMappingCount",
        "staticMappingCount",
        "publishedBytes",
    }
    _only_keys(summary, fields, f"{context}.summary")
    missing = fields - set(summary)
    if missing:
        raise SymbolManifestError(
            f"{context}.summary is missing field(s): " + ", ".join(sorted(missing))
        )
    for field in sorted(fields):
        count = summary[field]
        if type(count) is not int or count < 0:
            raise SymbolManifestError(
                f"{context}.summary.{field} must be a non-negative integer"
            )
    if summary["sourceAssetCount"] != source_asset_count:
        raise SymbolManifestError(
            f"{context}.summary.sourceAssetCount must equal the source asset count"
        )
    if summary["canonicalAssetCount"] != canonical_asset_count:
        raise SymbolManifestError(
            f"{context}.summary.canonicalAssetCount must equal duplicate canonical count"
        )
    if summary["publishedAssetCount"] != canonical_asset_count:
        raise SymbolManifestError(
            f"{context}.summary.publishedAssetCount must equal canonical asset count"
        )
    _artifact(record.get("mappingReport"), f"{context}.mappingReport")
    _artifact(record.get("armyMap"), f"{context}.armyMap")
    _artifact(record.get("unitMap"), f"{context}.unitMap")

def _duplicate_detection(value: Any, archive_paths: set[str], context: str) -> None:
    record = _object(value, context)
    _only_keys(
        record,
        {
            "status",
            "summary",
            "renderer",
            "canonicalByArchivePath",
            "groupsReport",
            "errorsReport",
            "summaryReport",
        },
        context,
    )
    if _string(record.get("status"), f"{context}.status") != "passed":
        raise SymbolManifestError(f"{context}.status must be 'passed'")

    summary = _object(record.get("summary"), f"{context}.summary")
    fields = {
        "sourceAssetCount",
        "uniqueByteSetCount",
        "rendersAvoidedExactCount",
        "exactGroupCount",
        "visualGroupCount",
        "redundantAssetCount",
        "canonicalAssetCount",
        "renderErrorCount",
    }
    size_fields = {
        "sourceAssetBytes",
        "canonicalAssetBytes",
        "reclaimedAssetBytes",
    }
    _only_keys(summary, fields | size_fields, f"{context}.summary")
    missing = fields - set(summary)
    if missing:
        raise SymbolManifestError(
            f"{context}.summary is missing field(s): " + ", ".join(sorted(missing))
        )
    for field in sorted(fields):
        count = summary[field]
        if type(count) is not int or count < 0:
            raise SymbolManifestError(
                f"{context}.summary.{field} must be a non-negative integer"
            )
    present_size_fields = size_fields & set(summary)
    if present_size_fields and present_size_fields != size_fields:
        raise SymbolManifestError(
            f"{context}.summary size fields must be present as a complete set"
        )
    for field in sorted(present_size_fields):
        count = summary[field]
        if type(count) is not int or count < 0:
            raise SymbolManifestError(
                f"{context}.summary.{field} must be a non-negative integer"
            )
    if present_size_fields:
        if summary["canonicalAssetBytes"] > summary["sourceAssetBytes"]:
            raise SymbolManifestError(
                f"{context}.summary.canonicalAssetBytes cannot exceed sourceAssetBytes"
            )
        if (
            summary["sourceAssetBytes"] - summary["canonicalAssetBytes"]
            != summary["reclaimedAssetBytes"]
        ):
            raise SymbolManifestError(
                f"{context}.summary.reclaimedAssetBytes must equal "
                "sourceAssetBytes - canonicalAssetBytes"
            )
    asset_count = len(archive_paths)
    if summary["sourceAssetCount"] != asset_count:
        raise SymbolManifestError(f"{context}.summary.sourceAssetCount must equal asset count")
    if summary["canonicalAssetCount"] + summary["redundantAssetCount"] != asset_count:
        raise SymbolManifestError(
            f"{context} canonical/redundant counts must account for every asset"
        )
    if summary["uniqueByteSetCount"] > asset_count:
        raise SymbolManifestError(f"{context}.summary.uniqueByteSetCount cannot exceed asset count")
    if summary["rendersAvoidedExactCount"] != asset_count - summary["uniqueByteSetCount"]:
        raise SymbolManifestError(
            f"{context}.summary.rendersAvoidedExactCount must equal "
            "sourceAssetCount - uniqueByteSetCount"
        )

    renderer = _object(record.get("renderer"), f"{context}.renderer")
    _only_keys(renderer, {"name", "version", "renderSize", "jobs"}, f"{context}.renderer")
    _string(renderer.get("name"), f"{context}.renderer.name")
    if "version" in renderer:
        _string(renderer["version"], f"{context}.renderer.version")
    for field in ("renderSize", "jobs"):
        count = renderer.get(field)
        if type(count) is not int or count < 1:
            raise SymbolManifestError(f"{context}.renderer.{field} must be a positive integer")

    canonical = _object(record.get("canonicalByArchivePath"), f"{context}.canonicalByArchivePath")
    if set(canonical) != archive_paths:
        raise SymbolManifestError(f"{context}.canonicalByArchivePath must cover every asset")
    canonical_values: set[str] = set()
    redundant_count = 0
    for source, target in canonical.items():
        _portable_path(source, f"{context}.canonicalByArchivePath key")
        canonical_target = _portable_path(target, f"{context}.canonicalByArchivePath[{source!r}]")
        if canonical_target not in archive_paths:
            raise SymbolManifestError(
                f"{context} canonical target is not an asset: {canonical_target}"
            )
        canonical_values.add(canonical_target)
        redundant_count += source != canonical_target
    for target in canonical_values:
        if canonical.get(target) != target:
            raise SymbolManifestError(f"{context} canonical target must map to itself: {target}")
    if redundant_count != summary["redundantAssetCount"]:
        raise SymbolManifestError(f"{context} redundant mapping count does not match summary")
    if len(canonical_values) != summary["canonicalAssetCount"]:
        raise SymbolManifestError(f"{context} canonical mapping count does not match summary")

    _artifact(record.get("groupsReport"), f"{context}.groupsReport")
    _artifact(record.get("errorsReport"), f"{context}.errorsReport")
    _artifact(record.get("summaryReport"), f"{context}.summaryReport")


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
