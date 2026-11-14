"""Focused Unit Explorer multi-selection API and query regression checks."""

import json
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
    assert status == 400
    assert "presentation-encoded Equipment" in payload["error"]
