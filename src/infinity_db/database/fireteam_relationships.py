"""Materialize Army-scoped Fireteam charts onto application-owned identities."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ..fireteam_semantics import (
    decode_fireteam_spec,
    equivalence_labels,
    fto_marker,
    fto_option_matches,
    is_wildcard_name,
    member_fto_marker,
)

FIRETEAM_APPLICATION_TABLES = (
    "application_fireteam_charts",
    "application_fireteam_chart_limits",
    "application_fireteams",
    "application_fireteam_types",
    "application_fireteam_members",
    "application_fireteam_member_loadouts",
    "application_fireteam_member_equivalence_labels",
)

FIRETEAM_MEMBER_RESOLUTIONS = frozenset({"army", "global", "ambiguous", "unresolved"})


def _normalized_fireteam_type(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty Fireteam type")
    return value.strip().upper()


@dataclass(frozen=True)
class ApplicationFireteamModel:
    """Deterministic application Fireteam rows derived from one normalized snapshot."""

    charts: tuple[tuple[Any, ...], ...]
    limits: tuple[tuple[Any, ...], ...]
    fireteams: tuple[tuple[Any, ...], ...]
    types: tuple[tuple[Any, ...], ...]
    members: tuple[tuple[Any, ...], ...]
    member_loadouts: tuple[tuple[Any, ...], ...]
    equivalence_labels: tuple[tuple[Any, ...], ...]


def _rows(connection: sqlite3.Connection, statement: str, *parameters: Any) -> list[sqlite3.Row]:
    return list(connection.execute(statement, parameters))


def _preferred_chart_sources(connection: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    """Choose one canonical Army-list source for each application Army.

    Application Army identity already owns source-alias selection. Fireteams remain
    Army-local, so the application projection uses one preferred source chart rather
    than merging source aliases into a synthetic chart. Non-selected source charts
    remain losslessly available in ``infinity.raw.db``.
    """

    candidates: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in _rows(
        connection,
        "SELECT aa.id AS application_army_id, aa.preferred_source_id, "
        "aas.source_army_id, al.kind, al.source_file, al.source_sha256, "
        "al.fireteam_description, al.fireteam_spec "
        "FROM application_armies AS aa "
        "JOIN application_army_sources AS aas ON aas.application_army_id = aa.id "
        "JOIN army_lists AS al ON al.id = aas.source_army_id "
        "WHERE aas.has_army_list = 1 "
        "ORDER BY aa.id, aas.source_army_id",
    ):
        candidates[int(row["application_army_id"])].append(row)

    selected: dict[int, sqlite3.Row] = {}
    for application_army_id, rows in candidates.items():
        preferred_source_id = rows[0]["preferred_source_id"]
        selected[application_army_id] = min(
            rows,
            key=lambda row: (
                0 if row["source_army_id"] == preferred_source_id else 1,
                0 if row["source_army_id"] == application_army_id else 1,
                int(row["source_army_id"]),
            ),
        )
    return selected


def derive_application_fireteams(connection: sqlite3.Connection) -> ApplicationFireteamModel:
    """Return the canonical Fireteam application projection for current source rows."""

    previous_row_factory = connection.row_factory
    connection.row_factory = sqlite3.Row
    try:
        selected_sources = _preferred_chart_sources(connection)
        source_to_logical = {
            int(row["source_unit_id"]): int(row["logical_unit_id"])
            for row in _rows(
                connection,
                "SELECT source_unit_id, logical_unit_id FROM logical_unit_sources",
            )
        }

        source_fireteams: dict[int, list[sqlite3.Row]] = defaultdict(list)
        for row in _rows(
            connection,
            "SELECT army_id, fireteam_id, position, name, observation "
            "FROM fireteams ORDER BY army_id, position, fireteam_id",
        ):
            source_fireteams[int(row["army_id"])].append(row)

        source_types: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
        for row in _rows(
            connection,
            "SELECT army_id, fireteam_id, position, fireteam_type "
            "FROM fireteam_types ORDER BY army_id, fireteam_id, position",
        ):
            source_types[(int(row["army_id"]), int(row["fireteam_id"]))].append(row)

        source_members: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
        for row in _rows(
            connection,
            "SELECT army_id, fireteam_id, member_id, position, slug, name, comment, "
            "min_count, max_count, required, resolved_unit_id, resolution "
            "FROM fireteam_members ORDER BY army_id, fireteam_id, position, member_id",
        ):
            source_members[(int(row["army_id"]), int(row["fireteam_id"]))].append(row)

        loadouts: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
        for row in _rows(
            connection,
            "SELECT lo.army_id, lo.unit_id, lo.group_id, lo.option_id, lo.position, lo.name, "
            "lpo.loadout_payload_id "
            "FROM loadout_options AS lo "
            "JOIN loadout_payload_occurrences AS lpo "
            "ON lpo.army_id = lo.army_id AND lpo.unit_id = lo.unit_id "
            "AND lpo.group_id = lo.group_id AND lpo.option_id = lo.option_id "
            "ORDER BY lo.army_id, lo.unit_id, lo.position, lo.group_id, lo.option_id",
        ):
            loadouts[(int(row["army_id"]), int(row["unit_id"]))].append(row)

        chart_rows: list[tuple[Any, ...]] = []
        limit_rows: list[tuple[Any, ...]] = []
        fireteam_rows: list[tuple[Any, ...]] = []
        type_rows: list[tuple[Any, ...]] = []
        member_rows: list[tuple[Any, ...]] = []
        member_loadout_rows: list[tuple[Any, ...]] = []
        equivalence_rows: list[tuple[Any, ...]] = []

        for application_army_id, source in sorted(selected_sources.items()):
            source_army_id = int(source["source_army_id"])
            chart_rows.append(
                (
                    application_army_id,
                    source_army_id,
                    source["kind"],
                    source["source_file"],
                    source["source_sha256"],
                    source["fireteam_description"],
                    source["fireteam_spec"],
                )
            )
            spec = decode_fireteam_spec(source["fireteam_spec"], source_army_id)
            limit_rows.extend(
                (
                    application_army_id,
                    fireteam_type,
                    position,
                    raw_limit,
                )
                for position, (fireteam_type, raw_limit) in enumerate(spec.items(), start=1)
            )

            for fireteam in source_fireteams.get(source_army_id, []):
                fireteam_id = int(fireteam["fireteam_id"])
                fireteam_rows.append(
                    (
                        application_army_id,
                        fireteam_id,
                        fireteam["position"],
                        fireteam["name"],
                        fireteam["observation"],
                        source_army_id,
                        fireteam_id,
                        int(is_wildcard_name(fireteam["name"])),
                    )
                )
                source_key = (source_army_id, fireteam_id)
                type_rows.extend(
                    (
                        application_army_id,
                        fireteam_id,
                        row["position"],
                        _normalized_fireteam_type(
                            row["fireteam_type"],
                            context=(
                                f"Army {source_army_id} Fireteam {fireteam_id} "
                                f"type row {row['position']}"
                            ),
                        ),
                    )
                    for row in source_types.get(source_key, [])
                )

                for member in source_members.get(source_key, []):
                    member_id = int(member["member_id"])
                    resolution = member["resolution"]
                    if resolution not in FIRETEAM_MEMBER_RESOLUTIONS:
                        raise ValueError(
                            f"Army {source_army_id} Fireteam {fireteam_id} member {member_id} "
                            f"has unsupported resolution {resolution!r}"
                        )
                    source_unit_id = member["resolved_unit_id"]
                    if source_unit_id is not None and type(source_unit_id) is not int:
                        raise ValueError(
                            f"Army {source_army_id} Fireteam {fireteam_id} member {member_id} "
                            "has a non-integer resolved Unit ID"
                        )
                    logical_unit_id = (
                        source_to_logical.get(source_unit_id)
                        if type(source_unit_id) is int
                        else None
                    )
                    if source_unit_id is not None and logical_unit_id is None:
                        raise ValueError(
                            f"Army {source_army_id} Fireteam {fireteam_id} member {member_id} "
                            f"resolved Unit {source_unit_id} has no logical identity"
                        )
                    required = member["required"]
                    if required not in (None, 0, 1):
                        raise ValueError(
                            f"Army {source_army_id} Fireteam {fireteam_id} member {member_id} "
                            f"has invalid required flag {required!r}"
                        )
                    marker = member_fto_marker(member["name"], member["comment"])
                    member_rows.append(
                        (
                            application_army_id,
                            fireteam_id,
                            member_id,
                            member["position"],
                            source_army_id,
                            fireteam_id,
                            member_id,
                            member["slug"],
                            member["name"],
                            member["comment"],
                            member["min_count"],
                            member["max_count"],
                            int(bool(required)),
                            source_unit_id,
                            logical_unit_id,
                            resolution,
                            marker,
                        )
                    )
                    equivalence_rows.extend(
                        (
                            application_army_id,
                            fireteam_id,
                            member_id,
                            position,
                            label,
                        )
                        for position, label in enumerate(
                            equivalence_labels(member["comment"]), start=1
                        )
                    )

                    if (
                        marker is None
                        or resolution != "army"
                        or type(source_unit_id) is not int
                    ):
                        continue
                    matches = [
                        option
                        for option in loadouts.get((source_army_id, source_unit_id), [])
                        if fto_option_matches(member["name"], marker, option["name"])
                    ]
                    member_loadout_rows.extend(
                        (
                            application_army_id,
                            fireteam_id,
                            member_id,
                            position,
                            source_army_id,
                            source_unit_id,
                            option["group_id"],
                            option["option_id"],
                            option["loadout_payload_id"],
                            option["name"],
                            fto_marker(option["name"]),
                        )
                        for position, option in enumerate(matches, start=1)
                    )

        return ApplicationFireteamModel(
            charts=tuple(chart_rows),
            limits=tuple(limit_rows),
            fireteams=tuple(fireteam_rows),
            types=tuple(type_rows),
            members=tuple(member_rows),
            member_loadouts=tuple(member_loadout_rows),
            equivalence_labels=tuple(equivalence_rows),
        )
    finally:
        connection.row_factory = previous_row_factory


def materialize_application_fireteams(connection: sqlite3.Connection) -> ApplicationFireteamModel:
    """Populate the application-owned Fireteam projection."""

    model = derive_application_fireteams(connection)
    for table in reversed(FIRETEAM_APPLICATION_TABLES):
        connection.execute(f"DELETE FROM {table}")
    connection.executemany(
        "INSERT INTO application_fireteam_charts "
        "(application_army_id, source_army_id, source_kind, source_file, source_sha256, "
        "description, source_spec) VALUES (?, ?, ?, ?, ?, ?, ?)",
        model.charts,
    )
    connection.executemany(
        "INSERT INTO application_fireteam_chart_limits "
        "(application_army_id, fireteam_type, position, raw_limit) VALUES (?, ?, ?, ?)",
        model.limits,
    )
    connection.executemany(
        "INSERT INTO application_fireteams "
        "(application_army_id, fireteam_id, position, name, observation, source_army_id, "
        "source_fireteam_id, is_wildcard) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        model.fireteams,
    )
    connection.executemany(
        "INSERT INTO application_fireteam_types "
        "(application_army_id, fireteam_id, position, fireteam_type) VALUES (?, ?, ?, ?)",
        model.types,
    )
    connection.executemany(
        "INSERT INTO application_fireteam_members "
        "(application_army_id, fireteam_id, member_id, position, source_army_id, "
        "source_fireteam_id, source_member_id, slug, name, comment, min_count, max_count, "
        "required, source_unit_id, logical_unit_id, resolution, fto_marker) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        model.members,
    )
    connection.executemany(
        "INSERT INTO application_fireteam_member_loadouts "
        "(application_army_id, fireteam_id, member_id, position, source_army_id, "
        "source_unit_id, group_id, option_id, loadout_payload_id, option_name, fto_marker) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        model.member_loadouts,
    )
    connection.executemany(
        "INSERT INTO application_fireteam_member_equivalence_labels "
        "(application_army_id, fireteam_id, member_id, position, label) "
        "VALUES (?, ?, ?, ?, ?)",
        model.equivalence_labels,
    )
    return model


def _stored_rows(
    connection: sqlite3.Connection, table: str, fields: str, order_by: str
) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        tuple(row)
        for row in connection.execute(
            f"SELECT {fields} FROM {table} ORDER BY {order_by}"
        )
    )


def validate_application_fireteams(connection: sqlite3.Connection) -> None:
    """Fail closed when the persisted Fireteam projection drifts from source rows."""

    expected = derive_application_fireteams(connection)
    actual = ApplicationFireteamModel(
        charts=_stored_rows(
            connection,
            "application_fireteam_charts",
            "application_army_id, source_army_id, source_kind, source_file, source_sha256, "
            "description, source_spec",
            "application_army_id",
        ),
        limits=_stored_rows(
            connection,
            "application_fireteam_chart_limits",
            "application_army_id, fireteam_type, position, raw_limit",
            "application_army_id, position, fireteam_type",
        ),
        fireteams=_stored_rows(
            connection,
            "application_fireteams",
            "application_army_id, fireteam_id, position, name, observation, source_army_id, "
            "source_fireteam_id, is_wildcard",
            "application_army_id, position, fireteam_id",
        ),
        types=_stored_rows(
            connection,
            "application_fireteam_types",
            "application_army_id, fireteam_id, position, fireteam_type",
            "application_army_id, fireteam_id, position",
        ),
        members=_stored_rows(
            connection,
            "application_fireteam_members",
            "application_army_id, fireteam_id, member_id, position, source_army_id, "
            "source_fireteam_id, source_member_id, slug, name, comment, min_count, max_count, "
            "required, source_unit_id, logical_unit_id, resolution, fto_marker",
            "application_army_id, fireteam_id, position, member_id",
        ),
        member_loadouts=_stored_rows(
            connection,
            "application_fireteam_member_loadouts",
            "application_army_id, fireteam_id, member_id, position, source_army_id, "
            "source_unit_id, group_id, option_id, loadout_payload_id, option_name, fto_marker",
            "application_army_id, fireteam_id, member_id, position",
        ),
        equivalence_labels=_stored_rows(
            connection,
            "application_fireteam_member_equivalence_labels",
            "application_army_id, fireteam_id, member_id, position, label",
            "application_army_id, fireteam_id, member_id, position",
        ),
    )
    if actual != expected:
        raise ValueError(
            "Database has invalid materialized application Fireteams; rebuild the database"
        )


def validate_application_fireteam_integrity(connection: sqlite3.Connection) -> None:
    """Validate the self-contained published Fireteam projection."""

    invalid_chart = connection.execute(
        "SELECT 1 FROM application_fireteam_charts AS c "
        "LEFT JOIN application_army_sources AS aas "
        "ON aas.application_army_id = c.application_army_id "
        "AND aas.source_army_id = c.source_army_id "
        "WHERE aas.source_army_id IS NULL OR aas.has_army_list != 1 LIMIT 1"
    ).fetchone()
    invalid_team = connection.execute(
        "SELECT 1 FROM application_fireteams WHERE is_wildcard NOT IN (0, 1) LIMIT 1"
    ).fetchone()
    invalid_member = connection.execute(
        "SELECT 1 FROM application_fireteam_members "
        "WHERE required NOT IN (0, 1) "
        "OR resolution NOT IN ('army', 'global', 'ambiguous', 'unresolved') "
        "OR (source_unit_id IS NULL AND logical_unit_id IS NOT NULL) "
        "OR (source_unit_id IS NOT NULL AND logical_unit_id IS NULL) LIMIT 1"
    ).fetchone()
    invalid_fto = connection.execute(
        "SELECT 1 FROM application_fireteam_member_loadouts AS eligible "
        "JOIN application_fireteam_members AS member "
        "ON member.application_army_id = eligible.application_army_id "
        "AND member.fireteam_id = eligible.fireteam_id "
        "AND member.member_id = eligible.member_id "
        "WHERE member.fto_marker IS NULL OR member.resolution != 'army' "
        "OR member.source_unit_id != eligible.source_unit_id "
        "OR eligible.fto_marker IS NULL LIMIT 1"
    ).fetchone()
    if any(item is not None for item in (invalid_chart, invalid_team, invalid_member, invalid_fto)):
        raise ValueError(
            "Database has invalid application Fireteam projection; rebuild the database"
        )
