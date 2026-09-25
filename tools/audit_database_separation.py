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
    DERIVED_TABLES,
    METADATA_TABLE,
    PUBLISHED_DATABASE_TABLES,
    RAW_ROWS_TABLE,
    SOURCE_ONLY_TABLES,
    TABLES,
    quote,
)

if __package__:
    from tools.audit_runtime_database_surface import audit_database as audit_runtime_surface
else:
    from audit_runtime_database_surface import audit_database as audit_runtime_surface

FORMAT = "InfinityDB application/raw database separation audit"
FORMAT_VERSION = 2

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
    connection: sqlite3.Connection,
    classification: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Return published foreign keys that still target raw-only tables."""

    blockers: list[dict[str, Any]] = []
    for table in sorted(PUBLISHED_DATABASE_TABLES):
        grouped: defaultdict[int, list[sqlite3.Row]] = defaultdict(list)
        for row in connection.execute(f"PRAGMA foreign_key_list({quote(table)})"):
            grouped[int(row[0])].append(row)
        for rows in grouped.values():
            target = str(rows[0][2])
            if classification.get(target) != SOURCE_ONLY:
                continue
            rows.sort(key=lambda row: int(row[1]))
            blockers.append(
                {
                    "table": table,
                    "fields": [str(row[3]) for row in rows],
                    "targetTable": target,
                    "targetFields": [str(row[4]) for row in rows],
                }
            )
    return blockers


def _raw_archive_report(
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
    connection.row_factory = sqlite3.Row
    try:
        tables = _table_names(connection)
        expected_tables = {METADATA_TABLE, RAW_ROWS_TABLE, *TABLES}
        if tables != expected_tables:
            missing = sorted(expected_tables - tables)
            unexpected = sorted(tables - expected_tables)
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise DatabaseSeparationAuditError(
                "Raw archive schema mismatch (" + "; ".join(details) + ")"
            )

        raw_metadata = _metadata_rows(connection)
        if dict(application_metadata) != raw_metadata:
            raise DatabaseSeparationAuditError("Application and raw sibling metadata differ")
        imported = _json_metadata(raw_metadata, "imported_tables")
        if not isinstance(imported, list) or any(not isinstance(item, str) for item in imported):
            raise DatabaseSeparationAuditError("Raw archive imported_tables metadata is invalid")
        unknown_imported = sorted(set(imported) - set(TABLES))
        if unknown_imported:
            raise DatabaseSeparationAuditError(
                "Raw archive imported_tables contains unsupported normalized tables: "
                + ", ".join(unknown_imported)
            )

        lossless_counts = {
            str(table): int(count)
            for table, count in connection.execute(
                f"SELECT table_name, COUNT(*) FROM {quote(RAW_ROWS_TABLE)} "
                "GROUP BY table_name ORDER BY table_name"
            )
        }
        unexpected_rows = sorted(set(lossless_counts) - set(imported))
        if unexpected_rows:
            raise DatabaseSeparationAuditError(
                "Raw archive contains rows for unknown normalized tables: "
                + ", ".join(unexpected_rows)
            )
        relational_counts = _row_counts(connection, sorted(TABLES))
        mismatches = [
            table
            for table in sorted(TABLES)
            if relational_counts[table] != lossless_counts.get(table, 0)
        ]
        if mismatches:
            raise DatabaseSeparationAuditError(
                "Raw relational source tables differ from lossless row storage: "
                + ", ".join(mismatches)
            )

        storage = _table_storage_bytes(connection)
        return {
            "status": "complete",
            "path": str(raw_path),
            "databaseBytes": raw_path.stat().st_size,
            "supportedNormalizedTableCount": len(TABLES),
            "relationalNormalizedTableCount": len(TABLES),
            "importedNormalizedTableCount": len(imported),
            "storedRowCount": sum(lossless_counts.values()),
            "tableRowCounts": relational_counts,
            "losslessTableRowCounts": {
                table: lossless_counts.get(table, 0) for table in sorted(TABLES)
            },
            "tableStorageBytes": storage,
            "metadataMatchesApplication": True,
            "policy": (
                "The raw sibling contains queryable normalized source tables plus exact JSON "
                "for every normalized source row. It shares build metadata with the published "
                "application database and is not read by normal serving."
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
    """Return deterministic evidence for the completed application/raw split."""

    path = path.resolve()
    project_root = project_root.resolve()
    if not path.is_file():
        raise DatabaseSeparationAuditError(f"Database does not exist: {path}")

    Database(path).validate()
    runtime = audit_runtime_surface(path, project_root=project_root)
    classification = _table_classification()
    logical_tables = set(classification)
    expected_application_tables = {METADATA_TABLE, *PUBLISHED_DATABASE_TABLES}
    source_only_tables = {
        table for table, role in classification.items() if role == SOURCE_ONLY
    }
    if source_only_tables != set(SOURCE_ONLY_TABLES):
        raise DatabaseSeparationAuditError(
            "Maintained source-only classification differs from the published schema policy"
        )

    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        actual_tables = _table_names(connection)
        missing = sorted(expected_application_tables - actual_tables)
        unexpected = sorted(actual_tables - expected_application_tables)
        if missing or unexpected:
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise DatabaseSeparationAuditError(
                "Published application database table inventory does not match policy ("
                + "; ".join(details)
                + ")"
            )
        application_counts = _row_counts(connection, sorted(actual_tables))
        application_storage = _table_storage_bytes(connection)
        metadata = _metadata_rows(connection)
        fk_blockers = _foreign_key_blockers(connection, classification)
    finally:
        connection.close()

    published_metadata = _json_metadata(metadata, "published_tables")
    if set(published_metadata) != set(PUBLISHED_DATABASE_TABLES):
        raise DatabaseSeparationAuditError("published_tables metadata differs from schema policy")
    source_only_metadata = _json_metadata(metadata, "source_only_tables")
    if set(source_only_metadata) != set(SOURCE_ONLY_TABLES):
        raise DatabaseSeparationAuditError("source_only_tables metadata differs from schema policy")

    runtime_tables = {item["table"] for item in runtime["inventory"]}
    runtime_source_only = sorted(runtime_tables & source_only_tables)
    if runtime_source_only:
        raise DatabaseSeparationAuditError(
            "Normal serving reads source/provenance-only table(s): "
            + ", ".join(runtime_source_only)
        )

    validation_reads = _validation_reads(path)
    validation_source_only = sorted(set(validation_reads) & source_only_tables)
    if fk_blockers or validation_source_only:
        raise DatabaseSeparationAuditError(
            "Published database still depends on raw-only schema structures"
        )

    selected_raw_path = (raw_path or raw_database_path(path)).resolve()
    raw_report = _raw_archive_report(selected_raw_path, metadata)
    raw_counts = raw_report.get("tableRowCounts", {})
    raw_storage = raw_report.get("tableStorageBytes") or {}

    inventory: list[dict[str, Any]] = []
    class_counts: defaultdict[str, int] = defaultdict(int)
    class_rows: defaultdict[str, int] = defaultdict(int)
    for table in sorted(logical_tables):
        role = classification[table]
        class_counts[role] += 1
        if table == METADATA_TABLE or table in PUBLISHED_DATABASE_TABLES:
            row_count = application_counts[table]
        else:
            row_count = int(raw_counts.get(table, 0))
        class_rows[role] += row_count
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
                "rowCount": row_count,
                "published": table in expected_application_tables,
                "rawStored": table in TABLES,
                "applicationStorageBytes": (
                    application_storage.get(table) if application_storage is not None else None
                ),
                "rawStorageBytes": raw_storage.get(table),
                "runtimeRead": table in runtime_tables,
                "validationRead": table in validation_reads,
            }
        )

    raw_source_only_bytes = (
        sum(int(raw_storage.get(table, 0)) for table in source_only_tables)
        if raw_storage
        else None
    )
    surface_roles = {
        surface: {table: classification[table] for table in sorted(tables)}
        for surface, tables in runtime["surfaces"].items()
    }

    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "database": {
            "path": str(path),
            "databaseBytes": path.stat().st_size,
            "tableCount": len(expected_application_tables),
            "logicalInventoryTableCount": len(logical_tables),
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
            "sourceOnlyStorageBytes": 0,
            "sourceOnlyStoragePercent": 0.0,
            "rawSourceOnlyStorageBytes": raw_source_only_bytes,
        },
        "rawArchive": raw_report,
        "foreignKeyBlockers": fk_blockers,
        "validationSourceOnlyDependencies": [],
        "runtime": {
            "surfaceCount": runtime["summary"]["surfaceCount"],
            "tableCount": runtime["summary"]["runtimeTableCount"],
            "fieldCount": runtime["summary"]["runtimeFieldCount"],
            "sourceOnlyViolations": runtime_source_only,
            "surfaceTableClassifications": surface_roles,
        },
        "inventory": inventory,
        "conclusion": (
            "The physical split is complete: published infinity.db contains only application "
            "tables, has no foreign-key or runtime-validation dependency on raw-only tables, "
            "and normal serving never reads infinity.raw.db. The raw sibling retains queryable "
            "normalized source tables plus exact lossless row JSON for audit and reconstruction."
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
    print("Published source-only footprint: 0 bytes")
    print(f"Raw archive: {report['rawArchive']['status']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
