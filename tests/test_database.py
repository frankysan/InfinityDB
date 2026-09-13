from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from infinity_army_data.normalize import main_army_id, normalize_master, validate_normalized
from infinity_army_data.weapon_categories import WEAPON_CATEGORIES, weapon_category
from infinity_army_data.weapon_profiles import weapon_profile_override
from infinity_db.database import Database, export_database
from infinity_db.database.repository import (
    canonical_skill_extra_name,
    canonical_skill_id,
    catalog_merge_key,
    logical_unit_groups,
    merged_catalog_name,
    merged_skill_name,
    skill_merge_key,
)
from infinity_db.database.schema import (
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    INDEXES,
    METADATA_TABLE,
    ROW_JSON,
    TABLES,
    quote,
)


@pytest.fixture
def normalized() -> dict:
    """Exercise the real normalizer, including every table it can generate."""
    reference = {"id": 1, "order": 2, "q": 1, "extra": [1], "future": {"enabled": True}}
    nested = {
        "skills": [reference],
        "equip": [reference],
        "weapons": [reference],
        "peripheral": [{"id": 1, "q": 1}],
        "chars": [1],
        "includes": [{"group": 1, "option": 1, "q": 1}],
        "orders": [{"type": "regular", "list": 1, "total": 1}],
    }
    group = {
        "id": 1,
        "category": 1,
        "isc": "Infantry",
        "profiles": [
            {
                "id": 1,
                "name": "Trooper",
                "type": 1,
                "move": [4, 4],
                "ava": "T",
                **nested,
            }
        ],
        "options": [{"id": 1, "name": "Rifle", "points": 10, "swc": "0.5", **nested}],
    }
    filters = {
        key: [{"id": 1, "name": key, "mercs": False, "future_field": {"value": [1, None]}}]
        for key in (
            "category",
            "chars",
            "type",
            "equip",
            "skills",
            "weapons",
            "ammunition",
            "extras",
        )
    }
    filters["peripheral"] = [{"id": 1, "name": "Drone"}]
    master = {
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyMetadata": {
            "sourceFile": "metadata.json",
            "sourceSha256": "test-metadata",
            "data": {"factions": []},
        },
        "armyLists": {
            "101": {
                "_meta": {"slug": "first_army", "kind": "faction"},
                "unitIds": [1, 3],
                "filters": filters,
                "reinforcements": 999,
                "resume": {"future": [True, "text"]},
                "fireteamChart": {
                    "spec": {"max": 2},
                    "teams": [
                        {
                            "name": "Team",
                            "type": ["Core"],
                            "units": [{"slug": "alpha", "name": "Alpha", "min": 1}],
                        }
                    ],
                },
                "relations": [
                    {
                        "min": 1,
                        "units": [
                            {
                                "unit": 1,
                                "profile": 1,
                                "depends": [{"unit": 9999, "options": [1], "future": "preserved"}],
                            }
                        ],
                    }
                ],
            },
            "201": {
                "_meta": {"slug": "second-army", "kind": "sectorial"},
                "unitIds": [1, 2],
                "filters": filters,
            },
            "301": {"_meta": {"slug": "empty_army"}, "unitIds": []},
        },
        "units": {
            "1": {
                "shared": {
                    "id": 1,
                    "name": "Álpha",
                    "slug": "alpha",
                    "canonical": 999,
                    "factions": [101],
                    "notes": {"language": "日本語"},
                    "options": [{"id": 1, "name": "Global", **nested}],
                },
                "byArmy": {
                    "101": {"profileGroups": [group], "filters": {"ava": "T"}},
                    "201": {"profileGroups": [copy.deepcopy(group)]},
                },
            },
            "2": {
                "shared": {"id": 2, "name": "Beta", "canonical": 101, "factions": [101]},
                "byArmy": {"201": {}},
            },
            "3": {
                "shared": {"id": 3, "name": "100%_Guard", "factions": [201]},
                "byArmy": {"101": {}},
            },
        },
    }
    master["units"]["1"]["byArmy"]["201"]["profileGroups"][0]["profiles"][0]["ava"] = 1
    data = normalize_master(master)
    validate_normalized(data)
    return data


def test_database_preserves_every_normalized_table_and_field(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    Database(path).validate()
    assert set(normalized["tables"]) == set(TABLES)
    connection = sqlite3.connect(path)
    try:
        for name, source_rows in normalized["tables"].items():
            stored_rows = connection.execute(
                f"SELECT {quote(ROW_JSON)} FROM {quote(name)} ORDER BY rowid"
            ).fetchall()
            assert [json.loads(row[0]) for row in stored_rows] == source_rows
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({quote(name)})")}
            assert {field for row in source_rows for field in row} <= columns
        assert connection.execute(
            "SELECT army_id, ava FROM profiles ORDER BY army_id"
        ).fetchall() == [(101, "T"), (201, 1)]
        assert json.loads(
            connection.execute("SELECT future_field FROM skills WHERE id = 1").fetchone()[0]
        ) == {"value": [1, None]}
        stored_warnings = connection.execute(
            f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = 'warnings'"
        ).fetchone()[0]
        assert json.loads(stored_warnings) == normalized["warnings"]
        compatibility = connection.execute(
            f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?",
            (DATABASE_COMPATIBILITY_KEY,),
        ).fetchone()[0]
        assert json.loads(compatibility) == DATABASE_COMPATIBILITY_VERSION
        indexes = {
            row[1]
            for table_name in TABLES
            for row in connection.execute(f"PRAGMA index_list({quote(table_name)})")
        }
        assert {index_name for index_name, _, _ in INDEXES} <= indexes
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError), connection:
            connection.execute("UPDATE profiles SET army_id = 404 WHERE army_id = 101")
    finally:
        connection.close()


def test_weapon_detail_includes_metadata_profiles(tmp_path: Path, normalized: dict) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["metadata_ammunitions"] = [{"id": 2, "name": "Normal"}]
    data["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 1,
            "type": "BS",
            "name": "Combi Rifle",
            "mode": "Standard",
            "ammunition": 2,
            "burst": "3",
            "damage": "7",
            "saving": "ARM",
            "savingNum": "1",
            "properties": ["Suppressive Fire"],
            "profile": "ARM=0, BTS=0, STR=1, S=1",
            "distance": {"short": {"max": 20, "mod": "+3"}, "med": {"max": 40, "mod": "0"}},
        }
    ]
    path = tmp_path / "army.sqlite3"
    export_database(data, path)

    detail = Database(path).get_catalog_item("weapons", 1)

    assert detail is not None
    assert detail["profiles"] == [
        {
            "id": 1,
            "name": "Combi Rifle",
            "mode": "Standard",
            "type": "BS",
            "ammunition": "Normal",
            "burst": "3",
            "damage": "7",
            "saving": "ARM",
            "saving_num": "1",
            "profile": "ARM=0, BTS=0, STR=1, S=1",
            "traits": ["Suppressive Fire"],
            "ranges": {"short": {"max": 20, "mod": "+3"}, "med": {"max": 40, "mod": "0"}},
        }
    ]
    assert detail["weapon_variants"] == [
        {
            "id": 1,
            "name": "weapons",
            "profiles": detail["profiles"],
        }
    ]


def test_armed_turret_uses_its_base_name_and_hides_placeholder_profile(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["weapons"].extend(
        [
            {
                "id": 209,
                "name": "Armed Turret (Combi R.)",
                "source_defined": True,
                "category": "Uncategorized",
            },
            {
                "id": 226,
                "name": "Armed Turret",
                "source_defined": True,
                "category": "Uncategorized",
            },
        ]
    )
    data["tables"]["metadata_weapons"] = [
        {"position": 1, "id": 226, "name": "Armed Turret", "burst": "-", "damage": "-"},
        {
            "position": 2,
            "id": 226,
            "name": "Armed Turret",
            "mode": "Combi Rifle",
            "burst": "3",
            "damage": "7",
        },
        {
            "position": 3,
            "id": 226,
            "name": "Armed Turret",
            "mode": "PARA CC Weapon",
            "burst": "1",
            "damage": "-",
        },
    ]
    path = tmp_path / "army.sqlite3"
    export_database(data, path)

    database = Database(path)

    assert [item for item in database.list_catalog_items("weapons") if item["id"] == 226] == [
        {
            "id": 226,
            "name": "Armed Turret",
            "category": "Uncategorized",
            "type": None,
            "ammunition": None,
            "properties": None,
            "use_count": 0,
        }
    ]
    detail = database.get_catalog_item("weapons", 226)
    assert detail is not None
    assert [(profile["name"], profile["mode"]) for profile in detail["profiles"]] == [
        ("Armed Turret", "Combi Rifle"),
    ]
    assert detail["special_profile"] == {
        "stats": [
            ["MOV", "--"],
            ["CC", "5"],
            ["BS", "10"],
            ["PH", "--"],
            ["WIP", "--"],
            ["ARM", "2"],
            ["BTS", "3"],
            ["STR", "1"],
            ["S", "2"],
        ],
        "equipment": ["360º Visor"],
        "skills": ["Total Reaction"],
        "cc_weapon": "PARA CC Weapon (-3)",
    }


def test_queries_use_actual_army_membership_and_unique_source_units(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)
    armies = database.list_armies()
    assert {row["id"]: row["unit_count"] for row in armies} == {101: 2, 201: 2, 301: 0}
    assert {row["id"]: row["name"] for row in armies}[101] == "First Army"
    assert database.list_units()["total"] == 3
    first_army = database.list_units(army_id=101)
    assert {unit["id"] for unit in first_army["items"]} == {1, 3}
    shared = next(unit for unit in first_army["items"] if unit["id"] == 1)
    assert shared["main_army_id"] is None
    assert shared["army_ids"] == [101, 201]
    assert shared["armies"] == [
        {"id": 101, "name": "First Army"},
        {"id": 201, "name": "Second Army"},
    ]
    assert database.list_units(army_id=301)["items"] == []
    assert database.list_units(army_id=999)["total"] == 0
    assert database.list_units(search="ÁLPHA")["items"][0]["id"] == 1
    assert database.list_units(search="alpha")["items"][0]["id"] == 1
    assert database.list_units(search="%_")["items"][0]["id"] == 3
    assert database.list_units(search="' OR 1 = 1 --")["total"] == 0
    assert database.list_units(search="missing")["items"] == []
    assert database.list_units(limit=1, offset=1) == {
        "items": [
            {
                "id": 1,
                "name": "Álpha",
                    "isc": None,
                    "slug": "alpha",
                    "main_army_id": None,
                    "main_army_name": None,
                    "source_ids": [1],
                "army_ids": [101, 201],
                "armies": [
                    {"id": 101, "name": "First Army"},
                    {"id": 201, "name": "Second Army"},
                ],
            }
        ],
        "total": 3,
        "limit": 1,
        "offset": 1,
    }


def test_list_skill_extras_returns_distinct_sorted_pairs(tmp_path: Path, normalized: dict) -> None:
    normalized["tables"]["extras"].extend(
        [
            {"id": 2, "name": "+5", "source_defined": True},
            {"id": 3, "name": "PS=5", "source_defined": True},
            {"id": 4, "name": "+5 CC", "source_defined": True},
            {"id": 5, "name": "-5", "source_defined": True},
        ]
    )
    profile_extra = normalized["tables"]["profile_skill_extras"][0]
    normalized["tables"]["profile_skill_extras"].append(
        {
            "occurrence_id": profile_extra["occurrence_id"],
            "position": 2,
            "extra_id": 2,
        }
    )
    normalized["tables"]["profile_skill_extras"].append(
        {
            "occurrence_id": profile_extra["occurrence_id"],
            "position": 3,
            "extra_id": 3,
        }
    )
    normalized["tables"]["profile_skill_extras"].append(
        {
            "occurrence_id": profile_extra["occurrence_id"],
            "position": 4,
            "extra_id": 4,
        }
    )
    normalized["tables"]["profile_skill_extras"].append(
        {
            "occurrence_id": profile_extra["occurrence_id"],
            "position": 5,
            "extra_id": 5,
        }
    )
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    assert Database(path).list_skill_extras() == [
        {
            "skill_id": 1,
            "skill_name": "skills",
            "extra_id": 2,
            "extra_name": "+5",
            "is_distance": True,
            "units": [{"id": 1, "name": "Álpha"}],
        },
        {
            "skill_id": 1,
            "skill_name": "skills",
            "extra_id": 5,
            "extra_name": "-5",
            "is_distance": True,
            "units": [{"id": 1, "name": "Álpha"}],
        },
    ]


def test_skill_extra_grouping_uses_skill_specific_sign_conventions() -> None:
    assert canonical_skill_extra_name("Super-Jump", "+7.5") == "7.5"
    assert canonical_skill_extra_name("Forward Deployment", "20") == "+20"
    assert canonical_skill_extra_name("Dodge", "+5") == "+5"
    assert canonical_skill_extra_name("Dodge", "-5") == "-5"


@pytest.mark.parametrize(
    ("skill_id", "expected"),
    [
        (19, 19),
        (20, 19),
        (21, 19),
        (22, 19),
        (23, 19),
        (69, 69),
        (70, 69),
        (201, 201),
        (278, 201),
        (279, 201),
        (240, 240),
        (274, 240),
        (24, 24),
    ],
)
def test_skill_variants_use_a_shared_catalog_identity(skill_id: int, expected: int) -> None:
    assert canonical_skill_id(skill_id) == expected


def test_skill_merge_key_collapses_any_numeric_name_variants() -> None:
    assert skill_merge_key("Strategos L1") == skill_merge_key("Strategos L2")
    assert skill_merge_key("BS=11") == skill_merge_key("BS=12")
    assert skill_merge_key("Martial Arts L3") == skill_merge_key("Martial Arts L5")
    assert skill_merge_key("Stealth") is None
    assert merged_skill_name("Strategos L1") == "Strategos"
    assert merged_skill_name("BS=12") == "BS"


def test_catalog_merge_key_treats_colon_suffixes_as_variants() -> None:
    assert catalog_merge_key("TinBot: Discover") == catalog_merge_key("TinBot: Firewall")
    assert merged_catalog_name("TinBot: Discover") == "TinBot"


@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Boarding Shotgun", "Shotguns"),
        ("MULTI Rifle", "Rifles"),
        ("Heavy Machine Gun", "Heavy Machine Guns"),
        ("Unknown Prototype", "Uncategorized"),
    ],
)
def test_weapon_categories_are_assigned_by_declarative_rules(name: str, category: str) -> None:
    assert weapon_category(name) == category
    assert category in WEAPON_CATEGORIES


def test_normalization_persists_weapon_categories(normalized: dict) -> None:
    assert all("category" in weapon for weapon in normalized["tables"]["weapons"])


@pytest.mark.parametrize(
    ("weapon_id", "category"),
    [
        (177, "CC Weapons"),
        (1, "Disposable Support Weapons"),
        (174, "Mines"),
        (18, "Uncategorized"),
    ],
)
def test_manual_weapon_category_overrides_take_precedence(weapon_id: int, category: str) -> None:
    assert weapon_category("Rifle", weapon_id) == category


@pytest.mark.parametrize("weapon_id", [62, 63, 196, 197, 199, 220])
def test_missing_mine_profiles_have_import_overrides(weapon_id: int) -> None:
    assert weapon_profile_override(weapon_id) == "ARM=0, BTS=0, STR=1, S=1"


def test_skill_catalog_and_details_merge_numeric_variants(tmp_path: Path, normalized: dict) -> None:
    normalized["tables"]["skills"].extend(
        [
            {"id": 69, "name": "Strategos L1", "source_defined": True},
            {"id": 70, "name": "Strategos L2", "source_defined": True},
        ]
    )
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    database = Database(path)
    strategos = [item for item in database.list_catalog_items("skills") if item["id"] == 69]
    assert strategos == [{"id": 69, "name": "Strategos", "wiki": None, "use_count": 0}]
    assert database.get_skill(70) == {
        "id": 69,
        "name": "Strategos",
        "wiki": None,
        "variants": [],
    }


@pytest.mark.parametrize("catalog", ["skills", "equipment", "weapons"])
def test_catalog_use_count_matches_detail_variant_unit_totals(
    tmp_path: Path, normalized: dict, catalog: str
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    database = Database(path)
    detail = database.get_skill(1) if catalog == "skills" else database.get_catalog_item(catalog, 1)
    assert detail is not None
    expected_count = sum(len(variant["units"]) for variant in detail["variants"])
    item = next(item for item in database.list_catalog_items(catalog) if item["id"] == 1)
    assert item["use_count"] == expected_count


@pytest.mark.parametrize("catalog", ["skills", "equipment", "weapons"])
def test_catalog_details_omit_variants_without_visible_units(
    tmp_path: Path, normalized: dict, catalog: str
) -> None:
    for membership in normalized["tables"]["army_units"]:
        if membership["unit_id"] == 1:
            membership["filters"] = {"mercs": True}
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    database = Database(path)
    detail = database.get_skill(1) if catalog == "skills" else database.get_catalog_item(catalog, 1)

    assert detail is not None
    assert detail["variants"] == []


def test_unit_details_flag_distance_skill_extras(tmp_path: Path, normalized: dict) -> None:
    normalized["tables"]["extras"].append({"id": 2, "name": "+5", "source_defined": True})
    normalized["tables"]["profile_skill_extras"][0]["extra_id"] = 2
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    details = Database(path).get_unit(1)
    assert details is not None
    assert details["armies"][0]["profiles"][0]["skills"][0]["extras"] == [
        {
            "id": 2,
            "name": "+5",
            "is_distance": True,
        }
    ]


def test_main_army_resolves_canonical_sectorials_to_whole_armies(normalized: dict) -> None:
    beta = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 2)
    assert beta["main_army_id"] == 101

    # A sectorial canonical ID resolves to its parent xx01 list, not the
    # sectorial itself.
    assert main_army_id(202, {101, 201, 202}) == 201
    assert main_army_id(1, {101, 201, 901}) == 901
    assert main_army_id(998, {901, 998}) == 901
    assert main_army_id(999, {101, 201}) is None


def test_duplicate_10000_id_family_is_one_logical_unit(tmp_path: Path, normalized: dict) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    normalized["tables"]["units"].append(
        {
            "id": 10_001,
            "name": original["name"],
            "isc": original["isc"],
            "canonical_faction_id": None,
            "source_defined": True,
        }
    )
    normalized["tables"]["army_units"].append({"army_id": 301, "unit_id": 10_001})
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    alpha = next(unit for unit in database.list_units()["items"] if unit["id"] == 1)
    assert alpha["main_army_id"] is None
    assert alpha["source_ids"] == [1, 10_001]
    assert alpha["army_ids"] == [101, 201, 301]
    assert database.list_units()["total"] == 3

    details = database.get_unit(10_001)
    assert details is not None
    assert details["id"] == 1
    assert details["main_army_id"] is None
    assert details["source_ids"] == [1, 10_001]
    assert {army["id"] for army in details["armies"]} == {101, 201, 301}


def test_explicit_unit_merge_alias_is_one_logical_unit() -> None:
    rows = [
        {"id": 1345, "name": "First record", "isc": "First ISC", "main_army_id": 101},
        {"id": 1875, "name": "Second record", "isc": "Second ISC", "main_army_id": 201},
        {"id": 11345, "name": "Third record", "isc": "Third ISC", "main_army_id": 301},
    ]
    memberships = {
        1345: [{"id": 101, "name": "First Army"}],
        1875: [{"id": 201, "name": "Second Army"}],
        11345: [{"id": 301, "name": "Third Army"}],
    }

    groups = logical_unit_groups(rows, memberships)

    assert len(groups) == 1
    assert groups[0]["id"] == 1345
    assert groups[0]["source_ids"] == [1345, 1875, 11345]
    assert list(groups[0]["armies"]) == [101, 201, 301]


def test_unit_300_merge_alias_is_one_logical_unit() -> None:
    rows = [
        {"id": 300, "name": "First record", "isc": "First ISC", "main_army_id": 101},
        {"id": 1690, "name": "Second record", "isc": "Second ISC", "main_army_id": 201},
        {"id": 10300, "name": "Third record", "isc": "Third ISC", "main_army_id": 301},
    ]
    memberships = {
        300: [{"id": 101, "name": "First Army"}],
        1690: [{"id": 201, "name": "Second Army"}],
        10300: [{"id": 301, "name": "Third Army"}],
    }

    groups = logical_unit_groups(rows, memberships)

    assert len(groups) == 1
    assert groups[0]["id"] == 300
    assert groups[0]["source_ids"] == [300, 1690, 10300]


def test_merged_source_profiles_do_not_repeat_identical_items(
    tmp_path: Path, normalized: dict
) -> None:
    """Merged IDs can share an army and local profile/option IDs."""
    duplicate_id = 10_001
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    duplicate = copy.deepcopy(original)
    duplicate["id"] = duplicate_id
    normalized["tables"]["units"].append(duplicate)

    for table in ("army_units", "profile_groups", "profiles", "loadout_options"):
        for row in list(normalized["tables"][table]):
            if row.get("unit_id") == 1 and row.get("army_id") == 101:
                duplicate = copy.deepcopy(row)
                duplicate["unit_id"] = duplicate_id
                if table == "profiles":
                    # An overlapping source may carry a conflicting AVA while
                    # omitting the profile's skills and equipment.
                    duplicate["ava"] = 1
                normalized["tables"][table].append(duplicate)

    for prefix in ("profile", "option"):
        if prefix == "profile":
            # The overlapping profile is deliberately sparse.
            continue
        occurrence_ids: dict[object, object] = {}
        for suffix in ("skills", "equipment", "weapons"):
            table = f"{prefix}_{suffix}"
            for row in list(normalized["tables"][table]):
                if row.get("unit_id") == 1 and row.get("army_id") == 101:
                    duplicate = copy.deepcopy(row)
                    duplicate["unit_id"] = duplicate_id
                    duplicate["occurrence_id"] = f"merged-{duplicate['occurrence_id']}"
                    occurrence_ids[row["occurrence_id"]] = duplicate["occurrence_id"]
                    normalized["tables"][table].append(duplicate)
        for suffix in ("skill_extras", "equipment_extras", "weapon_extras"):
            table = f"{prefix}_{suffix}"
            for row in list(normalized["tables"][table]):
                if row["occurrence_id"] in occurrence_ids:
                    duplicate = copy.deepcopy(row)
                    duplicate["occurrence_id"] = occurrence_ids[row["occurrence_id"]]
                    normalized["tables"][table].append(duplicate)

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    details = Database(path).get_unit(1)

    assert details is not None
    first_army = next(army for army in details["armies"] if army["id"] == 101)
    assert len(first_army["profiles"]) == 1
    assert [item["id"] for item in first_army["profiles"][0]["skills"]] == [1]
    assert [item["id"] for item in first_army["profiles"][0]["equipment"]] == [1]
    assert [item["id"] for item in first_army["profiles"][0]["weapons"]] == [1]
    assert [item["id"] for item in first_army["loadouts"][0]["skills"]] == [1]
    assert [item["id"] for item in first_army["loadouts"][0]["equipment"]] == [1]
    assert [item["id"] for item in first_army["loadouts"][0]["weapons"]] == [1]


def test_details_keep_normal_and_mercenary_army_occurrences_separate(
    tmp_path: Path, normalized: dict
) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    duplicate_id = 10_001
    duplicate = copy.deepcopy(original)
    duplicate.update(id=duplicate_id, canonical_faction_id=1)
    normalized["tables"]["units"].append(duplicate)
    normalized["tables"]["factions"].append(
        {
            "id": 1,
            "has_army_list": False,
            "canonical_reference_count": 1,
            "unit_membership_reference_count": 0,
        }
    )
    for table in ("army_units", "profile_groups", "profiles"):
        for row in list(normalized["tables"][table]):
            if row.get("unit_id") == 1 and row.get("army_id") == 101:
                duplicate = copy.deepcopy(row)
                duplicate["unit_id"] = duplicate_id
                normalized["tables"][table].append(duplicate)

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    details = Database(path).get_unit(1)

    assert details is not None
    first_army_occurrences = [army for army in details["armies"] if army["id"] == 101]
    assert [army["availability_flags"] for army in first_army_occurrences] == [[], ["mercs"]]
    assert all(len(army["profiles"]) == 1 for army in first_army_occurrences)


def test_reinforcement_only_variants_join_their_standard_unit() -> None:
    rows = [
        {
            "id": 265,
            "isc": "Wardrivers, Mercenary Hackers",
            "name": "WARDRIVERS",
            "main_army_id": 301,
        },
        {
            "id": 1635,
            "isc": "Reinf. Wardrivers, Mercenary Hackers",
            "name": "REINF: WARDRIVERS",
            "main_army_id": 401,
        },
        {
            "id": 1691,
            "isc": "Reinf. Wardrivers, Mercenary Hackers",
            "name": "REFUERZOS: WARDRIVERS",
            "main_army_id": 501,
        },
        {
            "id": 2691,
            "isc": "Reinf. Wardrivers, Mercenary Hackers",
            "name": "REINF: WARDRIVERS",
            "main_army_id": 901,
        },
    ]
    memberships = {
        265: [{"id": 301, "name": "Ariadna"}],
        1635: [{"id": 399, "name": "Reinforcements"}],
        1691: [{"id": 999, "name": "Reinforcements"}],
        2691: [{"id": 998, "name": "Reinforcements"}],
    }

    groups = logical_unit_groups(rows, memberships)

    assert len(groups) == 1
    assert groups[0]["id"] == 265
    assert groups[0]["main_army_id"] == 301
    assert groups[0]["source_ids"] == [265, 1635, 1691, 2691]
    assert list(groups[0]["armies"]) == [301, 399, 999]


def test_reinforcement_variant_matches_reordered_pluralized_identity() -> None:
    rows = [
        {
            "id": 35,
            "isc": "Armbots: Bulleteer",
            "name": "BULLETEER ARMBOTS",
            "main_army_id": 101,
        },
        {
            "id": 1649,
            "isc": "Reinf. Bulleteers Armbots",
            "name": "REINF: ARMBOTS BULLETEERS",
            "main_army_id": 101,
        },
    ]
    memberships = {
        35: [{"id": 101, "name": "PanOceania"}],
        1649: [{"id": 199, "name": "Reinforcements"}],
    }

    groups = logical_unit_groups(rows, memberships)

    assert len(groups) == 1
    assert groups[0]["id"] == 35
    assert groups[0]["source_ids"] == [35, 1649]
    assert list(groups[0]["armies"]) == [101, 199]


def test_reinforcement_variant_uses_display_name_when_isc_is_abbreviated() -> None:
    rows = [
        {
            "id": 1751,
            "isc": "Blade-Ops, Neoterran Unified Commando Regiment",
            "name": "BLADE-OPS, Neoterran Unified Commando Regiment",
            "main_army_id": 101,
        },
        {
            "id": 1642,
            "isc": "Reinf. Blade-Ops",
            "name": "REINF: BLADE-OPS, Unified Neoterran Commando Regiment",
            "main_army_id": 101,
        },
    ]
    memberships = {
        1751: [{"id": 101, "name": "PanOceania"}],
        1642: [{"id": 199, "name": "Reinforcements"}],
    }

    groups = logical_unit_groups(rows, memberships)

    assert len(groups) == 1
    assert groups[0]["id"] == 1751
    assert groups[0]["source_ids"] == [1751, 1642]


@pytest.mark.parametrize(
    ("standard", "reinforcement"),
    [
        (
            {
                "id": 1624,
                "isc": "Caskuda WCD Armored Jump Operator",
                "name": "CASKUDA",
                "main_army_id": 601,
            },
            {
                "id": 1618,
                "isc": "Reinf. Caskuda WCD Armoured Jump Operator",
                "name": "REINF. CASKUDA",
                "main_army_id": 601,
            },
        ),
        (
            {
                "id": 1610,
                "isc": "Ŝarko, Naval Reconaissance Special Unit",
                "name": "ŜARKO",
                "main_army_id": 1001,
            },
            {
                "id": 1700,
                "isc": "Reinf. Ŝarko, Naval Recon Special Unit",
                "name": "REINF: ŜARKO",
                "main_army_id": 1001,
            },
        ),
    ],
)
def test_reinforcement_variant_matches_known_spelling_aliases(
    standard: dict, reinforcement: dict
) -> None:
    memberships = {
        standard["id"]: [{"id": standard["main_army_id"], "name": "Standard Army"}],
        reinforcement["id"]: [{"id": 699, "name": "Reinforcements"}],
    }

    groups = logical_unit_groups([standard, reinforcement], memberships)

    assert len(groups) == 1
    assert groups[0]["id"] == standard["id"]
    assert groups[0]["source_ids"] == [standard["id"], reinforcement["id"]]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data["_meta"].update(format="not normalized"),
        lambda data: data["_meta"].update(formatVersion=2),
        lambda data: data.update(tables=[]),
        lambda data: data["tables"].update(units=["invalid"]),
        lambda data: data["tables"]["army_units"][0].update(unit_id=404),
        lambda data: data["tables"]["profile_skills"].append(data["tables"]["profile_skills"][0]),
        lambda data: data["tables"]["profiles"][0].update(profile_id=None),
        lambda data: data["tables"].update(unexpected_table=[]),
    ],
)
def test_invalid_import_keeps_existing_database(tmp_path: Path, normalized: dict, mutation) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    original = path.read_bytes()
    mutation(normalized)
    with pytest.raises(ValueError):
        export_database(normalized, path)
    assert path.read_bytes() == original
    assert sorted(item.name for item in tmp_path.iterdir()) == ["army.sqlite3"]


def test_empty_import_replaces_previous_database(tmp_path: Path, normalized: dict) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    empty = normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyMetadata": {
                "sourceFile": "metadata.json",
                "sourceSha256": "test-metadata",
                "data": {"factions": []},
            },
            "armyLists": {},
            "units": {},
        }
    )
    export_database(empty, path)
    database = Database(path)
    database.validate()
    assert database.list_armies() == []
    assert database.list_units() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_fallback_names_are_used_for_normalized_display_sorting_and_search(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["units"].extend(
        [
            {"id": 4, "name": None, "source_defined": True},
            {"id": 5, "name": "", "source_defined": True},
            {"id": 6, "name": "A-l.p/h+a", "source_defined": True},
            {"id": 7, "name": "Béta", "source_defined": True},
            {"id": 8, "name": "C.A.T.!", "source_defined": True},
            {"id": 237, "name": "S.A.S.", "source_defined": True},
            {"id": 1610, "name": "Ŝarko", "source_defined": True},
        ]
    )
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)
    assert [unit["name"] for unit in database.list_units()["items"]] == [
        "100%_Guard",
        "Álpha",
        "A-l.p/h+a",
        "Beta",
        "Béta",
        "C.A.T.!",
        "Ŝarko",
        "S.A.S.",
        "Unit 4",
        "Unit 5",
    ]
    assert database.list_units(search="sarko")["items"][0]["id"] == 1610
    assert database.list_units(search="sas")["items"][0]["id"] == 237
    assert database.list_units(search="UNIT 4")["items"] == [
        {
            "id": 4,
            "name": "Unit 4",
                "isc": None,
                "slug": None,
                "main_army_id": None,
                "main_army_name": None,
                "source_ids": [4],
            "army_ids": [],
            "armies": [],
        }
    ]
    assert database.list_units(search="unit", limit=1, offset=1) == {
        "items": [
            {
                "id": 5,
                "name": "Unit 5",
                    "isc": None,
                    "slug": None,
                    "main_army_id": None,
                    "main_army_name": None,
                    "source_ids": [5],
                "army_ids": [],
                "armies": [],
            }
        ],
        "total": 2,
        "limit": 1,
        "offset": 1,
    }


def test_reading_missing_or_unsupported_database_does_not_create_it(tmp_path: Path) -> None:
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(ValueError, match="does not exist"):
        Database(path).validate()
    assert not path.exists()
    connection = sqlite3.connect(path)
    connection.close()
    with pytest.raises(ValueError, match="Unsupported"):
        Database(path).validate()


def test_database_with_different_compatibility_revision_requires_rebuild(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            f"UPDATE {quote(METADATA_TABLE)} SET value = ? WHERE key = ?",
            (json.dumps(DATABASE_COMPATIBILITY_VERSION + 1), DATABASE_COMPATIBILITY_KEY),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="compatibility revision"):
        Database(path).validate()


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": 0},
        {"limit": 501},
        {"limit": True},
        {"offset": -1},
        {"offset": 0.5},
        {"army_id": "101"},
        {"search": None},
        {"army_id": 2**63},
        {"army_id": -(2**63) - 1},
        {"offset": 2**63},
    ],
)
def test_repository_rejects_invalid_query_arguments(tmp_path: Path, arguments: dict) -> None:
    with pytest.raises(ValueError, match=next(iter(arguments))):
        Database(tmp_path / "missing.sqlite3").list_units(**arguments)
