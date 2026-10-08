"""Bounded N5.3 Mine chart/profile and semantic-owner reconciliation.

The mapping is review evidence, not another source of playable weapon profiles.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from test_weaponry_catalog_api import _weapon_detail

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "config/validation/mine-variant-effects.json"


def _review() -> dict[str, Any]:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def weaponry_app() -> Callable:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


@pytest.mark.parametrize("entry", _review()["variants"], ids=lambda entry: entry["slug"])
def test_mine_source_profile_and_effect_owners_remain_distinct(
    weaponry_app: Callable, entry: dict[str, Any]
) -> None:
    payload = _weapon_detail(weaponry_app, entry["slug"])
    assert len(payload["profiles"]) == 1
    profile = payload["profiles"][0]
    for field, expected in entry["profile"].items():
        source_field = "saving_num" if field == "savingNum" else field
        assert profile[source_field] == expected, (entry["slug"], field)
    assert set(entry["requiredSourceTraits"]) <= set(profile["traits"])

    rules = {record["id"] for record in payload["rules"]}
    assert "weapon:mines" in rules
    assert ("weapon:cybermine" in rules) == (entry["slug"] == "cybermine")
    assert "weapon:chest-mine" not in rules

    with sqlite3.connect(ROOT / "data/generated/rules.db") as database:
        available = {
            row[0]
            for row in database.execute("SELECT id FROM records")
        }
    assert set(entry["effectRuleIds"]) <= available


def test_review_scope_and_source_are_explicit() -> None:
    review = _review()
    assert review["formatVersion"] == 1
    family_review = json.loads(
        (ROOT / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf-8"
        )
    )
    assert review["sources"]["corePdfSha256"] == family_review["corePdfSha256"]
    assert review["sources"]["corePdfVersion"] == "5.3"
    assert review["sources"]["weaponChartPrintedPage"] == 181
    assert review["sources"]["mineRulesPrintedPage"] == 72
    assert {entry["slug"] for entry in review["variants"]} == {
        "ap-mine", "e-m-mine", "monofilament-mine", "para-mine",
        "shock-mine", "viral-mine", "cybermine",
    }
    assert len({entry["slug"] for entry in review["variants"]}) == 7
    assert review["unresolved"] == [{
        "slug": "para-mine",
        "issue": (
            "PDF/Wiki p181 use [*] for Weaponry; Army profile uses [**] "
            "for Ammunition. No source string is overwritten."
        ),
    }]

    source = json.loads(
        (ROOT / "data/curated/rules/n5-core-v5.3.json").read_text(
            encoding="utf-8"
        )
    )
    family = next(record for record in source["records"] if record["id"] == "weapon:mines")
    assert {link["id"] for link in family["armyLinks"]} == {
        entry["slug"] for entry in review["variants"]
    }


def test_non_lethal_does_not_erase_mine_saving_rolls(weaponry_app: Callable) -> None:
    """An E/M/PARA/Cybermine is non-lethal but still forces Saving Rolls."""
    for slug, expected_count in (("e-m-mine", "2"), ("para-mine", "1"),
                                 ("cybermine", "2")):
        profile = _weapon_detail(weaponry_app, slug)["profiles"][0]
        assert "Non-lethal" in profile["traits"]
        assert profile["saving_num"] == expected_count
        assert profile["saving"] not in ("", "-", None)

    with sqlite3.connect(ROOT / "data/generated/rules.db") as database:
        summary = database.execute(
            "SELECT summary FROM records WHERE id = ?", ("trait:non-lethal",)
        ).fetchone()[0]
    assert "not by itself remove Saving Rolls" in summary
    assert "or requires Saving Rolls" not in summary


@pytest.mark.parametrize("entry", _review()["variants"], ids=lambda entry: entry["slug"])
def test_mine_effect_rules_are_routable_from_the_weapon_profile(
    weaponry_app: Callable, entry: dict[str, Any]
) -> None:
    payload = _weapon_detail(weaponry_app, entry["slug"])
    profiles = payload["weapon_variants"][0]["profiles"]
    assert len(profiles) == 1
    profile = profiles[0]
    refs = profile["rule_references"]
    ids = [reference["id"] for reference in refs]
    assert len(ids) == len(set(ids))

    # Source-native Traits and the Cybermine card already provide their own links.
    expected = set(entry["effectRuleIds"]) - {"trait:non-lethal", "weapon:cybermine"}
    assert set(ids) == expected
    assert payload["profiles"][0]["rule_references"] == refs
    for reference in refs:
        public = reference["public_reference"]
        assert public.get("href") or (public.get("catalog") and public.get("id"))
        assert reference["kind"] in {"ammunition", "trait", "state", "skill"}

    if entry["profile"]["ammunition"] == 0:
        assert all(reference["kind"] != "ammunition" for reference in refs)
    else:
        assert sum(reference["kind"] == "ammunition" for reference in refs) == 1


def test_chest_mine_does_not_inherit_variant_mine_references(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "chest-mine")
    for profile in payload["weapon_variants"][0]["profiles"]:
        assert "rule_references" not in profile
