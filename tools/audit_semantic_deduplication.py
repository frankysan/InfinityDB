#!/usr/bin/env python3
"""Audit canonical profile/loadout payload reuse in the published InfinityDB database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__:
    from .payload_audit_common import database_identity, validate_schema
else:
    from payload_audit_common import database_identity, validate_schema

REPORT_FORMAT = "InfinityDB semantic deduplication audit"
REPORT_FORMAT_VERSION = 2

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "profile_payloads": (
        "id", "logical_unit_id", "payload_sha256", "name", "type_id", "move_1", "move_2",
        "cc", "bs", "ph", "wip", "arm", "bts", "vitality", "silhouette",
        "is_structure", "notes",
    ),
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
    "loadout_payloads": (
        "id", "logical_unit_id", "payload_sha256", "name", "minis", "disabled",
    ),
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
    "logical_unit_sources": ("source_unit_id", "logical_unit_id"),
    "__infinity_metadata": ("key", "value"),
}


class SemanticDeduplicationAuditError(ValueError):
    """Raised when canonical payload reuse cannot be audited safely."""


def _kind_result(
    connection: sqlite3.Connection,
    *,
    payload_table: str,
    occurrence_table: str,
    payload_id_field: str,
    include_details: bool,
) -> dict[str, Any]:
    query = f"""
        SELECT o.unit_id,
               lus.logical_unit_id,
               o.{payload_id_field} AS payload_id,
               p.payload_sha256
        FROM {occurrence_table} AS o
        JOIN logical_unit_sources AS lus ON lus.source_unit_id = o.unit_id
        JOIN {payload_table} AS p ON p.id = o.{payload_id_field}
        ORDER BY o.unit_id, lus.logical_unit_id, o.{payload_id_field}
    """
    records = [dict(row) for row in connection.execute(query)]

    def scope(field: str, label: str) -> dict[str, Any]:
        groups: dict[tuple[int, str], list[int]] = defaultdict(list)
        for index, row in enumerate(records):
            groups[(int(row[field]), str(row["payload_sha256"]))].append(index)
        repeated = len(records) - len(groups)
        result: dict[str, Any] = {
            "scope": label,
            "storedOccurrences": len(records),
            "distinctPayloads": len(groups),
            "repeatedOccurrences": repeated,
            "repeatPercent": round((repeated / len(records) * 100) if records else 0.0, 2),
            "duplicateGroupCount": sum(1 for indexes in groups.values() if len(indexes) > 1),
        }
        if include_details:
            result["duplicateGroups"] = [
                {
                    f"{label}Id": group_id,
                    "payloadSha256": payload_sha256,
                    "occurrenceCount": len(indexes),
                }
                for (group_id, payload_sha256), indexes in sorted(groups.items())
                if len(indexes) > 1
            ]
        return result

    source = scope("unit_id", "sourceUnit")
    logical = scope("logical_unit_id", "logicalUnit")
    return {
        "storedOccurrences": len(records),
        "sourceUnit": source,
        "logicalUnit": logical,
        "additionalDistinctPayloadReductionFromLogicalIdentity": (
            source["distinctPayloads"] - logical["distinctPayloads"]
        ),
    }


def audit_database(path: Path, *, include_details: bool = False) -> dict[str, Any]:
    """Return a deterministic read-only payload-reuse report for one published DB."""
    path = path.resolve()
    if not path.is_file():
        raise SemanticDeduplicationAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        validate_schema(connection, REQUIRED_COLUMNS, SemanticDeduplicationAuditError)
        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": database_identity(connection, path),
            "payloadDefinitions": {
                "profile": {
                    "payloadTable": "profile_payloads",
                    "occurrenceTable": "profile_payload_occurrences",
                    "contextualOccurrenceFields": ["ava", "logo"],
                },
                "loadout": {
                    "payloadTable": "loadout_payloads",
                    "occurrenceTable": "loadout_payload_occurrences",
                    "contextualOccurrenceFields": ["points", "swc"],
                },
                "scope": (
                    "Canonical payload identities are scoped to logical Unit identity. "
                    "Source occurrences may reuse one canonical payload while retaining "
                    "Army-specific contextual fields in occurrence tables."
                ),
            },
            "profiles": _kind_result(
                connection,
                payload_table="profile_payloads",
                occurrence_table="profile_payload_occurrences",
                payload_id_field="profile_payload_id",
                include_details=include_details,
            ),
            "loadouts": _kind_result(
                connection,
                payload_table="loadout_payloads",
                occurrence_table="loadout_payload_occurrences",
                payload_id_field="loadout_payload_id",
                include_details=include_details,
            ),
        }
    finally:
        connection.close()


def _summary_line(label: str, result: dict[str, Any]) -> str:
    source = result["sourceUnit"]
    logical = result["logicalUnit"]
    return (
        f"{label:<9} {result['storedOccurrences']:>6} occurrences | "
        f"{source['distinctPayloads']:>5} source-unit payloads "
        f"({source['repeatPercent']:.2f}% repeated) | "
        f"{logical['distinctPayloads']:>5} logical-unit payloads "
        f"({logical['repeatPercent']:.2f}% repeated)"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Published infinity.db to audit")
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    parser.add_argument(
        "--details",
        action="store_true",
        help="Include repeated payload groups in JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database, include_details=args.details)
    except (OSError, sqlite3.Error, SemanticDeduplicationAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("InfinityDB semantic deduplication audit")
    print(_summary_line("Profiles", report["profiles"]))
    print(_summary_line("Loadouts", report["loadouts"]))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
