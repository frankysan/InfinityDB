"""Source-reviewed ITS 17 V0.2 Battleground, with different scoring from ITS 18."""
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
        next(item for item in historical["records"] if item["id"] == "scenario:battleground"),
        next(item for item in current["records"] if item["id"] == "scenario:battleground"),
    )


def test_battleground_has_independent_its17_source_pin() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [entry["id"] for entry in library["definitions"]] == [
        "scenario:evacuation",
        "scenario:hardlock",
        "scenario:uplink-center",
        "scenario:battleground",
        "scenario:annihilation",
        "scenario:cutthroat",
        "scenario:superiority",
        "scenario:provisioning",
        "scenario:area-of-interest",
    ]
    definition = library["definitions"][3]
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    membership = season["scenarioCollection"]["members"][3]
    assert membership["scenarioId"] == definition["id"]
    binding = membership["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(source["sourceId"], source["page"]) for source in binding["citations"]] == [
        *((EN, page) for page in (83, 84, 85)),
        *((ES, page) for page in (88, 89, 90)),
    ]


def test_battleground_distinct_objectives_and_exclusive_key_ops_awards() -> None:
    old, current = records()
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {citation["sourceId"] for citation in old["citations"]} == {EN, ES}
    assert old["facts"]["playRequirements"] == current["facts"]["playRequirements"]
    assert old["facts"]["mission"]["gameSizes"] == current["facts"]["mission"]["gameSizes"]
    assert old["facts"]["mission"]["endConditions"] == (
        current["facts"]["mission"]["endConditions"]
    )
    objectives = {o["id"]: o for o in old["facts"]["mission"]["objectives"]}
    expected = {
        "near-sector-a": 1, "near-sector-b": 1, "central-sector": 3,
        "far-sector-a": 4, "far-sector-b": 4, "enemy-key-ops": 2,
    }
    assert {identifier: obj["maximumPoints"] for identifier, obj in objectives.items()} == (
        expected
    )
    for identifier, points in expected.items():
        if identifier == "enemy-key-ops":
            continue
        assert objectives[identifier]["awards"][0]["objectivePoints"] == points
    assert {obj["id"]: obj["maximumPoints"]
            for obj in current["facts"]["mission"]["objectives"]} == {
        "near-sector-a": 2, "near-sector-b": 2, "central-sector": 3,
        "far-sector-a": 5, "far-sector-b": 5,
    }

    key = objectives["enemy-key-ops"]
    assert key["aggregation"] == "exclusive"
    assert key["timing"] == "end-of-game"
    assert key["sideIds"] == ["side-a", "side-b"]
    assert [award["objectivePoints"] for award in key["awards"]] == [2, 1]
    assert all(award["armyPoints"] == SIZES for award in key["awards"])
    assert all(award["condition"]["kind"] == "reviewed-prose" for award in key["awards"])
    assert "Alternatively" in key["awards"][1]["condition"]["text"]
    # Each player can score only 1 + 3 + 4 + (2 OR 1) = 10 OP.
    for near, far in (
        ("near-sector-a", "far-sector-a"),
        ("near-sector-b", "far-sector-b"),
    ):
        assert sum(objectives[identifier]["maximumPoints"] for identifier in (
            near, "central-sector", far, "enemy-key-ops",
        )) == 10


def test_battleground_geometry_reused_but_map_score_labels_updated() -> None:
    old, current = records()
    old_configs = {config["id"]: config for config in old["facts"]["configurations"]}
    new_configs = {config["id"]: config for config in current["facts"]["configurations"]}
    assert old_configs.keys() == new_configs.keys() == {
        "150-points", "200-250-points", "300-400-points",
    }
    for identifier in old_configs:
        old_geometry = old_configs[identifier]["geometry"]
        new_geometry = new_configs[identifier]["geometry"]
        assert old_geometry["table"] == new_geometry["table"]
        old_elements = {row["id"]: row for row in old_geometry["elements"]}
        new_elements = {row["id"]: row for row in new_geometry["elements"]}
        for element_id, element in old_elements.items():
            if element_id in {"sector-near-a-label", "sector-near-b-label"}:
                continue
            assert element == new_elements[element_id]
        assert old_geometry["annotations"] == new_geometry["annotations"]
        assert old_elements["sector-near-a-label"]["text"] == "A: 1 OP · B: 4 OP"
        assert old_elements["sector-near-b-label"]["text"] == "A: 4 OP · B: 1 OP"
        assert new_elements["sector-near-a-label"]["text"] == "A: 2 OP · B: 5 OP"
        assert new_elements["sector-near-b-label"]["text"] == "A: 5 OP · B: 2 OP"
        table = old_geometry["table"]
        sectors = [
            old_elements[key] for key in ("sector-near-a", "sector-center", "sector-near-b")
        ]
        expected_depth = 4 if identifier == "150-points" else 8
        assert all(region["y2"] - region["y1"] == expected_depth for region in sectors)
        assert all(region["x2"] == table["width"] for region in sectors)
        assert old_elements["deployment-a"]["y2"] == (
            8 if identifier == "150-points" else 12
        )


def test_battleground_source_differences_and_key_ops_ability_are_retained() -> None:
    old, current = records()
    old_rules = {rule["id"]: rule for rule in old["facts"]["mission"]["rules"]}
    current_rules = {rule["id"]: rule for rule in current["facts"]["mission"]["rules"]}
    for rule_id in current_rules:
        assert old_rules[rule_id] == current_rules[rule_id]
    assert set(old_rules) - set(current_rules) == {"key-ops", "threaten-key-ops"}
    prose = " ".join(old_rules["key-ops"]["paragraphs"])
    assert "Irregular" in prose and "REM or VH" in prose
    assert "[[skill:dodge|Dodge (+3)]]" in prose
    assert "[[skill:tactical-awareness|Tactical Awareness]]" in prose
    assert "not alongside" in " ".join(old_rules["threaten-key-ops"]["paragraphs"])

    issues = old["facts"]["mission"]["sourceIssues"]
    assert {issue["id"] for issue in issues} == {
        "key-ops-vh-eligibility-en-es",
        "shasvastii-embryo-eligibility-en-es",
    }
    assert all(issue["armyPoints"] == SIZES for issue in issues)
    assert all(issue["status"] == "needs-verification" for issue in issues)
    assert all("ITS 17 V0.2" in issue["description"] for issue in issues)


def test_battleground_standalone_database_and_season_isolation(tmp_path: Path) -> None:
    output = tmp_path / "its17.db"
    result = build_its_database(SEASON, output, shared_library=SHARED)
    assert len(result["scenarios"]) == 9
    assert result["inputIdentity"]["seasonId"] == "its-17"
    assert result["inputIdentity"]["sharedScenarioLibrary"]["sha256"] == (
        hashlib.sha256(SHARED.read_bytes()).hexdigest()
    )
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == result
    selected = select_its_scenario(
        output, season_id="its-17", revision="0.2", scenario_id="scenario:battleground",
    )
    assert selected is not None
    old, _ = records()
    assert selected["record"] == old
    assert [source["id"] for source in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        output, season_id="its-18", revision="2026.09.11", scenario_id="scenario:battleground",
    ) is None
