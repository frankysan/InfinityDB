from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.curated import load_curated_document
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
from infinity_db.scenario_mission import NumericRangeCondition, ProseCondition

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
        next(record for record in document["records"] if record["id"] == "scenario:annihilation")
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
