"""ITS 17 V0.2 Provisioning source-pinned publication and season isolation."""
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
        next(row for row in historical["records"] if row["id"] == "scenario:provisioning"),
        next(row for row in current["records"] if row["id"] == "scenario:provisioning"),
    )


def test_its17_provisioning_has_independent_source_and_shared_pin() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert source["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [row["id"] for row in library["definitions"]] == [
        "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
        "scenario:battleground", "scenario:annihilation", "scenario:cutthroat",
        "scenario:superiority", "scenario:provisioning",
        "scenario:area-of-interest",
        "scenario:last-launch",
        "scenario:b-pong",
        "scenario:crossing-lines",
        "scenario:corporate-appropriation",
        "scenario:critical-intervention",
        "scenario:outbreak",
        "scenario:akial-interference",
    ]
    definition = library["definitions"][7]
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    membership = source["scenarioCollection"]["members"][7]
    assert membership["scenarioId"] == "scenario:provisioning"
    binding = membership["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(row["sourceId"], row["page"]) for row in binding["citations"]] == [
        *((EN, page) for page in (72, 73, 74, 75, 76)),
        *((ES, page) for page in (70, 71, 72, 73, 74)),
        (EN, 13), (ES, 14),
    ]


def test_its17_provisioning_scoring_geometry_and_specialist_actions() -> None:
    historical, current = records()
    old, new = historical["facts"], current["facts"]
    assert historical["scope"]["seasons"] == ["its-17"]
    assert historical["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {c["sourceId"] for c in historical["citations"]} == {EN, ES}
    assert old["playRequirements"] == new["playRequirements"]
    assert old["mission"]["gameSizes"] == new["mission"]["gameSizes"]
    assert old["mission"]["objectives"] == new["mission"]["objectives"]
    assert old["mission"]["endConditions"] == new["mission"]["endConditions"]
    assert old["configurations"] == new["configurations"]
    assert {row["id"]: row["maximumPoints"] for row in old["mission"]["objectives"]} == {
        "control-supply-boxes": 4,
        "safe-area-comparison": 3,
        "opponent-empty-safe-area": 2,
        "classified-objective": 1,
    }
    for config, radius, gap in zip(
        old["configurations"], (12, 20, 24), (8, 12, 16), strict=True
    ):
        elements = {row["id"]: row for row in config["geometry"]["elements"]}
        assert elements["deployment-a"]["kind"] == "quarter-circle"
        assert elements["deployment-a"]["radius"] == radius
        assert elements["deployment-b"]["radius"] == radius
        markers = [row for row in elements.values() if row["kind"] == "marker"]
        assert len(markers) == 3
        assert elements["coffin-center"]["markerType"] == "tech-coffin"
        # Historical diagrams show outer coffins separated by the quoted
        # radial offset along the diagonal, with the central coffin between.
        center, lower = elements["coffin-center"], elements["coffin-lower"]
        distance_squared = (center["x"] - lower["x"]) ** 2 + (
            center["y"] - lower["y"]
        ) ** 2
        assert abs(distance_squared - gap**2) < 0.001
    old_rules = {row["id"]: row for row in old["mission"]["rules"]}
    current_rules = {row["id"]: row for row in new["mission"]["rules"]}
    for key in (
        "common-supply-box-rules", "control-supply-boxes",
        "specialist-troops", "operational-learning",
    ):
        assert old_rules[key] == current_rules[key]
    assert old_rules["extract-supply-boxes"]["skillFacts"]["effects"] == (
        current_rules["extract-supply-boxes"]["skillFacts"]["effects"]
    )


def test_its17_provisioning_does_not_inherit_its18_source_disputes() -> None:
    old, current = records()
    rules = {row["id"]: row for row in old["facts"]["mission"]["rules"]}
    current_rules = {row["id"]: row for row in current["facts"]["mission"]["rules"]}
    assert "40 mm Tech-Coffin Token" in " ".join(
        rules["deployment-and-tech-coffins"]["paragraphs"]
    )
    assert "EN p. 13 / ES p. 14" in rules["deployment-and-tech-coffins"]["paragraphs"][1]
    assert "40 mm" in " ".join(
        current_rules["deployment-and-tech-coffins"]["paragraphs"]
    )
    assert "place a Player A or B Token" in rules["extract-supply-boxes"]["paragraphs"][1]
    assert "the enemy's Safe Area" in rules["pickup-supply-boxes"]["paragraphs"][1]
    assert "completely inside" in rules["safe-areas"]["paragraphs"][1]
    assert "Both ITS 17 languages" in rules["safe-areas"]["paragraphs"][1]
    assert "Spanish explicitly requires" in current_rules["safe-areas"]["paragraphs"][1]
    notes = rules["extract-supply-boxes"]["skillFacts"]["sourceNotes"]
    assert len(notes) == 2
    assert "base contact" in notes[0] and "Silhouette contact" in notes[0]
    issues = old["facts"]["mission"]["sourceIssues"]
    assert len(issues) == 1
    assert issues[0]["id"] == "its17-extract-contact-en-es"
    assert issues[0]["armyPoints"] == SIZES
    assert issues[0]["status"] == "needs-verification"
    assert "ITS 17 V0.2" in issues[0]["description"]


def test_its17_provisioning_sqlite_stays_separate(tmp_path: Path) -> None:
    output = tmp_path / "its_17.db"
    report = build_its_database(SEASON, output, shared_library=SHARED)
    assert len(report["scenarios"]) == 16
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert report["inputIdentity"]["sharedScenarioLibrary"]["sha256"] == (
        hashlib.sha256(SHARED.read_bytes()).hexdigest()
    )
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        output, season_id="its-17", revision="0.2", scenario_id="scenario:provisioning",
    )
    assert selected is not None
    old, _ = records()
    assert selected["record"] == old
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        output, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:provisioning",
    ) is None
