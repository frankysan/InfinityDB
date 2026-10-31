"""N5.3 Combined Saving Roll + Immunity (Critical), exact Plasma Rifle case.

The original ARM+BTS hit requires both rolls. A Critical adds one ARM
roll (p. 67), which Immunity (Critical) alone removes (p. 95).
This is a reviewed reference, not a general attack evaluator.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pymupdf

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
EXPECTED = {
    "when": {
        "weaponId": "weapon:plasma-rifle",
        "immunity": "Critical",
        "attackClass": "non-comms",
        "ammunitionId": "ammunition:normal",
    },
    "criticalWithoutImmunity": [
        {"attribute": "ARM", "count": 2},
        {"attribute": "BTS", "count": 1},
    ],
    "criticalWithImmunity": [
        {"attribute": "ARM", "count": 1},
        {"attribute": "BTS", "count": 1},
    ],
    "removedCriticalRoll": {"attribute": "ARM", "count": 1},
    "result": "critical-extra-arm-roll-removed",
    "evidence": "derived-from-pinned-general-rules",
}


def test_pinned_critical_sources_support_plasma_attribute_distinction() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        pages: dict[int, str] = {}
        for number in (67, 95, 96):
            raw = pdf[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split())
    assert all(fragment in pages[67] for fragment in (
        "combined saving roll", "additional saving roll against the arm attribute",
        "two saving rolls against the arm attribute and one against the",
        "bts attribute",
    ))
    assert all(fragment in pages[95] for fragment in (
        "immunity", "immunity (critical)", "additional saving",
        "roll caused by critical hits", "comms attacks",
    ))
    assert all(fragment in pages[96] for fragment in (
        "example 3", "plasma rifle", "immunity (enhanced)",
        "saving roll against arm", "saving roll against bts",
    ))
    records = {r["id"]: r for r in load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]}
    immunity = records["skill:immunity"]
    assert EXPECTED == immunity["facts"]["immunityInteraction"][
        "reviewedSavingRollCases"
    ][1]
    assert {c["page"] for c in immunity["citations"]
            if c["sourceId"] == "n5-core-v5.3-pdf"} >= {95, 96}


def test_plasma_critical_review_matches_actual_army_profile_mapping() -> None:
    weapon = Database(ARMY).get_catalog_item("weapons", "plasma-rifle")
    assert weapon is not None
    resolver = WeaponCombinedSavingRolls()
    profiles = weapon["profiles"] + [
        p for v in weapon.get("weapon_variants", [])
        for p in v.get("profiles", [])
    ]
    assert profiles
    for profile in profiles:
        annotation = resolver.for_profile(profile)
        assert annotation is not None
        assert annotation["rolls"] == EXPECTED["criticalWithImmunity"]
        assert annotation["critical"] == {"additionalRolls": 1, "attribute": "ARM"}
        assert profile["ammunition"] == "N"
        assert profile["ammunition_source_id"] == 2


def test_critical_immunity_reference_is_public_but_weapon_stays_unresolved() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedSavingRollCases"][1] == EXPECTED
    app = create_app(ARMY, rules_database_path=RULES)

    def fetch(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        data = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        return json.loads(data)

    actual = fetch("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedSavingRollCases"]
    assert len(actual) == 2
    assert actual[1] == EXPECTED
    published = fetch("/api/weapons/plasma-rifle")
    profiles = published.get("profiles", []) + [
        p for v in published.get("weapon_variants", []) for p in v.get("profiles", [])
    ]
    assert profiles
    for profile in profiles:
        assert "immunity_result" not in profile
        assert "immunityInteraction" not in profile
        assert "ammunition_composition" not in profile
        assert profile["combined_saving_roll"]["rolls"] == EXPECTED[
            "criticalWithImmunity"
        ]
        assert profile["combined_saving_roll"]["critical"] == {
            "additionalRolls": 1, "attribute": "ARM",
        }
