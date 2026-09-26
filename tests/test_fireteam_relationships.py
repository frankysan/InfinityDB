from __future__ import annotations

import sqlite3

import pytest

from infinity_db.database.fireteam_relationships import (
    derive_application_fireteams,
    materialize_application_fireteams,
    validate_application_fireteam_integrity,
    validate_application_fireteams,
)
from infinity_db.database.schema import create_schema


def _insert(connection: sqlite3.Connection, table: str, **values: object) -> None:
    columns = ", ".join(f'"{name}"' for name in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )


def _fixture_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_schema(connection, {})

    for application_army_id, preferred_source_id, role in (
        (101, 101, "main"),
        (199, 199, "reinforcement"),
        (999, 999, "reinforcement"),
    ):
        _insert(
            connection,
            "application_armies",
            id=application_army_id,
            preferred_source_id=preferred_source_id,
            role=role,
            playable=1,
        )

    source_rows = (
        (101, 101, "army", '{"CORE":1,"HARIS":2}', "Parent note"),
        (199, 199, "reinforcement", '{"CORE":0,"HARIS":0}', "Section note"),
        # 998/999 are source aliases for one application Army. The canonical projection
        # must select 999 because application identity owns that preference.
        (999, 998, "reinforcement", '{"CORE":1}', "Unselected alias"),
        (999, 999, "reinforcement", '{"CORE":2}', "Selected alias"),
    )
    for application_id, source_id, kind, spec, description in source_rows:
        _insert(
            connection,
            "application_army_sources",
            application_army_id=application_id,
            source_army_id=source_id,
            has_army_list=1,
            has_metadata=0,
        )
        _insert(
            connection,
            "army_lists",
            id=source_id,
            kind=kind,
            source_file=f"{source_id}.json",
            source_sha256=str(source_id) * 8,
            fireteam_description=description,
            fireteam_spec=spec,
        )

    for unit_id, name in ((1, "Alpha"), (2, "Beta"), (3, "Gamma")):
        _insert(connection, "units", id=unit_id, name=name, source_defined=1)
        _insert(connection, "logical_units", id=unit_id, representative_unit_id=unit_id)
        _insert(
            connection,
            "logical_unit_sources",
            source_unit_id=unit_id,
            logical_unit_id=unit_id,
        )

    for unit_id in (1, 2):
        _insert(connection, "army_units", army_id=199, unit_id=unit_id)

    _insert(
        connection,
        "fireteams",
        army_id=199,
        fireteam_id=1,
        position=1,
        name="Reinforcement Team",
        observation="No Wildcards",
    )
    _insert(
        connection,
        "fireteam_types",
        army_id=199,
        fireteam_id=1,
        position=1,
        fireteam_type="Core",
    )
    _insert(
        connection,
        "fireteam_members",
        army_id=199,
        fireteam_id=1,
        member_id=1,
        position=1,
        slug="alpha",
        name="ALPHA REINF.",
        comment="FTO (Line Troops, Veterans)",
        min_count=1,
        max_count=2,
        required=1,
        resolved_unit_id=1,
        resolution="army",
    )
    _insert(
        connection,
        "fireteam_members",
        army_id=199,
        fireteam_id=1,
        member_id=2,
        position=2,
        slug="gamma",
        name="GAMMA REINF. FTO",
        comment=None,
        min_count=None,
        max_count=1,
        required=0,
        resolved_unit_id=3,
        resolution="global",
    )

    _insert(
        connection,
        "fireteams",
        army_id=199,
        fireteam_id=2,
        position=2,
        name="Wildcards",
        observation=None,
    )
    _insert(
        connection,
        "fireteam_members",
        army_id=199,
        fireteam_id=2,
        member_id=1,
        position=1,
        slug="beta",
        name="BETA",
        comment=None,
        min_count=None,
        max_count=None,
        required=0,
        resolved_unit_id=2,
        resolution="army",
    )

    _insert(
        connection,
        "loadout_options",
        army_id=199,
        unit_id=1,
        group_id=1,
        option_id=1,
        position=1,
        name="ALPHA REF. FTO-2",
    )
    _insert(connection, "loadout_payloads", id=10, logical_unit_id=1, payload_sha256="a" * 64)
    _insert(
        connection,
        "loadout_payload_occurrences",
        army_id=199,
        unit_id=1,
        group_id=1,
        option_id=1,
        loadout_payload_id=10,
        position=1,
    )

    # Distinct alias charts prove that selecting the application Army's preferred source
    # is deliberate rather than an accidental source-ID merge.
    for source_id, team_name in ((998, "Old Alias Team"), (999, "Preferred Alias Team")):
        _insert(
            connection,
            "fireteams",
            army_id=source_id,
            fireteam_id=1,
            position=1,
            name=team_name,
            observation=None,
        )
    connection.commit()
    return connection


def test_fireteam_projection_preserves_chart_context_and_option_semantics() -> None:
    connection = _fixture_connection()
    try:
        model = materialize_application_fireteams(connection)

        assert (199, "CORE", 1, 0) in model.limits
        assert (199, "HARIS", 2, 0) in model.limits
        assert (
            199,
            1,
            1,
            "Reinforcement Team",
            "No Wildcards",
            199,
            1,
            0,
        ) in model.fireteams
        assert (
            199,
            2,
            2,
            "Wildcards",
            None,
            199,
            2,
            1,
        ) in model.fireteams
        assert (199, 1, 1, "CORE") in model.types

        alpha = next(row for row in model.members if row[:3] == (199, 1, 1))
        assert alpha[10:17] == (1, 2, 1, 1, 1, "army", "generic")
        gamma = next(row for row in model.members if row[:3] == (199, 1, 2))
        assert gamma[13:17] == (3, 3, "global", "generic")

        assert model.member_loadouts == (
            (199, 1, 1, 1, 199, 1, 1, 1, 10, "ALPHA REF. FTO-2", "2"),
        )
        assert model.equivalence_labels == (
            (199, 1, 1, 1, "Line Troops"),
            (199, 1, 1, 2, "Veterans"),
        )
        validate_application_fireteam_integrity(connection)
        validate_application_fireteams(connection)
    finally:
        connection.close()


def test_fireteam_projection_uses_application_army_preferred_source() -> None:
    connection = _fixture_connection()
    try:
        model = derive_application_fireteams(connection)
        alias_chart = next(row for row in model.charts if row[0] == 999)
        assert alias_chart[1] == 999
        assert alias_chart[5] == "Selected alias"
        assert (999, "CORE", 1, 2) in model.limits
        assert [row[3] for row in model.fireteams if row[0] == 999] == [
            "Preferred Alias Team"
        ]
    finally:
        connection.close()


def test_fireteam_source_consistency_validation_detects_tampering() -> None:
    connection = _fixture_connection()
    try:
        materialize_application_fireteams(connection)
        connection.execute(
            "UPDATE application_fireteam_members SET name = 'tampered' "
            "WHERE application_army_id = 199 AND fireteam_id = 1 AND member_id = 1"
        )
        with pytest.raises(ValueError, match="invalid materialized application Fireteams"):
            validate_application_fireteams(connection)
    finally:
        connection.close()
