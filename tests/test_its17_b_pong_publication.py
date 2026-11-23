"""Original-source ITS 17 B-Pong migration and cross-season isolation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    build_its_database,
    inspect_its_database,
    select_its_scenario,
)
from tests.its17_inventory_expectations import EXPECTED_ITS17_SCENARIO_IDS

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
SIZES = [150, 200, 250, 300, 350, 400]


def records() -> tuple[dict, dict]:
    old = load_curated_document(SEASON, shared_scenario_library=SHARED)
    current = load_curated_document(ITS18)
    return (
        next(r for r in old["records"] if r["id"] == "scenario:b-pong"),
        next(r for r in current["records"] if r["id"] == "scenario:b-pong"),
    )


def test_its17_b_pong_is_independently_source_pinned() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert source["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [item["id"] for item in library["definitions"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    definition = library["definitions"][10]
    assert definition["id"] == "scenario:b-pong"
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = source["scenarioCollection"]["members"][10]
    assert member["scenarioId"] == "scenario:b-pong"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(c["sourceId"], c["page"]) for c in binding["citations"]] == [
        *((EN, page) for page in range(36, 40)),
        *((ES, page) for page in range(38, 42)),
        (EN, 13), (ES, 14),
    ]


def test_its17_b_pong_scoring_skills_and_map_geometry() -> None:
    old, current = records()
    original = old["facts"]
    modern = current["facts"]
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert original["playRequirements"] == {
        "classifiedObjectives": 2, "tacticalObjectives": 0, "hvts": 1,
    }
    assert original["mission"]["objectives"] == modern["mission"]["objectives"]
    assert original["mission"]["endConditions"] == modern["mission"]["endConditions"]
    assert original["mission"]["gameSizes"] == modern["mission"]["gameSizes"]
    # Same placements, but only ITS 17 has an undisputed physical footprint.
    from copy import deepcopy

    historical_configs = deepcopy(original["configurations"])
    for config in historical_configs:
        beacon = next(e for e in config["geometry"]["elements"] if e["id"] == "tracking-beacon")
        assert beacon.pop("diameterMm") == 25
    assert historical_configs == modern["configurations"]
    assert {
        o["id"]: o["maximumPoints"] for o in original["mission"]["objectives"]
    } == {
        "beacon-in-enemy-half": 2,
        "control-tracking-beacon": 3,
        "control-any-console": 3,
        "classified-objectives": 2,
    }
    for config, depth, exclusion, offset in zip(
        original["configurations"], (12, 16, 16),
        (2, 4, 4), (6, 8, 12), strict=True,
    ):
        geometry = config["geometry"]
        elements = {row["id"]: row for row in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == geometry["table"]["height"] - depth
        assert elements["exclusion-zone"]["y1"] == geometry["table"]["height"] / 2 - exclusion
        assert elements["exclusion-zone"]["y2"] == geometry["table"]["height"] / 2 + exclusion
        assert elements["console-left"]["x"] == offset
        assert elements["console-right"]["x"] == geometry["table"]["width"] - offset
        assert elements["tracking-beacon"]["x"] == geometry["table"]["width"] / 2
    for skill_id in ("relocate-tracking-beacon", "activate-console"):
        rules = {row["id"]: row for row in original["mission"]["rules"]}
        assert rules[skill_id]["skillTypeIds"] == ["short-skill"]


def test_its17_b_pong_preserves_only_original_bilingual_differences() -> None:
    old, current = records()
    historic = {r["id"]: r for r in old["facts"]["mission"]["rules"]}
    modern = {r["id"]: r for r in current["facts"]["mission"]["rules"]}
    assert "matching diameter" in historic["tracking-beacon-representation"]["paragraphs"][0]
    assert "40 mm" in modern["tracking-beacon-representation"]["paragraphs"][0]
    relocate = historic["relocate-tracking-beacon"]
    assert relocate["skillFacts"]["clarifications"] == []
    assert "[[distance:4:inch]]" in relocate["skillFacts"]["effects"][0]
    assert "Beacon's old position" in relocate["paragraphs"][1]
    assert "Trooper declaring the Order" in modern["relocate-tracking-beacon"]["paragraphs"][1]
    activate = historic["activate-console"]
    assert "Both ITS 17" in activate["skillFacts"]["restrictions"][0]
    assert "Spanish Activation entry omits" in (
        modern["activate-console"]["skillFacts"]["clarifications"][0]
    )
    assert "Conectada" in activate["skillFacts"]["sourceNotes"][0]
    assert "[[distance:15:cm]]" in activate["skillFacts"]["clarifications"][0]
    assert "Both ITS 17" in (
        historic["tracking-beacon-representation"]["paragraphs"][1]
    )
    issues = {item["id"]: item for item in old["facts"]["mission"]["sourceIssues"]}
    assert set(issues) == {
        "its17-b-pong-magnetize-distance-en-es",
        "its17-b-pong-console-connected-es",
    }
    assert all(item["armyPoints"] == SIZES for item in issues.values())
    assert all(item["status"] == "needs-verification" for item in issues.values())
    assert all("ITS 17 V0.2" in item["description"] for item in issues.values())
    assert not set(issues).intersection({
        issue["id"] for issue in current["facts"]["mission"]["sourceIssues"]
    })


def test_its17_b_pong_compiles_independently(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON, target, shared_library=SHARED)
    assert [item["id"] for item in report["scenarios"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2",
        scenario_id="scenario:b-pong",
    )
    assert selected is not None
    historic, _ = records()
    assert selected["record"] == historic
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:b-pong",
    ) is None
