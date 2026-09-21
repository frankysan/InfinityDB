from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_peripheral_semantics import (
    REQUIRED_COLUMNS,
    PeripheralSemanticsAuditError,
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
        _insert(
            connection,
            "__infinity_metadata",
            key="warnings",
            value=json.dumps(
                [
                    {
                        "code": "global_option_peripheral",
                        "message": "ambiguous army-local peripheral",
                        "context": {"unit_id": 1, "value": {"id": 99}},
                    }
                ]
            ),
        )

        for army_id, peripheral_id, name, mercs in (
            (101, 1, "BOT", 0),
            (102, 2, "BOT", 1),
            (101, 3, "DRONE", 0),
            (102, 4, "DRONE", 0),
            (101, 5, "ARMY-ONLY", 0),
            (102, 6, "ARMY-ONLY", 0),
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

        for army_id, item_id in ((101, 1), (102, 2)):
            _insert(
                connection,
                "profile_payload_occurrences",
                army_id=army_id,
                unit_id=10,
                group_id=1,
                profile_id=1,
                profile_payload_id=100,
            )
            _insert(
                connection,
                "profile_peripherals",
                occurrence_id=army_id,
                army_id=army_id,
                unit_id=10,
                group_id=1,
                profile_id=1,
                position=1,
                item_id=item_id,
                display_order=None,
                quantity=1,
                raw=None,
            )

        for army_id, item_id in ((101, 3), (102, 4)):
            _insert(
                connection,
                "loadout_payload_occurrences",
                army_id=army_id,
                unit_id=10,
                group_id=1,
                option_id=1,
                loadout_payload_id=200,
            )
            _insert(
                connection,
                "option_peripherals",
                occurrence_id=army_id,
                army_id=army_id,
                unit_id=10,
                group_id=1,
                option_id=1,
                position=1,
                item_id=item_id,
                display_order=None,
                quantity=1,
                raw=None,
            )

        _insert(
            connection,
            "loadout_payload_occurrences",
            army_id=101,
            unit_id=20,
            group_id=1,
            option_id=1,
            loadout_payload_id=201,
        )
        _insert(
            connection,
            "loadout_payload_occurrences",
            army_id=102,
            unit_id=20,
            group_id=1,
            option_id=1,
            loadout_payload_id=201,
        )
        _insert(
            connection,
            "option_peripherals",
            occurrence_id=999,
            army_id=101,
            unit_id=20,
            group_id=1,
            option_id=1,
            position=1,
            item_id=3,
            display_order=None,
            quantity=1,
            raw=None,
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_peripheral_audit_separates_identity_context_and_availability(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path))

    definitions = report["definitions"]
    assert definitions["definitionCount"] == 6
    assert definitions["distinctNameCount"] == 3
    assert definitions["namesWithMercsVariants"] == 1
    assert definitions["identityCandidate"]["fields"] == ["name"]

    availability = report["availabilityMechanisms"]
    assert availability["attachedDefinitionCount"] == 4
    assert availability["definitionOnlyCount"] == 2
    assert availability["definitionOnlyNameCount"] == 1


def test_peripheral_audit_detects_canonical_parent_relationship_variants(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path))

    profiles = report["canonicalParentStability"]["profile"]
    assert profiles["semanticVariantPayloadCount"] == 0
    assert profiles["representationVariantPayloadCount"] == 1

    loadouts = report["canonicalParentStability"]["loadout"]
    assert loadouts["semanticVariantPayloadCount"] == 1
    assert loadouts["payloadsWithAnyAttachment"] == 2


def test_peripheral_audit_preserves_curated_rules_boundary(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path))

    eligibility = report["controllerEligibility"]
    assert eligibility["status"] == "not_inferred_from_army_source"
    assert eligibility["curatedDataRequired"] is True
    assert report["normalizationGaps"]["globalUnitOptionPeripheralWarningCount"] == 1


def test_peripheral_audit_details_show_definition_only_and_variant_evidence(
    tmp_path: Path,
) -> None:
    report = audit_database(_fixture_database(tmp_path), include_details=True)

    definition_only = report["availabilityMechanisms"]["definitionOnlyDefinitions"]
    assert [(row["armyId"], row["name"]) for row in definition_only] == [
        (101, "ARMY-ONLY"),
        (102, "ARMY-ONLY"),
    ]
    variants = report["canonicalParentStability"]["loadout"]["semanticVariants"]
    assert len(variants) == 1
    assert variants[0]["payloadId"] == 201


def test_peripheral_audit_rejects_missing_schema(tmp_path: Path) -> None:
    path = tmp_path / "broken.db"
    sqlite3.connect(path).close()

    with pytest.raises(PeripheralSemanticsAuditError, match="Missing required table"):
        audit_database(path)


def test_peripheral_audit_cli_writes_report(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    output = tmp_path / "peripheral-audit.json"

    assert main([str(database), "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "InfinityDB peripheral semantics audit"
