"""Independently verify a compressed canonical symbol artifact before publication.

This is a byte/provenance/structure verifier, not a second raster comparison.
No external symbol-tools package, renderer, or network access is required.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from infinity_db.snapshot_provenance import sha256_file
from tools.verify_effective_symbol_handoff import _member, _sha

FORMAT = "InfinityDB symbol processing stage receipt"


class ProcessedSymbolHandoffError(ValueError):
    """External processed-symbol artifact failed independent validation."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProcessedSymbolHandoffError(f"Cannot read receipt: {path}") from exc
    if not isinstance(value, dict):
        raise ProcessedSymbolHandoffError("Receipt must be a JSON object")
    return value


def _pin(path: Path, value: Any, label: str) -> None:
    if value != {"name": path.name, "sha256": sha256_file(path)}:
        raise ProcessedSymbolHandoffError(f"{label} name/hash mismatch")


def _assets(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ProcessedSymbolHandoffError("Missing canonical asset records")
    result: dict[str, dict[str, Any]] = {}
    for row in value:
        if not isinstance(row, dict):
            raise ProcessedSymbolHandoffError("Malformed canonical asset record")
        path = _member(row.get("archivePath"))
        if path in result or path.casefold() in (p.casefold() for p in result):
            raise ProcessedSymbolHandoffError("Duplicate or case-colliding canonical path")
        _sha(row.get("sha256"), f"Hash of {path}")
        result[path] = row
    return result


def _zip_assets(archive: Path, expected: dict[str, dict[str, Any]]) -> None:
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        names = [item.filename for item in members]
        if len(names) != len(expected) or set(names) != set(expected):
            raise ProcessedSymbolHandoffError("ZIP members differ from canonical receipt")
        if len({name.casefold() for name in names}) != len(names):
            raise ProcessedSymbolHandoffError("Case-colliding ZIP member paths")
        for member in members:
            _member(member.filename)
            if member.is_dir() or member.file_size > 32 * 1024 * 1024:
                raise ProcessedSymbolHandoffError("Unsafe ZIP member")
            if member.flag_bits & 1:
                raise ProcessedSymbolHandoffError("Encrypted ZIP member")
            body = source.read(member)
            if hashlib.sha256(body).hexdigest() != expected[member.filename]["sha256"]:
                raise ProcessedSymbolHandoffError("Compressed SVG hash mismatch")
            try:
                root = ElementTree.fromstring(body)
            except ElementTree.ParseError as exc:
                raise ProcessedSymbolHandoffError("Invalid compressed SVG XML") from exc
            if root.tag.rsplit("}", 1)[-1] != "svg":
                raise ProcessedSymbolHandoffError("Compressed asset is not an SVG")
            if any(
                node.tag.rsplit("}", 1)[-1] in {"text", "flowRoot"}
                and "".join(node.itertext()).strip()
                for node in root.iter()
            ):
                raise ProcessedSymbolHandoffError("Compressed SVG contains active text")


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ProcessedSymbolHandoffError("Missing compression CSV header")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ProcessedSymbolHandoffError("Malformed compression CSV")
    return rows


def verify_processed_symbol_handoff(
    canonical_archive: Path,
    conversion_receipt: Path,
    compressed_archive: Path,
    compression_receipt: Path,
    compression_report: Path,
    candidates_report: Path,
    run_report: Path,
) -> dict[str, int]:
    """Check provenance, all output bytes and the compressor's reported coverage."""
    conversion = _load(conversion_receipt)
    compression = _load(compression_receipt)
    for state, stage in ((conversion, "textConversion"), (compression, "compression")):
        if any((
            state.get("format") != FORMAT,
            state.get("formatVersion") != 1,
            state.get("stage") != stage,
            state.get("status") != "passed",
        )):
            raise ProcessedSymbolHandoffError(f"Invalid or unpassed {stage} receipt")
    _pin(canonical_archive, conversion.get("outputArtifact"), "Converted artifact")
    _pin(canonical_archive, compression.get("inputArtifact"), "Compression input")
    _pin(conversion_receipt, compression.get("textConversionReceipt"), "Conversion receipt")
    _pin(compressed_archive, compression.get("outputArtifact"), "Compressed artifact")
    reports = compression.get("reports")
    if not isinstance(reports, dict) or set(reports) != {"compression", "candidates", "run"}:
        raise ProcessedSymbolHandoffError("Incomplete compression reports")
    for name, path in (
        ("compression", compression_report),
        ("candidates", candidates_report),
        ("run", run_report),
    ):
        _pin(path, reports[name], f"{name} report")

    original = _assets(conversion.get("outputAssets"))
    final = _assets(compression.get("outputAssets"))
    if set(original) != set(final):
        raise ProcessedSymbolHandoffError("Canonical identities changed during compression")
    mapping = conversion.get("canonicalByArchivePath")
    if (
        not isinstance(mapping, dict) or not mapping
        or set(mapping.values()) != set(original)
        or any(not isinstance(key, str) or not isinstance(value, str)
               or mapping.get(value) != value for key, value in mapping.items())
    ):
        raise ProcessedSymbolHandoffError("Invalid source-to-canonical mapping")
    for path in original:
        if final[path].get("sourceSha256") != original[path]["sha256"]:
            raise ProcessedSymbolHandoffError("Compressed source identity mismatch")
    _zip_assets(canonical_archive, original)
    _zip_assets(compressed_archive, final)

    info = _load(run_report)
    parameters = compression.get("parameters")
    if (
        not isinstance(parameters, dict)
        or compression.get("profile") not in {"balanced", "small"}
        or compression.get("renderer") not in {"resvg", "inkscape"}
        or not isinstance(compression.get("rendererVersion"), str)
        or not compression["rendererVersion"].strip()
        or compression["rendererVersion"] == "unknown"
        or not isinstance(compression.get("svgoVersion"), str)
        or not compression["svgoVersion"].strip()
        or compression["svgoVersion"] == "unknown"
        or info.get("profiles") != [compression["profile"]]
        or info.get("renderer") != compression["renderer"]
        or info.get("renderer_version") != compression["rendererVersion"]
        or info.get("svgo_version") != compression["svgoVersion"]
        or info.get("target_sizes_css_px") != parameters.get("targetSizes")
        or info.get("dprs") != parameters.get("dprs")
        or info.get("balanced_precisions") != parameters.get("balancedPrecisions")
        or info.get("max_rms") != parameters.get("maxRms")
        or info.get("max_changed_fraction") != parameters.get("maxChangedFraction")
        or info.get("pixel_diff_threshold") != parameters.get("pixelDiffThreshold")
        or info.get("jobs") != parameters.get("jobs")
    ):
        raise ProcessedSymbolHandoffError("Compression versions or parameters disagree")
    rows = _rows(compression_report)
    if len(rows) != len(final) or {row.get("file") for row in rows} != set(final):
        raise ProcessedSymbolHandoffError("Compression report coverage mismatch")
    for row in rows:
        if (
            row.get("profile") != compression["profile"]
            or row.get("error")
            or row.get("status") not in {
                "OK", "NO_SMALLER_PASSING_CANDIDATE", "LOSSLESS_FALLBACK",
            }
            or int(row["source_bytes"]) != len(_zip_member(canonical_archive, row["file"]))
            or int(row["output_bytes"]) != len(_zip_member(compressed_archive, row["file"]))
        ):
            raise ProcessedSymbolHandoffError("Compression report has invalid result")
    candidates = _rows(candidates_report)
    if any(row.get("error") for row in candidates):
        raise ProcessedSymbolHandoffError("Unresolved candidate errors")
    summary = compression.get("summary")
    if (
        not isinstance(summary, dict)
        or summary.get("assetCount") != len(final)
        or summary.get("sourceBytes") != sum(int(row["source_bytes"]) for row in rows)
        or summary.get("outputBytes") != sum(int(row["output_bytes"]) for row in rows)
    ):
        raise ProcessedSymbolHandoffError("Compression totals disagree")
    return {"canonicalAssets": len(final), "sourceIdentities": len(mapping)}


def _zip_member(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read(name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "canonical-archive", "conversion-receipt", "compressed-archive",
        "compression-receipt", "compression-report", "candidates-report", "run-report",
    ):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        summary = verify_processed_symbol_handoff(
            args.canonical_archive, args.conversion_receipt,
            args.compressed_archive, args.compression_receipt,
            args.compression_report, args.candidates_report, args.run_report,
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Processed symbol handoff PASS: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
