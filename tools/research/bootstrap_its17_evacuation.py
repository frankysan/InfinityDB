"""One-time, source-reviewed ITS 17 V0.2 Evacuation shared-authoring bootstrap.

Run once after reviewing ITS 17 EN pp. 55–58, ES pp. 50–53 and
ITS 18 EN pp. 88–91. Refuses existing outputs: never regenerate over
human-curated facts. The standalone season stays unregistered at runtime.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from infinity_db.curated import load_curated_document
from infinity_db.scenario_reuse import LIBRARY_FORMAT

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/curated/its/n5-its-season-18.json"
SHARED = ROOT / "data/curated/its/shared/evacuation-v1.json"
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
REVISION = "0.2"
COLLECTION = "its-season-17-v0.2"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
REVIEW = {"status": "reviewed", "reviewedOn": "2026-11-18"}


def citations() -> list[dict]:
    return [
        {"sourceId": EN, "page": page, "section": "Evacuation"}
        for page in (55, 56, 57, 58)
    ] + [
        {"sourceId": ES, "page": page, "section": "Evacuación"}
        for page in (50, 51, 52, 53)
    ]


def main() -> int:
    # Source-backed bootstrap is intentionally not a general migration utility.
    if SHARED.exists() or SEASON.exists():
        raise ValueError("ITS 17 curated outputs already exist; never overwrite reviewed work")
    original = load_curated_document(SOURCE)
    scenario = deepcopy(next(row for row in original["records"]
                             if row["id"] == "scenario:evacuation"))
    scenario["summary"] = (
        "ITS Season 17 Seekers Evacuation: extract map-placed Civilians or enemy "
        "HVTs using Extraction Consoles, with two Classified Objectives."
    )
    scenario["scope"]["seasons"] = ["its-17"]
    scenario["citations"] = citations()
    scenario["review"] = deepcopy(REVIEW)
    mission = scenario["facts"]["mission"]
    rules = {row["id"]: row for row in mission["rules"]}
    rules["extraction-consoles"]["paragraphs"][0] = (
        "Two Extraction Consoles begin on the table centerline at the "
        "printed positions. Each is a Console A Token or a scenery piece "
        "of the same diameter as that Token."
    )
    issues = {row["id"]: row for row in mission["sourceIssues"]}
    issues["classified-points-bilingual"]["description"] = (
        "ITS 17 V0.2 EN p. 55 explicitly gives 2 Objective Points per Classified "
        "Objective for two Objectives. ES p. 50 instead states two Classified "
        "Objectives and '2 Puntos de Objetivo' without 'each'. Preserve this "
        "language-scope ambiguity; follow the explicit English scoring."
    )
    issues["activation-first-round-bilingual"]["description"] = (
        "ITS 17 V0.2 EN p. 57 prohibits Activate Extraction Console in the first "
        "Game Round; ES p. 52 uses 'primer Turno de Juego' (first Game Turn), "
        "not the usual Spanish term for Game Round. Preserve the unresolved "
        "timing distinction."
    )
    issues["reactivation-english-omission"]["description"] = (
        "ITS 17 V0.2 ES p. 52 expressly allows reactivating a Console previously "
        "activated by an opponent; EN p. 57 does not contain the corresponding "
        "sentence. One successful activation extracts one CivEvaced subject."
    )
    # The validated legacy definition format keeps geometry and mission
    # rules together. A later typed-component migration may extract them
    # once rule inclusion semantics are reviewed for both editions.
    original_sources = [EN, ES]
    shared = {
        "format": LIBRARY_FORMAT, "formatVersion": 1, "id": "its-evacuation",
        "definitions": [{
            "id": scenario["id"], "version": "its17-v0.2",
            "origin": {
                "sourceCollectionId": COLLECTION,
                "seasonId": "its-17", "revision": REVISION,
                "sourceIds": original_sources,
            },
            "record": scenario,
            "components": [],
        }],
    }
    published_sources = [
        {
            "id": EN, "kind": "pdf",
            "title": "ITS 17 Seekers V0.2 (English)", "version": REVISION,
            "publishedDate": "2026-03-09", "authority": "primary",
            "pageCount": 105,
            "localPath": "data/pdf/legacy/its_17/its-rules-season-17-v0.2-en.pdf",
            "sha256": "73a184b80535f23499000bb81112d95168c12f970fa14a30050a95ec51cdfe71",
            "url": "https://downloads.corvusbelli.com/infinity/organized-play/"
                   "its-rules-season-17-en-v1.0.2.pdf",
        },
        {
            "id": ES, "kind": "pdf",
            "title": "ITS 17 Seekers V0.2 (Spanish)", "version": REVISION,
            "publishedDate": "2026-03-09", "authority": "primary",
            "pageCount": 112,
            "localPath": "data/pdf/legacy/its_17/its-rules-season-17-v0.2-es.pdf",
            "sha256": "d202d7e3373852204b848fa8eee3bbc19000695cec0296c9882e7d0f3a030457",
            "url": "https://downloads.corvusbelli.com/infinity/organized-play/"
                   "its-rules-season-17-es-v1.0.2.pdf",
        },
    ]
    library_bytes = (json.dumps(shared, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    document = {
        "format": original["format"],
        "formatVersion": original["formatVersion"],
        "collection": {
            "id": COLLECTION,
            "title": "ITS Season 17 Seekers V0.2 (reviewed Evacuation)",
            "domain": "its", "status": "archived",
            "effectiveFrom": "2026-03-09", "authority": "primary",
        },
        "scenarioCollection": {
            "id": "its-17", "title": "ITS Season 17 Seekers",
            "revision": REVISION,
            "members": [{
                "scenarioId": scenario["id"],
                "sharedDefinition": {
                    "version": "its17-v0.2",
                    "citations": citations(),
                    "review": deepcopy(REVIEW),
                    "componentCitations": {},
                    "overrides": [],
                },
            }],
        },
        "vocabularySources": original["vocabularySources"],
        "skillTypes": original["skillTypes"],
        "labels": [],
        "sources": published_sources,
        "seasonPolicies": [],
        "records": [],
        "sharedScenarioLibrary": {
            "id": shared["id"],
            "sha256": hashlib.sha256(library_bytes).hexdigest(),
        },
    }
    SHARED.parent.mkdir(parents=True, exist_ok=True)
    SHARED.write_bytes(library_bytes)
    try:
        SEASON.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")
    except Exception:
        SHARED.unlink(missing_ok=True)
        raise
    print(f"Created {SHARED.relative_to(ROOT)} and {SEASON.relative_to(ROOT)}")
    print(f"Shared SHA-256 {document['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
