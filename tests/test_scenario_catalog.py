from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.scenario_catalog import ScenarioCatalog
from infinity_db.scenario_definition import parse_scenario_definition_record


@pytest.fixture(scope="module")
def scenario_catalog(tmp_path_factory: pytest.TempPathFactory) -> ScenarioCatalog:
    root = Path(__file__).parents[1]
    output = tmp_path_factory.mktemp("scenario-catalog") / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    return ScenarioCatalog(RulesDatabase(output))


def test_current_scenario_collections_are_derived_from_readable_publications(
    scenario_catalog: ScenarioCatalog,
) -> None:
    assert scenario_catalog.list_collections() == [
        {"id": "n5-core", "revision": "5.3", "title": "N5 Core Scenarios", "scenario_count": 4},
        {
            "id": "its-18", "revision": "2026.09.01",
            "title": "ITS Season 18: Overheat", "scenario_count": 1,
        },
    ]
    assert ScenarioCatalog(None).list_collections() == []


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


def test_its_inspired_asymmetric_objectives_and_split_deployments_project_without_loss(
    scenario_catalog: ScenarioCatalog,
) -> None:
    """A synthetic Crossing Lines/Critical Intervention shape survives catalog projection.

    This tests existing core model boundaries; it does not publish ITS missions or
    claim support for ITS-only circular geometry, Classifieds, or season overlays.
    """
    source, publication = next(
        (record, metadata)
        for record, metadata in scenario_catalog._records()
        if record["id"] == "scenario:annihilation"
    )
    synthetic = deepcopy(source)
    mission = synthetic["facts"]["mission"]
    mission["objectives"][0]["sideIds"] = ["side-a"]
    mission["objectives"][1]["sideIds"] = ["side-b"]
    for configuration in synthetic["facts"]["configurations"]:
        deployment = deepcopy(configuration["geometry"]["elements"][0])
        deployment["id"] = "deployment-a-second"
        # A second, separate region for the same side, with valid table geometry.
        depth = deployment["y2"]
        deployment["y1"] = depth + 2
        deployment["y2"] = depth + 4
        configuration["geometry"]["elements"].append(deployment)
    for size in mission["gameSizes"]:
        size["deployments"][0]["elementIds"].append("deployment-a-second")
    parsed = parse_scenario_definition_record(synthetic)
    assert parsed.mission is not None
    assert parsed.mission.objectives[0].side_ids == ("side-a",)
    assert parsed.mission.objectives[1].side_ids == ("side-b",)
    assert all(
        len(size.deployments[0].element_ids) == 2
        for size in parsed.mission.game_sizes
    )

    catalog = ScenarioCatalog(scenario_catalog.rules_database)
    catalog._records_cache = [(synthetic, deepcopy(publication))]
    item = catalog.get_scenario("annihilation", army_points=300)
    assert item is not None
    assert item["setup"]["game_size"]["deployments"] == [
        {
            "sideId": "side-a",
            "elementIds": ["deployment-a", "deployment-a-second"],
        },
        {"sideId": "side-b", "elementIds": ["deployment-b"]},
    ]
    assert item["objectives"][0]["sideIds"] == ["side-a"]
    assert item["objectives"][1]["sideIds"] == ["side-b"]
    assert "deployment-a-second" in {
        element["id"] for element in item["placement"]["geometry"]["elements"]
    }
    # A synthetic geometry projection must not revise official collection/season metadata.
    assert item["publication"]["collection_id"] == "n5-core"
    assert item["publication"]["revision"] == "5.3"
    assert item["skills"] == []
    assert [rule["rule"]["id"] for rule in item["special_rules"]] == [
        "rule:scenario:killing",
    ]


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


def test_explicit_scenario_collection_revision_selection_isolated_from_core(
    scenario_catalog: ScenarioCatalog,
) -> None:
    """Real Battleground publication is isolated from the Core scenario set."""
    core = scenario_catalog.list_scenarios(collection="n5-core", revision="5.3")
    assert [item["slug"] for item in core] == [
        "annihilation", "domination", "supplies", "firefight",
    ]
    current_its = scenario_catalog.list_scenarios(
        collection="its-18", revision="2026.09.01",
    )
    assert [item["slug"] for item in current_its] == ["battleground"]
    assert current_its[0]["publication"]["source_collection_id"] == (
        "its-season-18-2026.09.01"
    )
    battleground = scenario_catalog.get_scenario(
        "battleground", army_points=300,
        collection="its-18", revision="2026.09.01",
    )
    assert battleground is not None
    assert battleground["publication"]["collection_id"] == "its-18"
    assert battleground["selected_army_points"] == 300
    assert scenario_catalog.get_scenario(
        "battleground", army_points=300,
        collection="n5-core", revision="5.3",
    ) is None
    assert scenario_catalog.get_scenario(
        "annihilation", army_points=300,
        collection="its-18", revision="2026.09.01",
    ) is None
    assert scenario_catalog.list_scenarios(
        collection="its-17", revision="2025.09.01",
    ) == []


@pytest.mark.parametrize(
    ("collection", "revision"),
    [
        ("its-18", None),
        (None, "2026.09.01"),
        ("ITS 18", "2026.09.01"),
        ("its-18", ""),
        ("its-18", " 2026.09.01"),
    ],
)
def test_scenario_catalog_rejects_partial_or_malformed_season_selection(
    scenario_catalog: ScenarioCatalog,
    collection: str | None,
    revision: str | None,
) -> None:
    with pytest.raises(ValueError):
        scenario_catalog.list_scenarios(collection=collection, revision=revision)
    with pytest.raises(ValueError):
        scenario_catalog.get_scenario(
            "annihilation", army_points=300,
            collection=collection, revision=revision,
        )


# Official ITS Season 18: Overheat, English printed pp. 121-123.
# Battleground has no Classified Deck or HVT and uses exactly three
# source-defined end-of-game Sectors. This intentionally does not
# publish other Season 18 missions or extrapolate their geometry.
@pytest.mark.parametrize(
    ("points", "swc", "configuration", "width", "height", "depth",
     "sector_depth", "center"),
    [
        (150, 3, "150-points", 24, 32, 8, 4, 16),
        (200, 4, "200-250-points", 32, 48, 12, 8, 24),
        (250, 5, "200-250-points", 32, 48, 12, 8, 24),
        (300, 6, "300-400-points", 48, 48, 12, 8, 24),
        (350, 7, "300-400-points", 48, 48, 12, 8, 24),
        (400, 8, "300-400-points", 48, 48, 12, 8, 24),
    ],
)
def test_battleground_exact_its18_source_sizes_scoring_and_zone_geometry(
    scenario_catalog: ScenarioCatalog,
    points: int,
    swc: int,
    configuration: str,
    width: int,
    height: int,
    depth: int,
    sector_depth: int,
    center: int,
) -> None:
    item = scenario_catalog.get_scenario(
        "battleground", army_points=points, collection="its-18", revision="2026.09.01",
    )
    assert item is not None
    assert item["name"] == "Battleground"
    assert item["publication"]["collection_id"] == "its-18"
    assert item["publication"]["revision"] == "2026.09.01"
    assert item["publication"]["source_collection_id"] == "its-season-18-2026.09.01"
    assert {citation["page"] for citation in item["citations"]} == {121, 122, 123}
    assert {citation["source_id"] for citation in item["citations"]} == {
        "its-season-18-en-pdf",
    }
    assert item["supported_army_points"] == [150, 200, 250, 300, 350, 400]
    assert item["setup"]["game_size"]["swc"] == swc
    assert item["placement"]["configuration_id"] == configuration
    geometry = item["placement"]["geometry"]
    assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
    rectangles = {region["id"]: region for region in geometry["elements"]}
    assert {
        key: (rectangles[key]["x1"], rectangles[key]["y1"],
              rectangles[key]["x2"], rectangles[key]["y2"])
        for key in ("sector-near-a", "sector-center", "sector-near-b")
    } == {
        "sector-near-a": (0, center - 1.5 * sector_depth, width,
                          center - 0.5 * sector_depth),
        "sector-center": (0, center - 0.5 * sector_depth, width,
                           center + 0.5 * sector_depth),
        "sector-near-b": (0, center + 0.5 * sector_depth, width,
                          center + 1.5 * sector_depth),
    }
    assert (rectangles["deployment-a"]["y1"], rectangles["deployment-a"]["y2"]) == (
        0, depth,
    )
    assert (rectangles["deployment-b"]["y1"], rectangles["deployment-b"]["y2"]) == (
        height - depth, height,
    )
    assert item["setup"]["game_size"]["deployments"] == [
        {"sideId": "side-a", "elementIds": ["deployment-a"]},
        {"sideId": "side-b", "elementIds": ["deployment-b"]},
    ]

    objectives = {o["id"]: o for o in item["objectives"]}
    assert {
        obj: (o["maximumPoints"], o["sideIds"],
              o["awards"][0]["condition"]["elementIds"])
        for obj, o in objectives.items()
    } == {
        "near-sector-a": (2, ["side-a"], ["sector-near-a"]),
        "near-sector-b": (2, ["side-b"], ["sector-near-b"]),
        "central-sector": (3, ["side-a", "side-b"], ["sector-center"]),
        "far-sector-a": (5, ["side-a"], ["sector-near-b"]),
        "far-sector-b": (5, ["side-b"], ["sector-near-a"]),
    }
    assert all(o["timing"] == "end-of-game" for o in objectives.values())
    assert sum(
        o["maximumPoints"] for o in objectives.values() if "side-a" in o["sideIds"]
    ) == 10
    assert sum(
        o["maximumPoints"] for o in objectives.values() if "side-b" in o["sideIds"]
    ) == 10
    assert len(item["special_rules"]) == 6
    assert "not before" in " ".join(item["special_rules"][0]["paragraphs"])
    assert "20 Victory Points" in " ".join(item["special_rules"][3]["paragraphs"])
    assert item["end_conditions"] == [{
        "id": "round-limit", "checkAt": "end-of-round", "finishAt": "end-of-round",
        "condition": {"kind": "round-limit", "rounds": 3},
    }]
    assert item["source_issues"] == []
