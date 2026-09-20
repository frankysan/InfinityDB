"""Materialize reusable canonical loadout payloads from lossless source loadout rows."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

LOADOUT_PAYLOAD_FORMAT = "InfinityDB canonical loadout payload"
LOADOUT_PAYLOAD_FORMAT_VERSION = 1

LOADOUT_KEY = ("army_id", "unit_id", "group_id", "option_id")
PAYLOAD_FIELDS = ("name", "minis", "disabled")

_RELATIONSHIP_TABLES = {
    "characteristics": ("option_characteristics", None),
    "orders": ("option_orders", None),
    "skills": ("option_skills", "option_skill_extras"),
    "equipment": ("option_equipment", "option_equipment_extras"),
    "weapons": ("option_weapons", "option_weapon_extras"),
}


@dataclass(frozen=True)
class LoadoutPayloadMaterialization:
    """Summary of one derived canonical-loadout materialization."""

    payload_count: int
    occurrence_count: int


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _decode_raw(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _stored_raw(value: Any) -> Any:
    """Store structured raw fallback deterministically; source rows retain exact text."""
    decoded = _decode_raw(value)
    if isinstance(decoded, (dict, list)):
        return _canonical_json(decoded)
    return decoded


def _row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row[field] for field in LOADOUT_KEY)


def _relationship_rows(
    connection: sqlite3.Connection, name: str, table: str
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    result: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    if name == "weapons":
        source = connection.execute(
            "SELECT o.occurrence_id, o.army_id, o.unit_id, o.group_id, o.option_id, "
            "o.position, t.item_id, t.display_order, t.quantity, t.raw "
            "FROM option_weapons AS o "
            "JOIN option_weapon_templates AS t ON t.id = o.template_id "
            "ORDER BY o.army_id, o.unit_id, o.group_id, o.option_id, o.position"
        )
    else:
        source = connection.execute(
            f'SELECT * FROM "{table}" '
            "ORDER BY army_id, unit_id, group_id, option_id, position"
        )
    for row in source:
        item = dict(row)
        result[_row_key(item)].append(item)
    return result


def _extras_by_occurrence(
    connection: sqlite3.Connection, table: str
) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        f'SELECT * FROM "{table}" ORDER BY occurrence_id, position'
    ):
        item = dict(row)
        result[item["occurrence_id"]].append(item)
    return result


def _relationship_payload(
    name: str,
    rows: list[dict[str, Any]],
    extras: Mapping[Any, list[dict[str, Any]]] | None,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        if name == "characteristics":
            item = {"characteristic_id": row["characteristic_id"]}
        elif name == "orders":
            item = {
                "order_type": row["order_type"],
                "list_count": row["list_count"],
                "total_count": row["total_count"],
                "raw": _decode_raw(row["raw"]),
            }
        else:
            item = {
                "item_id": row["item_id"],
                "display_order": row["display_order"],
                "quantity": row["quantity"],
                "raw": _decode_raw(row["raw"]),
            }
            if extras is not None:
                item["extras"] = [
                    extra["extra_id"] for extra in extras.get(row["occurrence_id"], ())
                ]
        payload.append(item)
    return payload


def _payload(
    loadout: Mapping[str, Any],
    relationships: Mapping[str, Mapping[tuple[Any, ...], list[dict[str, Any]]]],
    extras: Mapping[str, Mapping[Any, list[dict[str, Any]]]],
) -> dict[str, Any]:
    parent = _row_key(loadout)
    payload = {field: loadout[field] for field in PAYLOAD_FIELDS}
    for name in _RELATIONSHIP_TABLES:
        payload[name] = _relationship_payload(
            name,
            relationships[name].get(parent, []),
            extras.get(name),
        )
    return payload


def _serialized_payload(payload: Mapping[str, Any]) -> str:
    return _canonical_json(
        {
            "format": LOADOUT_PAYLOAD_FORMAT,
            "formatVersion": LOADOUT_PAYLOAD_FORMAT_VERSION,
            "payload": payload,
        }
    )


def _payload_sha256(serialized: str) -> str:
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _insert_many(
    connection: sqlite3.Connection, statement: str, rows: list[tuple[Any, ...]]
) -> None:
    if rows:
        connection.executemany(statement, rows)


def materialize_loadout_payloads(
    connection: sqlite3.Connection,
) -> LoadoutPayloadMaterialization:
    """Populate derived canonical-loadout tables from already-imported source rows."""
    row_factory = connection.row_factory
    try:
        connection.row_factory = sqlite3.Row
        return _materialize_loadout_payloads(connection)
    finally:
        connection.row_factory = row_factory


def _materialize_loadout_payloads(
    connection: sqlite3.Connection,
) -> LoadoutPayloadMaterialization:
    logical_units = {
        row["source_unit_id"]: row["logical_unit_id"]
        for row in connection.execute(
            "SELECT source_unit_id, logical_unit_id "
            "FROM logical_unit_sources ORDER BY source_unit_id"
        )
    }

    relationships: dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]] = {}
    extras: dict[str, dict[Any, list[dict[str, Any]]]] = {}
    for name, (table, extras_table) in _RELATIONSHIP_TABLES.items():
        relationships[name] = _relationship_rows(connection, name, table)
        if extras_table is not None:
            extras[name] = _extras_by_occurrence(connection, extras_table)

    candidates: list[dict[str, Any]] = []
    payloads_by_identity: dict[tuple[int, str], tuple[str, dict[str, Any]]] = {}
    for row in connection.execute(
        "SELECT * FROM loadout_options ORDER BY army_id, unit_id, group_id, option_id"
    ):
        loadout = dict(row)
        source_unit_id = loadout["unit_id"]
        try:
            logical_unit_id = logical_units[source_unit_id]
        except KeyError as exc:
            raise ValueError(
                f"Loadout source unit {source_unit_id} has no logical-unit mapping"
            ) from exc

        payload = _payload(loadout, relationships, extras)
        serialized = _serialized_payload(payload)
        payload_sha256 = _payload_sha256(serialized)
        identity = (logical_unit_id, payload_sha256)
        existing = payloads_by_identity.get(identity)
        if existing is not None and existing[0] != serialized:
            raise ValueError(
                "Canonical loadout payload SHA-256 collision inside logical unit "
                f"{logical_unit_id}"
            )
        payloads_by_identity.setdefault(identity, (serialized, payload))
        candidates.append(
            {
                "loadout": loadout,
                "logical_unit_id": logical_unit_id,
                "payload_sha256": payload_sha256,
            }
        )

    payload_ids = {
        identity: payload_id
        for payload_id, identity in enumerate(sorted(payloads_by_identity), start=1)
    }

    payload_rows: list[tuple[Any, ...]] = []
    characteristic_rows: list[tuple[Any, ...]] = []
    order_rows: list[tuple[Any, ...]] = []
    skill_rows: list[tuple[Any, ...]] = []
    skill_extra_rows: list[tuple[Any, ...]] = []
    equipment_rows: list[tuple[Any, ...]] = []
    equipment_extra_rows: list[tuple[Any, ...]] = []
    weapon_rows: list[tuple[Any, ...]] = []
    weapon_extra_rows: list[tuple[Any, ...]] = []

    for identity in sorted(payloads_by_identity):
        logical_unit_id, payload_sha256 = identity
        payload_id = payload_ids[identity]
        payload = payloads_by_identity[identity][1]
        payload_rows.append(
            (
                payload_id,
                logical_unit_id,
                payload_sha256,
                *(payload[field] for field in PAYLOAD_FIELDS),
            )
        )

        for position, item in enumerate(payload["characteristics"], start=1):
            characteristic_rows.append(
                (payload_id, position, item["characteristic_id"])
            )

        for position, item in enumerate(payload["orders"], start=1):
            order_rows.append(
                (
                    payload_id,
                    position,
                    item["order_type"],
                    item["list_count"],
                    item["total_count"],
                    _stored_raw(item["raw"]),
                )
            )

        for name, rows, extra_rows in (
            ("skills", skill_rows, skill_extra_rows),
            ("equipment", equipment_rows, equipment_extra_rows),
            ("weapons", weapon_rows, weapon_extra_rows),
        ):
            for position, item in enumerate(payload[name], start=1):
                rows.append(
                    (
                        payload_id,
                        position,
                        item["item_id"],
                        item["display_order"],
                        item["quantity"],
                        _stored_raw(item["raw"]),
                    )
                )
                for extra_position, extra_id in enumerate(item["extras"], start=1):
                    extra_rows.append((payload_id, position, extra_position, extra_id))

    _insert_many(
        connection,
        "INSERT INTO loadout_payloads "
        "(id, logical_unit_id, payload_sha256, name, minis, disabled) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        payload_rows,
    )

    occurrence_rows: list[tuple[Any, ...]] = []
    for candidate in candidates:
        loadout = candidate["loadout"]
        identity = (candidate["logical_unit_id"], candidate["payload_sha256"])
        occurrence_rows.append(
            (
                loadout["army_id"],
                loadout["unit_id"],
                loadout["group_id"],
                loadout["option_id"],
                payload_ids[identity],
                loadout["position"],
                loadout["points"],
                loadout["swc"],
            )
        )
    _insert_many(
        connection,
        "INSERT INTO loadout_payload_occurrences "
        "(army_id, unit_id, group_id, option_id, loadout_payload_id, position, points, swc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        occurrence_rows,
    )

    _insert_many(
        connection,
        "INSERT INTO loadout_payload_characteristics "
        "(loadout_payload_id, position, characteristic_id) VALUES (?, ?, ?)",
        characteristic_rows,
    )
    _insert_many(
        connection,
        "INSERT INTO loadout_payload_orders "
        "(loadout_payload_id, position, order_type, list_count, total_count, raw) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        order_rows,
    )

    for table, rows in (
        ("loadout_payload_skills", skill_rows),
        ("loadout_payload_equipment", equipment_rows),
        ("loadout_payload_weapons", weapon_rows),
    ):
        _insert_many(
            connection,
            f"INSERT INTO {table} "
            "(loadout_payload_id, position, item_id, display_order, quantity, raw) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )

    for table, rows in (
        ("loadout_payload_skill_extras", skill_extra_rows),
        ("loadout_payload_equipment_extras", equipment_extra_rows),
        ("loadout_payload_weapon_extras", weapon_extra_rows),
    ):
        _insert_many(
            connection,
            f"INSERT INTO {table} "
            "(loadout_payload_id, occurrence_position, position, extra_id) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )

    return LoadoutPayloadMaterialization(
        payload_count=len(payload_rows),
        occurrence_count=len(occurrence_rows),
    )
