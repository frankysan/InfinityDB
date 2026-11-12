"""Export source-pinned override lookup paths for standalone SVG processing.

The consumer supplies the *separate* approved override lookup path for
each source URL; these paths must not be guessed from the raw archive paths.
No SVG or override artwork is read or distributed by this exporter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.export_symbol_source_plan import build_source_plan, write_source_plan
from tools.symbol_source import (
    DEFAULT_LEGACY_ARMIES,
    DEFAULT_STATIC_CONFIG,
    discover_symbol_source,
    override_resolution_plan,
)

FORMAT = "InfinityDB symbol override lookup plan"
VERSION = 1


def _canonical(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def build_override_lookup_plan(
    army_archive: Path,
    army_manifest: Path,
    source_plan: dict[str, Any],
    *,
    static_symbols_path: Path = DEFAULT_STATIC_CONFIG,
    legacy_armies_path: Path | None = DEFAULT_LEGACY_ARMIES,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Require the source plan to match current discovery before exporting lookups."""
    root = project_root or Path.cwd()
    expected = build_source_plan(
        army_archive, army_manifest,
        static_symbols_path=static_symbols_path,
        legacy_armies_path=legacy_armies_path,
        project_root=root,
    )
    if expected != source_plan:
        raise ValueError("Raw source plan differs from current authoritative Army discovery")
    discovery = discover_symbol_source(
        army_archive, static_symbols_path=static_symbols_path,
        legacy_armies_path=legacy_armies_path, project_root=root,
    )
    resolution = override_resolution_plan(discovery)
    if set(resolution.override_paths) != {row["url"] for row in source_plan["requests"]}:
        raise ValueError("Override lookup URLs differ from authoritative source requests")
    return {
        "format": FORMAT,
        "formatVersion": VERSION,
        "sourcePlanSha256": hashlib.sha256(_canonical(source_plan)).hexdigest(),
        "lookups": [
            {"url": url, "overridePath": resolution.override_paths[url]}
            for url in sorted(resolution.override_paths)
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--static-symbols", type=Path, default=DEFAULT_STATIC_CONFIG)
    parser.add_argument("--legacy-armies", type=Path, default=DEFAULT_LEGACY_ARMIES)
    args = parser.parse_args(argv)
    try:
        source_plan = json.loads(args.source_plan.read_text(encoding="utf-8"))
        lookups = build_override_lookup_plan(
            args.snapshot, args.manifest, source_plan,
            static_symbols_path=args.static_symbols,
            legacy_armies_path=args.legacy_armies,
        )
        result = write_source_plan(args.output, lookups)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Override lookups -> {result} ({len(lookups['lookups'])} URLs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
