from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.scenario_components import compose_scenario_record
from infinity_db.scenario_definition import (
    ScenarioDefinitionError,
    parse_scenario_definition_record,
    scenario_definition_from_curated_document,
    select_scenario_geometry,
)
from infinity_db.scenario_geometry import (
    AreaSizeAnnotation,
    DimensionAnnotation,
    LineElement,
    MarkerElement,
    PointEdgeDistanceAnnotation,
    RectangleElement,
    resolve_coordinate,
)
from infinity_db.scenario_mission import (
    DominatedRegionComparison,
    ElementStatusComparison,
    ElementStatusCount,
    MetricComparison,
    NumericRangeCondition,
    ProseCondition,
)

_CORE_RULES = Path("data/curated/rules/n5-core-v5.3.json")


def test_maintained_domination_definition_owns_all_core_map_configurations() -> None:
    document = load_curated_document(_CORE_RULES)
    definition = scenario_definition_from_curated_document(
        document, "scenario:domination"
    )

    assert definition.name == "Domination"
    assert [configuration.id for configuration in definition.configurations] == [
        "150-points",
        "200-250-points",
        "300-400-points",
    ]
    assert [configuration.army_points for configuration in definition.configurations] == [
        (150,),
        (200, 250),
        (300, 350, 400),
    ]
    assert [
        (configuration.geometry.table.width, configuration.geometry.table.height)
        for configuration in definition.configurations
    ] == [(24, 32), (32, 48), (48, 48)]

    for configuration in definition.configurations:
        markers = [
            element
            for element in configuration.geometry.elements
            if isinstance(element, MarkerElement)
        ]
        assert len(markers) == 4
        assert {marker.marker_type for marker in markers} == {"console"}
        dimensions = [
            annotation
            for annotation in configuration.geometry.annotations
            if isinstance(annotation, DimensionAnnotation)
        ]
        area_sizes = [
            annotation
            for annotation in configuration.geometry.annotations
            if isinstance(annotation, AreaSizeAnnotation)
        ]
        assert {annotation.target for annotation in dimensions} == {
            "deployment-a",
            "deployment-b",
        }
        assert {annotation.target for annotation in area_sizes} == {
            "quadrant-1",
            "quadrant-2",
            "quadrant-3",
            "quadrant-4",
        }


def test_select_maintained_domination_geometry_uses_army_points() -> None:
    document = load_curated_document(_CORE_RULES)
    definition = scenario_definition_from_curated_document(
        document, "scenario:domination"
    )

    geometry = select_scenario_geometry(definition, 250)

    assert (geometry.table.width, geometry.table.height) == (32, 48)
    console = next(
        element
        for element in geometry.elements
        if isinstance(element, MarkerElement) and element.id == "console-q1"
    )
    assert resolve_coordinate(console.x, axis="x", table=geometry.table) == 8
    assert resolve_coordinate(console.y, axis="y", table=geometry.table) == 18


def test_maintained_supplies_definition_owns_all_core_map_configurations() -> None:
    document = load_curated_document(_CORE_RULES)
    definition = scenario_definition_from_curated_document(document, "scenario:supplies")

    assert definition.name == "Supplies"
    assert [configuration.id for configuration in definition.configurations] == [
        "150-points",
        "200-250-points",
        "300-400-points",
    ]
    assert [configuration.army_points for configuration in definition.configurations] == [
        (150,),
        (200, 250),
        (300, 350, 400),
    ]

    for configuration in definition.configurations:
        geometry = configuration.geometry
        width = geometry.table.width
        height = geometry.table.height
        markers = [
            element for element in geometry.elements if isinstance(element, MarkerElement)
        ]
        assert len(markers) == 3
        assert {marker.marker_type for marker in markers} == {"supply-box"}
        assert {
            (
                resolve_coordinate(marker.x, axis="x", table=geometry.table),
                resolve_coordinate(marker.y, axis="y", table=geometry.table),
            )
            for marker in markers
        } == {
            (8, height / 2),
            (width / 2, height / 2),
            (width - 8, height / 2),
        }
        dimensions = [
            annotation
            for annotation in geometry.annotations
            if isinstance(annotation, DimensionAnnotation)
        ]
        point_offsets = [
            annotation
            for annotation in geometry.annotations
            if isinstance(annotation, PointEdgeDistanceAnnotation)
        ]
        assert {annotation.target for annotation in dimensions} == {
            "deployment-a",
            "deployment-b",
        }
        assert {(annotation.target, annotation.edge) for annotation in point_offsets} == {
            ("supply-box-left", "left"),
            ("supply-box-right", "right"),
        }


def test_select_maintained_supplies_geometry_uses_army_points() -> None:
    document = load_curated_document(_CORE_RULES)
    definition = scenario_definition_from_curated_document(document, "scenario:supplies")

    geometry = select_scenario_geometry(definition, 250)

    assert (geometry.table.width, geometry.table.height) == (32, 48)
    right_box = next(
        element
        for element in geometry.elements
        if isinstance(element, MarkerElement) and element.id == "supply-box-right"
    )
    assert resolve_coordinate(right_box.x, axis="x", table=geometry.table) == 24
    assert resolve_coordinate(right_box.y, axis="y", table=geometry.table) == 24


@pytest.mark.parametrize(
    ("scenario_id", "expected_name"),
    [
        ("scenario:annihilation", "Annihilation"),
        ("scenario:firefight", "Firefight"),
    ],
)
def test_maintained_standard_deployment_scenarios_own_all_core_map_configurations(
    scenario_id: str, expected_name: str
) -> None:
    document = load_curated_document(_CORE_RULES)
    definition = scenario_definition_from_curated_document(document, scenario_id)

    assert definition.name == expected_name
    assert [configuration.id for configuration in definition.configurations] == [
        "150-points",
        "200-250-points",
        "300-400-points",
    ]
    assert [configuration.army_points for configuration in definition.configurations] == [
        (150,),
        (200, 250),
        (300, 350, 400),
    ]

    for configuration in definition.configurations:
        geometry = configuration.geometry
        width = geometry.table.width
        height = geometry.table.height
        deployment_depth = 8 if (width, height) == (24, 32) else 12
        elements = {element.id: element for element in geometry.elements}

        deployment_a = elements["deployment-a"]
        deployment_b = elements["deployment-b"]
        center_line = elements["center-line"]
        assert isinstance(deployment_a, RectangleElement)
        assert isinstance(deployment_b, RectangleElement)
        assert isinstance(center_line, LineElement)
        assert resolve_coordinate(deployment_a.y2, axis="y", table=geometry.table) == (
            deployment_depth
        )
        assert resolve_coordinate(deployment_b.y1, axis="y", table=geometry.table) == (
            height - deployment_depth
        )
        assert resolve_coordinate(center_line.y1, axis="y", table=geometry.table) == (
            height / 2
        )
        assert not any(isinstance(element, MarkerElement) for element in geometry.elements)

        dimensions = [
            annotation
            for annotation in geometry.annotations
            if isinstance(annotation, DimensionAnnotation)
        ]
        assert {(annotation.target, annotation.axis) for annotation in dimensions} == {
            ("deployment-a", "y"),
            ("deployment-b", "y"),
        }


def test_all_core_scenarios_are_maintained_definitions() -> None:
    document = load_curated_document(_CORE_RULES)
    scenario_ids = {
        record["id"]
        for record in document["records"]
        if record.get("kind") == "scenario"
    }

    assert scenario_ids == {
        "scenario:annihilation",
        "scenario:domination",
        "scenario:supplies",
        "scenario:firefight",
    }


def test_select_scenario_geometry_rejects_unsupported_army_points() -> None:
    document = load_curated_document(_CORE_RULES)
    definition = scenario_definition_from_curated_document(
        document, "scenario:domination"
    )

    with pytest.raises(ScenarioDefinitionError, match="does not support 175 Army Points"):
        select_scenario_geometry(definition, 175)


def test_scenario_definition_rejects_overlapping_army_points() -> None:
    record = {
        "id": "scenario:test",
        "kind": "scenario",
        "name": "Test",
        "facts": {
            "definitionVersion": 1,
            "configurations": [
                {
                    "id": "first",
                    "armyPoints": [150, 200],
                    "geometry": {
                        "format": "InfinityDB scenario geometry",
                        "formatVersion": 1,
                        "title": "Test",
                        "table": {"width": 24, "height": 32, "unit": "in"},
                        "elements": [],
                    },
                },
                {
                    "id": "second",
                    "armyPoints": [200],
                    "geometry": {
                        "format": "InfinityDB scenario geometry",
                        "formatVersion": 1,
                        "title": "Test",
                        "table": {"width": 32, "height": 48, "unit": "in"},
                        "elements": [],
                    },
                },
            ],
        },
    }

    with pytest.raises(ScenarioDefinitionError, match="overlaps another configuration: 200"):
        parse_scenario_definition_record(record)


@pytest.fixture
def annihilation_record() -> dict[str, Any]:
    document = load_curated_document(_CORE_RULES)
    return deepcopy(
        compose_scenario_record(
            next(
                record for record in document["records"] if record["id"] == "scenario:annihilation"
            ),
            document,
        )
    )


def test_annihilation_mission_setup_reuses_geometry_and_preserves_end_conditions(
    annihilation_record: dict[str, Any],
) -> None:
    definition = parse_scenario_definition_record(annihilation_record)
    mission = definition.mission
    assert mission is not None
    assert [(size.army_points, size.swc, size.configuration_id) for size in mission.game_sizes] == [
        (150, 3, "150-points"),
        (200, 4, "200-250-points"),
        (250, 5, "200-250-points"),
        (300, 6, "300-400-points"),
        (350, 7, "300-400-points"),
        (400, 8, "300-400-points"),
    ]
    for size in mission.game_sizes:
        assert [
            (deployment.side_id, deployment.element_ids) for deployment in size.deployments
        ] == [
            ("side-a", ("deployment-a",)),
            ("side-b", ("deployment-b",)),
        ]
    assert [side.id for side in mission.sides] == ["side-a", "side-b"]
    assert len(mission.rules) == 1
    assert "[[state:dead]]" in mission.rules[0].paragraphs[0]
    assert "never deployed" in mission.rules[0].paragraphs[1]
    round_limit, all_null = mission.end_conditions
    assert (round_limit.rounds, round_limit.check_at, round_limit.finish_at) == (
        3,
        "end-of-round",
        "end-of-round",
    )
    assert (all_null.check_at, all_null.finish_at) == ("tactical-phase", "end-of-player-turn")
    assert all_null.description and "classified as Null" in all_null.description
    assert {
        (citation["sourceId"], citation["page"]) for citation in annihilation_record["citations"]
    } == {
        ("n5-core-v5.3-pdf", 149),
        ("n5-core-v5.3-pdf", 150),
    }


@pytest.mark.parametrize(
    ("points", "kill_ranges", "survival_ranges"),
    [
        (150, [(40, 75), (76, 125), (126, None)], [(40, 75), (76, 125), (126, None)]),
        (200, [(50, 100), (101, 150), (151, None)], [(50, 100), (101, 150), (151, None)]),
        (250, [(65, 125), (126, 200), (201, None)], [(65, 125), (126, 200), (201, None)]),
        (300, [(75, 150), (151, 250), (251, None)], [(75, 150), (151, 250), (251, None)]),
        (350, [(85, 175), (176, 270), (271, None)], [(85, 150), (176, 270), (251, None)]),
        (400, [(100, 200), (201, 300), (301, None)], [(100, 200), (201, 300), (301, None)]),
    ],
)
def test_annihilation_preserves_each_printed_scoring_row(
    annihilation_record: dict[str, Any],
    points: int,
    kill_ranges: list[tuple[int, int | None]],
    survival_ranges: list[tuple[int, int | None]],
) -> None:
    mission = parse_scenario_definition_record(annihilation_record).mission
    assert mission is not None
    kill, survival, command = mission.objectives
    for objective, expected_ranges, metric in (
        (kill, kill_ranges, "enemy-army-points-killed"),
        (survival, survival_ranges, "surviving-victory-points"),
    ):
        assert (objective.timing, objective.aggregation, objective.maximum_points) == (
            "end-of-game",
            "exclusive",
            4,
        )
        applicable = [award for award in objective.awards if points in award.army_points]
        assert [award.objective_points for award in applicable] == [1, 3, 4]
        assert [award.condition for award in applicable] == [
            NumericRangeCondition(metric, low, high) for low, high in expected_ranges
        ]
    assert command.maximum_points == command.awards[0].objective_points == 2
    assert points in command.awards[0].army_points
    assert command.awards[0].condition == ProseCondition("Kill the enemy [[skill:lieutenant]].")
    assert [issue.id for issue in mission.source_issues if points in issue.army_points] == (
        ["350-point-survival-bands"] if points == 350 else []
    )


def test_geometry_only_definitions_remain_supported(annihilation_record: dict[str, Any]) -> None:
    del annihilation_record["facts"]["mission"]
    definition = parse_scenario_definition_record(annihilation_record)
    assert definition.mission is None
    assert select_scenario_geometry(definition, 350).table.width == 48


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("definitionVersion",), True, "definitionVersion"),
        (("mission", "futureFeature"), {}, "unsupported fields"),
        (("mission", "gameSizes"), [], "non-empty"),
        (("mission", "gameSizes", 0, "armyPoints"), True, "integer"),
        (("mission", "gameSizes", 0, "configurationId"), "300-400-points", "geometry for 150"),
        (("mission", "gameSizes", 0, "swc"), True, "finite non-negative"),
        (("mission", "gameSizes", 0, "swc"), -1, "finite non-negative"),
        (("mission", "gameSizes", 0, "swc"), float("nan"), "finite non-negative"),
        (("mission", "gameSizes", 0, "swc"), float("inf"), "finite non-negative"),
        (("mission", "gameSizes", 0, "deployments", 0, "sideId"), "missing", "unknown side"),
        (
            ("mission", "gameSizes", 0, "deployments", 0, "elementIds"),
            ["missing"],
            "unknown references",
        ),
        (
            ("mission", "gameSizes", 0, "deployments", 0, "elementIds"),
            ["center-line"],
            "unknown references",
        ),
        (
            ("mission", "gameSizes", 0, "deployments", 1, "elementIds"),
            ["deployment-a"],
            "multiple sides",
        ),
        (("mission", "objectives", 0, "sideIds"), ["missing"], "unknown references"),
        (("mission", "objectives", 0, "timing"), "during-match", "one of"),
        (("mission", "objectives", 0, "awards", 0, "armyPoints"), [175], "unsupported Army Points"),
        (("mission", "objectives", 0, "awards", 0, "objectivePoints"), 5, "exceeds"),
        (("mission", "objectives", 0, "awards", 0, "condition", "minimum"), -1, "integer"),
        (("mission", "objectives", 0, "awards", 0, "condition", "maximum"), 39, "integer"),
        (
            ("mission", "objectives", 0, "awards", 0, "condition", "kind"),
            "game-engine",
            "unsupported condition",
        ),
        (("mission", "endConditions", 0, "condition", "rounds"), 0, "integer"),
        (("mission", "endConditions", 0, "finishAt"), "immediate", "round-limit"),
        (("mission", "sourceIssues"), [], "overlapping score ranges for 350"),
        (("mission", "sourceIssues", 0, "objectiveId"), "missing", "unknown objective"),
        (("mission", "sourceIssues", 0, "armyPoints"), [300], "overlapping score ranges for 350"),
        (("mission", "sourceIssues", 0, "status"), "resolved", "one of"),
    ],
)
def test_mission_rejects_invalid_data_and_unacknowledged_overlap(
    annihilation_record: dict[str, Any],
    path: tuple[str | int, ...],
    value: Any,
    message: str,
) -> None:
    target = annihilation_record["facts"]
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = value
    with pytest.raises(ScenarioDefinitionError, match=message):
        parse_scenario_definition_record(annihilation_record)


def test_mission_requires_complete_game_size_and_objective_coverage(
    annihilation_record: dict[str, Any],
) -> None:
    incomplete = deepcopy(annihilation_record)
    incomplete["facts"]["mission"]["gameSizes"].pop()
    with pytest.raises(ScenarioDefinitionError, match="gameSizes must cover every"):
        parse_scenario_definition_record(incomplete)
    annihilation_record["facts"]["mission"]["objectives"][2]["awards"][0]["armyPoints"].pop()
    with pytest.raises(ScenarioDefinitionError, match="awards must cover every"):
        parse_scenario_definition_record(annihilation_record)


def test_mission_does_not_assume_symmetric_objectives_or_one_deployment_zone(
    annihilation_record: dict[str, Any],
) -> None:
    mission = annihilation_record["facts"]["mission"]
    mission["objectives"][0]["sideIds"] = ["side-a"]
    mission["objectives"][2]["aggregation"] = "cumulative"
    mission["objectives"][2]["awards"] *= 2
    for configuration in annihilation_record["facts"]["configurations"]:
        additional = deepcopy(configuration["geometry"]["elements"][0])
        additional["id"] = "deployment-a-second"
        configuration["geometry"]["elements"].append(additional)
    for size in mission["gameSizes"]:
        size["deployments"][0]["elementIds"].append("deployment-a-second")
    parsed = parse_scenario_definition_record(annihilation_record).mission
    assert parsed is not None
    assert parsed.objectives[0].side_ids == ("side-a",)
    assert len(parsed.game_sizes[0].deployments[0].element_ids) == 2
    assert parsed.objectives[2].maximum_points == 2  # Cumulative awards are capped.


@pytest.fixture
def domination_record() -> dict[str, Any]:
    document = load_curated_document(_CORE_RULES)
    return deepcopy(
        compose_scenario_record(
            next(record for record in document["records"] if record["id"] == "scenario:domination"),
            document,
        )
    )


def test_domination_preserves_each_game_size_and_source_specific_swc(
    domination_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(domination_record).mission
    assert mission is not None
    assert [
        (size.army_points, size.swc, size.minimum_victory_points) for size in mission.game_sizes
    ] == [
        (150, 3, 38),
        (200, 4, 50),
        (250, 5, 63),
        (300, 6, 75),
        (350, 6, 88),
        (400, 8, 100),
    ]
    assert [size.configuration_id for size in mission.game_sizes] == [
        "150-points",
        "200-250-points",
        "200-250-points",
        "300-400-points",
        "300-400-points",
        "300-400-points",
    ]
    for size in mission.game_sizes:
        assert [(d.side_id, d.element_ids) for d in size.deployments] == [
            ("side-a", ("deployment-a",)),
            ("side-b", ("deployment-b",)),
        ]
    issue = mission.source_issues[0]
    assert (issue.army_points, issue.objective_id, issue.game_size_field, issue.status) == (
        (350,),
        None,
        "swc",
        "needs-verification",
    )
    assert "6 SWC" in issue.description and "7 SWC" in issue.description
    assert {(c["sourceId"], c["page"]) for c in domination_record["citations"]} == {
        ("n5-core-v5.3-pdf", 151),
        ("n5-core-v5.3-pdf", 152),
    }


def test_domination_scoring_references_regions_and_consoles_with_explicit_cadence(
    domination_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(domination_record).mission
    assert mission is not None
    regions, consoles = mission.objectives
    assert (
        regions.timing,
        regions.aggregation,
        regions.maximum_points,
        regions.maximum_points_per_round,
    ) == ("end-of-round", "exclusive", 6, 2)
    assert [a.objective_points for a in regions.awards] == [1, 2]
    quadrants = ("quadrant-1", "quadrant-2", "quadrant-3", "quadrant-4")
    assert [a.condition for a in regions.awards] == [
        DominatedRegionComparison(quadrants, "equal", 1),
        DominatedRegionComparison(quadrants, "greater", None),
    ]
    assert all(a.army_points == (150, 200, 250, 300, 350, 400) for a in regions.awards)
    assert (
        consoles.timing,
        consoles.aggregation,
        consoles.maximum_points,
        consoles.maximum_points_per_round,
    ) == ("end-of-game", "cumulative", 4, None)
    assert consoles.awards[0].objective_points == 1
    assert consoles.awards[0].condition == ElementStatusCount(
        ("console-q1", "console-q2", "console-q3", "console-q4"),
        "hacked",
    )
    limit, threshold = mission.end_conditions
    assert (
        limit.rounds,
        threshold.check_at,
        threshold.finish_at,
        threshold.uses_minimum_victory_points,
    ) == (
        3,
        "tactical-phase",
        "end-of-player-turn",
        True,
    )
    assert threshold.description and "below" in threshold.description
    assert "not classified as Null" in threshold.description


def test_domination_retains_control_eligibility_and_console_interaction_rules(
    domination_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(domination_record).mission
    assert mission is not None
    rules = {rule.id: " ".join(rule.paragraphs) for rule in mission.rules}
    assert "more than half" in rules["dominate-quadrants"]
    assert "anything other than a Trooper" in rules["dominate-quadrants"]
    assert "[[skill:shasvastii]]" in rules["dominate-quadrants"]
    assert "[[state:normal|Normal]]" in rules["dominate-quadrants"]
    assert "Shasvastii-Embryo" in rules["dominate-quadrants"]
    assert "same diameter" in rules["consoles"]
    assert mission.skill_ids == ("skill:hack-consoles",)
    skill = next(
        r for r in load_curated_document(_CORE_RULES)["records"] if r["id"] == "skill:hack-consoles"
    )
    assert skill["facts"]["typeIds"] == ["short-skill"] and skill["labelIds"] == ["attack"]
    assert "Silhouette contact" in " ".join(skill["facts"]["requirements"])
    effects = " ".join(skill["facts"]["effects"])
    assert "failed attempt may be repeated" in effects and "most recent player" in effects
    assert "[[skill:hacker]] receives a +3 MOD" in effects and "[[attribute:wip]]" in effects
    for identity in (
        "doctor",
        "engineer",
        "forward-observer",
        "hacker",
        "paramedic",
        "specialist-operative",
        "chain-of-command",
    ):
        assert f"skill:{identity}" in mission.rules[-1].specialist_skill_ids
    assert "cannot use [[skill:peripheral:plural]]" in rules["specialist-troops"]


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("gameSizes", 0, "minimumVictoryPoints"), True, "integer"),
        (("gameSizes", 0, "minimumVictoryPoints"), 0, "integer"),
        (("gameSizes", 0, "minimumVictoryPoints"), 151, "exceeds Army Points"),
        (("objectives", 0, "maximumPointsPerRound"), True, "integer"),
        (("objectives", 0, "maximumPointsPerRound"), 7, "invalid maximumPointsPerRound"),
        (("objectives", 0, "maximumPointsPerRound"), 1, "exceeds"),
        (("objectives", 0, "timing"), "end-of-game", "invalid maximumPointsPerRound"),
        (
            ("objectives", 0, "awards", 0, "condition", "elementIds"),
            ["missing"],
            "incompatible scoring element",
        ),
        (
            ("objectives", 0, "awards", 0, "condition", "elementIds"),
            ["console-q1"],
            "incompatible scoring element",
        ),
        (("objectives", 0, "awards", 0, "condition", "minimum"), 5, "exceeds the number"),
        (("objectives", 0, "awards", 0, "condition", "minimum"), True, "integer"),
        (("objectives", 0, "awards", 0, "condition", "comparison"), "approximately", "one of"),
        (
            ("objectives", 0, "awards", 0, "condition", "elementIds"),
            ["quadrant-1", "quadrant-1"],
            "duplicate",
        ),
        (
            ("objectives", 1, "awards", 0, "condition", "elementIds"),
            ["quadrant-1"],
            "incompatible scoring element",
        ),
        (("objectives", 1, "awards", 0, "condition", "status"), "destroyed", "one of"),
        (("objectives", 1, "aggregation"), "exclusive", "per-element awards require cumulative"),
        (("endConditions", 1, "finishAt"), "immediate", "Tactical Phase/Player Turn"),
        (("sourceIssues", 0, "gameSizeField"), "unimplemented", "one of"),
        (("sourceIssues", 0, "objectiveId"), "dominate-quadrants", "exactly one"),
    ],
)
def test_domination_rejects_invalid_extensions(
    domination_record: dict[str, Any],
    path: tuple[str | int, ...],
    value: Any,
    message: str,
) -> None:
    target = domination_record["facts"]["mission"]
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = value
    with pytest.raises(ScenarioDefinitionError, match=message):
        parse_scenario_definition_record(domination_record)


def test_domination_requires_scoring_elements_in_every_applicable_configuration(
    domination_record: dict[str, Any],
) -> None:
    geometry = domination_record["facts"]["configurations"][1]["geometry"]
    geometry["elements"] = [e for e in geometry["elements"] if e["id"] != "console-q1"]
    with pytest.raises(
        ScenarioDefinitionError, match="scoring element 'console-q1'.*200-250-points"
    ):
        parse_scenario_definition_record(domination_record)


def test_domination_end_condition_requires_every_game_size_threshold(
    domination_record: dict[str, Any],
) -> None:
    del domination_record["facts"]["mission"]["gameSizes"][4]["minimumVictoryPoints"]
    with pytest.raises(ScenarioDefinitionError, match="minimumVictoryPoints for every game size"):
        parse_scenario_definition_record(domination_record)


def test_game_size_source_issue_cannot_excuse_unrelated_scoring_overlap(
    annihilation_record: dict[str, Any],
) -> None:
    issue = annihilation_record["facts"]["mission"]["sourceIssues"][0]
    del issue["objectiveId"]
    issue["gameSizeField"] = "swc"
    with pytest.raises(ScenarioDefinitionError, match="overlapping score ranges for 350"):
        parse_scenario_definition_record(annihilation_record)


@pytest.fixture
def supplies_record() -> dict[str, Any]:
    document = load_curated_document(_CORE_RULES)
    return deepcopy(
        compose_scenario_record(
            next(r for r in document["records"] if r["id"] == "scenario:supplies"), document
        )
    )


def test_supplies_preserves_every_game_size_and_minimum_vp(
    supplies_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(supplies_record).mission
    assert mission is not None
    assert [(s.army_points, s.swc, s.minimum_victory_points) for s in mission.game_sizes] == [
        (150, 3, 38),
        (200, 4, 50),
        (250, 5, 63),
        (300, 6, 75),
        (350, 7, 88),
        (400, 8, 100),
    ]
    assert [s.configuration_id for s in mission.game_sizes] == [
        "150-points",
        "200-250-points",
        "200-250-points",
        "300-400-points",
        "300-400-points",
        "300-400-points",
    ]
    assert mission.end_conditions[0].rounds == 3
    ending = mission.end_conditions[1]
    assert ending.uses_minimum_victory_points
    assert (ending.check_at, ending.finish_at) == ("tactical-phase", "end-of-player-turn")
    assert ending.description and "below" in ending.description
    assert "not classified as Null" in ending.description
    assert {(c["sourceId"], c["page"]) for c in supplies_record["citations"]} == {
        ("n5-core-v5.3-pdf", 153),
        ("n5-core-v5.3-pdf", 154),
    }


def test_supplies_scoring_keeps_per_box_and_both_additional_bonuses(
    supplies_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(supplies_record).mission
    assert mission is not None
    boxes = ("supply-box-left", "supply-box-center", "supply-box-right")
    per_box, more, all_boxes = mission.objectives
    assert [o.maximum_points for o in mission.objectives] == [6, 2, 2]
    assert [o.aggregation for o in mission.objectives] == ["cumulative", "exclusive", "exclusive"]
    assert all(o.timing == "end-of-game" for o in mission.objectives)
    assert all(o.side_ids == ("side-a", "side-b") for o in mission.objectives)
    assert all(
        o.awards[0].army_points == (150, 200, 250, 300, 350, 400) for o in mission.objectives
    )
    assert [o.awards[0].objective_points for o in mission.objectives] == [2, 2, 2]
    assert per_box.awards[0].condition == ElementStatusCount(boxes, "controlled")
    assert more.awards[0].condition == ElementStatusComparison(boxes, "controlled", "greater")
    assert all_boxes.awards[0].condition == ElementStatusComparison(boxes, "controlled", "all")


def test_supplies_pickup_carrying_and_control_rules_preserve_eligibility(
    supplies_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(supplies_record).mission
    assert mission is not None
    rules = {r.id: " ".join(r.paragraphs) for r in mission.rules}
    assert "Deployment in Silhouette contact" in rules["supply-boxes"]
    assert mission.skill_ids == ("skill:pick-up-supply-boxes",)
    skill = next(
        r
        for r in load_curated_document(_CORE_RULES)["records"]
        if r["id"] == "skill:pick-up-supply-boxes"
    )
    assert skill["facts"]["typeIds"] == ["short-skill"] and skill["labelIds"] == ["attack"]
    pickup = " ".join(skill["facts"]["requirements"] + skill["facts"]["effects"])
    assert "not being carried by a Model" in pickup
    assert "any Model classified as Null" in pickup
    assert "an allied Model in [[state:normal|Normal]]" in pickup
    assert "without making a Roll" in pickup
    carrying = rules["carrying-supply-boxes"]
    assert "at most one" in carrying and "Markers cannot" in carrying
    assert "on the table even if its carrier becomes classified as Null" in carrying
    control = rules["controlling-supply-boxes"]
    assert "one of their Models is carrying" in control and "A Marker cannot control" in control
    assert "must not be classified as Null" in control
    assert "any enemy Model" in control
    specialists = rules["specialist-troops"]
    for identity in (
        "doctor",
        "engineer",
        "forward-observer",
        "hacker",
        "paramedic",
        "specialist-operative",
        "chain-of-command",
    ):
        assert f"skill:{identity}" in mission.rules[-1].specialist_skill_ids
    assert "cannot use [[skill:peripheral:plural]]" in specialists


def test_supplies_placement_issue_is_scoped_to_large_table_outer_markers(
    supplies_record: dict[str, Any],
) -> None:
    definition = parse_scenario_definition_record(supplies_record)
    assert definition.mission is not None
    issue = definition.mission.source_issues[0]
    assert issue.army_points == (300, 350, 400)
    assert issue.objective_id is None and issue.game_size_field is None
    assert issue.geometry_element_ids == ("supply-box-left", "supply-box-right")
    assert issue.status == "needs-verification"
    assert "[[distance:8:inch]]" in issue.description
    assert "[[distance:12:inch]]" in issue.description
    geometry = select_scenario_geometry(definition, 350)
    outer = [
        e
        for e in geometry.elements
        if isinstance(e, MarkerElement) and e.id in issue.geometry_element_ids
    ]
    assert [resolve_coordinate(e.x, axis="x", table=geometry.table) for e in outer] == [8, 40]


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("objectives", 1, "awards", 0, "condition", "elementIds"), ["missing"], "scoring element"),
        (
            ("objectives", 1, "awards", 0, "condition", "elementIds"),
            ["deployment-a"],
            "scoring element",
        ),
        (
            ("objectives", 1, "awards", 0, "condition", "elementIds"),
            ["supply-box-left"] * 2,
            "duplicate",
        ),
        (("objectives", 1, "awards", 0, "condition", "comparison"), "equal", "one of"),
        (("objectives", 1, "awards", 0, "condition", "status"), "carried", "one of"),
        (("objectives", 2, "awards", 0, "condition", "minimum"), 2, "unsupported fields"),
        (("sourceIssues", 0, "geometryElementIds"), [], "non-empty"),
        (("sourceIssues", 0, "geometryElementIds"), ["missing"], "unknown references"),
        (("sourceIssues", 0, "geometryElementIds"), ["supply-box-left"] * 2, "duplicate"),
        (("sourceIssues", 0, "objectiveId"), "controlled-boxes", "exactly one"),
    ],
)
def test_supplies_rejects_invalid_marker_conditions_and_issue_references(
    supplies_record: dict[str, Any],
    path: tuple[str | int, ...],
    value: Any,
    message: str,
) -> None:
    target = supplies_record["facts"]["mission"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ScenarioDefinitionError, match=message):
        parse_scenario_definition_record(supplies_record)


def test_marker_comparison_references_must_resolve_in_every_covered_configuration(
    supplies_record: dict[str, Any],
) -> None:
    # The per-box objective covers 150 Points here, leaving the comparison's wider
    # scope responsible for checking the missing marker in the middle configuration.
    supplies_record["facts"]["mission"]["objectives"][0]["awards"][0]["armyPoints"] = [150]
    configuration = supplies_record["facts"]["configurations"][1]
    geometry = configuration["geometry"]
    geometry["elements"] = [e for e in geometry["elements"] if e["id"] != "supply-box-center"]
    # Keep every objective covering all sizes without referencing the missing marker
    # in the per-box awards, so the scalar comparison itself must reject this record.
    first = supplies_record["facts"]["mission"]["objectives"][0]
    other = deepcopy(first["awards"][0])
    other["armyPoints"] = [200, 250, 300, 350, 400]
    other["condition"]["elementIds"] = ["supply-box-left", "supply-box-right"]
    first["awards"].append(other)
    with pytest.raises(
        ScenarioDefinitionError, match="scoring element 'supply-box-center'.*200-250-points"
    ):
        parse_scenario_definition_record(supplies_record)


def test_geometry_issues_require_references_in_every_applicable_configuration(
    annihilation_record: dict[str, Any],
) -> None:
    issue = {
        "id": "geometry-note",
        "armyPoints": [150, 200],
        "geometryElementIds": ["first-only"],
        "status": "needs-verification",
        "description": "An explicitly scoped geometry discrepancy.",
    }
    annihilation_record["facts"]["mission"]["sourceIssues"].append(issue)
    geometry = annihilation_record["facts"]["configurations"][0]["geometry"]
    extra = deepcopy(geometry["elements"][0])
    extra["id"] = "first-only"
    geometry["elements"].append(extra)
    with pytest.raises(
        ScenarioDefinitionError, match="geometryElementIds in 200-250-points.*unknown"
    ):
        parse_scenario_definition_record(annihilation_record)


def test_geometry_issue_does_not_excuse_an_unrelated_exclusive_scoring_overlap(
    annihilation_record: dict[str, Any],
) -> None:
    issue = annihilation_record["facts"]["mission"]["sourceIssues"][0]
    del issue["objectiveId"]
    issue["geometryElementIds"] = ["deployment-a"]
    with pytest.raises(ScenarioDefinitionError, match="overlapping score ranges for 350"):
        parse_scenario_definition_record(annihilation_record)


@pytest.fixture
def firefight_record() -> dict[str, Any]:
    document = load_curated_document(_CORE_RULES)
    return deepcopy(
        compose_scenario_record(
            next(r for r in document["records"] if r["id"] == "scenario:firefight"), document
        )
    )


def test_firefight_preserves_each_game_size_and_all_null_end_condition(
    firefight_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(firefight_record).mission
    assert mission is not None
    assert [(s.army_points, s.swc, s.configuration_id) for s in mission.game_sizes] == [
        (150, 3, "150-points"),
        (200, 4, "200-250-points"),
        (250, 5, "200-250-points"),
        (300, 6, "300-400-points"),
        (350, 7, "300-400-points"),
        (400, 8, "300-400-points"),
    ]
    assert all(s.minimum_victory_points is None for s in mission.game_sizes)
    assert mission.end_conditions[0].rounds == 3
    ending = mission.end_conditions[1]
    assert not ending.uses_minimum_victory_points
    assert (ending.id, ending.check_at, ending.finish_at) == (
        "all-troopers-null",
        "tactical-phase",
        "end-of-player-turn",
    )
    assert ending.description and "all Troopers" in ending.description
    assert "classified as Null" in ending.description
    assert not mission.source_issues
    assert {(c["sourceId"], c["page"]) for c in firefight_record["citations"]} == {
        ("n5-core-v5.3-pdf", 155),
        ("n5-core-v5.3-pdf", 156),
    }


def test_firefight_comparative_objectives_preserve_the_four_awards(
    firefight_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(firefight_record).mission
    assert mission is not None
    assert [(o.id, o.maximum_points, o.awards[0].condition) for o in mission.objectives] == [
        ("surviving-specialists", 2, MetricComparison("surviving-specialist-troops", "greater")),
        ("killed-specialists", 1, MetricComparison("enemy-specialist-troops-killed", "greater")),
        ("killed-lieutenants", 3, MetricComparison("enemy-lieutenants-killed", "greater")),
        ("killed-army-points", 4, MetricComparison("enemy-army-points-killed", "greater")),
    ]
    assert all(
        o.timing == "end-of-game" and o.aggregation == "exclusive" for o in mission.objectives
    )
    assert all(o.maximum_points_per_round is None for o in mission.objectives)
    assert all(o.side_ids == ("side-a", "side-b") for o in mission.objectives)
    assert [o.awards[0].objective_points for o in mission.objectives] == [2, 1, 3, 4]
    assert all(
        o.awards[0].army_points == (150, 200, 250, 300, 350, 400) for o in mission.objectives
    )
    assert "[[skill:lieutenant:plural]]" in mission.objectives[2].name


def test_firefight_retains_tactical_link_landing_and_specialist_rules(
    firefight_record: dict[str, Any],
) -> None:
    mission = parse_scenario_definition_record(firefight_record).mission
    assert mission is not None
    rules = {r.id: " ".join(r.paragraphs) for r in mission.rules}
    assert "[[state:dead]]" in rules["killing"]
    assert "never deployed" in rules["killing"]
    link = rules["reinforced-tactical-link"]
    assert "identity of the [[skill:lieutenant]] is always Open Information" in link
    assert "identify which Marker" in link
    assert "beginning of the first Game Round" in link
    assert "start of the Tactical Phase" in link
    assert "not deployed or is classified as Null" in link
    assert "without spending an Order" in link
    assert "replacement [[skill:lieutenant]] must be a Model or Marker on the table" in link
    assert "[[state:isolated]]" not in link  # Do not invent an additional replacement trigger.
    landing = rules["designated-landing-area"]
    assert "whole game table" in landing
    assert "[[skill:combat-jump]] may apply a +3 MOD" in landing
    assert "[[attribute:ph]] Roll" in landing
    assert "cumulative with MODs provided by other rules" in landing
    assert "Special Skill carrying the Airborne Deployment (AD) Label" in landing
    assert "inside the enemy Deployment Zone" in landing
    specialists = rules["specialist-troops"]
    for identity in (
        "doctor",
        "engineer",
        "forward-observer",
        "hacker",
        "paramedic",
        "specialist-operative",
        "chain-of-command",
    ):
        assert f"skill:{identity}" in mission.rules[-1].specialist_skill_ids
    assert "cannot use [[skill:peripheral:plural]]" in specialists


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("metric", "unknown-statistic", "one of"),
        ("metric", True, "one of"),
        ("comparison", "equal", "one of"),
        ("comparison", "greater-or-equal", "one of"),
        ("comparison", True, "one of"),
        ("minimum", 1, "unsupported fields"),
        ("elementIds", ["deployment-a"], "unsupported fields"),
    ],
)
def test_firefight_metric_comparison_rejects_unsupported_semantics(
    firefight_record: dict[str, Any],
    field: str,
    value: Any,
    message: str,
) -> None:
    condition = firefight_record["facts"]["mission"]["objectives"][0]["awards"][0]["condition"]
    condition[field] = value
    with pytest.raises(ScenarioDefinitionError, match=message):
        parse_scenario_definition_record(firefight_record)


def test_all_core_scenarios_now_have_validated_mission_reference_facts() -> None:
    document = load_curated_document(_CORE_RULES)
    definitions = [
        parse_scenario_definition_record(r, definitions=document)
        for r in document["records"]
        if r["kind"] == "scenario"
    ]
    assert {d.id for d in definitions} == {
        "scenario:annihilation",
        "scenario:domination",
        "scenario:supplies",
        "scenario:firefight",
    }
    for definition in definitions:
        assert definition.mission is not None
        assert [s.army_points for s in definition.mission.game_sizes] == [
            150,
            200,
            250,
            300,
            350,
            400,
        ]
