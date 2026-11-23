"""One-time ITS 17 V0.2 Battleground migration with independent scoring.

Reviewed official originals:
  ITS 17 V0.2 EN pp. 83-85; ES pp. 88-90.
  ITS 18 2026.09.11 EN pp. 129-131.
Only source-matched geometry and rules carry forward; ITS 17 has separate
1/3/4 sector scoring, mutually exclusive Key Ops awards and source issues.
Not part of normal builds; refuses reruns and unexpected input changes.
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
ARMY_POINTS = [150, 200, 250, 300, 350, 400]
REVIEW = {"status": "reviewed", "reviewedOn": "2026-11-18"}
EXISTING = [
    "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Battleground"}
        for page in (83, 84, 85)
    ] + [
        {"sourceId": ES, "page": page, "section": "Campo de Batalla"}
        for page in (88, 89, 90)
    ]


def main() -> int:
    source = json.loads(ITS17.read_text(encoding="utf-8"))
    original_bytes = LIBRARY.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != source["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("ITS 17 shared-library SHA-256 mismatch")
    if [member["scenarioId"] for member in source["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("ITS 17 memberships differ; refusing to overwrite")
    library = json.loads(original_bytes)
    if [entry["id"] for entry in library["definitions"]] != EXISTING:
        raise ValueError("ITS 17 library definitions differ; refusing to overwrite")

    original = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in original["records"] if row["id"] == "scenario:battleground"
    ))
    record["summary"] = (
        "ITS Season 17 Seekers Battleground: dominate three Sectors for "
        "1/3/4 Objective Points and Kill or alternatively Threaten the enemy Key Ops."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)

    mission = record["facts"]["mission"]
    scores = {"near-sector-a": 1, "near-sector-b": 1,
              "central-sector": 3, "far-sector-a": 4, "far-sector-b": 4}
    for objective in mission["objectives"]:
        value = scores[objective["id"]]
        objective["maximumPoints"] = value
        if len(objective["awards"]) != 1:
            raise ValueError("Unexpected Battleground sector award count")
        objective["awards"][0]["objectivePoints"] = value

    # Both source languages explicitly call the two Key Ops awards
    # alternatives. One capped exclusive objective prevents 2+1 overcount.
    mission["objectives"].append({
        "id": "enemy-key-ops",
        "name": "Enemy Key Ops: Kill or Threaten",
        "sideIds": ["side-a", "side-b"],
        "timing": "end-of-game",
        "aggregation": "exclusive",
        "maximumPoints": 2,
        "awards": [
            {
                "armyPoints": ARMY_POINTS,
                "objectivePoints": 2,
                "condition": {
                    "kind": "reviewed-prose",
                    "text": (
                        "Kill the enemy Key Ops: it enters Dead State, is in a "
                        "Null State at the end of the game, or has not been "
                        "deployed on the table as a Model or Marker by game end."
                    ),
                },
            },
            {
                "armyPoints": ARMY_POINTS,
                "objectivePoints": 1,
                "condition": {
                    "kind": "reviewed-prose",
                    "text": (
                        "Alternatively to Killing (not in addition), at the "
                        "end of the game Threaten the enemy Key Ops with at "
                        "least one friendly non-Null Trooper represented as a "
                        "Model (not a Marker) inside its Zone of Control."
                    ),
                },
            },
        ],
    })
    mission["rules"].extend([
        {
            "id": "key-ops",
            "name": "Key Ops",
            "paragraphs": [
                "At the end of Deployment, in Initiative order, each player "
                "designates a Key Ops from their Army List. The chosen Trooper "
                "must be deployed on the table as a Model, not a Marker or in "
                "Hidden Deployment, and must remain represented as a Model. "
                "Irregular Troopers and REM or VH Troop Types are excluded "
                "in the ITS 17 English publication; the Spanish text omits VH.",
                "The designated Key Ops gains [[skill:dodge|Dodge (+3)]] and "
                "[[skill:tactical-awareness|Tactical Awareness]] even if "
                "not shown on its Unit Profile. These extra Skills do not "
                "stack with existing instances. Identify the Key Ops with "
                "a Player A or B Marker.",
            ],
        },
        {
            "id": "threaten-key-ops",
            "name": "Threaten Key Ops",
            "paragraphs": [
                "At the end of the game, an enemy Key Ops is Threatened when "
                "you have at least one non-Null Trooper, as a Model and not "
                "a Marker, inside that Key Ops' Zone of Control. "
                "Threatening earns 1 OP instead of (not alongside) the "
                "2 OP for Killing the enemy Key Ops."
            ],
        },
    ])

    mission["sourceIssues"] = [
        {
            "id": "key-ops-vh-eligibility-en-es",
            "armyPoints": ARMY_POINTS,
            "objectiveId": "enemy-key-ops",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 85 forbids REM and VH Troop Types from "
                "Key Ops designation, but ES p. 90 names only REM. The "
                "English exclusion is retained while the bilingual "
                "difference remains unresolved."
            ),
        },
        {
            "id": "shasvastii-embryo-eligibility-en-es",
            "armyPoints": ARMY_POINTS,
            "objectiveId": "central-sector",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 84 says Shasvastii Troopers count in "
                "Unconscious or any non-Null State. ES p. 89 instead "
                "specifies Normal or Shasvastii Embryo. Do not silently "
                "equate those state sets; the English rule is retained."
            ),
        },
    ]

    for configuration in record["facts"]["configurations"]:
        for element in configuration["geometry"]["elements"]:
            if element["kind"] != "label":
                continue
            label = element.get("text")
            replacements = {
                "A: 2 OP · B: 5 OP": "A: 1 OP · B: 4 OP",
                "A: 5 OP · B: 2 OP": "A: 4 OP · B: 1 OP",
            }
            if label in replacements:
                element["text"] = replacements[label]
        # A shared layout does not license the ITS 18 scoring labels.
        labels = [
            element.get("text", "")
            for element in configuration["geometry"]["elements"]
            if element["kind"] == "label"
        ]
        if not any("A: 1 OP · B: 4 OP" == label for label in labels):
            raise ValueError("Missing expected historical near sector map label")
        if not any("A: 4 OP · B: 1 OP" == label for label in labels):
            raise ValueError("Missing expected historical far sector map label")

    definition = {
        "id": "scenario:battleground",
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
    if [item["id"] for item in json.loads(updated_bytes)["definitions"]] != (
        EXISTING + ["scenario:battleground"]
    ):
        raise ValueError("Unexpected shared definitions after migration")

    source["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (reviewed Evacuation, Hardlock, "
        "Uplink Center and Battleground)"
    )
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:battleground",
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
    print("Added distinct ITS 17 Battleground definition and six bilingual citations")
    print(f"Shared SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
