"""ITS 17 Crossing Lines: historical geometry, text and SQLite separation."""
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
        next(r for r in historical["records"] if r["id"] == "scenario:crossing-lines"),
        next(r for r in current["records"] if r["id"] == "scenario:crossing-lines"),
    )


def test_its17_crossing_lines_is_independently_source_pinned() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert source["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert len(library["definitions"]) == 16
    definition = library["definitions"][11]
    assert definition["id"] == "scenario:crossing-lines"
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = source["scenarioCollection"]["members"][11]
    assert member["scenarioId"] == "scenario:crossing-lines"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(c["sourceId"], c["page"]) for c in binding["citations"]] == [
        *((EN, page) for page in (51, 52, 53, 54)),
        *((ES, page) for page in (42, 43, 44, 45)),
    ]


def test_its17_crossing_lines_scoring_geometry_and_specialist_skill() -> None:
    historical, modern = records()
    facts = historical["facts"]
    latest = modern["facts"]
    assert historical["scope"]["seasons"] == ["its-17"]
    assert historical["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert facts["playRequirements"] == {
        "classifiedObjectives": 0, "tacticalObjectives": 0, "hvts": 0,
    }
    assert facts["mission"]["objectives"] == latest["mission"]["objectives"]
    assert facts["mission"]["endConditions"] == latest["mission"]["endConditions"]
    assert facts["mission"]["gameSizes"] == latest["mission"]["gameSizes"]
    assert facts["configurations"] == latest["configurations"]
    assert {
        o["id"]: o["maximumPoints"] for o in facts["mission"]["objectives"]
    } == {
        "dominate-dead-zone-a": 3,
        "dominate-dead-zone-b": 3,
        "dominate-both-dead-zones": 2,
        "activate-antennas": 2,
    }
    for config, rear, width, offset in zip(
        facts["configurations"], (8, 12, 12),
        (24, 32, 48), (6, 8, 12), strict=True,
    ):
        geom = config["geometry"]
        rect = {e["id"]: e for e in geom["elements"]}
        assert geom["table"]["width"] == width
        assert rect["deployment-a-rear"]["y2"] == rear
        assert rect["deployment-b-rear"]["y1"] == geom["table"]["height"] - rear
        assert rect["deployment-a-forward"]["y2"] - rect["deployment-a-forward"]["y1"] == 4
        assert rect["deployment-b-forward"]["y2"] - rect["deployment-b-forward"]["y1"] == 4
        assert rect["dead-zone-a"]["y2"] == rect["deployment-b-forward"]["y1"]
        assert rect["dead-zone-b"]["y1"] == rect["deployment-a-forward"]["y2"]
        assert rect["antenna-left"]["x"] == offset
        assert rect["antenna-right"]["x"] == width - offset
        assert rect["antenna-left"]["y"] == geom["table"]["height"] / 2
    rules = {r["id"]: r for r in facts["mission"]["rules"]}
    assert rules["activate-antenna"]["skillTypeIds"] == ["short-skill"]
    assert rules["activate-antenna"]["skillFacts"]["requirements"] == (
        next(r for r in latest["mission"]["rules"] if r["id"] == "activate-antenna")
        ["skillFacts"]["requirements"]
    )


def test_its17_crossing_lines_keeps_own_bilingual_source_issues() -> None:
    historical, current = records()
    rules = {r["id"]: r for r in historical["facts"]["mission"]["rules"]}
    modern = {r["id"]: r for r in current["facts"]["mission"]["rules"]}
    antenna = rules["activate-antenna"]
    assert "Console A Token" in antenna["paragraphs"][0]
    assert "Transmission Antenna" in antenna["paragraphs"][0]
    assert "matching-diameter" in antenna["paragraphs"][0]
    assert "40 mm" in modern["activate-antenna"]["paragraphs"][0]
    assert "Shasvastii-Embryo" in rules["dominate-zo"]["paragraphs"][2]
    assert "Unconscious" in rules["dominate-zo"]["paragraphs"][2]
    assert "Secure Treasure" in rules["no-hvt-classified"]["paragraphs"][0]
    assert "does not explicitly" in rules["no-hvt-classified"]["paragraphs"][1]
    assert "Secure Treasure" not in modern["no-hvt-classified"]["paragraphs"][0]
    issues = {
        item["id"]: item for item in historical["facts"]["mission"]["sourceIssues"]
    }
    assert set(issues) == {
        "its17-crossing-lines-central-strip-en-es",
        "its17-crossing-lines-shasvastii-states-en-es",
        "its17-crossing-lines-antenna-token-en-es",
        "its17-crossing-lines-hvt-source-gap",
    }
    assert "[[distance:32:inch]]" in (
        issues["its17-crossing-lines-central-strip-en-es"]["description"]
    )
    assert "[[distance:80:cm]]" in (
        issues["its17-crossing-lines-central-strip-en-es"]["description"]
    )
    assert all(issue["armyPoints"] == SIZES for issue in issues.values())
    assert all(issue["status"] == "needs-verification" for issue in issues.values())
    assert all("ITS 17" in issue["description"] for issue in issues.values())
    assert current["facts"]["mission"]["sourceIssues"] == []


def test_its17_crossing_lines_build_stays_season_local(tmp_path: Path) -> None:
    output = tmp_path / "its_17.db"
    report = build_its_database(SEASON, output, shared_library=SHARED)
    assert len(report["scenarios"]) == 16
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        output, season_id="its-17", revision="0.2",
        scenario_id="scenario:crossing-lines",
    )
    assert selected is not None
    historical, _ = records()
    assert selected["record"] == historical
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        output, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:crossing-lines",
    ) is None
