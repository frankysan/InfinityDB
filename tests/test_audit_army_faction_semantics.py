from __future__ import annotations

import hashlib
from pathlib import Path

from infinity_army_data.normalize import normalize_master, validate_normalized
from infinity_db.database import export_database, raw_database_path
from tools.audit_army_faction_semantics import audit_database


def _army_database(tmp_path: Path) -> Path:
    master = {
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyMetadata": {
            "sourceFile": "metadata.json",
            "sourceSha256": "test-metadata",
            "data": {
                "factions": [
                    {"id": 101, "parent": 101, "name": "Main Army", "slug": "main-army"},
                    {"id": 102, "parent": 101, "name": "Sectorial", "slug": "sectorial"},
                ]
            },
        },
        "armyLists": {
            "101": {
                "_meta": {"slug": "main-army", "kind": "army"},
                "unitIds": [1],
                "filters": {},
            },
            "102": {
                "_meta": {"slug": "sectorial", "kind": "army"},
                "unitIds": [2],
                "filters": {},
            },
        },
        "units": {
            "1": {
                "shared": {
                    "id": 1,
                    "name": "Unit One",
                    "isc": "Unit One",
                    "slug": "unit-one",
                    "canonical": 101,
                    "factions": [101, 203],
                },
                "byArmy": {"101": {"profileGroups": []}},
            },
            "2": {
                "shared": {
                    "id": 2,
                    "name": "Unit Two",
                    "isc": "Unit Two",
                    "slug": "unit-two",
                    "canonical": 102,
                    "factions": [102],
                },
                "byArmy": {"102": {"profileGroups": []}},
            },
        },
    }
    normalized = normalize_master(master)
    validate_normalized(normalized)
    path = tmp_path / "infinity.db"
    export_database(normalized, path)
    return path


def test_army_faction_audit_distinguishes_list_occurrence_from_game_wide_membership(
    tmp_path: Path,
) -> None:
    report = audit_database(_army_database(tmp_path))

    assert report["formatVersion"] == 2
    assert report["summary"] == {
        "sourceArmyListCount": 2,
        "metadataFactionCount": 2,
        "sharedArmyMetadataIdentityCount": 2,
        "armyMetadataNameSlugMismatchCount": 0,
        "applicationArmyIdentityCount": 2,
        "materializedApplicationArmyIdentityCount": 2,
        "applicationArmySourceMappingCount": 2,
        "applicationReinforcementParentCount": 0,
        "canonicalizedSourceArmyIdentityCount": 2,
        "ordinarySourceListCount": 2,
        "reinforcementSourceListCount": 0,
        "playableApplicationArmyCount": 2,
        "nonPlayableApplicationArmyCount": 0,
        "factionIdentityRegistryCount": 3,
        "factionIdentityWithoutArmyListCount": 1,
        "armyUnitOccurrenceCount": 2,
        "declaredUnitFactionMembershipCount": 3,
        "unitsWithMembershipBeyondStandardOccurrencesCount": 1,
        "extraDeclaredMembershipReferenceCount": 1,
        "standardOccurrenceMissingDeclaredMembershipCount": 0,
        "sourceCanonicalFactionWithoutArmyListCount": 0,
        "nullAvailabilityKindCount": 2,
    }
    assert report["applicationRoles"] == {
        "main": 1,
        "sectorial": 1,
        "non_aligned": 0,
        "grouping": 0,
        "reinforcement": 0,
        "unknown": 0,
    }
    assert report["applicationModel"]["sourceDerivedIdentityEquivalent"] is True
    assert report["applicationModel"]["runtimeIdentityEquivalent"] is True
    assert [army["id"] for army in report["applicationModel"]["armies"]] == [101, 102]
    assert report["applicationModel"]["reinforcementParents"] == []
    assert report["gameWideFactionContext"]["identityRegistryWithoutArmyList"] == [203]
    assert report["gameWideFactionContext"]["declaredMembershipFactionIdsWithoutArmyList"] == [203]
    assert report["gameWideFactionContext"]["declaredMembershipExtrasByFaction"] == [
        {"factionId": 203, "referenceCount": 1}
    ]


def test_army_faction_audit_classifies_overlapping_source_constructs(tmp_path: Path) -> None:
    report = audit_database(_army_database(tmp_path))
    fields = report["fieldClassification"]

    assert fields["army_lists"]["id"]["role"] == "source_list_identity"
    assert fields["metadata_factions"]["parent"]["role"] == "hierarchy_context"
    assert fields["army_units"]["army_id"]["role"] == "army_local_occurrence"
    assert fields["unit_factions"]["faction_id"]["role"] == "game_wide_relationship"
    assert fields["units"]["canonical_faction_id"]["role"] == "source_origin_context"
    assert report["sourceIdentityOverlap"]["armyOnlyIds"] == []
    assert report["sourceIdentityOverlap"]["metadataOnlyIds"] == []
    assert report["sourceIdentityOverlap"]["nameSlugMismatches"] == []


def test_army_faction_audit_is_deterministic_and_read_only(tmp_path: Path) -> None:
    database = _army_database(tmp_path)
    raw = raw_database_path(database)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    raw_before = hashlib.sha256(raw.read_bytes()).hexdigest()

    assert audit_database(database) == audit_database(database)
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == raw_before
