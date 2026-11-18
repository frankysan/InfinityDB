"""ITS 17 Akial Interference: source-reviewed history, Skills and isolation."""
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
from infinity_db.scenario_definition import parse_scenario_definition_record

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
        next(r for r in old["records"] if r["id"] == "scenario:akial-interference"),
        next(r for r in current["records"] if r["id"] == "scenario:akial-interference"),
    )


def test_its17_akial_source_pins_and_membership() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert len(library["definitions"]) == 16
    definition = library["definitions"][15]
    assert definition["id"] == "scenario:akial-interference"
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = season["scenarioCollection"]["members"][15]
    assert member["scenarioId"] == "scenario:akial-interference"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(c["sourceId"], c["page"]) for c in binding["citations"]] == [
        *((EN, p) for p in range(31, 36)),
        *((ES, p) for p in range(58, 63)),
    ]


def test_its17_akial_scoring_geometry_and_hvt_setup() -> None:
    old, modern = records()
    history = old["facts"]
    current = modern["facts"]
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert history["playRequirements"] == {
        "classifiedObjectives": 1,
        "tacticalObjectives": 0,
        "hvts": 4,
        "sharedClassifiedObjectivesPerRound": 2,
    }
    assert history["mission"]["objectives"] == current["mission"]["objectives"]
    assert [
        (o["id"], o["maximumPoints"]) for o in history["mission"]["objectives"]
    ] == [
        ("common-classified", 6),
        ("more-classified", 1),
        ("classified-every-round", 1),
        ("private-classified", 2),
    ]
    assert history["mission"]["endConditions"] == current["mission"]["endConditions"]
    assert history["mission"]["gameSizes"] == current["mission"]["gameSizes"]
    assert history["configurations"] == current["configurations"]
    for config, width, height, depth in zip(
        history["configurations"], (24, 32, 48), (32, 48, 48),
        (8, 12, 12), strict=True,
    ):
        geom = config["geometry"]
        elements = {e["id"]: e for e in geom["elements"]}
        assert (geom["table"]["width"], geom["table"]["height"]) == (width, height)
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        assert (elements["akial-antenna"]["x"], elements["akial-antenna"]["y"]) == (
            width / 2, height / 2,
        )


def test_its17_akial_local_rule_and_nested_skill_citation_provenance() -> None:
    historic, modern = records()
    rules = {r["id"]: r for r in historic["facts"]["mission"]["rules"]}
    latest = {r["id"]: r for r in modern["facts"]["mission"]["rules"]}
    assert "Secure Treasure" in rules["multiple-hvts"]["paragraphs"][1]
    assert "Secure Treasure" not in latest["multiple-hvts"]["paragraphs"][1]
    assert "four HVT" in rules["multiple-hvts"]["paragraphs"][0]
    assert "matching" in rules["akial-antenna"]["paragraphs"][0]
    assert "40 mm" in latest["akial-antenna"]["paragraphs"][0]
    assert "Neither original fixes a 40 mm size" in rules["akial-antenna"]["paragraphs"][0]
    emit = rules["emit-akial-interference"]
    filtering = rules["filter-signal"]
    assert emit["skillTypeIds"] == filtering["skillTypeIds"] == ["short-skill"]
    assert emit["skillCitations"] == [
        {"sourceId": EN, "page": 33}, {"sourceId": EN, "page": 34},
        {"sourceId": ES, "page": 61},
    ]
    assert filtering["skillCitations"] == [
        {"sourceId": EN, "page": 34}, {"sourceId": ES, "page": 62},
    ]
    assert "once per Game Round" in emit["skillFacts"]["requirements"][2]
    assert "repeated" in emit["skillFacts"]["effects"][0] or (
        "retried" in emit["skillFacts"]["effects"][0]
    )
    assert "Private Classified Objectives" in emit["skillFacts"]["restrictions"][0]
    assert "only once" in emit["skillFacts"]["restrictions"][1]
    assert "unresolved" not in filtering["skillFacts"]["sourceNotes"][0]
    assert "without a Roll" in filtering["skillFacts"]["sourceNotes"][0]
    assert "its-season-18" not in json.dumps(historic)
    assert "ITS 18" not in json.dumps(historic)
    issues = historic["facts"]["mission"]["sourceIssues"]
    assert len(issues) == 1
    issue = issues[0]
    assert issue["id"] == "its17-akial-interference-emit-retries-per-round"
    assert issue["armyPoints"] == SIZES
    assert issue["objectiveId"] == "common-classified"
    assert issue["status"] == "needs-verification"
    assert "EN p. 34 and ES p. 61" in issue["description"]
    assert "Normal WIP" in issue["description"]
    assert modern["facts"]["mission"]["sourceIssues"][0]["id"] != issue["id"]


def test_its17_akial_skill_source_ids_remain_fail_closed() -> None:
    for invalid_source_id in (
        "ITS-season-17-v0.2-en-pdf",
        "its-season-17-v0..2-en-pdf",
        "its-season-17-v0/2-en-pdf",
        "its-season-17-v0.2-en-pdf-",
    ):
        historical, _ = records()
        skill = next(
            r for r in historical["facts"]["mission"]["rules"]
            if r["id"] == "emit-akial-interference"
        )
        skill["skillCitations"][0]["sourceId"] = invalid_source_id
        try:
            parse_scenario_definition_record(historical)
        except ValueError as exc:
            assert "source identifier" in str(exc)
        else:
            raise AssertionError(f"Accepted invalid source ID: {invalid_source_id}")


def test_its17_akial_builds_only_in_historical_sqlite(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON, target, shared_library=SHARED)
    assert len(report["scenarios"]) == 16
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED,
        require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2",
        scenario_id="scenario:akial-interference",
    )
    assert selected is not None
    historical, _ = records()
    assert selected["record"] == historical
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:akial-interference",
    ) is None
