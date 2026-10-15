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


# Source-reviewed from English N5 v5.3 Forces and Deployment tables,
# printed pp. 150 (Annihilation), 151 (Domination), 153 (Supplies), 155 (Firefight).
# This test deliberately does not depend on locally retained/gitignored PDFs.
@pytest.mark.parametrize(
    ("slug", "source_pages", "swc_at_350", "minimum_vp", "objectives", "rules"),
    [
        (
            "annihilation", {149, 150}, 7, False,
            ("destroy-forces", "preserve-forces", "eliminate-command"),
            ("rule:scenario:killing",),
        ),
        (
            "domination", {151, 152}, 6, True,
            ("dominate-quadrants", "hacked-consoles"),
            (
                "rule:scenario:dominate-quadrants",
                "rule:scenario:consoles",
                "rule:specialist-troops:standard",
            ),
        ),
        (
            "supplies", {153, 154}, 7, True,
            ("controlled-boxes", "more-boxes", "all-boxes"),
            (
                "rule:scenario:supply-boxes",
                "rule:scenario:carrying-supply-boxes",
                "rule:scenario:controlling-supply-boxes",
                "rule:specialist-troops:standard",
            ),
        ),
        (
            "firefight", {155, 156}, 7, False,
            (
                "surviving-specialists", "killed-specialists",
                "killed-lieutenants", "killed-army-points",
            ),
            (
                "rule:scenario:killing",
                "rule:scenario:reinforced-tactical-link",
                "rule:scenario:designated-landing-area",
                "rule:specialist-troops:standard",
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    ("points", "standard_swc", "table_width", "table_height", "deployment_depth",
     "minimum_victory_points", "configuration_id"),
    [
        (150, 3, 24, 32, 8, 38, "150-points"),
        (200, 4, 32, 48, 12, 50, "200-250-points"),
        (250, 5, 32, 48, 12, 63, "200-250-points"),
        (300, 6, 48, 48, 12, 75, "300-400-points"),
        (350, 7, 48, 48, 12, 88, "300-400-points"),
        (400, 8, 48, 48, 12, 100, "300-400-points"),
    ],
)
def test_core_scenario_source_inventory_matches_all_24_published_sizes(
    scenario_catalog: ScenarioCatalog,
    slug: str,
    source_pages: set[int],
    swc_at_350: int,
    minimum_vp: bool,
    objectives: tuple[str, ...],
    rules: tuple[str, ...],
    points: int,
    standard_swc: int,
    table_width: int,
    table_height: int,
    deployment_depth: int,
    minimum_victory_points: int,
    configuration_id: str,
) -> None:
    """Source chart, composed DB and public read model agree for all 24 choices."""
    item = scenario_catalog.get_scenario(slug, army_points=points)
    assert item is not None
    assert item["selected_army_points"] == points
    assert item["supported_army_points"] == [150, 200, 250, 300, 350, 400]
    assert item["publication"]["revision"] == "5.3"
    assert item["publication"]["source_collection_id"] == "n5-core-v5.3"
    assert {
        (citation["source_id"], citation["page"])
        for citation in item["citations"]
    } == {("n5-core-v5.3-pdf", page) for page in source_pages}

    size = item["setup"]["game_size"]
    assert size["armyPoints"] == points
    # Domination explicitly prints 6, not the normal 7, at 350 Army Points.
    assert size["swc"] == (swc_at_350 if points == 350 else standard_swc)
    if minimum_vp:
        assert size["minimumVictoryPoints"] == minimum_victory_points
    else:
        assert "minimumVictoryPoints" not in size
    assert size["configurationId"] == configuration_id
    assert size["deployments"] == [
        {"sideId": "side-a", "elementIds": ["deployment-a"]},
        {"sideId": "side-b", "elementIds": ["deployment-b"]},
    ]

    placement = item["placement"]
    assert placement["configuration_id"] == configuration_id
    assert points in placement["configuration_army_points"]
    geometry = placement["geometry"]
    assert geometry["table"] == {
        "width": table_width, "height": table_height, "unit": "in",
    }
    rects = {
        element["id"]: element
        for element in geometry["elements"]
        if element["id"] in ("deployment-a", "deployment-b")
    }
    assert rects["deployment-a"]["y2"] == deployment_depth
    assert rects["deployment-b"]["y1"] == {
        "anchor": "bottom", "offset": -deployment_depth,
    }
    assert [objective["id"] for objective in item["objectives"]] == list(objectives)
    assert all(
        award["armyPoints"] == [points]
        for objective in item["objectives"]
        for award in objective["awards"]
    )
    assert tuple(rule["rule"]["id"] for rule in item["special_rules"]) == rules
    assert len(item["end_conditions"]) == 2
    assert item["end_conditions"][0]["id"] == "round-limit"
    assert item["end_conditions"][0]["condition"]["rounds"] == 3

    if slug == "domination" and points == 350:
        assert {issue["id"] for issue in item["source_issues"]} == {
            "350-point-swc",
        }
        assert item["source_issues"][0]["status"] == "needs-verification"
        assert "Spanish N5.3" in item["source_issues"][0]["description"]
    elif slug == "annihilation" and points == 350:
        assert {issue["id"] for issue in item["source_issues"]} == {
            "350-point-survival-bands",
        }
        assert item["source_issues"][0]["status"] == "reviewed-resolution"
        assert "Spanish N5.3" in item["source_issues"][0]["description"]
    else:
        assert item["source_issues"] == []


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
        if annotation["kind"] == "element-edge-distance"
    } == {
        ("element-edge-distance", "supply-box-left", "left"),
        ("element-edge-distance", "supply-box-right", "right"),
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
