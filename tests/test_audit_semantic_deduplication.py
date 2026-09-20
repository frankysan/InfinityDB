from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_semantic_deduplication import (
    REQUIRED_COLUMNS,
    SemanticDeduplicationAuditError,
    audit_database,
    main,
)


def _insert(connection: sqlite3.Connection, table: str, **values: object) -> None:
    columns = ", ".join(f'"{name}"' for name in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )


def _profile_row(
    *,
    army_id: int,
    unit_id: int,
    profile_id: int,
    position: int,
    name: str = "Test Profile",
) -> dict[str, object]:
    return {
        "army_id": army_id,
        "unit_id": unit_id,
        "group_id": 1,
        "profile_id": profile_id,
        "position": position,
        "name": name,
        "logo": None,
        "type_id": 2,
        "move_1": 4,
        "move_2": 4,
        "cc": 15,
        "bs": 12,
        "ph": 11,
        "wip": 13,
        "arm": 1,
        "bts": 0,
        "vitality": 1,
        "silhouette": 2,
        "ava": 2,
        "is_structure": 0,
        "notes": None,
    }


def _loadout_row(
    *,
    army_id: int,
    unit_id: int,
    option_id: int,
    position: int,
    points: int = 20,
) -> dict[str, object]:
    return {
        "army_id": army_id,
        "unit_id": unit_id,
        "group_id": 1,
        "option_id": option_id,
        "position": position,
        "name": "Rifle",
        "points": points,
        "swc": "0",
        "minis": 1,
        "disabled": 0,
    }


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        for table, columns in REQUIRED_COLUMNS.items():
            definition = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{table}" ({definition})')

        connection.execute("PRAGMA application_id = 1229210161")
        connection.execute("PRAGMA user_version = 11")
        _insert(
            connection,
            "__infinity_metadata",
            key="_meta",
            value=json.dumps(
                {
                    "snapshotArchiveSha256": "a" * 64,
                    "snapshotDownloadedOn": "2026-09-18",
                },
                sort_keys=True,
            ),
        )
        _insert(
            connection,
            "__infinity_metadata",
            key="database_compatibility_version",
            value="16",
        )

        for logical_id, representative in ((1, 1), (2, 2)):
            _insert(
                connection,
                "logical_units",
                id=logical_id,
                representative_unit_id=representative,
            )
        for source_id, logical_id in ((1, 1), (10001, 1), (2, 2)):
            _insert(
                connection,
                "logical_unit_sources",
                source_unit_id=source_id,
                logical_unit_id=logical_id,
            )

        profiles = (
            _profile_row(army_id=101, unit_id=1, profile_id=1, position=1),
            _profile_row(army_id=102, unit_id=1, profile_id=7, position=9),
            _profile_row(army_id=901, unit_id=10001, profile_id=3, position=4),
            _profile_row(army_id=201, unit_id=2, profile_id=1, position=1),
        )
        for row in profiles:
            _insert(connection, "profiles", **row)

        for occurrence_id, row, item_id, raw in (
            (1, profiles[0], 10, '{"b":2,"a":1}'),
            (7, profiles[1], 10, '{ "a": 1, "b": 2 }'),
            (9, profiles[2], 10, '{"a":1,"b":2}'),
            (12, profiles[3], 11, '{"a":1,"b":2}'),
        ):
            _insert(
                connection,
                "profile_skills",
                occurrence_id=occurrence_id,
                army_id=row["army_id"],
                unit_id=row["unit_id"],
                group_id=row["group_id"],
                profile_id=row["profile_id"],
                position=occurrence_id * 3,
                item_id=item_id,
                display_order=1,
                quantity=1,
                raw=raw,
            )
            _insert(
                connection,
                "profile_skill_extras",
                occurrence_id=occurrence_id,
                position=occurrence_id * 2,
                extra_id=50,
            )

        loadouts = (
            _loadout_row(army_id=101, unit_id=1, option_id=1, position=1),
            _loadout_row(army_id=102, unit_id=1, option_id=8, position=11),
            _loadout_row(army_id=901, unit_id=10001, option_id=2, position=4),
            _loadout_row(army_id=201, unit_id=2, option_id=1, position=1, points=21),
        )
        for row in loadouts:
            _insert(connection, "loadout_options", **row)

        for template_id, raw in (
            (1, '{"b":2,"a":1}'),
            (2, '{ "a": 1, "b": 2 }'),
            (3, '{"a":1,"b":2}'),
            (4, '{"a":1,"b":2}'),
        ):
            _insert(
                connection,
                "option_weapon_templates",
                id=template_id,
                item_id=100,
                display_order=1,
                quantity=1,
                raw=raw,
            )

        for occurrence_id, row, template_id in (
            (101, loadouts[0], 1),
            (108, loadouts[1], 2),
            (109, loadouts[2], 3),
            (112, loadouts[3], 4),
        ):
            _insert(
                connection,
                "option_weapons",
                occurrence_id=occurrence_id,
                army_id=row["army_id"],
                unit_id=row["unit_id"],
                group_id=row["group_id"],
                option_id=row["option_id"],
                position=occurrence_id,
                template_id=template_id,
            )
            _insert(
                connection,
                "option_weapon_extras",
                occurrence_id=occurrence_id,
                position=occurrence_id + 5,
                extra_id=70,
            )

        connection.commit()
    finally:
        connection.close()
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_audit_collapses_context_only_repetition_and_preserves_semantic_difference(
    tmp_path: Path,
) -> None:
    database = _fixture_database(tmp_path)
    before = _sha256(database)

    report = audit_database(database, include_details=True)

    assert _sha256(database) == before
    assert report["profiles"]["storedOccurrences"] == 4
    assert report["profiles"]["sourceUnit"]["distinctPayloads"] == 3
    assert report["profiles"]["logicalUnit"]["distinctPayloads"] == 2
    assert report["loadouts"]["storedOccurrences"] == 4
    assert report["loadouts"]["sourceUnit"]["distinctPayloads"] == 3
    assert report["loadouts"]["logicalUnit"]["distinctPayloads"] == 2

    profile_group = report["profiles"]["logicalUnit"]["duplicateGroups"][0]
    assert profile_group["logicalUnitId"] == 1
    assert profile_group["occurrenceCount"] == 3

    loadout_group = report["loadouts"]["logicalUnit"]["duplicateGroups"][0]
    assert loadout_group["logicalUnitId"] == 1
    assert loadout_group["occurrenceCount"] == 3


def test_audit_preserves_relative_child_order(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        for occurrence_id, army_id, unit_id, profile_id, position, item_id in (
            (21, 101, 1, 1, 1, 20),
            (22, 101, 1, 1, 2, 21),
            (23, 102, 1, 7, 2, 20),
            (24, 102, 1, 7, 1, 21),
        ):
            _insert(
                connection,
                "profile_equipment",
                occurrence_id=occurrence_id,
                army_id=army_id,
                unit_id=unit_id,
                group_id=1,
                profile_id=profile_id,
                position=position,
                item_id=item_id,
                display_order=1,
                quantity=1,
                raw=None,
            )
        connection.commit()
    finally:
        connection.close()

    report = audit_database(database)

    assert report["profiles"]["sourceUnit"]["distinctPayloads"] == 4


def test_audit_rejects_unclassified_schema_drift(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE profiles ADD COLUMN new_semantic_field")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        SemanticDeduplicationAuditError,
        match=r"profiles.*unclassified new_semantic_field",
    ):
        audit_database(database)


def test_audit_requires_complete_logical_unit_mapping(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "DELETE FROM logical_unit_sources WHERE source_unit_id = 10001"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        SemanticDeduplicationAuditError,
        match="Source unit 10001 has no logical-unit mapping",
    ):
        audit_database(database)


def test_json_report_is_deterministic_and_details_are_opt_in(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = _fixture_database(tmp_path)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert main([str(database), "--output", str(first)]) == 0
    assert main([str(database), "--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()

    report = json.loads(first.read_text(encoding="utf-8"))
    assert "duplicateGroups" not in report["profiles"]["sourceUnit"]
    assert report["payloadDefinitions"]["rawJson"].startswith("raw fields are parsed")

    detailed = tmp_path / "detailed.json"
    assert main([str(database), "--output", str(detailed), "--details"]) == 0
    detailed_report = json.loads(detailed.read_text(encoding="utf-8"))
    assert detailed_report["profiles"]["logicalUnit"]["duplicateGroups"]

    output = capsys.readouterr().out
    assert "Profiles" in output
    assert "Loadouts" in output
