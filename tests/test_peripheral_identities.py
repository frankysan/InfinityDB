from __future__ import annotations

from pathlib import Path

import pytest

from infinity_db.peripheral_identities import (
    PERIPHERAL_IDENTITY_FORMAT,
    PERIPHERAL_IDENTITY_FORMAT_VERSION,
    PeripheralIdentityError,
    load_peripheral_identity_curated,
    parse_peripheral_identity_curated,
)


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
