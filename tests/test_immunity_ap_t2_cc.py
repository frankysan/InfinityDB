"""Exact AP+T2 CC Weapon / Immunity (AP) source and publication review.

AP halving is ignored, but a failed T2 hit Saving Roll still causes two
Wounds and a failed additional Critical Saving Roll causes only one.
Neither failure is inferred at runtime.
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
    "sourceAmmunitionId": 40,
    "sourceAmmunitionName": "AP+T2",
    "components": ["ammunition:ap", "ammunition:t2"],
    "when": {
        "immunity": "AP", "savingAttribute": "ARM",
        "attackClass": "non-comms", "weaponId": "weapon:ap-t2-cc-weapon",
    },
    "withoutImmunity": {
        "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "ARM/2",
    },
    "withImmunity": {
        "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "ARM",
        "treatedAs": "ammunition:t2",
        "ignoredComponents": ["ammunition:ap"],
        "remainingComponents": ["ammunition:t2"],
        "failedRollWounds": {"hit": 2, "criticalAdditionalRoll": 1},
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_pinned_n53_t2_critical_is_separate_from_hit_wounds() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        pages = {}
        for number in (63, 67, 95, 96, 177):
            raw = pdf[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split())
    for number, clauses in {
        63: ("armor-piercing (ap)", "half his arm or bts"),
        67: ("t2 ammunition", "inflicts 2 wounds",
             "only 1 additional wound", "before performing the saving rolls",
             "combined ammunition works as a single ammunition"),
        95: ("immunity", "ammunition listed between brackets",
             "number of the saving rolls are ignored", "comms attacks"),
        96: ("additional saving roll", "immunity (critical)"),
        177: ("ap+t2 cc", "arm/2", "anti-materiel", "cc."),
    }.items():
        assert all(clause in pages[number] for clause in clauses), number
    document = load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    assert EXPECTED in records["skill:immunity"]["facts"][
        "immunityInteraction"
    ]["reviewedCombinedCases"]
    t2 = records["ammunition:t2"]
    assert t2["facts"]["ammunitionResolution"]["woundsPerFailedSave"] == {
        "hit": 2, "criticalAdditionalRoll": 1,
    }
    assert {citation["page"] for citation in t2["citations"]
            if citation["sourceId"] == "n5-core-v5.3-pdf"} == {67}


def test_reviewed_ap_t2_weapon_identity_and_profile_are_source_preserved() -> None:
    mapping = load_ammunition_reference_map()[40]
    assert mapping["name"] == "AP+T2"
    assert mapping["components"] == EXPECTED["components"]
    weapon = Database(ARMY).get_catalog_item("weapons", "ap-t2-cc-weapon")
    assert weapon is not None
    profiles = weapon.get("profiles", []) + [
        p for v in weapon.get("weapon_variants", []) for p in v.get("profiles", [])
    ]
    matching = [p for p in profiles if p.get("ammunition_source_id") == 40]
    assert matching
    for profile in matching:
        assert profile["ammunition"] == "AP+T2"
        assert profile["saving"] == "ARM/2"
        assert profile["saving_num"] == "1"
        assert "Anti-materiel" in profile["traits"]
        assert "CC" in profile["traits"]


def test_reviewed_ap_t2_immunity_is_not_an_inferred_weapon_api_result() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert EXPECTED in immunity["facts"]["immunityInteraction"][
        "reviewedCombinedCases"
    ]
    t2 = rules.composed_record("ammunition:t2")
    assert t2 is not None
    assert t2["facts"]["ammunitionResolution"]["woundsPerFailedSave"] == (
        EXPECTED["withImmunity"]["failedRollWounds"]
    )
    app = create_app(ARMY, rules_database_path=RULES)

    def get(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        payload = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        return json.loads(payload)

    assert EXPECTED in get("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedCombinedCases"]
    weapon = get("/api/weapons/ap-t2-cc-weapon")
    profiles = weapon.get("profiles", []) + [
        p for v in weapon.get("weapon_variants", []) for p in v.get("profiles", [])
    ]
    matching = [p for p in profiles if p.get("ammunition_source_id") == 40]
    assert matching
    for profile in matching:
        assert profile["saving"] == "ARM/2"
        assert profile["saving_num"] == "1"
        assert "immunity_result" not in profile
        assert "immunityInteraction" not in profile
        assert [part["record_id"] for part in
                profile["ammunition_composition"]["components"]] == EXPECTED["components"]
