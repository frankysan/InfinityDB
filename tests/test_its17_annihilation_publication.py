"""ITS 17 V0.2 Annihilation: source-scoped EN/ES scoring conflicts."""
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
SIZES = (150, 200, 250, 300, 350, 400)


def records() -> tuple[dict, dict]:
    old = load_curated_document(SEASON, shared_scenario_library=SHARED)
    current = load_curated_document(ITS18)
    return (
        next(item for item in old["records"] if item["id"] == "scenario:annihilation"),
        next(item for item in current["records"] if item["id"] == "scenario:annihilation"),
    )


def test_its17_annihilation_membership_is_independently_cited_and_pinned() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    shared = json.loads(SHARED.read_text(encoding="utf-8"))
    assert source["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert [definition["id"] for definition in shared["definitions"]] == [
        "scenario:evacuation",
        "scenario:hardlock",
        "scenario:uplink-center",
        "scenario:battleground",
        "scenario:annihilation",
        "scenario:cutthroat",
        "scenario:superiority",
        "scenario:provisioning",
        "scenario:area-of-interest",
        "scenario:last-launch",
        "scenario:b-pong",
    ]
    definition = shared["definitions"][4]
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = source["scenarioCollection"]["members"][4]
    assert member["scenarioId"] == "scenario:annihilation"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(row["sourceId"], row["page"]) for row in binding["citations"]] == [
        (EN, 81), (EN, 82), (ES, 85), (ES, 86), (ES, 87),
    ]


def test_its17_en_annihilation_scoring_bands_match_reviewed_ranges() -> None:
    old, current = records()
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert old["facts"]["playRequirements"] == current["facts"]["playRequirements"]
    assert old["facts"]["mission"]["gameSizes"] == current["facts"]["mission"]["gameSizes"]
    assert old["facts"]["mission"]["objectives"] == current["facts"]["mission"]["objectives"]
    assert old["facts"]["mission"]["rules"] == current["facts"]["mission"]["rules"]
    assert old["facts"]["mission"]["endConditions"] == (
        current["facts"]["mission"]["endConditions"]
    )
    objectives = {row["id"]: row for row in old["facts"]["mission"]["objectives"]}
    assert set(objectives) == {
        "destroy-forces", "preserve-forces", "eliminate-lieutenant",
    }
    expected_bounds = {
        150: ((40, 75), (76, 125), (126, None)),
        200: ((50, 100), (101, 150), (151, None)),
        250: ((65, 125), (126, 200), (201, None)),
        300: ((75, 150), (151, 250), (251, None)),
        350: ((85, 175), (176, 274), (276, None)),
        400: ((100, 200), (201, 300), (301, None)),
    }
    for objective_id in ("destroy-forces", "preserve-forces"):
        objective = objectives[objective_id]
        assert objective["aggregation"] == "exclusive"
        assert objective["maximumPoints"] == 4
        for size, bounds in expected_bounds.items():
            awards = [
                award for award in objective["awards"] if award["armyPoints"] == [size]
            ]
            assert [award["objectivePoints"] for award in awards] == [1, 3, 4]
            assert [
                (award["condition"]["minimum"], award["condition"]["maximum"])
                for award in awards
            ] == list(bounds)
    lieutenant = objectives["eliminate-lieutenant"]
    assert lieutenant["maximumPoints"] == lieutenant["awards"][0]["objectivePoints"] == 2
    assert lieutenant["awards"][0]["armyPoints"] == list(SIZES)


def test_its17_annihilation_retains_different_es_scoring_and_source_errors() -> None:
    old, current = records()
    assert old["facts"]["configurations"] == current["facts"]["configurations"]
    configs = {c["id"]: c["geometry"] for c in old["facts"]["configurations"]}
    assert configs.keys() == {"150-points", "200-250-points", "300-400-points"}
    assert configs["150-points"]["table"] == {"width": 24, "height": 32, "unit": "in"}
    for name, depth in (("150-points", 8), ("200-250-points", 12),
                        ("300-400-points", 12)):
        region = {e["id"]: e for e in configs[name]["elements"]}
        assert region["deployment-a"]["y2"] == depth
        assert region["deployment-b"]["y1"] == configs[name]["table"]["height"] - depth

    issues = {item["id"]: item for item in old["facts"]["mission"]["sourceIssues"]}
    assert set(issues) == {
        "its17-surviving-vp-en-es-score-discrepancy",
        "its17-150-point-deployment-units",
        "its17-350-point-destroy-forces-gap",
        "its17-350-point-preserve-forces-gap",
    }
    assert all(item["status"] == "needs-verification" for item in issues.values())
    scoring = issues["its17-surviving-vp-en-es-score-discrepancy"]
    assert scoring["objectiveId"] == "preserve-forces"
    assert scoring["armyPoints"] == list(SIZES)
    assert "3/4/4" in scoring["description"] and "1/3/4" in scoring["description"]
    deployment = issues["its17-150-point-deployment-units"]
    assert deployment["armyPoints"] == [150]
    assert deployment["geometryElementIds"] == ["deployment-a", "deployment-b"]
    assert "[[distance:8:inch]] x [[distance:32:cm]]" in deployment["description"]
    assert "[[distance:20:cm]] x [[distance:60:cm]]" in deployment["description"]
    assert all("275" in issues[identifier]["description"] for identifier in (
        "its17-350-point-destroy-forces-gap",
        "its17-350-point-preserve-forces-gap",
    ))
    # The unrelated ITS 18 Spanish 400-point threshold typo is not
    # retroactively attributed to the distinct ITS 17 Spanish original.
    assert not any("400-point-preserve-forces-bilingual-threshold" in key for key in issues)
    assert {source["sourceId"] for source in old["citations"]} == {EN, ES}


def test_its17_annihilation_build_and_exact_publication_selection(tmp_path: Path) -> None:
    output = tmp_path / "its17.db"
    result = build_its_database(SEASON, output, shared_library=SHARED)
    assert len(result["scenarios"]) == 11
    assert result["inputIdentity"]["seasonId"] == "its-17"
    assert result["inputIdentity"]["sharedScenarioLibrary"]["sha256"] == (
        hashlib.sha256(SHARED.read_bytes()).hexdigest()
    )
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == result
    selected = select_its_scenario(
        output, season_id="its-17", revision="0.2", scenario_id="scenario:annihilation",
    )
    assert selected is not None
    old, _ = records()
    assert selected["record"] == old
    assert [source["id"] for source in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        output, season_id="its-18", revision="2026.09.11", scenario_id="scenario:annihilation",
    ) is None
