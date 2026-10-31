"""N5.3 E/M Grenade Launcher / Immunity (BTS), exact non-Comms source case.

E/M effects (Isolated and conditional Immobilized-B) are ignored; Non-Lethal
is an explicit Immunity exception. Template and Speculative Attack mechanics
are independent of this reviewed Saving Roll reference.
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
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
EXPECTED = {
    "when": {
        "weaponId": "weapon:e-m-grenade-launcher",
        "sourceAmmunitionId": 14,
        "immunity": "BTS",
        "savingAttribute": "BTS",
        "attackClass": "non-comms",
    },
    "ammunitionTreatedAs": "ammunition:normal",
    "survivingTraits": ["trait:non-lethal"],
    "sourceProfileTraits": ["trait:impact-template", "trait:speculative-attack"],
    "withoutImmunity": {
        "hitRolls": 2, "criticalRolls": 3, "savingAttribute": "BTS/2",
    },
    "withImmunity": {
        "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS",
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_grenade_em_immunity_derived_from_exact_pinned_rule_and_chart() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as document:
        pages: dict[int, str] = {}
        for number in (64, 95, 96, 179):
            raw = document[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split())
    for number, fragments in {
        64: ("electromagnetic (e/m) ammunition", "two saving rolls per hit",
             "bts/2", "isolated state", "immobilized-b"),
        95: ("immunity (bts)", "non-lethal and state:", "comms attacks",
             "treated as normal"),
        96: ("immunity and critical hits", "additional saving roll"),
        179: ("e/m grenade", "non-", "lethal", "speculative attack",
              "impact template", "bts/2"),
    }.items():
        assert all(fragment in pages[number] for fragment in fragments), number
    source = load_curated_document(ROOT / "data/curated/rules/n5-core-v5.3.json")
    records = {record["id"]: record for record in source["records"]}
    assert records["skill:immunity"]["facts"]["immunityInteraction"][
        "reviewedWeaponCases"
    ][4] == EXPECTED
    assert {citation["page"] for citation in records["skill:immunity"]["citations"]
            if citation["sourceId"] == "n5-core-v5.3-pdf"} >= {95, 96}


def test_grenade_em_army_source_profile_stays_non_comms_and_non_lethal() -> None:
    source = Database(ARMY).get_catalog_item("weapons", "e-m-grenade-launcher")
    assert source is not None
    profiles = source.get("profiles", []) + [
        profile for variant in source.get("weapon_variants", [])
        for profile in variant.get("profiles", [])
    ]
    matched = [p for p in profiles if p.get("ammunition_source_id") == 14]
    assert matched
    for profile in matched:
        assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
            "E/M", "BTS/2", "2",
        )
        assert "non-lethal" in [trait.casefold() for trait in profile["traits"]]
        assert any("Impact Template" in trait for trait in profile["traits"])
        assert "Speculative Attack" in profile["traits"]
        assert "Comms Attack" not in profile["traits"]


def test_grenade_em_immunity_api_preserves_weapon_fields() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"][4] == EXPECTED
    app = create_app(ARMY, rules_database_path=RULES)

    def fetch(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        results: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            results.append(status)

        payload = b"".join(app(environ, respond))
        assert results == ["200 OK"]
        return json.loads(payload)

    assert EXPECTED in fetch("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedWeaponCases"]
    weapon = fetch("/api/weapons/e-m-grenade-launcher")
    profiles = weapon.get("profiles", []) + [
        profile for variant in weapon.get("weapon_variants", [])
        for profile in variant.get("profiles", [])
    ]
    matched = [p for p in profiles if p.get("ammunition_source_id") == 14]
    assert matched
    assert all(
        (p["ammunition"], p["saving"], p["saving_num"]) == ("E/M", "BTS/2", "2")
        and "immunity_result" not in p and "immunityInteraction" not in p
        for p in matched
    )
