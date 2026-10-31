"""Stage and promote source-reviewed Plasma / Immunity (Enhanced) reference.

The source case is restricted to N5.3 PDF p. 96, Example 3. No computed
attack results or changed Weapon profiles are published. Stage outside
tracked outputs; promote with the existing rollback-aware batch helper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.weapon_combined_saving_rolls import WeaponCombinedSavingRolls
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.stage_hacking_device_chart_citations import STAGED_PATHS, _replace_staged_batch

ROOT = Path(__file__).resolve().parents[1]
CURATED, RULES, PUBLICATION = (ROOT / name for name in STAGED_PATHS)
ARMY = ROOT / "data/generated/infinity.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
SCOPE = "n53-immunity-plasma-saving-roll-p96-staged"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_source() -> None:
    if digest(PDF) != PIN:
        raise ValueError("Pinned N5.3 PDF changed")
    import fitz

    with fitz.open(PDF) as pdf:
        page_text = pdf[95].get_text("text")
        if not isinstance(page_text, str):
            raise ValueError("Pinned Immunity source page is not text")
        page = " ".join(page_text.casefold().split())
    if not all(clause in page for clause in (
        "example 3", "immunity (enhanced)", "plasma rifle",
        "saving roll against arm", "saving roll against bts",
    )):
        raise ValueError("N5.3 p. 96 source example changed")


def check_rules(path: Path) -> None:
    rules = RulesDatabase(path)
    immunity = rules.composed_record("skill:immunity")
    if immunity is None:
        raise ValueError("Missing Immunity source record")
    cases = immunity["facts"]["immunityInteraction"]["reviewedSavingRollCases"]
    if cases != [{
        "when": {
            "weaponId": "weapon:plasma-rifle",
            "immunity": "Enhanced",
            "ammunitionId": "ammunition:normal",
        },
        "savingRolls": [
            {"attribute": "ARM", "count": 1},
            {"attribute": "BTS", "count": 1},
        ],
        "result": "combined-saving-roll-preserved",
        "evidence": "explicit-n5.3-pdf-p96-example-3",
    }, {
        "when": {
            "weaponId": "weapon:plasma-rifle",
            "immunity": "Critical",
            "attackClass": "non-comms",
            "ammunitionId": "ammunition:normal",
        },
        "criticalWithoutImmunity": [
            {"attribute": "ARM", "count": 2},
            {"attribute": "BTS", "count": 1},
        ],
        "criticalWithImmunity": [
            {"attribute": "ARM", "count": 1},
            {"attribute": "BTS", "count": 1},
        ],
        "removedCriticalRoll": {"attribute": "ARM", "count": 1},
        "result": "critical-extra-arm-roll-removed",
        "evidence": "derived-from-pinned-general-rules",
    }]:
        raise ValueError("Unsupported Plasma Combined Saving Roll cases")
    if not any(c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 96
               for c in immunity["citations"]):
        raise ValueError("No pinned Immunity source citation")
    plasma = Database(ARMY).get_catalog_item("weapons", "plasma-rifle")
    if plasma is None:
        raise ValueError("Plasma Rifle missing from Army")
    for profile in plasma["profiles"]:
        reviewed = WeaponCombinedSavingRolls().for_profile(profile)
        if reviewed is None or reviewed["rolls"] != cases[0]["savingRolls"]:
            raise ValueError("Combined Saving Roll and printed example disagree")


def build(path: Path) -> bytes:
    return publication_bytes(build_publication(ARMY, path, CURATED, DELIVERY, CANDIDATES))


def _stage_dir(relative: Path) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Stage must be under local/")
    return path


def stage(relative: Path) -> dict[str, Any]:
    path = _stage_dir(relative)
    if path.exists():
        raise FileExistsError(f"Cannot overwrite staged artifacts: {path}")
    check_source()
    prior = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    if prior["sourceSnapshot"]["rulesDatabaseSha256"] != digest(RULES):
        raise ValueError("Existing rules/publication pair is not synchronized")
    path.mkdir(parents=True)
    staged_rules = path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), staged_rules)
    check_rules(staged_rules)
    updated_bytes = build(staged_rules)
    updated = json.loads(updated_bytes)
    if updated["objects"] != prior["objects"]:
        raise ValueError("Reviewed deployed-object payload was modified")
    if updated["sourceSnapshot"]["rulesDatabaseSha256"] != digest(staged_rules):
        raise ValueError("New publication does not reference staged rules.db")
    (path / "deployed-objects.json").write_bytes(updated_bytes)
    report = {
        "scope": SCOPE,
        "curatedSha256": digest(CURATED),
        "armySha256": digest(ARMY),
        "pdfSha256": digest(PDF),
        "previousRulesSha256": digest(RULES),
        "previousPublicationSha256": digest(PUBLICATION),
        "newRulesSha256": digest(staged_rules),
        "newPublicationSha256": digest(path / "deployed-objects.json"),
        "deployedObjects": len(updated["objects"]),
    }
    (path / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def promote(relative: Path) -> Path:
    path = _stage_dir(relative)
    if path.is_symlink():
        raise ValueError("Symlink staging paths are refused")
    report = json.loads((path / "report.json").read_text(encoding="utf-8"))
    if report.get("scope") != SCOPE:
        raise ValueError("Unrecognized staging contract")
    pairs = (
        (CURATED, "curatedSha256"),
        (ARMY, "armySha256"),
        (PDF, "pdfSha256"),
        (RULES, "previousRulesSha256"),
        (PUBLICATION, "previousPublicationSha256"),
        (path / "rules.db", "newRulesSha256"),
        (path / "deployed-objects.json", "newPublicationSha256"),
    )
    for item, key in pairs:
        if not item.is_file() or item.is_symlink() or digest(item) != report[key]:
            raise ValueError(f"Stale or unsafe staged input: {item}")
    check_source()
    check_rules(path / "rules.db")
    if build(path / "rules.db") != (path / "deployed-objects.json").read_bytes():
        raise ValueError("Staged deployed-object publication differs from fresh build")
    previous_objects = json.loads(PUBLICATION.read_text(encoding="utf-8"))["objects"]
    payloads = {
        STAGED_PATHS[0]: CURATED.read_bytes(),
        STAGED_PATHS[1]: (path / "rules.db").read_bytes(),
        STAGED_PATHS[2]: (path / "deployed-objects.json").read_bytes(),
    }

    def verify() -> None:
        check_rules(RULES)
        if digest(RULES) != report["newRulesSha256"] or build(RULES) != PUBLICATION.read_bytes():
            raise ValueError("Promoted rules/publication pair not reproducible")
        if json.loads(PUBLICATION.read_text(encoding="utf-8"))["objects"] != previous_objects:
            raise ValueError("Promotion changed deployed objects")
        if digest(PUBLICATION) != report["newPublicationSha256"]:
            raise ValueError("Published artifact hash drift")

    return _replace_staged_batch(ROOT, payloads, verify)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        backup = promote(args.output_dir)
        print(f"Promoted Plasma Immunity example; rollback backup: {backup}")
    else:
        print(json.dumps(stage(args.output_dir), indent=2))
        print("Stage only; tracked publication unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
