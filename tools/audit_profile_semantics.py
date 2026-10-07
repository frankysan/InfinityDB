#!/usr/bin/env python3
"""Audit canonical profile-payload semantics in the published InfinityDB database."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

if __package__:
    from .payload_audit_common import (
        canonical_json,
        characteristic_relationships,
        database_identity,
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
        extras_by_payload,
        grouped_rows,
        item_relationships,
        validate_schema,
        variation_count,
    )

REPORT_FORMAT = "InfinityDB profile semantics audit"
REPORT_FORMAT_VERSION = 3
PAYLOAD_FORMAT = "InfinityDB canonical profile payload"
PAYLOAD_FORMAT_VERSION = 1

PAYLOAD_FIELDS = (
    "name",
    "type_id",
    "move_1",
    "move_2",
    "cc",
    "bs",
    "ph",
    "wip",
    "arm",
    "bts",
    "vitality",
    "silhouette",
    "is_structure",
    "notes",
)

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "profile_payloads": ("id", "logical_unit_id", "payload_sha256", *PAYLOAD_FIELDS),
    "profile_payload_occurrences": (
        "army_id",
        "unit_id",
        "group_id",
        "profile_id",
        "profile_payload_id",
        "position",
        "ava",
        "logo",
    ),
    "profile_payload_characteristics": (
        "profile_payload_id",
        "position",
        "characteristic_id",
    ),
    "profile_payload_skills": (
        "profile_payload_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "profile_payload_skill_extras": (
        "profile_payload_id",
        "occurrence_position",
        "position",
        "extra_id",
    ),
    "profile_payload_equipment": (
        "profile_payload_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "profile_payload_equipment_extras": (
        "profile_payload_id",
        "occurrence_position",
        "position",
        "extra_id",
    ),
    "profile_payload_weapons": (
        "profile_payload_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "profile_payload_weapon_extras": (
        "profile_payload_id",
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
    "profile_payloads": {
        "id": "normalization_only",
        "logical_unit_id": "canonical_application_identity",
        "payload_sha256": "canonical_application_identity",
        "name": "canonical_fact",
        "type_id": "relationship",
        "move_1": "canonical_fact",
        "move_2": "canonical_fact",
        "cc": "canonical_fact",
        "bs": "canonical_fact",
        "ph": "canonical_fact",
        "wip": "canonical_fact",
        "arm": "canonical_fact",
        "bts": "canonical_fact",
        "vitality": "canonical_fact",
        "silhouette": "canonical_fact",
        "is_structure": "canonical_fact",
        "notes": "canonical_fact",
    },
    "profile_payload_occurrences": {
        "army_id": "source_context",
        "unit_id": "source_identity",
        "group_id": "source_identity",
        "profile_id": "source_identity",
        "profile_payload_id": "canonical_application_identity",
        "position": "presentation_context",
        "ava": "contextual_delta",
        "logo": "contextual_delta",
    },
}


class ProfileSemanticsAuditError(ValueError):
    """Raised when the published profile payload model cannot be audited safely."""


def _payload_hashes(connection: sqlite3.Connection) -> tuple[int, list[int]]:
    characteristics = characteristic_relationships(
        connection, "profile_payload_characteristics", "profile_payload_id"
    )
    skill_extras = extras_by_payload(
        connection, "profile_payload_skill_extras", "profile_payload_id"
    )
    equipment_extras = extras_by_payload(
        connection, "profile_payload_equipment_extras", "profile_payload_id"
    )
    weapon_extras = extras_by_payload(
        connection, "profile_payload_weapon_extras", "profile_payload_id"
    )
    skills = item_relationships(
        connection, "profile_payload_skills", "profile_payload_id", skill_extras
    )
    equipment = item_relationships(
        connection,
        "profile_payload_equipment",
        "profile_payload_id",
        equipment_extras,
    )
    weapons = item_relationships(
        connection, "profile_payload_weapons", "profile_payload_id", weapon_extras
    )

    invalid: list[int] = []
    count = 0
    for row in connection.execute("SELECT * FROM profile_payloads ORDER BY id"):
        count += 1
        payload_id = int(row["id"])
        payload = {field: row[field] for field in PAYLOAD_FIELDS}
        payload["characteristics"] = characteristics.get(payload_id, [])
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
    """Return a deterministic read-only report for the published profile payload model."""
    path = path.resolve()
    if not path.is_file():
        raise ProfileSemanticsAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        validate_schema(connection, EXPECTED_COLUMNS, ProfileSemanticsAuditError)
        payload_count, invalid_hashes = _payload_hashes(connection)
        occurrences = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM profile_payload_occurrences "
                "ORDER BY army_id, unit_id, group_id, profile_id"
            )
        ]
        source_groups = grouped_rows(occurrences, ("unit_id", "group_id", "profile_id"))
        repeated_source = {key: rows for key, rows in source_groups.items() if len(rows) > 1}
        multiple_payloads = sum(
            1
            for rows in source_groups.values()
            if len({row["profile_payload_id"] for row in rows}) > 1
        )
        payload_use = Counter(row["profile_payload_id"] for row in occurrences)
        orphan_payload_count = payload_count - len(payload_use)

        logical_mismatches = int(
            connection.execute(
                "SELECT COUNT(*) FROM profile_payload_occurrences AS ppo "
                "LEFT JOIN logical_unit_sources AS lus ON lus.source_unit_id = ppo.unit_id "
                "LEFT JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id "
                "WHERE lus.logical_unit_id IS NULL OR pp.id IS NULL "
                "OR pp.logical_unit_id != lus.logical_unit_id"
            ).fetchone()[0]
        )
        missing_groups = int(
            connection.execute(
                "SELECT COUNT(*) FROM profile_payload_occurrences AS ppo "
                "LEFT JOIN profile_groups AS pg ON pg.army_id = ppo.army_id "
                "AND pg.unit_id = ppo.unit_id AND pg.group_id = ppo.group_id "
                "WHERE pg.army_id IS NULL"
            ).fetchone()[0]
        )
        duplicate_identities = int(
            connection.execute(
                "SELECT COUNT(*) FROM (SELECT logical_unit_id, payload_sha256 "
                "FROM profile_payloads GROUP BY logical_unit_id, payload_sha256 "
                "HAVING COUNT(*) > 1)"
            ).fetchone()[0]
        )

        issues: list[str] = []
        if invalid_hashes:
            issues.append(f"{len(invalid_hashes)} profile payload hash mismatch(es)")
        if orphan_payload_count:
            issues.append(f"{orphan_payload_count} profile payload(s) have no occurrence")
        if logical_mismatches:
            issues.append(f"{logical_mismatches} profile occurrence logical-unit mismatch(es)")
        if missing_groups:
            issues.append(f"{missing_groups} profile occurrence(s) have no profile group")
        if duplicate_identities:
            issues.append(f"{duplicate_identities} duplicate profile payload identity group(s)")

        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": database_identity(connection, path),
            "fieldClassification": FIELD_CLASSIFICATION,
            "summary": {
                "status": "pass" if not issues else "fail",
                "profilePayloadCount": payload_count,
                "profileOccurrenceCount": len(occurrences),
                "repeatedSourceProfileKeyCount": len(repeated_source),
                "sourceProfileKeysWithMultiplePayloads": multiple_payloads,
                "sourceProfileKeysWithAvaVariation": variation_count(repeated_source, "ava"),
                "sourceProfileKeysWithLogoVariation": variation_count(repeated_source, "logo"),
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
    except (OSError, sqlite3.Error, ProfileSemanticsAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    summary = report["summary"]
    print("InfinityDB profile semantics audit")
    print(
        f"Profiles: {summary['profileOccurrenceCount']} occurrences -> "
        f"{summary['profilePayloadCount']} canonical payloads | "
        f"{summary['reusedPayloadCount']} reused payloads"
    )
    print(
        f"Source-key variation: {summary['sourceProfileKeysWithMultiplePayloads']} semantic | "
        f"{summary['sourceProfileKeysWithAvaVariation']} AVA | "
        f"{summary['sourceProfileKeysWithLogoVariation']} logo"
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
