"""Verify a standalone SVG duplicate-stage receipt without a renderer.

The original raw/effective-source handoff is verified separately. This
consumer validates the next stage's evidence against its immutable effective
ZIP and passed font audit; it does not establish visual parity independently.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
from tools.symbols.verify_effective_symbol_handoff import _json, _member, _object

RECEIPT_FORMAT = "InfinityDB symbol processing stage receipt"
FONT_FORMAT = "InfinityDB SVG font audit"
EFFECTIVE_FORMAT = "InfinityDB effective symbol processing report"
SUMMARY_FIELDS = {
    "sourceAssetCount": "source_svg_files",
    "canonicalAssetCount": "canonical_svg_files",
    "uniqueByteSetCount": "unique_byte_sets",
    "rendersAvoidedExactCount": "renders_avoided_exact",
    "exactGroupCount": "exact_groups",
    "visualGroupCount": "visual_groups",
    "redundantAssetCount": "redundant_files",
    "renderErrorCount": "render_errors",
    "sourceAssetBytes": "source_size_bytes",
    "canonicalAssetBytes": "canonical_size_bytes",
    "reclaimedAssetBytes": "reclaimed_size_bytes",
}


class DuplicateHandoffError(ValueError):
    """The external duplicate evidence is incomplete or inconsistent."""


def _csv(path: Path, fields: set[str]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or set(reader.fieldnames) != fields:
                raise DuplicateHandoffError(f"Unexpected CSV header in {path}")
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        raise DuplicateHandoffError(f"Could not read duplicate CSV {path}: {exc}") from exc
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise DuplicateHandoffError(f"Malformed duplicate CSV row in {path}")
    return rows


def _pinned_file(path: Path, record: Any, label: str) -> None:
    if record != {"name": path.name, "sha256": sha256_file(path)}:
        raise DuplicateHandoffError(f"{label} name/SHA-256 does not match supplied file")


def verify_duplicate_symbol_handoff(
    effective_archive: Path,
    effective_manifest: Path,
    effective_report: Path,
    font_report: Path,
    font_receipt: Path,
    groups_csv: Path,
    errors_csv: Path,
    summary_csv: Path,
    receipt_path: Path,
) -> dict[str, int]:
    """Verify canonical group/CSV evidence and all relevant SHA-256 identities."""
    provenance = load_snapshot_manifest(effective_manifest, archive=effective_archive)
    effective = _json(effective_report)
    if not isinstance(effective, dict) or (
        effective.get("format") != EFFECTIVE_FORMAT
        or effective.get("formatVersion") != 1
        or provenance["snapshot"]["type"] != "symbols"
    ):
        raise DuplicateHandoffError("Unrecognized effective-symbol source evidence")
    snapshot = effective.get("snapshot")
    if not isinstance(snapshot, dict) or any((
        snapshot.get("archiveName") != effective_archive.name,
        snapshot.get("sha256") != sha256_file(effective_archive),
        snapshot.get("manifestName") != effective_manifest.name,
        snapshot.get("manifestSha256") != sha256_file(effective_manifest),
        snapshot.get("documentCount") != provenance["snapshot"]["documentCount"],
    )):
        raise DuplicateHandoffError("Effective archive/manifest source evidence mismatch")
    source_assets = effective.get("assets")
    if not isinstance(source_assets, list) or not source_assets:
        raise DuplicateHandoffError("Missing effective symbol asset list")
    paths: dict[str, tuple[str, int]] = {}
    with zipfile.ZipFile(effective_archive) as source:
        members = [entry.filename for entry in source.infolist() if not entry.is_dir()]
        if len(set(members)) != len(members):
            raise DuplicateHandoffError("Duplicate effective ZIP members")
        for row in source_assets:
            if not isinstance(row, dict):
                raise DuplicateHandoffError("Invalid effective asset row")
            name = _member(row.get("archivePath"))
            if name in paths:
                raise DuplicateHandoffError("Repeated effective asset path")
            try:
                body = source.read(name)
            except KeyError as exc:
                raise DuplicateHandoffError(f"Missing source SVG: {name}") from exc
            sha = hashlib.sha256(body).hexdigest()
            if sha != row.get("sha256"):
                raise DuplicateHandoffError(f"Effective SVG byte hash mismatch: {name}")
            paths[name] = (sha, len(body))
        if set(paths) != set(members):
            raise DuplicateHandoffError("Effective source asset list differs from ZIP members")

    font = _json(font_report)
    font_state = _json(font_receipt)
    artifact = {"name": effective_archive.name, "sha256": sha256_file(effective_archive)}
    if not isinstance(font, dict) or (
        font.get("format") != FONT_FORMAT
        or font.get("formatVersion") != 1
        or font.get("symbolArtifact") != artifact
        or not isinstance(font_state, dict)
        or font_state.get("format") != RECEIPT_FORMAT
        or font_state.get("formatVersion") != 1
        or font_state.get("stage") != "fontAudit"
        or font_state.get("status") != "passed"
        or font_state.get("inputArtifact") != artifact
        or font_state.get("report") != {
            "name": font_report.name, "sha256": sha256_file(font_report),
        }
        or font_state.get("summary") != font.get("summary")
    ):
        raise DuplicateHandoffError("Font-audit evidence is not passed or source-pinned")
    font_rows = font.get("assets")
    if not isinstance(font_rows, list):
        raise DuplicateHandoffError("Font-audit classifications are missing")
    categories: dict[str, str] = {}
    for row in font_rows:
        if not isinstance(row, dict):
            raise DuplicateHandoffError("Invalid font-audit classification row")
        name, category = row.get("archivePath"), row.get("category")
        if (
            not isinstance(name, str)
            or name in categories
            or category not in {"no_active_text", "fonts_available"}
        ):
            raise DuplicateHandoffError("Unknown or duplicate font-audit classification")
        categories[name] = category
    if set(categories) != set(paths):
        raise DuplicateHandoffError("Font-audit asset coverage differs from effective ZIP")

    receipt = _json(receipt_path)
    receipt = _object(
        receipt,
        {
            "format", "formatVersion", "stage", "status", "inputArtifact",
            "fontAuditReport", "fontAuditReceipt", "renderer", "rendererVersion",
            "renderSize", "jobs", "reports", "summary", "canonicalByArchivePath",
        },
        "duplicate-stage receipt",
    )
    if (
        receipt["format"] != RECEIPT_FORMAT
        or receipt["formatVersion"] != 1
        or receipt["stage"] != "duplicateDetection"
        or receipt["status"] not in {"passed", "failed"}
        or receipt["inputArtifact"] != artifact
    ):
        raise DuplicateHandoffError("Unexpected duplicate-stage receipt state")
    _pinned_file(font_report, receipt["fontAuditReport"], "Font report")
    _pinned_file(font_receipt, receipt["fontAuditReceipt"], "Font receipt")
    if (
        not isinstance(receipt["renderer"], str)
        or not receipt["renderer"]
        or not isinstance(receipt["rendererVersion"], str)
        or type(receipt["renderSize"]) is not int or receipt["renderSize"] < 1
        or type(receipt["jobs"]) is not int or receipt["jobs"] < 1
    ):
        raise DuplicateHandoffError("Renderer/version/render parameters are invalid")

    report_files = {
        "groups": groups_csv, "errors": errors_csv, "summary": summary_csv,
    }
    if not isinstance(receipt["reports"], dict) or set(receipt["reports"]) != set(report_files):
        raise DuplicateHandoffError("Incomplete duplicate CSV report declarations")
    for label, file in report_files.items():
        _pinned_file(file, receipt["reports"][label], f"{label} CSV")

    mapping = receipt["canonicalByArchivePath"]
    if (
        not isinstance(mapping, dict)
        or set(mapping) != set(paths)
        or any(not isinstance(value, str) or value not in paths for value in mapping.values())
        or any(mapping[target] != target for target in mapping.values())
    ):
        raise DuplicateHandoffError("Invalid or chained canonical representative mapping")
    summary = receipt["summary"]
    if (
        not isinstance(summary, dict)
        or set(summary) != set(SUMMARY_FIELDS)
        or any(type(value) is not int or value < 0 for value in summary.values())
    ):
        raise DuplicateHandoffError("Invalid duplicate summary metric fields")
    groups = _csv(
        groups_csv,
        {
            "group", "type", "role", "representative", "classification",
            "file", "size_bytes", "byte_sha256", "visual_sha256",
        },
    )
    group_members: dict[str, list[dict[str, str]]] = {}
    seen: set[str] = set()
    for row in groups:
        name = row["file"]
        if name in seen or name not in paths:
            raise DuplicateHandoffError("Duplicate CSV group includes unknown/repeated SVG")
        seen.add(name)
        if (
            row["classification"] != categories[name]
            or row["byte_sha256"] != paths[name][0]
            or row["size_bytes"] != str(paths[name][1])
            or row["role"] not in {"representative", "duplicate"}
            or row["type"] not in {"exact", "visual"}
            or row["representative"] != mapping[name]
            or not row["group"]
        ):
            raise DuplicateHandoffError(f"Duplicate group metadata disagrees for {name}")
        group_members.setdefault(row["group"], []).append(row)

    group_types: Counter[str] = Counter()
    for group, entries in group_members.items():
        representatives = [row for row in entries if row["role"] == "representative"]
        if len(entries) < 2 or len(representatives) != 1:
            raise DuplicateHandoffError(f"Invalid duplicate group membership: {group}")
        representative = representatives[0]["file"]
        if (
            mapping[representative] != representative
            or any(row["representative"] != representative for row in entries)
            or any(row["type"] != entries[0]["type"] for row in entries)
            or any(row["visual_sha256"] != entries[0]["visual_sha256"] for row in entries)
            or any(
                (row["role"] == "representative") != (row["file"] == representative)
                for row in entries
            )
        ):
            raise DuplicateHandoffError(f"Conflicting duplicate representatives: {group}")
        kind = entries[0]["type"]
        byte_hashes = {row["byte_sha256"] for row in entries}
        if (kind == "exact") != (len(byte_hashes) == 1):
            raise DuplicateHandoffError(f"Duplicate group type/byte identity mismatch: {group}")
        group_types[kind] += 1

    redundant = {name for name, target in mapping.items() if target != name}
    if redundant != {row["file"] for row in groups if row["role"] == "duplicate"}:
        raise DuplicateHandoffError("Canonical representative map differs from CSV groups")
    errors = _csv(errors_csv, {"file", "byte_sha256", "renderer", "error"})
    for row in errors:
        name = row["file"]
        if (
            name not in paths
            or row["byte_sha256"] != paths[name][0]
            or row["renderer"] != receipt["renderer"]
            or not row["error"]
        ):
            raise DuplicateHandoffError("Invalid duplicate render-error row")

    source_bytes = sum(size for _, size in paths.values())
    canonical_bytes = sum(paths[name][1] for name, target in mapping.items() if name == target)
    expected_summary = {
        "sourceAssetCount": len(paths),
        "canonicalAssetCount": len(paths) - len(redundant),
        "uniqueByteSetCount": len({sha for sha, _size in paths.values()}),
        "rendersAvoidedExactCount": len(paths) - len({sha for sha, _size in paths.values()}),
        "exactGroupCount": group_types["exact"],
        "visualGroupCount": group_types["visual"],
        "redundantAssetCount": len(redundant),
        "renderErrorCount": len(errors),
        "sourceAssetBytes": source_bytes,
        "canonicalAssetBytes": canonical_bytes,
        "reclaimedAssetBytes": source_bytes - canonical_bytes,
    }
    if summary != expected_summary or (
        (receipt["status"] == "passed") != (summary["renderErrorCount"] == 0)
    ):
        raise DuplicateHandoffError("Duplicate receipt summary/count/status mismatch")

    report_rows = _csv(
        summary_csv,
        {
            "renderer", "renderer_version", "jobs", "render_size",
            "source_svg_files", "canonical_svg_files", "unique_byte_sets",
            "renders_avoided_exact", "exact_groups", "visual_groups",
            "redundant_files", "render_errors", "source_size_bytes",
            "canonical_size_bytes", "reclaimed_size_bytes",
            "reduction_percent", "elapsed_seconds",
        },
    )
    if len(report_rows) != 1:
        raise DuplicateHandoffError("Duplicate summary CSV must have exactly one row")
    report_row = report_rows[0]
    if (
        report_row["renderer"] != receipt["renderer"]
        or report_row["renderer_version"] != receipt["rendererVersion"]
        or report_row["render_size"] != str(receipt["renderSize"])
        or report_row["jobs"] != str(receipt["jobs"])
        or any(report_row[column] != str(summary[key]) for key, column in SUMMARY_FIELDS.items())
    ):
        raise DuplicateHandoffError("Duplicate summary CSV disagrees with pinned receipt")
    return {
        "assets": len(paths),
        "canonical": len(paths) - len(redundant),
        "redundant": len(redundant),
        "renderErrors": len(errors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "effective-archive", "effective-manifest", "effective-report",
        "font-report", "font-receipt", "groups-csv", "errors-csv",
        "summary-csv", "receipt",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_duplicate_symbol_handoff(
            args.effective_archive, args.effective_manifest, args.effective_report,
            args.font_report, args.font_receipt, args.groups_csv, args.errors_csv,
            args.summary_csv, args.receipt,
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(
        f"Duplicate report verified: {result['canonical']} canonical, "
        f"{result['redundant']} redundant, {result['renderErrors']} render errors; "
        "visual equivalence still requires renderer-based acceptance"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
