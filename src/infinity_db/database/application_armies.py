"""Materialize InfinityDB's game-wide application Army identity layer."""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from infinity_db.identities import IdentityConfig

ARMY_ROLE_MAIN = "main"
ARMY_ROLE_SECTORIAL = "sectorial"
ARMY_ROLE_NON_ALIGNED = "non_aligned"
ARMY_ROLE_REINFORCEMENT = "reinforcement"
ARMY_ROLE_GROUPING = "grouping"
ARMY_ROLE_UNKNOWN = "unknown"
ARMY_ROLES = frozenset(
    {
        ARMY_ROLE_MAIN,
        ARMY_ROLE_SECTORIAL,
        ARMY_ROLE_NON_ALIGNED,
        ARMY_ROLE_REINFORCEMENT,
        ARMY_ROLE_GROUPING,
        ARMY_ROLE_UNKNOWN,
    }
)


@dataclass(frozen=True)
class ApplicationArmyModel:
    """Rows for the materialized application Army abstraction and its provenance."""

    armies: tuple[dict[str, Any], ...]
    sources: tuple[dict[str, Any], ...]
    reinforcement_parents: tuple[dict[str, int], ...]


def _dict_rows(connection: sqlite3.Connection, statement: str) -> list[dict[str, Any]]:
    cursor = connection.execute(statement)
    columns = tuple(column[0] for column in cursor.description or ())
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _visible_name(row: Mapping[str, Any]) -> str:
    name = row.get("name")
    if isinstance(name, str) and name:
        return name
    slug = row.get("slug")
    if slug == "reinf":
        return f"Reinforcements ({row['id']})"
    if isinstance(slug, str) and slug:
        derived_name = re.sub(r"[_-]+", " ", slug).strip().title()
        if derived_name:
            return derived_name
    return f"Army {row['id']}"


def _preferred_source_id(source_ids: set[int], application_id: int) -> int:
    return application_id if application_id in source_ids else min(source_ids)


def derive_application_armies(
    connection: sqlite3.Connection,
    identity_config: IdentityConfig,
) -> ApplicationArmyModel:
    """Derive application Army identity/hierarchy rows from source projections.

    ``army_lists`` and ``metadata_factions`` remain source-native projections.
    This model is the explicit InfinityDB abstraction used to reconcile reviewed
    source aliases and derive application role/playability/grouping semantics.
    """

    army_lists = {
        row["id"]: row
        for row in _dict_rows(
            connection,
            "SELECT id, name, slug, kind, reinforcement_id FROM army_lists ORDER BY id",
        )
    }
    metadata = {
        row["id"]: row
        for row in _dict_rows(
            connection,
            "SELECT id, parent, name, slug FROM metadata_factions ORDER BY id",
        )
    }

    list_sources_by_application: dict[int, set[int]] = defaultdict(set)
    metadata_sources_by_application: dict[int, set[int]] = defaultdict(set)
    for source_id in army_lists:
        list_sources_by_application[identity_config.canonical_army_id(source_id)].add(source_id)
    for source_id in metadata:
        metadata_sources_by_application[identity_config.canonical_army_id(source_id)].add(source_id)

    reinforcement_parents: dict[int, set[int]] = defaultdict(set)
    for row in army_lists.values():
        reinforcement_id = row.get("reinforcement_id")
        if not isinstance(reinforcement_id, int):
            continue
        application_reinforcement_id = identity_config.canonical_army_id(reinforcement_id)
        application_parent_id = identity_config.canonical_army_id(row["id"])
        reinforcement_parents[application_reinforcement_id].add(application_parent_id)

    def preferred_list_source(application_id: int) -> int | None:
        source_ids = list_sources_by_application.get(application_id)
        if not source_ids:
            return None
        return _preferred_source_id(source_ids, application_id)

    def preferred_metadata_source(application_id: int) -> int | None:
        source_ids = metadata_sources_by_application.get(application_id)
        if not source_ids:
            return None
        return _preferred_source_id(source_ids, application_id)

    list_application_ids = set(list_sources_by_application)
    ordinary_application_ids: set[int] = set()
    for application_id in list_application_ids:
        list_source_id = preferred_list_source(application_id)
        if list_source_id is None:
            continue
        if (
            application_id not in reinforcement_parents
            and army_lists[list_source_id]["kind"] != "reinforcement"
        ):
            ordinary_application_ids.add(application_id)

    parent_ids: set[int] = set()
    for application_id in ordinary_application_ids:
        metadata_source_id = preferred_metadata_source(application_id)
        if metadata_source_id is None:
            continue
        parent_id = metadata[metadata_source_id].get("parent")
        if isinstance(parent_id, int):
            canonical_parent_id = identity_config.canonical_army_id(parent_id)
            if canonical_parent_id != application_id:
                parent_ids.add(canonical_parent_id)

    grouping_ids: set[int] = set()
    for candidate_id in parent_ids:
        candidate_metadata_source = preferred_metadata_source(candidate_id)
        if candidate_metadata_source is None:
            continue
        if candidate_id not in ordinary_application_ids:
            grouping_ids.add(candidate_id)
            continue
        candidate_parent = metadata[candidate_metadata_source].get("parent")
        canonical_candidate_parent = (
            identity_config.canonical_army_id(candidate_parent)
            if isinstance(candidate_parent, int)
            else None
        )
        if canonical_candidate_parent != candidate_id:
            grouping_ids.add(candidate_id)

    application_ids = list_application_ids | grouping_ids
    army_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    for application_id in sorted(application_ids):
        list_source_id = preferred_list_source(application_id)
        metadata_source_id = preferred_metadata_source(application_id)
        contributing_source_ids = (
            list_sources_by_application.get(application_id, set())
            | metadata_sources_by_application.get(application_id, set())
        )
        preferred_source_id = _preferred_source_id(contributing_source_ids, application_id)

        list_row = army_lists.get(list_source_id) if list_source_id is not None else None
        metadata_row = (
            metadata.get(metadata_source_id) if metadata_source_id is not None else None
        )
        identity_row = {
            "id": application_id,
            "name": (
                (list_row or {}).get("name")
                or (metadata_row or {}).get("name")
            ),
            "slug": (
                (list_row or {}).get("slug")
                or (metadata_row or {}).get("slug")
            ),
        }
        identity_row["name"] = _visible_name(identity_row)

        parent_id = (metadata_row or {}).get("parent")
        canonical_parent_id = (
            identity_config.canonical_army_id(parent_id)
            if isinstance(parent_id, int)
            else None
        )
        parent_army_ids = reinforcement_parents.get(application_id, set())

        if parent_army_ids:
            role = ARMY_ROLE_REINFORCEMENT
            playable = True
            group_id = None
        elif application_id in grouping_ids:
            role = ARMY_ROLE_GROUPING
            playable = False
            group_id = None
        elif canonical_parent_id == application_id:
            role = ARMY_ROLE_MAIN
            playable = True
            group_id = None
        elif canonical_parent_id in grouping_ids:
            role = ARMY_ROLE_NON_ALIGNED
            playable = True
            group_id = canonical_parent_id
        elif canonical_parent_id in application_ids:
            role = ARMY_ROLE_SECTORIAL
            playable = True
            group_id = canonical_parent_id
        else:
            role = ARMY_ROLE_UNKNOWN
            playable = True
            group_id = None

        army_rows.append(
            {
                "id": application_id,
                "name": identity_row["name"],
                "slug": identity_row["slug"],
                "role": role,
                "playable": int(playable),
                "group_id": group_id,
                "preferred_source_id": preferred_source_id,
            }
        )
        for source_id in sorted(contributing_source_ids):
            source_rows.append(
                {
                    "application_army_id": application_id,
                    "source_army_id": source_id,
                    "has_army_list": int(source_id in army_lists),
                    "has_metadata": int(source_id in metadata),
                }
            )

    reinforcement_rows = tuple(
        {
            "reinforcement_army_id": reinforcement_id,
            "parent_army_id": parent_id,
        }
        for reinforcement_id, parent_ids_for_army in sorted(reinforcement_parents.items())
        if reinforcement_id in application_ids
        for parent_id in sorted(parent_ids_for_army)
        if parent_id in application_ids
    )
    return ApplicationArmyModel(
        armies=tuple(army_rows),
        sources=tuple(source_rows),
        reinforcement_parents=reinforcement_rows,
    )


def materialize_application_armies(
    connection: sqlite3.Connection,
    identity_config: IdentityConfig,
) -> ApplicationArmyModel:
    """Populate the application Army abstraction from imported source rows."""

    model = derive_application_armies(connection, identity_config)
    connection.executemany(
        "INSERT INTO application_armies "
        "(id, name, slug, role, playable, group_id, preferred_source_id) "
        "VALUES (:id, :name, :slug, :role, :playable, :group_id, :preferred_source_id)",
        model.armies,
    )
    connection.executemany(
        "INSERT INTO application_army_sources "
        "(application_army_id, source_army_id, has_army_list, has_metadata) "
        "VALUES (:application_army_id, :source_army_id, :has_army_list, :has_metadata)",
        model.sources,
    )
    connection.executemany(
        "INSERT INTO application_army_reinforcement_parents "
        "(reinforcement_army_id, parent_army_id) "
        "VALUES (:reinforcement_army_id, :parent_army_id)",
        model.reinforcement_parents,
    )
    return model


def validate_application_armies(
    connection: sqlite3.Connection,
    identity_config: IdentityConfig,
) -> None:
    """Verify persisted application Army rows still match their source evidence."""

    expected = derive_application_armies(connection, identity_config)
    actual_armies = tuple(
        _dict_rows(
            connection,
            "SELECT id, name, slug, role, playable, group_id, preferred_source_id "
            "FROM application_armies ORDER BY id",
        )
    )
    actual_sources = tuple(
        _dict_rows(
            connection,
            "SELECT application_army_id, source_army_id, has_army_list, has_metadata "
            "FROM application_army_sources ORDER BY application_army_id, source_army_id",
        )
    )
    actual_reinforcement_parents = tuple(
        _dict_rows(
            connection,
            "SELECT reinforcement_army_id, parent_army_id "
            "FROM application_army_reinforcement_parents "
            "ORDER BY reinforcement_army_id, parent_army_id",
        )
    )
    if (
        actual_armies != expected.armies
        or actual_sources != expected.sources
        or actual_reinforcement_parents != expected.reinforcement_parents
    ):
        raise ValueError(
            "Database has invalid materialized application Army identity; rebuild the database"
        )
