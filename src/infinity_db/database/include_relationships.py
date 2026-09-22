"""Materialize contextual include relationships with canonical target identities."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncludeRelationshipMaterialization:
    """Summary of one derived include-relationship materialization."""

    profile_occurrence_include_count: int
    loadout_occurrence_include_count: int
    unit_option_include_count: int


def _loadout_payloads(
    connection: sqlite3.Connection,
) -> dict[tuple[int, int, int, int], int]:
    return {
        (row[0], row[1], row[2], row[3]): row[4]
        for row in connection.execute(
            "SELECT army_id, unit_id, group_id, option_id, loadout_payload_id "
            "FROM loadout_payload_occurrences"
        )
    }


def _shared_loadout_targets(
    loadout_payloads: dict[tuple[int, int, int, int], int],
) -> dict[tuple[int, int, int], list[tuple[int, int]]]:
    result: dict[tuple[int, int, int], list[tuple[int, int]]] = defaultdict(list)
    for (army_id, unit_id, group_id, option_id), payload_id in loadout_payloads.items():
        result[(unit_id, group_id, option_id)].append((army_id, payload_id))
    for targets in result.values():
        targets.sort()
    return result


def _target_payload_id(
    row: sqlite3.Row,
    loadout_payloads: dict[tuple[int, int, int, int], int],
) -> int:
    key = (
        row["army_id"],
        row["unit_id"],
        row["target_group_id"],
        row["target_option_id"],
    )
    try:
        return loadout_payloads[key]
    except KeyError as exc:
        raise ValueError(f"Include target {key!r} has no canonical loadout payload") from exc


def _contextual_include_rows(
    connection: sqlite3.Connection,
    *,
    source_table: str,
    parent_id_field: str,
    loadout_payloads: dict[tuple[int, int, int, int], int],
) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for row in connection.execute(
        f"SELECT army_id, unit_id, group_id, {parent_id_field}, position, "
        f"target_group_id, target_option_id, quantity, raw FROM {source_table} "
        f"ORDER BY army_id, unit_id, group_id, {parent_id_field}, position"
    ):
        rows.append(
            (
                row["army_id"],
                row["unit_id"],
                row["group_id"],
                row[parent_id_field],
                row["position"],
                _target_payload_id(row, loadout_payloads),
                row["quantity"],
                row["raw"],
            )
        )
    return rows


def _unit_option_include_rows(
    connection: sqlite3.Connection,
    *,
    shared_targets: dict[tuple[int, int, int], list[tuple[int, int]]],
) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for row in connection.execute(
        "SELECT unit_id, option_id, position, target_group_id, target_option_id, quantity, raw "
        "FROM unit_option_includes ORDER BY unit_id, option_id, position"
    ):
        target_key = (row["unit_id"], row["target_group_id"], row["target_option_id"])
        targets = shared_targets.get(target_key, [])
        if not targets:
            raise ValueError(
                "Shared unit-option include target has no canonical loadout occurrence: "
                f"{target_key!r}"
            )
        for target_army_id, target_payload_id in targets:
            rows.append(
                (
                    row["unit_id"],
                    row["option_id"],
                    row["position"],
                    target_army_id,
                    target_payload_id,
                    row["quantity"],
                    row["raw"],
                )
            )
    return rows


def materialize_include_relationships(
    connection: sqlite3.Connection,
) -> IncludeRelationshipMaterialization:
    """Populate contextual include relationships after canonical payload materialization."""
    row_factory = connection.row_factory
    try:
        connection.row_factory = sqlite3.Row
        return _materialize_include_relationships(connection)
    finally:
        connection.row_factory = row_factory


def _materialize_include_relationships(
    connection: sqlite3.Connection,
) -> IncludeRelationshipMaterialization:
    loadout_payloads = _loadout_payloads(connection)
    shared_targets = _shared_loadout_targets(loadout_payloads)

    profile_rows = _contextual_include_rows(
        connection,
        source_table="profile_includes",
        parent_id_field="profile_id",
        loadout_payloads=loadout_payloads,
    )
    loadout_rows = _contextual_include_rows(
        connection,
        source_table="option_includes",
        parent_id_field="option_id",
        loadout_payloads=loadout_payloads,
    )
    unit_option_rows = _unit_option_include_rows(
        connection,
        shared_targets=shared_targets,
    )

    if profile_rows:
        connection.executemany(
            "INSERT INTO profile_occurrence_includes "
            "(army_id, unit_id, group_id, profile_id, position, "
            "target_loadout_payload_id, quantity, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            profile_rows,
        )
    if loadout_rows:
        connection.executemany(
            "INSERT INTO loadout_occurrence_includes "
            "(army_id, unit_id, group_id, option_id, position, "
            "target_loadout_payload_id, quantity, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            loadout_rows,
        )
    if unit_option_rows:
        connection.executemany(
            "INSERT INTO unit_option_include_targets "
            "(unit_id, option_id, position, target_army_id, target_loadout_payload_id, "
            "quantity, raw) VALUES (?, ?, ?, ?, ?, ?, ?)",
            unit_option_rows,
        )

    return IncludeRelationshipMaterialization(
        profile_occurrence_include_count=len(profile_rows),
        loadout_occurrence_include_count=len(loadout_rows),
        unit_option_include_count=len(unit_option_rows),
    )


def validate_include_relationships(connection: sqlite3.Connection) -> None:
    """Verify that the derived include layer exactly represents retained source rows."""
    row_factory = connection.row_factory
    try:
        connection.row_factory = sqlite3.Row
        loadout_payloads = _loadout_payloads(connection)
        shared_targets = _shared_loadout_targets(loadout_payloads)

        expected_profile = set(
            _contextual_include_rows(
                connection,
                source_table="profile_includes",
                parent_id_field="profile_id",
                loadout_payloads=loadout_payloads,
            )
        )
        actual_profile = {
            tuple(row)
            for row in connection.execute(
                "SELECT army_id, unit_id, group_id, profile_id, position, "
                "target_loadout_payload_id, quantity, raw FROM profile_occurrence_includes"
            )
        }
        if actual_profile != expected_profile:
            raise ValueError("Database has invalid materialized contextual profile includes")

        expected_loadout = set(
            _contextual_include_rows(
                connection,
                source_table="option_includes",
                parent_id_field="option_id",
                loadout_payloads=loadout_payloads,
            )
        )
        actual_loadout = {
            tuple(row)
            for row in connection.execute(
                "SELECT army_id, unit_id, group_id, option_id, position, "
                "target_loadout_payload_id, quantity, raw FROM loadout_occurrence_includes"
            )
        }
        if actual_loadout != expected_loadout:
            raise ValueError("Database has invalid materialized contextual loadout includes")

        expected_unit_option = set(
            _unit_option_include_rows(connection, shared_targets=shared_targets)
        )
        actual_unit_option = {
            tuple(row)
            for row in connection.execute(
                "SELECT unit_id, option_id, position, target_army_id, target_loadout_payload_id, "
                "quantity, raw FROM unit_option_include_targets"
            )
        }
        if actual_unit_option != expected_unit_option:
            raise ValueError("Database has invalid materialized unit-option include targets")
    finally:
        connection.row_factory = row_factory
