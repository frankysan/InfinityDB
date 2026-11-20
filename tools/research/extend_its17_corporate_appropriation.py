"""Curate ITS 17 V0.2 Corporate Appropriation against bilingual originals.

Original sources: EN pp. 40–44; ES pp. 32–37. Independent historical
rules are required for token diameters, ADS/targeting, source conflicts
and the typed Use Panoply action. Refuses unexpected/rerun inputs.
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
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Corporate Appropriation"}
        for page in range(40, 45)
    ] + [
        {"sourceId": ES, "page": page, "section": "Apropiación Corporativa"}
        for page in range(32, 38)
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
    season = json.loads(ITS17.read_text(encoding="utf-8"))
    original = SHARED.read_bytes()
    if hashlib.sha256(original).hexdigest() != season["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("ITS 17 shared-library SHA-256 mismatch")
    if [m["scenarioId"] for m in season["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    library = json.loads(original)
    if [d["id"] for d in library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 definitions; refusing overwrite")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in modern["records"]
        if row["id"] == "scenario:corporate-appropriation"
    ))
    record["summary"] = (
        "ITS Season 17 Corporate Appropriation: Capture or Destroy Prototypes, "
        "collect Panoply equipment and complete three Classified Objectives."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    facts = record["facts"]
    mission = facts["mission"]
    if [o["id"] for o in mission["objectives"]] != [
        "capture-enemy-prototype", "bring-enemy-prototype-home",
        "own-prototype-outcome", "more-panoply-gear", "classified-objectives",
    ]:
        raise ValueError("Unexpected modern Corporate Appropriation objectives")
    if len(facts["configurations"]) != 3:
        raise ValueError("Unexpected modern Corporate Appropriation geometry")
    rules = {rule["id"]: rule for rule in mission["rules"]}
    if set(rules) != {
        "forces-exclusion", "prototype-profile", "automated-defense-system",
        "destroy-prototypes", "pick-up-prototype", "common-prototype-rules",
        "capture-prototype", "panoplies", "panoply-chart", "specialist-troops",
    }:
        raise ValueError("Unexpected modern Corporate Appropriation rules")

    rules["prototype-profile"]["paragraphs"] = [
        "Two Prototypes stand on the centerline at [[distance:6:inch]] / "
        "[[distance:8:inch]] / [[distance:12:inch]] from the table edges "
        "at 150 / 200–250 / 300–400 points. Before deployment, the "
        "second-turn player assigns which belongs to each side. "
        "Represent them with Objective Tokens or scenery of matching "
        "diameter; ITS 17 does not specify a 40 mm footprint.",
        "Each Prototype has ARM 6, BTS 6, STR 3 and S 3, with Fixed CC "
        "Roll 8 and GizmoKit (PH 9). Both ITS 17 EN p. 41 and ES p. 33 "
        "allow targeting a Prototype only if no allied or enemy Trooper "
        "would also be affected by the Attack.",
    ]
    rules["automated-defense-system"]["paragraphs"] = [
        "Each CC Attack against a Prototype triggers a Face to Face ADS "
        "CC Attack with a fixed Roll of 8. ITS 17 EN p. 42 and ES p. 34 "
        "both prohibit applying any MODs to the attacker's CC Attribute.",
        "A successful ADS Roll imposes a Stun Ammunition hit, PS 5, "
        "requiring one BTS Saving Roll. Immunity (Enhanced) and "
        "Immunity (BTS) do not protect against this hit.",
    ]
    rules["pick-up-prototype"]["name"] = "Pick Up Prototype"
    rules["common-prototype-rules"]["paragraphs"][0] = (
        "Carriers cannot declare Move as the second Basic Short Skill of "
        "an Order except with Baggage. ITS 17 EN p. 43 calls Baggage a "
        "Special Skill; ES p. 35 calls it Equipment. Only Models, not "
        "Markers, can carry Prototypes."
    )
    rules["capture-prototype"]["paragraphs"] = [
        "A player Captures the enemy Prototype at game end when a "
        "non-Null Model, not a Marker, carries it. ITS 17 EN p. 43 "
        "disallows contact with any enemy Model; ES p. 35 says enemy "
        "Trooper contact and explicitly disregards Null-state Models. "
        "The exact enemy-contact scope remains a source issue.",
    ]
    capture = next(
        o for o in mission["objectives"] if o["id"] == "capture-enemy-prototype"
    )
    capture["awards"][0]["condition"]["text"] = (
        "At game end, a non-Null Model (not Marker) carries the enemy "
        "Prototype without disqualifying enemy Silhouette contact. "
        "EN p. 43 says any enemy Model; ES p. 35 disregards Null-state "
        "Models. Preserve the bilingual source issue."
    )
    rules["panoplies"]["paragraphs"] = [
        "Two Panoplies, one in each table half, are at the midpoint of "
        "the forward boundary of each Deployment Zone. Use an Objective "
        "Token or matching-diameter scenery; ITS 17 gives no fixed 40 mm.",
        "A Trooper in Silhouette contact with a Panoply can spend one "
        "Short Skill to cancel Unloaded State. The separate Use Panoply "
        "Short Skill governs acquiring D-Charges or other equipment.",
    ]
    use_panoply = {
        "id": "use-panoply",
        "name": "Use Panoply",
        "skillTypeIds": ["short-skill"],
        "skillFacts": {
            "requirements": [
                "The Trooper must be in Silhouette contact with a Panoply.",
            ],
            "effects": [
                "With a successful Normal WIP Roll, acquire D-Charges or "
                "roll on the Panoply Chart for a weapon or item.",
                "Troopers with Booty or another applicable Special Skill "
                "do not need to perform the WIP Roll.",
                "If the chart yields an already-owned weapon or item, "
                "repeat that chart Roll.",
            ],
            "restrictions": [
                "After a success, the same Trooper cannot use that Panoply "
                "again.",
            ],
            "clarifications": [
                "An in-contact Trooper may spend one Short Skill to "
                "cancel Unloaded State; this is also described under "
                "the Panoplies rule.",
            ],
            "sourceNotes": [
                "ITS 17 EN pp. 43–44 / ES p. 36 call this an "
                "Attack, Scenario Short Skill.",
            ],
        },
        "paragraphs": [
            "Attack, Scenario Short Skill. A Trooper in Silhouette contact "
            "with a Panoply rolls Normal WIP to obtain D-Charges or a "
            "Panoply Chart result. A Trooper with Booty or another "
            "applicable Skill needs no WIP Roll.",
            "A successful user cannot use that same Panoply again; "
            "duplicates from the chart may be rerolled.",
        ],
    }
    index = next(
        i for i, rule in enumerate(mission["rules"])
        if rule["id"] == "panoply-chart"
    )
    mission["rules"].insert(index, use_panoply)
    mission["sourceIssues"] = [
        issue(
            "its17-corporate-appropriation-reinforcements-en-es",
            "more-panoply-gear",
            "ITS 17 V0.2 EN p. 40 says Suitable for Reinforcements YES, "
            "while ES p. 32 says NO. This source-level conflict does "
            "not alter the independently reviewed objective facts.",
        ),
        issue(
            "its17-corporate-appropriation-capture-contact-en-es",
            "capture-enemy-prototype",
            "ITS 17 V0.2 EN p. 43 prohibits contact with any enemy "
            "Model for Capture; ES p. 35 says enemy Troopers and "
            "explicitly excludes Null-state Models from consideration.",
        ),
        issue(
            "its17-corporate-appropriation-baggage-classification-en-es",
            "capture-enemy-prototype",
            "ITS 17 V0.2 EN p. 43 calls Baggage a Special Skill "
            "for the carrier's Move exception, while ES p. 35 calls "
            "Baggage a piece of Equipment. The exception itself matches.",
        ),
    ]
    definition = {
        "id": "scenario:corporate-appropriation",
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
        raise ValueError("Unexpected ITS 17 shared-library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated = (text[:-len(ending)] + "    },\n" + addition + "\n  ]\n}\n").encode("utf-8")
    if [d["id"] for d in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:corporate-appropriation"]
    ):
        raise ValueError("Unexpected ITS 17 shared-library result")
    season["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (thirteen reviewed scenarios)"
    )
    season["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:corporate-appropriation",
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
    print("Added ITS 17 Corporate Appropriation with 11 original citation pages")
    print(f"Shared SHA-256: {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
