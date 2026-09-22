"""Materialize selection-safe Army relation constraints onto canonical Unit identity."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

RELATION_CONSTRAINT_TABLES = (
    "application_unit_constraints",
    "application_unit_constraint_members",
)

FAMILY_SAME_LOGICAL_EXCLUSIVE = "same-logical-cross-context-exclusive"
FAMILY_CROSS_LOGICAL_CARDINALITY = "cross-logical-shared-cardinality"
FAMILY_SINGLE_LOGICAL_CARDINALITY = "single-logical-cardinality"


def _source_to_logical(connection: sqlite3.Connection) -> dict[int, int]:
    return {
        int(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT source_unit_id, logical_unit_id FROM logical_unit_sources"
        )
    }


def _dependencies_by_member(
    connection: sqlite3.Connection,
) -> set[tuple[int, int, int]]:
    return {
        (int(row[0]), int(row[1]), int(row[2]))
        for row in connection.execute(
            "SELECT DISTINCT army_id, relation_id, relation_unit_id "
            "FROM relation_dependencies"
        )
    }


def _family(
    relation: sqlite3.Row,
    members: list[sqlite3.Row],
    logical_ids: set[int],
) -> str:
    if len(logical_ids) > 1:
        return FAMILY_CROSS_LOGICAL_CARDINALITY
    if (
        len(members) >= 2
        and len({int(member["unit_id"]) for member in members}) >= 2
        and not bool(relation["is_group"])
        and relation["min_count"] == 1
        and relation["max_count"] == 1
    ):
        return FAMILY_SAME_LOGICAL_EXCLUSIVE
    return FAMILY_SINGLE_LOGICAL_CARDINALITY


def _profile_selectors_are_selection_equivalent(
    connection: sqlite3.Connection,
    *,
    army_id: int,
    members: list[sqlite3.Row],
    dependency_members: set[tuple[int, int, int]],
) -> bool:
    """Return whether source profile selectors are neutral at roster-selection level.

    A selector is selection-equivalent to the whole Unit only when every member is
    present in the Army, has exactly one profile group containing all selectable
    loadouts, and the selector identifies a selectable profile in that group.
    """
    for member in members:
        member_key = (
            int(member["army_id"]),
            int(member["relation_id"]),
            int(member["relation_unit_id"]),
        )
        selector = member["profile_id"]
        if (
            member["per_parent"] is not None
            or member_key in dependency_members
            or type(selector) is not int
        ):
            return False

        unit_id = int(member["unit_id"])
        if connection.execute(
            "SELECT 1 FROM army_units WHERE army_id = ? AND unit_id = ? LIMIT 1",
            (army_id, unit_id),
        ).fetchone() is None:
            return False

        groups = [
            int(row[0])
            for row in connection.execute(
                "SELECT group_id FROM profile_groups "
                "WHERE army_id = ? AND unit_id = ? ORDER BY group_id",
                (army_id, unit_id),
            )
        ]
        if len(groups) != 1:
            return False
        group_id = groups[0]

        profile = connection.execute(
            "SELECT ava FROM profiles "
            "WHERE army_id = ? AND unit_id = ? AND group_id = ? AND profile_id = ?",
            (army_id, unit_id, group_id, selector),
        ).fetchone()
        if profile is None or (profile[0] is not None and int(profile[0]) < 0):
            return False

        selectable_groups = {
            int(row[0])
            for row in connection.execute(
                "SELECT DISTINCT group_id FROM loadout_options "
                "WHERE army_id = ? AND unit_id = ? AND COALESCE(disabled, 0) = 0",
                (army_id, unit_id),
            )
        }
        if selectable_groups != {group_id}:
            return False
    return True


def expected_relation_constraint_rows(
    connection: sqlite3.Connection,
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    """Return deterministic rows for fully resolved, selection-safe source relations."""
    previous_row_factory = connection.row_factory
    connection.row_factory = sqlite3.Row
    try:
        source_to_logical = _source_to_logical(connection)
        dependency_members = _dependencies_by_member(connection)
        members_by_relation: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
        for member in connection.execute(
            "SELECT army_id, relation_id, relation_unit_id, position, unit_id, "
            "profile_id, per_parent FROM relation_units "
            "ORDER BY army_id, relation_id, position, relation_unit_id"
        ):
            members_by_relation[(member["army_id"], member["relation_id"])].append(member)

        constraint_rows: list[tuple[Any, ...]] = []
        member_rows: list[tuple[Any, ...]] = []
        for relation in connection.execute(
            "SELECT army_id, relation_id, position, min_count, max_count, is_group "
            "FROM relations ORDER BY army_id, relation_id"
        ):
            key = (relation["army_id"], relation["relation_id"])
            members = members_by_relation.get(key, [])
            if not members:
                continue
            selector_free = all(
                member["profile_id"] is None
                and member["per_parent"] is None
                and (
                    int(member["army_id"]),
                    int(member["relation_id"]),
                    int(member["relation_unit_id"]),
                )
                not in dependency_members
                for member in members
            )
            selection_equivalent_selectors = (
                not selector_free
                and _profile_selectors_are_selection_equivalent(
                    connection,
                    army_id=int(relation["army_id"]),
                    members=members,
                    dependency_members=dependency_members,
                )
            )
            if not selector_free and not selection_equivalent_selectors:
                continue
            if any(int(member["unit_id"]) not in source_to_logical for member in members):
                continue

            logical_ids = {
                source_to_logical[int(member["unit_id"])] for member in members
            }
            family = _family(relation, members, logical_ids)
            constraint_rows.append(
                (
                    int(relation["army_id"]),
                    int(relation["relation_id"]),
                    relation["position"],
                    family,
                    relation["min_count"],
                    relation["max_count"],
                    relation["is_group"],
                )
            )
            member_rows.extend(
                (
                    int(member["army_id"]),
                    int(member["relation_id"]),
                    int(member["relation_unit_id"]),
                    member["position"],
                    int(member["unit_id"]),
                    source_to_logical[int(member["unit_id"])],
                )
                for member in members
            )
        return constraint_rows, member_rows
    finally:
        connection.row_factory = previous_row_factory


def materialize_relation_constraints(connection: sqlite3.Connection) -> None:
    """Populate canonical selection-safe Unit-selection constraints."""
    constraints, members = expected_relation_constraint_rows(connection)
    connection.execute("DELETE FROM application_unit_constraint_members")
    connection.execute("DELETE FROM application_unit_constraints")
    connection.executemany(
        "INSERT INTO application_unit_constraints "
        "(army_id, relation_id, position, family, min_count, max_count, is_group) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        constraints,
    )
    connection.executemany(
        "INSERT INTO application_unit_constraint_members "
        "(army_id, relation_id, relation_unit_id, position, source_unit_id, logical_unit_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        members,
    )


def _stored_rows(connection: sqlite3.Connection, table: str, fields: str) -> list[tuple[Any, ...]]:
    return [
        tuple(row)
        for row in connection.execute(
            f"SELECT {fields} FROM {table} ORDER BY army_id, relation_id, "
            + ("relation_unit_id" if table.endswith("_members") else "relation_id")
        )
    ]


def validate_relation_constraints(connection: sqlite3.Connection) -> None:
    """Fail closed when materialized selection-safe constraints drift from source rows."""
    expected_constraints, expected_members = expected_relation_constraint_rows(connection)
    actual_constraints = _stored_rows(
        connection,
        "application_unit_constraints",
        "army_id, relation_id, position, family, min_count, max_count, is_group",
    )
    actual_members = _stored_rows(
        connection,
        "application_unit_constraint_members",
        "army_id, relation_id, relation_unit_id, position, source_unit_id, logical_unit_id",
    )
    if actual_constraints != expected_constraints or actual_members != expected_members:
        raise ValueError(
            "Database has invalid materialized Unit selection constraints; "
            "rebuild the database"
        )
