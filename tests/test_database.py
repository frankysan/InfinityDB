from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from infinity_army_data.normalize import main_army_id, normalize_master, validate_normalized
from infinity_db.database import Database, export_database
from infinity_db.database.repository import logical_unit_groups
from infinity_db.database.schema import METADATA_TABLE, ROW_JSON, TABLES, quote


@pytest.fixture
def normalized() -> dict:
    """Exercise the real normalizer, including every table it can generate."""
    reference = {"id": 1, "order": 2, "q": 1, "extra": [1], "future": {"enabled": True}}
    nested = {
        "skills": [reference], "equip": [reference], "weapons": [reference],
        "peripheral": [{"id": 1, "q": 1}], "chars": [1],
        "includes": [{"group": 1, "option": 1, "q": 1}],
        "orders": [{"type": "regular", "list": 1, "total": 1}],
    }
    group = {
        "id": 1, "category": 1, "isc": "Infantry",
        "profiles": [{
            "id": 1, "name": "Trooper", "type": 1, "move": [4, 4], "ava": "T",
            **nested,
        }],
        "options": [{"id": 1, "name": "Rifle", "points": 10, "swc": "0.5", **nested}],
    }
    filters = {
        key: [{"id": 1, "name": key, "mercs": False, "future_field": {"value": [1, None]}}]
        for key in (
            "category", "chars", "type", "equip", "skills", "weapons", "ammunition", "extras"
        )
    }
    filters["peripheral"] = [{"id": 1, "name": "Drone"}]
    master = {
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyLists": {
            "101": {
                "_meta": {"slug": "first_army", "kind": "faction"}, "unitIds": [1, 3],
                "filters": filters, "reinforcements": 999,
                "resume": {"future": [True, "text"]},
                "fireteamChart": {
                    "spec": {"max": 2}, "teams": [{
                        "name": "Team", "type": ["Core"],
                        "units": [{"slug": "alpha", "name": "Alpha", "min": 1}],
                    }],
                },
                "relations": [{"min": 1, "units": [{
                    "unit": 1, "profile": 1,
                    "depends": [{"unit": 9999, "options": [1], "future": "preserved"}],
                }]}],
            },
            "201": {
                "_meta": {"slug": "second-army", "kind": "sectorial"},
                "unitIds": [1, 2], "filters": filters,
            },
            "301": {"_meta": {"slug": "empty_army"}, "unitIds": []},
        },
        "units": {
            "1": {
                "shared": {
                    "id": 1, "name": "Álpha", "slug": "alpha", "canonical": 999,
                    "factions": [101], "notes": {"language": "日本語"},
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
        assert json.loads(connection.execute(
            "SELECT future_field FROM skills WHERE id = 1"
        ).fetchone()[0]) == {"value": [1, None]}
        stored_warnings = connection.execute(
            f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = 'warnings'"
        ).fetchone()[0]
        assert json.loads(stored_warnings) == normalized["warnings"]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError), connection:
            connection.execute("UPDATE profiles SET army_id = 404 WHERE army_id = 101")
    finally:
        connection.close()


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
        {"id": 101, "name": "First Army"}, {"id": 201, "name": "Second Army"},
    ]
    assert database.list_units(army_id=301)["items"] == []
    assert database.list_units(army_id=999)["total"] == 0
    assert database.list_units(search="ÁLPHA")["items"][0]["id"] == 1
    assert database.list_units(search="%_")["items"][0]["id"] == 3
    assert database.list_units(search="' OR 1 = 1 --")["total"] == 0
    assert database.list_units(search="missing")["items"] == []
    assert database.list_units(limit=1, offset=1) == {
        "items": [{
            "id": 1, "name": "Álpha", "isc": None, "slug": "alpha", "main_army_id": None,
            "source_ids": [1],
            "army_ids": [101, 201],
            "armies": [
                {"id": 101, "name": "First Army"},
                {"id": 201, "name": "Second Army"},
            ],
        }],
        "total": 3, "limit": 1, "offset": 1,
    }


def test_main_army_resolves_canonical_sectorials_to_whole_armies(normalized: dict) -> None:
    beta = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 2)
    assert beta["main_army_id"] == 101

    # A sectorial canonical ID resolves to its parent xx01 list, not the
    # sectorial itself.
    assert main_army_id(202, {101, 201, 202}) == 201
    assert main_army_id(1, {101, 201}) == 101
    assert main_army_id(998, {901, 998}) == 901
    assert main_army_id(999, {101, 201}) is None


def test_duplicate_10000_id_family_is_one_logical_unit(
    tmp_path: Path, normalized: dict
) -> None:
    original = next(unit for unit in normalized["tables"]["units"] if unit["id"] == 1)
    normalized["tables"]["units"].append({
        "id": 10_001,
        "name": original["name"],
        "isc": original["isc"],
        "canonical_faction_id": None,
        "source_defined": True,
    })
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


def test_reinforcement_only_variants_join_their_standard_unit() -> None:
    rows = [
        {
            "id": 265, "isc": "Wardrivers, Mercenary Hackers", "name": "WARDRIVERS",
            "main_army_id": 301,
        },
        {
            "id": 1635, "isc": "Reinf. Wardrivers, Mercenary Hackers",
            "name": "REINF: WARDRIVERS", "main_army_id": 401,
        },
        {
            "id": 1691, "isc": "Reinf. Wardrivers, Mercenary Hackers",
            "name": "REFUERZOS: WARDRIVERS", "main_army_id": 501,
        },
    ]
    memberships = {
        265: [{"id": 301, "name": "Ariadna"}],
        1635: [{"id": 399, "name": "Reinforcements"}],
        1691: [{"id": 999, "name": "Reinforcements"}],
    }

    groups = logical_unit_groups(rows, memberships)

    assert len(groups) == 1
    assert groups[0]["id"] == 265
    assert groups[0]["main_army_id"] == 301
    assert groups[0]["source_ids"] == [265, 1635, 1691]
    assert list(groups[0]["armies"]) == [301, 399, 999]


@pytest.mark.parametrize("mutation", [
    lambda data: data["_meta"].update(format="not normalized"),
    lambda data: data["_meta"].update(formatVersion=2),
    lambda data: data.update(tables=[]),
    lambda data: data["tables"].update(units=["invalid"]),
    lambda data: data["tables"]["army_units"][0].update(unit_id=404),
    lambda data: data["tables"]["profile_skills"].append(data["tables"]["profile_skills"][0]),
    lambda data: data["tables"]["profiles"][0].update(profile_id=None),
    lambda data: data["tables"].update(unexpected_table=[]),
])
def test_invalid_import_keeps_existing_database(
    tmp_path: Path, normalized: dict, mutation
) -> None:
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
    empty = normalize_master({
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyLists": {}, "units": {},
    })
    export_database(empty, path)
    database = Database(path)
    database.validate()
    assert database.list_armies() == []
    assert database.list_units() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_fallback_names_are_used_for_normalized_display_sorting_and_search(
    tmp_path: Path, normalized: dict
) -> None:
    normalized["tables"]["units"].extend([
        {"id": 4, "name": None, "source_defined": True},
        {"id": 5, "name": "", "source_defined": True},
        {"id": 6, "name": "A-l.p/h+a", "source_defined": True},
        {"id": 7, "name": "Béta", "source_defined": True},
        {"id": 8, "name": "C.A.T.!", "source_defined": True},
    ])
    path = tmp_path / "army.sqlite3"
    export_database(normalized, path)
    database = Database(path)
    assert [unit["name"] for unit in database.list_units()["items"]] == [
        "100%_Guard", "Álpha", "A-l.p/h+a", "Beta", "Béta", "C.A.T.!", "Unit 4", "Unit 5",
    ]
    assert database.list_units(search="UNIT 4")["items"] == [{
        "id": 4, "name": "Unit 4", "isc": None, "slug": None, "main_army_id": None,
        "source_ids": [4],
        "army_ids": [], "armies": [],
    }]
    assert database.list_units(search="unit", limit=1, offset=1) == {
        "items": [{
            "id": 5, "name": "Unit 5", "isc": None, "slug": None, "main_army_id": None,
            "source_ids": [5], "army_ids": [],
            "armies": [],
        }],
        "total": 2, "limit": 1, "offset": 1,
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


@pytest.mark.parametrize("arguments", [
    {"limit": 0}, {"limit": 501}, {"limit": True}, {"offset": -1}, {"offset": 0.5},
    {"army_id": "101"}, {"search": None}, {"army_id": 2**63}, {"army_id": -(2**63) - 1},
    {"offset": 2**63},
])
def test_repository_rejects_invalid_query_arguments(tmp_path: Path, arguments: dict) -> None:
    with pytest.raises(ValueError, match=next(iter(arguments))):
        Database(tmp_path / "missing.sqlite3").list_units(**arguments)
