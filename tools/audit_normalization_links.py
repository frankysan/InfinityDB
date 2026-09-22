#!/usr/bin/env python3
"""Audit relational links that are implementation structure rather than player facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from infinity_db.database.schema import DATABASE_TABLES

REPORT_FORMAT = "InfinityDB normalization link semantics audit"
REPORT_FORMAT_VERSION = 1

FILTER_CATALOG_LINKS: dict[str, tuple[str, str]] = {
    "category": ("army_categories", "categories"),
    "characteristics": ("army_characteristics", "characteristics"),
    "troopType": ("army_troop_types", "troop_types"),
    "equipment": ("army_equipment", "equipment"),
    "skills": ("army_skills", "skills"),
    "weapons": ("army_weapons", "weapons"),
    "ammunition": ("army_ammunition", "ammunition"),
    "extras": ("army_extras", "extras"),
}

# These links connect source/provenance identities to InfinityDB application
# abstractions. The link itself is not a separate player-facing game
# relationship, but it is not disposable normalization either: it preserves
# traceability and, in some rows, contextual deltas.
CANONICALIZATION_LINKS: tuple[dict[str, Any], ...] = (
    {
        "table": "application_army_sources",
        "fields": ("application_army_id",),
        "target": "application_armies",
        "contextualFields": ("has_army_list", "has_metadata"),
    },
    {
        "table": "application_catalog_sources",
        "fields": ("catalog", "application_item_id"),
        "target": "application_catalog_items",
        "contextualFields": ("source_name", "has_metadata"),
    },
    {
        "table": "logical_unit_sources",
        "fields": ("logical_unit_id",),
        "target": "logical_units",
        "contextualFields": (),
    },
    {
        "table": "profile_payload_occurrences",
        "fields": ("profile_payload_id",),
        "target": "profile_payloads",
        "contextualFields": ("position", "ava", "logo"),
    },
    {
        "table": "loadout_payload_occurrences",
        "fields": ("loadout_payload_id",),
        "target": "loadout_payloads",
        "contextualFields": ("position", "points", "swc"),
    },
    {
        "table": "application_peripheral_sources",
        "fields": ("entity_id",),
        "target": "application_peripheral_entities",
        "contextualFields": ("source_id", "source_name"),
    },
    {
        "table": "application_peripheral_unit_sources",
        "fields": ("logical_unit_id",),
        "target": "logical_units",
        "contextualFields": ("type_id", "source_id", "source_name"),
    },
)


class NormalizationLinkAuditError(ValueError):
    """Raised when the database/schema cannot support the maintained audit policy."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        "SELECT value FROM __infinity_metadata WHERE key = '_meta'"
    ).fetchone()
    if row is None:
        raise NormalizationLinkAuditError("Database metadata row '_meta' is missing")
    try:
        value = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        raise NormalizationLinkAuditError("Database metadata row '_meta' is invalid JSON") from exc
    if not isinstance(value, dict):
        raise NormalizationLinkAuditError("Database metadata row '_meta' must be an object")
    return value


def _validate_policy(connection: sqlite3.Connection) -> None:
    tables = _table_names(connection)
    required = {
        "__infinity_metadata",
        "option_weapon_templates",
        "option_weapons",
        *(
            table
            for table, _catalog in FILTER_CATALOG_LINKS.values()
        ),
        *(catalog for _table, catalog in FILTER_CATALOG_LINKS.values()),
        *(item["table"] for item in CANONICALIZATION_LINKS),
    }
    missing = sorted(required - tables)
    if missing:
        raise NormalizationLinkAuditError(
            "Database is missing required table(s): " + ", ".join(missing)
        )

    expected_filter_columns = {
        "army_id",
        "item_id",
        "position",
        "mercs",
        "specops",
        "teamops",
    }
    for table, catalog in FILTER_CATALOG_LINKS.values():
        missing_columns = sorted(expected_filter_columns - _columns(connection, table))
        if missing_columns:
            raise NormalizationLinkAuditError(
                f"Table {table!r} is missing required columns: {', '.join(missing_columns)}"
            )
        definition = DATABASE_TABLES.get(table)
        if definition is None or definition.key != ("army_id", "item_id"):
            raise NormalizationLinkAuditError(
                f"Maintained filter-link policy no longer matches schema table {table!r}"
            )
        targets = {(reference.table, reference.fields) for reference in definition.references}
        if ("army_lists", ("army_id",)) not in targets or (catalog, ("item_id",)) not in targets:
            raise NormalizationLinkAuditError(
                f"Maintained filter-link references no longer match schema table {table!r}"
            )

    option_columns = _columns(connection, "option_weapons")
    template_columns = _columns(connection, "option_weapon_templates")
    required_option_columns = {
        "template_id", "occurrence_id", "army_id", "unit_id", "group_id", "option_id"
    }
    if not required_option_columns <= option_columns:
        raise NormalizationLinkAuditError("option_weapons schema no longer matches audit policy")
    if not {"id", "item_id", "display_order", "quantity", "raw"} <= template_columns:
        raise NormalizationLinkAuditError(
            "option_weapon_templates schema no longer matches audit policy"
        )

    for item in CANONICALIZATION_LINKS:
        table = item["table"]
        missing_columns = sorted(
            (set(item["fields"]) | set(item["contextualFields"])) - _columns(connection, table)
        )
        if missing_columns:
            raise NormalizationLinkAuditError(
                f"Table {table!r} is missing maintained audit columns: "
                + ", ".join(missing_columns)
            )


def _filter_catalog_links(connection: sqlite3.Connection) -> dict[str, Any]:
    tables: list[dict[str, Any]] = []
    total_rows = 0
    for source_name, (table, catalog) in FILTER_CATALOG_LINKS.items():
        row = connection.execute(
            f'''SELECT COUNT(*) AS row_count,
                       COUNT(DISTINCT army_id) AS army_count,
                       COUNT(DISTINCT item_id) AS item_count,
                       SUM(CASE WHEN mercs = 1 THEN 1 ELSE 0 END) AS mercs_count,
                       SUM(CASE WHEN specops = 1 THEN 1 ELSE 0 END) AS specops_count,
                       SUM(CASE WHEN teamops = 1 THEN 1 ELSE 0 END) AS teamops_count
                FROM "{table}"'''
        ).fetchone()
        row_count = int(row["row_count"])
        total_rows += row_count
        tables.append(
            {
                "sourceFilter": source_name,
                "table": table,
                "catalogTable": catalog,
                "rowCount": row_count,
                "sourceArmyCount": int(row["army_count"]),
                "distinctItemCount": int(row["item_count"]),
                "contextFlagTrueCounts": {
                    "mercs": int(row["mercs_count"] or 0),
                    "specops": int(row["specops_count"] or 0),
                    "teamops": int(row["teamops_count"] or 0),
                },
            }
        )
    return {
        "classification": "normalization_only_source_filter_index",
        "tableCount": len(tables),
        "rowCount": total_rows,
        "tables": tables,
        "policy": (
            "These rows flatten each Army document's filters.* lookup arrays into relational "
            "Army-to-catalog joins. Their association, source ordering, and optional-mode flags "
            "describe the source filter/index presentation rather than an independent gameplay "
            "relationship. Preserve them in the lossless/source layer, but absence of a dedicated "
            "web presentation is not a 1.0 completeness gap."
        ),
    }


def _option_weapon_indirection(connection: sqlite3.Connection) -> dict[str, Any]:
    occurrence_count = int(connection.execute("SELECT COUNT(*) FROM option_weapons").fetchone()[0])
    template_count = int(
        connection.execute("SELECT COUNT(*) FROM option_weapon_templates").fetchone()[0]
    )
    distinct_template_count = int(
        connection.execute("SELECT COUNT(DISTINCT template_id) FROM option_weapons").fetchone()[0]
    )
    dangling_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM option_weapons AS ow "
            "LEFT JOIN option_weapon_templates AS wt ON wt.id = ow.template_id "
            "WHERE wt.id IS NULL"
        ).fetchone()[0]
    )
    unreferenced_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM option_weapon_templates AS wt "
            "LEFT JOIN option_weapons AS ow ON ow.template_id = wt.id "
            "WHERE ow.template_id IS NULL"
        ).fetchone()[0]
    )
    return {
        "classification": "normalization_only_storage_indirection",
        "occurrenceRowCount": occurrence_count,
        "templateRowCount": template_count,
        "referencedTemplateCount": distinct_template_count,
        "danglingOccurrenceCount": dangling_count,
        "unreferencedTemplateCount": unreferenced_count,
        "normalizationOnlyElements": [
            "option_weapon_templates.id",
            "option_weapons.template_id",
        ],
        "semanticOccurrenceFields": [
            "option_weapons army/unit/group/option parent coordinates",
            "option_weapons.position",
            "option_weapon_templates.item_id",
            "option_weapon_templates.display_order",
            "option_weapon_templates.quantity",
            "option_weapon_templates.raw",
        ],
        "policy": (
            "The template identity and template_id edge deduplicate repeated option-weapon "
            "payloads for storage. They are not a player-facing weapon relationship of their own. "
            "The rejoined occurrence still carries the source option-to-weapon attachment and "
            "must remain reconstructable."
        ),
    }


def _canonicalization_links(connection: sqlite3.Connection) -> dict[str, Any]:
    links = []
    for item in CANONICALIZATION_LINKS:
        table = item["table"]
        links.append(
            {
                "table": table,
                "fields": list(item["fields"]),
                "target": item["target"],
                "contextualFields": list(item["contextualFields"]),
                "rowCount": int(
                    connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                ),
            }
        )
    return {
        "classification": "canonicalization_or_provenance_infrastructure",
        "linkCount": len(links),
        "links": links,
        "policy": (
            "These source-to-application or occurrence-to-payload edges do not create an "
            "additional gameplay relationship, but they are intentionally not classified as "
            "normalization-only. They preserve canonical identity evidence, traceability, and/or "
            "contextual deltas and must survive any frontend/raw database split in equivalent form."
        ),
    }


def audit_database(path: Path) -> dict[str, Any]:
    """Return deterministic evidence for normalization-only relational links."""
    path = path.resolve()
    if not path.is_file():
        raise NormalizationLinkAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_policy(connection)
        metadata = _metadata(connection)
        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "sha256": _sha256_file(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "sourceFilterCatalogLinks": _filter_catalog_links(connection),
            "optionWeaponTemplateIndirection": _option_weapon_indirection(connection),
            "canonicalizationLinks": _canonicalization_links(connection),
            "conclusion": (
                "Only the maintained source-filter catalog joins and option-weapon template "
                "identity/link are classified as normalization-only link structures in this "
                "audit. Semantic attachment tables remain player-relevant relationships, while "
                "canonicalization/provenance mappings remain infrastructure rather than "
                "additional player-facing facts."
            ),
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Frontend infinity.db to audit")
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database)
    except (OSError, sqlite3.Error, NormalizationLinkAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    filters = report["sourceFilterCatalogLinks"]
    templates = report["optionWeaponTemplateIndirection"]
    canonical = report["canonicalizationLinks"]
    print("InfinityDB normalization link semantics audit")
    print(
        f"Source filter joins: {filters['tableCount']} tables | {filters['rowCount']} rows | "
        "normalization-only"
    )
    print(
        "Option weapon indirection: "
        f"{templates['occurrenceRowCount']} occurrences -> "
        f"{templates['templateRowCount']} templates | "
        f"{templates['danglingOccurrenceCount']} dangling"
    )
    print(
        f"Canonicalization/provenance links: {canonical['linkCount']} maintained link families | "
        "not player-facing, not disposable normalization"
    )

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
