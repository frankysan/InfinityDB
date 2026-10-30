"""Standalone E/Mitter / Immunity (BTS) is a non-Comms, Non-Lethal case.

N5.3 pp. 64, 95-96, 186 support only the standalone E/Mitter (Army 25).
The Armed Turret's separately imported one-roll E/Mitter mode is unresolved,
so neither that Weapon nor arbitrary E/M Comms attacks receive this outcome.
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
        "weaponId": "weapon:e-mitter", "sourceWeaponId": 25,
        "sourceAmmunitionId": 14, "immunity": "BTS",
        "savingAttribute": "BTS", "attackClass": "non-comms",
    },
    "ammunitionTreatedAs": "ammunition:normal",
    "survivingTraits": ["trait:non-lethal"],
    "withoutImmunity": {
        "hitRolls": 2, "criticalRolls": 3, "savingAttribute": "BTS/2",
    },
    "withImmunity": {
        "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS",
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_pinned_n53_emitter_trait_and_immunity_clauses() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        pages = {}
        for page in (64, 95, 96, 186):
            raw = pdf[page - 1].get_text("text")
            assert isinstance(raw, str)
            pages[page] = " ".join(raw.casefold().split())
    assert all(token in pages[64] for token in (
        "electromagnetic", "two saving rolls per hit suffered", "bts/2",
        "isolated state", "immobilized-b",
    ))
    assert all(token in pages[95] for token in (
        "immunity", "bts attribute is treated as normal",
        "comms attacks", "non-lethal",
    ))
    assert "additional saving roll" in pages[96]
    assert all(token in pages[186] for token in (
        "e/mitter", "non-lethal", "bts/2", "e/m",
    ))
    curated = load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in curated["records"]}
    assert records["skill:immunity"]["facts"]["immunityInteraction"][
        "reviewedWeaponCases"
    ][1] == EXPECTED
    assert {c["page"] for c in records["weapon:e-mitter"]["citations"]
            if c["sourceId"] == "n5-core-v5.3-pdf"} == {186}


def test_standalone_source_profile_and_separate_turret_discrepancy() -> None:
    db = Database(ARMY)
    emitter = db.get_catalog_item("weapons", "e-mitter")
    assert emitter is not None
    assert emitter["id"] == 25
    matched = [
        p for p in emitter.get("profiles", [])
        if p["ammunition_source_id"] == 14
    ]
    assert matched
    assert all(p["ammunition"] == "E/M"
               and p["saving"] == "BTS/2"
               and p["saving_num"] == "2" for p in matched)
    turret = db.get_catalog_item("weapons", "armed-turret")
    assert turret is not None
    turret_modes = [
        p for p in turret.get("profiles", []) +
        [item for v in turret.get("weapon_variants", [])
         for item in v.get("profiles", [])]
        if p.get("mode") == "E/Mitter"
    ]
    assert turret_modes and any(p.get("saving_num") == "1" for p in turret_modes)


def test_published_immunity_example_does_not_rewrite_emitter_profiles() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"][1] == EXPECTED
    weapon = rules.composed_record("weapon:e-mitter")
    assert weapon is not None
    assert {r["record_id"] for r in weapon["relations"]} >= {
        "ammunition:em", "trait:non-lethal",
    }

    app = create_app(ARMY, rules_database_path=RULES)
    def response(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)
        data = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        return json.loads(data)

    assert EXPECTED in response("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedWeaponCases"]
    for slug, expected in (("e-mitter", "2"), ("armed-turret", "1")):
        item = response(f"/api/weapons/{slug}")
        profiles = item.get("profiles", []) + [
            p for v in item.get("weapon_variants", [])
            for p in v.get("profiles", [])
        ]
        matched = [
            p for p in profiles
            if p.get("ammunition_source_id") == 14
            and (slug == "e-mitter" or p.get("mode") == "E/Mitter")
        ]
        assert matched
        assert any(p["saving_num"] == expected for p in matched)
        assert all(
            "immunity_result" not in p and "immunityInteraction" not in p
            for p in matched
        )
