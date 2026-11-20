"""Curate source-reviewed ITS 17 V0.2 Last Launch from bilingual originals.

EN pp. 63-67, ES pp. 75-80. Scoring, skills, and geometry match ITS 18;
retain historical token-diameter wording and season-local bilingual issues.
The migration refuses reruns and unexpected input identities.
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
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Last Launch"}
        for page in (63, 64, 65, 66, 67)
    ] + [
        {"sourceId": ES, "page": page, "section": "Último Lanzamiento"}
        for page in (75, 76, 77, 78, 79, 80)
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
        raise ValueError("ITS 17 shared-library SHA-256 mismatch")
    if [m["scenarioId"] for m in source["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    library = json.loads(original)
    if [d["id"] for d in library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 definitions; refusing overwrite")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in modern["records"] if row["id"] == "scenario:last-launch"
    ))
    record["summary"] = (
        "ITS Season 17 Last Launch: download and transfer IDs, extract identified "
        "Troopers from the Launching Tower, and score extracted points, "
        "Specialists, Tower Domination and three Classified Objectives."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    facts = record["facts"]
    mission = facts["mission"]
    if [o["id"] for o in mission["objectives"]] != [
        "extract-more-army-points", "extract-more-specialists",
        "kill-specialists-comparison", "dominate-launching-tower",
        "classified-objectives",
    ]:
        raise ValueError("Unexpected modern Last Launch objectives")
    if len(facts["configurations"]) != 3:
        raise ValueError("Unexpected Last Launch geometry count")
    rules = {rule["id"]: rule for rule in mission["rules"]}
    if set(rules) != {
        "deployment-and-launching-tower", "id-scanners", "download-id",
        "swap-id", "launching-tower-gates", "dominate-launching-tower",
        "id-checker", "extract-identified-trooper", "killing",
        "specialist-troops", "baggage-extracted", "no-quarter",
    }:
        raise ValueError("Unexpected modern Last Launch rule set")

    # Both ITS 17 language editions specify scenery size relative to its Token.
    rules["id-scanners"]["paragraphs"][0] = (
        "Two ID Scanners stand along the table centerline, each "
        "[[distance:4:inch]] from the table edge at 150 points and "
        "[[distance:8:inch]] otherwise (ES: [[distance:10:cm]] / "
        "[[distance:20:cm]]). Represent each with a Tech-Coffin Token or "
        "scenery of matching diameter. ITS 17 does not independently "
        "specify the 40 mm scenery size of ITS 18."
    )
    rules["id-checker"]["paragraphs"][0] = (
        "One ID Checker stands at the center of the Launching Tower. "
        "Represent it with a Console A Token or a piece of matching-diameter "
        "scenery; ITS 17 does not independently specify a 40 mm diameter."
    )
    rules["deployment-and-launching-tower"]["paragraphs"][2] = (
        "ITS 17 EN p. 65 specifies an [[distance:8:inch]] × "
        "[[distance:8:inch]] Launching Tower; ES p. 77 says "
        "[[distance:20:cm]] × [[distance:20:cm]]. This small unit "
        "difference is preserved as a bilingual source issue."
    )
    rules["launching-tower-gates"]["paragraphs"][0] = (
        "The Launching Tower has four Wide Gates centered on its walls, "
        "open at the start. ITS 17 ES p. 77 also explicitly requires "
        "Wide Gate Tokens or equivalent scenery and allows access "
        "regardless of Silhouette; EN p. 65 does not state that extra clause."
    )
    rules["dominate-launching-tower"]["paragraphs"][1] = (
        "A Trooper is inside the Tower if more than half its base lies "
        "inside. ITS 17 EN p. 65 counts Shasvastii Troopers in "
        "Unconscious or any non-Null State; ES p. 78 names Normal "
        "or Unconscious. The difference is unresolved."
    )
    extract = rules["extract-identified-trooper"]
    extract["skillFacts"]["sourceNotes"] = [
        "ITS 17 EN p. 66 refers to adding the removed Troopers' points "
        "(plural, including Peripherals removed inside the Tower), while "
        "ES p. 79 says the removed Trooper's cost (singular). Whether "
        "Peripheral costs contribute is not explicitly equivalent."
    ]
    extract["paragraphs"][1] = (
        "Remove the extracting Trooper and any of its Peripherals inside "
        "the Launching Tower. Extracted Army Points are Open Information; "
        "ITS 17 EN p. 66 refers to the removed Troopers' points, while "
        "ES p. 79 refers to the extracting Trooper's points alone. "
        "The Peripheral-cost interpretation remains unresolved."
    )
    mission["sourceIssues"] = [
        issue(
            "its17-last-launch-tower-dimensions-en-es",
            "dominate-launching-tower",
            "ITS 17 V0.2 EN p. 65 specifies an [[distance:8:inch]] × "
            "[[distance:8:inch]] Launching Tower; ES p. 77 gives "
            "[[distance:20:cm]] × [[distance:20:cm]]. Geometry uses the English "
            "dimensions without declaring these exact equivalents.",
        ),
        issue(
            "its17-last-launch-gate-access-en-es",
            "dominate-launching-tower",
            "ITS 17 V0.2 ES p. 77 requires Wide Gate Tokens or similar "
            "scenery and explicitly allows any Silhouette to pass. "
            "EN p. 65 only states that four Wide Gates start open.",
        ),
        issue(
            "its17-last-launch-shasvastii-states-en-es",
            "dominate-launching-tower",
            "ITS 17 V0.2 EN p. 65 counts Shasvastii Troopers while "
            "Unconscious or in any non-Null State; ES p. 78 specifically "
            "names Normal or Unconscious.",
        ),
        issue(
            "its17-last-launch-peripheral-points-en-es",
            "extract-more-army-points",
            "ITS 17 V0.2 EN p. 66 adds the removed Troopers' points "
            "after extracting a Trooper and its Peripherals inside "
            "the Tower; ES p. 79 refers to the removed Trooper's "
            "points in the singular. Whether Peripheral points count "
            "is not explicitly identical.",
        ),
    ]

    definition = {
        "id": "scenario:last-launch",
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
        EXISTING + ["scenario:last-launch"]
    ):
        raise ValueError("Unexpected ITS 17 shared-library result")
    source["collection"]["title"] = "ITS Season 17 Seekers V0.2 (ten reviewed scenarios)"
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:last-launch",
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
    print("Added ITS 17 Last Launch with 11 bilingual citation pages")
    print(f"Shared SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
