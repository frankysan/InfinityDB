"""General-profile display folding for common items with varied loadout extras."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from infinity_db.database import Database
from infinity_db.unit_presentation import enrich_unit_presentation

DATABASE = Path("data/generated/army.db")
PROPERTIES = ("skills", "equipment", "weapons")


def item(item_id: int, *, extra: int | None = None, quantity: int = 1) -> dict[str, Any]:
    return {
        "id": item_id, "name": f"Item {item_id}",
        "quantity": quantity, "extras": [] if extra is None else [{"id": extra}],
    }


def fixture_loadouts(
    *entries: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    return {
        "armies": [{
            "id": 101,
            "availability_flags": [],
            "profiles": [{
                "profile_identity": "test-profile",
                "display_name": "Test Trooper",
                "group_id": 1,
                **{key: [] for key in PROPERTIES},
            }],
            "loadouts": [
                {"group_id": 1, **{key: entry.get(key, []) for key in PROPERTIES}}
                for entry in entries
            ],
        }],
    }


def test_common_bases_move_to_general_and_only_no_extra_variants_are_hidden() -> None:
    unit = fixture_loadouts(
        {key: [item(index)] for index, key in enumerate(PROPERTIES, 10)},
        {key: [item(index, extra=70)] for index, key in enumerate(PROPERTIES, 10)},
        {key: [item(index, extra=71)] for index, key in enumerate(PROPERTIES, 10)},
    )
    original = deepcopy(unit)
    result = enrich_unit_presentation(unit, source_skill_classifications=())
    general = result["general_profiles"][0]["shared_items"]
    for index, key in enumerate(PROPERTIES, 10):
        assert [(entry["id"], entry["extras"]) for entry in general[key]] == [(index, [])]
        loadouts = result["armies"][0]["loadouts"]
        assert loadouts[0]["specific_items"][key] == []
        assert [entry["extras"][0]["id"] for entry in (
            loadouts[1]["specific_items"][key][0],
            loadouts[2]["specific_items"][key][0],
        )] == [70, 71]
        # The original Army payload is retained, including its exact extra variants.
        assert [loadout[key] for loadout in result["armies"][0]["loadouts"]] == [
            loadout[key] for loadout in original["armies"][0]["loadouts"]
        ]


def test_missing_or_differently_quantified_items_do_not_gain_shared_bases() -> None:
    unit = fixture_loadouts(
        {"weapons": [item(33)], "equipment": [item(34, quantity=1)]},
        {"weapons": [], "equipment": [item(34, extra=91, quantity=2)]},
    )
    result = enrich_unit_presentation(unit, source_skill_classifications=())
    general = result["general_profiles"][0]["shared_items"]
    assert general["weapons"] == []
    assert general["equipment"] == []
    for loadout in result["armies"][0]["loadouts"]:
        assert loadout["specific_items"]["weapons"] == loadout["weapons"]
        assert loadout["specific_items"]["equipment"] == loadout["equipment"]


def test_exact_shared_extras_remain_shared_without_inventing_a_base() -> None:
    unit = fixture_loadouts(
        {"weapons": [item(44, extra=90)]},
        {"weapons": [item(44, extra=90)]},
    )
    result = enrich_unit_presentation(unit, source_skill_classifications=())
    shared = result["general_profiles"][0]["shared_items"]["weapons"]
    assert len(shared) == 1
    assert [extra["id"] for extra in shared[0]["extras"]] == [90]
    assert all(
        not loadout["specific_items"]["weapons"]
        for loadout in result["armies"][0]["loadouts"]
    )


def test_identical_multiple_extra_variants_do_not_add_an_unnecessary_plain_base() -> None:
    same = {"weapons": [item(45, extra=90), item(45, extra=91)]}
    unit = fixture_loadouts(same, deepcopy(same))
    result = enrich_unit_presentation(unit, source_skill_classifications=())
    shared = result["general_profiles"][0]["shared_items"]["weapons"]
    assert sorted(entry["extras"][0]["id"] for entry in shared) == [90, 91]
    assert all(entry["extras"] for entry in shared)


def test_harbingers_breaker_pistol_variant_is_presented_in_general_profile() -> None:
    unit = Database(DATABASE).get_unit(1876)
    assert unit is not None
    result = enrich_unit_presentation(unit)
    shared = [
        weapon
        for general in result["general_profiles"]
        for weapon in general["shared_items"]["weapons"]
        if weapon["name"] == "Breaker Pistol"
    ]
    assert shared, "Harbingers' common Breaker Pistol is missing from General"
    assert any(not weapon["extras"] for weapon in shared)
    for army in result["armies"]:
        for loadout in army["loadouts"]:
            if any(weapon["name"] == "Breaker Pistol" and not weapon["extras"]
                   for weapon in loadout["weapons"]):
                assert not any(
                    weapon["name"] == "Breaker Pistol" and not weapon["extras"]
                    for weapon in loadout["specific_items"]["weapons"]
                )
