#!/usr/bin/env python3
"""Audit exact semantic duplication in InfinityDB profile and loadout payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REPORT_FORMAT = "InfinityDB semantic deduplication audit"
REPORT_FORMAT_VERSION = 1

PROFILE_KEY = ("army_id", "unit_id", "group_id", "profile_id")
LOADOUT_KEY = ("army_id", "unit_id", "group_id", "option_id")

PROFILE_FIELDS = (
    "name",
    "logo",
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
    "ava",
    "is_structure",
    "notes",
)
LOADOUT_FIELDS = ("name", "points", "swc", "minis", "disabled")
ITEM_FIELDS = ("item_id", "display_order", "quantity", "raw")
CHARACTERISTIC_FIELDS = ("characteristic_id",)
INCLUDE_FIELDS = ("target_group_id", "target_option_id", "quantity", "raw")
ORDER_FIELDS = ("order_type", "list_count", "total_count", "raw")
EXTRA_FIELDS = ("extra_id",)
TEMPLATE_FIELDS = ("item_id", "display_order", "quantity", "raw")

PROFILE_CHILDREN = (
    ("characteristics", "profile_characteristics", PROFILE_KEY, CHARACTERISTIC_FIELDS, None),
    ("skills", "profile_skills", PROFILE_KEY, ITEM_FIELDS, "profile_skill_extras"),
    ("equipment", "profile_equipment", PROFILE_KEY, ITEM_FIELDS, "profile_equipment_extras"),
    ("weapons", "profile_weapons", PROFILE_KEY, ITEM_FIELDS, "profile_weapon_extras"),
    ("includes", "profile_includes", PROFILE_KEY, INCLUDE_FIELDS, None),
    ("peripherals", "profile_peripherals", PROFILE_KEY, ITEM_FIELDS, None),
)
LOADOUT_CHILDREN = (
    ("characteristics", "option_characteristics", LOADOUT_KEY, CHARACTERISTIC_FIELDS, None),
    ("orders", "option_orders", LOADOUT_KEY, ORDER_FIELDS, None),
    ("skills", "option_skills", LOADOUT_KEY, ITEM_FIELDS, "option_skill_extras"),
    ("equipment", "option_equipment", LOADOUT_KEY, ITEM_FIELDS, "option_equipment_extras"),
    ("includes", "option_includes", LOADOUT_KEY, INCLUDE_FIELDS, None),
    ("peripherals", "option_peripherals", LOADOUT_KEY, ITEM_FIELDS, None),
)

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "profiles": (*PROFILE_KEY, "position", *PROFILE_FIELDS),
    "loadout_options": (*LOADOUT_KEY, "position", *LOADOUT_FIELDS),
    "profile_characteristics": (*PROFILE_KEY, "position", *CHARACTERISTIC_FIELDS),
    "profile_skills": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "profile_skill_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "profile_equipment": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "profile_equipment_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "profile_weapons": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "profile_weapon_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "profile_includes": (*PROFILE_KEY, "position", *INCLUDE_FIELDS),
    "profile_peripherals": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "option_characteristics": (*LOADOUT_KEY, "position", *CHARACTERISTIC_FIELDS),
    "option_orders": (*LOADOUT_KEY, "position", *ORDER_FIELDS),
    "option_skills": ("occurrence_id", *LOADOUT_KEY, "position", *ITEM_FIELDS),
    "option_skill_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "option_equipment": ("occurrence_id", *LOADOUT_KEY, "position", *ITEM_FIELDS),
    "option_equipment_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "option_weapons": ("occurrence_id", *LOADOUT_KEY, "position", "template_id"),
    "option_weapon_templates": ("id", *TEMPLATE_FIELDS),
    "option_weapon_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "option_includes": (*LOADOUT_KEY, "position", *INCLUDE_FIELDS),
    "option_peripherals": ("occurrence_id", *LOADOUT_KEY, "position", *ITEM_FIELDS),
    "logical_units": ("id", "representative_unit_id"),
    "logical_unit_sources": ("source_unit_id", "logical_unit_id"),
    "__infinity_metadata": ("key", "value"),
}


class SemanticDeduplicationAuditError(ValueError):
    """Raised when the selected database cannot be audited safely."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_raw(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _payload_fields(row: Mapping[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {
        field: _decode_raw(row[field]) if field == "raw" else row[field]
        for field in fields
    }


def _row_key(row: Mapping[str, Any], fields: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(row[field] for field in fields)


def _columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")'))


def _validate_schema(connection: sqlite3.Connection) -> None:
    for table, expected in REQUIRED_COLUMNS.items():
        actual = _columns(connection, table)
        if not actual:
            raise SemanticDeduplicationAuditError(f"Required table is missing: {table}")
        unexpected = sorted(set(actual) - set(expected))
        missing = sorted(set(expected) - set(actual))
        if unexpected or missing:
            details = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if unexpected:
                details.append(f"unclassified {', '.join(unexpected)}")
            raise SemanticDeduplicationAuditError(
                f"Audit field classification for {table} is stale ({'; '.join(details)})"
            )


def _read_rows(
    connection: sqlite3.Connection,
    table: str,
    parent_key: tuple[str, ...],
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    result: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    order = ", ".join((*parent_key, "position"))
    for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY {order}'):
        item = dict(row)
        result[_row_key(item, parent_key)].append(item)
    return result


def _read_extras(
    connection: sqlite3.Connection, table: str
) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        f'SELECT * FROM "{table}" ORDER BY occurrence_id, position'
    ):
        item = dict(row)
        result[item["occurrence_id"]].append(item)
    return result


def _child_payloads(
    rows: list[dict[str, Any]],
    fields: tuple[str, ...],
    extras: dict[Any, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    payloads = []
    for row in rows:
        item = _payload_fields(row, fields)
        if extras is not None:
            item["extras"] = [
                _payload_fields(extra, EXTRA_FIELDS)
                for extra in extras.get(row["occurrence_id"], ())
            ]
        payloads.append(item)
    return payloads


def _metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', ("_meta",)
    ).fetchone()
    if row is None:
        return {}
    try:
        value = json.loads(row["value"])
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _metadata_value(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', (key,)
    ).fetchone()
    return None if row is None else row["value"]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_definitions() -> dict[str, Any]:
    def child(
        name: str,
        table: str,
        fields: tuple[str, ...],
        extras: str | None,
    ) -> dict[str, Any]:
        table_columns = REQUIRED_COLUMNS[table]
        excluded = [
            field
            for field in table_columns
            if field not in fields
        ]
        result: dict[str, Any] = {
            "name": name,
            "table": table,
            "includedFields": list(fields),
            "excludedFields": excluded,
        }
        if extras is not None:
            result["extrasTable"] = extras
            result["extraIncludedFields"] = list(EXTRA_FIELDS)
        return result

    profile_children = [
        child(name, table, fields, extras)
        for name, table, _key, fields, extras in PROFILE_CHILDREN
    ]
    loadout_children = [
        child(name, table, fields, extras)
        for name, table, _key, fields, extras in LOADOUT_CHILDREN
    ]
    loadout_children.append(
        {
            "name": "weapons",
            "table": "option_weapons + option_weapon_templates",
            "includedFields": list(TEMPLATE_FIELDS),
            "excludedFields": [
                "occurrence_id",
                *LOADOUT_KEY,
                "position",
                "template_id",
                "option_weapon_templates.id",
            ],
            "extrasTable": "option_weapon_extras",
            "extraIncludedFields": list(EXTRA_FIELDS),
        }
    )
    return {
        "profile": {
            "table": "profiles",
            "includedFields": list(PROFILE_FIELDS),
            "excludedFields": [*PROFILE_KEY, "position"],
            "children": profile_children,
        },
        "loadout": {
            "table": "loadout_options",
            "includedFields": list(LOADOUT_FIELDS),
            "excludedFields": [*LOADOUT_KEY, "position"],
            "children": loadout_children,
        },
        "ordering": (
            "Literal position values are excluded, but child rows and extras remain ordered by "
            "position; changing their relative order therefore changes the payload."
        ),
        "rawJson": (
            "raw fields are parsed as JSON when valid, so JSON whitespace and object key order "
            "do not create distinct payloads."
        ),
        "firstPassBoundary": (
            "Referenced target_group_id/target_option_id and catalog item IDs remain part of "
            "the first-pass payload until their identities are canonicalized separately."
        ),
        "contextBoundary": (
            "profile_groups and wider unit/army context are outside these payloads and remain "
            "context for later classification."
        ),
    }


def _profile_payloads(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    child_rows = {
        table: _read_rows(connection, table, key)
        for _name, table, key, _fields, _extras in PROFILE_CHILDREN
    }
    extras = {
        extras_table: _read_extras(connection, extras_table)
        for _name, _table, _key, _fields, extras_table in PROFILE_CHILDREN
        if extras_table is not None
    }
    result = []
    for row in connection.execute(
        "SELECT * FROM profiles ORDER BY army_id, unit_id, group_id, profile_id"
    ):
        source = dict(row)
        parent = _row_key(source, PROFILE_KEY)
        payload = _payload_fields(source, PROFILE_FIELDS)
        for name, table, _key, fields, extras_table in PROFILE_CHILDREN:
            payload[name] = _child_payloads(
                child_rows[table].get(parent, []),
                fields,
                extras.get(extras_table) if extras_table else None,
            )
        result.append(
            {
                "kind": "profile",
                "unitId": source["unit_id"],
                "occurrence": {
                    "armyId": source["army_id"],
                    "unitId": source["unit_id"],
                    "groupId": source["group_id"],
                    "profileId": source["profile_id"],
                },
                "payload": payload,
            }
        )
    return result


def _loadout_payloads(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    child_rows = {
        table: _read_rows(connection, table, key)
        for _name, table, key, _fields, _extras in LOADOUT_CHILDREN
    }
    extras = {
        extras_table: _read_extras(connection, extras_table)
        for _name, _table, _key, _fields, extras_table in LOADOUT_CHILDREN
        if extras_table is not None
    }
    weapon_extras = _read_extras(connection, "option_weapon_extras")
    weapons: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    query = """
        SELECT o.occurrence_id, o.army_id, o.unit_id, o.group_id, o.option_id,
               o.position, t.item_id, t.display_order, t.quantity, t.raw
        FROM option_weapons AS o
        JOIN option_weapon_templates AS t ON t.id = o.template_id
        ORDER BY o.army_id, o.unit_id, o.group_id, o.option_id, o.position
    """
    for row in connection.execute(query):
        item = dict(row)
        weapons[_row_key(item, LOADOUT_KEY)].append(item)

    result = []
    for row in connection.execute(
        "SELECT * FROM loadout_options ORDER BY army_id, unit_id, group_id, option_id"
    ):
        source = dict(row)
        parent = _row_key(source, LOADOUT_KEY)
        payload = _payload_fields(source, LOADOUT_FIELDS)
        for name, table, _key, fields, extras_table in LOADOUT_CHILDREN:
            payload[name] = _child_payloads(
                child_rows[table].get(parent, []),
                fields,
                extras.get(extras_table) if extras_table else None,
            )
        payload["weapons"] = _child_payloads(
            weapons.get(parent, []), TEMPLATE_FIELDS, weapon_extras
        )
        result.append(
            {
                "kind": "loadout",
                "unitId": source["unit_id"],
                "occurrence": {
                    "armyId": source["army_id"],
                    "unitId": source["unit_id"],
                    "groupId": source["group_id"],
                    "optionId": source["option_id"],
                },
                "payload": payload,
            }
        )
    return result


def _logical_units(connection: sqlite3.Connection) -> dict[int, int]:
    mapping = {
        row["source_unit_id"]: row["logical_unit_id"]
        for row in connection.execute(
            "SELECT source_unit_id, logical_unit_id "
            "FROM logical_unit_sources ORDER BY source_unit_id"
        )
    }
    return mapping


def _fingerprint(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _scope_result(
    records: list[dict[str, Any]],
    *,
    scope_name: str,
    group_ids: Mapping[int, int] | None = None,
    include_details: bool = False,
) -> dict[str, Any]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        source_unit_id = record["unitId"]
        if group_ids is None:
            group_id = source_unit_id
        else:
            try:
                group_id = group_ids[source_unit_id]
            except KeyError as exc:
                raise SemanticDeduplicationAuditError(
                    f"Source unit {source_unit_id} has no logical-unit mapping"
                ) from exc
        fingerprint = _fingerprint(record["payload"])
        groups[(group_id, fingerprint)].append(record["occurrence"])

    distinct = len(groups)
    occurrences = len(records)
    repeated = occurrences - distinct
    duplicate_groups = []
    for (group_id, fingerprint), occurrences_for_payload in sorted(groups.items()):
        if len(occurrences_for_payload) <= 1:
            continue
        duplicate_groups.append(
            {
                f"{scope_name}Id": group_id,
                "payloadSha256": fingerprint,
                "occurrenceCount": len(occurrences_for_payload),
                "occurrences": occurrences_for_payload,
            }
        )
    result = {
        "scope": scope_name,
        "storedOccurrences": occurrences,
        "distinctPayloads": distinct,
        "repeatedOccurrences": repeated,
        "repeatPercent": round((repeated / occurrences * 100) if occurrences else 0.0, 2),
        "duplicateGroupCount": len(duplicate_groups),
    }
    if include_details:
        result["duplicateGroups"] = duplicate_groups
    return result


def _kind_result(
    records: list[dict[str, Any]],
    logical_mapping: Mapping[int, int],
    *,
    include_details: bool = False,
) -> dict[str, Any]:
    source = _scope_result(
        records, scope_name="sourceUnit", include_details=include_details
    )
    logical = _scope_result(
        records,
        scope_name="logicalUnit",
        group_ids=logical_mapping,
        include_details=include_details,
    )
    return {
        "storedOccurrences": len(records),
        "sourceUnit": source,
        "logicalUnit": logical,
        "additionalDistinctPayloadReductionFromLogicalIdentity": (
            source["distinctPayloads"] - logical["distinctPayloads"]
        ),
    }


def audit_database(path: Path, *, include_details: bool = False) -> dict[str, Any]:
    """Return a deterministic read-only semantic-duplication report for one frontend DB."""
    path = path.resolve()
    if not path.is_file():
        raise SemanticDeduplicationAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_schema(connection)
        metadata = _metadata(connection)
        logical_mapping = _logical_units(connection)
        profiles = _profile_payloads(connection)
        loadouts = _loadout_payloads(connection)
        report = {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "sha256": _sha256_file(path),
                "applicationId": connection.execute("PRAGMA application_id").fetchone()[0],
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "compatibilityVersion": _metadata_value(
                    connection, "database_compatibility_version"
                ),
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "payloadDefinitions": _payload_definitions(),
            "profiles": _kind_result(
                profiles, logical_mapping, include_details=include_details
            ),
            "loadouts": _kind_result(
                loadouts, logical_mapping, include_details=include_details
            ),
        }
    finally:
        connection.close()
    return report


def _summary_line(label: str, result: Mapping[str, Any]) -> str:
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
    parser.add_argument("database", type=Path, help="Frontend infinity.db to audit")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional deterministic JSON report path",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Include every repeated payload group and its source occurrences in JSON output",
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
