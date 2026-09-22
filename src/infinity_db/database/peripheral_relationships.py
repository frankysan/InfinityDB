"""Materialize reviewed Peripheral identities and Controller access relationships."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import Any

from ..peripheral_identities import (
    PERIPHERAL_IDENTITY_METADATA_KEY,
    PERIPHERAL_IDENTITY_SHA256_METADATA_KEY,
    PeripheralIdentityCurated,
    PeripheralIdentityError,
    parse_peripheral_identity_metadata,
    peripheral_identity_source_for_snapshot,
)
from .schema import METADATA_TABLE

PERIPHERAL_APPLICATION_TABLES = (
    "application_peripheral_entities",
    "application_peripheral_profiles",
    "application_peripheral_sources",
    "application_peripheral_unit_sources",
    "application_peripheral_controller_access",
    "application_peripheral_controller_targets",
)

_TYPE_SOURCE_LABELS = {
    "rule:peripheral-type:servant": "servant",
    "rule:peripheral-type:synchronized": "synchronized",
    "rule:peripheral-type:control": "control",
    "rule:peripheral-type:ancillary": "ancillary",
    "rule:peripheral-type:cyberplug": "cyberplug",
}


def _metadata_value(connection: sqlite3.Connection, key: str) -> Any | None:
    row = connection.execute(
        f"SELECT value FROM {METADATA_TABLE} WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Database has invalid metadata value for {key!r}") from exc


def _curated_from_connection(
    connection: sqlite3.Connection,
) -> PeripheralIdentityCurated | None:
    document = _metadata_value(connection, PERIPHERAL_IDENTITY_METADATA_KEY)
    digest = _metadata_value(connection, PERIPHERAL_IDENTITY_SHA256_METADATA_KEY)
    if document is None and digest is None:
        return None
    if document is None or digest is None:
        raise ValueError(
            "Database has incomplete Peripheral identity metadata; rebuild the database"
        )
    try:
        return parse_peripheral_identity_metadata(document, digest)
    except PeripheralIdentityError as exc:
        raise ValueError(
            "Database has invalid Peripheral identity metadata; rebuild the database"
        ) from exc


def _selected_source_id(
    connection: sqlite3.Connection, curated: PeripheralIdentityCurated
) -> str:
    meta = _metadata_value(connection, "_meta")
    snapshot_sha256 = meta.get("snapshotArchiveSha256") if isinstance(meta, dict) else None
    try:
        source_id = peripheral_identity_source_for_snapshot(curated, snapshot_sha256)
    except PeripheralIdentityError as exc:
        raise ValueError("Database Peripheral identity source selection is ambiguous") from exc
    if source_id is None:
        raise ValueError(
            "Peripheral identity data does not match the database Army snapshot; "
            "rebuild with reviewed data"
        )
    return source_id


def _source_name(
    connection: sqlite3.Connection, table: str, where: str, values: tuple[Any, ...]
) -> str | None:
    row = connection.execute(f"SELECT name FROM {table} WHERE {where}", values).fetchone()
    return None if row is None else row[0]


def _unit_peripheral_subtypes(connection: sqlite3.Connection, unit_id: int) -> set[str]:
    rows = connection.execute(
        "SELECT DISTINCT lower(trim(x.name)) "
        "FROM profiles AS p "
        "JOIN profile_skills AS ps "
        "ON ps.army_id = p.army_id AND ps.unit_id = p.unit_id "
        "AND ps.group_id = p.group_id AND ps.profile_id = p.profile_id "
        "JOIN skills AS s ON s.id = ps.item_id "
        "JOIN profile_skill_extras AS e ON e.occurrence_id = ps.occurrence_id "
        "JOIN extras AS x ON x.id = e.extra_id "
        "WHERE p.unit_id = ? AND lower(trim(s.name)) = 'peripheral'",
        (unit_id,),
    ).fetchall()
    return {str(row[0]) for row in rows if row[0] is not None}


def _controller_has_cyberplug(
    connection: sqlite3.Connection,
    *,
    kind: str,
    army_id: int,
    unit_id: int,
    group_id: int,
    parent_id: int,
) -> bool:
    if kind == "profile":
        row = connection.execute(
            "SELECT 1 FROM profile_skills AS ps "
            "JOIN skills AS s ON s.id = ps.item_id "
            "WHERE ps.army_id = ? AND ps.unit_id = ? AND ps.group_id = ? "
            "AND ps.profile_id = ? AND lower(trim(s.name)) = 'cyberplug' LIMIT 1",
            (army_id, unit_id, group_id, parent_id),
        ).fetchone()
        return row is not None

    direct = connection.execute(
        "SELECT 1 FROM option_skills AS os "
        "JOIN skills AS s ON s.id = os.item_id "
        "WHERE os.army_id = ? AND os.unit_id = ? AND os.group_id = ? "
        "AND os.option_id = ? AND lower(trim(s.name)) = 'cyberplug' LIMIT 1",
        (army_id, unit_id, group_id, parent_id),
    ).fetchone()
    if direct is not None:
        return True
    inherited = connection.execute(
        "SELECT 1 FROM profile_skills AS ps "
        "JOIN skills AS s ON s.id = ps.item_id "
        "WHERE ps.army_id = ? AND ps.unit_id = ? AND ps.group_id = ? "
        "AND lower(trim(s.name)) = 'cyberplug' LIMIT 1",
        (army_id, unit_id, group_id),
    ).fetchone()
    return inherited is not None


def _expected_rows(
    connection: sqlite3.Connection, curated: PeripheralIdentityCurated
) -> dict[str, list[tuple[Any, ...]]]:
    document = curated.document
    source_id = _selected_source_id(connection, curated)
    entities_by_id = {item["id"]: item for item in document["entities"]}
    profiles_by_id = {item["id"]: item for item in document["profiles"]}

    mappings = [item for item in document["mappings"] if item["sourceId"] == source_id]
    unit_mappings = [
        item for item in document["unitMappings"] if item["sourceId"] == source_id
    ]
    controller_access = [
        item for item in document["controllerAccess"] if item["sourceId"] == source_id
    ]

    referenced_entity_ids = {item["entityId"] for item in mappings}
    referenced_profile_ids = {
        item["profileId"] for item in mappings if item.get("profileId") is not None
    }

    entity_rows: list[tuple[Any, ...]] = []
    for entity_id in sorted(referenced_entity_ids):
        entity = entities_by_id[entity_id]
        entity_rows.append((entity_id, entity["name"], entity.get("typeId")))

    profile_rows: list[tuple[Any, ...]] = []
    for profile_id in sorted(referenced_profile_ids):
        profile = profiles_by_id[profile_id]
        profile_rows.append(
            (profile_id, profile["entityId"], profile["name"], profile.get("mode"))
        )

    source_rows: list[tuple[Any, ...]] = []
    for mapping in sorted(mappings, key=lambda item: (item["armyId"], item["peripheralId"])):
        actual_name = _source_name(
            connection,
            "peripherals",
            "army_id = ? AND id = ?",
            (mapping["armyId"], mapping["peripheralId"]),
        )
        if actual_name != mapping["sourceName"]:
            raise ValueError(
                "Reviewed Peripheral source mapping drifted from the Army snapshot: "
                f"army {mapping['armyId']} peripheral {mapping['peripheralId']}"
            )
        source_rows.append(
            (
                mapping["armyId"],
                mapping["peripheralId"],
                mapping["entityId"],
                mapping.get("profileId"),
                source_id,
                mapping["sourceName"],
            )
        )

    unit_rows: list[tuple[Any, ...]] = []
    unit_mapping_types: dict[int, set[str]] = {}
    for mapping in sorted(unit_mappings, key=lambda item: item["unitId"]):
        row = connection.execute(
            "SELECT u.name, lus.logical_unit_id FROM units AS u "
            "JOIN logical_unit_sources AS lus ON lus.source_unit_id = u.id "
            "WHERE u.id = ?",
            (mapping["unitId"],),
        ).fetchone()
        if row is None or row[0] != mapping["sourceName"] or row[1] != mapping["logicalUnitId"]:
            raise ValueError(
                "Reviewed Unit-backed Peripheral identity drifted from the Army snapshot: "
                f"unit {mapping['unitId']}"
            )
        expected_label = _TYPE_SOURCE_LABELS[mapping["typeId"]]
        if expected_label not in _unit_peripheral_subtypes(connection, mapping["unitId"]):
            raise ValueError(
                "Reviewed Unit-backed Peripheral type drifted from the Army snapshot: "
                f"unit {mapping['unitId']}"
            )
        unit_rows.append(
            (
                mapping["unitId"],
                mapping["logicalUnitId"],
                mapping["typeId"],
                source_id,
                mapping["sourceName"],
            )
        )
        unit_mapping_types.setdefault(mapping["logicalUnitId"], set()).add(mapping["typeId"])

    access_rows: list[tuple[Any, ...]] = []
    target_rows: list[tuple[Any, ...]] = []
    unit_mappings_by_type = {
        type_id: [item for item in unit_mappings if item["typeId"] == type_id]
        for type_id in _TYPE_SOURCE_LABELS
    }
    for access in sorted(controller_access, key=lambda item: item["id"]):
        if access["controllerKind"] == "loadout":
            parent_table = "loadout_options"
            parent_id_field = "option_id"
        else:
            parent_table = "profiles"
            parent_id_field = "profile_id"
        actual_name = _source_name(
            connection,
            parent_table,
            f"army_id = ? AND unit_id = ? AND group_id = ? AND {parent_id_field} = ?",
            (access["armyId"], access["unitId"], access["groupId"], access["parentId"]),
        )
        if actual_name != access["sourceName"]:
            raise ValueError(
                "Reviewed Peripheral Controller occurrence drifted from the Army snapshot: "
                f"{access['armyId']}:{access['unitId']}:{access['groupId']}:{access['parentId']}"
            )
        if access["typeId"] == "rule:peripheral-type:cyberplug" and not _controller_has_cyberplug(
            connection,
            kind=access["controllerKind"],
            army_id=access["armyId"],
            unit_id=access["unitId"],
            group_id=access["groupId"],
            parent_id=access["parentId"],
        ):
            raise ValueError(
                "Reviewed Cyberplug Controller no longer has the Cyberplug Skill: "
                f"{access['armyId']}:{access['unitId']}:{access['groupId']}:{access['parentId']}"
            )

        available_targets = {
            mapping["logicalUnitId"]
            for mapping in unit_mappings_by_type.get(access["typeId"], [])
            if connection.execute(
                "SELECT 1 FROM army_units WHERE army_id = ? AND unit_id = ? LIMIT 1",
                (access["armyId"], mapping["unitId"]),
            ).fetchone()
            is not None
        }
        reviewed_targets = set(access["targetLogicalUnitIds"])
        if available_targets != reviewed_targets:
            raise ValueError(
                "Reviewed Peripheral Controller target pool drifted from the Army snapshot: "
                f"{access['id']}"
            )
        for target_id in reviewed_targets:
            if access["typeId"] not in unit_mapping_types.get(target_id, set()):
                raise ValueError(
                    f"Reviewed Peripheral target logical Unit {target_id} has no matching type"
                )

        access_rows.append(
            (
                access["id"],
                source_id,
                access["controllerKind"],
                access["armyId"],
                access["unitId"],
                access["groupId"],
                access["parentId"],
                access["sourceName"],
                access["typeId"],
                access["relationship"],
            )
        )
        target_rows.extend(
            (access["id"], target_id) for target_id in sorted(reviewed_targets)
        )

    return {
        "application_peripheral_entities": entity_rows,
        "application_peripheral_profiles": profile_rows,
        "application_peripheral_sources": source_rows,
        "application_peripheral_unit_sources": unit_rows,
        "application_peripheral_controller_access": access_rows,
        "application_peripheral_controller_targets": target_rows,
    }


def _insert_rows(
    connection: sqlite3.Connection,
    table: str,
    columns: tuple[str, ...],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows
    )


def materialize_peripheral_relationships(
    connection: sqlite3.Connection, curated: PeripheralIdentityCurated | None
) -> None:
    """Persist reviewed Peripheral identities/relationships for the current snapshot."""
    if curated is None:
        return
    rows = _expected_rows(connection, curated)
    _insert_rows(
        connection,
        "application_peripheral_entities",
        ("id", "name", "type_id"),
        rows["application_peripheral_entities"],
    )
    _insert_rows(
        connection,
        "application_peripheral_profiles",
        ("id", "entity_id", "name", "mode"),
        rows["application_peripheral_profiles"],
    )
    _insert_rows(
        connection,
        "application_peripheral_sources",
        ("army_id", "peripheral_id", "entity_id", "profile_id", "source_id", "source_name"),
        rows["application_peripheral_sources"],
    )
    _insert_rows(
        connection,
        "application_peripheral_unit_sources",
        ("source_unit_id", "logical_unit_id", "type_id", "source_id", "source_name"),
        rows["application_peripheral_unit_sources"],
    )
    _insert_rows(
        connection,
        "application_peripheral_controller_access",
        (
            "id",
            "source_id",
            "controller_kind",
            "army_id",
            "unit_id",
            "group_id",
            "parent_id",
            "source_name",
            "type_id",
            "relationship",
        ),
        rows["application_peripheral_controller_access"],
    )
    _insert_rows(
        connection,
        "application_peripheral_controller_targets",
        ("access_id", "target_logical_unit_id"),
        rows["application_peripheral_controller_targets"],
    )


def _table_rows(
    connection: sqlite3.Connection, table: str, columns: tuple[str, ...]
) -> list[tuple[Any, ...]]:
    rows = connection.execute(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY {', '.join(columns)}"
    ).fetchall()
    return [tuple(row) for row in rows]


def validate_peripheral_relationships(connection: sqlite3.Connection) -> None:
    """Ensure materialized Peripheral rows match pinned reviewed data and source context."""
    curated = _curated_from_connection(connection)
    if curated is None:
        if any(
            connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
            for table in PERIPHERAL_APPLICATION_TABLES
        ):
            raise ValueError(
                "Database has Peripheral application rows without pinned reviewed metadata; "
                "rebuild the database"
            )
        return

    expected = _expected_rows(connection, curated)
    columns_by_table: Mapping[str, tuple[str, ...]] = {
        "application_peripheral_entities": ("id", "name", "type_id"),
        "application_peripheral_profiles": ("id", "entity_id", "name", "mode"),
        "application_peripheral_sources": (
            "army_id",
            "peripheral_id",
            "entity_id",
            "profile_id",
            "source_id",
            "source_name",
        ),
        "application_peripheral_unit_sources": (
            "source_unit_id",
            "logical_unit_id",
            "type_id",
            "source_id",
            "source_name",
        ),
        "application_peripheral_controller_access": (
            "id",
            "source_id",
            "controller_kind",
            "army_id",
            "unit_id",
            "group_id",
            "parent_id",
            "source_name",
            "type_id",
            "relationship",
        ),
        "application_peripheral_controller_targets": (
            "access_id",
            "target_logical_unit_id",
        ),
    }
    for table, columns in columns_by_table.items():
        actual = [tuple(row) for row in _table_rows(connection, table, columns)]
        wanted = sorted(expected[table])
        if actual != wanted:
            raise ValueError(
                "Database has invalid materialized Peripheral application relationships; "
                "rebuild the database"
            )
