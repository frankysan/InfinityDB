from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_fireteam_semantics import (
    REQUIRED_COLUMNS,
    FireteamSemanticsAuditError,
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


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        for table, columns in REQUIRED_COLUMNS.items():
            definition = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{table}" ({definition})')
        connection.execute("PRAGMA user_version = 25")
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

        for application_id, name, role in (
            (101, "Parent Army", "main"),
            (199, "Reinforcement Section", "reinforcement"),
        ):
            _insert(
                connection,
                "application_armies",
                id=application_id,
                name=name,
                role=role,
                playable=1,
            )
        _insert(
            connection,
            "application_army_reinforcement_parents",
            reinforcement_army_id=199,
            parent_army_id=101,
        )

        charts = (
            (
                101,
                101,
                "army",
                "Parent note",
                json.dumps({"CORE": 0, "HARIS": 1, "DUO": 2}),
            ),
            (
                199,
                199,
                "reinforcement",
                None,
                json.dumps({"CORE": 0, "HARIS": 0, "DUO": 0}),
            ),
        )
        for application_id, source_id, kind, description, spec in charts:
            _insert(
                connection,
                "application_fireteam_charts",
                application_army_id=application_id,
                source_army_id=source_id,
                source_kind=kind,
                description=description,
                source_spec=spec,
            )
            for position, (fireteam_type, raw_limit) in enumerate(
                json.loads(spec).items(), start=1
            ):
                _insert(
                    connection,
                    "application_fireteam_chart_limits",
                    application_army_id=application_id,
                    fireteam_type=fireteam_type,
                    position=position,
                    raw_limit=raw_limit,
                )

        _insert(
            connection,
            "application_fireteams",
            application_army_id=199,
            fireteam_id=1,
            position=1,
            name="Reinforcement Fireteam",
            observation="No Wildcards",
            source_army_id=199,
            is_wildcard=0,
        )
        for position, fireteam_type in enumerate(("CORE", "HARIS"), start=1):
            _insert(
                connection,
                "application_fireteam_types",
                application_army_id=199,
                fireteam_id=1,
                position=position,
                fireteam_type=fireteam_type,
            )

        members = (
            (1, "alpha", "ALPHA REINF.", "FTO", 1, 1, "army", "generic", 1),
            (2, "beta", "BETA REINF.", "FTO", 2, 2, "army", "generic", 1),
            (3, "gamma", "GAMMA REINF. FTO", "", 3, 3, "global", "generic", 0),
        )
        for (
            member_id,
            slug,
            name,
            comment,
            source_unit_id,
            logical_unit_id,
            resolution,
            marker,
            required,
        ) in members:
            _insert(
                connection,
                "application_fireteam_members",
                application_army_id=199,
                fireteam_id=1,
                member_id=member_id,
                position=member_id,
                source_army_id=199,
                slug=slug,
                name=name,
                comment=comment,
                min_count=0,
                max_count=1,
                required=required,
                source_unit_id=source_unit_id,
                logical_unit_id=logical_unit_id,
                resolution=resolution,
                fto_marker=marker,
            )

        _insert(
            connection,
            "application_fireteam_member_loadouts",
            application_army_id=199,
            fireteam_id=1,
            member_id=1,
            position=1,
            source_army_id=199,
            source_unit_id=1,
            group_id=1,
            option_id=1,
            loadout_payload_id=10,
            option_name="ALPHA REF. FTO-2",
            fto_marker="2",
        )

        _insert(
            connection,
            "application_fireteams",
            application_army_id=101,
            fireteam_id=1,
            position=1,
            name="Wildcards",
            observation=None,
            source_army_id=101,
            is_wildcard=1,
        )
        _insert(
            connection,
            "application_fireteam_members",
            application_army_id=101,
            fireteam_id=1,
            member_id=1,
            position=1,
            source_army_id=101,
            slug="alpha",
            name="ALPHA (Line Troops, Veterans)",
            comment="(Line Troops, Veterans)",
            min_count=0,
            max_count=None,
            required=0,
            source_unit_id=1,
            logical_unit_id=1,
            resolution="global",
            fto_marker=None,
        )
        for position, label in enumerate(("Line Troops", "Veterans"), start=1):
            _insert(
                connection,
                "application_fireteam_member_equivalence_labels",
                application_army_id=101,
                fireteam_id=1,
                member_id=1,
                position=position,
                label=label,
            )
        connection.commit()
    finally:
        connection.close()
    return path


def test_audit_fireteam_semantics_preserves_context_and_detects_fto_gaps(
    tmp_path: Path,
) -> None:
    report = audit_database(_fixture_database(tmp_path))

    assert report["chartShape"]["teamCount"] == 2
    assert report["memberResolution"]["nonArmyResolutionCount"] == 2
    assert report["requiredChoiceSets"]["requiredMemberRowCount"] == 2
    assert report["wildcards"] == {
        "teamCount": 1,
        "sourceArmyCount": 1,
        "typeMembershipCount": 0,
        "policy": report["wildcards"]["policy"],
    }
    assert report["levelEquivalence"]["labelReferenceCount"] == 2
    assert report["levelEquivalence"]["projectionMismatchCount"] == 0
    assert report["ruleBearingNotes"]["armyDescriptionCount"] == 1
    assert report["ruleBearingNotes"]["teamObservationCount"] == 1
    assert report["typeLimits"]["projectionMismatchCount"] == 0

    fto = report["ftoEligibility"]
    assert fto["memberRowCount"] == 3
    assert fto["statusCounts"] == {
        "no-matching-fto-option": 1,
        "resolved": 1,
        "source-unit-context-mismatch": 1,
    }
    assert fto["unresolvedCount"] == 2
    assert fto["eligibleOptionOccurrenceCount"] == 1
    assert fto["markerProjectionMismatchCount"] == 0

    reinforcement = report["reinforcementContext"]
    assert reinforcement["parentEdgeCount"] == 1
    assert reinforcement["playableParentTypeContextCount"] == 2
    assert reinforcement["blockedByParentTypeLimitCount"] == 1
    assert reinforcement["blockedByParentTypeLimit"][0]["fireteamType"] == "CORE"
    assert report["typeLimits"]["reinforcementSectionTypeRowsWhoseOwnSpecIsZeroCount"] == 2


def test_audit_fireteam_semantics_rejects_missing_schema(tmp_path: Path) -> None:
    path = tmp_path / "broken.db"
    sqlite3.connect(path).close()

    with pytest.raises(FireteamSemanticsAuditError, match="missing required tables"):
        audit_database(path)


def test_fireteam_audit_cli_writes_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _fixture_database(tmp_path)
    output = tmp_path / "report.json"

    assert main([str(database), "--output", str(output)]) == 0
    captured = capsys.readouterr().out
    assert "InfinityDB Fireteam semantics audit" in captured
    assert "FTO: 1/3 rows resolved" in captured
    assert json.loads(output.read_text(encoding="utf-8"))["formatVersion"] == 2


def test_tracked_runtime_fireteam_projection_is_auditable() -> None:
    database = Path(__file__).parents[1] / "data" / "generated" / "infinity.db"
    report = audit_database(database)

    assert report["chartShape"]["teamCount"] > 0
    assert report["typeLimits"]["projectionMismatchCount"] == 0
    assert report["levelEquivalence"]["projectionMismatchCount"] == 0
    assert report["ftoEligibility"]["markerProjectionMismatchCount"] == 0
