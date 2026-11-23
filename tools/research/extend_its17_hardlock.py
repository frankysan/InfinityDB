"""One-time reviewed ITS 17 V0.2 Hardlock migration into the season library.

Evidence: ITS 17 V0.2 EN pp. 59-62 and ES pp. 54-57, compared
against ITS 18 2026.09.11 EN pp. 49-52 / ES pp. 127-130.
Refuses reruns and only edits the two historical authoring files.
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
OLD_LIBRARY = ROOT / "data/curated/its/shared/evacuation-v1.json"
NEW_LIBRARY = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
REVIEW = {"status": "reviewed", "reviewedOn": "2026-11-18"}


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Hardlock"}
        for page in range(59, 63)
    ] + [
        {"sourceId": ES, "page": page, "section": "Hardlock"}
        for page in range(54, 58)
    ]


def main() -> int:
    if NEW_LIBRARY.exists() or not OLD_LIBRARY.is_file():
        raise ValueError("ITS 17 library already migrated or legacy library missing")
    source = json.loads(ITS17.read_text(encoding="utf-8"))
    legacy_bytes = OLD_LIBRARY.read_bytes()
    if hashlib.sha256(legacy_bytes).hexdigest() != source["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("Previous ITS 17 shared library SHA-256 does not match")
    if [member["scenarioId"] for member in source["scenarioCollection"]["members"]] != [
        "scenario:evacuation",
    ]:
        raise ValueError("Unexpected historical scenario membership; refusing overwrite")

    original = load_curated_document(ITS18)
    scenario = deepcopy(
        next(row for row in original["records"] if row["id"] == "scenario:hardlock")
    )
    scenario["summary"] = (
        "ITS Season 17 Seekers Hardlock: Activate three centerline Consoles, "
        "pick up and Control the opposing Beacon, and complete one Classified Objective."
    )
    scenario["scope"]["seasons"] = ["its-17"]
    scenario["citations"] = citations()
    scenario["review"] = deepcopy(REVIEW)

    mission = scenario["facts"]["mission"]
    rules = {row["id"]: row for row in mission["rules"]}
    rules["deployment-and-objectives"]["paragraphs"][1] = (
        "There are two Beacons, one for each player, positioned in the middle of "
        "the front edge of each Deployment Zone. The one beside the opponent's "
        "Deployment Zone is the Enemy Beacon. Three Consoles stand along the "
        "table centerline: one at the center, with the others [[distance:6:inch]] from "
        "the side edges at 150 points, [[distance:8:inch]] at 200/250 points "
        "and [[distance:12:inch]] "
        "at 300/350/400 points. Each Console uses a Console A Token or scenery "
        "of the same diameter as that Token; the ITS 17 mission does not state "
        "an independent millimeter diameter."
    )
    rules["classified-objective"]["paragraphs"][0] = (
        "Each player has one Classified Objective, worth 1 Objective Point "
        "if completed."
    )
    issues = {row["id"]: row for row in mission["sourceIssues"]}
    issues["connected-vs-activated-console"]["description"] = (
        "ITS 17 V0.2 EN p. 60 requires an Activated Console to Pick Up Beacon, "
        "whereas ES p. 55 says 'Consola Conectada'; its activation procedure "
        "on ES pp. 56-57 uses both Conectada and Activada. Preserve the "
        "terminology discrepancy without asserting a second Console state."
    )
    issues["allied-beacon-carrier-normal-state"]["description"] = (
        "ITS 17 V0.2 EN p. 60 requires a friendly Beacon carrier in Normal "
        "State for transfer; ES p. 55 does not repeat the Normal State "
        "qualification. Preserve the English restriction and the bilingual gap."
    )

    definition = {
        "id": "scenario:hardlock",
        "version": "its17-v0.2",
        "origin": {
            "sourceCollectionId": source["collection"]["id"],
            "seasonId": "its-17",
            "revision": "0.2",
            "sourceIds": [EN, ES],
        },
        "record": scenario,
        "components": [],
    }
    # Preserve the Evacuation definition byte-for-byte, apart from the new
    # generic library name and the one comma separating two definitions.
    current_text = legacy_bytes.decode("utf-8")
    expected_end = "    }\n  ]\n}\n"
    if not current_text.endswith(expected_end):
        raise ValueError("Unexpected historical shared-library serialization")
    renamed = current_text.replace('"id": "its-evacuation",', '"id": "its17-scenarios",', 1)
    serialized = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    new_text = renamed[:-len(expected_end)] + "    },\n" + serialized + "\n  ]\n}\n"
    library_bytes = new_text.encode("utf-8")
    library = json.loads(new_text)
    if [entry["id"] for entry in library["definitions"]] != [
        "scenario:evacuation", "scenario:hardlock",
    ]:
        raise ValueError("Unexpected shared definition content")

    source["collection"]["title"] = "ITS Season 17 Seekers V0.2 (reviewed Evacuation and Hardlock)"
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:hardlock",
        "sharedDefinition": {
            "version": "its17-v0.2",
            "citations": citations(),
            "review": deepcopy(REVIEW),
            "componentCitations": {},
            "overrides": [],
        },
    })
    source["sharedScenarioLibrary"] = {
        "id": library["id"],
        "sha256": hashlib.sha256(library_bytes).hexdigest(),
    }

    NEW_LIBRARY.write_bytes(library_bytes)
    ITS17.write_text(
        json.dumps(source, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    OLD_LIBRARY.unlink()
    print(f"Migrated {OLD_LIBRARY.name} to {NEW_LIBRARY.name} with two definitions")
    print(f"Shared SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
