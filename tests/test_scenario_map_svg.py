from __future__ import annotations

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
                    "x": {"anchor": "center", "offset": -6},
                    "y": {"anchor": "center"},
                    "radius": 0.75,
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
    assert '<circle id="console" class="objective" cx="18" cy="16" r="0.75"/>' in first
    assert "Console &amp; objective</text>" in first
    assert first.endswith("</svg>\n")


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
