"""One-time ITS 17 V0.2 Annihilation authoring, with bilingual source conflicts.

Read from the pinned ITS 17 originals (EN pp. 81-82; ES pp. 85-87)
and compared with ITS 18 2026.09.11 EN pp. 125-128. The English
thresholds and geometry are supported by the source; the Spanish
scoring conflict and historical defects remain explicit source issues.
Only historical authoring files change. Refuses reruns.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from textwrap import indent

from infinity_db.curated import load_curated_document

ROOT = Path(__file__).resolve().parents[2]
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
ITS17 = ROOT / "data/curated/its/n5-its-season-17.json"
LIBRARY = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
SIZES = [150, 200, 250, 300, 350, 400]
REVIEW = {"status": "reviewed", "reviewedOn": "2026-11-18"}
EXISTING = [
    "scenario:evacuation", "scenario:hardlock",
    "scenario:uplink-center", "scenario:battleground",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Annihilation"}
        for page in (81, 82)
    ] + [
        {"sourceId": ES, "page": page, "section": "Aniquilación"}
        for page in (85, 86, 87)
    ]


def main() -> int:
    source = json.loads(ITS17.read_text(encoding="utf-8"))
    original_bytes = LIBRARY.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != source["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("ITS 17 shared-library SHA-256 mismatch")
    if [item["scenarioId"] for item in source["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 membership: refuses to overwrite")
    old = json.loads(original_bytes)
    if [item["id"] for item in old["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 shared definitions")

    current = load_curated_document(ITS18)
    record = deepcopy(next(
        item for item in current["records"] if item["id"] == "scenario:annihilation"
    ))
    record["summary"] = (
        "ITS Season 17 Seekers Annihilation: score by enemy Army Points "
        "Killed, surviving Victory Points and the enemy Lieutenant "
        "Killed. The original English and Spanish survival bands conflict."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    mission = record["facts"]["mission"]

    # The numeric ranges in EN p. 81 are independently confirmed by the
    # current EN chart; the ES p. 85 surviving-VP row gives different OP
    # awards. Never select or merge Spanish 3/4/4 as a second scoring rule
    # without an explicit source adjudication.
    objectives = {item["id"]: item for item in mission["objectives"]}
    if set(objectives) != {"destroy-forces", "preserve-forces", "eliminate-lieutenant"}:
        raise ValueError("Unexpected Annihilation objective schema")
    def bands(objective: dict) -> list[int]:
        return [
            next(award["objectivePoints"] for award in objective["awards"]
                 if award["armyPoints"] == [150] and
                 award["condition"]["minimum"] == minimum)
            for minimum in (40, 76, 126)
        ]
    if bands(objectives["destroy-forces"]) != [1, 3, 4]:
        raise ValueError("Unexpected Annihilation enemy-army-points band values")
    if bands(objectives["preserve-forces"]) != [1, 3, 4]:
        raise ValueError("Unexpected Annihilation surviving-VP band values")

    mission["sourceIssues"] = [
        {
            "id": "its17-surviving-vp-en-es-score-discrepancy",
            "armyPoints": SIZES,
            "objectiveId": "preserve-forces",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 81 awards 1/3/4 OP for the low/middle/high "
                "surviving Victory Point bands, while ES p. 85 prints 3/4/4 "
                "OP for those same numerical bands. The English chart is "
                "retained, not silently reconciled with the Spanish table."
            ),
        },
        {
            "id": "its17-150-point-deployment-units",
            "armyPoints": [150],
            "geometryElementIds": ["deployment-a", "deployment-b"],
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 82 prints [[distance:8:inch]] x [[distance:32:cm]] as the "
                "150-point "
                "Deployment Zone size; its own diagram instead depicts an "
                "[[distance:8:inch]]-deep zone spanning the [[distance:24:inch]] table width. "
                "ES p. 86 prints [[distance:20:cm]] x [[distance:60:cm]] and shows that geometry. "
                "Retain the reviewed map, not an invented mixed-unit zone."
            ),
        },
        {
            "id": "its17-350-point-destroy-forces-gap",
            "armyPoints": [350],
            "objectiveId": "destroy-forces",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 81 and ES p. 85 award 3 OP for "
                "176-274 enemy Army Points Killed and 4 OP for more than "
                "275, leaving exactly 275 without a printed award."
            ),
        },
        {
            "id": "its17-350-point-preserve-forces-gap",
            "armyPoints": [350],
            "objectiveId": "preserve-forces",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 81 and ES p. 85 print 176-274 and "
                "more than 275 surviving Victory Points for adjacent "
                "bands, leaving exactly 275 without a printed award. "
                "The language editions additionally disagree on the "
                "awarded OP as documented separately."
            ),
        },
    ]

    definition = {
        "id": "scenario:annihilation",
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
    current_text = original_bytes.decode("utf-8")
    ending = "    }\n  ]\n}\n"
    if not current_text.endswith(ending):
        raise ValueError("Unexpected shared library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated_text = current_text[:-len(ending)] + "    },\n" + addition + "\n  ]\n}\n"
    updated_bytes = updated_text.encode("utf-8")
    if [row["id"] for row in json.loads(updated_bytes)["definitions"]] != (
        EXISTING + ["scenario:annihilation"]
    ):
        raise ValueError("Unexpected shared-library content")

    source["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (reviewed Evacuation, Hardlock, "
        "Uplink Center, Battleground and Annihilation)"
    )
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:annihilation",
        "sharedDefinition": {
            "version": "its17-v0.2",
            "citations": citations(),
            "review": deepcopy(REVIEW),
            "componentCitations": {},
            "overrides": [],
        },
    })
    source["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(updated_bytes).hexdigest()
    LIBRARY.write_bytes(updated_bytes)
    ITS17.write_text(
        json.dumps(source, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    print("Added ITS 17 Annihilation with historical EN/ES discrepancies")
    print(f"Shared library SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
