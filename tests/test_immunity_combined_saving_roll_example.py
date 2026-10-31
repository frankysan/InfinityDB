"""Pinned N5.3 Immunity Example 3 is a Combined Saving Roll, not Ammunition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_combined_saving_rolls import WeaponCombinedSavingRolls
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"


def reviewed_case() -> dict:
    records = load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]
    immunity = next(record for record in records if record["id"] == "skill:immunity")
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 96} in immunity["citations"]
    return immunity["facts"]["immunityInteraction"]["reviewedSavingRollCases"][0]


def test_printed_plasma_immunity_example_has_independent_n53_evidence() -> None:
    fitz = pytest.importorskip("fitz")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with fitz.open(PDF) as source:
        page = " ".join(source[95].get_text("text").split()).casefold()
    for phrase in (
        "example 3", "immunity (enhanced)", "plasma rifle",
        "normal ammunition", "saving roll against arm", "saving roll against bts",
    ):
        assert phrase in page
    case = reviewed_case()
    assert case == {
        "when": {
            "weaponId": "weapon:plasma-rifle",
            "immunity": "Enhanced",
            "ammunitionId": "ammunition:normal",
        },
        "savingRolls": [
            {"attribute": "ARM", "count": 1},
            {"attribute": "BTS", "count": 1},
        ],
        "result": "combined-saving-roll-preserved",
        "evidence": "explicit-n5.3-pdf-p96-example-3",
    }


def test_plasma_immunity_case_matches_weapon_metadata_and_stays_distinct() -> None:
    army = Database(ARMY)
    resolver = WeaponCombinedSavingRolls()
    plasma = army.get_catalog_item("weapons", "plasma-rifle")
    assert plasma is not None
    case = reviewed_case()
    for profile in plasma["profiles"]:
        combined = resolver.for_profile(profile)
        assert combined is not None
        assert combined["kind"] == "combined-saving-roll"
        assert combined["rolls"] == case["savingRolls"]
        assert profile["ammunition"] == "N"
        assert profile["ammunition_source_id"] == 2
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedSavingRollCases"][0] == case
    assert len(immunity["facts"]["immunityInteraction"]["reviewedSavingRollCases"]) == 2
    normal = rules.composed_record("ammunition:normal")
    assert normal is not None
    assert "ammunition_composition" not in case
    assert "reviewedCombinedCases" not in case


def test_plasma_case_reaches_immunity_api_but_not_weapon_attack_results() -> None:
    app = create_app(ARMY, rules_database_path=RULES)

    def detail(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        payload = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        return json.loads(payload)

    case = reviewed_case()
    assert detail("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedSavingRollCases"][0] == case
    weapon = detail("/api/weapons/plasma-rifle")
    for profile in weapon["profiles"]:
        assert "immunity_result" not in profile
        assert "ammunition_composition" not in profile
        assert profile["combined_saving_roll"]["rolls"] == case["savingRolls"]
