"""Source-reviewed ITS 17 Area of Interest and cross-season isolation."""
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

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
SIZES = [150, 200, 250, 300, 350, 400]


def records() -> tuple[dict, dict]:
    historical = load_curated_document(SEASON, shared_scenario_library=SHARED)
    current = load_curated_document(ITS18)
    return (
        next(row for row in historical["records"] if row["id"] == "scenario:area-of-interest"),
        next(row for row in current["records"] if row["id"] == "scenario:area-of-interest"),
    )


def test_its17_area_source_identity_and_bilingual_citations() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [row["id"] for row in library["definitions"]] == [
        "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
        "scenario:battleground", "scenario:annihilation", "scenario:cutthroat",
        "scenario:superiority", "scenario:provisioning", "scenario:area-of-interest",
        "scenario:last-launch",
        "scenario:b-pong",
        "scenario:crossing-lines",
        "scenario:corporate-appropriation",
        "scenario:critical-intervention",
        "scenario:outbreak",
        "scenario:akial-interference",
    ]
    definition = library["definitions"][8]
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = season["scenarioCollection"]["members"][8]
    assert member["scenarioId"] == "scenario:area-of-interest"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(row["sourceId"], row["page"]) for row in binding["citations"]] == [
        (EN, 77), (EN, 78), (EN, 79), (EN, 80),
        (ES, 80), (ES, 81), (ES, 82), (ES, 83), (ES, 84),
        (EN, 13), (ES, 14),
    ]


def test_its17_area_scores_reuse_only_source_confirmed_geometry() -> None:
    old, current = records()
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {citation["sourceId"] for citation in old["citations"]} == {EN, ES}
    original, now = old["facts"], current["facts"]
    assert original["playRequirements"] == now["playRequirements"]
    assert original["mission"]["gameSizes"] == now["mission"]["gameSizes"]
    assert original["mission"]["objectives"] == now["mission"]["objectives"]
    assert original["mission"]["endConditions"] == now["mission"]["endConditions"]
    assert original["configurations"] == now["configurations"]
    assert {obj["id"]: obj["maximumPoints"] for obj in original["mission"]["objectives"]} == {
        "dominate-areas": 3, "dominate-special-area": 3,
        "activate-antenna": 3, "classified-objective": 1,
    }
    for configuration, radius in zip(
        original["configurations"], (12, 20, 24), strict=True
    ):
        geometry = configuration["geometry"]
        elements = {row["id"]: row for row in geometry["elements"]}
        assert elements["deployment-a"]["kind"] == "quarter-circle"
        assert elements["deployment-a"]["radius"] == radius
        assert elements["deployment-b"]["radius"] == radius
        antenna = elements["communication-antenna"]
        assert antenna["kind"] == "marker"
        assert antenna["x"] == geometry["table"]["width"] / 2
        assert antenna["y"] == geometry["table"]["height"] / 2
        assert len([row for row in elements.values() if row["kind"] == "marker"]) == 1


def test_its17_area_historical_antenna_rules_and_source_differences() -> None:
    old, current = records()
    rules = {row["id"]: row for row in old["facts"]["mission"]["rules"]}
    current_rules = {row["id"]: row for row in current["facts"]["mission"]["rules"]}
    for name in ("deployment", "player-placed-areas", "specialist-troops"):
        assert rules[name] == current_rules[name]
    historic_antenna = " ".join(rules["communication-antenna"]["paragraphs"])
    assert "matching diameter" in historic_antenna
    assert "40 mm Transmission Antenna Token" in historic_antenna
    assert "EN p. 13 / ES p. 14" in historic_antenna
    assert "single 40 mm" in current_rules["communication-antenna"]["paragraphs"][0]
    activation = rules["activate-communication-antenna"]
    assert activation["skillTypeIds"] == ["short-skill"]
    assert activation["skillFacts"]["requirements"] == (
        current_rules["activate-communication-antenna"]["skillFacts"]["requirements"]
    )
    assert len(activation["skillFacts"]["sourceNotes"]) == 2
    assert "optional" in activation["paragraphs"][1]
    assert "Connected" in activation["skillFacts"]["sourceNotes"][1]
    assert "Shasvastii" in rules["dominate-zones"]["paragraphs"][2]
    assert "Normal or Unconscious" in rules["dominate-zones"]["paragraphs"][2]
    assert "ITS 17 EN p. 80" in rules["intelcom"]["paragraphs"][2]

    issues = {issue["id"]: issue for issue in old["facts"]["mission"]["sourceIssues"]}
    assert set(issues) == {
        "its17-reinforcements-en-es",
        "its17-hacker-aro-optional-vs-mandatory",
        "its17-shasvastii-zo-states-en-es",
        "its17-intelcom-final-vs-third-round",
        "its17-connected-vs-activated-antenna-es",
    }
    assert all(issue["armyPoints"] == SIZES for issue in issues.values())
    assert all(issue["status"] == "needs-verification" for issue in issues.values())
    assert all("ITS 17 V0.2" in issue["description"] for issue in issues.values())
    assert "YES" in issues["its17-reinforcements-en-es"]["description"]
    assert "NO" in issues["its17-reinforcements-en-es"]["description"]


def test_its17_area_sqlite_remains_season_local(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    result = build_its_database(SEASON, target, shared_library=SHARED)
    assert len(result["scenarios"]) == 16
    assert result["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == result
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2",
        scenario_id="scenario:area-of-interest",
    )
    assert selected is not None
    old, _ = records()
    assert selected["record"] == old
    assert [row["id"] for row in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:area-of-interest",
    ) is None
