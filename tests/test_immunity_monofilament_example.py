"""Printed N5.3 p. 96 Monofilament / Immunity (ARM) example.

Unlike combined-ammunition examples, this protects against the Weapon's
ARM=0 and State: Dead Traits while retaining its Normal Ammunition roll.
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
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
EXPECTED = {
    "when": {
        "weaponId": "weapon:monofilament-cc-weapon",
        "immunity": "ARM",
        "savingAttribute": "ARM",
        "attackClass": "non-comms",
    },
    "sourceProfile": {
        "ammunitionId": "ammunition:normal",
        "savingRoll": "ARM=0",
        "hitRolls": 1,
        "traits": ["trait:arm-0", "trait:state"],
        "stateId": "state:dead",
    },
    "withImmunity": {
        "savingAttribute": "ARM",
        "hitRolls": 1,
        "criticalRolls": 2,
        "ignoredTraits": ["trait:arm-0", "trait:state"],
        "stateAppliedOnFailedRoll": False,
    },
    "evidence": "explicit-n5.3-pdf-p96-example-2",
}


def test_monofilament_is_printed_n53_immunity_example_not_inferred() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as document:
        pages: dict[int, str] = {}
        for number in (95, 96, 177):
            raw = document[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split())
    for page, fragments in {
        95: ("immunity (arm)", "state: dead", "arm=0", "comms attacks"),
        96: ("example 2", "monofilament cc weapon", "ignoring the weapon",
             "state: dead traits", "two saving rolls", "dead state is not applied"),
        177: ("monofilament", "arm=0", "state: dead", "cc weapon"),
    }.items():
        assert all(fragment in pages[page] for fragment in fragments), page
    source = load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )
    immunity = next(r for r in source["records"] if r["id"] == "skill:immunity")
    assert EXPECTED == immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"][3]
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 96} in immunity["citations"]


def test_monofilament_source_weapon_and_ammunition_not_retyped() -> None:
    raw = Database(ARMY).get_catalog_item("weapons", "monofilament-cc-weapon")
    assert raw is not None
    assert raw["profiles"]
    for profile in raw["profiles"]:
        assert profile["ammunition"] == "N"
        assert profile["saving"] == "ARM=0"
        assert profile["saving_num"] == "1"
        assert "CC" in profile["traits"]
        assert "State: Dead" in profile["traits"]
        assert "ammunition_composition" not in profile


def test_monofilament_review_reaches_api_without_invented_combat_results() -> None:
    rules = RulesDatabase(RULES)
    record = rules.composed_record("skill:immunity")
    assert record is not None
    assert record["facts"]["immunityInteraction"]["reviewedWeaponCases"][3] == EXPECTED
    app = create_app(ARMY, rules_database_path=RULES)

    def get(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        body = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        return json.loads(body)

    immunity = get("/api/skills/immunity")
    assert EXPECTED in immunity["rules"][0]["facts"]["immunityInteraction"][
        "reviewedWeaponCases"
    ]
    weapon = get("/api/weapons/monofilament-cc-weapon")
    profiles = weapon.get("profiles", []) + [
        p for variant in weapon.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    assert profiles
    for profile in profiles:
        assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
            "N", "ARM=0", "1",
        )
        assert "immunity_result" not in profile
        assert "immunityInteraction" not in profile
