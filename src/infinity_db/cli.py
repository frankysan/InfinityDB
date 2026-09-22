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
from .peripheral_identities import (
    load_peripheral_identity_curated,
    peripheral_identity_source_for_snapshot,
)
from .peripheral_identity_coverage import audit_peripheral_identity_coverage
from .rules_database import export_rules_database
from .source_anomalies import (
    load_source_anomaly_baseline,
    source_anomaly_baseline_applies,
    validate_normalized_source_anomalies,
)

DEFAULT_DATABASE = Path("data/generated/infinity.db")
DEFAULT_RULES_DATABASE = Path("data/generated/rules.db")
DEFAULT_CURATED_RULES = Path("data/curated/rules")
DEFAULT_PERIPHERAL_IDENTITIES = Path("data/curated/peripherals/army-identities.json")


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
    peripheral_identities = load_peripheral_identity_curated()
    normalized_meta = normalized.get("_meta")
    snapshot_sha256 = (
        normalized_meta.get("snapshotArchiveSha256")
        if isinstance(normalized_meta, dict)
        else None
    )
    if peripheral_identity_source_for_snapshot(peripheral_identities, snapshot_sha256) is None:
        peripheral_identities = None
    export_database(
        normalized, destination, peripheral_identities=peripheral_identities
    )
    print(f"Database ready: {destination}")
    print(f"Raw archive ready: {raw_database_path(destination)}")


def cmd_normalize(args: argparse.Namespace) -> int:
    config = load_identity_config()
    display_identities = load_display_identity_curated()
    result = normalize_dataset(
        args,
        canonical_faction_overrides=config.canonical_faction_overrides,
        display_army_overrides=display_identities.resolve_master,
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
        display_army_overrides=display_identities.resolve_master,
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


def cmd_validate_peripheral_identities(args: argparse.Namespace) -> int:
    curated = load_peripheral_identity_curated(args.input)
    print(f"Validated Peripheral identity contract: {args.input}")
    print(
        f"Entities: {curated.entity_count}; profiles: {curated.profile_count}; "
        f"embedded mappings: {curated.mapping_count}; "
        f"unit mappings: {curated.unit_mapping_count}; "
        f"controller access: {curated.controller_access_count}"
    )
    if args.database is None:
        if args.output is not None:
            raise ValueError("--output requires --database")
        return 0

    report = audit_peripheral_identity_coverage(
        curated,
        args.database,
        include_details=True,
        rules_documents=load_curated_directory(DEFAULT_CURATED_RULES),
    )
    definitions = report["definitions"]
    validation = report["validation"]
    print(
        "Peripheral identity coverage: "
        f"{definitions['mappedDefinitionCount']}/{definitions['definitionCount']} "
        f"mapped ({definitions['coveragePercent']}%); "
        f"{definitions['unmappedReviewGroupCount']} review groups"
    )
    unit_backed = report["unitBackedIdentities"]
    print(
        "Unit-backed Peripheral identity coverage: "
        f"{unit_backed['mappedSourceUnitCount']}/{unit_backed['sourceUnitCount']} "
        f"mapped ({unit_backed['coveragePercent']}%); "
        f"{unit_backed['logicalUnitCount']} logical Units"
    )
    controller_access = report["controllerAccess"]
    print(
        "Peripheral controller access coverage: "
        f"{controller_access['mappedControllerOccurrenceCount']}/"
        f"{controller_access['sourceControllerOccurrenceCount']} mapped; "
        f"{controller_access['eligibleEdgeCount']} canonical access edges"
    )
    controller_graph = report["controllerGraph"]
    if controller_graph["status"] == "available":
        print(
            "Peripheral controller evidence: "
            f"{controller_graph['attachmentCount']} attachments across "
            f"{controller_graph['controllerCount']} controller occurrences; "
            f"{len(controller_graph['evaluableTypeIds'])} rule-backed type predicates"
        )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Coverage report: {args.output}")
    if validation["status"] != "valid":
        print(
            "ERROR: Peripheral identity mappings do not match the selected Army snapshot "
            f"({validation['staleMappingCount']} stale; "
            f"{validation['sourceNameDriftCount']} name drift).",
            file=sys.stderr,
        )
        return 1
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

    p_peripherals = sub.add_parser(
        "validate-peripheral-identities",
        help="Validate reviewed Army-Peripheral identity mappings",
    )
    p_peripherals.add_argument(
        "input", nargs="?", type=Path, default=DEFAULT_PERIPHERAL_IDENTITIES
    )
    p_peripherals.add_argument(
        "--database",
        type=Path,
        help="Compare mappings with an exact Army database snapshot and report coverage",
    )
    p_peripherals.add_argument(
        "--output",
        type=Path,
        help="Write the detailed snapshot coverage/review queue as JSON",
    )
    p_peripherals.set_defaults(func=cmd_validate_peripheral_identities)
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
