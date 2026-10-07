"""Deterministic SVG projection for validated scenario geometry."""

from __future__ import annotations

from html import escape
from typing import Literal

from .scenario_geometry import (
    Coordinate,
    LineElement,
    MarkerElement,
    RectangleElement,
    ScenarioElement,
    ScenarioGeometry,
    marker_diameter_mm,
    resolve_coordinate,
)

_MM_PER_INCH = 25.4
_DEFAULT_MARKER_RADIUS_IN = 0.35

_STYLE_CSS = """\
.table{fill:#fff;stroke:#111;stroke-width:.12}
.deployment-a{fill:#dbeafe;fill-opacity:.72;stroke:#2563eb;stroke-width:.09}
.deployment-b{fill:#fee2e2;fill-opacity:.72;stroke:#dc2626;stroke-width:.09}
.scoring{fill:#e5e7eb;fill-opacity:.46;stroke:#6b7280;stroke-width:.07}
.objective{fill:#fff;stroke:#111;stroke-width:.1}
.guide{fill:none;stroke:#6b7280;stroke-width:.06;stroke-dasharray:.35 .25}
.measurement{fill:none;stroke:#111;stroke-width:.05}
.label{fill:#111;font-family:sans-serif;font-size:1.15px;font-weight:600}
"""


def _number(value: float) -> str:
    if abs(value) < 0.0000005:
        return "0"
    rendered = f"{value:.6f}".rstrip("0").rstrip(".")
    return rendered


def _resolved(
    geometry: ScenarioGeometry, value: Coordinate, axis: Literal["x", "y"]
) -> float:
    return resolve_coordinate(value, axis=axis, table=geometry.table)


def _render_element(geometry: ScenarioGeometry, element: ScenarioElement) -> str:
    element_id = escape(element.id, quote=True)
    style = escape(element.style, quote=True)

    if isinstance(element, RectangleElement):
        x1 = _resolved(geometry, element.x1, "x")
        y1 = _resolved(geometry, element.y1, "y")
        x2 = _resolved(geometry, element.x2, "x")
        y2 = _resolved(geometry, element.y2, "y")
        return (
            f'<rect id="{element_id}" class="{style}" x="{_number(x1)}" y="{_number(y1)}" '
            f'width="{_number(x2 - x1)}" height="{_number(y2 - y1)}"/>'
        )

    if isinstance(element, LineElement):
        x1 = _resolved(geometry, element.x1, "x")
        y1 = _resolved(geometry, element.y1, "y")
        x2 = _resolved(geometry, element.x2, "x")
        y2 = _resolved(geometry, element.y2, "y")
        return (
            f'<line id="{element_id}" class="{style}" x1="{_number(x1)}" y1="{_number(y1)}" '
            f'x2="{_number(x2)}" y2="{_number(y2)}"/>'
        )

    if isinstance(element, MarkerElement):
        x = _resolved(geometry, element.x, "x")
        y = _resolved(geometry, element.y, "y")
        marker_type = escape(element.marker_type, quote=True)
        diameter_mm = marker_diameter_mm(element.marker_type)
        if diameter_mm is None:
            radius = _DEFAULT_MARKER_RADIUS_IN
            diameter = ""
        else:
            radius = diameter_mm / _MM_PER_INCH / 2.0
            diameter = f' data-diameter-mm="{_number(diameter_mm)}"'
        return (
            f'<circle id="{element_id}" class="{style}" data-marker-type="{marker_type}"'
            f'{diameter} cx="{_number(x)}" cy="{_number(y)}" r="{_number(radius)}"/>'
        )

    x = _resolved(geometry, element.x, "x")
    y = _resolved(geometry, element.y, "y")
    return (
        f'<text id="{element_id}" class="{style}" x="{_number(x)}" y="{_number(y)}" '
        f'text-anchor="{element.align}">{escape(element.text)}</text>'
    )


def render_scenario_map_svg(geometry: ScenarioGeometry) -> str:
    """Render deterministic standalone SVG bytes from validated geometry."""

    width = _number(geometry.table.width)
    height = _number(geometry.table.height)
    title = escape(geometry.title)
    elements = "\n".join(_render_element(geometry, element) for element in geometry.elements)
    if elements:
        elements += "\n"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="map-title" data-unit="in">\n'
        f'<title id="map-title">{title}</title>\n'
        f'<style>{_STYLE_CSS}</style>\n'
        f'<rect class="table" x="0" y="0" width="{width}" height="{height}"/>\n'
        f"{elements}"
        '</svg>\n'
    )
