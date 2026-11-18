"""Source-reviewed ITS 17 V0.2 Hardlock preserved alongside current ITS 18."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import build_its_database, select_its_scenario

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"


def hardlock_records() -> tuple[dict, dict]:
    historic = load_curated_document(SEASON, shared_scenario_library=SHARED)
    current = load_curated_document(ITS18)
    return (
        next(record for record in historic["records"] if record["id"] == "scenario:hardlock"),
        next(record for record in current["records"] if record["id"] == "scenario:hardlock"),
    )


def test_its17_hardlock_uses_pinned_historical_membership_and_citations() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    shared = json.loads(SHARED.read_text(encoding="utf-8"))
    assert source["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [entry["id"] for entry in shared["definitions"]] == [
        "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
        "scenario:battleground",
        "scenario:annihilation",
        "scenario:cutthroat",
        "scenario:superiority",
        "scenario:provisioning",
        "scenario:area-of-interest",
        "scenario:last-launch",
        "scenario:b-pong",
        "scenario:crossing-lines",
        "scenario:corporate-appropriation",
        "scenario:critical-intervention",
        "scenario:outbreak",
    ]
    definition = shared["definitions"][1]
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    membership = source["scenarioCollection"]["members"][1]
    assert membership["scenarioId"] == definition["id"]
    binding = membership["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(citation["sourceId"], citation["page"]) for citation in binding["citations"]] == [
        *((EN, page) for page in (59, 60, 61, 62)),
        *((ES, page) for page in (54, 55, 56, 57)),
    ]


def test_its17_hardlock_preserves_verified_scoring_geometry_and_source_differences() -> None:
    historical, current = hardlock_records()
    assert historical["scope"]["seasons"] == ["its-17"]
    assert historical["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {citation["sourceId"] for citation in historical["citations"]} == {EN, ES}

    # Both source sets independently establish the scoring, positions, two
    # Short Skills, specialist restrictions and termination conditions.
    assert historical["facts"]["playRequirements"] == current["facts"]["playRequirements"]
    assert historical["facts"]["mission"]["gameSizes"] == current["facts"]["mission"]["gameSizes"]
    assert historical["facts"]["mission"]["objectives"] == current["facts"]["mission"]["objectives"]
    assert historical["facts"]["mission"]["endConditions"] == (
        current["facts"]["mission"]["endConditions"]
    )
    assert historical["facts"]["configurations"] == current["facts"]["configurations"]
    historical_rules = {rule["id"]: rule for rule in historical["facts"]["mission"]["rules"]}
    current_rules = {rule["id"]: rule for rule in current["facts"]["mission"]["rules"]}
    for rule_id in ("pick-up-beacon", "activate-console", "specialist-troops"):
        assert historical_rules[rule_id] == current_rules[rule_id]

    positions = {
        configuration["id"]: {
            row["id"]: (row["x"], row["y"])
            for row in configuration["geometry"]["elements"] if row["kind"] == "marker"
        }
        for configuration in historical["facts"]["configurations"]
    }
    assert positions["150-points"]["console-left"] == (6, 16)
    assert positions["200-250-points"]["console-left"] == (8, 24)
    assert positions["300-400-points"]["console-left"] == (12, 24)

    # The historical publication identifies a Console A Token, not an
    # independently specified 40 mm scenery diameter; the modern text does.
    historical_text = " ".join(
        paragraph for rule in historical_rules.values() for paragraph in rule["paragraphs"]
    )
    assert "40 mm" not in historical_text
    assert "40 mm" in " ".join(current_rules["deployment-and-objectives"]["paragraphs"])
    assert "Unlike some other ITS Season 18" not in historical_text
    source_issues = historical["facts"]["mission"]["sourceIssues"]
    assert {issue["id"] for issue in source_issues} == {
        "connected-vs-activated-console",
        "allied-beacon-carrier-normal-state",
    }
    assert all("ITS 17 V0.2" in issue["description"] for issue in source_issues)


def test_hardlock_standalone_build_stays_season_local(tmp_path: Path) -> None:
    output = tmp_path / "its_17.db"
    result = build_its_database(SEASON, output, shared_library=SHARED)
    assert len(result["scenarios"]) == 15
    selected = select_its_scenario(
        output, season_id="its-17", revision="0.2", scenario_id="scenario:hardlock",
    )
    assert selected is not None
    historical, _ = hardlock_records()
    assert selected["record"] == historical
    assert [source["id"] for source in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        output, season_id="its-18", revision="2026.09.11", scenario_id="scenario:hardlock",
    ) is None
