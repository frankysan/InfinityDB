from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database.schema import create_schema
from tools.audit_relationship_presentation import (
    RelationshipPresentationAuditError,
    audit_database,
    main,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _insert(connection: sqlite3.Connection, table: str, **values: object) -> None:
    columns = ", ".join(f'"{name}"' for name in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        create_schema(connection, {})
        _insert(
            connection,
            "__infinity_metadata",
            key="_meta",
            value=json.dumps(
                {
                    "snapshotArchiveSha256": "a" * 64,
                    "snapshotDownloadedOn": "2026-09-18",
                }
            ),
        )
        _insert(
            connection,
            "profile_occurrence_includes",
            army_id=101,
            unit_id=1,
            group_id=1,
            profile_id=1,
            position=1,
        )
        _insert(
            connection,
            "loadout_occurrence_includes",
            army_id=101,
            unit_id=1,
            group_id=1,
            option_id=1,
            position=1,
        )
        _insert(connection, "unit_option_includes", unit_id=1, option_id=1, position=1)
        _insert(
            connection,
            "unit_option_include_targets",
            unit_id=1,
            option_id=1,
            position=1,
            target_army_id=101,
        )
        _insert(connection, "application_unit_constraints", army_id=101, relation_id=1)
        _insert(
            connection,
            "application_unit_constraint_members",
            army_id=101,
            relation_id=1,
            relation_unit_id=1,
            logical_unit_id=1,
        )
        _insert(
            connection,
            "application_unit_group_dependency_constraints",
            army_id=101,
            relation_id=2,
        )
        _insert(
            connection,
            "application_unit_group_dependency_members",
            army_id=101,
            relation_id=2,
            relation_unit_id=1,
            logical_unit_id=1,
        )
        _insert(
            connection,
            "application_unit_group_dependency_targets",
            army_id=101,
            relation_id=2,
            relation_unit_id=1,
            dependency_id=1,
            logical_unit_id=2,
        )
        _insert(connection, "profile_peripherals", occurrence_id=1)
        _insert(connection, "option_peripherals", occurrence_id=2)
        _insert(
            connection,
            "application_peripheral_sources",
            army_id=101,
            peripheral_id=1,
        )
        _insert(
            connection,
            "application_peripheral_unit_sources",
            source_unit_id=2,
            logical_unit_id=2,
        )
        _insert(connection, "application_peripheral_controller_access", id="access:1")
        _insert(
            connection,
            "application_peripheral_controller_targets",
            access_id="access:1",
            target_logical_unit_id=2,
        )
        _insert(connection, "fireteams", army_id=101, fireteam_id=1)
        _insert(connection, "fireteam_types", army_id=101, fireteam_id=1, position=1)
        _insert(
            connection,
            "fireteam_members",
            army_id=101,
            fireteam_id=1,
            member_id=1,
            resolution="army",
        )
        _insert(
            connection,
            "application_army_reinforcement_parents",
            reinforcement_army_id=198,
            parent_army_id=101,
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_relationship_presentation_audit_records_confirmed_gap_families(
    tmp_path: Path,
) -> None:
    report = audit_database(_fixture_database(tmp_path), project_root=PROJECT_ROOT)

    assert report["gapFamilyCount"] == 5
    gaps = report["gaps"]
    assert gaps["includeRelationships"]["status"] == "database_only"
    assert gaps["includeRelationships"]["loadoutOccurrenceCount"] == 1
    assert gaps["selectionRelationships"]["status"] == "repository_or_api_only"
    assert gaps["selectionRelationships"]["constraintCount"] == 1
    assert gaps["peripheralRelationships"]["status"] == "repository_or_api_only"
    assert gaps["peripheralRelationships"]["controllerTargetCount"] == 1
    assert gaps["fireteamRelationships"]["status"] == "database_only"
    assert gaps["fireteamRelationships"]["nonArmyResolutionCount"] == 0
    assert gaps["reinforcementParentRelationships"]["status"] == "repository_or_api_only"
    assert gaps["reinforcementParentRelationships"]["parentEdgeCount"] == 1


def test_relationship_presentation_audit_rejects_missing_schema(tmp_path: Path) -> None:
    path = tmp_path / "broken.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE __infinity_metadata (key, value)")
    connection.commit()
    connection.close()

    with pytest.raises(RelationshipPresentationAuditError, match="missing required table"):
        audit_database(path, project_root=PROJECT_ROOT)


def test_relationship_presentation_audit_cli_writes_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _fixture_database(tmp_path)
    output = tmp_path / "report.json"

    assert main(
        [
            str(database),
            "--project-root",
            str(PROJECT_ROOT),
            "--output",
            str(output),
        ]
    ) == 0
    captured = capsys.readouterr().out
    assert "InfinityDB relationship presentation gap audit" in captured
    assert "Confirmed gap families: 5" in captured
    assert json.loads(output.read_text(encoding="utf-8"))["formatVersion"] == 1
