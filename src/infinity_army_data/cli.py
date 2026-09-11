from __future__ import annotations

import argparse
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from . import __version__
from .merge import load_sources, merge_sources, validate_master
from .merge import write_json as write_master
from .metadata import MetadataError, decode_metadata, load_metadata
from .normalize import normalize_master, validate_normalized
from .normalize import write_json as write_normalized

DEFAULT_RAW_DIRECTORY = Path("data/raw")


def snapshot_downloaded_on(source: Path) -> str | None:
    """Return the ISO download date encoded by a downloader-created ZIP name."""
    match = re.fullmatch(
        r"JSON (\d{8})(?:-\d{6}(?:-\d+)?)?\.zip", source.name, re.IGNORECASE
    )
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def latest_snapshot(directory: Path = DEFAULT_RAW_DIRECTORY) -> Path:
    """Return the newest raw ZIP snapshot, preferring file modification time."""
    archives = [path for path in directory.glob("*.zip") if path.is_file()]
    if not archives:
        raise ValueError(
            f"No ZIP snapshots found in {directory}; provide a source path or run the downloader"
        )
    return max(archives, key=lambda path: (path.stat().st_mtime_ns, path.name.casefold()))


def discover_metadata(source: Path, explicit: Path | None, disabled: bool) -> dict | None:
    """Find the optional API metadata beside a snapshot or within its ZIP."""
    if disabled:
        return None
    if explicit is not None:
        return load_metadata(explicit)
    sidecar = (source / "metadata.json") if source.is_dir() else source.with_name("metadata.json")
    if sidecar.is_file():
        return load_metadata(sidecar)
    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            members = [
                name for name in archive.namelist() if Path(name).name.lower() == "metadata.json"
            ]
            if len(members) > 1:
                raise MetadataError(
                    "Multiple metadata.json files in ZIP; use --metadata to select one"
                )
            if members:
                member = members[0]
                return decode_metadata(archive.read(member), member)
    return None


def _merge(
    source: Path,
    output: Path,
    *,
    compact: bool,
    verify: bool = True,
    metadata: dict | None = None,
) -> dict:
    sources, skipped = load_sources(source)
    master = merge_sources(sources)
    if downloaded_on := snapshot_downloaded_on(source):
        master["_meta"]["snapshotDownloadedOn"] = downloaded_on
    if metadata is not None:
        master["armyMetadata"] = metadata
    if verify:
        validate_master(master, sources)
    write_master(output, master, compact)

    meta = master["_meta"]
    print(f"Merged {meta['sourceFileCount']} source files -> {output}")
    print(
        f"Units: {meta['unitOccurrenceCount']} occurrences, "
        f"{meta['distinctUnitCount']} distinct IDs"
    )
    if metadata is not None:
        print(f"Army metadata: {metadata['sourceFile']}")
    print(f"Lossless verification: {'passed' if verify else 'skipped'}")
    if skipped:
        print("Skipped non-Army JSON files: " + ", ".join(skipped), file=sys.stderr)
    return master


def _normalize(master: dict, output: Path, report: Path, *, compact: bool) -> dict:
    normalized = normalize_master(master)
    validation = validate_normalized(normalized)
    normalized["_meta"]["validationPassed"] = True
    normalized["_meta"]["validationCheckCount"] = validation["checkCount"]
    write_normalized(output, normalized, compact=compact)
    write_normalized(report, validation, compact=False)

    meta = normalized["_meta"]
    print(f"Normalized -> {output}")
    print(f"Tables: {len(meta['tableCounts'])}")
    print(f"Validation checks: {validation['checkCount']} passed")
    print(f"Warnings: {meta['warningCount']}")
    print(f"Validation report: {report}")
    return normalized


def cmd_merge(args: argparse.Namespace) -> int:
    metadata = discover_metadata(args.source, args.metadata, args.no_metadata)
    _merge(
        args.source,
        args.output,
        compact=args.compact,
        verify=not args.no_verify,
        metadata=metadata,
    )
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    from .normalize import load_master

    master = load_master(args.input)
    report = args.report or args.output.with_name(args.output.stem + "-validation.json")
    _normalize(master, args.output, report, compact=args.compact)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    if args.source is None:
        args.source = latest_snapshot()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "master.json"
    normalized_path = output_dir / "normalized.json"
    report_path = output_dir / "normalized-validation.json"

    metadata = discover_metadata(args.source, args.metadata, args.no_metadata)
    master = _merge(
        args.source,
        master_path,
        compact=args.compact,
        verify=not args.no_verify,
        metadata=metadata,
    )
    _normalize(master, normalized_path, report_path, compact=args.compact)
    print(f"Build complete: {output_dir}")
    return 0


def add_data_commands(sub, *, build_handler=cmd_build) -> None:
    """Register ingestion commands for both the standalone tools and application CLI."""
    p_merge = sub.add_parser("merge", help="Merge raw Army JSON files into lossless master.json")
    p_merge.add_argument("source", type=Path, help="Source directory or ZIP archive")
    p_merge.add_argument("output", nargs="?", type=Path, default=Path("data/generated/master.json"))
    p_merge.add_argument("--compact", action="store_true", help="Minify JSON output")
    p_merge.add_argument(
        "--no-verify", action="store_true", help="Skip lossless reconstruction verification"
    )
    metadata_group = p_merge.add_mutually_exclusive_group()
    metadata_group.add_argument(
        "--metadata", type=Path, help="Supplementary Army API metadata JSON"
    )
    metadata_group.add_argument(
        "--no-metadata", action="store_true", help="Do not load metadata.json"
    )
    p_merge.set_defaults(func=cmd_merge)

    p_norm = sub.add_parser("normalize", help="Normalize master.json into relational-style tables")
    p_norm.add_argument("input", type=Path, help="master.json input")
    p_norm.add_argument(
        "output", nargs="?", type=Path, default=Path("data/generated/normalized.json")
    )
    p_norm.add_argument("--report", type=Path, default=None, help="Validation report output path")
    p_norm.add_argument("--compact", action="store_true", help="Minify normalized JSON")
    p_norm.set_defaults(func=cmd_normalize)

    p_build = sub.add_parser("build", help="Run merge, verification, normalization and validation")
    p_build.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=None,
        help="Source directory or ZIP archive (default: newest ZIP in data/raw)",
    )
    p_build.add_argument("--output-dir", type=Path, default=Path("data/generated"))
    p_build.add_argument("--compact", action="store_true", help="Minify generated data files")
    p_build.add_argument(
        "--no-verify", action="store_true", help="Skip lossless reconstruction verification"
    )
    metadata_group = p_build.add_mutually_exclusive_group()
    metadata_group.add_argument(
        "--metadata", type=Path, help="Supplementary Army API metadata JSON"
    )
    metadata_group.add_argument(
        "--no-metadata", action="store_true", help="Do not load metadata.json"
    )
    p_build.set_defaults(func=build_handler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infinity-army",
        description="Merge and normalize Infinity Army JSON datasets",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    add_data_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
