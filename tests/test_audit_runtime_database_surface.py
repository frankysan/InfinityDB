from __future__ import annotations

import hashlib
from pathlib import Path

from infinity_army_data.normalize import normalize_master, validate_normalized
from infinity_db.database import export_database
from tools.audit_runtime_database_surface import (
    CONTEXTUAL,
    NO_ISSUE,
    OVERLAP,
    REPLACEABLE,
    SOURCE,
    audit_database,
    discover_runtime_database_methods,
)

ROOT = Path(__file__).resolve().parents[1]


def _runtime_database(tmp_path: Path) -> Path:
    nested = {
        "skills": [{"id": 11, "extra": [41]}],
        "equip": [{"id": 21, "extra": [42]}],
        "weapons": [{"id": 31, "extra": [43]}],
    }
    filters = {
        "category": [{"id": 1, "name": "Light Infantry"}],
        "chars": [{"id": 1, "name": "Cube"}],
        "type": [{"id": 1, "name": "Line Trooper"}],
        "equip": [{"id": 21, "name": "Medikit"}],
        "skills": [{"id": 11, "name": "Stealth"}],
        "weapons": [{"id": 31, "name": "Combi Rifle"}],
        "ammunition": [{"id": 51, "name": "Normal"}],
        "extras": [
            {"id": 41, "name": "+3"},
            {"id": 42, "name": "Mimetism"},
            {"id": 43, "name": "AP"},
        ],
    }
    group = {
        "id": 1,
        "category": 1,
        "profiles": [{"id": 1, "name": "Profile", "type": 1, **nested}],
        "options": [
            {
                "id": 1,
                "name": "Loadout",
                "points": 10,
                "swc": "0",
                **nested,
                "orders": [{"type": "regular", "list": 1, "total": 1}],
            }
        ],
    }
    master = {
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyMetadata": {
            "sourceFile": "metadata.json",
            "sourceSha256": "test-metadata",
            "data": {
                "factions": [{"id": 101, "parent": 101, "name": "Army", "slug": "army"}],
                "ammunitions": [{"id": 51, "name": "Normal"}],
                "weapons": [
                    {
                        "id": 31,
                        "type": "BS Weapon",
                        "name": "Combi Rifle",
                        "ammunition": 51,
                        "properties": ["AP"],
                        "distance": [],
                    }
                ],
                "skills": [{"id": 11, "name": "Stealth", "wiki": "skill"}],
                "equips": [{"id": 21, "name": "Medikit", "wiki": "equipment"}],
            },
        },
        "armyLists": {
            "101": {
                "_meta": {"slug": "army", "kind": "army"},
                "unitIds": [1],
                "filters": filters,
            }
        },
        "units": {
            "1": {
                "shared": {
                    "id": 1,
                    "name": "Unit",
                    "isc": "Unit",
                    "slug": "unit",
                    "canonical": 101,
                    "factions": [101],
                    "options": [{"id": 1, "name": "Global", **nested}],
                },
                "byArmy": {"101": {"profileGroups": [group]}},
            }
        },
    }
    normalized = normalize_master(master)
    validate_normalized(normalized)
    path = tmp_path / "infinity.db"
    export_database(normalized, path)
    return path


def _field(report: dict, table: str, field: str) -> dict:
    table_item = next(item for item in report["inventory"] if item["table"] == table)
    return next(item for item in table_item["fields"] if item["name"] == field)


def test_runtime_surface_audit_covers_current_player_serving_paths(tmp_path: Path) -> None:
    report = audit_database(_runtime_database(tmp_path), project_root=ROOT)

    assert report["summary"] == {
        "surfaceCount": 25,
        "runtimeTableCount": 62,
        "runtimeFieldCount": 230,
        "tableWithOpenIssueCount": 24,
        "replaceableSourceTableCount": 16,
        "semanticOverlapTableCount": 8,
        "issue:none:fieldCount": 152,
        "issue:replaceable_duplicate:fieldCount": 43,
        "issue:semantic_overlap:fieldCount": 35,
        "role:canonical_application:fieldCount": 105,
        "role:contextual_application:fieldCount": 60,
        "role:intentional_source_representation:fieldCount": 65,
    }
    assert report["openIssues"]["replaceableSourceTables"] == [
        "loadout_options",
        "option_equipment",
        "option_equipment_extras",
        "option_skill_extras",
        "option_skills",
        "option_weapon_extras",
        "option_weapon_templates",
        "option_weapons",
        "profile_equipment",
        "profile_equipment_extras",
        "profile_skill_extras",
        "profile_skills",
        "profile_weapon_extras",
        "profile_weapons",
        "profiles",
        "units",
    ]
    assert report["openIssues"]["semanticOverlapTables"] == [
        "army_lists",
        "equipment",
        "metadata_equipment",
        "metadata_factions",
        "metadata_skills",
        "metadata_weapons",
        "skills",
        "weapons",
    ]

    assert _field(report, "units", "name")["issue"] == REPLACEABLE
    assert _field(report, "units", "canonical_faction_id")["role"] == CONTEXTUAL
    assert _field(report, "unit_options", "name")["role"] == SOURCE
    assert _field(report, "unit_options", "name")["issue"] == NO_ISSUE
    assert _field(report, "metadata_skills", "name")["issue"] == OVERLAP


def test_runtime_surface_audit_is_deterministic_and_read_only(tmp_path: Path) -> None:
    database = _runtime_database(tmp_path)
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    first = audit_database(database, project_root=ROOT)
    second = audit_database(database, project_root=ROOT)

    assert first == second
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_runtime_method_discovery_matches_current_runtime_helpers() -> None:
    assert discover_runtime_database_methods(ROOT) == {
        "get_catalog_item",
        "get_skill",
        "get_trait",
        "get_unit",
        "list_armies",
        "list_catalog_items",
        "list_skill_extras",
        "list_traits",
        "list_units",
        "skill_source_ids",
        "snapshot_downloaded_on",
        "trait_usage_index",
        "validate",
        "visible_unit_ids",
    }
