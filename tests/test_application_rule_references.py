from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from infinity_army_data.metadata import decode_metadata
from infinity_army_data.normalize import normalize_master, validate_normalized
from infinity_db.curated import load_curated_directory
from infinity_db.database import Database, export_database
from infinity_db.hacking_program_catalog import HackingProgramCatalog
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.skill_catalog import SkillCatalog


def _reference_database(tmp_path: Path) -> Database:
    skills = [
        {"id": 1000, "name": "Hacker"},
        *[
            {"id": 18 + level, "name": f"Martial Arts L{level}"}
            for level in range(1, 6)
        ],
        {"id": 25, "name": "Booty"},
        {"id": 55, "name": "MetaChemistry"},
    ]
    equipment = [
        {"id": 100, "name": "Hacking Device"},
        {"id": 101, "name": "Hacking Device Plus"},
        {"id": 145, "name": "Killer Hacking Device"},
        {"id": 182, "name": "EVO Hacking Device"},
    ]
    source = {
        "factions": [{"id": 101, "parent": 101, "name": "Army", "slug": "army"}],
        "skills": skills,
        "equips": equipment,
        "hack": [
            {
                "name": "Carbonite",
                "attack": "0",
                "opponent": "0",
                "damage": "7",
                "burst": "2",
                "special": "DA Ammo. State: IMM-B. Non-Lethal.",
                "devices": [100, 101],
                "target": ["TAG", "HI", "REM", "Hacker", "VH"],
                "skillType": ["short", "aro"],
                "extra": 13,
            },
            {
                "name": "Zero Pain",
                "attack": "0",
                "opponent": "-3",
                "damage": "-",
                "burst": "2",
                "special": "Nullifies Comms Attack.",
                "target": [],
                "skillType": ["short", "aro"],
                "extra": 287,
            },
        ],
        "martialArts": [
            {
                "name": str(level),
                "attack": "0" if level == 1 else "+3",
                "opponent": "-3",
                "damage": "-",
                "burst": "+1B" if level >= 4 else "0",
            }
            for level in range(1, 6)
        ],
        "metachemistry": [
            {"id": 1, "name": "1-3", "value": "+3 PH"},
            {"id": 4, "name": "4-5", "value": "Super-Jump"},
        ],
        "booty": [
            {"id": 1, "name": "1-2", "value": "+1 ARM"},
            {"id": 3, "name": "3-4", "value": "Light Flamethrower"},
        ],
    }
    envelope = decode_metadata(json.dumps(source).encode(), "metadata.json")
    master = {
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyMetadata": envelope,
        "armyLists": {
            "101": {
                "_meta": {"slug": "army", "kind": "army"},
                "unitIds": [1],
                "filters": {"skills": skills, "equip": equipment},
            }
        },
        "units": {
            "1": {
                "shared": {"id": 1, "name": "Unit", "factions": [101]},
                "byArmy": {"101": {}},
            }
        },
    }
    normalized = normalize_master(master)
    validate_normalized(normalized)
    path = tmp_path / "infinity.db"
    export_database(normalized, path)
    return Database(path)


def test_structured_reference_metadata_is_materialized_without_raw_tables(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)

    programs = database.list_hacking_programs()
    assert [program["name"] for program in programs] == ["Carbonite", "Zero Pain"]
    assert programs[0]["attack_mod"] == "0"
    assert programs[0]["ps"] == "7"
    assert programs[0]["targets"] == ["TAG", "HI", "REM", "Hacker", "VH"]
    assert programs[0]["skill_types"] == ["short", "aro"]
    assert programs[0]["source_extra_id"] == 13
    assert programs[0]["devices"] == [
        {
            "source_id": 100,
            "id": 100,
            "slug": "hacking-device",
            "name": "Hacking Device",
        },
        {
            "source_id": 101,
            "id": 101,
            "slug": "hacking-device-plus",
            "name": "Hacking Device Plus",
        },
    ]
    assert programs[1]["devices"] == []

    assert database.list_martial_arts_levels()[0] == {
        "position": 1,
        "level": "1",
        "attack_mod": "0",
        "opponent_mod": "-3",
        "ps_mod": "-",
        "burst_mod": "0",
    }
    assert database.list_metachemistry_results() == [
        {"id": 1, "roll": "1-3", "result": "+3 PH"},
        {"id": 4, "roll": "4-5", "result": "Super-Jump"},
    ]
    assert database.list_booty_results() == [
        {"id": 1, "roll": "1-2", "result": "+1 ARM"},
        {"id": 3, "roll": "3-4", "result": "Light Flamethrower"},
    ]

    with sqlite3.connect(database.path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "metadata_hacking_programs" not in tables
    assert "metadata_martial_arts" not in tables
    assert "metadata_metachemistry" not in tables
    assert "metadata_booty" not in tables
    assert {
        "application_hacking_programs",
        "application_hacking_program_devices",
        "application_hacking_program_targets",
        "application_hacking_program_skill_types",
        "application_martial_arts_levels",
        "application_metachemistry_results",
        "application_booty_results",
    } <= tables


def test_structured_reference_metadata_is_attached_to_existing_skill_details(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)
    catalog = SkillCatalog(database, None)

    hacker = catalog.get_skill(1000)
    martial_arts = catalog.get_skill(19)
    booty = catalog.get_skill(25)
    metachemistry = catalog.get_skill(55)

    assert hacker is not None
    assert hacker["structured_reference"]["kind"] == "hacking-programs"
    assert hacker["structured_reference"]["rows"][0]["name"] == "Carbonite"

    assert martial_arts is not None
    assert martial_arts["slug"] == "martial-arts"
    assert martial_arts["structured_reference"]["kind"] == "martial-arts"
    assert len(martial_arts["structured_reference"]["rows"]) == 5

    assert booty is not None
    assert booty["structured_reference"] == {
        "kind": "random-chart",
        "title": "Booty chart",
        "rows": [
            {"id": 1, "roll": "1-2", "result": "+1 ARM"},
            {"id": 3, "roll": "3-4", "result": "Light Flamethrower"},
        ],
    }

    assert metachemistry is not None
    assert metachemistry["structured_reference"]["title"] == "MetaChemistry chart"


def test_hacking_program_catalog_composes_army_profiles_with_rules_semantics(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)
    rules_path = tmp_path / "rules.db"
    root = Path(__file__).parents[1]
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = HackingProgramCatalog(database, RulesDatabase(rules_path))

    programs = catalog.list_programs()
    assert [program["slug"] for program in programs] == ["carbonite", "zero-pain"]
    carbonite = catalog.get_program("carbonite")
    assert carbonite is not None
    assert carbonite["source_extra_id"] == 13
    assert carbonite["rules"][0]["id"] == "hacking-program:carbonite"
    assert {
        relation["record"]["id"]
        for relation in carbonite["rules"][0]["display_relations"]
    } == {"state:immobilized-b"}

    zero_pain = catalog.get_program(2)
    assert zero_pain is not None
    assert zero_pain["slug"] == "zero-pain"
    assert zero_pain["devices"] == []
    assert zero_pain["source_extra_id"] == 287

    assert catalog.programs_for_equipment("hacking-device") == [
        {"id": "carbonite", "slug": "carbonite", "name": "Carbonite"}
    ]
    assert catalog.programs_for_equipment("hacking-device-plus") == [
        {"id": "carbonite", "slug": "carbonite", "name": "Carbonite"}
    ]


def test_hacking_program_catalog_remains_available_without_rules_database(
    tmp_path: Path,
) -> None:
    catalog = HackingProgramCatalog(_reference_database(tmp_path), None)
    carbonite = catalog.get_program("carbonite")
    assert carbonite is not None
    assert carbonite["description"] == "DA Ammo. State: IMM-B. Non-Lethal."
    assert "rules" not in carbonite
