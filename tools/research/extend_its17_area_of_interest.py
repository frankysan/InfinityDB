"""One-time ITS 17 V0.2 Area of Interest publication from official originals.

EN pp. 77-80 and ES pp. 80-84. Scoring and geometry match ITS 18,
but source-local antenna size, Shasvastii, ARO, INTELCOM, activation
and Reinforcements-language distinctions must remain separate.
This migration refuses reruns and unexpected input identities.
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
    "scenario:superiority", "scenario:provisioning",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Area of Interest"}
        for page in (77, 78, 79, 80)
    ] + [
        {"sourceId": ES, "page": page, "section": "Área de Interés"}
        for page in (80, 81, 82, 83, 84)
    ]


def main() -> int:
    source = json.loads(ITS17.read_text(encoding="utf-8"))
    old_bytes = SHARED.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != source["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("ITS 17 source-library SHA-256 mismatch")
    if [row["scenarioId"] for row in source["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    library = json.loads(old_bytes)
    if [row["id"] for row in library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 shared-library definitions")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in modern["records"] if row["id"] == "scenario:area-of-interest"
    ))
    record["summary"] = (
        "ITS Season 17 Area of Interest: Dominate player-placed Areas and "
        "the Special Area, Activate the central Antenna each round, and "
        "choose between a Classified Objective and INTELCOM."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    mission = record["facts"]["mission"]
    if [row["id"] for row in mission["objectives"]] != [
        "dominate-areas", "dominate-special-area",
        "activate-antenna", "classified-objective",
    ]:
        raise ValueError("Unexpected modern Area of Interest objectives")
    rules = {row["id"]: row for row in mission["rules"]}
    if set(rules) != {
        "deployment", "communication-antenna",
        "activate-communication-antenna", "player-placed-areas",
        "dominate-zones", "specialist-troops", "intelcom",
    }:
        raise ValueError("Unexpected modern Area of Interest rules")
    rules["communication-antenna"]["paragraphs"][0] = (
        "One Communication Antenna stands at the table center, represented "
        "by a Transmission Antenna Token (TRANS. ANTENNA) or scenery "
        "of matching diameter. Neither ITS 17 language edition "
        "independently specifies a 40 mm diameter. Player A/B Tokens "
        "can mark its current Activation."
    )
    activation = rules["activate-communication-antenna"]
    activation["skillFacts"]["sourceNotes"] = [
        "ITS 17 EN p. 78 says one enemy Hacker within an Area of Interest "
        "can oppose with an ARO; ES p. 82 requires selecting one Hacker. "
        "The mandatory/optional distinction is unresolved.",
        "ITS 17 ES p. 82 calls the Antenna Connected on initial "
        "activation but Activated when describing later changes "
        "of control; the EN edition consistently calls it Activated.",
    ]
    activation["paragraphs"][1] = (
        "An enemy Hacker within an Area of Interest can oppose an "
        "Activation with an ARO, making a Face to Face WIP Roll. "
        "ITS 17 Spanish requires choosing a Hacker for this ARO; "
        "English uses optional wording. A failed attempt can be repeated."
    )
    rules["dominate-zones"]["paragraphs"][2] = (
        "ITS 17 English counts Troopers with [[skill:shasvastii|Shasvastii]] "
        "while Unconscious or in any non-Null State; Spanish names "
        "Normal or Unconscious. This bilingual state-set distinction "
        "is unresolved. Non-Null Troopers with "
        "[[equipment:baggage|Baggage]] add 20 Victory Points for Domination."
    )
    rules["intelcom"]["paragraphs"][2] = (
        "INTELCOM adds Victory Points in the chosen Area of Interest "
        "rather than awarding Objective Points directly. ITS 17 EN "
        "p. 80 places this at the end of the last Game Round, whereas "
        "ES pp. 83–84 explicitly name the third Game Round; "
        "Retreat! may end the game earlier."
    )
    mission["sourceIssues"] = [
        {
            "id": "its17-reinforcements-en-es",
            "armyPoints": SIZES,
            "objectiveId": "dominate-areas",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 77 explicitly marks Area of Interest "
                "suitable for Reinforcements (YES), but ES p. 80 "
                "explicitly states NO. Do not select one language "
                "as an unqualified season-wide permission."
            ),
        },
        {
            "id": "its17-hacker-aro-optional-vs-mandatory",
            "armyPoints": SIZES,
            "objectiveId": "activate-antenna",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 78 permits one enemy Hacker inside "
                "an Area of Interest to declare an ARO; ES p. 82 "
                "requires choosing one enemy Hacker for the ARO."
            ),
        },
        {
            "id": "its17-shasvastii-zo-states-en-es",
            "armyPoints": SIZES,
            "objectiveId": "dominate-areas",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 79 counts Shasvastii Troopers "
                "Unconscious or in any non-Null State; ES p. 83 "
                "specifies Normal or Unconscious. The state sets "
                "must not be silently equated."
            ),
        },
        {
            "id": "its17-intelcom-final-vs-third-round",
            "armyPoints": SIZES,
            "objectiveId": "dominate-areas",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 EN p. 80 allows INTELCOM at the end of "
                "the last Game Round; ES pp. 83–84 name the end of "
                "the third Game Round even though Retreat! can end "
                "the mission earlier."
            ),
        },
        {
            "id": "its17-connected-vs-activated-antenna-es",
            "armyPoints": SIZES,
            "objectiveId": "activate-antenna",
            "status": "needs-verification",
            "description": (
                "ITS 17 V0.2 ES p. 82 says the Antenna is Conectada "
                "on a successful activation but Activada when "
                "describing control changes. EN p. 78 uses Activated."
            ),
        },
    ]
    definition = {
        "id": "scenario:area-of-interest",
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
    text = old_bytes.decode("utf-8")
    ending = "    }\n  ]\n}\n"
    if not text.endswith(ending):
        raise ValueError("Unexpected historical library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated = (text[:-len(ending)] + "    },\n" + addition + "\n  ]\n}\n").encode("utf-8")
    if [row["id"] for row in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:area-of-interest"]
    ):
        raise ValueError("Unexpected shared-library result")

    source["collection"]["title"] = "ITS Season 17 Seekers V0.2 (nine reviewed scenarios)"
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:area-of-interest",
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
    print("Added source-pinned ITS 17 Area of Interest and nine bilingual pages")
    print(f"Shared SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
