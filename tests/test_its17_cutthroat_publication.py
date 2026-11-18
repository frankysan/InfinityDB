"""Pinned ITS 17 Cutthroat with independent Key Ops scoring and citations."""
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
        next(row for row in historical["records"] if row["id"] == "scenario:cutthroat"),
        next(row for row in current["records"] if row["id"] == "scenario:cutthroat"),
    )


def test_its17_cutthroat_pinned_membership_and_sources() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [entry["id"] for entry in library["definitions"]] == [
        "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
        "scenario:battleground", "scenario:annihilation", "scenario:cutthroat",
    ]
    definition = library["definitions"][5]
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = season["scenarioCollection"]["members"][5]
    assert member["scenarioId"] == "scenario:cutthroat"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(row["sourceId"], row["page"]) for row in binding["citations"]] == [
        (EN, 86), (EN, 87), (EN, 88), (ES, 91), (ES, 92), (ES, 93),
    ]


def test_its17_cutthroat_key_ops_scores_are_distinct_from_its18() -> None:
    historical, current = records()
    assert historical["scope"]["seasons"] == ["its-17"]
    assert historical["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {c["sourceId"] for c in historical["citations"]} == {EN, ES}
    old_facts, new_facts = historical["facts"], current["facts"]
    assert old_facts["playRequirements"] == new_facts["playRequirements"]
    assert old_facts["mission"]["gameSizes"] == new_facts["mission"]["gameSizes"]
    assert old_facts["mission"]["endConditions"] == new_facts["mission"]["endConditions"]
    assert old_facts["configurations"] == new_facts["configurations"]

    objectives = {row["id"]: row for row in old_facts["mission"]["objectives"]}
    assert {key: obj["maximumPoints"] for key, obj in objectives.items()} == {
        "kill-more-army-points": 3,
        "kill-same-lieutenants": 2,
        "kill-more-lieutenants": 3,
        "kill-enemy-key-ops": 1,
        "kill-more-with-key-ops": 3,
    }
    assert set(row["id"] for row in new_facts["mission"]["objectives"]) == {
        "kill-more-army-points", "kill-same-lieutenants",
        "kill-more-lieutenants", "kill-more-with-lieutenants",
    }
    assert objectives["kill-more-with-key-ops"]["awards"][0]["objectivePoints"] == 3
    assert objectives["kill-enemy-key-ops"]["awards"][0]["objectivePoints"] == 1
    assert sum((
        objectives["kill-more-army-points"]["maximumPoints"],
        objectives["kill-more-lieutenants"]["maximumPoints"],
        objectives["kill-enemy-key-ops"]["maximumPoints"],
        objectives["kill-more-with-key-ops"]["maximumPoints"],
    )) == 10
    assert all(
        obj["awards"][0]["armyPoints"] == SIZES for obj in objectives.values()
    )


def test_its17_cutthroat_reuses_geometry_and_retains_original_key_ops_rules() -> None:
    old, current = records()
    old_rules = {row["id"]: row for row in old["facts"]["mission"]["rules"]}
    new_rules = {row["id"]: row for row in current["facts"]["mission"]["rules"]}
    assert set(old_rules) - set(new_rules) == {"key-ops"}
    for name in ("reinforced-tactical-link", "no-quarter", "hvt-and-classified-deck"):
        assert old_rules[name] == new_rules[name]
    assert old_rules["killing"]["paragraphs"][:2] == new_rules["killing"]["paragraphs"][:2]
    assert old_rules["killing"]["paragraphs"][-1] == new_rules["killing"]["paragraphs"][-1]
    assert "Key Ops" in old_rules["killing"]["paragraphs"][2]
    prose = " ".join(old_rules["key-ops"]["paragraphs"])
    assert "REM or VH" in prose and "Irregular" in prose
    assert "[[skill:dodge|Dodge (+3)]]" in prose
    assert "[[skill:tactical-awareness|Tactical Awareness]]" in prose
    issues = {issue["id"]: issue for issue in old["facts"]["mission"]["sourceIssues"]}
    assert set(issues) == {
        "key-ops-vh-eligibility-en-es", "lieutenant-more-kills-minimum-en-es",
        "killed-lieutenant-history-en-es",
    }
    assert all(issue["status"] == "needs-verification" for issue in issues.values())
    assert all("ITS 17 V0.2" in issue["description"] for issue in issues.values())
    assert old["facts"]["configurations"][0]["geometry"]["table"] == {
        "width": 24, "height": 32, "unit": "in",
    }
    for config, depth in zip(old["facts"]["configurations"], (12, 16, 16), strict=True):
        rect = next(
            element for element in config["geometry"]["elements"]
            if element["id"] == "deployment-a"
        )
        assert rect["y2"] == depth


def test_its17_cutthroat_standalone_sqlite_is_season_local(tmp_path: Path) -> None:
    output = tmp_path / "its_17.db"
    result = build_its_database(SEASON, output, shared_library=SHARED)
    assert result["inputIdentity"]["seasonId"] == "its-17"
    assert len(result["scenarios"]) == 6
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == result
    selected = select_its_scenario(
        output, season_id="its-17", revision="0.2", scenario_id="scenario:cutthroat",
    )
    assert selected is not None
    old, _ = records()
    assert selected["record"] == old
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        output, season_id="its-18", revision="2026.09.11", scenario_id="scenario:cutthroat",
    ) is None
