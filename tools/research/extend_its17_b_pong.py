"""One-time ITS 17 V0.2 B-Pong migration from source-reviewed originals.

EN pp. 36-39 and ES pp. 38-41. Retain matching scoring and geometry;
unlike ITS 18, the originals agree on Beacon relocation origin, Console
requirements, and relative scenery diameter. Keep genuine wording differences.
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
    "scenario:superiority", "scenario:provisioning", "scenario:area-of-interest",
    "scenario:last-launch",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": p, "section": "B-Pong"} for p in range(36, 40)
    ] + [
        {"sourceId": ES, "page": p, "section": "B-Pong"} for p in range(38, 42)
    ]


def issue(issue_id: str, objective: str, description: str) -> dict:
    return {
        "id": issue_id,
        "armyPoints": SIZES,
        "objectiveId": objective,
        "status": "needs-verification",
        "description": description,
    }


def main() -> int:
    source = json.loads(ITS17.read_text(encoding="utf-8"))
    original = SHARED.read_bytes()
    if hashlib.sha256(original).hexdigest() != source["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("Unexpected ITS 17 shared-library SHA-256")
    if [m["scenarioId"] for m in source["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    library = json.loads(original)
    if [d["id"] for d in library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 definitions; refusing overwrite")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in modern["records"] if row["id"] == "scenario:b-pong"
    ))
    record["summary"] = (
        "ITS Season 17 B-Pong: reposition the central Tracking Beacon toward "
        "the enemy half, Control it and a Console each round, and complete "
        "two Classified Objectives."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    facts = record["facts"]
    mission = facts["mission"]
    if [o["id"] for o in mission["objectives"]] != [
        "beacon-in-enemy-half", "control-tracking-beacon",
        "control-any-console", "classified-objectives",
    ]:
        raise ValueError("Unexpected ITS 18 B-Pong objectives")
    if len(facts["configurations"]) != 3:
        raise ValueError("Unexpected B-Pong geometry count")
    rules = {rule["id"]: rule for rule in mission["rules"]}
    if set(rules) != {
        "forces-and-exclusion", "tracking-beacon-representation",
        "relocate-tracking-beacon", "beacon-movement", "activate-console",
        "control-console", "specialist-troops", "no-quarter",
        "classified-objectives",
    }:
        raise ValueError("Unexpected B-Pong rule set")

    rules["tracking-beacon-representation"]["paragraphs"][0] = (
        "One Tracking Beacon begins at the table center and is represented "
        "by a Beacon Token or equivalent scenery of matching diameter. "
        "Neither ITS 17 edition specifies an independent 40 mm or 25 mm "
        "diameter for this mission."
    )
    rules["tracking-beacon-representation"]["paragraphs"][1] = (
        "At the end of each Game Round, a player Controls the Beacon only "
        "if they alone have a non-Null Trooper Model, not a Marker, in "
        "Silhouette contact and no enemy Trooper is in contact. "
        "Both ITS 17 language editions use end-of-round timing."
    )
    relocate = rules["relocate-tracking-beacon"]
    relocate["skillFacts"]["effects"] = [
        "Spend one Short Skill without a Roll to place the Tracking Beacon "
        "anywhere within [[distance:4:inch]] of its previous position "
        "(ES [[distance:10:cm]]).",
    ]
    relocate["skillFacts"]["clarifications"] = []
    relocate["paragraphs"] = [
        "Attack, Scenario Short Skill. Only a Specialist Troop in Silhouette "
        "contact with the Tracking Beacon may declare this Skill, once per "
        "Game Round.",
        "Without a Roll, place the Beacon anywhere within "
        "[[distance:4:inch]] of its previous position (ES "
        "[[distance:10:cm]]). Both ITS 17 originals measure from the "
        "Beacon's old position, not from the declaring Trooper.",
    ]
    rules["forces-and-exclusion"]["paragraphs"][2] = (
        "The Beacon starts at the table center and can subsequently be "
        "moved by scenario actions. Two Consoles stand on the centerline "
        "at [[distance:6:inch]] / [[distance:8:inch]] / "
        "[[distance:12:inch]] from each table edge in 150 / 200–250 / "
        "300–400-point games respectively."
    )
    activate = rules["activate-console"]
    activate["skillFacts"]["effects"] = [
        "Make a Normal WIP Roll to Activate the Console; failed attempts "
        "can be repeated by spending another Short Skill.",
        "On success choose to Nudge the Tracking Beacon within "
        "[[distance:2:inch]] of its position, or Magnetize it up to "
        "[[distance:6:inch]] directly toward the table center, without "
        "crossing the center, per ITS 17 English.",
    ]
    activate["skillFacts"]["restrictions"] = [
        "Only a Specialist Troop in Silhouette contact with a Console "
        "may declare this Skill. The Beacon cannot be in Silhouette "
        "contact with a Trooper. Each Specialist Troop may successfully "
        "Activate a Console only once per Game Round. Both ITS 17 "
        "English and Spanish impose these requirements.",
    ]
    activate["skillFacts"]["clarifications"] = [
        "ITS 17 ES p. 41 describes moving the Beacon "
        "[[distance:15:cm]] toward the center, rather than up to that "
        "distance in the English version.",
    ]
    activate["skillFacts"]["sourceNotes"] = [
        "ITS 17 ES p. 41 calls a successfully Activated Console "
        "'Conectada' (Connected) despite titling the Skill 'Activar "
        "Consola'; EN p. 39 uses Activated.",
    ]
    activate["paragraphs"] = [
        "Attack, Scenario Short Skill. A Specialist Troop in Silhouette "
        "contact with a Console may make a Normal WIP Roll to Activate "
        "it; failed attempts can be retried with another Short Skill.",
        "The Beacon cannot be in Silhouette contact with any Trooper. "
        "Each Specialist Troop may successfully Activate a Console "
        "only once per Game Round. Both ITS 17 editions state these limits.",
        "On success choose to Nudge the Beacon within [[distance:2:inch]] "
        "(ES [[distance:5:cm]]) of its position, or Magnetize it up to "
        "[[distance:6:inch]] toward the center, without passing it. "
        "Spanish uses [[distance:15:cm]] toward the center without "
        "explicitly saying 'up to', and calls successful Activation "
        "'Connected'; these wording distinctions remain unresolved.",
    ]
    mission["sourceIssues"] = [
        issue(
            "its17-b-pong-magnetize-distance-en-es",
            "control-any-console",
            "ITS 17 V0.2 EN p. 39 permits placing the Beacon within "
            "[[distance:6:inch]] of its previous position toward the "
            "center; ES p. 41 specifies [[distance:15:cm]] toward "
            "the center without explicitly treating it as a maximum.",
        ),
        issue(
            "its17-b-pong-console-connected-es",
            "control-any-console",
            "ITS 17 V0.2 ES p. 41 describes successful Console "
            "activation as 'Conectada' while the action is 'Activar "
            "Consola'. EN p. 39 consistently says Activated.",
        ),
    ]
    definition = {
        "id": "scenario:b-pong",
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
    text = original.decode("utf-8")
    ending = "    }\n  ]\n}\n"
    if not text.endswith(ending):
        raise ValueError("Unexpected ITS 17 library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated = (text[:-len(ending)] + "    },\n" + addition + "\n  ]\n}\n").encode("utf-8")
    if [row["id"] for row in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:b-pong"]
    ):
        raise ValueError("Unexpected shared library result")
    source["collection"]["title"] = "ITS Season 17 Seekers V0.2 (eleven reviewed scenarios)"
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:b-pong",
        "sharedDefinition": {
            "version": "its17-v0.2",
            "citations": citations(),
            "review": deepcopy(REVIEW),
            "componentCitations": {},
            "overrides": [],
        },
    })
    source["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(updated).hexdigest()
    SHARED.write_bytes(updated)
    ITS17.write_text(
        json.dumps(source, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    print("Added ITS 17 B-Pong with eight original citation pages")
    print(f"Shared SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
