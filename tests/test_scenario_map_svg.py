from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest

from infinity_db.scenario_geometry import parse_scenario_geometry
from infinity_db.scenario_map_svg import render_scenario_map_svg


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


_CORE_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "scenario_geometry" / "core-v1.json"
)
_CORE_CASES: list[dict[str, Any]] = json.loads(
    _CORE_FIXTURE_PATH.read_text(encoding="utf-8")
)["cases"]


@pytest.mark.parametrize("case", _CORE_CASES, ids=lambda case: case["id"])
def test_render_core_scenario_geometry_fixtures_are_deterministic_and_well_formed(
    case: dict[str, Any],
) -> None:
    geometry = parse_scenario_geometry(case["geometry"])

    first = render_scenario_map_svg(geometry)
    second = render_scenario_map_svg(geometry)

    assert first == second
    root = ElementTree.fromstring(first)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["viewBox"] == f"0 0 {geometry.table.width:g} {geometry.table.height:g}"
