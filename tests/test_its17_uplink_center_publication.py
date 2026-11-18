"""Source-pinned ITS 17 V0.2 Uplink Center, isolated from ITS 18."""
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


def records() -> tuple[dict, dict]:
    old = load_curated_document(SEASON, shared_scenario_library=SHARED)
    current = load_curated_document(ITS18)
    return (
        next(row for row in old["records"] if row["id"] == "scenario:uplink-center"),
        next(row for row in current["records"] if row["id"] == "scenario:uplink-center"),
    )


def test_reviewed_uplink_membership_is_source_and_version_pinned() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [item["id"] for item in library["definitions"]] == [
        "scenario:evacuation", "scenario:hardlock", "scenario:uplink-center",
        "scenario:battleground",
        "scenario:annihilation",
        "scenario:cutthroat",
        "scenario:superiority",
    ]
    entry = library["definitions"][2]
    assert entry["version"] == "its17-v0.2"
    assert entry["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert entry["components"] == []
    membership = season["scenarioCollection"]["members"][2]
    assert membership["scenarioId"] == "scenario:uplink-center"
    binding = membership["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(citation["sourceId"], citation["page"]) for citation in binding["citations"]] == [
        *((EN, page) for page in (93, 94, 95, 96)),
        *((ES, page) for page in (99, 100, 101, 102)),
    ]


def test_uplink_review_matches_six_sizes_and_preserves_historical_ambiguity() -> None:
    old, current = records()
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {citation["sourceId"] for citation in old["citations"]} == {EN, ES}
    old_facts = old["facts"]
    current_facts = current["facts"]
    assert old_facts["playRequirements"] == current_facts["playRequirements"]
    assert old_facts["mission"]["gameSizes"] == current_facts["mission"]["gameSizes"]
    assert old_facts["mission"]["objectives"] == current_facts["mission"]["objectives"]
    assert old_facts["mission"]["endConditions"] == current_facts["mission"]["endConditions"]
    assert old_facts["configurations"] == current_facts["configurations"]
    old_rules = {rule["id"]: rule for rule in old_facts["mission"]["rules"]}
    current_rules = {rule["id"]: rule for rule in current_facts["mission"]["rules"]}
    for rule_id in current_rules.keys() - {"deployment-and-objectives"}:
        assert old_rules[rule_id] == current_rules[rule_id]
    source_text = " ".join(
        paragraph for rule in old_rules.values() for paragraph in rule["paragraphs"]
    )
    assert "40 mm" not in source_text
    assert "40 mm" in current_rules["deployment-and-objectives"]["paragraphs"][1]
    assert "[[distance:6:inch]]" in source_text
    assert "[[distance:8:inch]]" in source_text
    assert "[[distance:12:inch]]" in source_text

    positions = {
        config["id"]: {
            marker["id"]: (marker["x"], marker["y"])
            for marker in config["geometry"]["elements"] if marker["kind"] == "marker"
        }
        for config in old_facts["configurations"]
    }
    assert positions["150-points"]["antenna-left"] == (6, 16)
    assert positions["200-250-points"]["antenna-left"] == (8, 24)
    assert positions["300-400-points"]["antenna-left"] == (12, 24)
    assert positions["150-points"]["tech-coffin"] == (12, 16)
    issues = old_facts["mission"]["sourceIssues"]
    assert len(issues) == 1
    assert issues[0]["id"] == "spanish-antenna-350-placement-omission"
    assert issues[0]["armyPoints"] == [350]
    assert "ITS 17 V0.2" in issues[0]["description"]


def test_uplink_standalone_sqlite_retains_exact_historical_publication(
    tmp_path: Path,
) -> None:
    out = tmp_path / "its17.db"
    result = build_its_database(SEASON, out, shared_library=SHARED)
    assert len(result["scenarios"]) == 7
    assert result["inputIdentity"]["seasonId"] == "its-17"
    selected = select_its_scenario(
        out, season_id="its-17", revision="0.2", scenario_id="scenario:uplink-center",
    )
    assert selected is not None
    old, _ = records()
    assert selected["record"] == old
    assert [source["id"] for source in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        out, season_id="its-18", revision="2026.09.11", scenario_id="scenario:uplink-center",
    ) is None
