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
        for source_unit_id, logical_unit_id in ((1, 10), (2, 10), (3, 30), (4, 40)):
            _insert(
                connection,
                "logical_unit_sources",
                source_unit_id=source_unit_id,
                logical_unit_id=logical_unit_id,
            )
        for unit_id, name in ((1, "Alpha"), (2, "Alpha REINF"), (3, "Beta"), (4, "Gamma")):
            _insert(
                connection,
                "units",
                id=unit_id,
                name=name,
                source_defined=1,
                source_role="standard",
            )
        _insert(connection, "army_lists", id=101, name="Army", kind="army", reinforcement_id=199)
        _insert(
            connection,
            "army_lists",
            id=199,
            name="Reinforcement Pool",
            kind="reinforcement",
            reinforcement_id=None,
        )
        _insert(
            connection,
            "application_armies",
            id=101,
            name="Army",
            role="main",
            playable=1,
        )
        _insert(
            connection,
            "application_armies",
            id=199,
            name="Reinforcement Pool",
            role="reinforcement",
            playable=1,
        )
        _insert(
            connection,
            "application_army_sources",
            application_army_id=101,
            source_army_id=101,
        )
        _insert(
            connection,
            "application_army_sources",
            application_army_id=199,
            source_army_id=199,
        )
        _insert(
            connection,
            "application_army_reinforcement_parents",
            reinforcement_army_id=199,
            parent_army_id=101,
        )
        _insert(
            connection,
            "relations",
            army_id=101,
            relation_id=1,
            position=1,
            min_count=1,
            max_count=1,
            is_group=0,
        )
        for relation_unit_id, unit_id in ((1, 1), (2, 2)):
            _insert(
                connection,
                "relation_units",
                army_id=101,
                relation_id=1,
                relation_unit_id=relation_unit_id,
                position=relation_unit_id,
                unit_id=unit_id,
                profile_id=None,
                per_parent=None,
            )
        _insert(
            connection,
            "relations",
            army_id=101,
            relation_id=2,
            position=2,
            min_count=1,
            max_count=2,
            is_group=1,
        )
        _insert(
            connection,
            "relation_units",
            army_id=101,
            relation_id=2,
            relation_unit_id=1,
            position=1,
            unit_id=3,
            profile_id=2,
            per_parent=1,
        )
        _insert(
            connection,
            "relation_dependencies",
            army_id=101,
            relation_id=2,
            relation_unit_id=1,
            dependency_id=1,
            position=1,
            unit_id=4,
            profile_id=1,
            group_id=2,
            min_count=1,
            min_dependant=2,
            options="[7,8]",
            raw=None,
        )

        for army_id in (101, 102):
            _insert(
                connection,
                "profile_payload_occurrences",
                army_id=army_id,
                unit_id=1,
                group_id=1,
                profile_id=1,
                profile_payload_id=300,
                position=1,
                ava=1,
                logo=None,
            )

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
            "loadout_payloads",
            id=200,
            logical_unit_id=10,
            payload_sha256="200",
            name="Parent loadout",
            minis=1,
            disabled=0,
        )
        for army_id in (101, 102):
            _insert(
                connection,
                "loadout_payload_occurrences",
                army_id=army_id,
                unit_id=1,
                group_id=1,
                option_id=1,
                loadout_payload_id=200,
                position=1,
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
    assert report["includes"]["profile"]["parentPayloadInvariance"] == {
        "status": "contextual_variants",
        "affectedCanonicalParentPayloadCount": 1,
        "affectedCanonicalParentPayloadsWithMultipleOccurrences": 1,
        "variantCanonicalParentPayloadCount": 1,
        "unmappedParentRowCount": 0,
        "unresolvedTargetRowCount": 0,
    }
    assert report["relations"]["relationCount"] == 2
    assert report["relations"]["singleLogicalEndpointSetRelationCount"] == 1
    assert report["relations"]["crossLogicalEndpointSetRelationCount"] == 1
    assert report["relations"]["dependencyCount"] == 1
    assert report["reinforcementSections"]["missingCanonicalParentLinkCount"] == 0
    assert report["reinforcementSections"]["materializedCanonicalParentLinkCount"] == 1
    assert report["includes"]["loadout"]["parentPayloadInvariance"] == {
        "status": "contextual_variants",
        "affectedCanonicalParentPayloadCount": 1,
        "affectedCanonicalParentPayloadsWithMultipleOccurrences": 1,
        "variantCanonicalParentPayloadCount": 1,
        "unmappedParentRowCount": 0,
        "unresolvedTargetRowCount": 0,
    }


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

    profile = report["includes"]["profile"]["rows"][0]
    assert profile["groupId"] == 1
    assert profile["parentId"] == 1
    loadout = report["includes"]["loadout"]["rows"][0]
    assert loadout["groupId"] == 1
    assert loadout["parentId"] == 1
    shared = report["includes"]["unitOption"]["rows"][0]
    assert shared["targetArmyIds"] == [101, 102]
    assert shared["targetPayloadIds"] == [100, 101]
    relation = report["relations"]["relations"][1]
    assert relation["armyId"] == 101
    assert relation["members"][0]["logicalUnitId"] == 30
    assert relation["members"][0]["dependencies"][0]["logicalUnitId"] == 40
    reinforcement = report["reinforcementSections"]["parentLinks"][0]
    assert reinforcement == {
        "parentSourceArmyId": 101,
        "parentApplicationArmyId": 101,
        "reinforcementSourceArmyId": 199,
        "reinforcementApplicationArmyId": 199,
        "materialized": True,
    }
    repeated = report["peripherals"]["repeatedCandidateDefinitions"]
    assert repeated == [
        {
            "name": "BOT",
            "mercs": 0,
            "rawIdentities": [{"armyId": 101, "id": 1001}, {"armyId": 102, "id": 2001}],
        }
    ]
    profile_variants = report["includes"]["profile"]["parentPayloadInvariance"][
        "variantParentPayloads"
    ]
    assert profile_variants == [
        {
            "parentPayloadId": 300,
            "variants": [
                {
                    "signature": [
                        {
                            "position": 1,
                            "targetPayloadId": 100,
                            "quantity": 1,
                            "raw": None,
                        }
                    ],
                    "occurrences": [
                        {"armyId": 101, "unitId": 1, "groupId": 1, "parentId": 1}
                    ],
                },
                {
                    "signature": [],
                    "occurrences": [
                        {"armyId": 102, "unitId": 1, "groupId": 1, "parentId": 1}
                    ],
                },
            ],
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
    assert report["formatVersion"] == 3
