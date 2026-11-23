"""One-time source-reviewed ITS 17 Uplink Center library extension.

Evidence: ITS 17 V0.2 English pp. 93-96, Spanish pp. 99-102,
compared with ITS 18 2026.09.11 English pp. 139-142 and
Spanish pp. 144-147. Refuses reruns and preserves existing definitions.
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
REVIEW = {"status": "reviewed", "reviewedOn": "2026-11-18"}


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Uplink Center"}
        for page in range(93, 97)
    ] + [
        {"sourceId": ES, "page": page, "section": "Uplink Center"}
        for page in range(99, 103)
    ]


def main() -> int:
    source = json.loads(ITS17.read_text(encoding="utf-8"))
    original_bytes = LIBRARY.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != source["sharedScenarioLibrary"]["sha256"]:
        raise ValueError("Existing ITS 17 library SHA-256 mismatch")
    if [member["scenarioId"] for member in source["scenarioCollection"]["members"]] != [
        "scenario:evacuation", "scenario:hardlock",
    ]:
        raise ValueError("ITS 17 memberships already changed; refusing to overwrite")
    existing = json.loads(original_bytes)
    if [item["id"] for item in existing["definitions"]] != [
        "scenario:evacuation", "scenario:hardlock",
    ]:
        raise ValueError("Unexpected existing shared definitions")

    original = load_curated_document(ITS18)
    record = deepcopy(next(
        row for row in original["records"] if row["id"] == "scenario:uplink-center"
    ))
    record["summary"] = (
        "ITS Season 17 Seekers Uplink Center: Activate and Control the two "
        "Communication Antennas, Control the Tech-Coffin and keep an Active Lieutenant."
    )
    record["scope"]["seasons"] = ["its-17"]
    record["citations"] = citations()
    record["review"] = deepcopy(REVIEW)
    mission = record["facts"]["mission"]
    rules = {rule["id"]: rule for rule in mission["rules"]}
    rules["deployment-and-objectives"]["paragraphs"][1] = (
        "Two Communication Antennas are on the table centerline, "
        "[[distance:6:inch]] from the side edges at 150 points, "
        "[[distance:8:inch]] at 200/250 points, and [[distance:12:inch]] "
        "at 300/350/400 points. The Tech-Coffin is at the table center. "
        "Each objective uses its named Token or scenery of the same diameter; "
        "the ITS 17 mission does not independently specify a numeric diameter."
    )
    # This is an omission in the ES sentence, not a second placement rule:
    # the ES map depicts the 350-point layout with 300/400.
    mission["sourceIssues"] = [{
        "id": "spanish-antenna-350-placement-omission",
        "armyPoints": [350],
        "objectiveId": "activate-communication-antennas",
        "status": "needs-verification",
        "description": (
            "ITS 17 V0.2 EN p. 94 explicitly groups 300/350/400-point games "
            "for the [[distance:12:inch]] Antenna offset, but ES p. 100 lists "
            "only 400/300. Both printed mission maps (EN p. 93, ES p. 99) "
            "group 300/350/400 in the same layout. Treat the Spanish "
            "sentence as an omission, not an alternate 350-point placement."
        ),
    }]

    definition = {
        "id": "scenario:uplink-center",
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
    expected_end = "    }\n  ]\n}\n"
    if not current_text.endswith(expected_end):
        raise ValueError("Unexpected shared-library serialization")
    addition = indent(json.dumps(definition, indent=2, ensure_ascii=False), "    ")
    updated_text = (
        current_text[:-len(expected_end)]
        + "    },\n"
        + addition
        + "\n  ]\n}\n"
    )
    updated_bytes = updated_text.encode("utf-8")
    if len(json.loads(updated_bytes)["definitions"]) != 3:
        raise ValueError("Shared library should have three definitions")

    source["collection"]["title"] = (
        "ITS Season 17 Seekers V0.2 (reviewed Evacuation, Hardlock and Uplink Center)"
    )
    source["scenarioCollection"]["members"].append({
        "scenarioId": "scenario:uplink-center",
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
    print(f"Added source-reviewed ITS 17 Uplink Center to {LIBRARY.name}")
    print(f"New SHA-256: {source['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
