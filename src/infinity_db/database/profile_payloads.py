"""Materialize reusable canonical profile payloads from lossless source profile rows."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PROFILE_PAYLOAD_FORMAT = "InfinityDB canonical profile payload"
PROFILE_PAYLOAD_FORMAT_VERSION = 1

PROFILE_KEY = ("army_id", "unit_id", "group_id", "profile_id")
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

_RELATIONSHIP_TABLES = {
    "characteristics": ("profile_characteristics", None),
    "skills": ("profile_skills", "profile_skill_extras"),
    "equipment": ("profile_equipment", "profile_equipment_extras"),
    "weapons": ("profile_weapons", "profile_weapon_extras"),
}


@dataclass(frozen=True)
class ProfilePayloadMaterialization:
    """Summary of one derived canonical-profile materialization."""

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
    return tuple(row[field] for field in PROFILE_KEY)


def _relationship_rows(
    connection: sqlite3.Connection, table: str
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    result: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    query = (
        f'SELECT * FROM "{table}" '
        "ORDER BY army_id, unit_id, group_id, profile_id, position"
    )
    for row in connection.execute(query):
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
    profile: Mapping[str, Any],
    relationships: Mapping[str, Mapping[tuple[Any, ...], list[dict[str, Any]]]],
    extras: Mapping[str, Mapping[Any, list[dict[str, Any]]]],
) -> dict[str, Any]:
    parent = _row_key(profile)
    payload = {field: profile[field] for field in PAYLOAD_FIELDS}
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
            "format": PROFILE_PAYLOAD_FORMAT,
            "formatVersion": PROFILE_PAYLOAD_FORMAT_VERSION,
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


def materialize_profile_payloads(
    connection: sqlite3.Connection,
) -> ProfilePayloadMaterialization:
    """Populate the derived canonical-profile tables from already-imported source rows."""
    row_factory = connection.row_factory
    try:
        connection.row_factory = sqlite3.Row
        return _materialize_profile_payloads(connection)
    finally:
        connection.row_factory = row_factory


def _materialize_profile_payloads(
    connection: sqlite3.Connection,
) -> ProfilePayloadMaterialization:
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
        relationships[name] = _relationship_rows(connection, table)
        if extras_table is not None:
            extras[name] = _extras_by_occurrence(connection, extras_table)

    candidates: list[dict[str, Any]] = []
    payloads_by_identity: dict[tuple[int, str], tuple[str, dict[str, Any]]] = {}
    for row in connection.execute(
        "SELECT * FROM profiles ORDER BY army_id, unit_id, group_id, profile_id"
    ):
        profile = dict(row)
        source_unit_id = profile["unit_id"]
        try:
            logical_unit_id = logical_units[source_unit_id]
        except KeyError as exc:
            raise ValueError(
                f"Profile source unit {source_unit_id} has no logical-unit mapping"
            ) from exc

        payload = _payload(profile, relationships, extras)
        serialized = _serialized_payload(payload)
        payload_sha256 = _payload_sha256(serialized)
        identity = (logical_unit_id, payload_sha256)
        existing = payloads_by_identity.get(identity)
        if existing is not None and existing[0] != serialized:
            raise ValueError(
                "Canonical profile payload SHA-256 collision inside logical unit "
                f"{logical_unit_id}"
            )
        payloads_by_identity.setdefault(identity, (serialized, payload))
        candidates.append(
            {
                "profile": profile,
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
                    extra_rows.append(
                        (payload_id, position, extra_position, extra_id)
                    )

    _insert_many(
        connection,
        "INSERT INTO profile_payloads "
        "(id, logical_unit_id, payload_sha256, name, type_id, move_1, move_2, cc, bs, ph, "
        "wip, arm, bts, vitality, silhouette, is_structure, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        payload_rows,
    )

    occurrence_rows: list[tuple[Any, ...]] = []
    for candidate in candidates:
        profile = candidate["profile"]
        identity = (
            candidate["logical_unit_id"],
            candidate["payload_sha256"],
        )
        occurrence_rows.append(
            (
                profile["army_id"],
                profile["unit_id"],
                profile["group_id"],
                profile["profile_id"],
                payload_ids[identity],
                profile["position"],
                profile["ava"],
                profile["logo"],
            )
        )
    _insert_many(
        connection,
        "INSERT INTO profile_payload_occurrences "
        "(army_id, unit_id, group_id, profile_id, profile_payload_id, position, ava, logo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        occurrence_rows,
    )

    _insert_many(
        connection,
        "INSERT INTO profile_payload_characteristics "
        "(profile_payload_id, position, characteristic_id) VALUES (?, ?, ?)",
        characteristic_rows,
    )

    for table, rows in (
        ("profile_payload_skills", skill_rows),
        ("profile_payload_equipment", equipment_rows),
        ("profile_payload_weapons", weapon_rows),
    ):
        _insert_many(
            connection,
            f"INSERT INTO {table} "
            "(profile_payload_id, position, item_id, display_order, quantity, raw) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )

    for table, rows in (
        ("profile_payload_skill_extras", skill_extra_rows),
        ("profile_payload_equipment_extras", equipment_extra_rows),
        ("profile_payload_weapon_extras", weapon_extra_rows),
    ):
        _insert_many(
            connection,
            f"INSERT INTO {table} "
            "(profile_payload_id, occurrence_position, position, extra_id) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )

    return ProfilePayloadMaterialization(
        payload_count=len(payload_rows),
        occurrence_count=len(occurrence_rows),
    )
