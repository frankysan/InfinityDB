"""Focused Unit Explorer multi-selection API and query regression checks."""

import json
import sqlite3
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.database import Database
from infinity_db.equipment_catalog import EquipmentCatalog
from infinity_db.web import create_app
from infinity_db.web.api_handler import _unit_query


def test_multi_selection_query_preserves_legacy_and_canonical_values() -> None:
    assert _unit_query("skill_id=doctor")["skill_id"] == "doctor"
    assert _unit_query("skill_id=2")["skill_id"] == 2
    assert _unit_query("skill_id=doctor,paramedic,doctor")["skill_id"] == (
        "doctor",
        "paramedic",
    )
    assert _unit_query("skill_id=2,1,2")["skill_id"] == (1, 2)
    assert _unit_query("equipment_id=0&weapon_id=rifle")["equipment_id"] == 0
    assert _unit_query("skill_id=")["skill_id"] is None


@pytest.mark.parametrize(
    "query",
    [
        "skill_id=doctor&skill_id=paramedic",
        "skill_id=doctor,,paramedic",
        "skill_id=doctor,",
        "skill_id=doctor,%20",
        "skill_id=" + ",".join(str(number) for number in range(17)),
        "skill_id=" + "x" * 1025,
        "skill_id=../../etc/passwd",
    ],
)
def test_multi_selection_rejects_invalid_queries(query: str) -> None:
    with pytest.raises(ValueError):
        _unit_query(query)


def test_multi_selection_matches_union_of_one_category() -> None:
    database = Database(Path("data/generated/army.db"))
    chosen = []
    for item in database.list_catalog_items("skills")[:30]:
        result = database.list_units(
            skill_id=item["id"], limit=10_000, _unbounded=True
        )
        if result["total"]:
            chosen.append((item["id"], {unit["id"] for unit in result["items"]}))
        if len(chosen) == 2:
            break
    assert len(chosen) == 2
    combined = database.list_units(
        skill_id=tuple(item_id for item_id, _ in chosen),
        limit=10_000,
        _unbounded=True,
    )
    assert {unit["id"] for unit in combined["items"]} == (
        chosen[0][1] | chosen[1][1]
    )
    assert combined["total"] == len(combined["items"])


@pytest.mark.parametrize(
    ("argument", "vocabulary"),
    [
        ("troop_type", "troop_types"),
        ("classification", "classifications"),
        ("characteristic", "characteristics"),
    ],
)
def test_multi_categorical_selection_is_or_within_filter(
    argument: str, vocabulary: str
) -> None:
    database = Database(Path("data/generated/army.db"))
    def query(value: str | tuple[str, ...]) -> dict:
        if argument == "troop_type":
            return database.list_units(troop_type=value, limit=10_000, _unbounded=True)
        if argument == "classification":
            return database.list_units(classification=value, limit=10_000, _unbounded=True)
        return database.list_units(characteristic=value, limit=10_000, _unbounded=True)

    chosen = []
    for item in database.list_unit_filter_values()[vocabulary][:40]:
        result = query(item["slug"])
        if result["total"]:
            chosen.append((item["slug"], {unit["id"] for unit in result["items"]}))
        if len(chosen) == 2:
            break
    assert len(chosen) == 2
    result = query(tuple(slug for slug, _ in chosen))
    assert {unit["id"] for unit in result["items"]} == (
        chosen[0][1] | chosen[1][1]
    )


def test_combined_multi_filters_require_both_categories() -> None:
    database = Database(Path("data/generated/army.db"))
    skills = tuple(item["id"] for item in database.list_catalog_items("skills")[:2])
    equipment = database.list_catalog_items("equipment")[0]["id"]
    matching_skills = {
        item["id"]
        for item in database.list_units(
            skill_id=skills, limit=10_000, _unbounded=True
        )["items"]
    }
    matching_equipment = {
        item["id"]
        for item in database.list_units(
            equipment_id=equipment, limit=10_000, _unbounded=True
        )["items"]
    }
    combined = database.list_units(
        skill_id=skills, equipment_id=equipment, limit=10_000, _unbounded=True
    )
    assert {item["id"] for item in combined["items"]} <= (
        matching_skills & matching_equipment
    )
    assert combined["total"] == len(combined["items"])


def test_multi_selection_does_not_resolve_unknown_slugs() -> None:
    database = Database(Path("data/generated/army.db"))
    assert database.list_units(skill_id=("doctor", "does-not-exist"))["total"] == 0
    assert database.list_units(troop_type=("missing", "also-missing"))["total"] == 0
    with pytest.raises(ValueError, match="1 to 16"):
        database.list_units(skill_id=tuple(str(i) for i in range(17)))


def test_multi_selection_http_request_and_legacy_contract() -> None:
    path = Path("data/generated/army.db")
    database = Database(path)
    app = create_app(path, rules_database_path=Path("data/generated/rules_n5.db"))
    first, second = [item["id"] for item in database.list_catalog_items("skills")[:2]]

    def request(query: str) -> tuple[int, dict]:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO="/api/units", QUERY_STRING=query, REQUEST_METHOD="GET")
        response: dict = {}

        def start_response(status: str, _headers: list, _exc_info=None) -> None:
            response["status"] = int(status.split()[0])

        payload = b"".join(app(environ, start_response))
        return response["status"], json.loads(payload)

    for query in (f"skill_id={first}", f"skill_id={first},{second}"):
        status, payload = request(query)
        assert status == 200
        assert payload["total"] == database.list_units(
            skill_id=(first, second) if "," in query else first
        )["total"]
    status, payload = request(f"skill_id={first}&skill_id={second}")
    assert status == 400
    assert "only once" in payload["error"]
    catalog = EquipmentCatalog(database, None)
    encoded = next(
        encoding.equipment_id
        for encoding in catalog._encodings
        if catalog.logical_unit_ids_for_filter(encoding.equipment_id) is not None
    )
    equipment_id = database.list_catalog_items("equipment")[0]["id"]
    status, payload = request(f"equipment_id={encoded},{equipment_id}")
    assert status == 200
    encoded_ids = catalog.logical_unit_ids_for_filter(encoded)
    assert encoded_ids is not None
    visible_encoded_ids = {
        item["id"] for item in database.list_units(
            _logical_unit_ids=encoded_ids, limit=10_000, _unbounded=True,
        )["items"]
    }
    ordinary_ids = {
        item["id"] for item in database.list_units(
            equipment_id=equipment_id, limit=10_000, _unbounded=True,
        )["items"]
    }
    assert payload["total"] == len(visible_encoded_ids | ordinary_ids)
    assert {item["id"] for item in payload["items"]} <= visible_encoded_ids | ordinary_ids
    status, filtered = request(f"equipment_id={encoded},{equipment_id}&skill_id={first}")
    assert status == 200
    assert filtered["total"] <= payload["total"]
    status, invalid = request(f"equipment_id={encoded},does-not-exist")
    assert status == 200
    assert invalid["total"] == 0

def test_multiselect_contexts_reject_mixed_armies_groups_and_loadouts(
    tmp_path: Path,
) -> None:
    """A single logical Unit must not combine incompatible source occurrences."""

    path = tmp_path / "multi-context.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE logical_unit_sources (
                source_unit_id INTEGER, logical_unit_id INTEGER
            );
            CREATE TABLE application_army_sources (
                source_army_id INTEGER, application_army_id INTEGER, has_army_list INTEGER
            );
            CREATE TABLE profile_payload_occurrences (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER,
                profile_payload_id INTEGER, ava INTEGER
            );
            CREATE TABLE loadout_payload_occurrences (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER,
                loadout_payload_id INTEGER, points INTEGER, swc TEXT
            );
            CREATE TABLE profile_payload_skills (
                profile_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE loadout_payload_skills (
                loadout_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE unit_option_skills (unit_id INTEGER, item_id INTEGER);
            CREATE TABLE profile_payload_weapons (
                profile_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE loadout_payload_weapons (
                loadout_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE unit_option_weapons (unit_id INTEGER, item_id INTEGER);
            INSERT INTO logical_unit_sources VALUES (1, 1);
            INSERT INTO application_army_sources VALUES (101, 501, 1), (201, 502, 1);
            INSERT INTO profile_payload_occurrences VALUES
                (101, 1, 1, 10, 1),
                (101, 1, 2, 20, 2),
                (201, 1, 1, 30, 3);
            INSERT INTO profile_payload_skills VALUES (10, 1), (20, 2), (30, 3);
            INSERT INTO loadout_payload_occurrences VALUES
                (101, 1, 1, 100, 10, '0'),
                (101, 1, 1, 101, 20, '0'),
                (101, 1, 2, 102, 10, '0'),
                (201, 1, 1, 103, 10, '0');
            INSERT INTO loadout_payload_weapons VALUES
                (100, 4), (101, 5), (102, 6), (103, 5);
        """)
    database = Database(path)

    def matches(
        skill_ids: tuple[int, ...],
        weapon_ids: tuple[int, ...],
        *,
        army: int | None = None,
        points: int | None = None,
        ava: int | None = None,
    ) -> set[tuple[int, int, int]]:
        result = database._contextual_unit_filter_matches(
            army_id=army,
            rule_source_ids={"skills": skill_ids, "weapons": weapon_ids},
            troop_type_ids=(),
            classification_ids=(),
            characteristic_ids=(),
            equipment_characteristic_ids=(),
            ava=ava,
            ava_min=None,
            ava_max=None,
            points=points,
            points_min=None,
            points_max=None,
            swc=None,
            swc_min=None,
            swc_max=None,
            force_loadout_context=True,
        )
        return set(result.get(1, ()))

    # Alternatives in one dropdown are OR. Other categories must match the
    # same Army, group and, when Points is constrained, the same loadout.
    assert matches((1, 99), (4, 98), army=501, points=10) == {(1, 101, 1)}
    assert matches((1, 99), (5, 98), army=501, points=10) == set()
    assert matches((1, 99), (5, 98), army=501, points=20) == {(1, 101, 1)}
    assert matches((1, 99), (6, 98), army=501) == set()
    assert matches((1, 2), (6, 98), army=501) == {(1, 101, 2)}
    assert matches((1, 99), (5, 98), army=502) == set()
    assert matches((2, 99), (5, 98), army=502) == set()
    assert matches((1, 99), (4, 98), army=501, ava=2) == set()


def test_multiselect_availability_and_result_views_are_consistent() -> None:
    database = Database(Path("data/generated/army.db"))
    skills = tuple(item["id"] for item in database.list_catalog_items("skills")[:2])
    default = database.list_units(skill_id=skills, limit=10_000, _unbounded=True)
    optional = database.list_units(
        skill_id=skills,
        mercs=True, specops=True, teamops=True, reinforcement=True,
        limit=10_000, _unbounded=True,
    )
    default_ids = {unit["id"] for unit in default["items"]}
    optional_ids = {unit["id"] for unit in optional["items"]}
    assert default_ids <= optional_ids
    assert default["total"] == len(default_ids)
    assert optional["total"] == len(optional_ids)

    sorted_result = database.list_units(
        skill_id=skills, descending=True, limit=2, offset=0,
    )
    extended_result = database.list_units(
        skill_id=skills, extended=True, limit=2, offset=0,
    )
    assert sorted_result["total"] == extended_result["total"] == default["total"]
    assert {unit["id"] for unit in sorted_result["items"]} <= default_ids
    assert {unit["id"] for unit in extended_result["items"]} <= default_ids
