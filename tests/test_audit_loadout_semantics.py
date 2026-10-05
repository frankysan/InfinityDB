from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_loadout_semantics import (
    EXPECTED_COLUMNS,
    PAYLOAD_FIELDS,
    PAYLOAD_FORMAT,
    PAYLOAD_FORMAT_VERSION,
    LoadoutSemanticsAuditError,
    audit_database,
    main,
)
from tools.payload_audit_common import canonical_json


def _insert(connection: sqlite3.Connection, table: str, **values: object) -> None:
    columns = ", ".join(f'"{name}"' for name in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )


def _payload_values(name: str) -> dict[str, object]:
    return {"name": name, "minis": 1, "disabled": 0}


def _payload_sha(values: dict[str, object]) -> str:
    payload = {field: values[field] for field in PAYLOAD_FIELDS}
    payload.update(
        {
            "characteristics": [],
            "orders": [],
            "skills": [],
            "equipment": [],
            "weapons": [],
        }
    )
    serialized = canonical_json(
        {
            "format": PAYLOAD_FORMAT,
            "formatVersion": PAYLOAD_FORMAT_VERSION,
            "payload": payload,
        },
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        for table, columns in EXPECTED_COLUMNS.items():
            definition = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{table}" ({definition})')

        connection.execute("PRAGMA application_id = 1229210161")
        connection.execute("PRAGMA user_version = 25")
        _insert(
            connection,
            "__infinity_metadata",
            key="_meta",
            value=json.dumps(
                {
                    "snapshotArchiveSha256": "a" * 64,
                    "snapshotDownloadedOn": "2026-09-29",
                },
                sort_keys=True,
            ),
        )
        _insert(
            connection,
            "__infinity_metadata",
            key="database_compatibility_version",
            value="34",
        )

        for source_id, logical_id in ((1, 1), (2, 2)):
            _insert(
                connection,
                "logical_unit_sources",
                source_unit_id=source_id,
                logical_unit_id=logical_id,
            )

        first = _payload_values("Shared")
        second = _payload_values("Other")
        _insert(
            connection,
            "loadout_payloads",
            id=1,
            logical_unit_id=1,
            payload_sha256=_payload_sha(first),
            **first,
        )
        _insert(
            connection,
            "loadout_payloads",
            id=2,
            logical_unit_id=2,
            payload_sha256=_payload_sha(second),
            **second,
        )

        for army_id, unit_id, option_id, payload_id, points, swc in (
            (101, 1, 1, 1, 20, "0"),
            (102, 1, 1, 1, 21, "1"),
            (201, 2, 1, 2, 25, "0"),
        ):
            _insert(
                connection,
                "profile_groups",
                army_id=army_id,
                unit_id=unit_id,
                group_id=1,
                position=1,
                category_id=1,
                isc="Group",
                notes=None,
            )
            _insert(
                connection,
                "loadout_payload_occurrences",
                army_id=army_id,
                unit_id=unit_id,
                group_id=1,
                option_id=option_id,
                loadout_payload_id=payload_id,
                position=1,
                points=points,
                swc=swc,
            )
        connection.commit()
    finally:
        connection.close()
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_loadout_semantics_audits_published_payload_boundary(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    before = _sha256(database)

    report = audit_database(database)

    assert _sha256(database) == before
    summary = report["summary"]
    assert summary["status"] == "pass"
    assert summary["loadoutPayloadCount"] == 2
    assert summary["loadoutOccurrenceCount"] == 3
    assert summary["reusedPayloadCount"] == 1
    assert summary["repeatedSourceLoadoutKeyCount"] == 1
    assert summary["sourceLoadoutKeysWithPointsVariation"] == 1
    assert summary["sourceLoadoutKeysWithSwcVariation"] == 1
    assert summary["sourceLoadoutKeysWithMultiplePayloads"] == 0


def test_loadout_semantics_rejects_schema_drift(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE loadout_payloads ADD COLUMN new_semantic_field")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        LoadoutSemanticsAuditError,
        match=r"loadout_payloads.*unclassified new_semantic_field",
    ):
        audit_database(database)


def test_loadout_semantics_reports_invalid_payload_hash(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE loadout_payloads SET payload_sha256 = ? WHERE id = 1",
            ("0" * 64,),
        )
        connection.commit()
    finally:
        connection.close()

    report = audit_database(database)
    assert report["summary"]["status"] == "fail"
    assert report["summary"]["invalidPayloadHashCount"] == 1
    assert report["invalidPayloadIds"] == [1]
    assert main([str(database)]) == 1


def test_loadout_semantics_reports_logical_unit_mismatch(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE loadout_payload_occurrences SET loadout_payload_id = 2 "
            "WHERE army_id = 101"
        )
        connection.commit()
    finally:
        connection.close()

    report = audit_database(database)
    assert report["summary"]["status"] == "fail"
    assert report["summary"]["logicalUnitMismatchCount"] == 1


def test_loadout_semantics_json_is_deterministic(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert main([str(database), "--output", str(first)]) == 0
    assert main([str(database), "--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()
