"""Prepare a fresh semantic publication candidate from external processed SVGs.

Offline and renderer-free. This verifies the complete handoff before writing a
candidate directory; it does not replace release assets or runtime databases.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from infinity_db.identities import DEFAULT_IDENTITY_CONFIG
from infinity_db.snapshot_provenance import sha256_file
from tools.symbols.export_symbol_override_lookups import build_override_lookup_plan
from tools.symbols.symbol_publication import (
    PUBLICATION_MANIFEST,
    build_publication,
    load_snapshot_index,
)
from tools.symbols.symbol_source import (
    DEFAULT_LEGACY_ARMIES,
    DEFAULT_STATIC_CONFIG,
    discover_symbol_source,
)
from tools.symbols.verify_effective_symbol_handoff import _member, verify_effective_symbol_handoff
from tools.symbols.verify_processed_symbol_handoff import (
    FORMAT,
    _load,
    _pin,
    _rows,
    verify_processed_symbol_handoff,
)
from tools.symbols.verify_symbol_duplicate_handoff import verify_duplicate_symbol_handoff


@dataclass(frozen=True)
class SymbolPublicationHandoff:
    """Explicit immutable selections; companion filenames follow the v1 format."""

    source_plan: Path
    override_lookups: Path
    army: Path
    army_manifest: Path
    raw_archive: Path
    effective_archive: Path
    stage_reports: Path
    processed_root: Path

    def files(self) -> dict[str, Path]:
        result = {
            "source_plan": self.source_plan, "override_lookups": self.override_lookups,
            "army": self.army, "army_manifest": self.army_manifest,
            "raw_archive": self.raw_archive,
            "raw_manifest": self.raw_archive.with_suffix(".json"),
            "raw_report": self.raw_archive.with_suffix(".raw-report.json"),
            "effective_archive": self.effective_archive,
            "effective_manifest": self.effective_archive.with_suffix(".json"),
            "effective_report": self.effective_archive.with_suffix(".effective-report.json"),
        }
        for name in ("svg-preflight", "font-audit", "duplicate"):
            if name != "duplicate":
                result[name + "_report"] = self.stage_reports / (name + ".json")
            result[name + "_receipt"] = self.stage_reports / (name + "-state.json")
        for name in ("groups", "render-errors", "summary"):
            result["duplicate_" + name] = (
                self.stage_reports / "duplicates" / ("duplicate-" + name + ".csv")
            )
        result.update({
            "canonical_archive": self.processed_root / "CANONICAL.zip",
            "conversion_receipt": self.processed_root / "text-conversion-state.json",
            "conversion_report": self.processed_root / "svg-text-to-path-report.csv",
            "conversion_summary": self.processed_root / "text-conversion-summary.csv",
            "compressed_archive": self.processed_root / "COMPRESSED.zip",
            "compression_receipt": self.processed_root / "compression-state.json",
            "compression_report": self.processed_root / "compression-report.csv",
            "candidates_report": self.processed_root / "compression-candidates.csv",
            "run_report": self.processed_root / "compression-run.json",
        })
        return result


def _pins(files: dict[str, Path]) -> dict[str, dict[str, str]]:
    return {key: {"name": path.name, "sha256": sha256_file(path)}
            for key, path in sorted(files.items())}


def _verify_chain(files: dict[str, Path]) -> dict[str, Any]:
    """Join independently verified stages to the same effective source artifact."""
    preflight = _load(files["svg-preflight_receipt"])
    font = _load(files["font-audit_receipt"])
    duplicate = _load(files["duplicate_receipt"])
    conversion = _load(files["conversion_receipt"])
    for state, stage in (
        (preflight, "svgPreflight"), (font, "fontAudit"),
        (duplicate, "duplicateDetection"), (conversion, "textConversion"),
    ):
        if (state.get("format") != FORMAT or state.get("formatVersion") != 1
                or state.get("stage") != stage or state.get("status") != "passed"):
            raise ValueError(f"Unpassed or unsupported {stage} receipt")
        _pin(files["effective_archive"], state.get("inputArtifact"), stage + " input")
    _pin(files["svg-preflight_report"], preflight.get("report"), "Preflight report")
    _pin(files["svg-preflight_receipt"], font.get("preflightReceipt"), "Preflight receipt")
    _pin(files["svg-preflight_report"], font.get("preflightReport"), "Font preflight report")
    report = _load(files["svg-preflight_report"])
    if (preflight.get("summary") != report.get("summary")
            or report.get("symbolArtifact") != preflight["inputArtifact"]
            or report["summary"].get("parseErrorCount") != 0):
        raise ValueError("Preflight report has inconsistent or failed results")
    for state in (font, conversion):
        _pin(files["font_aliases"], state.get("fontAliases"), "Font aliases")
    for label, file in (
        ("fontAuditReceipt", "font-audit_receipt"),
        ("fontAuditReport", "font-audit_report"), ("duplicateReceipt", "duplicate_receipt"),
    ):
        _pin(files[file], conversion.get(label), label)
    version = conversion.get("converterVersion")
    if (conversion.get("canonicalByArchivePath") != duplicate["canonicalByArchivePath"]
            or conversion.get("duplicateReports") != duplicate.get("reports")
            or not isinstance(conversion.get("converter"), str) or not conversion["converter"]
            or not isinstance(version, str) or not version.strip() or version == "unknown"
            or conversion.get("summary", {}).get("conversionFailureCount") != 0):
        raise ValueError("Conversion does not preserve the passed duplicate-stage evidence")
    for key, file in (("conversion", "conversion_report"), ("summary", "conversion_summary")):
        _pin(files[file], conversion.get("reports", {}).get(key), "Conversion " + key)
    sources = {row["archivePath"]: row["sha256"]
               for row in _load(files["effective_report"])["assets"]}
    converted = set()
    for row in conversion["outputAssets"]:
        if (row.get("sourceSha256") != sources.get(row["archivePath"])
                or type(row.get("converted")) is not bool
                or (not row["converted"] and row["sha256"] != row["sourceSha256"])):
            raise ValueError("Converted asset is not bound to its effective source bytes")
        if row["converted"]:
            converted.add(row["archivePath"])
    summary = conversion["summary"]
    if (summary.get("sourceAssetCount") != len(sources)
            or summary.get("canonicalAssetCount") != len(conversion["outputAssets"])
            or summary.get("convertedCount") != len(converted)
            or summary.get("textCandidateCount") != len(converted)
            or preflight["summary"].get("svgCount") != len(sources)):
        raise ValueError("Conversion/preflight counts differ from verified source coverage")
    rows = _rows(files["conversion_report"])
    if (len(rows) != len(converted) or {row.get("file") for row in rows} != converted
            or any(row.get("error") or row.get("converter") != conversion["converter"]
                   or row.get("status") not in {
                       "CONVERTED", "CONVERTED+ALIASES", "CONVERTED+FALLBACK",
                       "CONVERTED+ALIASES+FALLBACK",
                   } for row in rows)):
        raise ValueError("Conversion CSV does not cover exactly the successful conversions")
    totals = _rows(files["conversion_summary"])
    if (len(totals) != 1 or totals[0].get("converter") != conversion["converter"]
            or totals[0].get("converter_version") != version
            or totals[0].get("files_found") != str(len(converted))
            or totals[0].get("converted") != str(len(converted))
            or any(totals[0].get(key) != "0" for key in (
                "failed", "skipped_existing", "skipped_duplicates",
            ))):
        raise ValueError("Conversion summary CSV disagrees with its passed receipt")
    return conversion


def prepare_symbol_publication(
    handoff: SymbolPublicationHandoff,
    output: Path,
    *,
    font_aliases: Path,
    static_symbols: Path = DEFAULT_STATIC_CONFIG,
    legacy_armies: Path | None = DEFAULT_LEGACY_ARMIES,
) -> dict[str, Any]:
    """Verify source/stage provenance and prepare one immutable candidate."""
    if output.exists() or output.is_symlink():
        raise FileExistsError("Candidate destination already exists")
    files = handoff.files()
    files.update({"static_symbols": static_symbols, "font_aliases": font_aliases,
                  "identities": DEFAULT_IDENTITY_CONFIG})
    if legacy_armies is not None:
        files["legacy_armies"] = legacy_armies
    before = _pins(files)
    source_plan = _load(handoff.source_plan)
    expected = build_override_lookup_plan(
        handoff.army, handoff.army_manifest, source_plan,
        static_symbols_path=static_symbols, legacy_armies_path=legacy_armies,
    )
    if expected != _load(handoff.override_lookups):
        raise ValueError("Override lookup plan differs from authoritative Army discovery")
    verify_effective_symbol_handoff(*(files[key] for key in (
        "source_plan", "override_lookups", "army", "raw_archive", "raw_manifest",
        "raw_report", "effective_archive", "effective_manifest", "effective_report",
    )))
    duplicate_counts = verify_duplicate_symbol_handoff(*(files[key] for key in (
        "effective_archive", "effective_manifest", "effective_report", "font-audit_report",
        "font-audit_receipt", "duplicate_groups", "duplicate_render-errors",
        "duplicate_summary", "duplicate_receipt",
    )))
    if duplicate_counts["renderErrors"]:
        raise ValueError("Duplicate detection has unresolved render errors")
    verify_processed_symbol_handoff(*(files[key] for key in (
        "canonical_archive", "conversion_receipt", "compressed_archive",
        "compression_receipt", "compression_report", "candidates_report", "run_report",
    )))
    conversion = _verify_chain(files)
    effective = _load(files["effective_report"])
    discovery = discover_symbol_source(
        handoff.army, static_symbols_path=static_symbols, legacy_armies_path=legacy_armies,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".symbol-candidate-", dir=output.parent) as temporary:
        staging = Path(temporary)
        compressed = staging / "compressed"
        with zipfile.ZipFile(files["compressed_archive"]) as archive:
            # The independent verifier has already checked every portable member and hash.
            for member in archive.infolist():
                name = _member(member.filename)
                if member.file_size > 32 * 1024 * 1024 or member.flag_bits & 1:
                    raise ValueError("Unsafe compressed SVG member")
                path = compressed / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(member))
        candidate = staging / "candidate"
        report, _ = build_publication(
            assets=effective["assets"], references=discovery.references,
            canonical_by_source=conversion["canonicalByArchivePath"],
            army_artifact=source_plan["inputArtifact"],
            unavailable_assets=effective["unavailableAssets"],
            snapshot_index=load_snapshot_index(handoff.army),
            compressed_root=compressed, staging_static=candidate / "static",
        )
        manifest = candidate / PUBLICATION_MANIFEST
        manifest.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False)
                            + "\n", encoding="utf-8", newline="\n")
        if _pins(files) != before:
            raise ValueError("Symbol publication inputs changed during preparation")
        evidence = {
            "format": "InfinityDB symbol publication candidate", "formatVersion": 1,
            "status": "prepared", "inputFiles": before,
            "publicationManifestSha256": sha256_file(manifest),
        }
        (candidate / "candidate-evidence.json").write_text(
            json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n",
        )
        # Reserve a fresh directory exclusively; never replace an existing empty directory.
        output.mkdir()
        installed: list[Path] = []
        try:
            for child in sorted(candidate.iterdir()):
                destination = output / child.name
                child.replace(destination)
                installed.append(destination)
        except BaseException:
            for destination in reversed(installed):
                destination.replace(candidate / destination.name)
            output.rmdir()
            raise
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in fields(SymbolPublicationHandoff):
        parser.add_argument("--" + field.name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--static-symbols", type=Path, default=DEFAULT_STATIC_CONFIG)
    parser.add_argument("--legacy-armies", type=Path, default=DEFAULT_LEGACY_ARMIES)
    parser.add_argument("--font-aliases", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = prepare_symbol_publication(
            SymbolPublicationHandoff(**{field.name: getattr(args, field.name)
                                       for field in fields(SymbolPublicationHandoff)}),
            args.output, static_symbols=args.static_symbols, legacy_armies=args.legacy_armies,
            font_aliases=args.font_aliases,
        )
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Symbol publication candidate prepared: {report['summary']['publishedAssetCount']} SVGs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
