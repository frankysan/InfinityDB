"""Source-scoped AP+T2 Critical Immunity retains the hit-roll T2 consequence.

N5.3 pp. 67, 95 and 177: Critical adds one roll, but Immunity (Critical)
removes it; the original ARM/2 hit Saving Roll and T2's two-Wound failure
remain. This is not Immunity (AP) or a general attack evaluator.
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
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
EXPECTED = {
    "when": {
        "weaponId": "weapon:ap-t2-cc-weapon",
        "sourceAmmunitionId": 40,
        "ammunitionId": "ammunition:t2",
        "immunity": "Critical",
        "attackClass": "non-comms",
    },
    "components": ["ammunition:ap", "ammunition:t2"],
    "criticalWithoutImmunity": {
        "savingAttribute": "ARM/2",
        "hitRolls": 1,
        "criticalRolls": 2,
        "failedHitRollWounds": 2,
        "failedAdditionalCriticalRollWounds": 1,
    },
    "criticalWithImmunity": {
        "savingAttribute": "ARM/2",
        "hitRolls": 1,
        "criticalRolls": 1,
        "failedHitRollWounds": 2,
        "additionalCriticalRollRemoved": True,
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_t2_critical_extra_roll_and_arm_halving_are_separately_sourced() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        pages: dict[int, str] = {}
        for number in (63, 67, 95, 177):
            raw = pdf[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split())
    phrases = {
        63: ("armor-piercing (ap)", "arm or bts"),
        67: ("t2 ammunition", "inflicts 2 wounds",
             "only 1 additional wound", "before performing the saving rolls",
             "combined ammunition works as a single ammunition"),
        95: ("immunity (critical)", "additional saving",
             "roll caused by critical hits", "comms attacks"),
        177: ("ap+t2 cc", "arm/2", "anti-materiel", "cc."),
    }
    assert all(phrase in pages[n] for n, terms in phrases.items() for phrase in terms)
    records = {record["id"]: record for record in load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]}
    assert records["skill:immunity"]["facts"]["immunityInteraction"][
        "reviewedCriticalCases"
    ][0] == EXPECTED
    t2 = records["ammunition:t2"]["facts"]["ammunitionResolution"]
    assert t2["woundsPerFailedSave"] == {
        "hit": 2, "criticalAdditionalRoll": 1,
    }
    assert {c["page"] for c in records["skill:immunity"]["citations"]
            if c["sourceId"] == "n5-core-v5.3-pdf"} >= {95, 96}


def test_t2_critical_does_not_rewrite_source_weapon_or_ammunition() -> None:
    ammo = load_ammunition_reference_map()[40]
    assert ammo["name"] == "AP+T2"
    assert ammo["components"] == EXPECTED["components"]
    weapon = Database(ARMY).get_catalog_item("weapons", "ap-t2-cc-weapon")
    assert weapon is not None
    profiles = weapon.get("profiles", []) + [
        p for v in weapon.get("weapon_variants", [])
        for p in v.get("profiles", [])
    ]
    matches = [p for p in profiles if p.get("ammunition_source_id") == 40]
    assert matches
    assert all(
        (p["ammunition"], p["saving"], p["saving_num"]) ==
        ("AP+T2", "ARM/2", "1")
        and "Anti-materiel" in p["traits"] for p in matches
    )


def test_t2_critical_reference_publishes_only_on_immunity_skill() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedCriticalCases"][0] == EXPECTED
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

    facts = get("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]
    assert facts["reviewedCriticalCases"][0] == EXPECTED
    assert len(facts["reviewedCriticalCases"]) == 5
    assert len(facts["reviewedCombinedCases"]) == 9
    assert facts["reviewedCombinedCases"][4]["when"]["immunity"] == "AP"
    weapon = get("/api/weapons/ap-t2-cc-weapon")
    profiles = weapon.get("profiles", []) + [
        p for v in weapon.get("weapon_variants", []) for p in v.get("profiles", [])
    ]
    matching = [p for p in profiles if p.get("ammunition_source_id") == 40]
    assert matching
    assert all(
        p["saving"] == "ARM/2" and p["saving_num"] == "1"
        and "immunity_result" not in p and "immunityInteraction" not in p
        for p in matching
    )
