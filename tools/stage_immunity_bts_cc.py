"""Coordinate the reviewed N5.3 BTS Immunity / E/M CC Weapon publication.

Reuse the rollback-aware rules/publication pair staging machinery; add an
independent exact-weapon/provenance gate before and after promotion.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pymupdf

from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from tools.stage_immunity_plasma_saving_roll import (
    ARMY,
    PDF,
    PIN,
    ROOT,
    RULES,
    promote,
    stage,
)

EXPECTED_CASE = {
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


def verify_source_and_rules(path: Path) -> None:
    if hashlib.sha256(PDF.read_bytes()).hexdigest() != PIN:
        raise ValueError("N5.3 source hash mismatch")
    with pymupdf.open(PDF) as pdf:
        pages = {}
        for number in (67, 95, 177):
            value = pdf[number - 1].get_text("text")
            if not isinstance(value, str):
                raise ValueError(f"Non-text N5.3 page: {number}")
            pages[number] = " ".join(value.casefold().split())
    if not all(term in pages[67] for term in (
        "n+e/m ammunition", "two saving rolls", "bts attribute halved",
    )) or not all(term in pages[95] for term in (
        "immunity", "bts attribute is treated as normal", "comms attacks",
    )) or not all(term in pages[177] for term in (
        "e/m cc weapon", "n+e/m", "bts/2",
    )):
        raise ValueError("N5.3 source applicability drift")
    source = load_ammunition_reference_map()[5]
    if source["name"] != "N+E/M" or source["components"] != EXPECTED_CASE["components"]:
        raise ValueError("Combined Ammunition source mapping differs from review")
    weapon = Database(ARMY).get_catalog_item("weapons", "e-m-cc-weapon")
    if not weapon or not any(
        p.get("ammunition_source_id") == 5
        and p.get("saving") == "BTS/2"
        and p.get("saving_num") == "2"
        for p in weapon["profiles"]
    ):
        raise ValueError("Reviewed Army E/M CC Weapon profile missing")
    immunity = RulesDatabase(path).composed_record("skill:immunity")
    if immunity is None or immunity["facts"]["immunityInteraction"][
        "reviewedCombinedCases"
    ][-1] != EXPECTED_CASE:
        raise ValueError("N5.3 BTS Weapon-specific Immunity case missing or changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    staging = (ROOT / args.output_dir).resolve()
    if not staging.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Only local/ staging is permitted")
    if args.promote_staged:
        verify_source_and_rules(staging / "rules.db")
        backup = promote(args.output_dir)
        verify_source_and_rules(RULES)
        print(f"BTS E/M CC Weapon published with recovery backup: {backup}")
    else:
        report = stage(args.output_dir)
        verify_source_and_rules(staging / "rules.db")
        print(
            f"Verified staged BTS E/M CC case with {report['deployedObjects']} "
            "unchanged reviewed deployed objects; no promotion performed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
