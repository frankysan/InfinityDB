"""Deterministic SVG projection for validated scenario geometry."""

from __future__ import annotations

from html import escape
from typing import Literal

from .scenario_geometry import (
    AreaSizeAnnotation,
    Coordinate,
    ElementEdgeDistanceAnnotation,
    LineElement,
    MarkerElement,
    RectangleElement,
    ScenarioAnnotation,
    ScenarioElement,
    ScenarioGeometry,
    element_bounds,
    element_edge_distance_to_table,
    marker_diameter_mm,
    marker_radius_inches,
    resolve_coordinate,
)

_RENDERABLE_ELEMENT_STYLES = frozenset(
    {
        "deployment-a",
        "deployment-b",
        "scoring",
        "objective",
        "guide",
        "measurement",
        "label",
    }
)


class ScenarioMapRenderError(ValueError):
    """Raised when valid scenario geometry cannot be represented by SVG renderer v1."""


# The SVG works as a standalone light-map image with fallbacks, but inherits
# semantic tokens from InfinityDB when embedded inline in the browser.
_STYLE_CSS = """\
.table{fill:var(--color-scenario-map-table,#fffefa);
stroke:var(--color-scenario-map-outline,#203b35);stroke-width:.12}
.deployment-a{fill:var(--color-scenario-map-deployment-a,#dbeafe);
stroke:var(--color-scenario-map-deployment-a-edge,#2563eb);stroke-width:.09}
.deployment-b{fill:var(--color-scenario-map-deployment-b,#fee2e2);
stroke:var(--color-scenario-map-deployment-b-edge,#dc2626);stroke-width:.09}
.scoring{fill:var(--color-scenario-map-scoring,#e5e7eb);fill-opacity:.65;
stroke:var(--color-scenario-map-scoring-edge,#6b7280);stroke-width:.07}
.objective{fill:var(--color-scenario-map-marker,#fffefa);
stroke:var(--color-scenario-map-outline,#203b35);stroke-width:.1}
.guide{fill:none;stroke:var(--color-scenario-map-guide,#65716b);
stroke-width:.06;stroke-dasharray:.35 .25}
.measurement{fill:none;stroke:var(--color-scenario-map-measurement,#203b35);stroke-width:.05}
.dimension-label,.area-size{fill:var(--color-scenario-map-text,#203b35);
font-family:sans-serif;font-size:var(--scenario-map-measure-size,1.1px);font-weight:600;
paint-order:stroke;stroke:var(--color-scenario-map-text-halo,#fffefa);stroke-width:.055;stroke-linejoin:round}
.label{fill:var(--color-scenario-map-text,#203b35);
font-family:sans-serif;font-size:var(--scenario-map-label-size,1.4px);font-weight:600}
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
            raise ScenarioMapRenderError(
                "scenario SVG renderer v1 has no canonical marker metadata for "
                f"marker type {element.marker_type!r}"
            )
        radius = marker_radius_inches(element.marker_type)
        assert radius is not None
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
    text_scale: float,
) -> str:
    annotation_id = escape(annotation.id, quote=True)
    target_id = escape(annotation.target, quote=True)

    if isinstance(annotation, ElementEdgeDistanceAnnotation):
        target = markers.get(annotation.target) or rectangles.get(annotation.target)
        if target is None:
            raise ScenarioMapRenderError(
                f"scenario SVG renderer v1 cannot measure target {annotation.target!r}"
            )
        x1, y1, x2, y2 = element_bounds(target, table=geometry.table)
        distance = element_edge_distance_to_table(
            target, edge=annotation.edge, table=geometry.table
        )
        tick = 0.25 * text_scale
        edge = annotation.edge
        if edge in {"left", "right"}:
            edge_x = 0.0 if edge == "left" else geometry.table.width
            target_x = x1 if edge == "left" else x2
            target_y = (y1 + y2) / 2.0
            line_y = target_y + annotation.offset
            measure_x1, measure_x2 = sorted((target_x, edge_x))
            label_y = (
                line_y - 0.4 * text_scale
                if annotation.offset <= 0
                else line_y + 1.05 * text_scale
            )
            return (
                f'<g id="{annotation_id}" class="measurement" data-target="{target_id}" '
                f'data-edge="{edge}" data-axis="x">'
                f'<line x1="{_number(measure_x1)}" y1="{_number(line_y)}" '
                f'x2="{_number(measure_x2)}" y2="{_number(line_y)}"/>'
                f'<line x1="{_number(measure_x1)}" y1="{_number(line_y - tick)}" '
                f'x2="{_number(measure_x1)}" y2="{_number(line_y + tick)}"/>'
                f'<line x1="{_number(measure_x2)}" y1="{_number(line_y - tick)}" '
                f'x2="{_number(measure_x2)}" y2="{_number(line_y + tick)}"/>'
                f'<text class="dimension-label" x="{_number((measure_x1 + measure_x2) / 2.0)}" '
                f'y="{_number(label_y)}" text-anchor="middle">'
                f'{_measurement_text(distance)}</text></g>'
            )

        edge_y = 0.0 if edge == "top" else geometry.table.height
        target_y = y1 if edge == "top" else y2
        target_x = (x1 + x2) / 2.0
        line_x = target_x + annotation.offset
        measure_y1, measure_y2 = sorted((target_y, edge_y))
        label_dy = 0.4 * text_scale if annotation.offset <= 0 else -0.4 * text_scale
        mid_y = (measure_y1 + measure_y2) / 2.0
        return (
            f'<g id="{annotation_id}" class="measurement" data-target="{target_id}" '
            f'data-edge="{edge}" data-axis="y">'
            f'<line x1="{_number(line_x)}" y1="{_number(measure_y1)}" '
            f'x2="{_number(line_x)}" y2="{_number(measure_y2)}"/>'
            f'<line x1="{_number(line_x - tick)}" y1="{_number(measure_y1)}" '
            f'x2="{_number(line_x + tick)}" y2="{_number(measure_y1)}"/>'
            f'<line x1="{_number(line_x - tick)}" y1="{_number(measure_y2)}" '
            f'x2="{_number(line_x + tick)}" y2="{_number(measure_y2)}"/>'
            f'<text class="dimension-label" x="{_number(line_x)}" y="{_number(mid_y)}" '
            f'text-anchor="middle" transform="rotate(-90 {_number(line_x)} {_number(mid_y)})" '
            f'dy="{_number(label_dy)}">{_measurement_text(distance)}</text></g>'
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

    tick = 0.25 * text_scale
    if annotation.axis == "x":
        y = y1 + annotation.offset if annotation.side == "start" else y2 - annotation.offset
        mid_x = (x1 + x2) / 2.0
        label_y = y - 0.4 * text_scale if annotation.side == "start" else y + 1.05 * text_scale
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
    label_dy = 0.4 * text_scale if annotation.side == "start" else -0.4 * text_scale
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


def _validate_renderer_support(geometry: ScenarioGeometry) -> None:
    for element in geometry.elements:
        if element.style not in _RENDERABLE_ELEMENT_STYLES:
            raise ScenarioMapRenderError(
                "scenario SVG renderer v1 does not support element style "
                f"{element.style!r}"
            )
        if (
            isinstance(element, MarkerElement)
            and marker_diameter_mm(element.marker_type) is None
        ):
            raise ScenarioMapRenderError(
                "scenario SVG renderer v1 has no canonical marker metadata for "
                f"marker type {element.marker_type!r}"
            )


def render_scenario_map_svg(geometry: ScenarioGeometry) -> str:
    """Render deterministic standalone SVG bytes from validated geometry."""

    _validate_renderer_support(geometry)
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
    # Increase viewBox-space text on wider tables; at the same on-screen map width,
    # 48-inch maps should no longer render labels at half the size of 24-inch maps.
    text_scale = 1.0 + max(0.0, min(24.0, geometry.table.width - 24.0)) / 48.0
    annotations = "\n".join(
        _render_annotation(geometry, annotation, rectangles, markers, text_scale)
        for annotation in geometry.annotations
    )
    if annotations:
        annotations += "\n"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="map-title" data-unit="in" '
        f'style="--scenario-map-label-size:{_number(1.4 * text_scale)}px;'
        f'--scenario-map-measure-size:{_number(1.1 * text_scale)}px">\n'
        f'<title id="map-title">{title}</title>\n'
        f'<style>{_STYLE_CSS}</style>\n'
        f'<rect class="table" x="0" y="0" width="{width}" height="{height}"/>\n'
        f"{elements}"
        f"{annotations}"
        '</svg>\n'
    )
