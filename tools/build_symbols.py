#!/usr/bin/env python3
"""Orchestrate one symbol build from an explicitly pinned Infinity Army snapshot.

The orchestrator never selects the newest available snapshot implicitly. Use
``--snapshot`` for an existing immutable Army ZIP or ``--fetch-snapshot`` for an
explicit network refresh. The same entrypoint can stop at verified checkpoints
or resume an existing build without reacquiring immutable inputs. It pins Army
provenance, resolves one immutable raw symbol snapshot, materializes verified work
files, runs structural/font audits, performs exact-first visual deduplication,
converts canonical active text to paths, compresses the complete canonical set,
and transactionally publishes the final asset tree and browser mappings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, NamedTuple

from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
from infinity_db.symbol_manifest import load_symbol_manifest

try:
    from tools.download_army_json import (
        API_BASE_URL,
        ArmySnapshotResult,
        acquire_army_snapshot,
        resolve_army_snapshot,
    )
    from tools.download_army_symbols import (
        DEFAULT_OVERRIDE_ROOT,
        DEFAULT_STATIC_CONFIG,
        acquire_symbol_snapshot,
        discover_symbol_source,
        print_discovery_summary,
    )
    from tools.reorganize_symbols import publish_symbols
    from tools.symbol_work import (
        audit_symbol_fonts,
        audit_symbol_work,
        compress_symbol_work,
        convert_symbol_text,
        detect_symbol_duplicates,
        load_materialized_symbol_work,
        materialize_symbol_archive,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from download_army_json import (
        API_BASE_URL,
        ArmySnapshotResult,
        acquire_army_snapshot,
        resolve_army_snapshot,
    )
    from download_army_symbols import (
        DEFAULT_OVERRIDE_ROOT,
        DEFAULT_STATIC_CONFIG,
        acquire_symbol_snapshot,
        discover_symbol_source,
        print_discovery_summary,
    )
    from reorganize_symbols import publish_symbols
    from symbol_work import (
        audit_symbol_fonts,
        audit_symbol_work,
        compress_symbol_work,
        convert_symbol_text,
        detect_symbol_duplicates,
        load_materialized_symbol_work,
        materialize_symbol_archive,
    )


def print_pinned_snapshot(snapshot: ArmySnapshotResult) -> None:
    """Print the provenance that downstream stages are pinned to."""
    print(f"Pinned Army snapshot -> {snapshot.archive}")
    print(f"Army snapshot provenance -> {snapshot.manifest}")
    print(
        "Army source -> "
        f"{snapshot.source_url} | language {snapshot.language} | "
        f"acquired {snapshot.acquired_at.isoformat(timespec='seconds')} | "
        f"{snapshot.document_count} documents"
    )
    print(
        "Army source revisions -> "
        + ", ".join(
            f"{version}: {count}"
            for version, count in snapshot.source_revisions.items()
        )
    )


STAGES = (
    "snapshot",
    "acquisition",
    "materialization",
    "preflight",
    "font-audit",
    "deduplication",
    "text-conversion",
    "compression",
    "publication",
)
STAGE_VERSIONS = {
    "acquisition": 2,
    "materialization": 2,
    "preflight": 3,
    "font-audit": 4,
    "deduplication": 5,
    "text-conversion": 6,
    "compression": 7,
    "publication": 8,
}


class ResumedSymbolState(NamedTuple):
    archive: Path
    snapshot_manifest: Path
    build_manifest: Path
    asset_count: int


def _stage_index(stage: str) -> int:
    return STAGES.index(stage)


def _stop_after(stage: str, requested: str) -> bool:
    return _stage_index(stage) >= _stage_index(requested)


def _resolve_bound_path(
    record: dict[str, Any],
    *,
    project_root: Path,
    fallback: Path | None = None,
    explicit: Path | None = None,
) -> Path:
    """Resolve one SHA-bound artifact from explicit, portable, then fallback paths."""
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    portable = record.get("path")
    if isinstance(portable, str):
        candidates.append(project_root / Path(portable))
    if fallback is not None:
        candidates.append(fallback)

    for candidate in candidates:
        if not candidate.is_file():
            continue
        actual = sha256_file(candidate)
        if actual != record["sha256"]:
            if explicit is not None and candidate == explicit:
                raise ValueError(
                    f"Artifact SHA-256 mismatch for {candidate}: "
                    f"expected {record['sha256']}, got {actual}"
                )
            continue
        return candidate
    raise ValueError(
        f"Could not resolve pinned artifact {record['name']!r}; "
        "provide the original Army snapshot with --snapshot when resuming an "
        "external build"
    )


def _resolve_report_path(
    record: dict[str, Any],
    *,
    project_root: Path,
    report_root: Path,
) -> Path:
    return _resolve_bound_path(
        record,
        project_root=project_root,
        fallback=report_root / record["name"],
    )


def _validate_resume_army_pin(
    pinned: ArmySnapshotResult,
    build_document: dict[str, Any],
) -> None:
    snapshot = build_document["snapshot"]
    artifact = snapshot["armyArtifact"]
    source = snapshot["armySource"]
    if pinned.archive.name != artifact["name"] or sha256_file(pinned.archive) != artifact["sha256"]:
        raise ValueError("Resumed Army snapshot does not match army-symbol-build.json")
    expected = {
        "language": pinned.language,
        "url": pinned.source_url,
        "documentCount": pinned.document_count,
        "sourceRevisions": pinned.source_revisions,
        "acquiredAt": pinned.acquired_at.isoformat(timespec="seconds"),
    }
    if source != expected:
        raise ValueError("Resumed Army snapshot provenance does not match army-symbol-build.json")


def _resume_state(
    *,
    build_manifest: Path,
    manifest_directory: Path,
    army_destination: Path,
    symbol_destination: Path,
    snapshot: Path | None,
    snapshot_manifest: Path | None,
    expected_language: str | None,
    project_root: Path,
) -> tuple[ArmySnapshotResult, ResumedSymbolState, dict[str, Any]]:
    if not build_manifest.is_file():
        raise ValueError(f"Cannot resume: build manifest is missing: {build_manifest}")
    document = load_symbol_manifest(build_manifest)
    army_record = document["snapshot"]["armyArtifact"]
    army_archive = _resolve_bound_path(
        army_record,
        project_root=project_root,
        fallback=army_destination / army_record["name"],
        explicit=snapshot,
    )
    army_manifest = snapshot_manifest or manifest_directory / f"{army_archive.stem}.json"
    pinned = resolve_army_snapshot(
        army_archive,
        manifest_directory=manifest_directory,
        manifest=army_manifest,
        expected_language=expected_language or document["snapshot"]["armySource"]["language"],
    )
    _validate_resume_army_pin(pinned, document)

    symbol_record = document["snapshot"]["symbolArtifact"]
    symbol_archive = _resolve_bound_path(
        symbol_record,
        project_root=project_root,
        fallback=symbol_destination / symbol_record["name"],
    )
    symbol_manifest = manifest_directory / f"{symbol_archive.stem}.json"
    provenance = load_snapshot_manifest(symbol_manifest, archive=symbol_archive)
    if provenance["snapshot"]["type"] != "symbols":
        raise ValueError(f"Pinned symbol provenance is not a symbol snapshot: {symbol_manifest}")
    input_artifact = provenance.get("inputArtifact")
    if not isinstance(input_artifact, dict) or (
        input_artifact.get("name") != army_record["name"]
        or input_artifact.get("sha256") != army_record["sha256"]
    ):
        raise ValueError("Pinned symbol provenance Army input does not match build state")

    return (
        pinned,
        ResumedSymbolState(
            archive=symbol_archive,
            snapshot_manifest=symbol_manifest,
            build_manifest=build_manifest,
            asset_count=len(document["assets"]),
        ),
        document,
    )


def _print_checkpoint(
    stage: str,
    *,
    build_manifest: Path | None = None,
    work_root: Path | None = None,
) -> None:
    print(f"Checkpoint reached -> {stage}")
    if build_manifest is not None and build_manifest.is_file():
        document = load_symbol_manifest(build_manifest)
        artifact = document["snapshot"]["symbolArtifact"]
        print(f"Build state -> version {document['formatVersion']} | {build_manifest}")
        print(f"Symbol artifact -> {artifact['name']} | sha256 {artifact['sha256']}")
    if work_root is not None:
        print(f"Symbol work root -> {work_root}")


def _existing_stage_status(document: dict[str, Any], key: str) -> str | None:
    processing = document.get("processing")
    if not isinstance(processing, dict):
        return None
    record = processing.get(key)
    if not isinstance(record, dict):
        return None
    status = record.get("status")
    return status if isinstance(status, str) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_mode = parser.add_mutually_exclusive_group()
    source_mode.add_argument(
        "--snapshot",
        type=Path,
        help=(
            "Existing immutable Army JSON ZIP to pin for a new build, or the "
            "original external Army ZIP when --resume cannot resolve it from build state"
        ),
    )
    source_mode.add_argument(
        "--fetch-snapshot",
        action="store_true",
        help="Explicitly download and pin a fresh Army snapshot before symbol acquisition",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume the existing data/manifests/army-symbol-build.json without "
            "reacquiring Army or symbol snapshots"
        ),
    )
    parser.add_argument(
        "--stop-after",
        choices=STAGES,
        default="publication",
        help="Stop after the named verified pipeline checkpoint (default: publication)",
    )
    parser.add_argument(
        "--snapshot-manifest",
        type=Path,
        help="Army snapshot provenance manifest (defaults to data/manifests/snapshots/<name>.json)",
    )
    parser.add_argument(
        "--language",
        help="Expected/fetched Army language (fetch default: en)",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="InfinityDB data root (default: data)",
    )
    parser.add_argument(
        "--static-symbols",
        type=Path,
        default=DEFAULT_STATIC_CONFIG,
        help="Maintained static-symbol declarations",
    )
    parser.add_argument(
        "--image-overrides",
        type=Path,
        default=DEFAULT_OVERRIDE_ROOT,
        help="Local SVG override root (default: image_overrides)",
    )
    parser.add_argument(
        "--refresh-symbols",
        action="store_true",
        help="Bypass the prior immutable symbol cache; local overrides still take precedence",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Seconds to wait between symbol downloads (default: 0.2)",
    )
    parser.add_argument(
        "--snapshot-only",
        action="store_true",
        help="Legacy alias for --stop-after snapshot",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Parallel jobs for duplicate rendering and later processing stages (default: 4)",
    )
    parser.add_argument(
        "--text-converter",
        choices=("inkscape", "inkscape-shell", "usvg", "auto"),
        default="inkscape-shell",
        help=(
            "Text-to-path backend for canonical active-text assets "
            "(default: inkscape-shell)"
        ),
    )
    parser.add_argument(
        "--duplicate-render-size",
        type=int,
        default=512,
        help="Raster width for visual duplicate detection (default: 512)",
    )
    parser.add_argument(
        "--duplicate-renderer",
        choices=("resvg", "inkscape", "auto"),
        default="resvg",
        help="Renderer for visual duplicate detection (default: resvg)",
    )
    parser.add_argument(
        "--compression-renderer",
        choices=("resvg", "inkscape", "auto"),
        default="resvg",
        help="Renderer for compression validation (default: resvg)",
    )
    parser.add_argument(
        "--static-root",
        type=Path,
        default=Path("src/infinity_db/web/static"),
        help="Application static root for final symbol publication",
    )
    args = parser.parse_args(argv)

    if args.delay < 0:
        parser.error("--delay must not be negative")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if args.duplicate_render_size < 1:
        parser.error("--duplicate-render-size must be at least 1")
    if args.fetch_snapshot and args.snapshot_manifest is not None:
        parser.error("--snapshot-manifest is only valid with --snapshot")
    if args.snapshot_manifest is not None and args.snapshot is None:
        parser.error("--snapshot-manifest requires --snapshot")
    if args.resume and args.fetch_snapshot:
        parser.error("--resume cannot be combined with --fetch-snapshot")
    if args.resume and args.refresh_symbols:
        parser.error("--resume cannot be combined with --refresh-symbols")
    if args.resume and args.snapshot_only:
        parser.error("--snapshot-only cannot be combined with --resume")
    if not args.resume and args.snapshot is None and not args.fetch_snapshot:
        parser.error("a new build requires --snapshot or --fetch-snapshot")

    stop_after = "snapshot" if args.snapshot_only else args.stop_after
    if args.resume and stop_after == "snapshot":
        parser.error("--resume starts from symbol build state and cannot stop at snapshot")

    manifest_directory = args.data_root / "manifests" / "snapshots"
    army_destination = args.data_root / "raw"
    symbol_destination = args.data_root / "raw" / "symbols"
    build_manifest = args.data_root / "manifests" / "army-symbol-build.json"
    symbol_work = args.data_root / "work" / "symbols"
    symbol_reports = args.data_root / "reports" / "symbols"
    project_root = Path.cwd()

    try:
        if args.resume:
            pinned, symbols, document = _resume_state(
                build_manifest=build_manifest,
                manifest_directory=manifest_directory,
                army_destination=army_destination,
                symbol_destination=symbol_destination,
                snapshot=args.snapshot,
                snapshot_manifest=args.snapshot_manifest,
                expected_language=args.language,
                project_root=project_root,
            )
            print_pinned_snapshot(pinned)
            print(
                f"Resuming symbol build -> version {document['formatVersion']} | "
                f"{symbols.build_manifest}"
            )
            print(f"Pinned symbol snapshot -> {symbols.archive}")
            print(f"Symbol snapshot provenance -> {symbols.snapshot_manifest}")
            current = document
            current_version = document["formatVersion"]
            if _stop_after("acquisition", stop_after):
                _print_checkpoint("acquisition", build_manifest=symbols.build_manifest)
                return 0
        else:
            if args.fetch_snapshot:
                language = args.language or "en"
                acquired = acquire_army_snapshot(
                    army_destination,
                    manifest_directory,
                    language=language,
                    api_base_url=API_BASE_URL,
                )
                pinned = resolve_army_snapshot(
                    acquired.archive,
                    manifest_directory=manifest_directory,
                    manifest=acquired.manifest,
                    expected_language=language,
                )
            else:
                assert args.snapshot is not None
                pinned = resolve_army_snapshot(
                    args.snapshot,
                    manifest_directory=manifest_directory,
                    manifest=args.snapshot_manifest,
                    expected_language=args.language,
                )

            print_pinned_snapshot(pinned)
            if _stop_after("snapshot", stop_after):
                _print_checkpoint("snapshot")
                return 0

            discovery = discover_symbol_source(
                pinned.archive,
                static_symbols_path=args.static_symbols,
            )
            if discovery.source_document_count != pinned.document_count:
                raise ValueError(
                    "Symbol discovery source-document count does not match pinned Army "
                    f"provenance: {discovery.source_document_count} != {pinned.document_count}"
                )
            print_discovery_summary(discovery)

            symbols = acquire_symbol_snapshot(
                pinned.archive,
                symbol_destination,
                manifest_directory,
                build_manifest,
                static_symbols_path=args.static_symbols,
                delay=args.delay,
                discovery=discovery,
                progress=print,
                army_snapshot=pinned,
                override_root=args.image_overrides,
                refresh_symbols=args.refresh_symbols,
            )
            if _stop_after("acquisition", stop_after):
                _print_checkpoint("acquisition", build_manifest=symbols.build_manifest)
                print(f"Resolved {symbols.asset_count} symbols -> {symbols.archive}")
                print(f"Symbol snapshot provenance -> {symbols.snapshot_manifest}")
                return 0
            current = {}
            current_version = 2

        if args.resume:
            try:
                materialized = load_materialized_symbol_work(
                    symbols.archive,
                    symbols.snapshot_manifest,
                    symbols.build_manifest,
                    symbol_work,
                )
                print(f"Verified materialized symbol work -> {materialized.raw_root}")
            except ValueError:
                if current_version > STAGE_VERSIONS["materialization"]:
                    raise
                materialized = materialize_symbol_archive(
                    symbols.archive,
                    symbols.snapshot_manifest,
                    symbols.build_manifest,
                    symbol_work,
                )
                print(f"Materialized symbol work -> {materialized.raw_root}")
        else:
            materialized = materialize_symbol_archive(
                symbols.archive,
                symbols.snapshot_manifest,
                symbols.build_manifest,
                symbol_work,
            )
            print(f"Materialized symbol work -> {materialized.raw_root}")

        if _stop_after("materialization", stop_after):
            _print_checkpoint(
                "materialization",
                build_manifest=symbols.build_manifest,
                work_root=materialized.work_root,
            )
            return 0

        preflight_status = _existing_stage_status(current, "svgPreflight")
        if current_version < 3 or (current_version == 3 and preflight_status != "passed"):
            preflight = audit_symbol_work(
                materialized,
                archive=symbols.archive,
                build_manifest_path=symbols.build_manifest,
                reports_base=symbol_reports,
                project_root=project_root,
            )
            print(
                "SVG preflight -> "
                f"{preflight.summary['svgCount']} SVGs | "
                f"parse errors {preflight.summary['parseErrorCount']} | "
                f"active text {preflight.summary['activeTextAssetCount']} | "
                f"declared fonts {preflight.summary['uniqueDeclaredFontCount']}"
            )
            print(f"SVG preflight report -> {preflight.report}")
            if preflight.status != "passed":
                raise ValueError(
                    "SVG preflight failed; inspect the generated report before processing"
                )
            current_version = 3
            preflight_status = "passed"
        elif preflight_status == "passed":
            print("SVG preflight -> existing passed state verified")
        else:
            raise ValueError("Existing SVG preflight state is not passed")
        if _stop_after("preflight", stop_after):
            _print_checkpoint(
                "preflight",
                build_manifest=symbols.build_manifest,
                work_root=materialized.work_root,
            )
            return 0

        symbol_sha = (
            current["snapshot"]["symbolArtifact"]["sha256"]
            if current
            else ""
        )
        report_root = symbol_reports / (
            f"{symbols.archive.stem}--{symbol_sha[:12]}"
        )
        font_status = _existing_stage_status(current, "fontAudit")
        if current_version == 3:
            font_audit = audit_symbol_fonts(
                materialized,
                archive=symbols.archive,
                build_manifest_path=symbols.build_manifest,
                reports_base=symbol_reports,
                project_root=project_root,
            )
            print(
                "Font audit -> "
                f"available assets {font_audit.summary['fontAvailableAssetCount']} | "
                f"missing assets {font_audit.summary['fontMissingAssetCount']} | "
                f"aliases {font_audit.summary['normalizedAliasReferenceCount']} | "
                f"unused declarations {font_audit.summary['unusedDeclarationCount']}"
            )
            print(f"Font audit report -> {font_audit.report}")
            if font_audit.status != "passed":
                raise ValueError(
                    "Font audit failed; install/resolve required fonts before processing"
                )
            font_report = font_audit.report
            current_version = 4
            font_status = "passed"
        elif current_version >= 4 and font_status == "passed":
            font_record = current["processing"]["fontAudit"]["report"]
            font_report = _resolve_report_path(
                font_record,
                project_root=project_root,
                report_root=report_root,
            )
            print(f"Font audit -> existing passed state verified | {font_report}")
        else:
            raise ValueError(
                "Existing font-audit state is not resumable; rerun from a clean "
                "version-3 checkpoint after resolving the reported fonts"
            )
        if _stop_after("font-audit", stop_after):
            _print_checkpoint(
                "font-audit",
                build_manifest=symbols.build_manifest,
                work_root=materialized.work_root,
            )
            return 0

        duplicate_status = _existing_stage_status(current, "duplicateDetection")
        if current_version == 4:
            duplicates = detect_symbol_duplicates(
                materialized,
                archive=symbols.archive,
                build_manifest_path=symbols.build_manifest,
                font_report=font_report,
                reports_base=symbol_reports,
                project_root=project_root,
                render_size=args.duplicate_render_size,
                jobs=args.jobs,
                renderer=args.duplicate_renderer,
            )
            print(
                "Duplicate detection -> "
                f"canonical {duplicates.summary['canonicalAssetCount']} | "
                f"redundant {duplicates.summary['redundantAssetCount']} | "
                f"exact groups {duplicates.summary['exactGroupCount']} | "
                f"visual groups {duplicates.summary['visualGroupCount']} | "
                f"render errors {duplicates.summary['renderErrorCount']}"
            )
            source_bytes = duplicates.summary["sourceAssetBytes"]
            canonical_bytes = duplicates.summary["canonicalAssetBytes"]
            reclaimed_bytes = duplicates.summary["reclaimedAssetBytes"]
            reduction_percent = (
                reclaimed_bytes * 100.0 / source_bytes if source_bytes else 0.0
            )
            print(
                "Symbol set size -> "
                f"{source_bytes:,} bytes before | "
                f"{canonical_bytes:,} bytes after | "
                f"{reclaimed_bytes:,} bytes saved ({reduction_percent:.2f}%)"
            )
            print(f"Duplicate report -> {duplicates.groups_report}")
            current_version = 5
            duplicate_status = "passed"
        elif current_version >= 5 and duplicate_status == "passed":
            print("Duplicate detection -> existing passed state verified")
        else:
            raise ValueError("Existing duplicate-detection state is not passed")
        if _stop_after("deduplication", stop_after):
            _print_checkpoint(
                "deduplication",
                build_manifest=symbols.build_manifest,
                work_root=materialized.work_root,
            )
            return 0

        conversion_status = _existing_stage_status(current, "textConversion")
        if current_version == 5 or (current_version == 6 and conversion_status != "passed"):
            conversion = convert_symbol_text(
                materialized,
                archive=symbols.archive,
                build_manifest_path=symbols.build_manifest,
                font_report=font_report,
                reports_base=symbol_reports,
                project_root=project_root,
                jobs=args.jobs,
                text_converter=args.text_converter,
            )
            version_suffix = (
                f" ({conversion.converter_version})"
                if conversion.converter_version
                else ""
            )
            print(
                "Text conversion -> "
                f"{conversion.summary['convertedAssetCount']} converted | "
                f"{conversion.summary['carriedForwardAssetCount']} unchanged | "
                f"{conversion.summary['failedAssetCount']} failed"
            )
            print(f"Text converter -> {conversion.converter}{version_suffix}")
            print(f"Text conversion report -> {conversion.report}")
            if conversion.status != "passed":
                raise ValueError(
                    "Text conversion failed; verified source assets remain available "
                    "and canonical output was not replaced"
                )
            print(f"Canonical symbol work -> {conversion.canonical_root}")
            current_version = 6
            conversion_status = "passed"
        elif current_version >= 6 and conversion_status == "passed":
            print("Text conversion -> existing passed state verified")
        else:
            raise ValueError("Existing text-conversion state is not passed")
        if _stop_after("text-conversion", stop_after):
            _print_checkpoint(
                "text-conversion",
                build_manifest=symbols.build_manifest,
                work_root=materialized.work_root,
            )
            return 0

        compression_status = _existing_stage_status(current, "compression")
        if current_version == 6:
            compression = compress_symbol_work(
                materialized,
                archive=symbols.archive,
                build_manifest_path=symbols.build_manifest,
                reports_base=symbol_reports,
                project_root=project_root,
                jobs=args.jobs,
                renderer=args.compression_renderer,
            )
            compression_source = compression.summary["sourceBytes"]
            compression_output = compression.summary["outputBytes"]
            compression_saved = compression.summary["reclaimedBytes"]
            compression_percent = (
                compression_saved * 100.0 / compression_source
                if compression_source
                else 0.0
            )
            renderer_suffix = (
                f" ({compression.renderer_version})"
                if compression.renderer_version
                else ""
            )
            print(
                "Compression -> "
                f"{compression.summary['compressedAssetCount']} smaller | "
                f"{compression.summary['retainedAssetCount']} retained | "
                f"{compression_source:,} -> {compression_output:,} bytes "
                f"({compression_percent:.2f}% saved)"
            )
            print(f"Compression renderer -> {compression.renderer}{renderer_suffix}")
            print(f"Compression report -> {compression.report}")
            print(f"Compressed symbol work -> {compression.compressed_root}")
            current_version = 7
            compression_status = "passed"
        elif current_version >= 7 and compression_status == "passed":
            print("Compression -> existing passed state verified")
        else:
            raise ValueError("Existing compression state is not passed")
        if _stop_after("compression", stop_after):
            _print_checkpoint(
                "compression",
                build_manifest=symbols.build_manifest,
                work_root=materialized.work_root,
            )
            return 0

        publication_status = _existing_stage_status(current, "publication")
        if current_version == 7:
            publication = publish_symbols(
                army_snapshot=pinned.archive,
                build_manifest_path=symbols.build_manifest,
                work_root=materialized.work_root,
                reports_base=symbol_reports,
                static_root=args.static_root,
                project_root=project_root,
            )
            print(
                "Publication -> "
                f"{publication.summary['publishedAssetCount']} canonical SVGs | "
                f"{publication.summary['unitMappingCount']} unit mappings | "
                f"{publication.summary['factionMappingCount']} faction mappings | "
                f"{publication.summary['staticMappingCount']} static mappings"
            )
            print(f"Published symbol root -> {publication.static_root}")
            print(f"Publication mapping -> {publication.mapping_report}")
            current_version = 8
            publication_status = "passed"
        elif current_version == 8 and publication_status == "passed":
            print("Publication -> existing passed state verified")
        else:
            raise ValueError("Existing publication state is not passed")

        _print_checkpoint(
            "publication",
            build_manifest=symbols.build_manifest,
            work_root=materialized.work_root,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Resolved {symbols.asset_count} symbols -> {symbols.archive}")
    print(f"Symbol snapshot provenance -> {symbols.snapshot_manifest}")
    print(f"Symbol build manifest -> {symbols.build_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
