"""Curate ITS 17 V0.2 Outbreak with its distinct historical scoring.

Source-reviewed originals: EN pp. 68–71 and ES pp. 46–49.
ITS 17 awards one OP for Stabilizing Alpha and one for CivEvacing
Stabilized Alpha; ITS 18 omits the former and awards two for the latter.
Do not alias these two season definitions. One-time, guarded migration.
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
    "scenario:last-launch", "scenario:b-pong", "scenario:crossing-lines",
    "scenario:corporate-appropriation", "scenario:critical-intervention",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": p, "section": "Outbreak"} for p in range(68, 72)
    ] + [
        {"sourceId": ES, "page": p, "section": "Estallido"} for p in range(46, 50)
    ]


def main() -> int:
    season = json.loads(ITS17.read_text(encoding="utf-8"))
    original = SHARED.read_bytes()
    if hashlib.sha256(original).hexdigest() != season["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("Unexpected ITS 17 shared-library SHA-256")
    if [m["scenarioId"] for m in season["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    library = json.loads(original)
    if [d["id"] for d in library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 shared definitions; refusing overwrite")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(r for r in modern["records"] if r["id"] == "scenario:outbreak"))
    record["summary"] = (
        "ITS Season 17 Outbreak: Scan up to three Infected, Stabilize more and "
        "the Alpha Infected, CivEvac more and the Stabilized Alpha Infected, "
        "and Secure an Infected; historical scoring differs from ITS 18."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    facts = record["facts"]
    mission = facts["mission"]
    objectives = mission["objectives"]
    expected = [
        "scan-infected", "stabilize-more-infected",
        "civevac-more-stabilized", "civevac-stabilized-alpha",
        "secure-infected",
    ]
    if [o["id"] for o in objectives] != expected:
        raise ValueError("Unexpected ITS 18 Outbreak objective list")
    if [o["maximumPoints"] for o in objectives] != [3, 2, 2, 2, 1]:
        raise ValueError("Unexpected ITS 18 Outbreak scoring")
    if len(facts["configurations"]) != 3:
        raise ValueError("Unexpected ITS 18 Outbreak geometry")
    if {r["id"] for r in mission["rules"]} != {
        "infected-placement", "corner-deployment", "stabilization-zones",
        "stabilize-infected", "scan-infected", "doctor-paramedic-bonus",
        "secure-infected", "no-hvt-classified",
    }:
        raise ValueError("Unexpected ITS 18 Outbreak rule set")

    alpha = deepcopy(objectives[3])
    alpha["id"] = "stabilize-alpha-infected"
    alpha["name"] = "Stabilize Alpha Infected"
    alpha["maximumPoints"] = 1
    alpha["awards"][0]["objectivePoints"] = 1
    alpha["awards"][0]["condition"]["text"] = (
        "At game end, have Stabilized the Alpha Infected (ITS 17 "
        "EN p. 68 / ES p. 46). This separate 1-point objective "
        "does not exist in ITS 18."
    )
    objectives.insert(2, alpha)
    objectives[4]["maximumPoints"] = 1
    objectives[4]["awards"][0]["objectivePoints"] = 1
    objectives[4]["awards"][0]["condition"]["text"] = (
        "At game end, be CivEvacing the Stabilized Alpha Infected "
        "(1 Objective Point in ITS 17 EN p. 68 / ES p. 46, "
        "rather than 2 Objective Points in ITS 18)."
    )
    mission["sourceIssues"] = [{
        "id": "its17-outbreak-infected-placement-distance-en-es",
        "status": "needs-verification",
        "armyPoints": SIZES,
        "objectiveId": "secure-infected",
        "description": (
            "ITS 17 V0.2 EN p. 69 requires placement at least "
            "[[distance:4:inch]] outside the enemy Deployment Zone "
            "and [[distance:8:inch]] between Infected; ES p. 47 "
            "prints [[distance:10:cm]] and [[distance:20:cm]]. "
            "Geometry uses English units; both measurements are "
            "preserved without treating them as exactly equivalent."
        ),
    }]
    # This objective rearrangement is intentional: season-local source
    # changes must not propagate into the still-current ITS 18 edition.
    if [o["maximumPoints"] for o in objectives] != [3, 2, 1, 2, 1, 1]:
        raise ValueError("Invalid historical Outbreak scoring")
    definition = {
        "id": "scenario:outbreak",
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
        raise ValueError("Unexpected ITS 17 shared library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated = (text[:-len(ending)] + "    },\n" + addition + "\n  ]\n}\n").encode("utf-8")
    if [d["id"] for d in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:outbreak"]
    ):
        raise ValueError("Unexpected ITS 17 shared library result")
    season["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (fifteen reviewed scenarios)"
    )
    season["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:outbreak",
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
    print("Added historical ITS 17 Outbreak with eight source citations")
    print(f"Shared SHA-256: {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
