"""Stage/promote the exact AP Immunity versus Silenced Pistol source case.

The new partial AP+Shock review leaves the source BTS/2 Weapon profile
unchanged, retains the conditional Shock effect and Silent Trait, and
does not implement general component-based combat adjudication.
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
    "sourceAmmunitionId": 30,
    "sourceAmmunitionName": "AP+Shock",
    "components": ["ammunition:ap", "ammunition:shock"],
    "when": {
        "immunity": "AP",
        "savingAttribute": "BTS",
        "attackClass": "non-comms",
        "weaponId": "weapon:silenced-pistol",
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


def verify(path: Path) -> None:
    if hashlib.sha256(PDF.read_bytes()).hexdigest() != PIN:
        raise ValueError("Pinned N5.3 source revision drift")
    with pymupdf.open(PDF) as pdf:
        for number, phrases in {
            63: ("armor-piercing (ap)", "arm or bts"),
            65: ("shock ammunition", "vita attribute", "dead state"),
            67: ("combined ammunition", "additional saving roll"),
            95: ("immunity", "comms attacks"),
            96: ("additional saving roll",),
            175: ("silent (x)", "face to face dodge"),
            182: ("silenced pistol", "ap+shock", "bts/2", "silent (-6)"),
        }.items():
            raw = pdf[number - 1].get_text("text")
            if not isinstance(raw, str) or any(
                phrase not in " ".join(raw.casefold().split()) for phrase in phrases
            ):
                raise ValueError(f"Unverified N5.3 p. {number} applicability")
    source = load_ammunition_reference_map()[30]
    if source["name"] != "AP+Shock" or source["components"] != EXPECTED["components"]:
        raise ValueError("AP+Shock source map differs from review")
    weapon = Database(ARMY).get_catalog_item("weapons", "silenced-pistol")
    if weapon is None or not any(
        p.get("ammunition_source_id") == 30
        and p.get("saving") == "BTS/2"
        and p.get("saving_num") == "1"
        for p in weapon["profiles"]
    ):
        raise ValueError("Silenced Pistol source profile not verified")
    immunity = RulesDatabase(path).composed_record("skill:immunity")
    if immunity is None or immunity["facts"]["immunityInteraction"][
        "reviewedCombinedCases"
    ][3] != EXPECTED:
        raise ValueError("Unsupported partial BTS-based AP Immunity case")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    destination = (ROOT / args.output_dir).resolve()
    if not destination.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Stage must remain under local/")
    if args.promote_staged:
        verify(destination / "rules.db")
        backup = promote(args.output_dir)
        verify(RULES)
        print(f"Silenced Pistol partial Immunity promoted; recovery backup: {backup}")
    else:
        report = stage(args.output_dir)
        verify(destination / "rules.db")
        print(
            f"Staged AP+Shock partial Immunity; {report['deployedObjects']} "
            "reviewed deployed objects unchanged; no promotion yet."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
