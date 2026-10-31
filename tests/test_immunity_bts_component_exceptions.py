"""Exact non-Comms BTS examples for Shock-only and E/M-only Immunity.

The surviving Ammunition remains separate from the covered component.
No target evaluator or Weapon-profile rewrite is introduced.
"""
from __future__ import annotations

import hashlib
import json
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
        "sourceAmmunitionId": 30, "sourceAmmunitionName": "AP+Shock",
        "components": ["ammunition:ap", "ammunition:shock"],
        "when": {
            "immunity": "Shock", "savingAttribute": "BTS", "attackClass": "non-comms",
            "weaponId": "weapon:silenced-pistol",
        },
        "withoutImmunity": {
            "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS/2",
        },
        "withImmunity": {
            "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS/2",
            "treatedAs": "ammunition:ap", "ignoredComponents": ["ammunition:shock"],
            "remainingComponents": ["ammunition:ap"],
        },
        "evidence": "derived-from-pinned-general-rules",
    },
    {
        "sourceAmmunitionId": 5, "sourceAmmunitionName": "N+E/M",
        "components": ["ammunition:normal", "ammunition:em"],
        "when": {
            "immunity": "E/M", "savingAttribute": "BTS", "attackClass": "non-comms",
            "weaponId": "weapon:e-m-cc-weapon",
        },
        "withoutImmunity": {
            "hitRolls": 2, "criticalRolls": 3, "savingAttribute": "BTS/2",
        },
        "withImmunity": {
            "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS",
            "treatedAs": "ammunition:normal", "ignoredComponents": ["ammunition:em"],
            "remainingComponents": ["ammunition:normal"],
        },
        "evidence": "derived-from-pinned-general-rules",
    },
]


@pytest.mark.parametrize("index", (0, 1))
def test_partial_bts_immunity_is_grounded_in_pinned_source_and_weapon(index: int) -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        pages = {n: " ".join(str(pdf[n - 1].get_text("text")).casefold().split())
                 for n in (63, 64, 65, 67, 95, 96, 177, 182)}
    assert "immunity (ammunition): the ammunition listed between brackets" in pages[95]
    assert "its special effects, and any mods" in pages[95]
    assert "number of the saving rolls are ignored" in pages[95]
    assert "unless they have immunity (critical)" in pages[96]
    assert "comms attacks, with the sole exception of immunity (state)" in pages[95]
    assert "single ammunition that adds the effects" in pages[67]
    if index == 0:
        assert "silenced pistol +3 0 -6 8 2 ap+shock bts/2 1 silent (-6)" in pages[182]
        assert "each saving roll failed against ap ammunition inflicts 1 wound" in pages[63]
        assert "vita attribute, with a value of 1" in pages[65]
        assert "passes directly to dead state" in pages[65]
    else:
        assert "e/m cc weapon 8 1 n+e/m bts/2 2 cc, [**]." in pages[177]
        assert (
            "due to the normal ammunition, each failed saving roll inflicts one wound" in pages[67]
        )
        assert "half his bts value (bts/2 x 2)" in pages[64]
    expected = EXPECTED[index]
    assert load_ammunition_reference_map()[expected["sourceAmmunitionId"]]["components"] == (
        expected["components"]
    )
    slug = expected["when"]["weaponId"].split(":")[1]
    weapon = Database(ARMY).get_catalog_item("weapons", slug)
    assert weapon is not None
    assert weapon["id"] == (211 if index == 0 else 7)
    matches = [p for p in weapon["profiles"]
               if p.get("ammunition_source_id") == expected["sourceAmmunitionId"]]
    assert matches
    for profile in matches:
        assert profile["ammunition"] == expected["sourceAmmunitionName"]
        assert profile["saving"] == "BTS/2"
        assert profile["saving_num"] == ("1" if index == 0 else "2")
        assert not any("Comms Attack" in t for t in profile["traits"])


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


@pytest.mark.parametrize("index", (0, 1))
def test_partial_bts_case_reaches_api_without_overwriting_weapon(
    published: dict[str, Any], index: int,
) -> None:
    expected = EXPECTED[index]
    records = load_curated_document(CURATED)["records"]
    immunity = next(r for r in records if r["id"] == "skill:immunity")
    assert immunity["facts"]["immunityInteraction"]["reviewedCombinedCases"][7 + index] == expected
    stored = RulesDatabase(RULES).composed_record("skill:immunity")
    assert stored is not None
    assert stored["facts"]["immunityInteraction"]["reviewedCombinedCases"][7 + index] == expected
    cases = published["immunity"]["rules"][0]["facts"]["immunityInteraction"][
        "reviewedCombinedCases"
    ]
    assert cases[7 + index] == expected
    # The earlier full BTS case and distinct component cases remain separately published.
    assert any(c["when"].get("weaponId") == expected["when"]["weaponId"]
               and c["when"]["immunity"] == "BTS" for c in cases)
    weapon = published["weapons"][expected["when"]["weaponId"]]
    matches = [p for p in weapon["profiles"]
               if p.get("ammunition_source_id") == expected["sourceAmmunitionId"]]
    assert matches
    for profile in matches:
        assert (profile["saving"], profile["saving_num"]) == (
            "BTS/2", "1" if index == 0 else "2",
        )
        assert [c["record_id"] for c in profile["ammunition_composition"]["components"]] == (
            expected["components"]
        )
        assert "immunity_result" not in profile and "immunityInteraction" not in profile


@pytest.mark.parametrize("index", (7, 8))
@pytest.mark.parametrize("section,key,value", [
    ("when", "weaponId", "weapon:flash-pulse"),
    ("when", "attackClass", "comms"),
    ("when", "savingAttribute", "ARM"),
    ("", "sourceAmmunitionId", 14),
    ("", "sourceAmmunitionName", "E/M"),
    ("", "components", ["ammunition:em", "ammunition:shock"]),
    ("withoutImmunity", "savingAttribute", "ARM/2"),
    ("withImmunity", "hitRolls", 0),
    ("withImmunity", "hitRolls", True),
    ("withImmunity", "criticalRolls", 1),
    ("withImmunity", "criticalRolls", 2.0),
    ("withImmunity", "savingAttribute", "ARM"),
    ("withImmunity", "treatedAs", "ammunition:exp"),
    ("withImmunity", "ignoredComponents", []),
    ("withImmunity", "remainingComponents", ["ammunition:shock"]),
    ("", "evidence", "explicit-pinned-wiki-example"),
])
def test_partial_bts_immunity_rejects_unreviewed_semantics(
    tmp_path: Path, index: int, section: str, key: str, value: Any,
) -> None:
    document = json.loads(CURATED.read_text(encoding="utf-8"))
    immunity = next(r for r in document["records"] if r["id"] == "skill:immunity")
    case = immunity["facts"]["immunityInteraction"]["reviewedCombinedCases"][index]
    (case[section] if section else case)[key] = value
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="applicability|covered-attack|evidence"):
        load_curated_document(path)
