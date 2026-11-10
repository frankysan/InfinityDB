"""Application commands built on the existing data ingestion tools."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from infinity_army_data.cli import add_data_commands
from infinity_army_data.cli import cmd_build as build_dataset
from infinity_army_data.cli import cmd_normalize as normalize_dataset

from . import __version__
from .build_provenance import BUILD_PROVENANCE_KEY
from .curated import load_curated_directory, load_curated_document
from .database import database_health_report, export_database, raw_database_path
from .database_set import database_set_health_report
from .display_identities import display_identity_metadata, load_display_identity_curated
from .identities import identity_metadata, load_identity_config
from .peripheral_identities import (
    load_peripheral_identity_curated,
    peripheral_identity_source_for_snapshot,
)
from .peripheral_identity_coverage import audit_peripheral_identity_coverage
from .rules_database import export_rules_database
from .scenario_definition import (
    scenario_definition_from_curated_document,
    select_scenario_geometry,
)
from .scenario_geometry import parse_scenario_geometry
from .scenario_map_svg import render_scenario_map_svg
from .source_anomalies import (
    load_source_anomaly_baseline,
    source_anomaly_baseline_applies,
    validate_normalized_source_anomalies,
)

DEFAULT_DATABASE = Path("data/generated/infinity.db")
DEFAULT_RULES_DATABASE = Path("data/generated/rules.db")
DEFAULT_STANDALONE_RULES_DATABASE = Path("local/rules-standalone.db")
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
    if args.db_dir is not None:
        from .database_set_builder import build_database_set

        result = build_database_set(args, _build_army)
        print(f"Runtime database set ready: {args.db_dir.resolve()}")
        print(f"Build set: {result['buildProvenance']['buildSetId']}")
        return 0
    return _build_army(args)


def _build_army(
    args: argparse.Namespace, build_provenance: dict[str, Any] | None = None,
) -> int:
    config = load_identity_config()
    display_identities = load_display_identity_curated()
    build_dataset(
        args,
        canonical_faction_overrides=config.canonical_faction_overrides,
        display_army_overrides=display_identities.resolve_master,
        normalized_metadata={
            **identity_metadata(config),
            **display_identity_metadata(display_identities),
            **({BUILD_PROVENANCE_KEY: build_provenance} if build_provenance is not None else {}),
        },
    )
    normalized = args.output_dir / "normalized.json"
    _validate_source_anomaly_baseline(normalized)
    database = args.output_dir / "infinity.db"
    _export(normalized, database)
    print(f"Application database size: {database.stat().st_size:,} bytes")
    print(f"Raw archive size: {raw_database_path(database).stat().st_size:,} bytes")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    _export(args.input, args.output)
    return 0



def cmd_database_health(args: argparse.Namespace) -> int:
    if args.db_dir is not None:
        if args.require_raw:
            raise ValueError("--require-raw applies to an Army database, not --db-dir")
        report = database_set_health_report(args.db_dir)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"Database-set health: {report['status']}")
            print(f"Database directory: {report['directory']}")
            if error := report.get("error"):
                print(f"Database-set error: {error}")
            else:
                print(f"Layout: {report['layout']}; integrity: {report['integrityCheck']}")
                provenance = report["buildProvenance"]
                print(f"Build provenance: {provenance.get('buildSetId', provenance['status'])}")
                for name, digest in report["sha256"].items():
                    print(f"{name}: {digest}")
            print("Source-policy freshness and graphical assets: not checked")
        return 0 if report["status"] == "healthy" else 1

    report = database_health_report(args.database, require_raw=args.require_raw)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "healthy" else 1

    application = report["application"]
    raw_archive = report["rawArchive"]
    print(f"Database health: {report['status']}")
    print(f"Application database: {application['path']}")
    if application["bytes"] is not None:
        print(f"Application size: {application['bytes']:,} bytes")
    print(
        "Schema revision: "
        f"{application['schemaRevision']} (expected {application['expectedSchemaRevision']})"
    )
    print(
        "Compatibility revision: "
        f"{application['compatibilityRevision']} "
        f"(expected {application['expectedCompatibilityRevision']})"
    )
    print(
        f"Application validation: {application['status']} "
        f"({application['validationMs']:.3f} ms)"
    )
    if error := application.get("error"):
        print(f"Application error: {error}")
    if args.require_raw:
        print(f"Raw archive: {raw_archive['path']}")
        if raw_archive["bytes"] is not None:
            print(f"Raw archive size: {raw_archive['bytes']:,} bytes")
        print(
            f"Raw pair validation: {raw_archive['status']} "
            f"({raw_archive['validationMs']:.3f} ms)"
        )
        if pair_sha256 := raw_archive.get("pairSha256"):
            print(f"Export pair SHA-256: {pair_sha256}")
        elif raw_archive["status"] == "valid":
            print("Export pair: legacy metadata match (no pair fingerprint)")
        if error := raw_archive.get("error"):
            print(f"Raw archive error: {error}")
    else:
        print("Raw archive: not checked (use --require-raw to validate the sibling pair)")
    return 0 if report["status"] == "healthy" else 1

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
    output = args.output if args.output is not None else DEFAULT_STANDALONE_RULES_DATABASE
    if output.resolve() == DEFAULT_RULES_DATABASE.resolve():
        raise ValueError(
            "build-rules cannot write the tracked release rules.db directly; "
            "build outside data/generated/ and review the complete matched set"
        )
    documents = load_curated_directory(args.input)
    source = (
        args.restrictions_manifest
        if args.restrictions_manifest is not None
        else Path("config/validation/restrictions-source-chart.json")
    )
    manifest = json.loads(source.read_text(encoding="utf-8"))
    from infinity_db.deployed_object_builder import build_deployed_objects

    curated_source = next(
        (
            path for path, document in documents
            if document["collection"]["id"] == "n5-core-v5.3"
            and document["collection"]["status"] == "current"
        ),
        None,
    )
    if curated_source is None:
        raise ValueError("Current N5.3 core source required for deployed objects")
    deployed_objects = build_deployed_objects(
        args.army_db, curated_source, args.delivery_reviews,
        args.candidate_reviews,
    )
    export_rules_database(
        documents, output, restrictions_manifest=manifest,
        deployed_objects=deployed_objects,
    )
    print(f"Rules database ready: {output} (schema v10)")
    print(f"Collections: {len(documents)}")
    if args.output is None:
        # A checkout has two supported targets: this ignored, complete runtime
        # for local/LAN hosting, and the separately promoted tracked Docker data.
        # Do not publish a mismatched variant/Weapon view during development.
        from tools.build_v10_runtime_candidate import publish_checkout_runtime

        publish_checkout_runtime(output)
        print("Checkout runtime ready: local/checkout-runtime")
    return 0


def cmd_render_scenario_map(args: argparse.Namespace) -> int:
    if args.scenario_id is None:
        if args.army_points is not None:
            raise ValueError("--army-points requires --scenario-id")
        document = json.loads(args.input.read_text(encoding="utf-8"))
        geometry = parse_scenario_geometry(document)
    else:
        if args.army_points is None:
            raise ValueError("--scenario-id requires --army-points")
        document = load_curated_document(args.input)
        definition = scenario_definition_from_curated_document(
            document, args.scenario_id
        )
        geometry = select_scenario_geometry(definition, args.army_points)

    svg = render_scenario_map_svg(geometry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Scenario map ready: {args.output}")
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
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
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
        database_set_build=True,
    )

    p_export = sub.add_parser("export", help="Import validated normalized JSON into SQLite")
    p_export.add_argument("input", type=Path, help="normalized.json input")
    p_export.add_argument("output", nargs="?", type=Path, default=DEFAULT_DATABASE)
    p_export.set_defaults(func=cmd_export)

    p_health = sub.add_parser(
        "database-health",
        help="Validate an Army database or an explicitly selected runtime directory",
    )
    health_selection = p_health.add_mutually_exclusive_group()
    health_selection.add_argument("database", nargs="?", type=Path, default=DEFAULT_DATABASE)
    health_selection.add_argument(
        "--db-dir", type=Path,
        help="Validate one complete runtime directory without fallback",
    )
    p_health.add_argument(
        "--require-raw",
        action="store_true",
        help="Require and validate the release-matched raw database sibling",
    )
    p_health.add_argument(
        "--json",
        action="store_true",
        help="Emit the health report as machine-readable JSON",
    )
    p_health.set_defaults(func=cmd_database_health)

    p_serve = sub.add_parser("serve", help="Start the local unit browser and read-only API")
    p_serve.add_argument(
        "--database", type=Path,
        help="Explicit Army database (disables automatic checkout runtime selection)",
    )
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
    p_rules.add_argument(
        "--output", type=Path,
        help=(
            "Standalone output (default: local/rules-standalone.db); without --output "
            "also prepares the ignored complete checkout runtime; never writes tracked rules.db"
        ),
    )
    p_rules.add_argument(
        "--restrictions-manifest", type=Path,
        help="Override the reviewed Restrictions chart manifest",
    )
    p_rules.add_argument(
        "--army-db", type=Path, default=DEFAULT_DATABASE,
        help="Source Army database for reviewed deployed-object usage",
    )
    p_rules.add_argument(
        "--delivery-reviews", type=Path,
        default=Path("config/validation/deployed-object-delivery-reviews.json"),
    )
    p_rules.add_argument(
        "--candidate-reviews", type=Path,
        default=Path("config/validation/deployed-object-candidate-reviews.json"),
    )
    p_rules.set_defaults(func=cmd_build_rules)

    p_scenario_map = sub.add_parser(
        "render-scenario-map",
        help="Render standalone or maintained scenario geometry as deterministic SVG",
    )
    p_scenario_map.add_argument(
        "input",
        type=Path,
        help="Scenario geometry JSON or curated rules collection",
    )
    p_scenario_map.add_argument("output", type=Path, help="SVG output path")
    p_scenario_map.add_argument(
        "--scenario-id",
        help="Typed maintained scenario id, for example scenario:domination",
    )
    p_scenario_map.add_argument(
        "--army-points",
        type=int,
        help="Army Points configuration to select for a maintained scenario",
    )
    p_scenario_map.set_defaults(func=cmd_render_scenario_map)

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


if __name__ == "__main__":
    raise SystemExit(main())
