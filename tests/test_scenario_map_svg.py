from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.scenario_definition import scenario_definition_from_curated_document
from infinity_db.scenario_geometry import parse_scenario_geometry
from infinity_db.scenario_map_svg import ScenarioMapRenderError, render_scenario_map_svg


def test_render_scenario_map_svg_is_deterministic_and_uses_inch_viewbox() -> None:
    geometry = parse_scenario_geometry(
        {
            "format": "InfinityDB scenario geometry",
            "formatVersion": 1,
            "title": "Domination <test>",
            "table": {"width": 48, "height": 32, "unit": "in"},
            "elements": [
                {
                    "id": "deployment-a",
                    "kind": "rectangle",
                    "style": "deployment-a",
                    "x1": 0,
                    "y1": 0,
                    "x2": {"anchor": "right"},
                    "y2": 8,
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
                    "id": "console",
                    "kind": "marker",
                    "style": "objective",
                    "markerType": "console",
                    "x": {"anchor": "center", "offset": -6},
                    "y": {"anchor": "center"},
                },
                {
                    "id": "console-label",
                    "kind": "label",
                    "style": "label",
                    "x": {"anchor": "center", "offset": -6},
                    "y": {"anchor": "center", "offset": -2},
                    "text": "Console & objective",
                    "align": "middle",
                },
            ],
        }
    )

    first = render_scenario_map_svg(geometry)
    second = render_scenario_map_svg(geometry)

    assert first == second
    assert first.startswith('<?xml version="1.0" encoding="UTF-8"?>\n')
    assert 'viewBox="0 0 48 32"' in first
    assert 'data-unit="in"' in first
    assert "<title id=\"map-title\">Domination &lt;test&gt;</title>" in first
    assert (
        '<rect id="deployment-a" class="deployment-a" x="0" y="0" '
        'width="48" height="8"/>'
    ) in first
    assert (
        '<line id="center-line" class="guide" x1="0" y1="16" x2="48" y2="16"/>'
    ) in first
    assert (
        '<circle id="console" class="objective" data-marker-type="console" '
        'data-diameter-mm="40" cx="18" cy="16" r="0.787402"/>'
    ) in first
    assert "Console &amp; objective</text>" in first
    assert first.endswith("</svg>\n")


def test_render_scenario_map_svg_uses_canonical_size_for_supply_boxes() -> None:
    geometry = parse_scenario_geometry(
        {
            "format": "InfinityDB scenario geometry",
            "formatVersion": 1,
            "title": "Supply Box reference size",
            "table": {"width": 24, "height": 32, "unit": "in"},
            "elements": [
                {
                    "id": "supply-box",
                    "kind": "marker",
                    "style": "objective",
                    "markerType": "supply-box",
                    "x": {"anchor": "center"},
                    "y": {"anchor": "center"},
                }
            ],
        }
    )

    svg = render_scenario_map_svg(geometry)

    assert (
        '<circle id="supply-box" class="objective" data-marker-type="supply-box" '
        'data-diameter-mm="25" cx="12" cy="16" r="0.492126"/>'
    ) in svg


@pytest.mark.parametrize(
    ("width", "height"),
    [(24, 32), (32, 48), (48, 48)],
)
def test_render_scenario_map_svg_supports_core_table_size_presets(
    width: int, height: int
) -> None:
    geometry = parse_scenario_geometry(
        {
            "format": "InfinityDB scenario geometry",
            "formatVersion": 1,
            "title": "Core table size",
            "table": {"width": width, "height": height, "unit": "in"},
            "elements": [],
        }
    )

    svg = render_scenario_map_svg(geometry)

    assert f'viewBox="0 0 {width} {height}"' in svg


_CORE_RULES = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"


@pytest.mark.parametrize(
    "scenario_id",
    [
        "scenario:annihilation",
        "scenario:domination",
        "scenario:supplies",
        "scenario:firefight",
    ],
)
def test_render_maintained_core_scenario_maps_are_deterministic_and_well_formed(
    scenario_id: str,
) -> None:
    document = load_curated_document(_CORE_RULES)
    definition = scenario_definition_from_curated_document(document, scenario_id)

    for configuration in definition.configurations:
        geometry = configuration.geometry
        first = render_scenario_map_svg(geometry)
        second = render_scenario_map_svg(geometry)

        assert first == second
        root = ElementTree.fromstring(first)
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        assert root.attrib["viewBox"] == (
            f"0 0 {geometry.table.width:g} {geometry.table.height:g}"
        )


def test_render_scenario_map_svg_projects_derived_dimensions_and_area_size() -> None:
    geometry = parse_scenario_geometry(
        {
            "format": "InfinityDB scenario geometry",
            "formatVersion": 1,
            "title": "Measured region",
            "table": {"width": 24, "height": 32, "unit": "in"},
            "elements": [
                {
                    "id": "deployment-a",
                    "kind": "rectangle",
                    "style": "deployment-a",
                    "x1": 0,
                    "y1": 0,
                    "x2": {"anchor": "right"},
                    "y2": 8,
                }
            ],
            "annotations": [
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
            ],
        }
    )

    svg = render_scenario_map_svg(geometry)

    assert (
        '<g id="deployment-depth" class="measurement" data-target="deployment-a" '
        'data-axis="y">'
    ) in svg
    assert '>8″</text></g>' in svg
    assert (
        '<text id="deployment-size" class="area-size" data-target="deployment-a" '
        'x="12" y="6.56" text-anchor="middle">24″ × 8″</text>'
    ) in svg


def test_render_scenario_map_svg_projects_point_to_edge_distance() -> None:
    geometry = parse_scenario_geometry(
        {
            "format": "InfinityDB scenario geometry",
            "formatVersion": 1,
            "title": "Measured point",
            "table": {"width": 24, "height": 32, "unit": "in"},
            "elements": [
                {
                    "id": "supply-box-left",
                    "kind": "marker",
                    "style": "objective",
                    "markerType": "supply-box",
                    "x": 8,
                    "y": {"anchor": "center"},
                }
            ],
            "annotations": [
                {
                    "id": "supply-box-left-offset",
                    "kind": "point-edge-distance",
                    "target": "supply-box-left",
                    "edge": "left",
                    "offset": -1.5,
                }
            ],
        }
    )

    svg = render_scenario_map_svg(geometry)

    assert (
        '<g id="supply-box-left-offset" class="measurement" '
        'data-target="supply-box-left" data-edge="left" data-axis="x">'
    ) in svg
    assert '<line x1="0" y1="14.5" x2="8" y2="14.5"/>' in svg
    assert '>8″</text></g>' in svg


def test_render_scenario_map_svg_fails_closed_for_unknown_style() -> None:
    geometry = parse_scenario_geometry(
        {
            "format": "InfinityDB scenario geometry",
            "formatVersion": 1,
            "title": "Future style",
            "table": {"width": 24, "height": 32, "unit": "in"},
            "elements": [
                {
                    "id": "hazard",
                    "kind": "rectangle",
                    "style": "future-hazard",
                    "x1": 4,
                    "y1": 4,
                    "x2": 20,
                    "y2": 28,
                }
            ],
        }
    )

    with pytest.raises(ScenarioMapRenderError, match="does not support element style"):
        render_scenario_map_svg(geometry)


def test_render_scenario_map_svg_fails_closed_for_unknown_marker_type() -> None:
    geometry = parse_scenario_geometry(
        {
            "format": "InfinityDB scenario geometry",
            "formatVersion": 1,
            "title": "Future marker",
            "table": {"width": 24, "height": 32, "unit": "in"},
            "elements": [
                {
                    "id": "future-objective",
                    "kind": "marker",
                    "style": "objective",
                    "markerType": "future-objective",
                    "x": {"anchor": "center"},
                    "y": {"anchor": "center"},
                }
            ],
        }
    )

    with pytest.raises(ScenarioMapRenderError, match="no canonical marker metadata"):
        render_scenario_map_svg(geometry)
