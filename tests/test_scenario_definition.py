from __future__ import annotations

from pathlib import Path

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
