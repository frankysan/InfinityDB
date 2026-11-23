"""One-time source-reviewed ITS 17 V0.2 Crossing Lines migration.

ITS 17 originals: EN pp. 51-54 / ES pp. 42-45. The objectives, three
maps, Antenna action, and endings match ITS 18, but source-local Antenna
representation, Shasvastii, HVT and English strip-width claims do not.
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
    "scenario:last-launch", "scenario:b-pong",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Crossing Lines"}
        for page in (51, 52, 53, 54)
    ] + [
        {"sourceId": ES, "page": page, "section": "Cruce de Líneas"}
        for page in (42, 43, 44, 45)
    ]


def issue(issue_id: str, objective_id: str, description: str) -> dict:
    return {
        "id": issue_id,
        "armyPoints": SIZES,
        "objectiveId": objective_id,
        "status": "needs-verification",
        "description": description,
    }


def main() -> int:
    source = json.loads(ITS17.read_text(encoding="utf-8"))
    original = SHARED.read_bytes()
    if hashlib.sha256(original).hexdigest() != source["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("Unexpected ITS 17 shared library SHA-256; refusing overwrite")
    if [m["scenarioId"] for m in source["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    library = json.loads(original)
    if [d["id"] for d in library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 definitions; refusing overwrite")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in modern["records"] if row["id"] == "scenario:crossing-lines"
    ))
    record["summary"] = (
        "ITS Season 17 Crossing Lines: Dominate both Dead Zones across a split "
        "deployment, Activate the two Antennas, and score without Classified Objectives."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    facts = record["facts"]
    mission = facts["mission"]
    if [objective["id"] for objective in mission["objectives"]] != [
        "dominate-dead-zone-a", "dominate-dead-zone-b",
        "dominate-both-dead-zones", "activate-antennas",
    ]:
        raise ValueError("Unexpected ITS 18 Crossing Lines scoring")
    if len(facts["configurations"]) != 3:
        raise ValueError("Unexpected ITS 18 Crossing Lines geometry")
    rules = {rule["id"]: rule for rule in mission["rules"]}
    if set(rules) != {
        "deployment-and-exclusion", "dominate-zo", "activate-antenna",
        "specialist-troops", "no-hvt-classified",
    }:
        raise ValueError("Unexpected ITS 18 Crossing Lines rules")

    # The English table's central-strip length appears to use the longer
    # table dimension for 150/200/250 points. Use source-consistent Spanish
    # dimensions and the already reviewed ITS 18 geometry without silently
    # treating the English table as equivalent.
    rules["deployment-and-exclusion"]["paragraphs"][0] = (
        "Each player has a rear Deployment Zone and a second Deployment "
        "Zone in the opposing half of the table, inside the central strip. "
        "Up to 75 Army Points of Troops can deploy in the central strip. "
        "Both forward Zones are [[distance:4:inch]] deep (ES "
        "[[distance:10:cm]])."
    )
    rules["deployment-and-exclusion"]["paragraphs"][1] = (
        "Two Dead Zones between the Deployment Zones are Exclusion Zones. "
        "Airborne Deployment and Superior Deployment cannot be used "
        "to deploy inside them."
    )
    rules["deployment-and-exclusion"]["paragraphs"][2] = (
        "No Trooper may deploy in Silhouette contact with an Antenna. "
        "Superior Deployment Skills are prohibited except Impersonation."
    )
    rules["dominate-zo"]["paragraphs"][2] = (
        "ITS 17 EN p. 53 says Shasvastii Troops inside the ZO count while "
        "in Shasvastii-Embryo or any non-Null State; ES p. 44 specifies "
        "Normal or Unconscious instead. Baggage Troops in non-Null "
        "States add 20 Victory Points to Domination."
    )
    antenna = rules["activate-antenna"]
    antenna["paragraphs"][0] = (
        "Two Antennas are positioned on the centerline, "
        "[[distance:6:inch]] / [[distance:8:inch]] / "
        "[[distance:12:inch]] from the table edges at 150 / 200–250 / "
        "300–400 points respectively. ITS 17 EN p. 53 requires a "
        "Transmission Antenna Token or matching-diameter scenery; "
        "ES p. 44 instead specifies a Console A Token or equivalent "
        "same-diameter scenery. Neither specifies a fixed 40 mm size."
    )
    antenna["skillFacts"]["sourceNotes"] = [
        "ITS 17 V0.2 EN p. 53 represents Antennas with Transmission Antenna "
        "Tokens; ES p. 44 says Console A Tokens. Both say matching-diameter "
        "scenery; do not inherit ITS 18's explicit 40 mm requirement."
    ]
    rules["no-hvt-classified"]["name"] = (
        "Secure HVT and Secure Treasure not used"
    )
    rules["no-hvt-classified"]["paragraphs"] = [
        "There are no Classified Objectives in ITS 17 Crossing Lines. "
        "The mission explicitly does not apply Secure HVT or Secure "
        "Treasure (EN p. 54 / ES p. 45).",
        "Unlike ITS 18, ITS 17 does not explicitly say that the HVT Model "
        "must not be deployed or that the Classified Deck is not used. "
        "The zero-HVT play-context projection is retained provisionally "
        "and this source gap is recorded for verification.",
    ]
    mission["sourceIssues"] = [
        issue(
            "its17-crossing-lines-central-strip-en-es",
            "dominate-dead-zone-a",
            "ITS 17 EN pp. 51-52 describe central strips of "
            "[[distance:4:inch]] × [[distance:32:inch]] at 150 points "
            "and [[distance:4:inch]] × [[distance:48:inch]] at "
            "200/250 points, whereas ES p. 42 describes "
            "[[distance:10:cm]] × [[distance:60:cm]] and "
            "[[distance:10:cm]] × [[distance:80:cm]] respectively. "
            "The English strip length conflicts with table width. "
            "Geometry follows the Spanish widths and published layout.",
        ),
        issue(
            "its17-crossing-lines-shasvastii-states-en-es",
            "dominate-dead-zone-a",
            "ITS 17 EN p. 53 counts Shasvastii Troops in "
            "Shasvastii-Embryo or any non-Null State; ES p. 44 "
            "says Normal or Unconscious. The formulations differ.",
        ),
        issue(
            "its17-crossing-lines-antenna-token-en-es",
            "activate-antennas",
            "ITS 17 EN p. 53 represents an Antenna with a "
            "Transmission Antenna Token; ES p. 44 instead says "
            "Console A Token. Both allow scenery matching that "
            "Token's diameter without independently fixing a 40 mm size.",
        ),
        issue(
            "its17-crossing-lines-hvt-source-gap",
            "dominate-both-dead-zones",
            "ITS 17 EN p. 54 / ES p. 45 disable Secure HVT and "
            "Secure Treasure but do not explicitly prohibit HVT Model "
            "deployment. The no-HVT play-context count follows the "
            "existing edition's schema and needs source verification; "
            "ITS 18's explicit no-HVT/no-Classified-Deck clause cannot "
            "be attributed to ITS 17.",
        ),
    ]
    definition = {
        "id": "scenario:crossing-lines",
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
        EXISTING + ["scenario:crossing-lines"]
    ):
        raise ValueError("Unexpected ITS 17 library result")
    source["collection"]["title"] = "ITS Season 17 Seekers V0.2 (twelve reviewed scenarios)"
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:crossing-lines",
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
    print("Added ITS 17 Crossing Lines with eight original citation pages")
    print(f"Shared SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
