"""Deterministic SVG projection for validated scenario geometry."""

from __future__ import annotations

from html import escape
from typing import Literal

from .scenario_geometry import (
    AreaSizeAnnotation,
    Coordinate,
    LineElement,
    MarkerElement,
    PointEdgeDistanceAnnotation,
    RectangleElement,
    ScenarioAnnotation,
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
.dimension-label,.area-size{fill:#111;font-family:sans-serif;font-size:.82px;font-weight:600;
paint-order:stroke;stroke:#fff;stroke-width:.045;stroke-linejoin:round}
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


def _rectangle_bounds(
    geometry: ScenarioGeometry, rectangle: RectangleElement
) -> tuple[float, float, float, float]:
    return (
        _resolved(geometry, rectangle.x1, "x"),
        _resolved(geometry, rectangle.y1, "y"),
        _resolved(geometry, rectangle.x2, "x"),
        _resolved(geometry, rectangle.y2, "y"),
    )


def _measurement_text(value: float) -> str:
    return f"{_number(value)}″"


def _render_annotation(
    geometry: ScenarioGeometry,
    annotation: ScenarioAnnotation,
    rectangles: dict[str, RectangleElement],
    markers: dict[str, MarkerElement],
) -> str:
    annotation_id = escape(annotation.id, quote=True)
    target_id = escape(annotation.target, quote=True)

    if isinstance(annotation, PointEdgeDistanceAnnotation):
        target = markers[annotation.target]
        x = _resolved(geometry, target.x, "x")
        y = _resolved(geometry, target.y, "y")
        tick = 0.25
        edge = annotation.edge
        if edge in {"left", "right"}:
            edge_x = 0.0 if edge == "left" else geometry.table.width
            line_y = y + annotation.offset
            x1, x2 = sorted((x, edge_x))
            label_y = line_y - 0.22 if annotation.offset <= 0 else line_y + 0.72
            return (
                f'<g id="{annotation_id}" class="measurement" data-target="{target_id}" '
                f'data-edge="{edge}" data-axis="x">'
                f'<line x1="{_number(x1)}" y1="{_number(line_y)}" '
                f'x2="{_number(x2)}" y2="{_number(line_y)}"/>'
                f'<line x1="{_number(x1)}" y1="{_number(line_y - tick)}" '
                f'x2="{_number(x1)}" y2="{_number(line_y + tick)}"/>'
                f'<line x1="{_number(x2)}" y1="{_number(line_y - tick)}" '
                f'x2="{_number(x2)}" y2="{_number(line_y + tick)}"/>'
                f'<text class="dimension-label" x="{_number((x1 + x2) / 2.0)}" '
                f'y="{_number(label_y)}" text-anchor="middle">'
                f'{_measurement_text(abs(x - edge_x))}</text></g>'
            )

        edge_y = 0.0 if edge == "top" else geometry.table.height
        line_x = x + annotation.offset
        y1, y2 = sorted((y, edge_y))
        label_dy = 0.3 if annotation.offset <= 0 else -0.3
        mid_y = (y1 + y2) / 2.0
        return (
            f'<g id="{annotation_id}" class="measurement" data-target="{target_id}" '
            f'data-edge="{edge}" data-axis="y">'
            f'<line x1="{_number(line_x)}" y1="{_number(y1)}" '
            f'x2="{_number(line_x)}" y2="{_number(y2)}"/>'
            f'<line x1="{_number(line_x - tick)}" y1="{_number(y1)}" '
            f'x2="{_number(line_x + tick)}" y2="{_number(y1)}"/>'
            f'<line x1="{_number(line_x - tick)}" y1="{_number(y2)}" '
            f'x2="{_number(line_x + tick)}" y2="{_number(y2)}"/>'
            f'<text class="dimension-label" x="{_number(line_x)}" y="{_number(mid_y)}" '
            f'text-anchor="middle" transform="rotate(-90 {_number(line_x)} {_number(mid_y)})" '
            f'dy="{_number(label_dy)}">{_measurement_text(abs(y - edge_y))}</text></g>'
        )

    target = rectangles[annotation.target]
    x1, y1, x2, y2 = _rectangle_bounds(geometry, target)

    if isinstance(annotation, AreaSizeAnnotation):
        x = (x1 + x2) / 2.0
        y = y1 + (y2 - y1) * 0.82
        text = f"{_measurement_text(x2 - x1)} × {_measurement_text(y2 - y1)}"
        return (
            f'<text id="{annotation_id}" class="area-size" data-target="{target_id}" '
            f'x="{_number(x)}" y="{_number(y)}" text-anchor="middle">{text}</text>'
        )

    tick = 0.25
    if annotation.axis == "x":
        y = y1 + annotation.offset if annotation.side == "start" else y2 - annotation.offset
        mid_x = (x1 + x2) / 2.0
        label_y = y - 0.22 if annotation.side == "start" else y + 0.72
        return (
            f'<g id="{annotation_id}" class="measurement" data-target="{target_id}" data-axis="x">'
            f'<line x1="{_number(x1)}" y1="{_number(y)}" x2="{_number(x2)}" y2="{_number(y)}"/>'
            f'<line x1="{_number(x1)}" y1="{_number(y - tick)}" '
            f'x2="{_number(x1)}" y2="{_number(y + tick)}"/>'
            f'<line x1="{_number(x2)}" y1="{_number(y - tick)}" '
            f'x2="{_number(x2)}" y2="{_number(y + tick)}"/>'
            f'<text class="dimension-label" x="{_number(mid_x)}" y="{_number(label_y)}" '
            f'text-anchor="middle">{_measurement_text(x2 - x1)}</text></g>'
        )

    x = x1 + annotation.offset if annotation.side == "start" else x2 - annotation.offset
    mid_y = (y1 + y2) / 2.0
    label_dy = 0.3 if annotation.side == "start" else -0.3
    return (
        f'<g id="{annotation_id}" class="measurement" data-target="{target_id}" data-axis="y">'
        f'<line x1="{_number(x)}" y1="{_number(y1)}" x2="{_number(x)}" y2="{_number(y2)}"/>'
        f'<line x1="{_number(x - tick)}" y1="{_number(y1)}" '
        f'x2="{_number(x + tick)}" y2="{_number(y1)}"/>'
        f'<line x1="{_number(x - tick)}" y1="{_number(y2)}" '
        f'x2="{_number(x + tick)}" y2="{_number(y2)}"/>'
        f'<text class="dimension-label" x="{_number(x)}" y="{_number(mid_y)}" '
        f'text-anchor="middle" transform="rotate(-90 {_number(x)} {_number(mid_y)})" '
        f'dy="{_number(label_dy)}">{_measurement_text(y2 - y1)}</text></g>'
    )


def render_scenario_map_svg(geometry: ScenarioGeometry) -> str:
    """Render deterministic standalone SVG bytes from validated geometry."""

    width = _number(geometry.table.width)
    height = _number(geometry.table.height)
    title = escape(geometry.title)
    elements = "\n".join(_render_element(geometry, element) for element in geometry.elements)
    if elements:
        elements += "\n"
    rectangles = {
        element.id: element
        for element in geometry.elements
        if isinstance(element, RectangleElement)
    }
    markers = {
        element.id: element
        for element in geometry.elements
        if isinstance(element, MarkerElement)
    }
    annotations = "\n".join(
        _render_annotation(geometry, annotation, rectangles, markers)
        for annotation in geometry.annotations
    )
    if annotations:
        annotations += "\n"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="map-title" data-unit="in">\n'
        f'<title id="map-title">{title}</title>\n'
        f'<style>{_STYLE_CSS}</style>\n'
        f'<rect class="table" x="0" y="0" width="{width}" height="{height}"/>\n'
        f"{elements}"
        f"{annotations}"
        '</svg>\n'
    )
