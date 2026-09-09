from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .merge import load_sources, merge_sources, validate_master, write_json as write_master
from .normalize import normalize_master, validate_normalized, write_json as write_normalized


def _merge(source: Path, output: Path, *, compact: bool, verify: bool = True) -> dict:
    sources, skipped = load_sources(source)
    master = merge_sources(sources)
    if verify:
        validate_master(master, sources)
    write_master(output, master, compact)

    meta = master["_meta"]
    print(f"Merged {meta['sourceFileCount']} source files -> {output}")
    print(
        f"Units: {meta['unitOccurrenceCount']} occurrences, "
        f"{meta['distinctUnitCount']} distinct IDs"
    )
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
    _merge(args.source, args.output, compact=args.compact, verify=not args.no_verify)
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    from .normalize import load_master

    master = load_master(args.input)
    report = args.report or args.output.with_name(args.output.stem + "-validation.json")
    _normalize(master, args.output, report, compact=args.compact)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "master.json"
    normalized_path = output_dir / "normalized.json"
    report_path = output_dir / "normalized-validation.json"

    master = _merge(
        args.source,
        master_path,
        compact=args.compact,
        verify=not args.no_verify,
    )
    _normalize(master, normalized_path, report_path, compact=args.compact)
    print(f"Build complete: {output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infinity-army",
        description="Merge and normalize Infinity Army JSON datasets",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_merge = sub.add_parser("merge", help="Merge raw Army JSON files into lossless master.json")
    p_merge.add_argument("source", type=Path, help="Source directory or ZIP archive")
    p_merge.add_argument("output", nargs="?", type=Path, default=Path("data/generated/master.json"))
    p_merge.add_argument("--compact", action="store_true", help="Minify JSON output")
    p_merge.add_argument("--no-verify", action="store_true", help="Skip lossless reconstruction verification")
    p_merge.set_defaults(func=cmd_merge)

    p_norm = sub.add_parser("normalize", help="Normalize master.json into relational-style tables")
    p_norm.add_argument("input", type=Path, help="master.json input")
    p_norm.add_argument("output", nargs="?", type=Path, default=Path("data/generated/normalized.json"))
    p_norm.add_argument("--report", type=Path, default=None, help="Validation report output path")
    p_norm.add_argument("--compact", action="store_true", help="Minify normalized JSON")
    p_norm.set_defaults(func=cmd_normalize)

    p_build = sub.add_parser("build", help="Run merge, verification, normalization and validation")
    p_build.add_argument("source", type=Path, help="Source directory or ZIP archive")
    p_build.add_argument("--output-dir", type=Path, default=Path("data/generated"))
    p_build.add_argument("--compact", action="store_true", help="Minify generated data files")
    p_build.add_argument("--no-verify", action="store_true", help="Skip lossless reconstruction verification")
    p_build.set_defaults(func=cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
