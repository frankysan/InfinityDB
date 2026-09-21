from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_relationship_semantics import (
    REQUIRED_COLUMNS,
    RelationshipSemanticsAuditError,
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
        connection.execute("PRAGMA user_version = 16")
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
        _insert(connection, "logical_unit_sources", source_unit_id=1, logical_unit_id=10)

        for payload_id, army_id in ((100, 101), (101, 102)):
            _insert(
                connection,
                "loadout_payloads",
                id=payload_id,
                logical_unit_id=10,
                payload_sha256=str(payload_id),
                name="Included loadout",
                minis=1,
                disabled=0,
            )
            _insert(
                connection,
                "loadout_payload_occurrences",
                army_id=army_id,
                unit_id=1,
                group_id=1,
                option_id=2,
                loadout_payload_id=payload_id,
                position=2,
                points=10,
                swc=0,
            )

        _insert(
            connection,
            "profile_includes",
            army_id=101,
            unit_id=1,
            group_id=1,
            profile_id=1,
            position=1,
            target_group_id=1,
            target_option_id=2,
            quantity=1,
            raw=None,
        )
        _insert(
            connection,
            "option_includes",
            army_id=102,
            unit_id=1,
            group_id=1,
            option_id=1,
            position=1,
            target_group_id=1,
            target_option_id=2,
            quantity=1,
            raw=None,
        )
        _insert(
            connection,
            "unit_option_includes",
            unit_id=1,
            option_id=1,
            position=1,
            target_group_id=1,
            target_option_id=2,
            quantity=1,
            raw=None,
        )

        for army_id, peripheral_id, name, mercs in (
            (101, 1001, "BOT", 0),
            (102, 2001, "BOT", 0),
            (101, 1002, "TURTLEMEK", 0),
            (102, 2002, "TURTLEMEK", 1),
        ):
            _insert(
                connection,
                "peripherals",
                army_id=army_id,
                id=peripheral_id,
                position=1,
                name=name,
                mercs=mercs,
            )

        for occurrence_id, army_id, item_id in ((1, 101, 1001), (2, 102, 2001)):
            _insert(
                connection,
                "profile_peripherals",
                occurrence_id=occurrence_id,
                army_id=army_id,
                unit_id=1,
                group_id=1,
                profile_id=1,
                position=1,
                item_id=item_id,
                display_order=None,
                quantity=1,
                raw=None,
            )

        for occurrence_id, army_id, item_id in ((3, 101, 1002), (4, 102, 2002)):
            _insert(
                connection,
                "option_peripherals",
                occurrence_id=occurrence_id,
                army_id=army_id,
                unit_id=1,
                group_id=1,
                option_id=1,
                position=1,
                item_id=item_id,
                display_order=None,
                quantity=1,
                raw=None,
            )
        connection.commit()
    finally:
        connection.close()
    return path


def test_relationship_audit_resolves_includes_and_exposes_context(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path))

    assert report["includes"]["profile"]["resolvedTargetCount"] == 1
    assert report["includes"]["loadout"]["resolvedTargetCount"] == 1
    assert report["includes"]["profile"]["crossLogicalTargetCount"] == 0
    assert report["includes"]["unitOption"]["multiPayloadTargetCount"] == 1
    assert report["includes"]["unitOption"]["multiLogicalTargetCount"] == 0


def test_relationship_audit_treats_peripheral_identity_as_diagnostic(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path))
    peripherals = report["peripherals"]

    assert peripherals["definitionCount"] == 4
    assert peripherals["candidateDefinitionCount"] == 3
    assert peripherals["candidateDefinitionsWithMultipleRawIds"] == 1
    assert peripherals["candidateIdentity"]["status"] == "diagnostic_only"
    assert peripherals["occurrences"]["profile"]["sameSourceContextVariantCount"] == 0
    assert peripherals["occurrences"]["option"]["sameSourceContextVariantCount"] == 1


def test_relationship_audit_details_preserve_evidence(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path), include_details=True)

    shared = report["includes"]["unitOption"]["rows"][0]
    assert shared["targetArmyIds"] == [101, 102]
    assert shared["targetPayloadIds"] == [100, 101]
    repeated = report["peripherals"]["repeatedCandidateDefinitions"]
    assert repeated == [
        {
            "name": "BOT",
            "mercs": 0,
            "rawIdentities": [{"armyId": 101, "id": 1001}, {"armyId": 102, "id": 2001}],
        }
    ]


def test_relationship_audit_rejects_missing_schema(tmp_path: Path) -> None:
    path = tmp_path / "broken.db"
    sqlite3.connect(path).close()

    with pytest.raises(RelationshipSemanticsAuditError, match="Missing required table"):
        audit_database(path)


def test_relationship_audit_cli_writes_report(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    output = tmp_path / "relationship-audit.json"

    assert main([str(database), "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "InfinityDB relationship semantics audit"
