#!/usr/bin/env python3
"""Orchestrate one symbol build from an explicitly pinned Infinity Army snapshot.

The orchestrator never selects the newest available snapshot implicitly. Use
``--snapshot`` for an existing immutable Army ZIP or ``--fetch-snapshot`` for an
explicit network refresh. Later processing stages will be integrated here; the
current orchestration boundary pins Army provenance, resolves one immutable raw
symbol snapshot, materializes verified work files, runs structural SVG preflight,
and audits effective fonts against the installed font environment.
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
    from tools.symbol_work import (
        audit_symbol_fonts,
        audit_symbol_work,
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
    from symbol_work import audit_symbol_fonts, audit_symbol_work, materialize_symbol_archive


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
    args = parser.parse_args(argv)

    if args.delay < 0:
        parser.error("--delay must not be negative")
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
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Resolved {symbols.asset_count} symbols -> {symbols.archive}")
    print(f"Symbol snapshot provenance -> {symbols.snapshot_manifest}")
    print(f"Symbol build manifest -> {symbols.build_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
