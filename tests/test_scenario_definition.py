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
    MarkerElement,
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
