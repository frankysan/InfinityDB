"""Add the independently reviewed ITS 17 V0.2 Resilience Operations Extra.

This is a tournament format, not a seventeenth standard scenario. The source
review uses all relevant original EN pp. 96–104 and ES pp. 103–111.
The resulting Rule belongs only to the unregistered ITS 17 SQLite build.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
ID = "rule:resilience-operations"


def _record() -> dict:
    return {
        "id": ID,
        "kind": "rule",
        "name": "Resilience Operations",
        "summary": (
            "Optional ITS Season 17 tournament Extra using Tactical Objective and Battle "
            "Condition decks in place of standard ITS missions and Classified Objectives. "
            "This is an alternate event format, not a standard scenario."
        ),
        "composition": {"role": "definition"},
        "scope": {"game": "N5", "seasons": ["its-17"]},
        "facts": {
            "category": "optional-extra",
            "applicability": {
                "context": "resilience-operations-extra", "revision": "0.2",
            },
            "tacticalObjectives": {
                "draw": 4, "discard": 1, "maxPointsPerCard": 3,
                "completionMinimum": 1, "moreCompletedBonus": 1,
                "commandTokenRedraw": 1, "revealPerRound": 1,
                "priorityTargetFirst": True, "privateUntilRevealed": True,
            },
            "battleConditions": {
                "draw": 2, "discard": 1, "appliesToBoth": True,
                "wholeGame": True, "duplicateResolution": "second-player-redraws",
                "stackMovementBonuses": False,
            },
            "gameSizes": [
                {"armyPoints": points, "swc": swc, "tableWidthIn": width,
                 "tableHeightIn": height, "deploymentDepthIn": depth}
                for points, swc, width, height, depth in (
                    (150, 3, 24, 32, 8),
                    (200, 4, 32, 48, 12),
                    (250, 5, 32, 48, 12),
                    (300, 6, 48, 48, 12),
                    (350, 7, 48, 48, 12),
                    (400, 8, 48, 48, 12),
                )
            ],
            "tacticalElements": [
                {
                    "id": "beacons", "quantity": "2 per player (4 total)",
                    "placement": (
                        "Before deployment, fully within each player's Deployment Zone "
                        "and in Silhouette contact with its boundary. The player who "
                        "kept Deployment places theirs first."
                    ),
                    "rules": [
                        "Beacon Token or matching 25 mm scenery (EN p. 13, ES p. 14).",
                        "ARM 4, BTS 4, STR 3, S2; GizmoKit (PH=10).",
                        "Only Anti-materiel Weapons may damage a Beacon; Engineer or "
                        "GizmoKit can repair it; remove when STR reaches zero.",
                        "Troopers may not deploy in Silhouette contact with a Beacon.",
                    ],
                },
                {
                    "id": "hvts", "quantity": "4 per player (8 total)",
                    "placement": (
                        "Before deployment, entirely within the area extending 4 inches "
                        "from that player's Deployment Zone (ES: 10 cm). "
                        "The player who kept Deployment places theirs first."
                    ),
                    "rules": [
                        "Follow ITS Civilian rules except this placement; Troopers may not "
                        "deploy in Silhouette contact with an HVT.",
                        "Normal HVT: CC 6, BS 5, PH 10, WIP 11, S2; the English MOV is '--' "
                        "but the Spanish profile prints 10-10 (cm).",
                        "A Battle Condition may specify hostile/reactive HVTs: "
                        "MOV 4-4 inches (ES 10-10 cm), CC 6, BS 8, PH 11, WIP 11, "
                        "ARM 1, BTS 0, VITA 1, S2; Stun Pistol.",
                    ],
                },
                {
                    "id": "beepers",
                    "quantity": "1 per Trooper; each Specialist Trooper has 1 additional Beeper",
                    "placement": (
                        "Deploy using the Place Deployable Skill, not as part of a "
                        "Coordinated Order; represented by a Player A/B Token or an "
                        "S2 Model/scenery."
                    ),
                    "rules": [
                        "ARM 2, BTS 0, STR 1, S2; destroyed at STR 0 or less.",
                        "Player A/B Token diameter is 25 mm (EN p. 13 / ES p. 14).",
                        "Beepers can be damaged by Attacks.",
                    ],
                },
                {
                    "id": "objectives", "quantity": "3 per player (6 total)",
                    "placement": (
                        "Before deployment, wholly within an 8-inch (ES: 20 cm) band "
                        "from the table centerline in that player's half. "
                        "The player who kept Deployment places theirs first."
                    ),
                    "rules": [
                        "Objective Token or matching 40 mm scenery (EN p. 13 / ES p. 14).",
                        "No deployment in Silhouette contact with an Objective.",
                    ],
                },
                {
                    "id": "f13-defensive-turrets",
                    "quantity": "Only when specified by a Battle Condition",
                    "placement": (
                        "Not initially deployed by default; place according to "
                        "the selected Battle Condition card."
                    ),
                    "rules": [
                        "ARM 2, BTS 3, STR 1, S2; CC 5, BS 10; 360-degree Visor, "
                        "Total Reaction, Combi Rifle and PARA (-3) CCW.",
                        "Respond with BS or CC Attack to Orders by active enemy Models "
                        "(not Markers) in LoF or Silhouette contact.",
                        "Defensive Turret Token diameter 25 mm (EN p. 13 / ES p. 14), "
                        "or an S2 Model/scenery; remove at STR 0 or less.",
                    ],
                },
            ],
            "glossary": [
                {
                    "id": "capture",
                    "text": (
                        "Capture Tactical Element is an Attack Short Skill without a Roll. "
                        "It requires Silhouette contact with a Null-State Model carrying "
                        "an Element, an allied Trooper carrying one, or an uncarried Element."
                    ),
                },
                {
                    "id": "captured-elements",
                    "text": (
                        "Only Models may carry; normally one Element per Model, two with "
                        "Baggage. Keep the Token on the table in Silhouette contact with "
                        "its carrier; drop it when the carrier enters/is in a Null State. "
                        "Carried Elements do not block movement or LoF."
                    ),
                },
                {
                    "id": "control",
                    "text": (
                        "A Tactical Element is Controlled if the player alone has a "
                        "non-Null Trooper Model (not Marker) in Silhouette contact, "
                        "with no enemy Trooper Model in contact."
                    ),
                },
                {
                    "id": "dominate",
                    "text": (
                        "Dominate a Quadrant/Sector by having more Victory Points in it "
                        "than the opponent. More than half a Trooper's base must be inside; "
                        "count non-Null Models/Markers including Proxies and Peripherals, "
                        "not weapon Tokens or fake Holoechoes. Non-Null Baggage adds 20 VP."
                    ),
                },
                {
                    "id": "killing",
                    "text": (
                        "Enemy Troopers count as Killed on entering Dead State, being in "
                        "a Null State at game end, or not being deployed as a Model or "
                        "Marker at game end."
                    ),
                },
                {
                    "id": "subjugate",
                    "text": (
                        "Subjugate a Quadrant/Sector if the player alone has a non-Null "
                        "Trooper Model (not Marker) with more than half its base inside, "
                        "and no enemy Trooper inside."
                    ),
                },
            ],
            "effects": [
                "Replace the normal ITS Scenario and Classified Deck with the Tactical "
                "Objective and Battle Condition decks; ordinary ITS tournament rules "
                "otherwise apply.",
                "After learning the opposing Faction but before Army List selection, "
                "each player draws four Tactical Objective cards, discards one and may "
                "spend one Command Token to swap a selected card for a new draw. "
                "Selected cards apply only to their owner and remain Private Information "
                "until revealed, unless otherwise stated.",
                "Reveal one chosen Tactical Objective simultaneously each Game Round; "
                "Priority Target must be revealed first if selected. Show all selected "
                "cards to the opponent at game end.",
                "After Initiative and before Deployment, each player draws two Battle "
                "Conditions and discards one; reveal and apply in Initiative order. "
                "When identical, the second-turn player discards and redraws.",
                "Battle Conditions affect both players all game; if multiple conditions "
                "grant Movement Bonuses, use only one.",
                "Sides deploy on opposite table edges. The game ends after the third "
                "Game Round, or at the end of a player's Turn if they began their "
                "Active Turn in Retreat!. Place all Tactical Elements except "
                "conditional F-13 Turrets before deployment.",
            ],
            "restrictions": [
                "Not selectable as an ordinary ITS scenario; the 16-member historical "
                "scenarioCollection does not contain this Extra.",
                "The pinned PDFs describe the Tactical Objective and Battle Condition "
                "selection process, not the complete contents of either physical deck. "
                "No unavailable card text or derived card-specific points are claimed.",
            ],
            "sourceNotes": [
                "EN p. 97 describes first card reveal at the beginning of Game Round 1; "
                "ES p. 104 explicitly places it after Deployment but before that Round. "
                "The sequence diagrams agree on reveal after Deployment.",
                "EN p. 100 prints normal HVT MOV '--', while ES p. 107 prints 10-10 (cm). "
                "The conflicting profile is not normalized.",
                "ES p. 106 explicitly says a failed Beacon repair Roll does not reduce "
                "STR; EN p. 99 does not state that additional clause.",
                "EN p. 103 calls Baggage a Special Skill for captured Element capacity, "
                "but the same page calls it Equipment for Dominate; ES pp. 110-111 "
                "uses Equipment. Preserve the source inconsistency.",
            ],
        },
        "citations": [
            {"sourceId": EN, "page": page, "section": "Resilience Operations"}
            for page in range(96, 105)
        ] + [
            {"sourceId": ES, "page": page, "section": "Operaciones de Resiliencia"}
            for page in range(103, 112)
        ] + [
            {"sourceId": EN, "page": 13, "section": "Diameter of ITS Tokens"},
            {"sourceId": ES, "page": 14, "section": "Diámetro de los Tokens ITS"},
        ],
        "review": {"status": "reviewed", "reviewedOn": "2026-11-19"},
    }


def main() -> int:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    original = [entry["id"] for entry in season["records"]]
    if original != ["skill:civevac", "skill:casevac", "state:casevac"]:
        raise ValueError("Unexpected ITS 17 record inventory; refusing to overwrite")
    members = season["scenarioCollection"]["members"]
    if len(members) != 16 or len({m["scenarioId"] for m in members}) != 16:
        raise ValueError("Unexpected ITS 17 membership inventory")
    if season["scenarioCollection"]["revision"] != "0.2":
        raise ValueError("Unexpected historical revision")
    if hashlib.sha256(SHARED.read_bytes()).hexdigest() != (
        season["sharedScenarioLibrary"]["sha256"]
    ):
        raise ValueError("ITS 17 source no longer pins its reviewed shared definitions")
    if {source["id"] for source in season["sources"]} != {EN, ES}:
        raise ValueError("ITS 17 original source inventory has changed")
    season["records"].append(_record())
    SEASON.write_text(
        json.dumps(season, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"Curated {ID} as a season-local Extra; scenario memberships: {len(members)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
