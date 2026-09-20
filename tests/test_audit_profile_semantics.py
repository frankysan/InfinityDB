from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_profile_semantics import (
    EXPECTED_COLUMNS,
    ProfileSemanticsAuditError,
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


def _profile(army_id: int, unit_id: int, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "army_id": army_id,
        "unit_id": unit_id,
        "group_id": 1,
        "profile_id": 1,
        "position": 1,
        "name": f"Profile {unit_id}",
        "logo": "logo.svg",
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
    row.update(overrides)
    return row


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        for table, columns in EXPECTED_COLUMNS.items():
            definition = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{table}" ({definition})')

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
        for unit_id in range(1, 6):
            _insert(
                connection,
                "logical_unit_sources",
                source_unit_id=unit_id,
                logical_unit_id=unit_id,
            )

        # Each source-profile key occurs in two armies.  The five keys isolate
        # AVA, logo, representation-only skill data, real skill data, and WIP.
        profiles = [
            _profile(101, 1, ava=2),
            _profile(102, 1, ava=1),
            _profile(101, 2, logo="a.svg"),
            _profile(102, 2, logo="b.svg"),
            _profile(101, 3),
            _profile(102, 3),
            _profile(101, 4),
            _profile(102, 4),
            _profile(101, 5, wip=13),
            _profile(102, 5, wip=14),
        ]
        for row in profiles:
            _insert(connection, "profiles", **row)
            _insert(
                connection,
                "profile_groups",
                army_id=row["army_id"],
                unit_id=row["unit_id"],
                group_id=1,
                position=1,
                category_id=1,
                isc=f"Group {row['unit_id']}",
                notes=None,
            )

        # Unit 3 differs only by explicit-vs-omitted quantity and display_order.
        for occurrence_id, army_id, display_order, quantity in (
            (1, 101, 1, None),
            (2, 102, 7, 1),
        ):
            _insert(
                connection,
                "profile_skills",
                occurrence_id=occurrence_id,
                army_id=army_id,
                unit_id=3,
                group_id=1,
                profile_id=1,
                position=1,
                item_id=10,
                display_order=display_order,
                quantity=quantity,
                raw=None,
            )

        # Unit 4 has a genuine extra skill in the second army.
        _insert(
            connection,
            "profile_skills",
            occurrence_id=3,
            army_id=101,
            unit_id=4,
            group_id=1,
            profile_id=1,
            position=1,
            item_id=10,
            display_order=1,
            quantity=None,
            raw=None,
        )
        for occurrence_id, position, item_id in ((4, 1, 10), (5, 2, 11)):
            _insert(
                connection,
                "profile_skills",
                occurrence_id=occurrence_id,
                army_id=102,
                unit_id=4,
                group_id=1,
                profile_id=1,
                position=position,
                item_id=item_id,
                display_order=position,
                quantity=None,
                raw=None,
            )

        connection.commit()
    finally:
        connection.close()
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_profile_semantics_stages_context_and_representation_variation(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    report = audit_database(database)

    assert report["summary"] == {
        "profileOccurrenceCount": 10,
        "sourceProfileIdentityCount": 5,
        "repeatedSourceProfileIdentityCount": 5,
        "repeatedSourceProfileOccurrenceCount": 10,
        "baselineVariantIdentityCount": 5,
        "withoutAvaVariantIdentityCount": 4,
        "withoutAvaOrLogoVariantIdentityCount": 3,
        "withoutAvaOrLogoAndNormalizedRepresentationVariantIdentityCount": 2,
    }
    assert report["fields"]["ava"]["sameSourceVariantIdentityCount"] == 1
    assert report["fields"]["logo"]["sameSourceVariantIdentityCount"] == 1
    assert report["fields"]["wip"]["sameSourceVariantIdentityCount"] == 1

    candidate = report["candidateModel"]
    assert candidate["scope"] == "logical_unit"
    assert candidate["profileOccurrenceCount"] == 10
    assert candidate["sourceUnitDistinctPayloadCount"] == 8
    assert candidate["logicalUnitDistinctPayloadCount"] == 8
    assert candidate["repeatedOccurrenceCount"] == 2
    assert candidate["payloadRelationships"] == [
        "characteristics",
        "skills",
        "equipment",
        "weapons",
    ]
    assert candidate["deferredContextRelationships"] == [
        "includes",
        "peripherals",
        "profile_groups",
    ]

    skills = report["relationships"]["skills"]
    assert skills["sameSourceRawVariantIdentityCount"] == 2
    assert skills["sameSourceNormalizedVariantIdentityCount"] == 1
    assert skills["representationOnlyVariantIdentityCount"] == 1


def test_profile_semantics_records_field_and_relationship_classification(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path))

    assert report["fields"]["army_id"]["classification"] == "source_provenance"
    assert report["fields"]["position"]["classification"] == "normalization_only"
    assert report["fields"]["name"]["classification"] == "canonical_fact"
    assert report["fields"]["type_id"]["classification"] == "relationship"
    assert report["fields"]["ava"]["classification"] == "contextual_delta"
    assert report["fields"]["notes"]["nonNullCount"] == 0
    assert report["relationships"]["peripherals"]["rowCount"] == 0
    assert report["profileGroups"]["fields"]["category_id"]["classification"] == "relationship"


def test_profile_semantics_rejects_unclassified_schema_drift(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE profiles ADD COLUMN future_field")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        ProfileSemanticsAuditError,
        match=r"profiles.*unclassified future_field",
    ):
        audit_database(database)


def test_candidate_payloads_reuse_exact_payload_across_one_logical_unit(
    tmp_path: Path,
) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE logical_unit_sources SET logical_unit_id = 1 WHERE source_unit_id = 2"
        )
        connection.execute(
            "UPDATE profiles SET name = 'Profile 1' WHERE unit_id = 2"
        )
        connection.commit()
    finally:
        connection.close()

    candidate = audit_database(database)["candidateModel"]

    assert candidate["sourceUnitDistinctPayloadCount"] == 8
    assert candidate["logicalUnitDistinctPayloadCount"] == 7
    assert candidate["additionalDistinctPayloadReductionFromLogicalIdentity"] == 1


def test_profile_semantics_requires_complete_logical_unit_mapping(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "DELETE FROM logical_unit_sources WHERE source_unit_id = 5"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        ProfileSemanticsAuditError,
        match="Source unit 5 has no logical-unit mapping",
    ):
        audit_database(database)


def test_profile_semantics_is_read_only_and_json_is_deterministic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = _fixture_database(tmp_path)
    before = _sha256(database)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert main([str(database), "--output", str(first)]) == 0
    assert main([str(database), "--output", str(second)]) == 0
    assert _sha256(database) == before
    assert first.read_bytes() == second.read_bytes()

    report = json.loads(first.read_text(encoding="utf-8"))
    assert report["formatVersion"] == 2
    assert report["sourceProfileKey"] == ["unit_id", "group_id", "profile_id"]
    assert "not a proposed canonical" in report["sourceProfileKeyCaveat"]
    output = capsys.readouterr().out
    assert "Profiles: 10 occurrences" in output
    assert "8 logical-unit payloads from 10 occurrences" in output
