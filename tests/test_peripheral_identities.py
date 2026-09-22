from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.peripheral_identities import (
    PERIPHERAL_IDENTITY_FORMAT,
    PERIPHERAL_IDENTITY_FORMAT_VERSION,
    PeripheralIdentityError,
    load_peripheral_identity_curated,
    parse_peripheral_identity_curated,
)
from infinity_db.peripheral_identity_coverage import audit_peripheral_identity_coverage


def _source() -> dict:
    return {
        "id": "army-json-test",
        "kind": "army-snapshot",
        "artifact": "JSON test.zip",
        "sha256": "a" * 64,
        "acquiredAt": "2026-09-22T06:00:00+02:00",
        "authority": "primary",
    }


def _document() -> dict:
    return {
        "format": PERIPHERAL_IDENTITY_FORMAT,
        "formatVersion": PERIPHERAL_IDENTITY_FORMAT_VERSION,
        "sources": [_source()],
        "entities": [
            {
                "id": "peripheral:example",
                "name": "Example Peripheral",
                "typeId": "rule:peripheral-type:cyberplug",
                "review": {"status": "reviewed", "reviewedOn": "2026-09-22"},
            }
        ],
        "profiles": [
            {
                "id": "peripheral-profile:example-connected",
                "entityId": "peripheral:example",
                "name": "Example Peripheral (Connected)",
                "mode": "connected",
                "review": {"status": "reviewed", "reviewedOn": "2026-09-22"},
            }
        ],
        "mappings": [
            {
                "id": "peripheral-mapping:army-101-1",
                "sourceId": "army-json-test",
                "armyId": 101,
                "peripheralId": 1,
                "sourceName": "EXAMPLE",
                "entityId": "peripheral:example",
                "profileId": "peripheral-profile:example-connected",
                "review": {
                    "status": "reviewed",
                    "reviewedOn": "2026-09-22",
                    "reason": "Reviewed test mapping.",
                },
            }
        ],
    }


def test_checked_in_peripheral_identity_contract_is_valid_and_unmapped() -> None:
    curated = load_peripheral_identity_curated()

    assert curated.entity_count == 0
    assert curated.profile_count == 0
    assert curated.mapping_count == 0
    assert curated.document["sources"][0]["id"] == "army-json-20260918-204434"


def test_peripheral_identity_contract_accepts_reviewed_entity_profile_and_mapping() -> None:
    curated = parse_peripheral_identity_curated(_document())

    assert curated.entity_count == 1
    assert curated.profile_count == 1
    assert curated.mapping_count == 1
    assert len(curated.content_sha256) == 64


def test_peripheral_identity_contract_rejects_mercs_as_identity_data() -> None:
    document = _document()
    document["mappings"][0]["mercs"] = 1

    with pytest.raises(PeripheralIdentityError, match="unknown field.*mercs"):
        parse_peripheral_identity_curated(document)


def test_peripheral_identity_contract_rejects_profile_from_other_entity() -> None:
    document = _document()
    document["entities"].append(
        {
            "id": "peripheral:other",
            "name": "Other Peripheral",
            "typeId": "rule:peripheral-type:servant",
            "review": {"status": "reviewed", "reviewedOn": "2026-09-22"},
        }
    )
    document["mappings"][0]["entityId"] = "peripheral:other"

    with pytest.raises(PeripheralIdentityError, match="profile belonging to entityId"):
        parse_peripheral_identity_curated(document)


def test_peripheral_identity_contract_requires_mapping_review_reason() -> None:
    document = _document()
    del document["mappings"][0]["review"]["reason"]

    with pytest.raises(PeripheralIdentityError, match="review.reason"):
        parse_peripheral_identity_curated(document)


def test_peripheral_identity_contract_rejects_duplicate_source_definition_mapping() -> None:
    document = _document()
    duplicate = dict(document["mappings"][0])
    duplicate["id"] = "peripheral-mapping:duplicate"
    duplicate["review"] = dict(duplicate["review"])
    document["mappings"].append(duplicate)

    with pytest.raises(PeripheralIdentityError, match="duplicate source Peripheral identity"):
        parse_peripheral_identity_curated(document)


def test_peripheral_identity_default_path_is_source_controlled() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "peripherals" / "army-identities.json"

    assert load_peripheral_identity_curated(path).document["format"] == PERIPHERAL_IDENTITY_FORMAT



def _coverage_database(tmp_path: Path, *, snapshot_sha256: str = "a" * 64) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            'CREATE TABLE "__infinity_metadata" (key TEXT PRIMARY KEY, value TEXT NOT NULL)'
        )
        connection.execute(
            "CREATE TABLE peripherals (army_id INTEGER, id INTEGER, name TEXT, mercs INTEGER)"
        )
        connection.execute("PRAGMA user_version = 18")
        connection.execute(
            'INSERT INTO "__infinity_metadata" (key, value) VALUES (?, ?)',
            (
                "_meta",
                json.dumps({"snapshotArchiveSha256": snapshot_sha256}),
            ),
        )
        connection.executemany(
            "INSERT INTO peripherals (army_id, id, name, mercs) VALUES (?, ?, ?, ?)",
            [
                (101, 1, "EXAMPLE", 0),
                (102, 2, "EXAMPLE", 1),
                (103, 3, " Example  ", 0),
                (101, 4, "UNMAPPED", 0),
            ],
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_peripheral_identity_coverage_reports_review_queue_and_curated_only(
    tmp_path: Path,
) -> None:
    curated = parse_peripheral_identity_curated(_document())
    report = audit_peripheral_identity_coverage(curated, _coverage_database(tmp_path))

    assert report["status"] == "needs-review"
    assert report["definitions"]["definitionCount"] == 4
    assert report["definitions"]["mappedDefinitionCount"] == 1
    assert report["definitions"]["unmappedDefinitionCount"] == 3
    assert report["definitions"]["reviewGroupCount"] == 2
    assert report["definitions"]["normalizedNameCollisionCount"] == 1
    assert report["validation"]["status"] == "valid"
    assert report["curated"]["curatedOnlyEntityCount"] == 0
    example = next(
        item for item in report["reviewQueue"] if item["normalizedName"] == "example"
    )
    assert example["definitionCount"] == 3
    assert example["unmappedDefinitionCount"] == 2
    assert example["nameCollision"] is True
    assert example["reviewedTargets"] == [
        {
            "entityId": "peripheral:example",
            "profileId": "peripheral-profile:example-connected",
        }
    ]


def test_peripheral_identity_coverage_detects_stale_mapping_and_source_name_drift(
    tmp_path: Path,
) -> None:
    document = _document()
    document["mappings"][0]["sourceName"] = "OLD NAME"
    stale = dict(document["mappings"][0])
    stale["id"] = "peripheral-mapping:army-999-99"
    stale["armyId"] = 999
    stale["peripheralId"] = 99
    stale["review"] = dict(stale["review"])
    document["mappings"].append(stale)

    report = audit_peripheral_identity_coverage(
        parse_peripheral_identity_curated(document), _coverage_database(tmp_path)
    )

    assert report["status"] == "invalid"
    assert report["validation"]["staleMappingCount"] == 1
    assert report["validation"]["sourceNameDriftCount"] == 1
    assert report["validation"]["status"] == "invalid"


def test_peripheral_identity_coverage_rejects_wrong_snapshot(tmp_path: Path) -> None:
    curated = parse_peripheral_identity_curated(_document())

    with pytest.raises(PeripheralIdentityError, match="exactly one source matching"):
        audit_peripheral_identity_coverage(
            curated, _coverage_database(tmp_path, snapshot_sha256="b" * 64)
        )


def _controller_coverage_database(tmp_path: Path) -> Path:
    path = _coverage_database(tmp_path)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE profiles (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, profile_id INTEGER, name TEXT
            );
            CREATE TABLE loadout_options (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, option_id INTEGER, name TEXT
            );
            CREATE TABLE profile_peripherals (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, profile_id INTEGER,
                position INTEGER, item_id INTEGER, quantity INTEGER
            );
            CREATE TABLE option_peripherals (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, option_id INTEGER,
                position INTEGER, item_id INTEGER, quantity INTEGER
            );
            CREATE TABLE profile_skills (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, profile_id INTEGER,
                item_id INTEGER
            );
            CREATE TABLE option_skills (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, option_id INTEGER,
                item_id INTEGER
            );
            CREATE TABLE skills (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE application_catalog_sources (
                catalog TEXT, application_item_id INTEGER, source_item_id INTEGER
            );
            CREATE TABLE application_domain_slugs (
                domain TEXT, application_id INTEGER, slug TEXT, status TEXT
            );
            """
        )
        connection.executemany(
            "INSERT INTO units (id, name) VALUES (?, ?)",
            [(10, "Doctor Controller"), (20, "Cyberplug Controller")],
        )
        connection.executemany(
            "INSERT INTO profiles (army_id, unit_id, group_id, profile_id, name) "
            "VALUES (?, ?, ?, ?, ?)",
            [(101, 10, 1, 1, "Doctor Profile"), (101, 20, 1, 1, "Cyberplug Profile")],
        )
        connection.execute(
            "INSERT INTO loadout_options (army_id, unit_id, group_id, option_id, name) "
            "VALUES (?, ?, ?, ?, ?)",
            (101, 20, 1, 1, "Cyberplug Loadout"),
        )
        connection.execute(
            "INSERT INTO profile_peripherals "
            "(army_id, unit_id, group_id, profile_id, position, item_id, quantity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (101, 10, 1, 1, 1, 1, 1),
        )
        connection.execute(
            "INSERT INTO option_peripherals "
            "(army_id, unit_id, group_id, option_id, position, item_id, quantity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (101, 20, 1, 1, 1, 4, 1),
        )
        connection.executemany(
            "INSERT INTO skills (id, name) VALUES (?, ?)",
            [(10, "Doctor"), (20, "Cyberplug")],
        )
        connection.execute(
            "INSERT INTO profile_skills (army_id, unit_id, group_id, profile_id, item_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (101, 10, 1, 1, 10),
        )
        connection.execute(
            "INSERT INTO option_skills (army_id, unit_id, group_id, option_id, item_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (101, 20, 1, 1, 20),
        )
        connection.executemany(
            "INSERT INTO application_catalog_sources "
            "(catalog, application_item_id, source_item_id) VALUES (?, ?, ?)",
            [("skills", 100, 10), ("skills", 200, 20)],
        )
        connection.executemany(
            "INSERT INTO application_domain_slugs (domain, application_id, slug, status) "
            "VALUES (?, ?, ?, ?)",
            [("skills", 100, "doctor", "resolved"), ("skills", 200, "cyberplug", "resolved")],
        )
        connection.commit()
    finally:
        connection.close()
    return path


def _controller_rules_documents() -> list[tuple[Path, dict]]:
    return [
        (
            Path("synthetic-rules.json"),
            {
                "records": [
                    {
                        "id": "skill:doctor",
                        "kind": "skill",
                        "armyLinks": [{"entity": "skill", "id": "doctor"}],
                    },
                    {
                        "id": "skill:engineer",
                        "kind": "skill",
                        "armyLinks": [{"entity": "skill", "id": "engineer"}],
                    },
                    {
                        "id": "skill:cyberplug",
                        "kind": "skill",
                        "armyLinks": [{"entity": "skill", "id": "cyberplug"}],
                    },
                    {
                        "id": "rule:peripheral-type:servant",
                        "kind": "rule",
                        "facts": {
                            "category": "peripheral-type",
                            "controllerEligibility": {
                                "anyOf": [
                                    {"hasSkill": "skill:doctor"},
                                    {"hasSkill": "skill:engineer"},
                                ]
                            },
                        },
                    },
                    {
                        "id": "rule:peripheral-type:cyberplug",
                        "kind": "rule",
                        "facts": {
                            "category": "peripheral-type",
                            "controllerEligibility": {"hasSkill": "skill:cyberplug"},
                        },
                    },
                    {
                        "id": "rule:peripheral-type:synchronized",
                        "kind": "rule",
                        "facts": {
                            "category": "peripheral-type",
                            "controllerEligibility": {"status": "not-stated"},
                        },
                    },
                ]
            },
        )
    ]


def test_peripheral_identity_coverage_reports_bidirectional_controller_evidence(
    tmp_path: Path,
) -> None:
    report = audit_peripheral_identity_coverage(
        parse_peripheral_identity_curated(_document()),
        _controller_coverage_database(tmp_path),
        rules_documents=_controller_rules_documents(),
    )

    graph = report["controllerGraph"]
    assert graph["status"] == "available"
    assert graph["attachmentCount"] == 2
    assert graph["controllerCount"] == 2
    assert graph["evaluableTypeIds"] == [
        "rule:peripheral-type:cyberplug",
        "rule:peripheral-type:servant",
    ]

    evidence = {
        (row["armyId"], row["peripheralId"]): row for row in graph["definitionEvidence"]
    }
    example = evidence[(101, 1)]
    assert example["typeEligibility"]["rule:peripheral-type:servant"]["consistent"] == 1
    assert example["typeEligibility"]["rule:peripheral-type:cyberplug"]["inconsistent"] == 1
    assert example["controllers"][0]["directSkillSlugs"] == ["doctor"]

    unmapped = evidence[(101, 4)]
    assert unmapped["typeEligibility"]["rule:peripheral-type:cyberplug"]["consistent"] == 1
    assert unmapped["typeEligibility"]["rule:peripheral-type:servant"]["inconsistent"] == 1
    loadout_controller = next(
        row for row in graph["controllerToPeripherals"] if row["controllerKind"] == "loadout"
    )
    assert loadout_controller["peripherals"] == [
        {"peripheralId": 4, "peripheralName": "UNMAPPED", "quantity": 1}
    ]

    review = next(row for row in report["reviewQueue"] if row["normalizedName"] == "unmapped")
    assert review["controllerEvidence"]["attachmentCount"] == 1
    assert (
        review["controllerEvidence"]["typeEligibility"]["rule:peripheral-type:cyberplug"]
        == {"consistent": 1, "inconsistent": 0, "ambiguous": 0, "unknown": 0}
    )
