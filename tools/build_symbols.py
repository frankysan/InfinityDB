#!/usr/bin/env python3
"""Orchestrate one symbol build from an explicitly pinned Infinity Army snapshot.

The orchestrator never selects the newest available snapshot implicitly. Use
``--snapshot`` for an existing immutable Army ZIP or ``--fetch-snapshot`` for an
explicit network refresh. Later processing stages will be integrated here; the
current orchestration boundary pins Army provenance, resolves one immutable raw
symbol snapshot, materializes verified work files, runs structural SVG preflight,
audits effective fonts against the installed font environment, performs
exact-first visual duplicate detection with a persisted canonical mapping, and
converts active text on canonical assets into paths, compresses the complete
canonical set through display-aware validation, and transactionally publishes the final
asset tree and browser mappings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--snapshot",
        type=Path,
        help="Existing immutable Army JSON ZIP to pin for this build",
    )
    mode.add_argument(
        "--fetch-snapshot",
        action="store_true",
        help="Explicitly download and pin a fresh Army snapshot before symbol acquisition",
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
        help="Resolve/fetch and report the pinned Army snapshot without acquiring symbols",
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

    manifest_directory = args.data_root / "manifests" / "snapshots"
    army_destination = args.data_root / "raw"
    symbol_destination = args.data_root / "raw" / "symbols"
    build_manifest = args.data_root / "manifests" / "army-symbol-build.json"
    symbol_work = args.data_root / "work" / "symbols"
    symbol_reports = args.data_root / "reports" / "symbols"

    try:
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
        if args.snapshot_only:
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

        materialized = materialize_symbol_archive(
            symbols.archive,
            symbols.snapshot_manifest,
            symbols.build_manifest,
            symbol_work,
        )
        print(f"Materialized symbol work -> {materialized.raw_root}")
        preflight = audit_symbol_work(
            materialized,
            archive=symbols.archive,
            build_manifest_path=symbols.build_manifest,
            reports_base=symbol_reports,
            project_root=Path.cwd(),
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

        font_audit = audit_symbol_fonts(
            materialized,
            archive=symbols.archive,
            build_manifest_path=symbols.build_manifest,
            reports_base=symbol_reports,
            project_root=Path.cwd(),
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

        duplicates = detect_symbol_duplicates(
            materialized,
            archive=symbols.archive,
            build_manifest_path=symbols.build_manifest,
            font_report=font_audit.report,
            reports_base=symbol_reports,
            project_root=Path.cwd(),
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

        conversion = convert_symbol_text(
            materialized,
            archive=symbols.archive,
            build_manifest_path=symbols.build_manifest,
            font_report=font_audit.report,
            reports_base=symbol_reports,
            project_root=Path.cwd(),
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

        compression = compress_symbol_work(
            materialized,
            archive=symbols.archive,
            build_manifest_path=symbols.build_manifest,
            reports_base=symbol_reports,
            project_root=Path.cwd(),
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

        publication = publish_symbols(
            army_snapshot=pinned.archive,
            build_manifest_path=symbols.build_manifest,
            work_root=materialized.work_root,
            reports_base=symbol_reports,
            static_root=args.static_root,
            project_root=Path.cwd(),
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
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Resolved {symbols.asset_count} symbols -> {symbols.archive}")
    print(f"Symbol snapshot provenance -> {symbols.snapshot_manifest}")
    print(f"Symbol build manifest -> {symbols.build_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
