"""Source-scoped AP Immunity versus Silenced Pistol's AP+Shock/BTS profile.

This exact partial-component result is not a combat resolver. Shock's
conditional VITA=1 failed-save effect and Silent Trait remain independent.
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
    "sourceAmmunitionId": 30,
    "sourceAmmunitionName": "AP+Shock",
    "components": ["ammunition:ap", "ammunition:shock"],
    "when": {
        "immunity": "AP", "savingAttribute": "BTS",
        "attackClass": "non-comms", "weaponId": "weapon:silenced-pistol",
    },
    "withoutImmunity": {
        "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS/2",
    },
    "withImmunity": {
        "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS",
        "treatedAs": "ammunition:shock",
        "ignoredComponents": ["ammunition:ap"],
        "remainingComponents": ["ammunition:shock"],
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_n53_ap_shock_bts_and_silent_evidence() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        pages = {}
        for number in (63, 65, 67, 95, 96, 175, 182):
            raw = pdf[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split())
    for number, fragments in {
        63: ("armor-piercing (ap)", "arm or bts", "rounding up"),
        65: ("shock ammunition", "vita attribute", "dead state"),
        67: ("combined ammunition", "additional saving roll"),
        95: ("immunity", "ammunition", "comms attacks"),
        96: ("additional saving roll",),
        175: ("silent (x)", "face to face dodge"),
        182: ("silenced pistol", "ap+shock", "bts/2", "silent (-6)"),
    }.items():
        assert all(token in pages[number] for token in fragments), number
    records = {row["id"]: row for row in load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]}
    assert EXPECTED in records["skill:immunity"]["facts"][
        "immunityInteraction"
    ]["reviewedCombinedCases"]
    assert {c["page"] for c in records["weapon:silenced-pistol"]["citations"]
            if c["sourceId"] == "n5-core-v5.3-pdf"} >= {67, 175, 182}
    shock = records["ammunition:shock"]["facts"]["ammunitionResolution"]
    assert any(state.get("targetAttribute") == {"name": "VITA", "equals": 1}
               for state in shock.get("stateEffects", []))


def test_silenced_pistol_source_and_rule_ids_remain_distinct() -> None:
    ammo = load_ammunition_reference_map()[30]
    assert ammo["name"] == "AP+Shock"
    assert ammo["components"] == EXPECTED["components"]
    raw = Database(ARMY).get_catalog_item("weapons", "silenced-pistol")
    assert raw is not None
    profiles = raw.get("profiles", []) + [
        profile for variant in raw.get("weapon_variants", [])
        for profile in variant.get("profiles", [])
    ]
    matched = [p for p in profiles if p.get("ammunition_source_id") == 30]
    assert matched
    assert all(p.get("saving") == "BTS/2" and p.get("saving_num") == "1"
               for p in matched)
    assert any("Silent" in json.dumps(p) for p in matched) or "Silent" in json.dumps(raw)


def test_published_partial_immunity_is_not_weapon_profile_calculation() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert EXPECTED in immunity["facts"]["immunityInteraction"][
        "reviewedCombinedCases"
    ]
    weapon = rules.composed_record("weapon:silenced-pistol")
    assert weapon is not None
    assert {relation["record_id"] for relation in weapon["relations"]} >= {
        "ammunition:ap", "ammunition:shock", "trait:silent-x",
    }
    app = create_app(ARMY, rules_database_path=RULES)

    def get(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def response(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        data = b"".join(app(environ, response))
        assert statuses == ["200 OK"]
        return json.loads(data)

    assert EXPECTED in get("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedCombinedCases"]
    published = get("/api/weapons/silenced-pistol")
    profiles = published.get("profiles", []) + [
        p for variant in published.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    matched = [p for p in profiles if p.get("ammunition_source_id") == 30]
    assert matched
    assert all(
        p["saving"] == "BTS/2" and p["saving_num"] == "1"
        and "immunity_result" not in p
        for p in matched
    )
