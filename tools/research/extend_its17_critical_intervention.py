"""One-time source-reviewed ITS 17 V0.2 Critical Intervention migration.

English pp. 45-50 and Spanish pp. 63-69. Reuse matching ITS 18
scoring and geometry while preserving independent ITS 17 skill
wording, token sizes, turret targeting, and bilingual source issues.
Refuse unexpected source/definition identities and reruns.
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
    "scenario:corporate-appropriation",
]


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Critical Intervention"}
        for page in range(45, 51)
    ] + [
        {"sourceId": ES, "page": page, "section": "Intervención Crítica"}
        for page in range(63, 70)
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
        raise ValueError("Unexpected ITS 17 shared-library SHA-256")
    if [m["scenarioId"] for m in season["scenarioCollection"]["members"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 memberships; refusing overwrite")
    library = json.loads(original)
    if [d["id"] for d in library["definitions"]] != EXISTING:
        raise ValueError("Unexpected ITS 17 definitions; refusing overwrite")

    modern = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in modern["records"] if row["id"] == "scenario:critical-intervention"
    ))
    record["summary"] = (
        "ITS Season 17 Critical Intervention: asymmetrical Attacker/Defender "
        "objectives for extracting a Data Pack, holding the Server Room, "
        "and commanding or bypassing its defensive turret system."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    facts = record["facts"]
    mission = facts["mission"]
    expected_objectives = [
        "attacker-unlock-console", "attacker-extract-pack",
        "attacker-extractor-not-killed", "attacker-extractor-home",
        "attacker-dominate-room", "attacker-kill-threshold",
        "defender-prevent-unlock", "defender-prevent-extract",
        "defender-kill-extractor", "defender-dominate-room",
        "defender-kill-threshold", "classified-objective",
    ]
    if [row["id"] for row in mission["objectives"]] != expected_objectives:
        raise ValueError("Unexpected ITS 18 Critical Intervention objectives")
    if len(facts["configurations"]) != 3:
        raise ValueError("Unexpected ITS 18 Critical Intervention geometry")
    rules = {rule["id"]: rule for rule in mission["rules"]}
    if set(rules) != {
        "attacker-defender", "deployment-and-exclusion", "server-room",
        "dominate-zone", "defense-system", "data-console",
        "extract-data-pack", "data-pack", "inhibitor-antenna",
        "use-inhibitor-antenna", "specialist-troops", "killing",
        "intelcom-support-control",
    }:
        raise ValueError("Unexpected ITS 18 Critical Intervention rules")

    rules["server-room"]["paragraphs"] = [
        "The central Server Room is a Zone of Operations measuring "
        "[[distance:8:inch]] square in ITS 17 EN p. 47, or "
        "[[distance:20:cm]] square in ES p. 65. Its infinitely high walls "
        "block Line of Fire; four Wide Gates centered on the walls "
        "are open at the start of the game.",
        "Use Wide Gate Tokens or equal-size scenery (EN p. 47, ES p. 66). "
        "ITS 17 ES p. 66 additionally states that any Silhouette may "
        "access the room through these Gates. A numerical Gate width "
        "is not specified; the source map only places the openings.",
    ]
    rules["dominate-zone"]["paragraphs"] = [
        "To Dominate the Server Room ZO, a player must have more Victory "
        "Points of eligible Troopers inside than the opponent. Models, "
        "Trooper Markers, Proxies and Peripheral Troops count; Null-state "
        "Troops, non-Trooper equipment Tokens and fake Holoechoes do not.",
        "A Trooper is inside when more than half their base is inside. "
        "ITS 17 EN p. 47 includes Shasvastii-Embryo or any non-Null "
        "State; ES p. 66 specifically names Normal or Unconscious.",
        "A non-Null Baggage Trooper inside the Server Room adds 20 "
        "Victory Points for the Domination comparison.",
    ]
    rules["defense-system"]["paragraphs"] = [
        "Two Armed Turrets in different Server Room corners are represented "
        "by Defensive Turret A/B Tokens or Models/scenery of matching "
        "Silhouette (ITS 17 EN p. 48 / ES pp. 66–67). Turret positions "
        "are schematic; no footprint or corner clearance is specified.",
        "When active, the Server Room Defense System reacts with BS or "
        "CC Attacks to Orders declared by active enemy Models (not "
        "Markers) in Line of Fire or Silhouette contact. Both ITS 17 "
        "languages say 'enemy Models', not specifically Attacker Models.",
        "Both originals print CC 5, BS 10, WIP 11, ARM 2, BTS 3, "
        "STR 1, S 2, 360° Visor, Total Reaction, Combi Rifle, and "
        "PARA CC Weapon (-3). MOV and PH have no printed values.",
    ]
    rules["data-console"]["paragraphs"] = [
        "One Data Console at the center of the Server Room holds exactly "
        "one Data Pack. Represent it with a Console A Token or scenery "
        "of matching diameter (ITS 17 EN p. 48 / ES p. 67). "
        "Neither edition specifies an independent 40 mm dimension.",
    ]
    rules["inhibitor-antenna"]["paragraphs"] = [
        "One Inhibitor Antenna stands next to an exterior Server Room "
        "corner in the Defender's table half. It uses a Transmission "
        "Antenna Token or matching-diameter scenery (ITS 17 EN p. 49 "
        "/ ES p. 68), without a specified fixed 40 mm footprint.",
    ]
    rules["extract-data-pack"]["name"] = "Extract Data Pack (Attacker Only)"
    rules["extract-data-pack"]["skillFacts"]["sourceNotes"] = [
        "ITS 17 EN pp. 48–49 and ES p. 67: Attack, Scenario Short Skill. "
        "Both originals impose WIP-6 before unlocking the Data Console "
        "and unmodified WIP after unlocking; failed attempts are repeatable.",
    ]
    rules["use-inhibitor-antenna"]["name"] = "Use Inhibitor Antenna"
    rules["use-inhibitor-antenna"]["skillFacts"]["sourceNotes"] = [
        "ITS 17 EN pp. 49–50 and ES p. 68: Attack, Scenario Short Skill. "
        "Unlock Data Console only for the Attacker; either player may "
        "activate or deactivate the Server Room Defense System.",
    ]
    rules["intelcom-support-control"]["paragraphs"] = [
        "After selecting the Classified Objective but before the game "
        "begins, each player declares whether the card will be used as "
        "Classified or INTELCOM. Both roll a die; the high roller "
        "announces first, while the mission/number on the card stays "
        "Private Information.",
        "At the end of the final Game Round, in Initiative order, a "
        "player with at least one non-Null Trooper in the Server Room "
        "may apply the INTELCOM numeric value in Support and Control "
        "Mode to that Zone's Domination comparison.",
        "ITS 17 EN p. 50 calls this adding the card's value to Victory "
        "Points inside a chosen ZO; ES p. 69 says Army Points "
        "(Puntos de Ejército). Preserve the source terminology difference.",
    ]
    mission["sourceIssues"] = [
        issue(
            "its17-critical-intervention-defender-maximum",
            "defender-prevent-extract",
            "ITS 17 V0.2 EN p. 45 and ES pp. 63–64 each print Defender "
            "Main Objectives worth 1 + 3 + 2 + 3 + 2 = 11 OP, plus "
            "one Classified OP, for a possible 12. Preserve the "
            "printed awards without silently imposing a 10-point cap.",
        ),
        issue(
            "its17-critical-intervention-room-dimension-en-es",
            "attacker-dominate-room",
            "ITS 17 V0.2 EN p. 47 gives an [[distance:8:inch]] square "
            "Server Room while ES p. 65 says [[distance:20:cm]] square. "
            "The geometry follows English inches; these are not exact "
            "physical equivalents.",
        ),
        issue(
            "its17-critical-intervention-gate-access-es",
            "attacker-dominate-room",
            "ITS 17 V0.2 ES p. 66 explicitly grants Wide Gate access "
            "regardless of Silhouette. EN p. 47 says Gates are open "
            "and describes their representation, but not that clause.",
        ),
        issue(
            "its17-critical-intervention-shasvastii-en-es",
            "defender-dominate-room",
            "ITS 17 V0.2 EN p. 47 counts Shasvastii-Embryo or any "
            "non-Null State in the Server Room; ES p. 66 instead "
            "specifies Normal or Unconscious.",
        ),
        issue(
            "its17-critical-intervention-intelcom-points-en-es",
            "attacker-dominate-room",
            "ITS 17 V0.2 EN p. 50 applies INTELCOM numeric value to "
            "Victory Points within a ZO; ES p. 69 says Army Points "
            "(Puntos de Ejército). This is a terminology discrepancy.",
        ),
        issue(
            "its17-critical-intervention-exclusion-distance-en-es",
            "attacker-kill-threshold",
            "ITS 17 V0.2 EN p. 46 places the exclusion boundary "
            "[[distance:4:inch]] either side of center; ES p. 65 "
            "says [[distance:10:cm]]. Geometry follows English inches.",
        ),
    ]

    definition = {
        "id": "scenario:critical-intervention",
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
    if [row["id"] for row in json.loads(updated)["definitions"]] != (
        EXISTING + ["scenario:critical-intervention"]
    ):
        raise ValueError("Unexpected ITS 17 shared-library result")
    season["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (fourteen reviewed scenarios)"
    )
    season["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:critical-intervention",
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
    print("Added ITS 17 Critical Intervention with 13 bilingual source citations")
    print(f"Shared SHA-256: {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
