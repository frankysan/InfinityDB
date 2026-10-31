"""N5.3 source-closed Immunity (BTS) vs N+E/M E/M CC Weapon review.

This derived example is *only* a non-Comms E/M CC Weapon attack.
Other E/M profiles, Comms Attacks, and target-immunity calculations are not inferred.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PDF_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"

EXPECTED = {
    "sourceAmmunitionId": 5,
    "sourceAmmunitionName": "N+E/M",
    "components": ["ammunition:normal", "ammunition:em"],
    "when": {
        "immunity": "BTS",
        "savingAttribute": "BTS",
        "attackClass": "non-comms",
        "weaponId": "weapon:e-m-cc-weapon",
    },
    "withoutImmunity": {"hitRolls": 2, "criticalRolls": 3},
    "withImmunity": {
        "hitRolls": 1, "criticalRolls": 2,
        "treatedAs": "ammunition:normal",
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_pinned_n53_rules_support_exact_non_comms_em_cc_case() -> None:
    fitz = pytest.importorskip("pymupdf")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PDF_SHA256
    with fitz.open(PDF) as source:
        pages = {
            number: " ".join(source[number - 1].get_text("text").casefold().split())
            for number in (64, 67, 95, 96, 177)
        }
    for phrase in (
        "two saving rolls per hit suffered, using half his bts",
        "if the target fails a saving roll and is heavy infantry",
    ):
        assert phrase in pages[64]
    for phrase in (
        "an impact with n+e/m ammunition forces the target",
        "two saving rolls (due to the e/m ammunition)",
        "critical with n+e/m ammunition",
        "three saving rolls with the bts attribute halved",
    ):
        assert phrase in pages[67]
    for phrase in (
        "immunity", "any ammunition that requires a saving roll using",
        "bts attribute is treated as normal", "does not apply against comms attacks",
    ):
        assert phrase in pages[95]
    assert "additional saving roll" in pages[96]
    assert "e/m cc weapon" in pages[177]
    assert "n+e/m" in pages[177]
    assert "bts/2" in pages[177]
    assert "cc, [**]" in pages[177]
    assert "comms attack" not in pages[177].split("e/m cc weapon", 1)[1].split(
        "exp cc weapon", 1
    )[0]


def test_bts_case_has_exact_army_weapon_and_ammunition_provenance() -> None:
    source = load_ammunition_reference_map()[5]
    assert source["name"] == "N+E/M"
    assert source["components"] == EXPECTED["components"]
    weapon = Database(ARMY).get_catalog_item("weapons", "e-m-cc-weapon")
    assert weapon is not None
    profiles = weapon["profiles"] + [
        p for variant in weapon.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    matched = [p for p in profiles if p.get("ammunition_source_id") == 5]
    assert matched
    for profile in matched:
        assert profile["ammunition"] == "N+E/M"
        assert profile["saving"] == "BTS/2"
        assert profile["saving_num"] == "2"

    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    cc = rules.composed_record("weapon:e-m-cc-weapon")
    assert immunity is not None and cc is not None
    assert EXPECTED in immunity["facts"]["immunityInteraction"]["reviewedCombinedCases"]
    assert {(citation["source_id"], citation.get("page")) for citation
            in cc["citations"]} >= {
        ("n5-core-v5.3-pdf", 67), ("n5-core-v5.3-pdf", 177),
    }
    assert {x["record_id"] for x in cc["relations"]} >= {
        "ammunition:normal", "ammunition:em",
    }


def test_reviewed_bts_case_reaches_skill_api_not_derived_weapon_profile() -> None:
    app = create_app(ARMY, rules_database_path=RULES)

    def fetch(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []
        def start(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)
        content = b"".join(app(environ, start))
        assert statuses == ["200 OK"]
        return json.loads(content)

    skill = fetch("/api/skills/immunity")
    assert EXPECTED in skill["rules"][0]["facts"]["immunityInteraction"][
        "reviewedCombinedCases"
    ]
    weapon = fetch("/api/weapons/e-m-cc-weapon")
    profiles = weapon["profiles"] + [
        p for variant in weapon.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    matched = [p for p in profiles if p.get("ammunition_source_id") == 5]
    assert matched
    for profile in matched:
        assert "immunity_result" not in profile
        assert "immunityInteraction" not in profile
        assert profile["saving"] == "BTS/2"
        assert profile["saving_num"] == "2"
        assert [part["record_id"] for part in
                profile["ammunition_composition"]["components"]] == EXPECTED["components"]
