from __future__ import annotations

import hashlib
from pathlib import Path

from infinity_army_data.normalize import normalize_master, validate_normalized
from infinity_db.database import export_database
from tools.audit_runtime_database_surface import (
    CANONICAL,
    CONTEXTUAL,
    NO_ISSUE,
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
        "surfaceCount": 29,
        "runtimeTableCount": 50,
        "runtimeFieldCount": 200,
        "tableWithOpenIssueCount": 0,
        "replaceableSourceTableCount": 0,
        "semanticOverlapTableCount": 0,
        "issue:none:fieldCount": 200,
        "role:canonical_application:fieldCount": 115,
        "role:contextual_application:fieldCount": 62,
        "role:intentional_source_representation:fieldCount": 23,
    }
    assert report["openIssues"]["replaceableSourceTables"] == []
    assert report["openIssues"]["semanticOverlapTables"] == []

    observed_tables = {item["table"] for item in report["inventory"]}
    assert {
        "profiles",
        "profile_skills",
        "profile_skill_extras",
        "profile_equipment",
        "profile_equipment_extras",
        "profile_weapons",
        "profile_weapon_extras",
        "loadout_options",
        "option_skills",
        "option_skill_extras",
        "option_equipment",
        "option_equipment_extras",
        "option_weapons",
        "option_weapon_templates",
        "option_weapon_extras",
    }.isdisjoint(observed_tables)
    assert _field(report, "units", "canonical_faction_id")["role"] == CONTEXTUAL
    assert _field(report, "logical_units", "canonical_faction_id")["role"] == CONTEXTUAL
    assert _field(report, "logical_units", "main_army_id")["role"] == CONTEXTUAL
    assert _field(report, "logical_units", "display_army_id")["role"] == CONTEXTUAL
    assert _field(report, "logical_units", "name")["role"] == CANONICAL
    assert _field(report, "application_armies", "name")["role"] == CANONICAL
    assert _field(report, "application_army_sources", "source_army_id")["role"] == CONTEXTUAL
    assert _field(report, "application_catalog_items", "name")["role"] == CANONICAL
    assert _field(report, "application_domain_slugs", "slug")["role"] == CANONICAL
    assert _field(report, "application_catalog_sources", "source_item_id")["role"] == CONTEXTUAL
    assert _field(report, "army_lists", "kind")["role"] == SOURCE
    assert "metadata_factions" not in observed_tables
    assert _field(report, "unit_options", "name")["role"] == SOURCE
    assert _field(report, "unit_options", "name")["issue"] == NO_ISSUE
    assert "metadata_skills" not in observed_tables
    assert "metadata_equipment" not in observed_tables
    assert _field(report, "metadata_weapons", "name")["role"] == CONTEXTUAL
    assert _field(report, "metadata_weapons", "name")["issue"] == NO_ISSUE


def test_runtime_surface_audit_is_deterministic_and_read_only(tmp_path: Path) -> None:
    database = _runtime_database(tmp_path)
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    first = audit_database(database, project_root=ROOT)
    second = audit_database(database, project_root=ROOT)

    assert first == second
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_runtime_method_discovery_matches_current_runtime_helpers() -> None:
    assert discover_runtime_database_methods(ROOT) == {
        "application_catalog_id",
        "application_domain_id",
        "application_slug",
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
