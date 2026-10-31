"""Exact AP+DA CC Weapon Immunity (Critical) precedence, N5.3 pp. 67, 95, 177.

DA's two Saving Rolls and AP's halved ARM remain. Only the
Critical-added third roll is removed, without modifying Army profiles.
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
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
EXPECTED = {
    "when": {
        "weaponId": "weapon:ap-da-cc-weapon",
        "sourceAmmunitionId": 10,
        "immunity": "Critical",
        "attackClass": "non-comms",
    },
    "components": ["ammunition:ap", "ammunition:da"],
    "criticalWithoutImmunity": {
        "savingAttribute": "ARM/2",
        "hitRolls": 2,
        "criticalRolls": 3,
    },
    "criticalWithImmunity": {
        "savingAttribute": "ARM/2",
        "hitRolls": 2,
        "criticalRolls": 2,
        "additionalCriticalRollRemoved": True,
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_ap_da_cc_critical_is_independently_supported_by_n53() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        sections = {}
        for number in (67, 95, 177):
            value = pdf[number - 1].get_text("text")
            assert isinstance(value, str)
            sections[number] = " ".join(value.casefold().split())
    checks = {
        67: (
            "a critical with ap+da ammunition",
            "three saving rolls",
            "two due to the da ammunition and one due to the critical",
        ),
        95: (
            "immunity (critical)", "additional saving",
            "roll caused by critical hits", "comms attacks",
        ),
        177: ("ap+da cc", "arm/2", "anti-materiel", "cc."),
    }
    assert all(term in sections[page] for page, terms in checks.items()
               for term in terms)
    records = load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]
    immunity = next(row for row in records if row["id"] == "skill:immunity")
    assert immunity["facts"]["immunityInteraction"]["reviewedCriticalCases"][1] == EXPECTED
    assert {citation["page"] for citation in immunity["citations"]
            if citation["sourceId"] == "n5-core-v5.3-pdf"} >= {95, 96}


def test_ap_da_cc_preserves_army_weapon_profile_and_components() -> None:
    source = load_ammunition_reference_map()[10]
    assert source["name"] == "AP+DA"
    assert source["components"] == EXPECTED["components"]
    raw = Database(ARMY).get_catalog_item("weapons", "ap-da-cc-weapon")
    assert raw is not None
    profiles = raw.get("profiles", []) + [
        profile for variant in raw.get("weapon_variants", [])
        for profile in variant.get("profiles", [])
    ]
    matches = [profile for profile in profiles
               if profile.get("ammunition_source_id") == 10]
    assert matches
    assert all(
        (profile["ammunition"], profile["saving"], profile["saving_num"])
        == ("AP+DA", "ARM/2", "2")
        and "Anti-materiel" in profile["traits"]
        and "CC" in profile["traits"]
        and not any("Comms Attack" in trait for trait in profile["traits"])
        for profile in matches
    )


def test_ap_da_cc_critical_reference_api_does_not_calculate_weapon_results() -> None:
    db = RulesDatabase(RULES)
    immunity = db.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedCriticalCases"][1] == EXPECTED
    app = create_app(ARMY, rules_database_path=RULES)

    def fetch(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        results: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            results.append(status)

        data = b"".join(app(environ, respond))
        assert results == ["200 OK"]
        return json.loads(data)

    facts = fetch("/api/skills/immunity")["rules"][0]["facts"]["immunityInteraction"]
    assert facts["reviewedCriticalCases"][1] == EXPECTED
    assert facts["reviewedCriticalCases"][0]["when"]["weaponId"] == (
        "weapon:ap-t2-cc-weapon"
    )
    weapon = fetch("/api/weapons/ap-da-cc-weapon")
    profiles = weapon.get("profiles", []) + [
        profile for variant in weapon.get("weapon_variants", [])
        for profile in variant.get("profiles", [])
    ]
    assert any(profile.get("ammunition_source_id") == 10 for profile in profiles)
    assert all(
        profile["saving"] == "ARM/2" and profile["saving_num"] == "2"
        and "immunity_result" not in profile
        and "immunityInteraction" not in profile
        for profile in profiles if profile.get("ammunition_source_id") == 10
    )
