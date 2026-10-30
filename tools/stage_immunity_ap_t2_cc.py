"""Stage and promote the exact N5.3 AP+T2 CC / Immunity (AP) review.

Only AP's defense reduction disappears; T2's hit/extra-Critical failed-roll
Wound counts remain distinct. The source Army Weapon profile is never mutated.
The existing rollback-aware helper promotes rules.db and deployed publication
as one verified set, preserving reviewed deployed objects.
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


def verify(path: Path) -> None:
    if hashlib.sha256(PDF.read_bytes()).hexdigest() != PIN:
        raise ValueError("N5.3 source hash changed")
    with pymupdf.open(PDF) as pdf:
        for number, terms in {
            63: ("armor-piercing (ap)", "arm or bts"),
            67: ("t2 ammunition", "inflicts 2 wounds", "only 1 additional wound",
                 "before performing the saving rolls", "combined ammunition"),
            95: ("immunity", "ammunition listed between brackets", "comms attacks"),
            96: ("additional saving roll",),
            177: ("ap+t2 cc", "arm/2", "anti-materiel", "cc."),
        }.items():
            raw = pdf[number - 1].get_text("text")
            if not isinstance(raw, str) or any(
                term not in " ".join(raw.casefold().split()) for term in terms
            ):
                raise ValueError(f"Unverified N5.3 applicability on p. {number}")
    source = load_ammunition_reference_map()[40]
    if source["name"] != "AP+T2" or source["components"] != EXPECTED["components"]:
        raise ValueError("Source combined Ammunition identity changed")
    weapon = Database(ARMY).get_catalog_item("weapons", "ap-t2-cc-weapon")
    if weapon is None or not any(
        p.get("ammunition_source_id") == 40
        and p.get("saving") == "ARM/2"
        and p.get("saving_num") == "1"
        and "Anti-materiel" in p.get("traits", [])
        for p in weapon["profiles"]
    ):
        raise ValueError("Reviewed AP+T2 CC Weapon source profile unavailable")
    rules = RulesDatabase(path)
    immunity = rules.composed_record("skill:immunity")
    if immunity is None or immunity["facts"]["immunityInteraction"][
        "reviewedCombinedCases"
    ][4] != EXPECTED:
        raise ValueError("Unverified Immunity/AP+T2 case")
    t2 = rules.composed_record("ammunition:t2")
    if t2 is None or t2["facts"]["ammunitionResolution"][
        "woundsPerFailedSave"
    ] != EXPECTED["withImmunity"]["failedRollWounds"]:
        raise ValueError("T2 hit/extra Critical Wound effects drifted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    dest = (ROOT / args.output_dir).resolve()
    if not dest.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Staging outside local/ refused")
    if args.promote_staged:
        verify(dest / "rules.db")
        backup = promote(args.output_dir)
        verify(RULES)
        print(f"AP+T2 partial Immunity promoted; rollback backup: {backup}")
    else:
        report = stage(args.output_dir)
        verify(dest / "rules.db")
        print(
            f"Staged AP+T2 partial Immunity; {report['deployedObjects']} "
            "reviewed objects unchanged; promotion not performed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
