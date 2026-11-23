"""One-time source-reviewed ITS 17 V0.2 Akial Interference migration.

Originals: EN pp. 31–35 and ES pp. 58–62. Source-local token sizing,
Secure Treasure exclusion, Skill citations and once-per-round ambiguity
must not inherit ITS 18 provenance.
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
    "scenario:outbreak",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": p, "section": "Akial Interference"}
        for p in range(31, 36)
    ] + [
        {"sourceId": ES, "page": p, "section": "Interferencia Akial"}
        for p in range(58, 63)
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
        raise ValueError("Unexpected ITS 17 definitions; refusing overwrite")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(
        r for r in modern["records"] if r["id"] == "scenario:akial-interference"
    ))
    record["summary"] = (
        "ITS Season 17 Akial Interference: complete Common Classified "
        "Objectives, use the central Antenna to cancel or replace public "
        "cards, and score one private Classified Objective."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    facts = record["facts"]
    mission = facts["mission"]
    if [r["id"] for r in mission["objectives"]] != [
        "common-classified", "more-classified",
        "classified-every-round", "private-classified",
    ]:
        raise ValueError("Unexpected modern Akial objective list")
    if [r["maximumPoints"] for r in mission["objectives"]] != [6, 1, 1, 2]:
        raise ValueError("Unexpected modern Akial scoring")
    if facts["playRequirements"] != {
        "classifiedObjectives": 1,
        "tacticalObjectives": 0,
        "hvts": 4,
        "sharedClassifiedObjectivesPerRound": 2,
    }:
        raise ValueError("Unexpected modern Akial play context")
    if len(facts["configurations"]) != 3:
        raise ValueError("Unexpected modern Akial geometry")
    rules = {r["id"]: r for r in mission["rules"]}
    if set(rules) != {
        "deployment", "common-classified", "private-classified",
        "signal-redundancy", "multiple-hvts", "akial-antenna",
        "emit-akial-interference", "filter-signal", "specialist-troops",
    }:
        raise ValueError("Unexpected modern Akial mission rules")

    rules["multiple-hvts"]["name"] = "Multiple HVTs and Exclusions"
    rules["multiple-hvts"]["paragraphs"] = [
        "Each player deploys four HVT Models following standard HVT "
        "deployment rules. Each HVT may be used for only one Classified "
        "Objective; once an HVT-targeting Objective is completed, "
        "that HVT Model is removed from the table.",
        "Neither Secure HVT nor Secure Treasure applies (ITS 17 V0.2 "
        "EN p. 33 and ES p. 60). The HVT Models themselves still deploy.",
    ]
    rules["akial-antenna"]["paragraphs"] = [
        "One Akial Antenna stands at the center of the table (ITS 17 "
        "EN p. 33 and ES p. 60). Represent it with a Transmission "
        "Antenna Token (TRANS. ANTENNA) or a scenery piece matching "
        "the Token's diameter. Neither original fixes a 40 mm size.",
        "The Akial Antenna is used by Emit Akial Interference and "
        "Filter the Signal. No deployment in Silhouette contact with "
        "the Antenna or any HVT is permitted.",
    ]

    emit = rules["emit-akial-interference"]
    emit["skillCitations"] = [
        {"sourceId": EN, "page": 33},
        {"sourceId": EN, "page": 34},
        {"sourceId": ES, "page": 61},
    ]
    emit["skillFacts"]["requirements"] = [
        "Only a Specialist Troop in Silhouette contact with the Akial "
        "Antenna may declare this Attack, Scenario Short Skill.",
        "The player's completed Common Classified Objective must bear "
        "one of the four symbols pictured in ITS 17 EN p. 34 / "
        "ES p. 61. Each such Common card may be chosen only once.",
        "Each Specialist Troop may Emit Akial Interference only once "
        "per Game Round, subject to the source's unresolved wording "
        "about retrying failed WIP Rolls.",
    ]
    emit["skillFacts"]["effects"] = [
        "Make a Normal WIP Roll to Emit Akial Interference. A failed "
        "Roll may be retried by spending another Short Skill.",
        "On success, cancel an opponent's accomplished Common "
        "Classified Objective sharing a symbol with a Common "
        "Classified Objective previously accomplished by the player. "
        "The opponent no longer counts that card; discard it if neither "
        "player has accomplished it.",
    ]
    emit["skillFacts"]["restrictions"] = [
        "Only accomplished Common Classified Objectives may be selected "
        "for Emission or score final Common Classified points; Private "
        "Classified Objectives are not eligible.",
        "Each eligible accomplished Common card can be chosen only "
        "once for this Skill, and each Specialist can Emit no more "
        "than once per Game Round.",
    ]
    emit["skillFacts"]["clarifications"] = [
        "ITS 17 EN p. 34 and ES p. 61 both say each Specialist may "
        "Emit only once per Round yet also allow repeated failed "
        "attempts; the texts do not resolve whether the limit "
        "counts attempts or successful emissions.",
    ]
    emit["skillFacts"]["sourceNotes"] = [
        "ITS 17 V0.2 EN pp. 33–34 / ES p. 61: Short Skill with Attack "
        "and Scenario Labels; required four symbols are pictured "
        "rather than spelled out in the extracted PDF text.",
    ]
    emit["paragraphs"] = [
        "Attack, Scenario Short Skill. A Specialist Troop in "
        "Silhouette contact with the Akial Antenna may Emit "
        "Interference if the player has accomplished a Common "
        "Classified card bearing one of the four printed symbols. "
        "Each eligible card may be chosen once.",
        "Make a Normal WIP Roll; failed attempts may be retried "
        "with additional Short Skills. Both originals also limit "
        "each Specialist to Emitting once per Game Round without "
        "clarifying whether the limit covers failed attempts.",
        "On success, cancel an opponent's accomplished Common "
        "Classified card sharing a printed symbol with one "
        "previously accomplished by the player. That opponent "
        "no longer counts the completion; discard the card "
        "if neither player has accomplished it.",
        "Only accomplished Common cards score or can be "
        "selected for Emission. Private Classified cards cannot "
        "Emit or be canceled.",
    ]

    filtering = rules["filter-signal"]
    filtering["skillCitations"] = [
        {"sourceId": EN, "page": 34},
        {"sourceId": ES, "page": 62},
    ]
    filtering["skillFacts"]["sourceNotes"] = [
        "ITS 17 V0.2 EN p. 34 / ES p. 62: Attack, Scenario Short Skill, "
        "without a Roll.",
    ]

    mission["sourceIssues"] = [{
        "id": "its17-akial-interference-emit-retries-per-round",
        "armyPoints": SIZES,
        "objectiveId": "common-classified",
        "status": "needs-verification",
        "description": (
            "ITS 17 V0.2 EN p. 34 and ES p. 61 both allow "
            "repeating failed Normal WIP Rolls to Emit Akial "
            "Interference while also restricting each Specialist "
            "to one Emission per Game Round. The sources do not "
            "explicitly distinguish attempts from successes."
        ),
    }]
    if "its-season-18" in json.dumps(record) or "ITS 18" in json.dumps(record):
        raise ValueError("ITS 18 provenance remains in historical Akial record")

    definition = {
        "id": "scenario:akial-interference",
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
    if [d["id"] for d in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:akial-interference"]
    ):
        raise ValueError("Unexpected ITS 17 library result")
    season["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (sixteen reviewed scenarios)"
    )
    season["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:akial-interference",
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
    print("Added ITS 17 Akial Interference with 10 bilingual citation pages")
    print(f"Shared SHA-256: {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
