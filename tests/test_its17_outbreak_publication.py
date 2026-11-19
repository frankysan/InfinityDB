"""ITS 17 Outbreak: independently reviewed scoring and SQLite isolation."""
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
        next(r for r in old["records"] if r["id"] == "scenario:outbreak"),
        next(r for r in current["records"] if r["id"] == "scenario:outbreak"),
    )


def test_its17_outbreak_source_identity_and_membership() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert source["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [item["id"] for item in library["definitions"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    definition = library["definitions"][14]
    assert definition["id"] == "scenario:outbreak"
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = source["scenarioCollection"]["members"][14]
    assert member["scenarioId"] == "scenario:outbreak"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(c["sourceId"], c["page"]) for c in binding["citations"]] == [
        *((EN, p) for p in range(68, 72)),
        *((ES, p) for p in range(46, 50)),
    ]


def test_its17_outbreak_historical_scoring_is_not_its18_scoring() -> None:
    historic, latest = records()
    h = historic["facts"]
    m = latest["facts"]
    assert historic["scope"]["seasons"] == ["its-17"]
    assert historic["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert h["playRequirements"] == {
        "classifiedObjectives": 0, "tacticalObjectives": 0, "hvts": 0,
    }
    assert [(x["id"], x["maximumPoints"]) for x in h["mission"]["objectives"]] == [
        ("scan-infected", 3),
        ("stabilize-more-infected", 2),
        ("stabilize-alpha-infected", 1),
        ("civevac-more-stabilized", 2),
        ("civevac-stabilized-alpha", 1),
        ("secure-infected", 1),
    ]
    assert [(x["id"], x["maximumPoints"]) for x in m["mission"]["objectives"]] == [
        ("scan-infected", 3),
        ("stabilize-more-infected", 2),
        ("civevac-more-stabilized", 2),
        ("civevac-stabilized-alpha", 2),
        ("secure-infected", 1),
    ]
    assert sum(x["maximumPoints"] for x in h["mission"]["objectives"]) == 10
    assert sum(x["maximumPoints"] for x in m["mission"]["objectives"]) == 10
    assert "ITS 17" in h["mission"]["objectives"][2]["awards"][0]["condition"]["text"]
    assert "ITS 18" in h["mission"]["objectives"][4]["awards"][0]["condition"]["text"]
    assert h["mission"]["endConditions"] == m["mission"]["endConditions"]
    assert h["mission"]["gameSizes"] == m["mission"]["gameSizes"]


def test_its17_outbreak_geometry_skills_and_source_differences() -> None:
    historic, modern = records()
    old = historic["facts"]
    latest = modern["facts"]
    assert old["configurations"] == latest["configurations"]
    for conf, radius, width, height in zip(
        old["configurations"], (12, 20, 24), (24, 32, 48),
        (32, 48, 48), strict=True,
    ):
        geom = conf["geometry"]
        assert (geom["table"]["width"], geom["table"]["height"]) == (width, height)
        elements = {e["id"]: e for e in geom["elements"]}
        assert elements["deployment-a"]["radius"] == radius
        assert elements["deployment-b"]["radius"] == radius
        assert elements["alpha-infected"]["x"] == width / 2
        assert elements["alpha-infected"]["y"] == height / 2
    h_rules = {r["id"]: r for r in old["mission"]["rules"]}
    m_rules = {r["id"]: r for r in latest["mission"]["rules"]}
    for skill in ("stabilize-infected", "scan-infected"):
        assert h_rules[skill] == m_rules[skill]
        assert h_rules[skill]["skillTypeIds"] == ["short-skill"]
    assert "each player places two" in h_rules["infected-placement"]["paragraphs"][0]
    assert "Circular Template" in h_rules["stabilization-zones"]["paragraphs"][0]
    assert "Doctor or Paramedic" in h_rules["doctor-paramedic-bonus"]["paragraphs"][0]
    issues = old["mission"]["sourceIssues"]
    assert len(issues) == 1
    assert issues[0]["id"] == "its17-outbreak-infected-placement-distance-en-es"
    assert issues[0]["status"] == "needs-verification"
    assert issues[0]["armyPoints"] == SIZES
    assert issues[0]["objectiveId"] == "secure-infected"
    assert "ITS 17 V0.2" in issues[0]["description"]
    assert "[[distance:10:cm]]" in issues[0]["description"]
    assert "[[distance:8:inch]]" in issues[0]["description"]
    assert latest["mission"]["sourceIssues"][0]["id"] != issues[0]["id"]


def test_its17_outbreak_compiles_without_its18_publication(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON, target, shared_library=SHARED)
    assert [item["id"] for item in report["scenarios"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2",
        scenario_id="scenario:outbreak",
    )
    assert selected is not None
    historical, _ = records()
    assert selected["record"] == historical
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:outbreak",
    ) is None
