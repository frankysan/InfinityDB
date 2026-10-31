"""Exact Critical-Immunity examples for the remaining reviewed combined forms.

These source-qualified references remove one Critical-added roll only.
They do not evaluate a target, suppress constituent effects or rewrite Weapons.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pymupdf
import pytest

from infinity_db.curated import load_curated_document
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
EXPECTED = [
    {
        "when": {
            "weaponId": "weapon:ap-exp-cc-weapon", "sourceAmmunitionId": 13,
            "immunity": "Critical", "attackClass": "non-comms",
        },
        "components": ["ammunition:ap", "ammunition:exp"],
        "criticalWithoutImmunity": {
            "savingAttribute": "ARM/2", "hitRolls": 3, "criticalRolls": 4,
        },
        "criticalWithImmunity": {
            "savingAttribute": "ARM/2", "hitRolls": 3, "criticalRolls": 3,
            "additionalCriticalRollRemoved": True,
        },
        "evidence": "derived-from-pinned-general-rules",
    },
    {
        "when": {
            "weaponId": "weapon:silenced-pistol", "sourceAmmunitionId": 30,
            "immunity": "Critical", "attackClass": "non-comms",
        },
        "components": ["ammunition:ap", "ammunition:shock"],
        "criticalWithoutImmunity": {
            "savingAttribute": "BTS/2", "hitRolls": 1, "criticalRolls": 2,
        },
        "criticalWithImmunity": {
            "savingAttribute": "BTS/2", "hitRolls": 1, "criticalRolls": 1,
            "additionalCriticalRollRemoved": True,
        },
        "evidence": "derived-from-pinned-general-rules",
    },
    {
        "when": {
            "weaponId": "weapon:e-m-cc-weapon", "sourceAmmunitionId": 5,
            "immunity": "Critical", "attackClass": "non-comms",
        },
        "components": ["ammunition:normal", "ammunition:em"],
        "criticalWithoutImmunity": {
            "savingAttribute": "BTS/2", "hitRolls": 2, "criticalRolls": 3,
        },
        "criticalWithImmunity": {
            "savingAttribute": "BTS/2", "hitRolls": 2, "criticalRolls": 2,
            "additionalCriticalRollRemoved": True,
        },
        "evidence": "derived-from-pinned-general-rules",
    },
]
# Independent exact Army profile identities, chart rows and source spellings.
PROFILES = [
    (227, "AP+Exp", 177, "ap+exp cc weapon 8 1 ap+exp arm/2 3 anti-materiel, cc."),
    (211, "AP+Shock", 182, "silenced pistol +3 0 -6 8 2 ap+shock bts/2 1 silent (-6)"),
    (7, "N+E/M", 177, "e/m cc weapon 8 1 n+e/m bts/2 2 cc, [**]."),
]


@pytest.mark.parametrize("index", range(3))
def test_remaining_critical_case_matches_pinned_rules_and_exact_weapon(index: int) -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    weapon_id, ammunition_name, page, row = PROFILES[index]
    with pymupdf.open(PDF) as pdf:
        pages = {n: " ".join(str(pdf[n - 1].get_text("text")).casefold().split())
                 for n in (63, 64, 65, 67, 95, page)}
    assert row in pages[page]
    assert "immunity (critical): the trooper will not make the additional saving" in pages[95]
    assert "sole exception of immunity (state)" in pages[95]
    combined = pages[67].split("combined ammunition", 1)[1].split("combined saving roll", 1)[0]
    assert "the additional saving roll will apply the effects" in combined
    if index == 0:
        assert "four saving rolls" in combined and "three due to the exp ammunition" in combined
    elif index == 1:
        assert "vita attribute, with a value of 1" in pages[65]
        assert "passes directly to dead state" in pages[65]
    else:
        assert "any failed saving roll causes the target to enter isolated state" in combined
        assert "heavy infantry (hi), a tag, a remote (rem), or a vehicle" in combined
        assert "two due to the e/m ammunition and one due to the critical" in combined
    case = EXPECTED[index]
    source_id = case["when"]["sourceAmmunitionId"]
    source = load_ammunition_reference_map()[source_id]
    assert (source["name"], source["components"]) == (ammunition_name, case["components"])
    slug = case["when"]["weaponId"].split(":", 1)[1]
    weapon = Database(ARMY).get_catalog_item("weapons", slug)
    assert weapon is not None
    matched = [p for p in weapon["profiles"] if p.get("id") == weapon_id]
    assert matched
    for profile in matched:
        assert profile["ammunition_source_id"] == source_id
        assert profile["ammunition"] == ammunition_name
        assert profile["saving"] == case["criticalWithoutImmunity"]["savingAttribute"]
        assert profile["saving_num"] == str(case["criticalWithoutImmunity"]["hitRolls"])
        assert not any("Comms Attack" in trait for trait in profile["traits"])


@pytest.fixture(scope="module")
def published() -> dict[str, Any]:
    app = create_app(ARMY, rules_database_path=RULES)

    def get(path: str) -> dict[str, Any]:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        result = json.loads(b"".join(app(environ, respond)))
        assert statuses == ["200 OK"]
        return result

    return {"immunity": get("/api/skills/immunity"), "weapons": {
        c["when"]["weaponId"]: get("/api/weapons/" + c["when"]["weaponId"].split(":")[1])
        for c in EXPECTED
    }}


@pytest.mark.parametrize("index", range(3))
def test_exact_critical_cases_reach_api_without_weapon_results(
    published: dict[str, Any], index: int,
) -> None:
    expected = EXPECTED[index]
    records = load_curated_document(CURATED)["records"]
    authored = next(r for r in records if r["id"] == "skill:immunity")
    assert authored["facts"]["immunityInteraction"]["reviewedCriticalCases"][index + 2] == expected
    stored = RulesDatabase(RULES).composed_record("skill:immunity")
    assert stored is not None
    assert stored["facts"]["immunityInteraction"]["reviewedCriticalCases"][index + 2] == expected
    facts = published["immunity"]["rules"][0]["facts"]["immunityInteraction"]
    assert facts["reviewedCriticalCases"][index + 2] == expected
    weapon = published["weapons"][expected["when"]["weaponId"]]
    profiles = weapon.get("profiles", []) + [p for v in weapon.get("weapon_variants", [])
                                           for p in v.get("profiles", [])]
    matches = [p for p in profiles if p.get("ammunition_source_id")
               == expected["when"]["sourceAmmunitionId"]]
    assert matches
    for profile in matches:
        assert profile["saving"] == expected["criticalWithoutImmunity"]["savingAttribute"]
        assert profile["saving_num"] == str(expected["criticalWithoutImmunity"]["hitRolls"])
        assert [c["record_id"] for c in profile["ammunition_composition"]["components"]] == (
            expected["components"]
        )
        assert "immunity_result" not in profile and "immunityInteraction" not in profile


def test_all_five_reviewed_combined_forms_have_exact_critical_examples() -> None:
    records = {r["id"]: r for r in load_curated_document(CURATED)["records"]}
    cases = records["skill:immunity"]["facts"]["immunityInteraction"]["reviewedCriticalCases"]
    source_ids = [c["when"]["sourceAmmunitionId"] for c in cases]
    assert len(source_ids) == len(set(source_ids)) == 5
    assert set(source_ids) == {5, 10, 13, 30, 40}
    for case in cases:
        assert case["components"] == load_ammunition_reference_map()[
            case["when"]["sourceAmmunitionId"]
        ]["components"]
        assert case["criticalWithoutImmunity"]["hitRolls"] + 1 == (
            case["criticalWithoutImmunity"]["criticalRolls"]
        )
        assert case["criticalWithImmunity"]["criticalRolls"] == (
            case["criticalWithoutImmunity"]["hitRolls"]
        )
    shock = records["ammunition:shock"]["facts"]["ammunitionResolution"]
    assert shock["stateEffects"] == [{
        "stateId": "state:dead", "condition": "failed-saving-roll",
        "targetAttribute": {"name": "VITA", "equals": 1}, "application": "bypass-unconscious",
    }]
    em = records["ammunition:em"]["facts"]["ammunitionResolution"]
    assert em["stateEffects"] == [
        {"stateId": "state:isolated", "condition": "failed-saving-roll"},
        {"stateId": "state:immobilized-b", "condition": "failed-saving-roll",
         "targetTypes": ["HI", "TAG", "REM", "VH"]},
    ]


@pytest.mark.parametrize("index", (2, 3, 4))
@pytest.mark.parametrize("section,key,value", [
    ("when", "weaponId", "weapon:flash-pulse"),
    ("when", "sourceAmmunitionId", 14),
    ("when", "immunity", "BTS"),
    ("when", "attackClass", "comms"),
    ("criticalWithoutImmunity", "savingAttribute", "ARM"),
    ("criticalWithoutImmunity", "hitRolls", 9),
    ("criticalWithoutImmunity", "criticalRolls", 9),
    ("criticalWithImmunity", "savingAttribute", "ARM"),
    ("criticalWithImmunity", "criticalRolls", 0),
    ("criticalWithImmunity", "additionalCriticalRollRemoved", False),
    ("", "components", ["ammunition:normal", "ammunition:shock"]),
    ("", "evidence", "explicit-pinned-wiki-example"),
])
def test_critical_completion_rejects_unreviewed_changes(
    tmp_path: Path, index: int, section: str, key: str, value: Any,
) -> None:
    doc = deepcopy(json.loads(CURATED.read_text(encoding="utf-8")))
    immunity = next(r for r in doc["records"] if r["id"] == "skill:immunity")
    case = immunity["facts"]["immunityInteraction"]["reviewedCriticalCases"][index]
    (case[section] if section else case)[key] = value
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="source-scoped Critical immunity cases"):
        load_curated_document(path)
