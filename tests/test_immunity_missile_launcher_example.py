"""N5.3 p. 96 Example 1: Missile Launcher Blast EXP versus Immunity (ARM).

This printed example is source-scoped to Blast Mode. The separate Hit Mode
uses AP+EXP and ARM/2 and is not reinterpreted by this reference.
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
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
EXPECTED = {
    "when": {
        "weaponId": "weapon:missile-launcher",
        "mode": "Blast Mode",
        "immunity": "ARM",
        "savingAttribute": "ARM",
        "attackClass": "non-comms",
    },
    "sourceProfile": {
        "ammunitionId": "ammunition:exp",
        "savingRoll": "ARM",
        "hitRolls": 3,
        "traits": ["trait:anti-materiel", "trait:impact-template"],
    },
    "withImmunity": {
        "savingAttribute": "ARM",
        "hitRolls": 1,
        "criticalRolls": 2,
        "treatedAs": "ammunition:normal",
    },
    "evidence": "explicit-n5.3-pdf-p96-example-1",
}


def test_printed_missile_launcher_immunity_example_matches_pinned_pdf() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        text_by_page = {}
        for number in (95, 96, 187):
            raw = pdf[number - 1].get_text("text")
            assert isinstance(raw, str)
            text_by_page[number] = " ".join(raw.casefold().split())
    assert all(phrase in text_by_page[96] for phrase in (
        "example 1", "immunity (arm)", "missile launcher",
        "three saving rolls", "exp ammunition", "only make one saving roll",
    ))
    assert all(phrase in text_by_page[187] for phrase in (
        "missile launcher", "blast mode", "hit mode",
        "ap+exp", "arm/2", "impact", "anti-materiel",
    ))
    assert "immunity" in text_by_page[95] and "comms attacks" in text_by_page[95]
    records = load_curated_document(ROOT / "data/curated/rules/n5-core-v5.3.json")[
        "records"
    ]
    immunity = next(record for record in records if record["id"] == "skill:immunity")
    assert EXPECTED == immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"][2]
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 96} in immunity["citations"]


def test_missile_launcher_source_modes_remain_separate() -> None:
    item = Database(ARMY).get_catalog_item("weapons", "missile-launcher")
    assert item is not None
    profiles = item.get("profiles", []) + [
        p for v in item.get("weapon_variants", []) for p in v.get("profiles", [])
    ]
    blast = [p for p in profiles if p.get("mode") == "Blast Mode"]
    hit = [p for p in profiles if p.get("mode") == "Hit Mode"]
    assert blast and hit
    for p in blast:
        assert (p["ammunition"], p["saving"], p["saving_num"]) == ("Exp", "ARM", "3")
        assert any("Impact Template" in trait for trait in p["traits"])
        assert "Anti-materiel" in p["traits"]
    for p in hit:
        assert (p["ammunition"], p["saving"], p["saving_num"]) == (
            "AP+Exp", "ARM/2", "3",
        )
        assert "Anti-materiel" in p["traits"]
        assert not any("Impact Template" in trait for trait in p["traits"])


def test_missile_immunity_reaches_skill_api_without_modifying_weapon() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"][2] == EXPECTED
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

    assert EXPECTED in fetch("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedWeaponCases"]
    item = fetch("/api/weapons/missile-launcher")
    profiles = item.get("profiles", []) + [
        p for v in item.get("weapon_variants", []) for p in v.get("profiles", [])
    ]
    assert {p["mode"] for p in profiles} >= {"Blast Mode", "Hit Mode"}
    for p in profiles:
        assert "immunity_result" not in p
        assert "immunityInteraction" not in p
        if p["mode"] == "Blast Mode":
            assert (p["ammunition"], p["saving"], p["saving_num"]) == (
                "Exp", "ARM", "3",
            )
        elif p["mode"] == "Hit Mode":
            assert (p["ammunition"], p["saving"], p["saving_num"]) == (
                "AP+Exp", "ARM/2", "3",
            )
