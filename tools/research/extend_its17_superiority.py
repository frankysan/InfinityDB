"""One-time ITS 17 V0.2 Superiority historical publication.

English pp. 89-92; Spanish pp. 94-98. Retain the 3-point Console
ceiling and Dominant Key Ops instead of ITS 18's 4-point ceiling.
Only writes source-pinned historical authoring; refuses reruns.
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
EN, ES = "its-season-17-v0.2-en-pdf", "its-season-17-v0.2-es-pdf"
SIZES = [150, 200, 250, 300, 350, 400]
REVIEW = {"status": "reviewed", "reviewedOn": "2026-11-18"}
EXISTING = [
    "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
    "scenario:battleground", "scenario:annihilation", "scenario:cutthroat",
]


def citations() -> list[dict]:
    return (
        [{"sourceId": EN, "page": page, "section": "Superiority"} for page in (89, 90, 91, 92)]
        + [{"sourceId": ES, "page": page, "section": "Superioridad"}
           for page in (94, 95, 96, 97, 98)]
    )


def main() -> int:
    season = json.loads(ITS17.read_text(encoding="utf-8"))
    original_bytes = SHARED.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != season["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("ITS 17 source/library pin differs; refusing update")
    old_library = json.loads(original_bytes)
    if [x["scenarioId"] for x in season["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships")
    if [x["id"] for x in old_library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 shared definitions")

    current = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in current["records"] if row["id"] == "scenario:superiority"
    ))
    record["summary"] = (
        "ITS Season 17 Superiority: dominate more Quadrants at each round end, "
        "Hack up to three Consoles for points, and have a Dominant Key Ops at game end."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    mission = record["facts"]["mission"]
    if [o["id"] for o in mission["objectives"]] != [
        "dominate-more-quadrants", "hack-consoles",
    ]:
        raise ValueError("Unexpected current Superiority objective schema")
    hack = mission["objectives"][1]
    if hack["maximumPoints"] != 4 or hack["awards"][0]["objectivePoints"] != 1:
        raise ValueError("Unexpected current Console scoring")
    hack["maximumPoints"] = 3
    mission["objectives"].append({
        "id": "dominant-key-ops",
        "name": "Dominant Key Ops",
        "sideIds": ["side-a", "side-b"],
        "timing": "end-of-game",
        "aggregation": "exclusive",
        "maximumPoints": 1,
        "awards": [{
            "armyPoints": SIZES,
            "objectivePoints": 1,
            "condition": {
                "kind": "reviewed-prose",
                "text": (
                    "At game end, have your designated Key Ops in a non-Null "
                    "State within a Zone of Operations that you Dominate."
                ),
            },
        }],
    })

    rules = {row["id"]: row for row in mission["rules"]}
    if set(rules) != {
        "quadrants-zo", "shasvastii", "baggage", "consoles", "hack-consoles",
        "specialist-troops", "operational-learning", "hvt-and-classified-deck",
    }:
        raise ValueError("Unexpected current Superiority rules")
    rules["consoles"]["paragraphs"][0] = (
        "Four Consoles stand in the center of the four Quadrants. "
        "Use a Console A Token or a piece of scenery of the same "
        "diameter; ITS 17 does not independently specify a numeric diameter."
    )
    mission["rules"].extend([
        {
            "id": "key-ops",
            "name": "Key Ops",
            "paragraphs": [
                "At the end of Deployment, in Initiative order, each player "
                "designates a Key Ops from their Army List, deployed and "
                "remaining on the table as a Model, not a Marker or in "
                "Hidden Deployment.",
                "Irregular Troopers and REM or VH Troop Types cannot be "
                "designated in the English ITS 17 source. The Spanish "
                "version excludes Irregular and REM but does not mention VH.",
                "The Key Ops gains [[skill:dodge|Dodge (+3)]] and "
                "[[skill:tactical-awareness|Tactical Awareness]]; extra "
                "instances do not stack. Identify the Key Ops with a "
                "Player A or B Marker.",
            ],
        },
        {
            "id": "dominant-key-ops",
            "name": "Dominant Key Ops",
            "paragraphs": [
                "A player has a Dominant Key Ops at the end of the game "
                "when that Key Ops is in any non-Null State within a "
                "Zone of Operations Dominated by that player."
            ],
        },
    ])
    mission["sourceIssues"] = [
        {
            "id": "its17-shasvastii-en-es-zo-state",
            "armyPoints": SIZES,
            "objectiveId": "dominate-more-quadrants",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 90 counts Shasvastii Troopers in "
                "Unconscious or any non-Null State, whereas ES p. 95 "
                "names Normal or Shasvastii Embryo. The English wording "
                "is retained; do not silently equate the state sets."
            ),
        },
        {
            "id": "its17-key-ops-vh-eligibility-en-es",
            "armyPoints": SIZES,
            "objectiveId": "dominant-key-ops",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 92 excludes Irregular, REM and VH "
                "Troopers as Key Ops; ES p. 97 omits VH. Preserve "
                "the English exclusion and record the bilingual gap."
            ),
        },
    ]
    definition = {
        "id": "scenario:superiority",
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
        EXISTING + ["scenario:superiority"]
    ):
        raise ValueError("Unexpected new shared library")
    season["collection"]["title"] = "ITS Season 17 Seekers V0.2 (seven reviewed scenarios)"
    season["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:superiority",
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
    print(f"Added ITS 17 Superiority; library sha256 {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
