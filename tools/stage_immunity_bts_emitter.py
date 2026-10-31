"""Stage/promote the exact standalone E/Mitter Immunity (BTS) example.

Keep Armed Turret's unresolved one-roll mode untouched. The ordinary
rollback-aware batch helper stages a coherent rules.db / deployed-object
publication pair; this wrapper adds exact source and published-fact checks.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pymupdf

from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
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
    "when": {
        "weaponId": "weapon:e-mitter",
        "sourceWeaponId": 25,
        "sourceAmmunitionId": 14,
        "immunity": "BTS",
        "savingAttribute": "BTS",
        "attackClass": "non-comms",
    },
    "ammunitionTreatedAs": "ammunition:normal",
    "survivingTraits": ["trait:non-lethal"],
    "withoutImmunity": {
        "hitRolls": 2, "criticalRolls": 3, "savingAttribute": "BTS/2",
    },
    "withImmunity": {
        "hitRolls": 1, "criticalRolls": 2, "savingAttribute": "BTS",
    },
    "evidence": "derived-from-pinned-general-rules",
}


def verify(path: Path) -> None:
    if hashlib.sha256(PDF.read_bytes()).hexdigest() != PIN:
        raise ValueError("N5.3 source revision drift")
    with pymupdf.open(PDF) as source:
        pages: dict[int, str] = {}
        for number in (64, 95, 96, 186):
            raw = source[number - 1].get_text("text")
            if not isinstance(raw, str):
                raise ValueError(f"Missing N5.3 source text on p. {number}")
            pages[number] = " ".join(raw.casefold().split())
    for number, phrases in {
        64: ("two saving rolls per hit suffered", "bts/2", "isolated state"),
        95: ("bts attribute is treated as normal", "non-lethal", "comms attacks"),
        96: ("additional saving roll",),
        186: ("e/mitter", "bts/2", "non-lethal", "e/m"),
    }.items():
        if any(phrase not in pages[number] for phrase in phrases):
            raise ValueError(f"Current source applicability drift on p. {number}")
    source_weapon = Database(ARMY).get_catalog_item("weapons", "e-mitter")
    if source_weapon is None or source_weapon["id"] != 25:
        raise ValueError("Unexpected standalone E/Mitter source identity")
    profiles = source_weapon.get("profiles", [])
    if not profiles or any(
        (p["ammunition_source_id"], p["saving"], p["saving_num"]) !=
        (14, "BTS/2", "2") for p in profiles
    ):
        raise ValueError("Unexpected standalone E/Mitter source profile")
    immunity = RulesDatabase(path).composed_record("skill:immunity")
    if immunity is None:
        raise ValueError("Missing Immunity reference")
    reviewed = immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"]
    if len(reviewed) != 2 or reviewed[1] != EXPECTED:
        raise ValueError("Missing exact standalone E/Mitter Immunity case")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    destination = (ROOT / args.output_dir).resolve()
    if not destination.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Staging outside local/ is refused")
    if args.promote_staged:
        verify(destination / "rules.db")
        backup = promote(args.output_dir)
        verify(RULES)
        print(f"Standalone E/Mitter Immunity promoted; recovery backup: {backup}")
    else:
        report = stage(args.output_dir)
        verify(destination / "rules.db")
        print(
            f"Staged E/Mitter Immunity case; {report['deployedObjects']} "
            "reviewed objects unchanged; no promotion yet."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
