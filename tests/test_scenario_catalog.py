from __future__ import annotations

from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.scenario_catalog import ScenarioCatalog


@pytest.fixture(scope="module")
def scenario_catalog(tmp_path_factory: pytest.TempPathFactory) -> ScenarioCatalog:
    root = Path(__file__).parents[1]
    output = tmp_path_factory.mktemp("scenario-catalog") / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    return ScenarioCatalog(RulesDatabase(output))


def test_scenario_catalog_lists_current_publications_in_collection_order(
    scenario_catalog: ScenarioCatalog,
) -> None:
    items = scenario_catalog.list_scenarios()

    assert [item["slug"] for item in items] == [
        "annihilation",
        "domination",
        "supplies",
        "firefight",
    ]
    assert all(item["supported_army_points"] == [150, 200, 250, 300, 350, 400] for item in items)
    assert all(item["publication"]["collection_id"] == "n5-core" for item in items)
    assert all(item["publication"]["revision"] == "5.3" for item in items)
    assert all(item["publication"]["source_collection_id"] == "n5-core-v5.3" for item in items)
    assert all(len(item["publication"]["content_sha256"]) == 64 for item in items)
    assert all(item["publication"]["sources"][0]["version"] == "5.3" for item in items)


def test_scenario_detail_projects_exact_domination_game_size(
    scenario_catalog: ScenarioCatalog,
) -> None:
    item = scenario_catalog.get_scenario("domination", army_points=350)

    assert item is not None
    assert item["selected_army_points"] == 350
    assert item["setup"]["game_size"] == {
        "armyPoints": 350,
        "swc": 6,
        "minimumVictoryPoints": 88,
        "configurationId": "300-400-points",
        "deployments": [
            {"sideId": "side-a", "elementIds": ["deployment-a"]},
            {"sideId": "side-b", "elementIds": ["deployment-b"]},
        ],
    }
    assert item["placement"]["configuration_id"] == "300-400-points"
    assert item["placement"]["configuration_army_points"] == [300, 350, 400]
    assert item["placement"]["geometry"]["title"] == "Domination"
    assert {issue["id"] for issue in item["source_issues"]} == {"350-point-swc"}
    assert [rule["id"] for rule in item["special_rules"]] == [
        "dominate-quadrants",
        "consoles",
        "specialist-troops",
    ]
    assert [rule["rule"]["id"] for rule in item["special_rules"]] == [
        "rule:scenario:dominate-quadrants",
        "rule:scenario:consoles",
        "rule:specialist-troops:standard",
    ]
    assert [skill["id"] for skill in item["skills"]] == ["skill:hack-consoles"]
    assert all(
        award["armyPoints"] == [350]
        for objective in item["objectives"]
        for award in objective["awards"]
    )


def test_scenario_detail_filters_point_specific_source_issues(
    scenario_catalog: ScenarioCatalog,
) -> None:
    domination = scenario_catalog.get_scenario("domination", army_points=300)
    supplies = scenario_catalog.get_scenario("supplies", army_points=300)

    assert domination is not None and domination["source_issues"] == []
    assert supplies is not None and supplies["source_issues"] == []
    annotations = supplies["placement"]["geometry"]["annotations"]
    assert {
        (annotation["kind"], annotation["target"], annotation.get("edge"))
        for annotation in annotations
        if annotation["kind"] == "point-edge-distance"
    } == {
        ("point-edge-distance", "supply-box-left", "left"),
        ("point-edge-distance", "supply-box-right", "right"),
    }


def test_scenario_detail_rejects_unsupported_game_size_and_unknown_identity(
    scenario_catalog: ScenarioCatalog,
) -> None:
    with pytest.raises(ValueError, match="does not support 175 Army Points"):
        scenario_catalog.get_scenario("annihilation", army_points=175)
    with pytest.raises(ValueError, match="positive integer"):
        scenario_catalog.get_scenario("annihilation", army_points=0)
    assert scenario_catalog.get_scenario("missing", army_points=300) is None


def test_scenario_catalog_is_empty_without_rules_database() -> None:
    catalog = ScenarioCatalog(None)

    assert catalog.list_scenarios() == []
    assert catalog.get_scenario("annihilation", army_points=300) is None
