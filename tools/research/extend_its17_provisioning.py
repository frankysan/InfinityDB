"""One-time ITS 17 V0.2 Provisioning curation from pinned bilingual originals.

EN pp. 72-76, ES pp. 70-74. Retain matching scoring/geometry,
but restore historical Tech-Coffin, Safe Area and pickup wording.
Unregistered ITS 17 library only; refuses reruns or unexpected inputs.
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
    "scenario:battleground", "scenario:annihilation", "scenario:cutthroat",
    "scenario:superiority",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Provisioning"}
        for page in (72, 73, 74, 75, 76)
    ] + [
        {"sourceId": ES, "page": page, "section": "Reabastecimiento"}
        for page in (70, 71, 72, 73, 74)
    ]


def main() -> int:
    season = json.loads(ITS17.read_text(encoding="utf-8"))
    original_bytes = SHARED.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != season["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("Unexpected ITS 17 shared-library SHA-256")
    if [row["scenarioId"] for row in season["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    shared = json.loads(original_bytes)
    if [row["id"] for row in shared["definitions"]] != EXISTING:
        raise ValueError("Unexpected historical definitions; refusing overwrite")

    current = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in current["records"] if row["id"] == "scenario:provisioning"
    ))
    record["summary"] = (
        "ITS Season 17 Provisioning: extract four Supply Boxes from three "
        "Tech-Coffins, secure player-placed Safe Areas, and score end-game "
        "Control with one Classified Objective."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    mission = record["facts"]["mission"]
    if {row["id"] for row in mission["objectives"]} != {
        "control-supply-boxes", "safe-area-comparison",
        "opponent-empty-safe-area", "classified-objective",
    }:
        raise ValueError("Unexpected current Provisioning objectives")
    if len(record["facts"]["configurations"]) != 3:
        raise ValueError("Unexpected current Provisioning geometry count")
    rules = {rule["id"]: rule for rule in mission["rules"]}
    if set(rules) != {
        "deployment-and-tech-coffins", "extract-supply-boxes",
        "pickup-supply-boxes", "common-supply-box-rules",
        "control-supply-boxes", "safe-areas",
        "specialist-troops", "operational-learning",
    }:
        raise ValueError("Unexpected current Provisioning rule set")

    # ITS 17 both languages specify relative Token diameter, not 40 mm.
    rules["deployment-and-tech-coffins"]["paragraphs"][1] = (
        "Three Tech-Coffins lie along the central diagonal, one at the "
        "table center and two [[distance:8:inch]] / "
        "[[distance:12:inch]] / [[distance:16:inch]] from it in "
        "150 / 200–250 / 300–400-point games. Each outer Tech-Coffin "
        "contains one Supply Box and the central one contains two. "
        "Use a Tech-Coffin Marker or a scenery piece of equal diameter; "
        "the ITS 17 mission does not specify an independent 40 mm size."
    )
    extract = rules["extract-supply-boxes"]
    extract["skillFacts"]["sourceNotes"] = [
        "ITS 17 EN p. 74 requires base contact with a Tech-Coffin, "
        "while ES p. 71 requires Silhouette contact. The historical "
        "requirement preserves this unresolved language distinction.",
        "Both ITS 17 editions require marking a Tech-Coffin with a "
        "Player A/B Token once all its Supply Boxes are extracted; "
        "neither directs removal of the emptied Tech-Coffin Token.",
    ]
    extract["paragraphs"][1] = (
        "Once all Supply Boxes have been Extracted from a Tech-Coffin, "
        "place a Player A or B Token beside it to mark the extraction. "
        "Unlike ITS 18 English, the ITS 17 mission does not direct "
        "removal of the emptied Tech-Coffin Token."
    )
    rules["pickup-supply-boxes"]["paragraphs"][1] = (
        "If the Supply Box is in the enemy's Safe Area, only a Specialist "
        "Troop may pick it up, requiring a Normal WIP-3 Roll. Both ITS 17 "
        "editions specifically name the opposing player's Safe Area; "
        "do not apply the broader ITS 18 English 'any Safe Area' wording."
    )
    rules["safe-areas"]["paragraphs"][1] = (
        "These are player-placed Circular Templates, not fixed map "
        "objects. A Trooper can deposit a Supply Box in their Safe Area "
        "with a Short Skill and no Roll, placing the Box completely "
        "inside the Safe Area. Both ITS 17 languages require the Box "
        "to be wholly inside."
    )
    rules["safe-areas"]["paragraphs"][2] = (
        "Only Specialist Troops may recover a Supply Box from the "
        "enemy's Safe Area using Pick Up Supply Boxes and a WIP-3 Roll."
    )
    mission["sourceIssues"] = [
        {
            "id": "its17-extract-contact-en-es",
            "armyPoints": SIZES,
            "objectiveId": "control-supply-boxes",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 74 requires base contact to Extract "
                "from a Tech-Coffin; ES p. 71 says Silhouette contact. "
                "The terms are not assumed equivalent in the historical record."
            ),
        },
    ]

    definition = {
        "id": "scenario:provisioning",
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
        raise ValueError("Unexpected historical library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated = (text[:-len(ending)] + "    },\n" + addition + "\n  ]\n}\n").encode("utf-8")
    if [row["id"] for row in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:provisioning"]
    ):
        raise ValueError("Unexpected historical library result")

    season["collection"]["title"] = "ITS Season 17 Seekers V0.2 (eight reviewed scenarios)"
    season["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:provisioning",
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
    print("Added source-pinned ITS 17 Provisioning; 10 bilingual citation pages")
    print(f"Shared SHA-256: {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
