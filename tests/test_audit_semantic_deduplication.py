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


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        for table, columns in REQUIRED_COLUMNS.items():
            definition = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{table}" ({definition})')

        connection.execute("PRAGMA application_id = 1229210161")
        connection.execute("PRAGMA user_version = 25")
        _insert(connection, "__infinity_metadata", key="_meta", value=json.dumps({}))
        _insert(
            connection,
            "__infinity_metadata",
            key="database_compatibility_version",
            value="34",
        )
        for source_id, logical_id in ((1, 1), (10001, 1), (2, 2)):
            _insert(
                connection,
                "logical_unit_sources",
                source_unit_id=source_id,
                logical_unit_id=logical_id,
            )

        profile_defaults = {
            "name": "Profile",
            "type_id": 1,
            "move_1": 4,
            "move_2": 4,
            "cc": 10,
            "bs": 10,
            "ph": 10,
            "wip": 10,
            "arm": 0,
            "bts": 0,
            "vitality": 1,
            "silhouette": 2,
            "is_structure": 0,
            "notes": None,
        }
        _insert(
            connection,
            "profile_payloads",
            id=1,
            logical_unit_id=1,
            payload_sha256="a" * 64,
            **profile_defaults,
        )
        _insert(
            connection,
            "profile_payloads",
            id=2,
            logical_unit_id=2,
            payload_sha256="b" * 64,
            **profile_defaults,
        )
        for army_id, unit_id, profile_id, payload_id in (
            (101, 1, 1, 1),
            (102, 1, 7, 1),
            (901, 10001, 3, 1),
            (201, 2, 1, 2),
        ):
            _insert(
                connection,
                "profile_payload_occurrences",
                army_id=army_id,
                unit_id=unit_id,
                group_id=1,
                profile_id=profile_id,
                profile_payload_id=payload_id,
                position=1,
                ava=1,
                logo=None,
            )

        for payload_id, logical_id, sha in ((1, 1, "c" * 64), (2, 2, "d" * 64)):
            _insert(
                connection,
                "loadout_payloads",
                id=payload_id,
                logical_unit_id=logical_id,
                payload_sha256=sha,
                name="Loadout",
                minis=1,
                disabled=0,
            )
        for army_id, unit_id, option_id, payload_id in (
            (101, 1, 1, 1),
            (102, 1, 8, 1),
            (901, 10001, 2, 1),
            (201, 2, 1, 2),
        ):
            _insert(
                connection,
                "loadout_payload_occurrences",
                army_id=army_id,
                unit_id=unit_id,
                group_id=1,
                option_id=option_id,
                loadout_payload_id=payload_id,
                position=1,
                points=20,
                swc="0",
            )
        connection.commit()
    finally:
        connection.close()
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_audit_reports_runtime_payload_reuse(tmp_path: Path) -> None:
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
    assert report["profiles"]["logicalUnit"]["duplicateGroups"][0]["logicalUnitId"] == 1


def test_audit_rejects_unclassified_schema_drift(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE profile_payloads ADD COLUMN new_semantic_field")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        SemanticDeduplicationAuditError,
        match=r"profile_payloads.*unclassified new_semantic_field",
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
    assert report["payloadDefinitions"]["profile"]["contextualOccurrenceFields"] == [
        "ava",
        "logo",
    ]

    detailed = tmp_path / "detailed.json"
    assert main([str(database), "--output", str(detailed), "--details"]) == 0
    detailed_report = json.loads(detailed.read_text(encoding="utf-8"))
    assert detailed_report["profiles"]["logicalUnit"]["duplicateGroups"]

    output = capsys.readouterr().out
    assert "Profiles" in output
    assert "Loadouts" in output
