from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from infinity_db.scenario_geometry import (
    SCENARIO_GEOMETRY_FORMAT,
    SCENARIO_GEOMETRY_VERSION,
    AnchorCoordinate,
    AreaSizeAnnotation,
    DimensionAnnotation,
    LabelElement,
    LineElement,
    MarkerElement,
    PointEdgeDistanceAnnotation,
    RectangleElement,
    ScenarioElement,
    ScenarioGeometry,
    ScenarioGeometryError,
    marker_diameter_mm,
    parse_scenario_geometry,
    resolve_coordinate,
)


def _document() -> dict[str, object]:
    return {
        "format": SCENARIO_GEOMETRY_FORMAT,
        "formatVersion": SCENARIO_GEOMETRY_VERSION,
        "title": "Core scenario geometry test",
        "table": {"width": 48, "height": 48, "unit": "in"},
        "elements": [
            {
                "id": "deployment-a",
                "kind": "rectangle",
                "style": "deployment-a",
                "x1": 0,
                "y1": 0,
                "x2": {"anchor": "right"},
                "y2": 12,
            },
            {
                "id": "deployment-b",
                "kind": "rectangle",
                "style": "deployment-b",
                "x1": 0,
                "y1": {"anchor": "bottom", "offset": -12},
                "x2": {"anchor": "right"},
                "y2": {"anchor": "bottom"},
            },
            {
                "id": "center-line",
                "kind": "line",
                "style": "guide",
                "x1": 0,
                "y1": {"anchor": "center"},
                "x2": {"anchor": "right"},
                "y2": {"anchor": "center"},
            },
            {
                "id": "objective-center",
                "kind": "marker",
                "style": "objective",
                "markerType": "console",
                "x": {"anchor": "center"},
                "y": {"anchor": "center"},
            },
            {
                "id": "map-label",
                "kind": "label",
                "style": "label",
                "x": {"anchor": "center"},
                "y": {"anchor": "center", "offset": -2},
                "text": "Objective & center",
            },
        ],
    }


def test_parse_scenario_geometry_resolves_absolute_and_table_relative_coordinates() -> None:
    geometry = parse_scenario_geometry(_document())

    assert geometry.title == "Core scenario geometry test"
    assert geometry.table.width == 48
    assert geometry.table.height == 48
    assert len(geometry.elements) == 5

    first = geometry.elements[0]
    assert isinstance(first, RectangleElement)
    assert first.x2 == AnchorCoordinate(anchor="right", offset=0)
    assert resolve_coordinate(first.x2, axis="x", table=geometry.table) == 48

    marker = geometry.elements[3]
    assert isinstance(marker, MarkerElement)
    assert marker.marker_type == "console"
    assert resolve_coordinate(marker.x, axis="x", table=geometry.table) == 24
    assert resolve_coordinate(marker.y, axis="y", table=geometry.table) == 24

    label = geometry.elements[4]
    assert isinstance(label, LabelElement)
    assert label.align == "middle"



def test_parse_scenario_geometry_validates_derived_annotations() -> None:
    document = _document()
    document["annotations"] = [
        {
            "id": "deployment-depth",
            "kind": "dimension",
            "target": "deployment-a",
            "axis": "y",
            "side": "start",
        },
        {
            "id": "deployment-size",
            "kind": "area-size",
            "target": "deployment-a",
        },
    ]

    geometry = parse_scenario_geometry(document)

    assert geometry.annotations == (
        DimensionAnnotation(
            id="deployment-depth",
            target="deployment-a",
            axis="y",
            side="start",
            offset=0.75,
        ),
        AreaSizeAnnotation(id="deployment-size", target="deployment-a"),
    )


def test_parse_scenario_geometry_validates_point_to_edge_distance_annotation() -> None:
    document = _document()
    document["annotations"] = [
        {
            "id": "objective-left-offset",
            "kind": "point-edge-distance",
            "target": "objective-center",
            "edge": "left",
            "offset": -1.5,
        }
    ]

    geometry = parse_scenario_geometry(document)

    assert geometry.annotations == (
        PointEdgeDistanceAnnotation(
            id="objective-left-offset",
            target="objective-center",
            edge="left",
            offset=-1.5,
        ),
    )


def test_parse_scenario_geometry_rejects_point_edge_annotation_targeting_rectangle() -> None:
    document = _document()
    document["annotations"] = [
        {
            "id": "deployment-left-offset",
            "kind": "point-edge-distance",
            "target": "deployment-a",
            "edge": "left",
        }
    ]

    with pytest.raises(ScenarioGeometryError, match="must reference a marker"):
        parse_scenario_geometry(document)


def test_parse_scenario_geometry_rejects_point_edge_annotation_outside_table() -> None:
    document = _document()
    document["annotations"] = [
        {
            "id": "objective-left-offset",
            "kind": "point-edge-distance",
            "target": "objective-center",
            "edge": "left",
            "offset": -25,
        }
    ]

    with pytest.raises(ScenarioGeometryError, match="outside the table"):
        parse_scenario_geometry(document)


def test_parse_scenario_geometry_rejects_annotation_targeting_non_rectangle() -> None:
    document = _document()
    document["annotations"] = [
        {
            "id": "center-measurement",
            "kind": "dimension",
            "target": "center-line",
            "axis": "x",
            "side": "start",
        }
    ]

    with pytest.raises(ScenarioGeometryError, match="must reference a rectangle"):
        parse_scenario_geometry(document)


def test_parse_scenario_geometry_rejects_duplicate_annotation_identity() -> None:
    document = _document()
    document["annotations"] = [
        {
            "id": "deployment-a",
            "kind": "area-size",
            "target": "deployment-a",
        }
    ]

    with pytest.raises(ScenarioGeometryError, match="duplicate id.*deployment-a"):
        parse_scenario_geometry(document)

def test_parse_scenario_geometry_rejects_unknown_format_version() -> None:
    document = _document()
    document["formatVersion"] = 2

    with pytest.raises(ScenarioGeometryError, match="formatVersion must be 1"):
        parse_scenario_geometry(document)


def test_parse_scenario_geometry_rejects_axis_incompatible_anchor() -> None:
    document = _document()
    elements = document["elements"]
    assert isinstance(elements, list)
    rectangle = elements[0]
    assert isinstance(rectangle, dict)
    rectangle["x2"] = {"anchor": "bottom"}

    with pytest.raises(ScenarioGeometryError, match="for the x-axis"):
        parse_scenario_geometry(document)


def test_parse_scenario_geometry_rejects_resolved_out_of_bounds_coordinates() -> None:
    document = _document()
    elements = document["elements"]
    assert isinstance(elements, list)
    rectangle = elements[0]
    assert isinstance(rectangle, dict)
    rectangle["x2"] = {"anchor": "right", "offset": 1}

    with pytest.raises(ScenarioGeometryError, match="outside table x-range"):
        parse_scenario_geometry(document)


def test_parse_scenario_geometry_rejects_presentation_radius_on_semantic_marker() -> None:
    document = _document()
    elements = document["elements"]
    assert isinstance(elements, list)
    marker = elements[3]
    assert isinstance(marker, dict)
    marker["radius"] = 0.75

    with pytest.raises(ScenarioGeometryError, match="unsupported field.*radius"):
        parse_scenario_geometry(document)


def test_parse_scenario_geometry_rejects_duplicate_element_ids() -> None:
    document = _document()
    elements = document["elements"]
    assert isinstance(elements, list)
    duplicate = copy.deepcopy(elements[0])
    assert isinstance(duplicate, dict)
    duplicate["kind"] = "line"
    duplicate["style"] = "guide"
    elements.append(duplicate)

    with pytest.raises(ScenarioGeometryError, match="duplicate id.*deployment-a"):
        parse_scenario_geometry(document)


_CORE_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "scenario_geometry" / "core-v1.json"
)
_CORE_FIXTURE = json.loads(_CORE_FIXTURE_PATH.read_text(encoding="utf-8"))
_CORE_CASES: list[dict[str, Any]] = _CORE_FIXTURE["cases"]


def _element_by_id(geometry: ScenarioGeometry, element_id: str) -> ScenarioElement:
    return next(element for element in geometry.elements if element.id == element_id)


def _resolved_rectangle(
    rectangle: RectangleElement, geometry: ScenarioGeometry
) -> tuple[float, float, float, float]:
    table = geometry.table
    return (
        resolve_coordinate(rectangle.x1, axis="x", table=table),
        resolve_coordinate(rectangle.y1, axis="y", table=table),
        resolve_coordinate(rectangle.x2, axis="x", table=table),
        resolve_coordinate(rectangle.y2, axis="y", table=table),
    )


def test_core_scenario_geometry_fixture_inventory_covers_all_core_configurations() -> None:
    assert _CORE_FIXTURE["format"] == "InfinityDB core scenario geometry fixtures"
    assert _CORE_FIXTURE["formatVersion"] == 1
    diameters = _CORE_FIXTURE["source"]["markerDiameters"]["itsTokenTable"]
    assert diameters["consoleMm"] == 40
    assert diameters["supplyBoxMm"] == 25
    assert marker_diameter_mm("console") == 40
    assert marker_diameter_mm("supply-box") == 25
    assert marker_diameter_mm("future-marker") is None
    assert len(_CORE_CASES) == 6
    assert {case["scenario"] for case in _CORE_CASES} == {
        "annihilation",
        "firefight",
    }

    expected_groups = {(150,), (200, 250), (300, 350, 400)}
    for scenario in {"annihilation", "firefight"}:
        groups = {
            tuple(case["armyPoints"])
            for case in _CORE_CASES
            if case["scenario"] == scenario
        }
        assert groups == expected_groups


@pytest.mark.parametrize("case", _CORE_CASES, ids=lambda case: case["id"])
def test_core_scenario_geometry_v1_represents_current_core_maps(
    case: dict[str, Any],
) -> None:
    geometry = parse_scenario_geometry(case["geometry"])
    scenario = case["scenario"]
    width = geometry.table.width
    height = geometry.table.height
    deployment_depth = 8 if (width, height) == (24, 32) else 12

    assert (width, height) in {(24, 32), (32, 48), (48, 48)}
    assert geometry.title.casefold() == scenario

    deployment_a = _element_by_id(geometry, "deployment-a")
    deployment_b = _element_by_id(geometry, "deployment-b")
    center_line = _element_by_id(geometry, "center-line")
    assert isinstance(deployment_a, RectangleElement)
    assert isinstance(deployment_b, RectangleElement)
    assert isinstance(center_line, LineElement)
    assert _resolved_rectangle(deployment_a, geometry) == (0, 0, width, deployment_depth)
    assert _resolved_rectangle(deployment_b, geometry) == (
        0,
        height - deployment_depth,
        width,
        height,
    )
    assert (
        resolve_coordinate(center_line.y1, axis="y", table=geometry.table) == height / 2
    )
    assert (
        resolve_coordinate(center_line.y2, axis="y", table=geometry.table) == height / 2
    )

    markers = [
        element for element in geometry.elements if isinstance(element, MarkerElement)
    ]
    assert markers == []
