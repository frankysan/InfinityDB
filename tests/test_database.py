from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from infinity_army_data.normalize import main_army_id, normalize_master, validate_normalized
from infinity_army_data.weapon_categories import WEAPON_CATEGORIES, weapon_category
from infinity_army_data.weapon_config import (
    load_weapon_category_config,
    load_weapon_override_config,
    resolve_weapon_category_config,
    resolve_weapon_override_config,
)
from infinity_army_data.weapon_profiles import weapon_profile_override
from infinity_db.catalog_slugs import (
    attach_public_catalog_slug,
    enrich_nested_catalog_slugs,
)
from infinity_db.curated import load_curated_directory
from infinity_db.database import Database, export_database, raw_database_path
from infinity_db.database.importer import BATCH_SIZE, batched, reinforcement_unit_matches
from infinity_db.database.repository import (
    army_required_flags,
    availability_summary,
    catalog_merge_key,
    logical_source_loadout_merge_key,
    merged_catalog_name,
    merged_skill_name,
    minimal_availability_requirements,
    skill_merge_key,
    visible_armies_for_group,
)
from infinity_db.database.schema import (
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    INDEXES,
    METADATA_TABLE,
    PUBLISHED_DATABASE_TABLES,
    RAW_ROWS_TABLE,
    ROW_JSON,
    SOURCE_ONLY_TABLES,
    TABLES,
    create_indexes,
    create_schema,
    quote,
)
from infinity_db.domain_references import public_slug_for_reference
from infinity_db.domain_slugs import APPLICATION_SLUG_DOMAINS
from infinity_db.identities import (
    REINFORCEMENT_UNIT_MATCHES_KEY,
    load_identity_config,
    parse_identity_config,
)
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.skill_catalog import SkillCatalog
from infinity_db.trait_catalog import TraitCatalog


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


def test_database_splits_lossless_source_from_published_application_data(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    Database(path).validate()
    assert set(normalized["tables"]) == set(TABLES)

    archive = sqlite3.connect(raw_database_path(path))
    connection = sqlite3.connect(path)
    try:
        application_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert set(PUBLISHED_DATABASE_TABLES) <= application_tables
        assert SOURCE_ONLY_TABLES.isdisjoint(application_tables)

        for name, source_rows in normalized["tables"].items():
            stored_rows = archive.execute(
                f"SELECT {quote(ROW_JSON)} FROM {quote(RAW_ROWS_TABLE)} "
                "WHERE table_name = ? ORDER BY row_position",
                (name,),
            ).fetchall()
            assert [json.loads(row[0]) for row in stored_rows] == source_rows
            if name in PUBLISHED_DATABASE_TABLES:
                columns = {
                    row[1]
                    for row in connection.execute(
                        f"PRAGMA table_info({quote(name)})"
                    )
                }
                assert {field for row in source_rows for field in row} <= columns
                assert ROW_JSON not in columns

        assert json.loads(
            connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = 'published_tables'"
            ).fetchone()[0]
        ) == list(PUBLISHED_DATABASE_TABLES)
        assert json.loads(
            connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = 'source_only_tables'"
            ).fetchone()[0]
        ) == sorted(SOURCE_ONLY_TABLES)
        assert json.loads(
            archive.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = 'source_only_tables'"
            ).fetchone()[0]
        ) == sorted(SOURCE_ONLY_TABLES)

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
        reinforcement_matches = connection.execute(
            f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?",
            (REINFORCEMENT_UNIT_MATCHES_KEY,),
        ).fetchone()[0]
        assert json.loads(reinforcement_matches) == []

        assert connection.execute(
            "SELECT id, representative_unit_id FROM logical_units ORDER BY id"
        ).fetchall() == [(1, 1), (2, 2), (3, 3)]
        assert connection.execute(
            "SELECT source_unit_id, logical_unit_id FROM logical_unit_sources "
            "ORDER BY source_unit_id"
        ).fetchall() == [(1, 1), (2, 2), (3, 3)]
        assert connection.execute(
            "SELECT pp.id, pp.logical_unit_id, pp.name, ppo.ava "
            "FROM profile_payloads AS pp "
            "JOIN profile_payload_occurrences AS ppo ON ppo.profile_payload_id = pp.id "
            "ORDER BY ppo.ava"
        ).fetchall() == [(1, 1, "Trooper", 1), (1, 1, "Trooper", "T")]
        assert connection.execute(
            "SELECT army_id, unit_id, group_id, profile_id, profile_payload_id, ava, logo "
            "FROM profile_payload_occurrences ORDER BY army_id"
        ).fetchall() == [
            (101, 1, 1, 1, 1, "T", None),
            (201, 1, 1, 1, 1, 1, None),
        ]
        assert connection.execute("SELECT COUNT(*) FROM profile_payloads").fetchone()[0] == 1
        for table in (
            "profile_payload_characteristics",
            "profile_payload_skills",
            "profile_payload_skill_extras",
            "profile_payload_equipment",
            "profile_payload_equipment_extras",
            "profile_payload_weapons",
            "profile_payload_weapon_extras",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {quote(table)}"
            ).fetchone()[0] == 1
        source_skill_raw = next(
            row["raw"]
            for row in normalized["tables"]["profile_skills"]
            if row["army_id"] == 101
        )
        payload_skill_raw = connection.execute(
            "SELECT raw FROM profile_payload_skills"
        ).fetchone()[0]
        assert json.loads(payload_skill_raw) == source_skill_raw

        assert connection.execute("SELECT COUNT(*) FROM loadout_payloads").fetchone()[0] == 1
        assert connection.execute(
            "SELECT army_id, points, swc FROM loadout_payload_occurrences ORDER BY army_id"
        ).fetchall() == [(101, 10, "0.5"), (201, 10, "0.5")]
        for table in (
            "loadout_payload_characteristics",
            "loadout_payload_orders",
            "loadout_payload_skills",
            "loadout_payload_skill_extras",
            "loadout_payload_equipment",
            "loadout_payload_equipment_extras",
            "loadout_payload_weapons",
            "loadout_payload_weapon_extras",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {quote(table)}"
            ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM profile_occurrence_includes"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM loadout_occurrence_includes"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM unit_option_include_targets"
        ).fetchone()[0] == 2
        source_loadout_skill_raw = next(
            row["raw"]
            for row in normalized["tables"]["option_skills"]
            if row["army_id"] == 101
        )
        payload_loadout_skill_raw = connection.execute(
            "SELECT raw FROM loadout_payload_skills"
        ).fetchone()[0]
        assert json.loads(payload_loadout_skill_raw) == source_loadout_skill_raw

        indexes = {
            row[1]
            for table_name in PUBLISHED_DATABASE_TABLES
            for row in connection.execute(f"PRAGMA index_list({quote(table_name)})")
        }
        assert {
            index_name
            for index_name, table_name, _ in INDEXES
            if table_name in PUBLISHED_DATABASE_TABLES
        } <= indexes
        assert connection.execute("SELECT COUNT(*) FROM sqlite_stat1").fetchone()[0] > 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError), connection:
            connection.execute("UPDATE army_units SET army_id = 404 WHERE army_id = 101")
    finally:
        connection.close()
        archive.close()


def test_published_database_validates_without_raw_sibling(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    raw_database_path(path).unlink()

    Database(path).validate()
    assert Database(path).list_armies()


def _query_plan(connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...]) -> str:
    """Return the detail strings from SQLite's query planner."""
    return "\n".join(row[3] for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}", parameters))


@pytest.mark.parametrize(
    ("index_name", "table_name"),
    [
        (index_name, table_name)
        for index_name, table_name, _ in INDEXES
        if index_name.endswith("_unit") and table_name in PUBLISHED_DATABASE_TABLES
    ],
)
def test_unit_detail_queries_use_unit_indexes(
    tmp_path: Path, normalized: dict, index_name: str, table_name: str
) -> None:
    """Keep cold unit-detail lookups from degrading into table scans."""
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    connection = sqlite3.connect(path)
    try:
        plan = _query_plan(
            connection,
            f"SELECT 1 FROM {quote(table_name)} WHERE unit_id IN (?, ?)",
            (1, 3),
        )
        assert index_name in plan
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("index_name", "table_name"),
    [
        (index_name, table_name)
        for index_name, table_name, _ in INDEXES
        if index_name.endswith("_item") and table_name in PUBLISHED_DATABASE_TABLES
    ],
)
def test_catalog_detail_queries_use_item_indexes(
    tmp_path: Path, normalized: dict, index_name: str, table_name: str
) -> None:
    """Keep reverse catalog lookups from degrading into table scans."""
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    connection = sqlite3.connect(path)
    try:
        plan = _query_plan(
            connection,
            f"SELECT 1 FROM {quote(table_name)} WHERE item_id IN (?, ?)",
            (1, 2),
        )
        assert index_name in plan
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
    assert Database(path).list_traits() == [
        {
            "id": "suppressive-fire",
            "slug": "suppressive-fire",
            "name": "Suppressive Fire",
            "use_count": 1,
            "description": None,
        }
    ]
    trait = Database(path).get_trait("suppressive-fire")
    assert trait is not None
    assert trait["name"] == "Suppressive Fire"
    assert trait["variants"][0]["catalog"] == "weapons"
    assert trait["variants"][0]["item_name"] == "weapons"


def test_weapon_profile_preserves_only_raw_traits_before_application_composition(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 1,
            "type": "BS",
            "name": "Combi Rifle",
            "properties": [
                "Continous Damage",
                "Disposable (2)",
                "[PH=10]",
            ],
        }
    ]
    path = tmp_path / "army.sqlite3"
    export_database(data, path)

    detail = Database(path).get_catalog_item("weapons", 1)

    assert detail is not None
    profile = detail["profiles"][0]
    assert profile["traits"] == [
        "Continous Damage",
        "Disposable (2)",
        "[PH=10]",
    ]
    assert "trait_references" not in profile


def test_trait_catalog_resolves_curated_aliases_prefixes_and_citations(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 1,
            "type": "BS",
            "name": "Combi Rifle",
            "properties": [
                "Suppressive Fire",
                "Continous Damage",
                "Disposable (2)",
                "[PH=10]",
            ],
        }
    ]
    database_path = tmp_path / "army.sqlite3"
    export_database(data, database_path)

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_database = RulesDatabase(rules_path)
    rules_database.validate()
    catalog = TraitCatalog(Database(database_path), rules_database)

    assert catalog.reference("Suppressive Fire") == {
        "label": "Suppressive Fire",
        "name": "Suppressive Fire (SF)",
        "slug": "suppressive-fire",
    }
    assert catalog.reference("Continous Damage") == {
        "label": "Continous Damage",
        "name": "Continuous Damage",
        "slug": "continuous-damage",
    }
    assert catalog.reference("Disposable (2)") == {
        "label": "Disposable (2)",
        "name": "Disposable (X)",
        "slug": "disposable-x",
    }
    assert catalog.reference("[PH=10]") == {
        "label": "[PH=10]",
        "name": None,
        "slug": None,
    }

    traits = {item["id"]: item for item in catalog.list_traits()}
    assert traits["suppressive-fire"] == {
        "id": "suppressive-fire",
        "slug": "suppressive-fire",
        "name": "Suppressive Fire (SF)",
        "use_count": 1,
        "description": (
            "Allows the user to enter Suppressive Fire State and use its SF Mode profile."
        ),
    }
    detail = catalog.get_trait("continuous-damage")
    assert detail is not None
    assert detail["slug"] == "continuous-damage"
    assert detail["name"] == "Continuous Damage"
    assert detail["rules"][0]["id"] == "trait:continuous-damage"
    assert detail["rules"][0]["citations"][0]["heading"] == "Continuous Damage"


def test_trait_public_slug_is_owned_by_curated_id_not_display_name(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 1,
            "type": "BS",
            "name": "Combi Rifle",
            "properties": ["Continous Damage"],
        }
    ]
    database_path = tmp_path / "army.sqlite3"
    export_database(data, database_path)

    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    document = copy.deepcopy(documents[0][1])
    record = next(
        record
        for record in document["records"]
        if record["id"] == "trait:continuous-damage"
    )
    record["name"] = "Persistent Damage"
    rules_path = tmp_path / "rules.db"
    export_rules_database([(root / "curated.json", document)], rules_path)
    catalog = TraitCatalog(Database(database_path), RulesDatabase(rules_path))

    reference = catalog.reference("Continous Damage")
    assert reference == {
        "label": "Continous Damage",
        "name": "Persistent Damage",
        "slug": "continuous-damage",
    }
    detail = catalog.get_trait("continuous-damage")
    assert detail is not None
    assert detail["slug"] == "continuous-damage"
    assert detail["name"] == "Persistent Damage"


def test_uncurated_trait_reference_uses_catalog_slug_instead_of_guessing(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 1,
            "type": "BS",
            "name": "Combi Rifle",
            "properties": ["Uncurated Trait"],
        }
    ]
    database_path = tmp_path / "army.sqlite3"
    export_database(data, database_path)
    catalog = TraitCatalog(Database(database_path), None)

    assert catalog.reference("Uncurated Trait") == {
        "label": "Uncurated Trait",
        "name": "Uncurated Trait",
        "slug": "uncurated-trait",
    }
    assert catalog.reference("Not Present In Army Data") == {
        "label": "Not Present In Army Data",
        "name": "Not Present In Army Data",
        "slug": None,
    }


def test_trait_catalog_enriches_catalog_profiles_from_curated_rules(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 1,
            "type": "BS",
            "name": "Combi Rifle",
            "properties": ["Bioweapon (DA+Shock)", "Target (VITA)"],
        }
    ]
    database_path = tmp_path / "army.sqlite3"
    export_database(data, database_path)
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = TraitCatalog(Database(database_path), RulesDatabase(rules_path))

    item = Database(database_path).get_catalog_item("weapons", 1)
    assert item is not None
    enriched = catalog.enrich_catalog_item(item)
    assert enriched["profiles"][0]["trait_references"] == [
        {
            "label": "Bioweapon (DA+Shock)",
            "name": "BioWeapon",
            "slug": "bioweapon",
        },
        {
            "label": "Target (VITA)",
            "name": "Target (Attribute)",
            "slug": "target-attribute",
        },
    ]


def test_armed_turret_uses_its_base_name_with_visible_metadata_profile(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["weapons"].extend(
        [
            {
                "id": source_id,
                "name": name,
                "source_defined": True,
                "category": "Uncategorized",
            }
            for source_id, name in (
                (209, "Armed Turret (Combi R.)"),
                (215, "Armed Turret (Marksman R.)"),
                (219, "Armed Turret (AP Rifle)"),
                (222, "Armed Turret (Rifle)"),
                (226, "Armed Turret"),
                (228, "Armed Turret (E/Mitter)"),
            )
        ]
    )
    data["tables"]["metadata_weapons"] = [
        {
            "position": 2,
            "id": 226,
            "name": "Armed Turret",
            "mode": "Combi Rifle",
            "burst": "3",
            "damage": "7",
        }
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
            "source_ids": [209, 215, 219, 222, 226, 228],
            "use_count": 0,
        }
    ]
    detail = database.get_catalog_item("weapons", 226)
    assert detail is not None
    assert [(profile["name"], profile["mode"]) for profile in detail["profiles"]] == [
        ("Armed Turret", "Combi Rifle"),
    ]
    assert "special_profile" not in detail


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
    first_army_by_slug = database.list_units(army_id="first-army")
    assert {unit["id"] for unit in first_army_by_slug["items"]} == {1, 3}
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
                "main_faction": None,
                "display_army_id": None,
                "display_army_name": None,
                "display_faction": None,
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
        "availability": {
            "shown": 3,
            "available": 3,
            "filtered": 0,
            "categories": {
                "standard": {"shown": 3, "filtered": 0},
                "mercs": {"shown": 0, "filtered": 0},
                "specops": {"shown": 0, "filtered": 0},
                "teamops": {"shown": 0, "filtered": 0},
                "reinforcement": {"shown": 0, "filtered": 0},
            },
        },
    }


def test_army_unit_count_uses_distinct_logical_units(
    tmp_path: Path, normalized: dict
) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    original["source_role"] = "standard"
    duplicate_id = 10_001
    duplicate = copy.deepcopy(original)
    duplicate["id"] = duplicate_id
    duplicate["source_role"] = "standard"
    normalized["tables"]["units"].append(duplicate)
    normalized["genericUnitMatches"] = [
        {
            "sourceUnitId": duplicate_id,
            "representativeUnitId": 1,
            "method": "generic_duplicate_key",
        }
    ]
    for row in list(normalized["tables"]["army_units"]):
        if row.get("unit_id") == 1 and row.get("army_id") == 101:
            occurrence = copy.deepcopy(row)
            occurrence["unit_id"] = duplicate_id
            normalized["tables"]["army_units"].append(occurrence)

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    army = next(item for item in database.list_armies() if item["id"] == 101)
    assert army["unit_count"] == database.list_units(army_id=101)["total"] == 2


def test_list_skill_extras_returns_distinct_sorted_pairs(tmp_path: Path, normalized: dict) -> None:
    normalized["tables"]["extras"].extend(
        [
            {"id": 2, "name": "+5", "type": "DISTANCE", "source_defined": True},
            {"id": 3, "name": "PS=5", "type": "TEXT", "source_defined": True},
            {"id": 4, "name": "+5 CC", "type": "TEXT", "source_defined": True},
            {"id": 5, "name": "-5", "type": "DISTANCE", "source_defined": True},
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
    source_names = {
        177: "Trench-Hammer",
        1: "Akrylat-Kanone",
        174: "Cybermine",
        18: "Chain Rifle",
    }
    config = resolve_weapon_category_config(
        load_weapon_category_config(), source_names, allow_missing=True
    )
    assert weapon_category("Rifle", weapon_id, config=config) == category


@pytest.mark.parametrize(
    ("weapon_id", "source_name"),
    [
        (62, "Monofilament Mine"),
        (63, "Viral Mine"),
        (196, "Shock Mine"),
        (197, "E/M Mine"),
        (199, "AP Mine"),
        (220, "PARA Mine"),
    ],
)
def test_missing_mine_profiles_have_import_overrides(
    weapon_id: int, source_name: str
) -> None:
    config = resolve_weapon_override_config(
        load_weapon_override_config(), {weapon_id: source_name}, allow_missing=True
    )
    assert (
        weapon_profile_override(weapon_id, config=config)
        == "ARM=0, BTS=0, STR=1, S=1"
    )


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
    assert strategos == [
        {
            "id": 69,
            "name": "Strategos",
            "wiki": None,
            "source_ids": [69, 70],
            "use_count": 0,
        }
    ]
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
def test_catalog_details_include_optional_units_for_client_filtering(
    tmp_path: Path, normalized: dict, catalog: str
) -> None:
    for membership in normalized["tables"]["army_units"]:
        if membership["unit_id"] == 1:
            membership["filters"] = {"teamops": True}
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    database = Database(path)
    detail = database.get_skill(1) if catalog == "skills" else database.get_catalog_item(catalog, 1)

    assert detail is not None
    assert detail["variants"]
    assert detail["variants"][0]["units"][0]["id"] == 1


def test_unit_details_expose_backend_profile_display_name(
    tmp_path: Path, normalized: dict
) -> None:
    for profile in normalized["tables"]["profiles"]:
        if profile["unit_id"] == 1:
            profile["name"] = "REFUERZOS: Trooper"
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    details = Database(path).get_unit(1)
    assert details is not None
    for army in details["armies"]:
        profile = army["profiles"][0]
        assert profile["name"] == "REFUERZOS: Trooper"
        assert profile["display_name"] == "Trooper"
        assert profile["profile_identity"] == "trooper"


def test_unit_details_flag_distance_skill_extras(tmp_path: Path, normalized: dict) -> None:
    normalized["tables"]["extras"].append(
        {"id": 2, "name": "+5", "type": "DISTANCE", "source_defined": True}
    )
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


def test_unit_details_do_not_infer_distance_from_text_extras(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["extras"].append(
        {"id": 2, "name": "+5 CC", "type": "TEXT", "source_defined": True}
    )
    normalized["tables"]["profile_skill_extras"][0]["extra_id"] = 2
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    details = Database(path).get_unit(1)
    assert details is not None
    assert details["armies"][0]["profiles"][0]["skills"][0]["extras"] == [
        {"id": 2, "name": "+5 CC"}
    ]

def test_main_army_prefers_metadata_parent_and_keeps_legacy_fallback(normalized: dict) -> None:
    beta = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 2)
    assert beta["main_army_id"] == 101

    faction_ids = {101, 201, 202, 777, 901}
    assert main_army_id(202, faction_ids, faction_parents={202: 777}) == 777
    assert main_army_id(202, faction_ids, faction_parents={202: None}) is None
    assert main_army_id(202, faction_ids) == 201
    assert main_army_id(1, {101, 201, 901}) is None
    assert main_army_id(50, {101, 901}, {50: 901}, {50: 101}) == 901
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


def test_database_uses_persisted_generic_mapping(tmp_path: Path, normalized: dict) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    original["source_role"] = "standard"
    normalized["tables"]["units"].append(
        {
            "id": 10_001,
            "name": "Different source label",
            "isc": "Different source ISC",
            "isc_abbr": "DSI",
            "slug": "different-source-label",
            "notes": "Source-specific note",
            "spectables": {"source": ["context"]},
            "canonical_faction_id": None,
            "main_army_id": None,
            "source_defined": True,
            "source_role": "standard",
        }
    )
    normalized["tables"]["army_units"].append(
        {"army_id": 301, "unit_id": 10_001, "availability_kind": "standard"}
    )
    normalized["genericUnitMatches"] = [
        {
            "sourceUnitId": 10_001,
            "representativeUnitId": 1,
            "method": "generic_duplicate_key",
        }
    ]
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    alpha = next(unit for unit in database.list_units()["items"] if unit["id"] == 1)
    assert alpha["source_ids"] == [1, 10_001]
    assert alpha["army_ids"] == [101, 201, 301]
    assert database.list_units()["total"] == 3

    details = database.get_unit(10_001)
    assert details is not None
    assert details["id"] == 1
    assert details["source_ids"] == [1, 10_001]

    connection = sqlite3.connect(path)
    try:
        representative = connection.execute(
            "SELECT name, isc, isc_abbr, slug, canonical_faction_id, main_army_id, "
            "display_army_id FROM units WHERE id = 1"
        ).fetchone()
        canonical = connection.execute(
            "SELECT name, isc, isc_abbr, slug, canonical_faction_id, main_army_id, "
            "display_army_id FROM logical_units WHERE id = 1"
        ).fetchone()
        assert canonical == representative
        assert connection.execute(
            "SELECT source_unit_id, field, value FROM logical_unit_aliases "
            "WHERE logical_unit_id = 1 ORDER BY source_unit_id, field"
        ).fetchall() == [
            (10_001, "isc", "Different source ISC"),
            (10_001, "isc_abbr", "DSI"),
            (10_001, "name", "Different source label"),
            (10_001, "slug", "different-source-label"),
        ]
        assert connection.execute(
            "SELECT note FROM logical_unit_notes "
            "WHERE logical_unit_id = 1 AND source_unit_id = 10001"
        ).fetchone() == ("Source-specific note",)
        stored_spectables = connection.execute(
            "SELECT spectables FROM logical_unit_spectables "
            "WHERE logical_unit_id = 1 AND source_unit_id = 10001"
        ).fetchone()[0]
        assert json.loads(stored_spectables) == {"source": ["context"]}
    finally:
        connection.close()


def test_unit_display_and_alias_reads_use_canonical_logical_unit_layer(
    tmp_path: Path, normalized: dict
) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    original["source_role"] = "standard"
    normalized["tables"]["units"].append(
        {
            "id": 10_001,
            "name": "Alternate source label",
            "isc": "Alternate source ISC",
            "isc_abbr": "ASI",
            "slug": "alternate-source-label",
            "canonical_faction_id": None,
            "main_army_id": None,
            "source_defined": True,
            "source_role": "standard",
        }
    )
    normalized["tables"]["army_units"].append(
        {"army_id": 301, "unit_id": 10_001, "availability_kind": "standard"}
    )
    normalized["genericUnitMatches"] = [
        {
            "sourceUnitId": 10_001,
            "representativeUnitId": 1,
            "method": "generic_duplicate_key",
        }
    ]
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    database = Database(path)
    baseline_page = database.list_units(limit=500)
    baseline_detail = database.get_unit(10_001)
    baseline_alias_search = database.list_units(search="Alternate source label")
    assert [item["id"] for item in baseline_alias_search["items"]] == [1]

    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE units SET name = 'BROKEN NAME', isc = 'BROKEN ISC', "
            "isc_abbr = 'BAD', slug = 'broken-slug', notes = 'BROKEN NOTE', "
            "main_army_id = NULL, display_army_id = NULL "
            "WHERE id IN (1, 10001)"
        )
        connection.commit()
    finally:
        connection.close()

    rebuilt = Database(path)
    assert rebuilt.list_units(limit=500) == baseline_page
    assert rebuilt.get_unit(10_001) == baseline_detail
    assert rebuilt.list_units(search="Alternate source label") == baseline_alias_search
    assert rebuilt.list_units(search="BROKEN NAME")["items"] == []


def test_logical_unit_aliases_preserve_source_fallback_name_search(
    tmp_path: Path, normalized: dict
) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    original["source_role"] = "standard"
    normalized["tables"]["units"].append(
        {
            "id": 10_001,
            "name": None,
            "isc": original["isc"],
            "isc_abbr": original.get("isc_abbr"),
            "slug": original.get("slug"),
            "canonical_faction_id": None,
            "main_army_id": None,
            "source_defined": True,
            "source_role": "standard",
        }
    )
    normalized["tables"]["army_units"].append(
        {"army_id": 301, "unit_id": 10_001, "availability_kind": "standard"}
    )
    normalized["genericUnitMatches"] = [
        {
            "sourceUnitId": 10_001,
            "representativeUnitId": 1,
            "method": "generic_duplicate_key",
        }
    ]
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)

    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT field, value FROM logical_unit_aliases "
            "WHERE logical_unit_id = 1 AND source_unit_id = 10001 ORDER BY field"
        ).fetchall() == [("name", "Unit 10001")]
    finally:
        connection.close()

    result = Database(path).list_units(search="Unit 10001")
    assert [item["id"] for item in result["items"]] == [1]


def test_database_validation_rejects_missing_logical_unit_alias(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    original = next(unit for unit in data["tables"]["units"] if unit["id"] == 1)
    original["source_role"] = "standard"
    data["tables"]["units"].append(
        {
            "id": 10_001,
            "name": "Alternate label",
            "isc": original["isc"],
            "canonical_faction_id": None,
            "main_army_id": None,
            "source_defined": True,
            "source_role": "standard",
        }
    )
    data["tables"]["army_units"].append(
        {"army_id": 301, "unit_id": 10_001, "availability_kind": "standard"}
    )
    data["genericUnitMatches"] = [
        {
            "sourceUnitId": 10_001,
            "representativeUnitId": 1,
            "method": "generic_duplicate_key",
        }
    ]
    path = tmp_path / "army.sqlite3"
    export_database(data, path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "DELETE FROM logical_unit_aliases "
            "WHERE logical_unit_id = 1 AND source_unit_id = 10001 AND field = 'name'"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="canonical logical-unit payloads"):
        Database(path).validate()


def test_database_empty_generic_audit_prevents_legacy_grouping(
    tmp_path: Path, normalized: dict
) -> None:
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
    normalized["genericUnitMatches"] = []
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    assert database.list_units()["total"] == 4
    duplicate = database.get_unit(10_001)
    assert duplicate is not None
    assert duplicate["id"] == 10_001
    assert duplicate["source_ids"] == [10_001]
    assert database.application_slug("units", 1) is None
    assert database.application_slug("units", 10_001) is None


def test_database_uses_persisted_mercenary_mapping_for_logical_unit(
    tmp_path: Path, normalized: dict
) -> None:
    for unit in normalized["tables"]["units"]:
        if unit["source_defined"]:
            unit["source_role"] = "standard"

    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    mercenary_id = 10_001
    normalized["tables"]["units"].append(
        {
            "id": mercenary_id,
            "name": "DIFFERENT SOURCE LABEL",
            "isc": "Different Source ISC",
            "slug": "merc-different-source-label",
            "canonical_faction_id": 1,
            "main_army_id": original["main_army_id"],
            "source_defined": True,
            "source_role": "mercenary_variant",
        }
    )
    if not any(faction["id"] == 1 for faction in normalized["tables"]["factions"]):
        normalized["tables"]["factions"].append(
            {
                "id": 1,
                "has_army_list": False,
                "canonical_reference_count": 1,
                "unit_membership_reference_count": 0,
            }
        )
    normalized["tables"]["army_units"].append(
        {
            "army_id": 301,
            "unit_id": mercenary_id,
            "availability_kind": "mercenary",
        }
    )
    normalized["mercenaryUnitMatches"] = [
        {
            "mercenaryUnitId": mercenary_id,
            "standardUnitId": 1,
            "method": "generic_duplicate_key",
        }
    ]
    normalized["unmatchedMercenaryUnitIds"] = []

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    alpha = next(unit for unit in database.list_units(mercs=True)["items"] if unit["id"] == 1)
    assert alpha["source_ids"] == [1, mercenary_id]
    assert 301 in alpha["army_ids"]
    details = database.get_unit(mercenary_id)
    assert details is not None
    assert details["id"] == 1
    assert details["source_ids"] == [1, mercenary_id]


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
                if table == "profiles":
                    row["ava"] = 2
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
    assert first_army["profiles"][0]["ava"] == 1
    assert [item["id"] for item in first_army["profiles"][0]["skills"]] == [1]
    assert [item["id"] for item in first_army["profiles"][0]["equipment"]] == [1]
    assert [item["id"] for item in first_army["profiles"][0]["weapons"]] == [1]
    assert [item["id"] for item in first_army["loadouts"][0]["skills"]] == [1]
    assert [item["id"] for item in first_army["loadouts"][0]["equipment"]] == [1]
    assert [item["id"] for item in first_army["loadouts"][0]["weapons"]] == [1]


def test_logical_source_profile_merge_keeps_scalar_variants_separate(
    tmp_path: Path, normalized: dict
) -> None:
    duplicate_id = 10_001
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    duplicate = copy.deepcopy(original)
    duplicate["id"] = duplicate_id
    normalized["tables"]["units"].append(duplicate)

    for table in ("army_units", "profile_groups", "profiles"):
        for row in list(normalized["tables"][table]):
            if row.get("unit_id") == 1 and row.get("army_id") == 101:
                if table == "profiles":
                    row["wip"] = 13
                duplicate = copy.deepcopy(row)
                duplicate["unit_id"] = duplicate_id
                if table == "profiles":
                    duplicate["wip"] = 14
                normalized["tables"][table].append(duplicate)

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    details = Database(path).get_unit(1)

    assert details is not None
    first_army = next(army for army in details["armies"] if army["id"] == 101)
    assert sorted(profile["wip"] for profile in first_army["profiles"]) == [13, 14]


def test_logical_source_loadout_merge_key_preserves_occurrence_identity() -> None:
    occurrence_key = (101, ("mercs",))
    loadout = {
        "group_id": 1,
        "option_id": 1,
        "name": "Loadout",
        "points": 10,
        "swc": "0.5",
        "minis": 1,
        "disabled": 0,
    }

    baseline = logical_source_loadout_merge_key(occurrence_key, loadout)
    assert logical_source_loadout_merge_key(occurrence_key, loadout) == baseline
    assert logical_source_loadout_merge_key(
        occurrence_key, {**loadout, "option_id": 2}
    ) != baseline
    assert logical_source_loadout_merge_key(
        occurrence_key, {**loadout, "points": 11}
    ) != baseline
    assert logical_source_loadout_merge_key(
        (101, ("reinforcement",)), loadout
    ) != baseline


def test_details_keep_normal_and_mercenary_army_occurrences_separate(
    tmp_path: Path, normalized: dict
) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    duplicate_id = 10_001
    duplicate = copy.deepcopy(original)
    # Keep the same non-mercenary canonical faction deliberately: the explicit
    # army occurrence provenance, not canonical faction 1, must mark this source
    # record as optional mercenary availability.
    duplicate.update(id=duplicate_id)
    normalized["tables"]["units"].append(duplicate)
    for table in ("army_units", "profile_groups", "profiles"):
        for row in list(normalized["tables"][table]):
            if row.get("unit_id") == 1 and row.get("army_id") == 101:
                if table == "army_units":
                    row["availability_kind"] = "standard"
                duplicate = copy.deepcopy(row)
                duplicate["unit_id"] = duplicate_id
                if table == "army_units":
                    duplicate["availability_kind"] = "mercenary"
                normalized["tables"][table].append(duplicate)

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    details = Database(path).get_unit(1)

    assert details is not None
    first_army_occurrences = [army for army in details["armies"] if army["id"] == 101]
    assert [army["availability_flags"] for army in first_army_occurrences] == [[], ["mercs"]]
    assert all(len(army["profiles"]) == 1 for army in first_army_occurrences)


def test_minimal_availability_requirements_drop_redundant_optional_paths() -> None:
    group = {
        "names": ["Example Unit"],
        "slug": "example-unit",
        "armies": {101: {}},
        "army_occurrences": [
            {
                "id": 101,
                "source_id": 1,
                "availability_kind": "standard",
                "role": "main",
                "kind": "army",
                "filters": {},
            },
            {
                "id": 101,
                "source_id": 2,
                "availability_kind": "standard",
                "role": "main",
                "kind": "army",
                "filters": {"reinforcement": True},
            },
        ],
    }

    requirements = minimal_availability_requirements(
        group,
        {1: 101, 2: 101},
        {1: {101}, 2: {101}},
        101,
    )

    assert requirements == (frozenset(),)


def test_availability_summary_uses_unique_units_and_reports_overlapping_categories() -> None:
    requirements = [
        (frozenset(),),
        (frozenset({"specops"}),),
        (frozenset({"mercs"}), frozenset({"reinforcement"})),
        (frozenset({"mercs", "reinforcement"}),),
    ]

    summary = availability_summary(requirements, {"specops"})

    assert summary == {
        "shown": 2,
        "available": 4,
        "filtered": 2,
        "categories": {
            "standard": {"shown": 1, "filtered": 0},
            "mercs": {"shown": 0, "filtered": 2},
            "specops": {"shown": 1, "filtered": 0},
            "teamops": {"shown": 0, "filtered": 0},
            "reinforcement": {"shown": 0, "filtered": 2},
        },
    }


def test_reinforcement_classification_uses_application_role_with_source_fallback() -> None:
    group = {
        "canonical_faction_id": 301,
        "declared_faction_ids": {399},
        "names": ["TEST"],
        "slug": "test",
    }

    assert army_required_flags({"id": 399, "role": "main", "kind": "army"}, group) == set()
    assert army_required_flags(
        {"id": 350, "role": "reinforcement", "kind": "army"},
        group,
    ) == {"reinforcement"}
    assert army_required_flags(
        {"id": 350, "role": "unknown", "kind": "reinforcement"},
        group,
    ) == {"reinforcement"}


def test_explicit_availability_kind_is_authoritative_for_mercenary_flags() -> None:
    group = {
        "canonical_faction_id": 1,
        "declared_faction_ids": set(),
        "names": ["TEST"],
        "slug": "test",
    }

    assert army_required_flags(
        {"id": 101, "availability_kind": "standard"},
        group,
    ) == set()
    assert army_required_flags(
        {"id": 101, "availability_kind": "mercenary"},
        {**group, "canonical_faction_id": 301, "declared_faction_ids": {101}},
    ) == {"mercs"}


def test_list_availability_uses_source_specific_occurrences() -> None:
    group = {
        "canonical_faction_id": 301,
        "declared_faction_ids": {303},
        "names": ["WOLFGANG"],
        "slug": "wolfgang",
        "army_occurrences": [
            {
                "source_id": 1555,
                "id": 303,
                "name": "Kosmoflot",
                "availability_kind": "standard",
            },
            {
                "source_id": 11555,
                "id": 101,
                "name": "PanOceania",
                "availability_kind": "mercenary",
            },
            {
                "source_id": 1634,
                "id": 350,
                "name": "Reinforcements",
                "kind": "reinforcement",
                "availability_kind": "standard",
            },
        ],
    }
    # Deliberately contradict the old canonical/faction heuristic: explicit
    # occurrence provenance must determine mercenary visibility when present.
    canonical_factions = {1555: 1, 11555: 301, 1634: 1}
    normal_armies = {1555: set(), 11555: {101}, 1634: set()}

    assert set(visible_armies_for_group(group, set(), canonical_factions, normal_armies)) == {303}
    assert set(visible_armies_for_group(group, {"mercs"}, canonical_factions, normal_armies)) == {
        101,
        303,
    }
    assert set(
        visible_armies_for_group(group, {"reinforcement"}, canonical_factions, normal_armies)
    ) == {303, 350}


def test_database_creation_audits_reinforcement_identity() -> None:
    data = {
        "tables": {
            "units": [
                {
                    "id": 35,
                    "isc": "Armbots: Bulleteer",
                    "name": "BULLETEER ARMBOTS",
                    "source_defined": True,
                    "source_role": "standard",
                },
                {
                    "id": 1649,
                    "isc": "Reinf. Bulleteers Armbots",
                    "name": "REINF: ARMBOTS BULLETEERS",
                    "source_defined": True,
                    "source_role": "standard",
                },
                {
                    "id": 2649,
                    "isc": "Reinf. Bulleteers Armbots",
                    "name": "REFUERZOS: ARMBOTS BULLETEERS",
                    "source_defined": True,
                    "source_role": "standard",
                },
            ],
            "army_lists": [
                {"id": 101, "kind": "faction"},
                {"id": 199, "kind": "reinforcement"},
            ],
            "army_units": [
                {"army_id": 101, "unit_id": 35},
                {"army_id": 199, "unit_id": 1649},
                {"army_id": 199, "unit_id": 2649},
            ],
        }
    }

    assert reinforcement_unit_matches(data, load_identity_config()) == {1649: 35, 2649: 35}


def test_database_uses_exported_reinforcement_mapping(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["factions"].append(
        {
            "id": 199,
            "has_army_list": True,
            "canonical_reference_count": 0,
            "unit_membership_reference_count": 0,
        }
    )
    normalized["tables"]["army_lists"].append(
        {
            "id": 199,
            "name": "Reinforcements",
            "slug": "reinf",
            "kind": "reinforcement",
        }
    )
    normalized["tables"]["units"].append(
        {
            "id": 1649,
            "name": "REINF: Álpha",
            "isc": "Reinf. Álpha",
            "canonical_faction_id": None,
            "main_army_id": None,
            "source_defined": True,
        }
    )
    normalized["tables"]["army_units"].append({"army_id": 199, "unit_id": 1649})

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    connection = sqlite3.connect(path)
    try:
        stored = connection.execute(
            f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?",
            (REINFORCEMENT_UNIT_MATCHES_KEY,),
        ).fetchone()[0]
        assert json.loads(stored) == [
            {
                "reinforcementUnitId": 1649,
                "standardUnitId": 1,
                "method": "normalized_unit_identity",
            }
        ]
        connection.execute(
            "UPDATE units SET name = ?, isc = ? WHERE id = 1649",
            ("DIFFERENT AFTER EXPORT", "Different after export"),
        )
        connection.commit()
    finally:
        connection.close()

    details = Database(path).get_unit(1649)
    assert details is not None
    assert details["id"] == 1
    assert details["source_ids"] == [1, 1649]


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
    archive_path = raw_database_path(path)
    original_archive = archive_path.read_bytes()
    mutation(normalized)
    with pytest.raises(ValueError):
        export_database(normalized, path)
    assert path.read_bytes() == original
    assert archive_path.read_bytes() == original_archive
    assert sorted(item.name for item in tmp_path.iterdir()) == ["army.raw.sqlite3", "army.sqlite3"]


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
    assert database.list_units() == {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0,
        "availability": {
            "shown": 0,
            "available": 0,
            "filtered": 0,
            "categories": {
                "standard": {"shown": 0, "filtered": 0},
                "mercs": {"shown": 0, "filtered": 0},
                "specops": {"shown": 0, "filtered": 0},
                "teamops": {"shown": 0, "filtered": 0},
                "reinforcement": {"shown": 0, "filtered": 0},
            },
        },
    }


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
    assert database.application_slug("units", 4) is None
    assert database.application_slug("units", 5) is None
    assert database.list_units(search="UNIT 4")["items"] == [
        {
            "id": 4,
            "name": "Unit 4",
            "isc": None,
            "slug": None,
            "main_army_id": None,
            "main_army_name": None,
            "main_faction": None,
            "display_army_id": None,
            "display_army_name": None,
            "display_faction": None,
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
                "main_faction": None,
                "display_army_id": None,
                "display_army_name": None,
                "display_faction": None,
                "source_ids": [5],
                "army_ids": [],
                "armies": [],
            }
        ],
        "total": 2,
        "limit": 1,
        "offset": 1,
        "availability": {
            "shown": 2,
            "available": 2,
            "filtered": 0,
            "categories": {
                "standard": {"shown": 2, "filtered": 0},
                "mercs": {"shown": 0, "filtered": 0},
                "specops": {"shown": 0, "filtered": 0},
                "teamops": {"shown": 0, "filtered": 0},
                "reinforcement": {"shown": 0, "filtered": 0},
            },
        },
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


def test_bulk_insert_batches_are_bounded() -> None:
    rows = ((number,) for number in range(BATCH_SIZE * 2 + 1))

    batches = list(batched(rows))

    assert [len(batch) for batch in batches] == [BATCH_SIZE, BATCH_SIZE, 1]
    assert batches[0][0] == (0,)
    assert batches[-1] == [(BATCH_SIZE * 2,)]


def test_secondary_indexes_are_created_after_schema_setup() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        create_schema(connection, {})
        indexes_before = {row[1] for row in connection.execute("PRAGMA index_list(units)")}
        assert "units_name" not in indexes_before

        create_indexes(connection)

        indexes_after = {row[1] for row in connection.execute("PRAGMA index_list(units)")}
        assert "units_name" in indexes_after
    finally:
        connection.close()


def test_database_validation_rejects_incomplete_logical_unit_mapping(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("DELETE FROM logical_unit_sources WHERE source_unit_id = 1")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="materialized logical-unit identity"):
        Database(path).validate()


def test_profile_payload_materialization_preserves_context_and_payload_variants(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    profiles = data["tables"]["profiles"]
    first = next(row for row in profiles if row["army_id"] == 101)
    second = next(row for row in profiles if row["army_id"] == 201)
    first["logo"] = "main-logo"
    second["logo"] = "sectorial-logo"

    path = tmp_path / "shared.sqlite3"
    export_database(data, path)
    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM profile_payloads"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT army_id, ava, logo FROM profile_payload_occurrences ORDER BY army_id"
        ).fetchall() == [
            (101, "T", "main-logo"),
            (201, 1, "sectorial-logo"),
        ]
    finally:
        connection.close()

    data = copy.deepcopy(normalized)
    next(row for row in data["tables"]["profiles"] if row["army_id"] == 201)["wip"] = 14
    variant_path = tmp_path / "variant.sqlite3"
    export_database(data, variant_path)
    variant = sqlite3.connect(variant_path)
    try:
        assert variant.execute(
            "SELECT COUNT(*) FROM profile_payloads"
        ).fetchone()[0] == 2
        assert variant.execute(
            "SELECT DISTINCT profile_payload_id FROM profile_payload_occurrences"
        ).fetchall() == [(1,), (2,)]
    finally:
        variant.close()


def test_profile_payloads_do_not_merge_across_logical_units(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    for table in (
        "profile_characteristics",
        "profile_skills",
        "profile_skill_extras",
        "profile_equipment",
        "profile_equipment_extras",
        "profile_weapons",
        "profile_weapon_extras",
    ):
        data["tables"][table] = []

    group = copy.deepcopy(
        next(
            row
            for row in data["tables"]["profile_groups"]
            if row["army_id"] == 201 and row["unit_id"] == 1
        )
    )
    group["unit_id"] = 2
    data["tables"]["profile_groups"].append(group)

    profile = copy.deepcopy(
        next(
            row
            for row in data["tables"]["profiles"]
            if row["army_id"] == 201 and row["unit_id"] == 1
        )
    )
    profile["unit_id"] = 2
    data["tables"]["profiles"].append(profile)

    path = tmp_path / "scoped.sqlite3"
    export_database(data, path)
    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM profile_payloads"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT logical_unit_id, COUNT(*) FROM profile_payloads "
            "GROUP BY logical_unit_id ORDER BY logical_unit_id"
        ).fetchall() == [(1, 1), (2, 1)]
    finally:
        connection.close()


def test_profile_payload_materialization_is_deterministic(
    tmp_path: Path, normalized: dict
) -> None:
    first = tmp_path / "first.sqlite3"
    second = tmp_path / "second.sqlite3"
    export_database(normalized, first)
    export_database(normalized, second)

    first_connection = sqlite3.connect(first)
    second_connection = sqlite3.connect(second)
    try:
        tables = (
            "profile_payloads",
            "profile_payload_occurrences",
            "profile_payload_characteristics",
            "profile_payload_skills",
            "profile_payload_skill_extras",
            "profile_payload_equipment",
            "profile_payload_equipment_extras",
            "profile_payload_weapons",
            "profile_payload_weapon_extras",
        )
        for table in tables:
            left = first_connection.execute(
                f"SELECT * FROM {quote(table)} ORDER BY rowid"
            ).fetchall()
            right = second_connection.execute(
                f"SELECT * FROM {quote(table)} ORDER BY rowid"
            ).fetchall()
            assert left == right
    finally:
        first_connection.close()
        second_connection.close()


def test_export_staging_rejects_invalid_profile_payload_context(
    tmp_path: Path, normalized: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from infinity_db.database import importer as database_importer

    original = database_importer.materialize_profile_payloads

    def corrupt(connection: sqlite3.Connection):
        result = original(connection)
        connection.execute(
            "UPDATE profile_payload_occurrences SET ava = 'corrupt' WHERE army_id = 101"
        )
        return result

    monkeypatch.setattr(database_importer, "materialize_profile_payloads", corrupt)
    with pytest.raises(ValueError, match="canonical profile payloads"):
        export_database(normalized, tmp_path / "army.sqlite3")


def test_loadout_payload_materialization_preserves_context_and_payload_variants(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    loadouts = data["tables"]["loadout_options"]
    first = next(row for row in loadouts if row["army_id"] == 101)
    second = next(row for row in loadouts if row["army_id"] == 201)
    first["points"] = 10
    first["swc"] = "0.5"
    second["points"] = 11
    second["swc"] = "1"

    path = tmp_path / "shared-loadouts.sqlite3"
    export_database(data, path)
    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM loadout_payloads"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT army_id, points, swc FROM loadout_payload_occurrences ORDER BY army_id"
        ).fetchall() == [(101, 10, "0.5"), (201, 11, "1")]
    finally:
        connection.close()

    data = copy.deepcopy(normalized)
    next(
        row
        for row in data["tables"]["option_orders"]
        if row["army_id"] == 201
    )["total_count"] = 2
    variant_path = tmp_path / "variant-loadouts.sqlite3"
    export_database(data, variant_path)
    variant = sqlite3.connect(variant_path)
    try:
        assert variant.execute(
            "SELECT COUNT(*) FROM loadout_payloads"
        ).fetchone()[0] == 2
        assert variant.execute(
            "SELECT DISTINCT loadout_payload_id FROM loadout_payload_occurrences"
        ).fetchall() == [(1,), (2,)]
    finally:
        variant.close()


def test_loadout_payloads_do_not_merge_across_logical_units(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    for table in (
        "option_characteristics",
        "option_orders",
        "option_skills",
        "option_skill_extras",
        "option_equipment",
        "option_equipment_extras",
        "option_weapons",
        "option_weapon_extras",
        "option_includes",
        "option_peripherals",
    ):
        data["tables"][table] = []

    group = copy.deepcopy(
        next(
            row
            for row in data["tables"]["profile_groups"]
            if row["army_id"] == 201 and row["unit_id"] == 1
        )
    )
    group["unit_id"] = 2
    data["tables"]["profile_groups"].append(group)

    loadout = copy.deepcopy(
        next(
            row
            for row in data["tables"]["loadout_options"]
            if row["army_id"] == 201 and row["unit_id"] == 1
        )
    )
    loadout["unit_id"] = 2
    data["tables"]["loadout_options"].append(loadout)

    path = tmp_path / "scoped-loadouts.sqlite3"
    export_database(data, path)
    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM loadout_payloads"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT logical_unit_id, COUNT(*) FROM loadout_payloads "
            "GROUP BY logical_unit_id ORDER BY logical_unit_id"
        ).fetchall() == [(1, 1), (2, 1)]
    finally:
        connection.close()


def test_loadout_payload_materialization_is_deterministic(
    tmp_path: Path, normalized: dict
) -> None:
    first = tmp_path / "first-loadouts.sqlite3"
    second = tmp_path / "second-loadouts.sqlite3"
    export_database(normalized, first)
    export_database(normalized, second)

    first_connection = sqlite3.connect(first)
    second_connection = sqlite3.connect(second)
    try:
        tables = (
            "loadout_payloads",
            "loadout_payload_occurrences",
            "loadout_payload_characteristics",
            "loadout_payload_orders",
            "loadout_payload_skills",
            "loadout_payload_skill_extras",
            "loadout_payload_equipment",
            "loadout_payload_equipment_extras",
            "loadout_payload_weapons",
            "loadout_payload_weapon_extras",
            "profile_occurrence_includes",
            "loadout_occurrence_includes",
            "unit_option_include_targets",
        )
        for table in tables:
            left = first_connection.execute(
                f"SELECT * FROM {quote(table)} ORDER BY rowid"
            ).fetchall()
            right = second_connection.execute(
                f"SELECT * FROM {quote(table)} ORDER BY rowid"
            ).fetchall()
            assert left == right
    finally:
        first_connection.close()
        second_connection.close()


def test_export_staging_rejects_invalid_loadout_payload_context(
    tmp_path: Path, normalized: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from infinity_db.database import importer as database_importer

    original = database_importer.materialize_loadout_payloads

    def corrupt(connection: sqlite3.Connection):
        result = original(connection)
        connection.execute(
            "UPDATE loadout_payload_occurrences SET points = 999 WHERE army_id = 101"
        )
        return result

    monkeypatch.setattr(database_importer, "materialize_loadout_payloads", corrupt)
    with pytest.raises(ValueError, match="canonical loadout payloads"):
        export_database(normalized, tmp_path / "army.sqlite3")


def test_include_relationships_materialize_with_evidence_based_parent_scope(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "include-relationships.sqlite3"
    export_database(normalized, path)

    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT army_id, unit_id, group_id, profile_id, position, "
            "target_loadout_payload_id, quantity, raw "
            "FROM profile_occurrence_includes ORDER BY army_id"
        ).fetchall() == [
            (101, 1, 1, 1, 1, 1, 1, None),
            (201, 1, 1, 1, 1, 1, 1, None),
        ]
        assert connection.execute(
            "SELECT army_id, unit_id, group_id, option_id, position, "
            "target_loadout_payload_id, quantity, raw "
            "FROM loadout_occurrence_includes ORDER BY army_id"
        ).fetchall() == [
            (101, 1, 1, 1, 1, 1, 1, None),
            (201, 1, 1, 1, 1, 1, 1, None),
        ]
        assert connection.execute(
            "SELECT unit_id, option_id, position, target_army_id, "
            "target_loadout_payload_id, quantity, raw "
            "FROM unit_option_include_targets ORDER BY target_army_id"
        ).fetchall() == [
            (1, 1, 1, 101, 1, 1, None),
            (1, 1, 1, 201, 1, 1, None),
        ]
    finally:
        connection.close()


def test_loadout_include_relationships_preserve_contextual_variants(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    row = next(
        row for row in data["tables"]["option_includes"] if row["army_id"] == 201
    )
    row["quantity"] = 2

    path = tmp_path / "contextual-includes.sqlite3"
    export_database(data, path)
    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM loadout_payloads"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT army_id, quantity FROM loadout_occurrence_includes ORDER BY army_id"
        ).fetchall() == [(101, 1), (201, 2)]
    finally:
        connection.close()


def test_profile_include_relationships_preserve_contextual_target_variants(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    next(
        row for row in data["tables"]["option_orders"] if row["army_id"] == 201
    )["total_count"] = 2

    path = tmp_path / "contextual-profile-includes.sqlite3"
    export_database(data, path)
    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM loadout_payloads"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT army_id, target_loadout_payload_id "
            "FROM profile_occurrence_includes ORDER BY army_id"
        ).fetchall() == [(101, 1), (201, 2)]
        assert connection.execute(
            "SELECT target_army_id, target_loadout_payload_id "
            "FROM unit_option_include_targets ORDER BY target_army_id"
        ).fetchall() == [(101, 1), (201, 2)]
    finally:
        connection.close()


def test_export_staging_rejects_invalid_materialized_include_relationship(
    tmp_path: Path, normalized: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from infinity_db.database import importer as database_importer

    original = database_importer.materialize_include_relationships

    def corrupt(connection: sqlite3.Connection):
        result = original(connection)
        connection.execute(
            "UPDATE loadout_occurrence_includes SET quantity = 2 WHERE army_id = 201"
        )
        return result

    monkeypatch.setattr(database_importer, "materialize_include_relationships", corrupt)
    with pytest.raises(ValueError, match="contextual loadout includes"):
        export_database(normalized, tmp_path / "army.sqlite3")


def test_unit_profile_read_path_uses_materialized_canonical_payloads(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    expected = Database(path).get_unit(1)
    assert expected is not None

    connection = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "profiles",
            "profile_characteristics",
            "profile_skills",
            "profile_equipment",
            "profile_weapons",
        }.isdisjoint(tables)
    finally:
        connection.close()

    assert Database(path).get_unit(1) == expected


def test_unit_loadout_read_path_uses_materialized_canonical_payloads(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    expected = Database(path).get_unit(1)
    assert expected is not None

    connection = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "loadout_options",
            "option_characteristics",
            "option_orders",
            "option_skills",
            "option_equipment",
            "option_weapons",
        }.isdisjoint(tables)
    finally:
        connection.close()

    assert Database(path).get_unit(1) == expected


def test_unit_catalog_filter_expands_logical_equipment_identity(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["equipment"] = [
        {"id": 235, "name": "TinBot", "source_defined": True},
        {"id": 244, "name": "TinBot: Discover", "source_defined": True},
    ]
    normalized["tables"]["metadata_equipment"] = [
        {"id": 169, "name": "TinBot: Firewall", "wiki": None},
        {"id": 188, "name": "TinBot: Neourocinetics", "wiki": None},
        {"id": 193, "name": "TinBot (Albedo)", "wiki": None},
        {"id": 235, "name": "TinBot", "wiki": None},
        {"id": 244, "name": "TinBot: Discover", "wiki": None},
        {"id": 247, "name": "TinBot: ECM Guided", "wiki": None},
        {"id": 248, "name": "Tinbot (Repeater)", "wiki": None},
    ]
    for table in (
        "army_equipment",
        "profile_equipment",
        "option_equipment",
        "unit_option_equipment",
    ):
        for occurrence in normalized["tables"][table]:
            occurrence["item_id"] = 244

    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    assert database.application_catalog_id("equipment", 244) == 235
    assert database.application_slug("equipment", 235) == "tinbot"
    tinbot = next(
        item for item in database.list_catalog_items("equipment") if item["id"] == 235
    )
    assert tinbot["source_ids"] == [235, 244]
    expected_ids = {1}
    for equipment_ref in (244, 235, "tinbot"):
        result = database.list_units(equipment_id=equipment_ref)
        assert {item["id"] for item in result["items"]} == expected_ids


def test_runtime_catalog_paths_use_canonical_profile_and_loadout_payloads(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)
    expected = {
        "profile_search": database.list_units(search="Trooper"),
        "loadout_search": database.list_units(search="Rifle"),
        "skill_filter": database.list_units(skill_id=1),
        "equipment_filter": database.list_units(equipment_id=1),
        "weapon_filter": database.list_units(weapon_id=1),
        "skill_extras": database.list_skill_extras(),
        "skills": database.list_catalog_items("skills"),
        "equipment": database.list_catalog_items("equipment"),
        "weapons": database.list_catalog_items("weapons"),
        "skill": database.get_skill(1),
        "equipment_detail": database.get_catalog_item("equipment", 1),
        "weapon_detail": database.get_catalog_item("weapons", 1),
    }

    connection = sqlite3.connect(path)
    try:
        connection.execute("UPDATE units SET name = 'context mutation'")
        connection.execute("UPDATE skills SET name = 'context skill mutation'")
        connection.execute("UPDATE equipment SET name = 'context equipment mutation'")
        connection.execute(
            "UPDATE weapons SET name = 'context weapon mutation', "
            "category = 'context category'"
        )
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert SOURCE_ONLY_TABLES.isdisjoint(tables)
        connection.commit()
    finally:
        connection.close()

    database = Database(path)
    assert database.list_units(search="Trooper") == expected["profile_search"]
    assert database.list_units(search="Rifle") == expected["loadout_search"]
    assert database.list_units(skill_id=1) == expected["skill_filter"]
    assert database.list_units(equipment_id=1) == expected["equipment_filter"]
    assert database.list_units(weapon_id=1) == expected["weapon_filter"]
    assert database.list_skill_extras() == expected["skill_extras"]
    assert database.list_catalog_items("skills") == expected["skills"]
    assert database.list_catalog_items("equipment") == expected["equipment"]
    assert database.list_catalog_items("weapons") == expected["weapons"]
    assert database.get_skill(1) == expected["skill"]
    assert database.get_catalog_item("equipment", 1) == expected["equipment_detail"]
    assert database.get_catalog_item("weapons", 1) == expected["weapon_detail"]


def test_database_validation_rejects_published_content_drift(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE unit_factions SET faction_id = 999 WHERE unit_id = 1"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="published application content"):
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


def test_skill_catalog_uses_curated_declaration_categories(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["skills"].extend(
        [
            {"id": 69, "name": "Strategos L1", "source_defined": True},
            {"id": 70, "name": "Strategos L2", "source_defined": True},
            {"id": 89, "name": "Sapper", "source_defined": True},
            {"id": 201, "name": "BS Attack", "source_defined": True},
            {"id": 278, "name": "BS=12", "source_defined": True},
            {"id": 279, "name": "BS=11", "source_defined": True},
            {"id": 260, "name": "Unclassified Example", "source_defined": True},
        ]
    )
    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = SkillCatalog(Database(database_path), RulesDatabase(rules_path))

    strategos = next(item for item in catalog.list_skills() if item["id"] == 69)
    assert strategos["categories"] == [
        {"name": "Automatic", "source": "N5 Core Rules v5.3", "page": 113}
    ]
    detail = catalog.get_skill(70)
    assert detail is not None
    assert detail["categories"] == [
        {"name": "Automatic", "source": "N5 Core Rules v5.3", "page": 113}
    ]
    multi = next(item for item in catalog.list_skills() if item["id"] == 89)
    assert multi["categories"] == [
        {"name": "Deployment", "source": "N5 Core Rules v5.3", "page": 111},
        {"name": "Long Skill", "source": "N5 Core Rules v5.3", "page": 111},
    ]
    mixed = catalog.get_skill(278)
    assert mixed is not None
    assert mixed["categories"] == [
        {"name": "Basic Short Skill", "source": "N5 Core Rules v5.3", "page": 40},
        {"name": "ARO", "source": "N5 Core Rules v5.3", "page": 40},
    ]
    unclassified = next(item for item in catalog.list_skills() if item["id"] == 260)
    assert unclassified["categories"] == [
        {"name": "Unclassified", "source": None, "page": None}
    ]


def test_skill_catalog_adds_curated_distance_parameter_semantics(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["skills"].append(
        {"id": 74, "name": "Super-Jump", "source_defined": True}
    )
    normalized["tables"]["extras"][0].update(
        {"name": "+5", "type": "DISTANCE"}
    )
    for occurrence in normalized["tables"]["profile_skills"]:
        occurrence["item_id"] = 74

    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    database = Database(database_path)
    catalog = SkillCatalog(database, RulesDatabase(rules_path))

    detail = catalog.get_skill(74)
    assert detail is not None
    assert detail["parameter_semantics"] == {
        "kind": "distance",
        "positive_sign": "omit",
    }

    extra = next(item for item in catalog.list_skill_extras() if item["skill_id"] == 74)
    assert extra["skill_slug"] == "super-jump"
    assert extra["is_distance"] is True
    assert extra["parameter_semantics"] == {
        "kind": "distance",
        "positive_sign": "omit",
    }

    raw_unit = database.get_unit(1)
    assert raw_unit is not None
    raw_skill = raw_unit["armies"][0]["profiles"][0]["skills"][0]
    assert "parameter_semantics" not in raw_skill
    enriched_unit = catalog.enrich_unit(raw_unit)
    skill = enriched_unit["armies"][0]["profiles"][0]["skills"][0]
    assert skill["parameter_semantics"] == {
        "kind": "distance",
        "positive_sign": "omit",
    }


def test_skill_catalog_without_rules_keeps_source_distance_typing(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["extras"][0].update(
        {"name": "+5", "type": "DISTANCE"}
    )
    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    catalog = SkillCatalog(Database(database_path), None)

    extra = catalog.list_skill_extras()[0]
    assert extra["is_distance"] is True
    assert "parameter_semantics" not in extra

def test_skill_catalog_without_rules_database_does_not_embed_rule_knowledge(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["skills"].extend(
        [
            {"id": 69, "name": "Strategos L1", "source_defined": True},
            {"id": 70, "name": "Strategos L2", "source_defined": True},
        ]
    )
    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    catalog = SkillCatalog(Database(database_path), None)

    strategos = next(item for item in catalog.list_skills() if item["id"] == 69)
    assert strategos["categories"] == [
        {"name": "Unclassified", "source": None, "page": None}
    ]


def test_application_domain_slugs_are_separate_from_source_slugs(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    assert database.list_armies()[0]["slug"] == "first_army"
    assert database.application_slug("armies", 101) == "first-army"
    assert database.application_id_for_slug("armies", "first-army") == 101
    assert database.application_domain_id("armies", 101) == 101
    assert database.application_domain_id("armies", "first-army") == 101
    assert database.application_army_id(101) == 101
    assert database.application_army_id("first-army") == 101
    assert database.application_army_id("missing-army") is None
    assert database.application_slug("units", 1) == "alpha"
    assert database.application_id_for_slug("units", "alpha") == 1
    assert database.application_domain_id("units", "alpha") == 1
    assert database.application_unit_id(1) == 1
    assert database.application_unit_id("alpha") == 1
    assert database.application_unit_id(999_999) is None
    assert database.application_slug("units", 3) == "100-guard"
    unit_by_slug = database.get_unit("alpha")
    unit_by_id = database.get_unit(1)
    assert unit_by_slug is not None
    assert unit_by_id is not None
    assert unit_by_slug["id"] == unit_by_id["id"]

    for catalog in ("skills", "equipment", "weapons"):
        item = database.list_catalog_items(catalog)[0]
        item_slug = database.application_slug(catalog, item["id"])
        assert item_slug is not None
        assert database.application_id_for_slug(catalog, item_slug) == item["id"]
        assert database.application_domain_id(catalog, item_slug) == item["id"]
        assert database.application_catalog_id(catalog, item_slug) == item["id"]
        detail = (
            database.get_skill(item_slug)
            if catalog == "skills"
            else database.get_catalog_item(catalog, item_slug)
        )
        assert detail is not None
        assert detail["id"] == item["id"]


def test_application_catalog_aliases_accept_readable_slug_references(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["skills"].extend(
        [
            {"id": 41, "name": "Mirrorball L1", "source_defined": True},
            {"id": 42, "name": "Mirrorball L2", "source_defined": True},
        ]
    )
    document = load_identity_config().document
    document["catalogs"]["skills"]["groups"].append(
        {
            "canonical_id": "mirrorball-l1",
            "source_ids": ["mirrorball-l1", "mirrorball-l2"],
            "reason": "Readable slug-authored alias test",
        }
    )
    config = parse_identity_config(document)

    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path, identity_config=config)
    database = Database(database_path)

    assert database.application_catalog_id("skills", 41) == 41
    assert database.application_catalog_id("skills", 42) == 41
    assert database.application_slug("skills", 41) == "mirrorball"


def test_catalog_identity_slugs_resolve_against_complete_metadata_catalog(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["equipment"].append(
        {"id": 169, "name": "TinBot: Firewall", "source_defined": True}
    )
    normalized["tables"]["metadata_equipment"] = [
        {"id": 169, "name": "TinBot: Firewall", "wiki": None},
        {"id": 188, "name": "TinBot: Neourocinetics", "wiki": None},
        {"id": 193, "name": "TinBot (Albedo)", "wiki": None},
        {"id": 235, "name": "TinBot", "wiki": None},
        {"id": 244, "name": "TinBot: Discover", "wiki": None},
        {"id": 247, "name": "TinBot: ECM Guided", "wiki": None},
        {"id": 248, "name": "Tinbot (Repeater)", "wiki": None},
    ]

    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    database = Database(database_path)

    assert database.application_catalog_id("equipment", 169) == 235
    assert database.application_catalog_id("equipment", 188) is None


def test_skill_catalog_resolves_source_variant_ids_before_attaching_public_slug(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["skills"].extend(
        [
            {"id": 19, "name": "Martial Arts L1", "source_defined": True},
            {"id": 20, "name": "Martial Arts L2", "source_defined": True},
            {"id": 21, "name": "Martial Arts L3", "source_defined": True},
            {"id": 22, "name": "Martial Arts L4", "source_defined": True},
            {"id": 23, "name": "Martial Arts L5", "source_defined": True},
        ]
    )
    for occurrence in normalized["tables"]["profile_skills"]:
        occurrence["item_id"] = 20

    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    database = Database(database_path)
    catalog = SkillCatalog(database, None)

    assert database.application_catalog_id("skills", 20) == 19
    assert database.application_slug("skills", 19) == "martial-arts"

    raw_unit = database.get_unit(1)
    assert raw_unit is not None
    raw_skill = raw_unit["armies"][0]["profiles"][0]["skills"][0]
    assert raw_skill["id"] == 20
    assert "slug" not in raw_skill

    enriched = catalog.enrich_unit(raw_unit)
    skill = enriched["armies"][0]["profiles"][0]["skills"][0]
    assert skill["id"] == 20
    assert skill["slug"] == "martial-arts"


def test_skill_catalog_does_not_emit_numeric_only_slug_that_would_shadow_compatibility_route(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["skills"][0]["name"] = "100"
    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    catalog = SkillCatalog(Database(database_path), None)

    skill = catalog.list_skills()[0]
    assert skill["id"] == 1
    assert "slug" not in skill
    assert Database(database_path).application_slug("skills", 1) is None

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT candidate_slug, slug, status FROM application_domain_slugs "
            "WHERE domain = 'skills' AND application_id = 1"
        ).fetchone()
    assert row == ("100", None, "unavailable")


def test_equipment_slug_enrichment_resolves_source_variant_ids(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["equipment"].extend(
        [
            {"id": 169, "name": "TinBot: Firewall", "source_defined": True},
            {"id": 188, "name": "TinBot: Neourocinetics", "source_defined": True},
            {"id": 193, "name": "TinBot (Albedo)", "source_defined": True},
            {"id": 235, "name": "TinBot", "source_defined": True},
            {"id": 244, "name": "TinBot: Discover", "source_defined": True},
            {"id": 247, "name": "TinBot: ECM Guided", "source_defined": True},
            {"id": 248, "name": "Tinbot (Repeater)", "source_defined": True},
        ]
    )
    for occurrence in normalized["tables"]["profile_equipment"]:
        occurrence["item_id"] = 244
    for occurrence in normalized["tables"]["option_equipment"]:
        occurrence["item_id"] = 244

    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    database = Database(database_path)

    assert database.application_catalog_id("equipment", 244) == 235
    assert database.application_slug("equipment", 235) == "tinbot"

    raw_unit = database.get_unit(1)
    assert raw_unit is not None
    raw_equipment = raw_unit["armies"][0]["profiles"][0]["equipment"][0]
    assert raw_equipment["id"] == 244
    assert "slug" not in raw_equipment

    enriched = enrich_nested_catalog_slugs(
        database,
        raw_unit,
        frozenset({"equipment"}),
    )
    equipment = enriched["armies"][0]["profiles"][0]["equipment"][0]
    assert equipment["id"] == 244
    assert equipment["slug"] == "tinbot"


def test_equipment_slug_enrichment_does_not_emit_numeric_only_slug(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["equipment"][0]["name"] = "100"
    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    database = Database(database_path)

    equipment = database.list_catalog_items("equipment")[0]
    attach_public_catalog_slug(database, "equipment", equipment)

    assert equipment["id"] == 1
    assert "slug" not in equipment
    assert database.application_slug("equipment", 1) is None


def test_weapon_slug_enrichment_resolves_source_variant_ids(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["weapons"].extend(
        [
            {
                "id": source_id,
                "name": name,
                "source_defined": True,
                "category": "Uncategorized",
            }
            for source_id, name in (
                (209, "Armed Turret (Combi R.)"),
                (215, "Armed Turret (Marksman R.)"),
                (219, "Armed Turret (AP Rifle)"),
                (222, "Armed Turret (Rifle)"),
                (226, "Armed Turret"),
                (228, "Armed Turret (E/Mitter)"),
            )
        ]
    )
    for occurrence in normalized["tables"]["profile_weapons"]:
        occurrence["item_id"] = 228
    for occurrence in normalized["tables"]["option_weapons"]:
        occurrence["item_id"] = 228

    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    database = Database(database_path)

    assert database.application_catalog_id("weapons", 228) == 226
    assert database.application_slug("weapons", 226) == "armed-turret"

    raw_unit = database.get_unit(1)
    assert raw_unit is not None
    raw_weapon = raw_unit["armies"][0]["profiles"][0]["weapons"][0]
    assert raw_weapon["id"] == 228
    assert "slug" not in raw_weapon

    enriched = enrich_nested_catalog_slugs(
        database,
        raw_unit,
        frozenset({"weapons"}),
    )
    weapon = enriched["armies"][0]["profiles"][0]["weapons"][0]
    assert weapon["id"] == 228
    assert weapon["slug"] == "armed-turret"


def test_weapon_slug_enrichment_does_not_emit_numeric_only_slug(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["weapons"][0]["name"] = "100"
    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    database = Database(database_path)

    weapon = database.list_catalog_items("weapons")[0]
    attach_public_catalog_slug(database, "weapons", weapon)

    assert weapon["id"] == 1
    assert "slug" not in weapon
    assert database.application_slug("weapons", 1) is None


def test_dual_identifier_contract_canonicalizes_source_ids_and_prefers_public_slugs(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    document = load_identity_config().document
    document["units"]["groups"].append(
        {
            "canonical_id": 1,
            "source_ids": [1, 2],
            "reason": "Dual-identifier contract fixture",
        }
    )
    document["armies"]["groups"].append(
        {
            "canonical_id": 201,
            "source_ids": [201, 301],
            "reason": "Dual-identifier contract fixture",
        }
    )

    catalog_cases: dict[str, tuple[int, int]] = {}
    for catalog in ("skills", "equipment", "weapons"):
        rows = [
            {
                "id": 41,
                "name": f"Contract {catalog.title()} L1",
                "source_defined": True,
            },
            {
                "id": 42,
                "name": f"Contract {catalog.title()} L2",
                "source_defined": True,
            },
        ]
        if catalog == "weapons":
            for row in rows:
                row["category"] = "Uncategorized"
        data["tables"][catalog].extend(rows)
        document["catalogs"][catalog]["groups"].append(
            {
                "canonical_id": f"contract-{catalog}-l1",
                "source_ids": [
                    f"contract-{catalog}-l1",
                    f"contract-{catalog}-l2",
                ],
                "reason": "Dual-identifier contract fixture",
            }
        )
        catalog_cases[catalog] = (42, 41)

    path = tmp_path / "dual-identifiers.sqlite3"
    export_database(data, path, identity_config=parse_identity_config(document))
    database = Database(path)

    cases = {
        "armies": (301, 201),
        "units": (2, 1),
        **catalog_cases,
    }
    assert set(cases) == set(APPLICATION_SLUG_DOMAINS)

    for domain in APPLICATION_SLUG_DOMAINS:
        source_id, application_id = cases[domain]
        slug = database.application_slug(domain, application_id)
        assert slug is not None
        assert not slug.isdigit()
        assert database.application_domain_id(domain, application_id) == application_id
        assert database.application_domain_id(domain, source_id) == application_id
        assert database.application_domain_id(domain, slug) == application_id
        assert database.application_id_for_slug(domain, slug) == application_id
        assert public_slug_for_reference(database, domain, source_id) == slug
        assert public_slug_for_reference(database, domain, slug) == slug
        assert database.application_domain_id(domain, "unknown-contract-slug") is None

    for catalog, (source_id, application_id) in catalog_cases.items():
        item = next(
            item
            for item in database.list_catalog_items(catalog)
            if item["id"] == application_id
        )
        assert source_id in item["source_ids"]


def test_dual_identifier_contract_unavailable_and_colliding_slugs_fail_closed(
    tmp_path: Path, normalized: dict
) -> None:
    numeric = copy.deepcopy(normalized)
    next(row for row in numeric["tables"]["army_lists"] if row["id"] == 101)["slug"] = "100"
    next(row for row in numeric["tables"]["units"] if row["id"] == 1)["slug"] = "100"
    for catalog in ("skills", "equipment", "weapons"):
        numeric["tables"][catalog][0]["name"] = "100"

    numeric_path = tmp_path / "numeric-shadow.sqlite3"
    export_database(numeric, numeric_path)
    numeric_database = Database(numeric_path)
    numeric_ids = {
        "armies": 101,
        "units": 1,
        "skills": 1,
        "equipment": 1,
        "weapons": 1,
    }
    assert set(numeric_ids) == set(APPLICATION_SLUG_DOMAINS)
    for domain, application_id in numeric_ids.items():
        assert numeric_database.application_domain_id(domain, application_id) == application_id
        assert numeric_database.application_slug(domain, application_id) is None
        assert public_slug_for_reference(numeric_database, domain, application_id) is None

    collision = copy.deepcopy(normalized)
    for army_id in (101, 201):
        next(
            row for row in collision["tables"]["army_lists"] if row["id"] == army_id
        )["slug"] = "contract-collision"
    for unit_id in (1, 2):
        next(row for row in collision["tables"]["units"] if row["id"] == unit_id)[
            "slug"
        ] = "contract-collision"
    for catalog in ("skills", "equipment", "weapons"):
        collision["tables"][catalog][0]["name"] = "Contract Collision"
        second = {
            "id": 2,
            "name": "Contract Collision",
            "source_defined": True,
        }
        if catalog == "weapons":
            second["category"] = "Uncategorized"
        collision["tables"][catalog].append(second)

    collision_path = tmp_path / "slug-collision.sqlite3"
    export_database(collision, collision_path)
    collision_database = Database(collision_path)
    collision_ids = {
        "armies": (101, 201),
        "units": (1, 2),
        "skills": (1, 2),
        "equipment": (1, 2),
        "weapons": (1, 2),
    }
    assert set(collision_ids) == set(APPLICATION_SLUG_DOMAINS)
    for domain, application_ids in collision_ids.items():
        assert collision_database.application_domain_id(
            domain, "contract-collision"
        ) is None
        for application_id in application_ids:
            assert collision_database.application_slug(domain, application_id) is None
            assert (
                public_slug_for_reference(collision_database, domain, application_id)
                is None
            )


def test_dual_identifier_contract_traits_keep_slug_owned_identity(
    tmp_path: Path, normalized: dict
) -> None:
    data = copy.deepcopy(normalized)
    data["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 1,
            "type": "BS",
            "name": "Combi Rifle",
            "properties": ["Continous Damage"],
        }
    ]
    database_path = tmp_path / "trait-contract.sqlite3"
    export_database(data, database_path)

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "trait-contract-rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = TraitCatalog(Database(database_path), RulesDatabase(rules_path))

    assert "traits" not in APPLICATION_SLUG_DOMAINS
    trait = catalog.get_trait("continuous-damage")
    assert trait is not None
    assert trait["id"] == "continuous-damage"
    assert trait["slug"] == "continuous-damage"
    assert catalog.reference("Continous Damage")["slug"] == "continuous-damage"
    assert catalog.get_trait("unknown-contract-trait") is None
    assert catalog.reference("Not Present In Army Data")["slug"] is None


def test_application_domain_slug_lookup_rejects_unknown_domains(
    tmp_path: Path, normalized: dict
) -> None:
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)

    with pytest.raises(ValueError, match="Unknown slug domain"):
        database.application_slug("profiles", 1)
    with pytest.raises(ValueError, match="Unknown slug domain"):
        database.application_id_for_slug("profiles", "trooper")


def test_database_materializes_and_exposes_reviewed_embedded_peripheral(
    tmp_path: Path, normalized: dict
) -> None:
    from infinity_db.peripheral_identities import parse_peripheral_identity_curated

    data = copy.deepcopy(normalized)
    data["_meta"]["snapshotArchiveSha256"] = "a" * 64
    curated = parse_peripheral_identity_curated(
        {
            "format": "InfinityDB curated Peripheral identities",
            "formatVersion": 3,
            "sources": [
                {
                    "id": "army-json-test",
                    "kind": "army-snapshot",
                    "artifact": "JSON test.zip",
                    "sha256": "a" * 64,
                    "acquiredAt": "2026-09-22T06:00:00+02:00",
                    "authority": "primary",
                }
            ],
            "entities": [
                {
                    "id": "peripheral:drone",
                    "name": "Drone",
                    "typeId": "rule:peripheral-type:servant",
                    "review": {"status": "reviewed", "reviewedOn": "2026-09-22"},
                }
            ],
            "profiles": [],
            "mappings": [
                {
                    "id": "peripheral-mapping:army-101-1",
                    "sourceId": "army-json-test",
                    "armyId": 101,
                    "peripheralId": 1,
                    "sourceName": "Drone",
                    "entityId": "peripheral:drone",
                    "review": {
                        "status": "reviewed",
                        "reviewedOn": "2026-09-22",
                        "reason": "Reviewed test mapping.",
                    },
                }
            ],
            "unitMappings": [],
            "controllerAccess": [],
        }
    )
    path = tmp_path / "army.sqlite3"

    export_database(data, path, peripheral_identities=curated)

    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT id, name, type_id FROM application_peripheral_entities"
        ).fetchall() == [
            ("peripheral:drone", "Drone", "rule:peripheral-type:servant")
        ]
        assert connection.execute(
            "SELECT army_id, peripheral_id, entity_id FROM application_peripheral_sources"
        ).fetchall() == [(101, 1, "peripheral:drone")]
    finally:
        connection.close()

    details = Database(path).get_unit(1)
    assert details is not None
    first_army = next(army for army in details["armies"] if army["id"] == 101)
    assert first_army["profiles"][0]["peripherals"] == [
        {
            "id": "peripheral:drone",
            "name": "Drone",
            "type_id": "rule:peripheral-type:servant",
            "quantity": 1,
        }
    ]
    assert first_army["loadouts"][0]["peripherals"] == [
        {
            "id": "peripheral:drone",
            "name": "Drone",
            "type_id": "rule:peripheral-type:servant",
            "quantity": 1,
        }
    ]


def test_skill_catalog_keeps_source_specific_rules_on_matching_variant(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["skills"].extend(
        [
            {"id": 19, "name": "Martial Arts L1", "source_defined": True},
            {"id": 20, "name": "Martial Arts L2", "source_defined": True},
            {"id": 21, "name": "Martial Arts L3", "source_defined": True},
            {"id": 22, "name": "Martial Arts L4", "source_defined": True},
            {"id": 23, "name": "Martial Arts L5", "source_defined": True},
        ]
    )
    for occurrence in normalized["tables"]["profile_skills"]:
        occurrence["item_id"] = 20

    database_path = tmp_path / "army.sqlite3"
    export_database(normalized, database_path)
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    document = copy.deepcopy(current)
    common = {
        "kind": "skill",
        "summary": "Martial Arts test semantics.",
        "scope": {"game": "N5", "seasons": ["current"]},
        "facts": {"category": "special-skill", "typeId": "automatic"},
        "labelIds": [],
        "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 100}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
    }
    document["records"].extend(
        [
            {
                **common,
                "id": "skill:martial-arts",
                "name": "Martial Arts",
                "armyLinks": [{"entity": "skill", "id": "martial-arts"}],
                "variantSemantics": {"inheritance": "family"},
            },
            {
                **common,
                "id": "skill:martial-arts-l2",
                "name": "Martial Arts L2",
                "summary": "Level 2 semantics only.",
                "armyLinks": [{"entity": "skill", "id": 20}],
                "variantSemantics": {"inheritance": "source"},
                "relations": [
                    {"type": "variant-of", "recordId": "skill:martial-arts"}
                ],
            },
        ]
    )
    rules_path = tmp_path / "rules.db"
    export_rules_database([(current_path, document)], rules_path)

    detail = SkillCatalog(Database(database_path), RulesDatabase(rules_path)).get_skill(20)

    assert detail is not None
    assert [rule["id"] for rule in detail["rules"]] == ["skill:martial-arts"]
    variant = next(item for item in detail["variants"] if item["skill_id"] == 20)
    assert [rule["id"] for rule in variant["rules"]] == ["skill:martial-arts-l2"]
