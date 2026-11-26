"""Build InfinityDB's complete runtime set using a pinned Army ZIP/manifest pair.

This thin, MCP-invocable wrapper delegates to the existing offline CLI.
The optional recorded-source mode reuses the exact source identity in the
currently published runtime set; it does not choose a newer archive.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from infinity_db.build_provenance import (
    BUILD_PROVENANCE_KEY,
    _metadata,
    file_sha256,
    validate_build_record,
)
from infinity_db.cli import main as infinity_db_main


def recorded_source_paths(db_dir: Path) -> tuple[Path, Path]:
    """Select the exact original Army archive recorded in the published database."""
    metadata = _metadata(db_dir / "army.db")
    record = validate_build_record(metadata[BUILD_PROVENANCE_KEY], "army")
    source = record["manifest"]["source"]
    archive = Path("local/data/raw/army") / source["archiveName"]
    manifest = Path("local/data/manifests/snapshots") / f"{archive.stem}.json"
    if not archive.is_file() or file_sha256(archive) != source["archiveSha256"]:
        raise ValueError(f"Recorded Army source archive is missing or differs: {archive}")
    if not manifest.is_file():
        raise ValueError(f"Recorded Army source provenance is missing: {manifest}")
    return archive, manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--source", type=Path, help="Immutable Army ZIP")
    selection.add_argument(
        "--use-recorded-source", action="store_true",
        help="Reuse the current database's exact Army archive and provenance",
    )
    parser.add_argument("--manifest", type=Path, help="Matching v3 provenance")
    parser.add_argument(
        "--db-dir", type=Path, default=Path("data/generated"),
        help="Complete runtime set destination (default: data/generated)",
    )
    parser.add_argument("--with-unit-history", action="store_true",
                        help="Embed the accepted local Army history corpus")
    args = parser.parse_args(argv)
    if args.use_recorded_source:
        if args.manifest is not None:
            parser.error("--manifest cannot be combined with --use-recorded-source")
        try:
            source, manifest = recorded_source_paths(args.db_dir)
        except (KeyError, ValueError) as exc:
            parser.error(str(exc))
    else:
        if args.manifest is None:
            parser.error("--manifest is required with --source")
        source, manifest = args.source, args.manifest
    return infinity_db_main([
        "build", str(source),
        "--snapshot-manifest", str(manifest),
        "--db-dir", str(args.db_dir),
        "--compact",
        *(["--with-unit-history"] if args.with_unit_history else []),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
