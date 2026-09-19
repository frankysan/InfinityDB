"""Application commands built on the existing data ingestion tools."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from infinity_army_data.cli import add_data_commands
from infinity_army_data.cli import cmd_build as build_dataset
from infinity_army_data.cli import cmd_normalize as normalize_dataset

from . import __version__
from .curated import load_curated_directory, load_curated_document
from .database import export_database, raw_database_path
from .display_identities import display_identity_metadata, load_display_identity_curated
from .identities import identity_metadata, load_identity_config
from .rules_database import export_rules_database
from .source_anomalies import (
    load_source_anomaly_baseline,
    source_anomaly_baseline_applies,
    validate_normalized_source_anomalies,
)

DEFAULT_DATABASE = Path("data/generated/infinity.db")
DEFAULT_RULES_DATABASE = Path("data/generated/rules.db")
DEFAULT_CURATED_RULES = Path("data/curated/rules")


def _validate_source_anomaly_baseline(source: Path) -> None:
    with source.open(encoding="utf-8") as handle:
        normalized = json.load(handle)
    baseline = load_source_anomaly_baseline()
    if not source_anomaly_baseline_applies(normalized, baseline):
        return
    audit = validate_normalized_source_anomalies(normalized, baseline)
    print(
        "Source anomaly baseline: passed "
        f"({audit.warning_count} warnings; "
        f"baseline {audit.baseline_warning_count} from "
        f"{audit.baseline_snapshot_downloaded_on})"
    )


def _export(source: Path, destination: Path) -> None:
    with source.open(encoding="utf-8") as handle:
        normalized = json.load(handle)
    export_database(normalized, destination)
    print(f"Database ready: {destination}")
    print(f"Raw archive ready: {raw_database_path(destination)}")


def cmd_normalize(args: argparse.Namespace) -> int:
    config = load_identity_config()
    display_identities = load_display_identity_curated()
    result = normalize_dataset(
        args,
        canonical_faction_overrides=config.canonical_faction_overrides,
        display_army_overrides=display_identities.canonical_faction_display_armies,
        normalized_metadata={
            **identity_metadata(config),
            **display_identity_metadata(display_identities),
        },
    )
    _validate_source_anomaly_baseline(args.output)
    return result


def cmd_build(args: argparse.Namespace) -> int:
    config = load_identity_config()
    display_identities = load_display_identity_curated()
    build_dataset(
        args,
        canonical_faction_overrides=config.canonical_faction_overrides,
        display_army_overrides=display_identities.canonical_faction_display_armies,
        normalized_metadata={
            **identity_metadata(config),
            **display_identity_metadata(display_identities),
        },
    )
    normalized = args.output_dir / "normalized.json"
    _validate_source_anomaly_baseline(normalized)
    _export(normalized, args.output_dir / "infinity.db")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    _export(args.input, args.output)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .web.server import serve

    serve(args.database, host=args.host, port=args.port)
    return 0


def cmd_validate_curated(args: argparse.Namespace) -> int:
    if args.input.is_dir():
        documents = load_curated_directory(args.input)
        for path, document in documents:
            print(f"Validated curated reference: {path}")
            print(f"Sources: {len(document['sources'])}; records: {len(document['records'])}")
        print("Skipped reserved template: example.json")
        return 0

    document = load_curated_document(args.input)
    print(f"Validated curated reference: {args.input}")
    print(f"Sources: {len(document['sources'])}; records: {len(document['records'])}")
    return 0


def cmd_build_rules(args: argparse.Namespace) -> int:
    documents = load_curated_directory(args.input)
    export_rules_database(documents, args.output)
    print(f"Rules database ready: {args.output}")
    print(f"Collections: {len(documents)}")
    return 0


def _port(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infinity-db",
        description="Build the Infinity database and browse units on the web",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    add_data_commands(
        sub,
        build_handler=cmd_build,
        normalize_handler=cmd_normalize,
        require_metadata_for_build=True,
    )

    p_export = sub.add_parser("export", help="Import validated normalized JSON into SQLite")
    p_export.add_argument("input", type=Path, help="normalized.json input")
    p_export.add_argument("output", nargs="?", type=Path, default=DEFAULT_DATABASE)
    p_export.set_defaults(func=cmd_export)

    p_serve = sub.add_parser("serve", help="Start the local unit browser and read-only API")
    p_serve.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    p_serve.add_argument(
        "--host",
        default="0.0.0.0",
        help="Interface to bind (defaults to all interfaces, including the local network)",
    )
    p_serve.add_argument("--port", type=_port, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    p_curated = sub.add_parser(
        "validate-curated", help="Validate curated reference JSON files or a collection directory"
    )
    p_curated.add_argument("input", type=Path, help="Curated JSON file or directory")
    p_curated.set_defaults(func=cmd_validate_curated)

    p_rules = sub.add_parser(
        "build-rules", help="Build the separate rules database from curated JSON collections"
    )
    p_rules.add_argument("input", nargs="?", type=Path, default=DEFAULT_CURATED_RULES)
    p_rules.add_argument("--output", type=Path, default=DEFAULT_RULES_DATABASE)
    p_rules.set_defaults(func=cmd_build_rules)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nServer stopped.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
