"""Materialize deterministic Army profile-group dependency relations."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Any

RELATION_GROUP_DEPENDENCY_TABLES = (
    "application_unit_group_dependency_constraints",
    "application_unit_group_dependency_members",
    "application_unit_group_dependency_targets",
)


def _source_to_logical(connection: sqlite3.Connection) -> dict[int, int]:
    return {
        int(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT source_unit_id, logical_unit_id FROM logical_unit_sources"
        )
    }


def _profile_group_exists(
    connection: sqlite3.Connection,
    *,
    army_id: int,
    unit_id: int,
    group_id: int,
) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM profile_groups "
            "WHERE army_id = ? AND unit_id = ? AND group_id = ? LIMIT 1",
            (army_id, unit_id, group_id),
        ).fetchone()
        is not None
    )


def _normalized_options(
    connection: sqlite3.Connection,
    *,
    army_id: int,
    unit_id: int,
    group_id: int,
    raw: Any,
) -> str | None:
    if raw is None:
        return None
    value = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(value, list) or any(type(item) is not int for item in value):
        return None
    expected = set(value)
    available = {
        int(row[0])
        for row in connection.execute(
            "SELECT option_id FROM loadout_options "
            "WHERE army_id = ? AND unit_id = ? AND group_id = ?",
            (army_id, unit_id, group_id),
        )
    }
    if not expected.issubset(available):
        return None
    return json.dumps(value, separators=(",", ":"))


def expected_relation_group_dependency_rows(
    connection: sqlite3.Connection,
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    """Return deterministic rows for same-logical profile-group dependencies."""
    previous_row_factory = connection.row_factory
    connection.row_factory = sqlite3.Row
    try:
        source_to_logical = _source_to_logical(connection)
        members_by_relation: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
        dependencies_by_member: dict[tuple[int, int, int], list[sqlite3.Row]] = defaultdict(list)

        for member in connection.execute(
            "SELECT army_id, relation_id, relation_unit_id, position, unit_id, "
            "profile_id, per_parent FROM relation_units "
            "ORDER BY army_id, relation_id, position, relation_unit_id"
        ):
            members_by_relation[(member["army_id"], member["relation_id"])].append(member)

        for dependency in connection.execute(
            "SELECT army_id, relation_id, relation_unit_id, dependency_id, position, "
            "unit_id, profile_id, group_id, min_count, min_dependant, options, raw "
            "FROM relation_dependencies "
            "ORDER BY army_id, relation_id, relation_unit_id, position, dependency_id"
        ):
            dependencies_by_member[
                (
                    dependency["army_id"],
                    dependency["relation_id"],
                    dependency["relation_unit_id"],
                )
            ].append(dependency)

        constraint_rows: list[tuple[Any, ...]] = []
        member_rows: list[tuple[Any, ...]] = []
        target_rows: list[tuple[Any, ...]] = []

        for relation in connection.execute(
            "SELECT army_id, relation_id, position, min_count, max_count, is_group "
            "FROM relations ORDER BY army_id, relation_id"
        ):
            army_id = int(relation["army_id"])
            relation_id = int(relation["relation_id"])
            members = members_by_relation.get((army_id, relation_id), [])
            if not members:
                continue

            candidate_members: list[
                tuple[sqlite3.Row, int, list[tuple[sqlite3.Row, int, str | None]]]
            ] = []
            logical_ids: set[int] = set()
            valid = True
            for member in members:
                source_unit_id = member["unit_id"]
                member_group_id = member["profile_id"]
                if type(source_unit_id) is not int or type(member_group_id) is not int:
                    valid = False
                    break
                logical_unit_id = source_to_logical.get(source_unit_id)
                if logical_unit_id is None or not _profile_group_exists(
                    connection,
                    army_id=army_id,
                    unit_id=source_unit_id,
                    group_id=member_group_id,
                ):
                    valid = False
                    break

                dependencies = dependencies_by_member.get(
                    (army_id, relation_id, int(member["relation_unit_id"])), []
                )
                if not dependencies:
                    valid = False
                    break

                resolved_dependencies: list[tuple[sqlite3.Row, int, str | None]] = []
                for dependency in dependencies:
                    dependency_unit_id = dependency["unit_id"]
                    dependency_group_id = dependency["profile_id"]
                    if (
                        type(dependency_unit_id) is not int
                        or type(dependency_group_id) is not int
                        or dependency["raw"] is not None
                    ):
                        valid = False
                        break
                    dependency_logical_id = source_to_logical.get(dependency_unit_id)
                    if dependency_logical_id is None or not _profile_group_exists(
                        connection,
                        army_id=army_id,
                        unit_id=dependency_unit_id,
                        group_id=dependency_group_id,
                    ):
                        valid = False
                        break
                    options = _normalized_options(
                        connection,
                        army_id=army_id,
                        unit_id=dependency_unit_id,
                        group_id=dependency_group_id,
                        raw=dependency["options"],
                    )
                    if dependency["options"] is not None and options is None:
                        valid = False
                        break
                    resolved_dependencies.append(
                        (dependency, dependency_logical_id, options)
                    )
                    logical_ids.add(dependency_logical_id)
                if not valid:
                    break
                candidate_members.append(
                    (member, logical_unit_id, resolved_dependencies)
                )
                logical_ids.add(logical_unit_id)

            if not valid or len(logical_ids) != 1:
                continue

            constraint_rows.append(
                (
                    army_id,
                    relation_id,
                    relation["position"],
                    relation["min_count"],
                    relation["max_count"],
                    relation["is_group"],
                )
            )
            for member, logical_unit_id, dependencies in candidate_members:
                relation_unit_id = int(member["relation_unit_id"])
                member_rows.append(
                    (
                        army_id,
                        relation_id,
                        relation_unit_id,
                        member["position"],
                        int(member["unit_id"]),
                        logical_unit_id,
                        int(member["profile_id"]),
                        member["per_parent"],
                    )
                )
                for dependency, dependency_logical_id, options in dependencies:
                    target_rows.append(
                        (
                            army_id,
                            relation_id,
                            relation_unit_id,
                            int(dependency["dependency_id"]),
                            dependency["position"],
                            int(dependency["unit_id"]),
                            dependency_logical_id,
                            int(dependency["profile_id"]),
                            dependency["group_id"],
                            dependency["min_count"],
                            dependency["min_dependant"],
                            options,
                        )
                    )

        return constraint_rows, member_rows, target_rows
    finally:
        connection.row_factory = previous_row_factory


def materialize_relation_group_dependencies(connection: sqlite3.Connection) -> None:
    """Populate deterministic profile-group dependency relations."""
    constraints, members, targets = expected_relation_group_dependency_rows(connection)
    connection.execute("DELETE FROM application_unit_group_dependency_targets")
    connection.execute("DELETE FROM application_unit_group_dependency_members")
    connection.execute("DELETE FROM application_unit_group_dependency_constraints")
    connection.executemany(
        "INSERT INTO application_unit_group_dependency_constraints "
        "(army_id, relation_id, position, min_count, max_count, is_group) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        constraints,
    )
    connection.executemany(
        "INSERT INTO application_unit_group_dependency_members "
        "(army_id, relation_id, relation_unit_id, position, source_unit_id, "
        "logical_unit_id, group_id, per_parent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        members,
    )
    connection.executemany(
        "INSERT INTO application_unit_group_dependency_targets "
        "(army_id, relation_id, relation_unit_id, dependency_id, position, source_unit_id, "
        "logical_unit_id, group_id, source_group_selector, min_count, min_dependant, options) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        targets,
    )


def _stored_rows(connection: sqlite3.Connection, table: str, fields: str) -> list[tuple[Any, ...]]:
    suffix = {
        "application_unit_group_dependency_constraints": "relation_id",
        "application_unit_group_dependency_members": "relation_unit_id",
        "application_unit_group_dependency_targets": "relation_unit_id, dependency_id",
    }[table]
    return [
        tuple(row)
        for row in connection.execute(
            f"SELECT {fields} FROM {table} ORDER BY army_id, relation_id, {suffix}"
        )
    ]


def validate_relation_group_dependencies(connection: sqlite3.Connection) -> None:
    """Fail closed when materialized profile-group dependencies drift from source rows."""
    expected_constraints, expected_members, expected_targets = (
        expected_relation_group_dependency_rows(connection)
    )
    actual_constraints = _stored_rows(
        connection,
        "application_unit_group_dependency_constraints",
        "army_id, relation_id, position, min_count, max_count, is_group",
    )
    actual_members = _stored_rows(
        connection,
        "application_unit_group_dependency_members",
        "army_id, relation_id, relation_unit_id, position, source_unit_id, logical_unit_id, "
        "group_id, per_parent",
    )
    actual_targets = _stored_rows(
        connection,
        "application_unit_group_dependency_targets",
        "army_id, relation_id, relation_unit_id, dependency_id, position, source_unit_id, "
        "logical_unit_id, group_id, source_group_selector, min_count, min_dependant, options",
    )
    if (
        actual_constraints != expected_constraints
        or actual_members != expected_members
        or actual_targets != expected_targets
    ):
        raise ValueError(
            "Database has invalid materialized Unit profile-group dependencies; "
            "rebuild the database"
        )
