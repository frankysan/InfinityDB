#!/usr/bin/env python3
"""Audit canonical loadout-payload semantics in the published InfinityDB database."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__:
    from .payload_audit_common import (
        canonical_json,
        characteristic_relationships,
        database_identity,
        decode_raw,
        extras_by_payload,
        grouped_rows,
        item_relationships,
        validate_schema,
        variation_count,
    )
else:
    from payload_audit_common import (
        canonical_json,
        characteristic_relationships,
        database_identity,
        decode_raw,
        extras_by_payload,
        grouped_rows,
        item_relationships,
        validate_schema,
        variation_count,
    )

REPORT_FORMAT = "InfinityDB loadout semantics audit"
REPORT_FORMAT_VERSION = 3
PAYLOAD_FORMAT = "InfinityDB canonical loadout payload"
PAYLOAD_FORMAT_VERSION = 1

PAYLOAD_FIELDS = ("name", "minis", "disabled")

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "loadout_payloads": ("id", "logical_unit_id", "payload_sha256", *PAYLOAD_FIELDS),
    "loadout_payload_occurrences": (
        "army_id",
        "unit_id",
        "group_id",
        "option_id",
        "loadout_payload_id",
        "position",
        "points",
        "swc",
    ),
    "loadout_payload_characteristics": (
        "loadout_payload_id",
        "position",
        "characteristic_id",
    ),
    "loadout_payload_orders": (
        "loadout_payload_id",
        "position",
        "order_type",
        "list_count",
        "total_count",
        "raw",
    ),
    "loadout_payload_skills": (
        "loadout_payload_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "loadout_payload_skill_extras": (
        "loadout_payload_id",
        "occurrence_position",
        "position",
        "extra_id",
    ),
    "loadout_payload_equipment": (
        "loadout_payload_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "loadout_payload_equipment_extras": (
        "loadout_payload_id",
        "occurrence_position",
        "position",
        "extra_id",
    ),
    "loadout_payload_weapons": (
        "loadout_payload_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "loadout_payload_weapon_extras": (
        "loadout_payload_id",
        "occurrence_position",
        "position",
        "extra_id",
    ),
    "profile_groups": (
        "army_id",
        "unit_id",
        "group_id",
        "position",
        "category_id",
        "isc",
        "notes",
    ),
    "logical_unit_sources": ("source_unit_id", "logical_unit_id"),
    "__infinity_metadata": ("key", "value"),
}

FIELD_CLASSIFICATION = {
    "loadout_payloads": {
        "id": "normalization_only",
        "logical_unit_id": "canonical_application_identity",
        "payload_sha256": "canonical_application_identity",
        "name": "canonical_fact",
        "minis": "canonical_fact",
        "disabled": "canonical_fact",
    },
    "loadout_payload_occurrences": {
        "army_id": "source_context",
        "unit_id": "source_identity",
        "group_id": "source_identity",
        "option_id": "source_identity",
        "loadout_payload_id": "canonical_application_identity",
        "position": "presentation_context",
        "points": "contextual_delta",
        "swc": "contextual_delta",
    },
}


class LoadoutSemanticsAuditError(ValueError):
    """Raised when the published loadout payload model cannot be audited safely."""


def _order_relationships(connection: sqlite3.Connection) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        "SELECT * FROM loadout_payload_orders ORDER BY loadout_payload_id, position"
    ):
        result[int(row["loadout_payload_id"])].append(
            {
                "order_type": row["order_type"],
                "list_count": row["list_count"],
                "total_count": row["total_count"],
                "raw": decode_raw(row["raw"]),
            }
        )
    return result


def _payload_hashes(connection: sqlite3.Connection) -> tuple[int, list[int]]:
    characteristics = characteristic_relationships(
        connection, "loadout_payload_characteristics", "loadout_payload_id"
    )
    orders = _order_relationships(connection)
    skill_extras = extras_by_payload(
        connection, "loadout_payload_skill_extras", "loadout_payload_id"
    )
    equipment_extras = extras_by_payload(
        connection, "loadout_payload_equipment_extras", "loadout_payload_id"
    )
    weapon_extras = extras_by_payload(
        connection, "loadout_payload_weapon_extras", "loadout_payload_id"
    )
    skills = item_relationships(
        connection, "loadout_payload_skills", "loadout_payload_id", skill_extras
    )
    equipment = item_relationships(
        connection,
        "loadout_payload_equipment",
        "loadout_payload_id",
        equipment_extras,
    )
    weapons = item_relationships(
        connection, "loadout_payload_weapons", "loadout_payload_id", weapon_extras
    )

    invalid: list[int] = []
    count = 0
    for row in connection.execute("SELECT * FROM loadout_payloads ORDER BY id"):
        count += 1
        payload_id = int(row["id"])
        payload = {field: row[field] for field in PAYLOAD_FIELDS}
        payload["characteristics"] = characteristics.get(payload_id, [])
        payload["orders"] = orders.get(payload_id, [])
        payload["skills"] = skills.get(payload_id, [])
        payload["equipment"] = equipment.get(payload_id, [])
        payload["weapons"] = weapons.get(payload_id, [])
        serialized = canonical_json(
            {
                "format": PAYLOAD_FORMAT,
                "formatVersion": PAYLOAD_FORMAT_VERSION,
                "payload": payload,
            },
            allow_nan=False,
        )
        actual = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        if actual != row["payload_sha256"]:
            invalid.append(payload_id)
    return count, invalid


def audit_database(path: Path) -> dict[str, Any]:
    """Return a deterministic read-only report for the published loadout payload model."""
    path = path.resolve()
    if not path.is_file():
        raise LoadoutSemanticsAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        validate_schema(connection, EXPECTED_COLUMNS, LoadoutSemanticsAuditError)
        payload_count, invalid_hashes = _payload_hashes(connection)
        occurrences = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM loadout_payload_occurrences "
                "ORDER BY army_id, unit_id, group_id, option_id"
            )
        ]
        source_groups = grouped_rows(occurrences, ("unit_id", "group_id", "option_id"))
        repeated_source = {key: rows for key, rows in source_groups.items() if len(rows) > 1}
        multiple_payloads = sum(
            1
            for rows in source_groups.values()
            if len({row["loadout_payload_id"] for row in rows}) > 1
        )
        payload_use = Counter(row["loadout_payload_id"] for row in occurrences)
        orphan_payload_count = payload_count - len(payload_use)

        logical_mismatches = int(
            connection.execute(
                "SELECT COUNT(*) FROM loadout_payload_occurrences AS lpo "
                "LEFT JOIN logical_unit_sources AS lus ON lus.source_unit_id = lpo.unit_id "
                "LEFT JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id "
                "WHERE lus.logical_unit_id IS NULL OR lp.id IS NULL "
                "OR lp.logical_unit_id != lus.logical_unit_id"
            ).fetchone()[0]
        )
        missing_groups = int(
            connection.execute(
                "SELECT COUNT(*) FROM loadout_payload_occurrences AS lpo "
                "LEFT JOIN profile_groups AS pg ON pg.army_id = lpo.army_id "
                "AND pg.unit_id = lpo.unit_id AND pg.group_id = lpo.group_id "
                "WHERE pg.army_id IS NULL"
            ).fetchone()[0]
        )
        duplicate_identities = int(
            connection.execute(
                "SELECT COUNT(*) FROM (SELECT logical_unit_id, payload_sha256 "
                "FROM loadout_payloads GROUP BY logical_unit_id, payload_sha256 "
                "HAVING COUNT(*) > 1)"
            ).fetchone()[0]
        )

        issues: list[str] = []
        if invalid_hashes:
            issues.append(f"{len(invalid_hashes)} loadout payload hash mismatch(es)")
        if orphan_payload_count:
            issues.append(f"{orphan_payload_count} loadout payload(s) have no occurrence")
        if logical_mismatches:
            issues.append(f"{logical_mismatches} loadout occurrence logical-unit mismatch(es)")
        if missing_groups:
            issues.append(f"{missing_groups} loadout occurrence(s) have no profile group")
        if duplicate_identities:
            issues.append(f"{duplicate_identities} duplicate loadout payload identity group(s)")

        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": database_identity(connection, path),
            "fieldClassification": FIELD_CLASSIFICATION,
            "summary": {
                "status": "pass" if not issues else "fail",
                "loadoutPayloadCount": payload_count,
                "loadoutOccurrenceCount": len(occurrences),
                "repeatedSourceLoadoutKeyCount": len(repeated_source),
                "sourceLoadoutKeysWithMultiplePayloads": multiple_payloads,
                "sourceLoadoutKeysWithPointsVariation": variation_count(
                    repeated_source, "points"
                ),
                "sourceLoadoutKeysWithSwcVariation": variation_count(repeated_source, "swc"),
                "reusedPayloadCount": sum(1 for count in payload_use.values() if count > 1),
                "invalidPayloadHashCount": len(invalid_hashes),
                "orphanPayloadCount": orphan_payload_count,
                "logicalUnitMismatchCount": logical_mismatches,
                "missingProfileGroupCount": missing_groups,
                "duplicatePayloadIdentityCount": duplicate_identities,
            },
            "invalidPayloadIds": invalid_hashes,
            "issues": issues,
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Published infinity.db to audit")
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database)
    except (OSError, sqlite3.Error, LoadoutSemanticsAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    summary = report["summary"]
    print("InfinityDB loadout semantics audit")
    print(
        f"Loadouts: {summary['loadoutOccurrenceCount']} occurrences -> "
        f"{summary['loadoutPayloadCount']} canonical payloads | "
        f"{summary['reusedPayloadCount']} reused payloads"
    )
    print(
        f"Source-key variation: {summary['sourceLoadoutKeysWithMultiplePayloads']} semantic | "
        f"{summary['sourceLoadoutKeysWithPointsVariation']} points | "
        f"{summary['sourceLoadoutKeysWithSwcVariation']} SWC"
    )
    print(f"Status: {summary['status'].upper()}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Report: {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
