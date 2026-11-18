"""Pinned ITS 17 Superiority: 3-OP Consoles and Dominant Key Ops."""
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
EN, ES = "its-season-17-v0.2-en-pdf", "its-season-17-v0.2-es-pdf"
SIZES = [150, 200, 250, 300, 350, 400]


def records() -> tuple[dict, dict]:
    old = load_curated_document(SEASON, shared_scenario_library=SHARED)
    current = load_curated_document(ITS18)
    return (
        next(row for row in old["records"] if row["id"] == "scenario:superiority"),
        next(row for row in current["records"] if row["id"] == "scenario:superiority"),
    )


def test_its17_superiority_source_pins_and_membership() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [entry["id"] for entry in library["definitions"]] == [
        "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
        "scenario:battleground", "scenario:annihilation", "scenario:cutthroat",
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
    definition = library["definitions"][6]
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = season["scenarioCollection"]["members"][6]
    assert member["scenarioId"] == "scenario:superiority"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["overrides"] == []
    assert binding["componentCitations"] == {}
    assert [(row["sourceId"], row["page"]) for row in binding["citations"]] == [
        (EN, 89), (EN, 90), (EN, 91), (EN, 92),
        (ES, 94), (ES, 95), (ES, 96), (ES, 97), (ES, 98),
    ]


def test_superiority_historical_scoring_cap_and_original_rules() -> None:
    old, current = records()
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {citation["sourceId"] for citation in old["citations"]} == {EN, ES}
    old_facts, now_facts = old["facts"], current["facts"]
    assert old_facts["playRequirements"] == now_facts["playRequirements"]
    assert old_facts["mission"]["gameSizes"] == now_facts["mission"]["gameSizes"]
    assert old_facts["mission"]["endConditions"] == now_facts["mission"]["endConditions"]
    assert old_facts["configurations"] == now_facts["configurations"]
    objectives = {obj["id"]: obj for obj in old_facts["mission"]["objectives"]}
    assert {name: obj["maximumPoints"] for name, obj in objectives.items()} == {
        "dominate-more-quadrants": 6, "hack-consoles": 3, "dominant-key-ops": 1,
    }
    assert {obj["id"]: obj["maximumPoints"]
            for obj in now_facts["mission"]["objectives"]} == {
        "dominate-more-quadrants": 6, "hack-consoles": 4,
    }
    assert objectives["dominate-more-quadrants"]["maximumPointsPerRound"] == 2
    assert objectives["hack-consoles"]["aggregation"] == "cumulative"
    assert objectives["hack-consoles"]["awards"] == (
        now_facts["mission"]["objectives"][1]["awards"]
    )
    assert sum(obj["maximumPoints"] for obj in objectives.values()) == 10
    dominant = objectives["dominant-key-ops"]
    assert dominant["timing"] == "end-of-game"
    assert dominant["aggregation"] == "exclusive"
    assert dominant["awards"][0]["armyPoints"] == SIZES
    assert dominant["awards"][0]["objectivePoints"] == 1
    assert "non-Null" in dominant["awards"][0]["condition"]["text"]
    assert "Dominate" in dominant["awards"][0]["condition"]["text"]


def test_superiority_reuses_reviewed_skills_and_notes_source_differences() -> None:
    old, current = records()
    rules = {row["id"]: row for row in old["facts"]["mission"]["rules"]}
    current_rules = {row["id"]: row for row in current["facts"]["mission"]["rules"]}
    assert set(rules) - set(current_rules) == {"key-ops", "dominant-key-ops"}
    for name in (
        "quadrants-zo", "shasvastii", "baggage", "hack-consoles",
        "specialist-troops", "operational-learning", "hvt-and-classified-deck",
    ):
        assert rules[name] == current_rules[name]
    assert "40 mm" not in " ".join(rules["consoles"]["paragraphs"])
    assert "40 mm" in " ".join(current_rules["consoles"]["paragraphs"])
    key = " ".join(rules["key-ops"]["paragraphs"])
    assert "REM or VH" in key
    assert "[[skill:dodge|Dodge (+3)]]" in key
    assert "[[skill:tactical-awareness|Tactical Awareness]]" in key
    assert "non-Null" in rules["dominant-key-ops"]["paragraphs"][0]
    issues = {issue["id"]: issue for issue in old["facts"]["mission"]["sourceIssues"]}
    assert set(issues) == {
        "its17-shasvastii-en-es-zo-state",
        "its17-key-ops-vh-eligibility-en-es",
    }
    assert all(issue["status"] == "needs-verification" for issue in issues.values())
    assert all("ITS 17 V0.2" in issue["description"] for issue in issues.values())
    for geometry, expected in zip(old_facts_geometry(old), (8, 12, 12), strict=True):
        deployment = next(
            item for item in geometry["elements"] if item["id"] == "deployment-a"
        )
        assert deployment["y2"] == expected
        assert len([e for e in geometry["elements"] if e["kind"] == "marker"]) == 4


def old_facts_geometry(record: dict) -> list[dict]:
    return [entry["geometry"] for entry in record["facts"]["configurations"]]


def test_superiority_standalone_sqlite_and_season_isolation(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON, target, shared_library=SHARED)
    assert len(report["scenarios"]) == 15
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2", scenario_id="scenario:superiority",
    )
    assert selected is not None
    old, _ = records()
    assert selected["record"] == old
    assert [source["id"] for source in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:superiority",
    ) is None
