#!/usr/bin/env python3
"""Audit the boundary between infinity.db and the lossless infinity.raw.db archive."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from infinity_db.database.paths import raw_database_path
from infinity_db.database.repository import Database, unit_sort_key
from infinity_db.database.schema import (
    DATABASE_TABLES,
    DERIVED_TABLES,
    METADATA_TABLE,
    RAW_ROWS_TABLE,
    TABLES,
    quote,
)

if __package__:
    from tools.audit_runtime_database_surface import audit_database as audit_runtime_surface
else:
    from audit_runtime_database_surface import audit_database as audit_runtime_surface

FORMAT = "InfinityDB application/raw database separation audit"
FORMAT_VERSION = 1

CANONICAL = "canonical_application"
CONTEXTUAL = "contextual_application"
SOURCE_ONLY = "source_provenance_only"

# These normalized source catalogs are currently the application identity for their
# domains. They have no separate application-catalog layer yet.
SOURCE_CANONICAL_TABLES = {
    "categories",
    "characteristics",
    "extras",
    "troop_types",
}

# These normalized source tables remain intentionally application-visible because
# current serving still needs source/context coordinates or source-backed catalog
# variants. Everything else in TABLES is a raw/source-only candidate once normal
# serving proves it is unused.
SOURCE_CONTEXTUAL_TABLES = {
    "army_lists",
    "army_units",
    "equipment",
    "metadata_ammunitions",
    "metadata_weapons",
    "option_peripherals",
    "profile_groups",
    "profile_peripherals",
    "skills",
    "unit_factions",
    "unit_option_equipment",
    "unit_option_equipment_extras",
    "unit_option_skill_extras",
    "unit_option_skills",
    "unit_option_weapon_extras",
    "unit_option_weapons",
    "unit_options",
    "units",
    "weapons",
}

DERIVED_CANONICAL_TABLES = {
    "application_armies",
    "application_catalog_items",
    "application_domain_slugs",
    "application_peripheral_entities",
    "application_peripheral_profiles",
    "loadout_payload_characteristics",
    "loadout_payload_equipment",
    "loadout_payload_equipment_extras",
    "loadout_payload_orders",
    "loadout_payload_skill_extras",
    "loadout_payload_skills",
    "loadout_payload_weapon_extras",
    "loadout_payload_weapons",
    "loadout_payloads",
    "logical_units",
    "profile_payload_characteristics",
    "profile_payload_equipment",
    "profile_payload_equipment_extras",
    "profile_payload_skill_extras",
    "profile_payload_skills",
    "profile_payload_weapon_extras",
    "profile_payload_weapons",
    "profile_payloads",
}


class DatabaseSeparationAuditError(ValueError):
    """Raised when the maintained application/raw split policy is stale or invalid."""


def _table_classification() -> dict[str, str]:
    overlap = SOURCE_CANONICAL_TABLES & SOURCE_CONTEXTUAL_TABLES
    unknown_source_policy = (SOURCE_CANONICAL_TABLES | SOURCE_CONTEXTUAL_TABLES) - set(TABLES)
    unknown_derived_policy = DERIVED_CANONICAL_TABLES - set(DERIVED_TABLES)
    if overlap or unknown_source_policy or unknown_derived_policy:
        raise DatabaseSeparationAuditError("Maintained database-separation policy is invalid")

    result = {METADATA_TABLE: CANONICAL}
    for table in TABLES:
        if table in SOURCE_CANONICAL_TABLES:
            result[table] = CANONICAL
        elif table in SOURCE_CONTEXTUAL_TABLES:
            result[table] = CONTEXTUAL
        else:
            result[table] = SOURCE_ONLY
    for table in DERIVED_TABLES:
        result[table] = CANONICAL if table in DERIVED_CANONICAL_TABLES else CONTEXTUAL
    return result


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _row_counts(connection: sqlite3.Connection, tables: Sequence[str]) -> dict[str, int]:
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {quote(table)}").fetchone()[0])
        for table in tables
    }


def _table_storage_bytes(connection: sqlite3.Connection) -> dict[str, int] | None:
    try:
        objects = {
            str(row[0]): str(row[1])
            for row in connection.execute(
                "SELECT name, tbl_name FROM sqlite_master WHERE type IN ('table', 'index')"
            )
        }
        totals: defaultdict[str, int] = defaultdict(int)
        for name, size in connection.execute(
            "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"
        ):
            totals[objects.get(str(name), str(name))] += int(size or 0)
        return dict(totals)
    except sqlite3.Error:
        return None


def _metadata_rows(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row[0]): str(row[1])
        for row in connection.execute(
            f"SELECT key, value FROM {quote(METADATA_TABLE)} ORDER BY key"
        )
    }


def _json_metadata(rows: Mapping[str, str], key: str) -> Any:
    if key not in rows:
        raise DatabaseSeparationAuditError(f"Database metadata is missing {key!r}")
    try:
        return json.loads(rows[key])
    except (TypeError, json.JSONDecodeError) as exc:
        raise DatabaseSeparationAuditError(
            f"Database metadata {key!r} is not valid JSON"
        ) from exc


class _ValidationTracingDatabase(Database):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.reads: set[tuple[str, str]] = set()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function("casefold", 1, lambda value: (value or "").casefold())
        connection.create_function("unit_sort_key", 1, unit_sort_key)

        def authorize(
            action: int,
            table: str | None,
            column: str | None,
            _database: str | None,
            _trigger: str | None,
        ) -> int:
            if action == sqlite3.SQLITE_READ and table and column:
                self.reads.add((table, column))
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorize)
        try:
            connection.execute("BEGIN")
            yield connection
        finally:
            connection.close()


def _validation_reads(path: Path) -> dict[str, list[str]]:
    database = _ValidationTracingDatabase(path)
    database.validate()
    grouped: defaultdict[str, set[str]] = defaultdict(set)
    for table, field in database.reads:
        grouped[table].add(field)
    return {table: sorted(fields) for table, fields in sorted(grouped.items())}


def _foreign_key_blockers(
    classification: Mapping[str, str],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for table, definition in DATABASE_TABLES.items():
        if classification[table] == SOURCE_ONLY:
            continue
        for reference in definition.references:
            if classification[reference.table] != SOURCE_ONLY:
                continue
            blockers.append(
                {
                    "table": table,
                    "fields": list(reference.fields),
                    "targetTable": reference.table,
                    "targetFields": list(reference.target),
                }
            )
    return blockers


def _raw_archive_report(
    application_path: Path,
    raw_path: Path,
    application_metadata: Mapping[str, str],
) -> dict[str, Any]:
    if not raw_path.is_file():
        return {
            "status": "not_available",
            "path": str(raw_path),
            "reason": "Raw sibling was not available to this audit run.",
        }

    connection = sqlite3.connect(raw_path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        tables = _table_names(connection)
        expected_tables = {METADATA_TABLE, RAW_ROWS_TABLE}
        if tables != expected_tables:
            raise DatabaseSeparationAuditError(
                "Raw archive schema mismatch: expected only metadata and lossless row storage"
            )
        raw_metadata = _metadata_rows(connection)
        if dict(application_metadata) != raw_metadata:
            raise DatabaseSeparationAuditError(
                "Application and raw sibling metadata differ"
            )
        imported = _json_metadata(raw_metadata, "imported_tables")
        if not isinstance(imported, list) or any(not isinstance(item, str) for item in imported):
            raise DatabaseSeparationAuditError("Raw archive imported_tables metadata is invalid")
        unknown_imported = sorted(set(imported) - set(TABLES))
        if unknown_imported:
            raise DatabaseSeparationAuditError(
                "Raw archive imported_tables contains unsupported normalized tables: "
                + ", ".join(unknown_imported)
            )
        raw_counts = {
            str(table): int(count)
            for table, count in connection.execute(
                f"SELECT table_name, COUNT(*) FROM {quote(RAW_ROWS_TABLE)} "
                "GROUP BY table_name ORDER BY table_name"
            )
        }
        unexpected_rows = sorted(set(raw_counts) - set(imported))
        if unexpected_rows:
            raise DatabaseSeparationAuditError(
                "Raw archive contains rows for unknown normalized tables: "
                + ", ".join(unexpected_rows)
            )
        return {
            "status": "complete",
            "path": str(raw_path),
            "databaseBytes": raw_path.stat().st_size,
            "supportedNormalizedTableCount": len(TABLES),
            "importedNormalizedTableCount": len(imported),
            "storedRowCount": sum(raw_counts.values()),
            "tableRowCounts": {table: raw_counts.get(table, 0) for table in imported},
            "metadataMatchesApplication": True,
            "policy": (
                "The raw sibling contains the shared build metadata plus exact JSON for every "
                "normalized source row. Empty normalized tables are represented by imported_tables "
                "metadata even when they contribute no raw-row records."
            ),
        }
    finally:
        connection.close()


def audit_database(
    path: Path,
    *,
    project_root: Path,
    raw_path: Path | None = None,
) -> dict[str, Any]:
    """Return deterministic evidence for the frontend/raw database boundary."""
    path = path.resolve()
    project_root = project_root.resolve()
    if not path.is_file():
        raise DatabaseSeparationAuditError(f"Database does not exist: {path}")

    Database(path).validate()
    runtime = audit_runtime_surface(path, project_root=project_root)
    classification = _table_classification()
    expected_tables = set(classification)

    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        actual_tables = _table_names(connection)
        missing = sorted(expected_tables - actual_tables)
        unexpected = sorted(actual_tables - expected_tables)
        if missing or unexpected:
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise DatabaseSeparationAuditError(
                "Application database table inventory does not match policy ("
                + "; ".join(details)
                + ")"
            )
        counts = _row_counts(connection, sorted(expected_tables))
        storage = _table_storage_bytes(connection)
        metadata = _metadata_rows(connection)
    finally:
        connection.close()

    runtime_tables = {item["table"] for item in runtime["inventory"]}
    source_only_tables = {
        table for table, role in classification.items() if role == SOURCE_ONLY
    }
    runtime_source_only = sorted(runtime_tables & source_only_tables)
    if runtime_source_only:
        raise DatabaseSeparationAuditError(
            "Normal serving reads table(s) classified as source/provenance-only: "
            + ", ".join(runtime_source_only)
        )

    validation_reads = _validation_reads(path)
    validation_source_only = sorted(set(validation_reads) & source_only_tables)
    fk_blockers = _foreign_key_blockers(classification)

    inventory = []
    class_counts: defaultdict[str, int] = defaultdict(int)
    class_rows: defaultdict[str, int] = defaultdict(int)
    for table in sorted(expected_tables):
        role = classification[table]
        class_counts[role] += 1
        class_rows[role] += counts[table]
        origin = (
            "operational_metadata"
            if table == METADATA_TABLE
            else "normalized_source"
            if table in TABLES
            else "derived_application"
        )
        inventory.append(
            {
                "table": table,
                "origin": origin,
                "classification": role,
                "rowCount": counts[table],
                "storageBytes": storage.get(table) if storage is not None else None,
                "runtimeRead": table in runtime_tables,
                "validationRead": table in validation_reads,
            }
        )

    source_only_bytes = (
        sum(storage.get(table, 0) for table in source_only_tables)
        if storage is not None
        else None
    )
    database_bytes = path.stat().st_size
    source_only_percent = (
        round((source_only_bytes / database_bytes) * 100, 2)
        if source_only_bytes is not None and database_bytes
        else None
    )

    selected_raw_path = (raw_path or raw_database_path(path)).resolve()
    raw_report = _raw_archive_report(path, selected_raw_path, metadata)

    surface_roles = {}
    for surface, tables in runtime["surfaces"].items():
        surface_roles[surface] = {
            table: classification[table] for table in sorted(tables)
        }

    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "database": {
            "path": str(path),
            "databaseBytes": database_bytes,
            "tableCount": len(expected_tables),
            "normalizedSourceTableCount": len(TABLES),
            "derivedApplicationTableCount": len(DERIVED_TABLES),
        },
        "summary": {
            "canonicalApplicationTableCount": class_counts[CANONICAL],
            "contextualApplicationTableCount": class_counts[CONTEXTUAL],
            "sourceProvenanceOnlyTableCount": class_counts[SOURCE_ONLY],
            "canonicalApplicationRowCount": class_rows[CANONICAL],
            "contextualApplicationRowCount": class_rows[CONTEXTUAL],
            "sourceProvenanceOnlyRowCount": class_rows[SOURCE_ONLY],
            "runtimeTableCount": runtime["summary"]["runtimeTableCount"],
            "runtimeSourceOnlyViolationCount": len(runtime_source_only),
            "foreignKeyBlockerCount": len(fk_blockers),
            "validationSourceOnlyDependencyCount": len(validation_source_only),
            "sourceOnlyStorageBytes": source_only_bytes,
            "sourceOnlyStoragePercent": source_only_percent,
        },
        "rawArchive": raw_report,
        "foreignKeyBlockers": fk_blockers,
        "validationSourceOnlyDependencies": [
            {"table": table, "fields": validation_reads[table]}
            for table in validation_source_only
        ],
        "runtime": {
            "surfaceCount": runtime["summary"]["surfaceCount"],
            "tableCount": runtime["summary"]["runtimeTableCount"],
            "fieldCount": runtime["summary"]["runtimeFieldCount"],
            "sourceOnlyViolations": runtime_source_only,
            "surfaceTableClassifications": surface_roles,
        },
        "inventory": inventory,
        "conclusion": (
            "The current frontend/raw split has a deterministic table boundary. Source-only "
            "candidates are already absent from normal serving, but physical removal is still "
            "blocked by retained foreign-key references and validation queries that compare "
            "canonical materializations with duplicated source tables. Resolve those blockers "
            "before changing the published infinity.db schema."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Frontend infinity.db to audit")
    parser.add_argument(
        "--raw-database",
        type=Path,
        help="Optional raw sibling path; defaults to the infinity.raw.db sibling when present",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root used for runtime serving-surface verification",
    )
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(
            args.database,
            project_root=args.project_root,
            raw_path=args.raw_database,
        )
    except (OSError, sqlite3.Error, DatabaseSeparationAuditError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    summary = report["summary"]
    print("InfinityDB application/raw database separation audit")
    print(
        "Application tables: "
        f"{summary['canonicalApplicationTableCount']} canonical | "
        f"{summary['contextualApplicationTableCount']} contextual | "
        f"{summary['sourceProvenanceOnlyTableCount']} source/provenance-only"
    )
    print(
        "Physical split blockers: "
        f"{summary['foreignKeyBlockerCount']} foreign keys | "
        f"{summary['validationSourceOnlyDependencyCount']} validation source tables"
    )
    if summary["sourceOnlyStorageBytes"] is not None:
        print(
            "Current source-only footprint: "
            f"{summary['sourceOnlyStorageBytes']} bytes "
            f"({summary['sourceOnlyStoragePercent']}% of infinity.db)"
        )
    print(f"Raw archive: {report['rawArchive']['status']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
