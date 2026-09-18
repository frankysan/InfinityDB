#!/usr/bin/env python3
"""Orchestrate one symbol build from an explicitly pinned Infinity Army snapshot.

The orchestrator never selects the newest available snapshot implicitly. Use
``--snapshot`` for an existing immutable Army ZIP or ``--fetch-snapshot`` for an
explicit network refresh. Later processing stages will be integrated here; the
current orchestration boundary pins Army provenance and performs raw symbol
discovery/acquisition from that exact snapshot.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

from infinity_db.snapshot_provenance import load_snapshot_manifest

try:
    from tools.download_army_json import (
        API_BASE_URL,
        acquire_army_snapshot,
        snapshot_source_revision_counts,
    )
    from tools.download_army_symbols import (
        DEFAULT_STATIC_CONFIG,
        acquire_symbol_snapshot,
        discover_symbol_source,
        print_discovery_summary,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from download_army_json import (
        API_BASE_URL,
        acquire_army_snapshot,
        snapshot_source_revision_counts,
    )
    from download_army_symbols import (
        DEFAULT_STATIC_CONFIG,
        acquire_symbol_snapshot,
        discover_symbol_source,
        print_discovery_summary,
    )


class PinnedArmySnapshot(NamedTuple):
    """Verified provenance needed by every stage of one symbol build."""

    archive: Path
    manifest: Path
    acquired_at: str
    language: str
    source_url: str
    document_count: int
    source_revisions: dict[str, int]


def resolve_army_snapshot(
    archive: Path,
    *,
    manifest_directory: Path,
    manifest: Path | None = None,
    expected_language: str | None = None,
) -> PinnedArmySnapshot:
    """Verify one Army archive and resolve its generated acquisition provenance."""
    if not archive.is_file():
        raise ValueError(f"Army snapshot does not exist: {archive}")

    manifest_path = manifest or manifest_directory / f"{archive.stem}.json"
    if not manifest_path.is_file():
        raise ValueError(
            "Army snapshot provenance is required; expected manifest at "
            f"{manifest_path}"
        )

    document = load_snapshot_manifest(manifest_path, archive=archive)
    snapshot = document["snapshot"]
    if snapshot["type"] != "army":
        raise ValueError(
            f"Snapshot manifest {manifest_path} describes {snapshot['type']!r}, not 'army'"
        )
    source = document["source"]
    language = source.get("language")
    if not isinstance(language, str) or not language:
        raise ValueError(f"Army snapshot manifest {manifest_path} has no source language")
    if expected_language is not None and language != expected_language:
        raise ValueError(
            f"Army snapshot language is {language!r}, expected {expected_language!r}"
        )

    revisions = snapshot_source_revision_counts(archive)
    expected_documents = sum(revisions.values()) + 1
    if snapshot["documentCount"] != expected_documents:
        raise ValueError(
            "Army snapshot provenance documentCount does not match archive contents: "
            f"{snapshot['documentCount']} != {expected_documents}"
        )

    return PinnedArmySnapshot(
        archive=archive,
        manifest=manifest_path,
        acquired_at=snapshot["acquiredAt"],
        language=language,
        source_url=source["url"],
        document_count=snapshot["documentCount"],
        source_revisions=revisions,
    )


def print_pinned_snapshot(snapshot: PinnedArmySnapshot) -> None:
    """Print the provenance that downstream stages are pinned to."""
    print(f"Pinned Army snapshot -> {snapshot.archive}")
    print(f"Army snapshot provenance -> {snapshot.manifest}")
    print(
        "Army source -> "
        f"{snapshot.source_url} | language {snapshot.language} | "
        f"acquired {snapshot.acquired_at} | {snapshot.document_count} documents"
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
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Downloaded {symbols.asset_count} symbols -> {symbols.archive}")
    print(f"Symbol snapshot provenance -> {symbols.snapshot_manifest}")
    print(f"Symbol build manifest -> {symbols.build_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
