"""One-time ITS 17 V0.2 Cutthroat migration (EN pp. 86-88, ES pp. 91-93).

Retains season-specific Key Ops objectives and published bilingual differences.
The existing ITS 18 Cutthroat remains untouched. Refuses unexpected reruns.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from textwrap import indent

from infinity_db.curated import load_curated_document

ROOT = Path(__file__).resolve().parents[2]
ITS17 = ROOT / "data/curated/its/n5-its-season-17.json"
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
SIZES = [150, 200, 250, 300, 350, 400]
REVIEW = {"status": "reviewed", "reviewedOn": "2026-11-18"}
EXISTING = [
    "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
    "scenario:battleground", "scenario:annihilation",
]


def citations() -> list[dict]:
    return (
        [{"sourceId": EN, "page": page, "section": "Cutthroat"}
         for page in (86, 87, 88)]
        + [{"sourceId": ES, "page": page, "section": "Degüello"}
           for page in (91, 92, 93)]
    )


def objective(identifier: str, name: str, points: int, text: str) -> dict:
    return {
        "id": identifier,
        "name": name,
        "sideIds": ["side-a", "side-b"],
        "timing": "end-of-game",
        "aggregation": "exclusive",
        "maximumPoints": points,
        "awards": [{
            "armyPoints": SIZES,
            "objectivePoints": points,
            "condition": {"kind": "reviewed-prose", "text": text},
        }],
    }


def main() -> int:
    season = json.loads(ITS17.read_text(encoding="utf-8"))
    original_bytes = SHARED.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != season["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("ITS 17 shared library SHA-256 mismatch")
    if [x["scenarioId"] for x in season["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 membership order; refusing overwrite")
    original = json.loads(original_bytes)
    if [x["id"] for x in original["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 shared definitions; refusing overwrite")

    current = load_curated_document(ITS18)
    record = deepcopy(next(
        x for x in current["records"] if x["id"] == "scenario:cutthroat"
    ))
    record["summary"] = (
        "ITS Season 17 Cutthroat: Kill enemy Army Points and Lieutenants, "
        "Kill the enemy Key Ops and exceed their Key Ops' Trooper kills. "
        "Reinforced Tactical Link replaces Loss of Lieutenant."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    mission = record["facts"]["mission"]
    old_ids = [x["id"] for x in mission["objectives"]]
    if old_ids != [
        "kill-more-army-points", "kill-same-lieutenants",
        "kill-more-lieutenants", "kill-more-with-lieutenants",
    ]:
        raise ValueError("Unexpected current Cutthroat objective schema")
    mission["objectives"] = mission["objectives"][:3] + [
        objective(
            "kill-enemy-key-ops", "Kill the enemy Key Ops", 1,
            "Kill the opposing Key Ops: the selected Trooper is Killed under "
            "the mission's Killing criteria.",
        ),
        objective(
            "kill-more-with-key-ops", "Key Ops enemy Trooper kills", 3,
            "Kill more enemy Troopers with your Key Ops than the opposing "
            "player kills with theirs. Credit a Key Ops when they cause a "
            "Trooper to be in a Null State at game end, or cause Wounds/STR "
            "loss during the Order in which that Trooper enters Dead State.",
        ),
    ]
    current_rules = {x["id"]: x for x in mission["rules"]}
    if set(current_rules) != {
        "reinforced-tactical-link", "killing", "no-quarter",
        "hvt-and-classified-deck",
    }:
        raise ValueError("Unexpected current Cutthroat rule schema")
    current_rules["killing"]["paragraphs"].insert(2, (
        "The Key Ops counts as Killing a target if they cause it to end "
        "in a Null State or cause a loss of Wounds/STR in the Order in "
        "which it enters Dead State."
    ))
    mission["rules"].insert(1, {
        "id": "key-ops",
        "name": "Key Ops",
        "paragraphs": [
            "At the end of the Deployment Phase, in Initiative order, "
            "each player designates one Key Ops from their Army List. The "
            "Trooper must be deployed on the table as a Model, not in "
            "Hidden Deployment or Marker State, and must remain a Model.",
            "Irregular Troopers and REM or VH Troop Types cannot become "
            "Key Ops under the English ITS 17 text; the Spanish source "
            "omits the VH restriction.",
            "The Key Ops gains [[skill:dodge|Dodge (+3)]] and "
            "[[skill:tactical-awareness|Tactical Awareness]], even if "
            "not in their Unit Profile. These do not stack with already "
            "possessed instances. Identify the Key Ops with the Player "
            "A or B Marker.",
        ],
    })
    mission["sourceIssues"] = [
        {
            "id": "key-ops-vh-eligibility-en-es",
            "armyPoints": SIZES,
            "objectiveId": "kill-enemy-key-ops",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 87 excludes REM and VH from Key Ops "
                "designation, while ES p. 92 excludes REM but omits VH. "
                "Retain the English exclusion and flag the disagreement."
            ),
        },
        {
            "id": "lieutenant-more-kills-minimum-en-es",
            "armyPoints": SIZES,
            "objectiveId": "kill-more-lieutenants",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 ES p. 91 adds a condition requiring at least "
                "one Lieutenant Killed to the more-Lieutenants objective, "
                "which EN p. 86 does not explicitly state. Retain the "
                "English objective wording and the language difference."
            ),
        },
        {
            "id": "killed-lieutenant-history-en-es",
            "armyPoints": SIZES,
            "objectiveId": "kill-more-lieutenants",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 88 counts Troopers that were Lieutenants "
                "at any time as Killed Lieutenants if Dead or Null at "
                "game end; ES p. 93 omits that explicit sentence."
            ),
        },
    ]

    definition = {
        "id": "scenario:cutthroat",
        "version": "its17-v0.2",
        "origin": {
            "sourceCollectionId": "its-season-17-v0.2",
            "seasonId": "its-17",
            "revision": "0.2",
            "sourceIds": [EN, ES],
        },
        "record": record,
        "components": [],
    }
    text = original_bytes.decode("utf-8")
    ending = "    }\n  ]\n}\n"
    if not text.endswith(ending):
        raise ValueError("Unexpected shared-library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated = (text[:-len(ending)] + "    },\n" + addition + "\n  ]\n}\n").encode("utf-8")
    if [x["id"] for x in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:cutthroat"]
    ):
        raise ValueError("Unexpected shared-library result")
    season["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (six reviewed scenarios)"
    )
    season["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:cutthroat",
        "sharedDefinition": {
            "version": "its17-v0.2",
            "citations": citations(),
            "review": deepcopy(REVIEW),
            "componentCitations": {},
            "overrides": [],
        },
    })
    season["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(updated).hexdigest()
    SHARED.write_bytes(updated)
    ITS17.write_text(
        json.dumps(season, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"Added Cutthroat to ITS 17; library sha256 {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
