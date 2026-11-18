"""Source-reviewed ITS 17 Corporate Appropriation and SQLite isolation."""
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
        next(
            r for r in historical["records"]
            if r["id"] == "scenario:corporate-appropriation"
        ),
        next(
            r for r in current["records"]
            if r["id"] == "scenario:corporate-appropriation"
        ),
    )


def test_its17_corporate_appropriation_has_independent_source_pins() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert len(library["definitions"]) == 16
    definition = library["definitions"][12]
    assert definition["id"] == "scenario:corporate-appropriation"
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = season["scenarioCollection"]["members"][12]
    assert member["scenarioId"] == "scenario:corporate-appropriation"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(c["sourceId"], c["page"]) for c in binding["citations"]] == [
        *((EN, page) for page in range(40, 45)),
        *((ES, page) for page in range(32, 38)),
    ]


def test_its17_corporate_appropriation_scoring_geometry_and_skills() -> None:
    historical, modern = records()
    old = historical["facts"]
    current = modern["facts"]
    assert historical["scope"]["seasons"] == ["its-17"]
    assert historical["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert old["playRequirements"] == {
        "classifiedObjectives": 3, "tacticalObjectives": 0, "hvts": 1,
    }
    assert old["mission"]["objectives"] != current["mission"]["objectives"]
    assert [
        o["id"] for o in old["mission"]["objectives"]
    ] == [
        "capture-enemy-prototype", "bring-enemy-prototype-home",
        "own-prototype-outcome", "more-panoply-gear", "classified-objectives",
    ]
    assert {
        o["id"]: o["maximumPoints"] for o in old["mission"]["objectives"]
    } == {
        "capture-enemy-prototype": 2,
        "bring-enemy-prototype-home": 1,
        "own-prototype-outcome": 3,
        "more-panoply-gear": 1,
        "classified-objectives": 3,
    }
    own = old["mission"]["objectives"][2]
    assert [a["objectivePoints"] for a in own["awards"]] == [3, 1]
    assert old["mission"]["endConditions"] == current["mission"]["endConditions"]
    assert old["mission"]["gameSizes"] == current["mission"]["gameSizes"]
    assert old["configurations"] == current["configurations"]
    for config, rear, width, offset in zip(
        old["configurations"], (8, 12, 12), (24, 32, 48),
        (6, 8, 12), strict=True,
    ):
        geom = config["geometry"]
        items = {e["id"]: e for e in geom["elements"]}
        center = geom["table"]["height"] / 2
        assert geom["table"]["width"] == width
        assert items["deployment-a"]["y2"] == rear
        assert items["deployment-b"]["y1"] == geom["table"]["height"] - rear
        assert items["exclusion-zone"]["y1"] == center - 4
        assert items["exclusion-zone"]["y2"] == center + 4
        assert items["prototype-left"]["x"] == offset
        assert items["prototype-right"]["x"] == width - offset
        assert items["prototype-left"]["y"] == center
        assert items["panoply-a"]["x"] == width / 2
        assert items["panoply-a"]["y"] == rear
        assert items["panoply-b"]["y"] == geom["table"]["height"] - rear
    rules = {r["id"]: r for r in old["mission"]["rules"]}
    assert rules["pick-up-prototype"]["name"] == "Pick Up Prototype"
    assert rules["pick-up-prototype"]["skillTypeIds"] == ["short-skill"]
    use_panoply = rules["use-panoply"]
    assert use_panoply["name"] == "Use Panoply"
    assert use_panoply["skillTypeIds"] == ["short-skill"]
    assert "Normal WIP Roll" in use_panoply["skillFacts"]["effects"][0]
    assert "Booty" in use_panoply["skillFacts"]["effects"][1]
    assert "same Trooper" in use_panoply["skillFacts"]["restrictions"][0]
    assert old["mission"]["rules"].index(use_panoply) == (
        next(i for i, r in enumerate(old["mission"]["rules"])
             if r["id"] == "panoply-chart") - 1
    )


def test_its17_corporate_appropriation_keeps_historical_source_differences() -> None:
    historical, modern = records()
    old = {r["id"]: r for r in historical["facts"]["mission"]["rules"]}
    current = {r["id"]: r for r in modern["facts"]["mission"]["rules"]}
    assert "matching" in old["prototype-profile"]["paragraphs"][0]
    assert "40 mm" in current["prototype-profile"]["paragraphs"][0]
    assert "Both ITS 17" in old["prototype-profile"]["paragraphs"][1]
    assert "EN p. 42 and ES p. 34 both" in old["automated-defense-system"]["paragraphs"][0]
    assert "any MODs" in old["automated-defense-system"]["paragraphs"][0]
    assert "same Trooper" in old["use-panoply"]["skillFacts"]["restrictions"][0]
    assert "matching-diameter" in old["panoplies"]["paragraphs"][0]
    assert "Baggage" in old["common-prototype-rules"]["paragraphs"][0]
    assert "Null-state" in old["capture-prototype"]["paragraphs"][0]
    assert "EN p. 43" in (
        historical["facts"]["mission"]["objectives"][0]["awards"][0]
        ["condition"]["text"]
    )
    issues = {
        row["id"]: row for row in historical["facts"]["mission"]["sourceIssues"]
    }
    assert set(issues) == {
        "its17-corporate-appropriation-reinforcements-en-es",
        "its17-corporate-appropriation-capture-contact-en-es",
        "its17-corporate-appropriation-baggage-classification-en-es",
    }
    assert "YES" in issues[
        "its17-corporate-appropriation-reinforcements-en-es"
    ]["description"]
    assert "NO" in issues[
        "its17-corporate-appropriation-reinforcements-en-es"
    ]["description"]
    assert all(row["armyPoints"] == SIZES for row in issues.values())
    assert all(row["status"] == "needs-verification" for row in issues.values())
    assert all("ITS 17 V0.2" in row["description"] for row in issues.values())
    assert not set(issues).intersection({
        row["id"] for row in modern["facts"]["mission"]["sourceIssues"]
    })


def test_its17_corporate_appropriation_compiles_in_its17_only(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON, target, shared_library=SHARED)
    assert len(report["scenarios"]) == 16
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2",
        scenario_id="scenario:corporate-appropriation",
    )
    assert selected is not None
    historical, _ = records()
    assert selected["record"] == historical
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:corporate-appropriation",
    ) is None
