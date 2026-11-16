"""Deterministic SVG projection for validated scenario geometry."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Literal

from .scenario_geometry import (
    AreaSizeAnnotation,
    CircleRegionElement,
    Coordinate,
    ElementEdgeDistanceAnnotation,
    LineElement,
    MarkerElement,
    QuarterCircleElement,
    RectangleElement,
    RulerAnnotation,
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
        "exclusion",
        "influence",
        "sector",
        "sector-center",
        "objective",
        "guide",
        "measurement",
        "label",
    }
)


class ScenarioMapRenderError(ValueError):
    """Raised when valid scenario geometry cannot be represented by SVG renderer v1."""


# Standalone SVGs use the same semantic map tokens as the browser themes.
# SVGs loaded through <img> cannot inherit the page's CSS variables.
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
.center-measurement{fill:none;stroke:var(--color-scenario-map-measurement,#203b35);
stroke-width:.075;stroke-dasharray:.3 .16}
.dimension-label,.area-size{fill:var(--color-scenario-map-text,#203b35);
font-family:sans-serif;font-size:var(--scenario-map-measure-size,1.1px);font-weight:600;
paint-order:stroke;stroke:var(--color-scenario-map-text-halo,#fffefa);stroke-width:.055;stroke-linejoin:round}
.label{fill:var(--color-scenario-map-text,#203b35);
font-family:sans-serif;font-size:var(--scenario-map-label-size,1.4px);font-weight:600}
"""

# Optional ITS-only styling is omitted from historical Core and Battleground
# SVGs to preserve their frozen byte-level publication identity.
_EXCLUSION_CSS = """.exclusion{fill:url(#scenario-exclusion-hatch);
stroke:var(--color-scenario-map-deployment-b-edge,#dc2626);stroke-width:.09}
"""
_EXCLUSION_DEFS = """<defs><pattern id="scenario-exclusion-hatch"
patternUnits="userSpaceOnUse" width="1.1" height="1.1" patternTransform="rotate(-45)">
<rect width="1.1" height="1.1" fill="var(--color-scenario-map-deployment-b,#fee2e2)"
fill-opacity=".7"/>
<line x1=".2" y1="0" x2=".2" y2="1.1"
stroke="var(--color-scenario-map-deployment-b-edge,#dc2626)" stroke-width=".28"
stroke-opacity=".48"/></pattern></defs>
"""
_SPECIAL_ZONE_CSS = """.influence{fill:#d4c7f1;fill-opacity:.8;stroke:#7463a8;stroke-width:.10}
.sector{fill:#b9c995;fill-opacity:.85;stroke:#667e47;stroke-width:.08}
.sector-center{fill:#eee7b7;fill-opacity:.85;stroke:#9e9855;stroke-width:.08}
svg[data-theme="dark"] .influence{fill:#51476b;stroke:#c0adf0}
svg[data-theme="dark"] .sector{fill:#4b5b3e;stroke:#a6c083}
svg[data-theme="dark"] .sector-center{fill:#6c6444;stroke:#d2c88b}
"""
_BEACON_MARKER_CSS = """.objective#beacon-a{fill:#cf4047;stroke:#8f1520}
.objective#beacon-b{fill:#278ec4;stroke:#15577c}
.objective[data-marker-type="console"]{fill:#84ca7a;stroke:#377735}
svg[data-theme="dark"] .objective#beacon-a{fill:#ed8388;stroke:#f5b6b9}
svg[data-theme="dark"] .objective#beacon-b{fill:#77c4ef;stroke:#c4eafd}
svg[data-theme="dark"] .objective[data-marker-type="console"]{fill:#6aa968;stroke:#b7ebb0}
"""
_UPLINK_MARKER_CSS = """.objective[data-marker-type="antenna"]{fill:#f7c86a;stroke:#b97b09}
.objective[data-marker-type="tech-coffin"]{fill:#a99ac5;stroke:#6d4d91}
svg[data-theme="dark"] .objective[data-marker-type="antenna"]{fill:#97741e;stroke:#efd18d}
svg[data-theme="dark"] .objective[data-marker-type="tech-coffin"]{fill:#725991;stroke:#dec9f1}
"""
_RULER_CSS = """.placement-ruler{stroke-width:.11}
.placement-ruler line{stroke-width:.11;stroke-dasharray:none}
"""


_THEME_TOKEN_RE = re.compile(r"(--color-scenario-map-[a-z-]+):\s*(#[0-9a-fA-F]{6});")


@lru_cache(maxsize=2)
def _theme_style(theme: Literal["light", "dark"]) -> str:
    """Embed canonical theme tokens so downloaded maps retain their appearance."""
    path = Path(__file__).resolve().parent / "web" / "static" / "themes" / f"{theme}.css"
    colors = dict(_THEME_TOKEN_RE.findall(path.read_text(encoding="utf-8")))
    required = set(re.findall(r"--color-scenario-map-[a-z-]+", _STYLE_CSS))
    if not required <= colors.keys():
        raise ScenarioMapRenderError(f"incomplete {theme} scenario-map theme palette")
    return ";".join(f"{name}:{colors[name]}" for name in sorted(required))


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

    if isinstance(element, CircleRegionElement):
        x = _resolved(geometry, element.x, "x")
        y = _resolved(geometry, element.y, "y")
        return (
            f'<circle id="{element_id}" class="{style}" data-region-shape="circle" '
            f'cx="{_number(x)}" cy="{_number(y)}" r="{_number(element.radius)}"/>'
        )

    if isinstance(element, QuarterCircleElement):
        radius = _number(element.radius)
        width = _number(geometry.table.width)
        height = _number(geometry.table.height)
        x_end = _number(geometry.table.width - element.radius)
        y_end = _number(geometry.table.height - element.radius)
        segments = {
            "top-left": f"M0 0 L{radius} 0 A{radius} {radius} 0 0 1 0 {radius} Z",
            "top-right": (
                f"M{width} 0 L{x_end} 0 A{radius} {radius} 0 0 0 {width} {radius} Z"
            ),
            "bottom-left": (
                f"M0 {height} L0 {y_end} A{radius} {radius} 0 0 1 {radius} {height} Z"
            ),
            "bottom-right": (
                f"M{width} {height} L{width} {y_end} "
                f"A{radius} {radius} 0 0 0 {x_end} {height} Z"
            ),
        }
        return (
            f'<path id="{element_id}" class="{style}" data-region-shape="quarter-circle" '
            f'data-corner="{element.corner}" data-radius-inches="{radius}" '
            f'd="{segments[element.corner]}"/>'
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
        if diameter_mm is None and element.marker_type != "beacon":
            raise ScenarioMapRenderError(
                "scenario SVG renderer v1 has no canonical marker metadata for "
                f"marker type {element.marker_type!r}"
            )
        if diameter_mm is None:
            # Schematic point: the Hardlock source gives a position but no token size.
            return (
                f'<circle id="{element_id}" class="{style}" data-marker-type="beacon" '
                f'data-physical-size="unspecified" cx="{_number(x)}" '
                f'cy="{_number(y)}" r=".3"/>'
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
    if "\n" in element.text:
        parts = element.text.split("\n")
        spans = "".join(
            f'<tspan x="{_number(x)}" dy="{"-.45" if index == 0 else "1.1"}em">'
            f'{escape(part)}</tspan>'
            for index, part in enumerate(parts)
        )
        accessible_label = escape(element.text.replace(chr(10), " "), quote=True)
        return (
            f'<text id="{element_id}" class="{style}" x="{_number(x)}" y="{_number(y)}" '
            f'text-anchor="{element.align}" aria-label="{accessible_label}">'
            f'{spans}</text>'
        )
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


def _measurement_text(value: float, distance_unit: Literal["in", "cm"]) -> str:
    if distance_unit == "cm":
        # Infinity's published distances use 2.5 cm per inch; physical marker
        # footprints remain fixed millimeters in canonical geometry.
        return f"{_number(value * 2.5)} cm"
    return f"{_number(value)}″"


def _render_ruler(
    geometry: ScenarioGeometry, ruler: RulerAnnotation,
    text_scale: float, distance_unit: Literal["in", "cm"],
) -> str:
    """Draw an exact, unit-convertible placement guide without adding map geometry."""
    x1 = _resolved(geometry, ruler.x1, "x")
    y1 = _resolved(geometry, ruler.y1, "y")
    x2 = _resolved(geometry, ruler.x2, "x")
    y2 = _resolved(geometry, ruler.y2, "y")
    length = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / length, (x2 - x1) / length
    x1 += ruler.offset * nx
    y1 += ruler.offset * ny
    x2 += ruler.offset * nx
    y2 += ruler.offset * ny
    tick = .25 * text_scale
    label_x = (x1 + x2) / 2 - .95 * text_scale * nx
    label_y = (y1 + y2) / 2 - .95 * text_scale * ny + .27 * text_scale
    ruler_id = escape(ruler.id, quote=True)
    display_distance = round(length, 3)
    return (
        f'<g id="{ruler_id}" class="measurement placement-ruler" '
        f'data-distance-inches="{_number(display_distance)}" data-ruler-reference="positions">'
        f'<line x1="{_number(x1)}" y1="{_number(y1)}" '
        f'x2="{_number(x2)}" y2="{_number(y2)}"/>'
        f'<line x1="{_number(x1 - tick * nx)}" y1="{_number(y1 - tick * ny)}" '
        f'x2="{_number(x1 + tick * nx)}" y2="{_number(y1 + tick * ny)}"/>'
        f'<line x1="{_number(x2 - tick * nx)}" y1="{_number(y2 - tick * ny)}" '
        f'x2="{_number(x2 + tick * nx)}" y2="{_number(y2 + tick * ny)}"/>'
        f'<text class="dimension-label" x="{_number(label_x)}" '
        f'y="{_number(label_y)}" text-anchor="middle" '
        f'data-distance-inches="{_number(display_distance)}">'
        f'{_measurement_text(display_distance, distance_unit)}</text></g>'
    )


def _render_annotation(
    geometry: ScenarioGeometry,
    annotation: ScenarioAnnotation,
    rectangles: dict[str, RectangleElement],
    markers: dict[str, MarkerElement],
    text_scale: float,
    distance_unit: Literal["in", "cm"],
) -> str:
    if isinstance(annotation, RulerAnnotation):
        return _render_ruler(geometry, annotation, text_scale, distance_unit)
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
                f'y="{_number(label_y)}" text-anchor="middle" '
                f'data-distance-inches="{_number(distance)}">'
                f'{_measurement_text(distance, distance_unit)}</text></g>'
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
            f'dy="{_number(label_dy)}" data-distance-inches="{_number(distance)}">'
            f'{_measurement_text(distance, distance_unit)}</text></g>'
        )

    target = rectangles[annotation.target]
    x1, y1, x2, y2 = _rectangle_bounds(geometry, target)

    if isinstance(annotation, AreaSizeAnnotation):
        x = (x1 + x2) / 2.0
        y = y1 + (y2 - y1) * 0.82
        text = (
            f"{_measurement_text(x2 - x1, distance_unit)} × "
            f"{_measurement_text(y2 - y1, distance_unit)}"
        )
        return (
            f'<text id="{annotation_id}" class="area-size" data-target="{target_id}" '
            f'x="{_number(x)}" y="{_number(y)}" text-anchor="middle" '
            f'data-distance-size-inches="{_number(x2 - x1)},{_number(y2 - y1)}">'
            f'{text}</text>'
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
            f'text-anchor="middle" data-distance-inches="{_number(x2 - x1)}">'
            f'{_measurement_text(x2 - x1, distance_unit)}</text></g>'
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
        f'dy="{_number(label_dy)}" data-distance-inches="{_number(y2 - y1)}">'
        f'{_measurement_text(y2 - y1, distance_unit)}</text></g>'
    )


def _domination_console_centers(geometry: ScenarioGeometry) -> dict[str, MarkerElement]:
    """Return reviewed quadrant-center Consoles, never approximate other maps.

    The four source-defined scoring rectangles and Console IDs are present in
    every N5.3 Domination size. Only draw placement rulers when each physical
    Console is at the exact center of its matching Quadrant.
    """
    rectangles = {
        element.id: element
        for element in geometry.elements
        if isinstance(element, RectangleElement) and element.style == "scoring"
    }
    markers = {
        element.id: element
        for element in geometry.elements
        if isinstance(element, MarkerElement) and element.marker_type == "console"
    }
    if set(rectangles) != {f"quadrant-{index}" for index in range(1, 5)}:
        return {}
    if set(markers) != {f"console-q{index}" for index in range(1, 5)}:
        return {}
    for index in range(1, 5):
        bounds = _rectangle_bounds(geometry, rectangles[f"quadrant-{index}"])
        marker = markers[f"console-q{index}"]
        x = _resolved(geometry, marker.x, "x")
        y = _resolved(geometry, marker.y, "y")
        if abs(x - (bounds[0] + bounds[2]) / 2) > 0.000001:
            return {}
        if abs(y - (bounds[1] + bounds[3]) / 2) > 0.000001:
            return {}
    return markers


def _render_console_center_guides(
    geometry: ScenarioGeometry,
    marker: MarkerElement,
    text_scale: float,
    distance_unit: Literal["in", "cm"],
) -> str:
    """Measure to marker *centers*, not to physical marker boundaries."""
    x = _resolved(geometry, marker.x, "x")
    y = _resolved(geometry, marker.y, "y")
    horizontal_edge = "left" if x < geometry.table.width / 2 else "right"
    vertical_edge = "top" if y < geometry.table.height / 2 else "bottom"
    edge_x = 0.0 if horizontal_edge == "left" else geometry.table.width
    edge_y = 0.0 if vertical_edge == "top" else geometry.table.height
    name = escape(marker.id, quote=True)
    return (
        f'<g id="{name}-center-{horizontal_edge}" class="center-measurement" '
        f'data-target="{name}" data-edge="{horizontal_edge}" data-reference="center">'
        f'<line x1="{_number(edge_x)}" y1="{_number(y)}" '
        f'x2="{_number(x)}" y2="{_number(y)}"/>'
        f'<text class="dimension-label" x="{_number((x + edge_x) / 2)}" '
        f'y="{_number(y + 1.05 * text_scale)}" text-anchor="middle" '
        f'data-distance-inches="{_number(abs(x - edge_x))}">'
        f'{_measurement_text(abs(x - edge_x), distance_unit)}</text></g>\n'
        f'<g id="{name}-center-{vertical_edge}" class="center-measurement" '
        f'data-target="{name}" data-edge="{vertical_edge}" data-reference="center">'
        f'<line x1="{_number(x)}" y1="{_number(edge_y)}" '
        f'x2="{_number(x)}" y2="{_number(y)}"/>'
        f'<text class="dimension-label" x="{_number(x + 1.1 * text_scale)}" '
        f'y="{_number((y + edge_y) / 2)}" text-anchor="start" '
        f'data-distance-inches="{_number(abs(y - edge_y))}">'
        f'{_measurement_text(abs(y - edge_y), distance_unit)}</text></g>'
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
            and element.marker_type != "beacon"
        ):
            raise ScenarioMapRenderError(
                "scenario SVG renderer v1 has no canonical marker metadata for "
                f"marker type {element.marker_type!r}"
            )


def render_scenario_map_svg(
    geometry: ScenarioGeometry, *, distance_unit: Literal["in", "cm"] = "in",
    theme: Literal["light", "dark"] = "light",
) -> str:
    """Render deterministic standalone SVG bytes from validated geometry."""

    if distance_unit not in {"in", "cm"}:
        raise ValueError("distance_unit must be in or cm")
    if theme not in {"light", "dark"}:
        raise ValueError("theme must be light or dark")
    _validate_renderer_support(geometry)
    width = _number(geometry.table.width)
    height = _number(geometry.table.height)
    title = escape(geometry.title)
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
    center_consoles = _domination_console_centers(geometry)
    elements = "\n".join(
        (
            _render_console_center_guides(
                geometry, center_consoles[element.id], text_scale, distance_unit
            ) + "\n"
            if element.id in center_consoles else ""
        ) + _render_element(geometry, element)
        for element in geometry.elements
    )
    if elements:
        elements += "\n"
    annotations = "\n".join(
        _render_annotation(geometry, annotation, rectangles, markers, text_scale, distance_unit)
        for annotation in geometry.annotations
        if not (
            center_consoles
            and isinstance(annotation, AreaSizeAnnotation)
            and annotation.target in {f"quadrant-{index}" for index in range(1, 5)}
        )
    )
    if annotations:
        annotations += "\n"
    styles = {element.style for element in geometry.elements}
    has_exclusion = "exclusion" in styles
    has_special_zones = bool(styles & {"influence", "sector", "sector-center"})
    has_rulers = any(isinstance(a, RulerAnnotation) for a in geometry.annotations)
    has_beacons = any(
        isinstance(element, MarkerElement) and element.marker_type == "beacon"
        for element in geometry.elements
    )
    has_tech_coffin = any(
        isinstance(element, MarkerElement) and element.marker_type == "tech-coffin"
        for element in geometry.elements
    )
    extra_style = (
        (_EXCLUSION_CSS if has_exclusion else "")
        + (_SPECIAL_ZONE_CSS if has_special_zones else "")
        + (_UPLINK_MARKER_CSS if has_tech_coffin else "")
        + (_BEACON_MARKER_CSS if has_beacons else "")
        + (_RULER_CSS if has_rulers else "")
    )
    defs = _EXCLUSION_DEFS if has_exclusion else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="map-title" data-unit="in" '
        f'data-distance-unit="{distance_unit}" data-theme="{theme}" '
        f'style="--scenario-map-label-size:{_number(1.4 * text_scale)}px;'
        f'--scenario-map-measure-size:{_number(1.1 * text_scale)}px;'
        f'{_theme_style(theme)}">\n'
        f'<title id="map-title">{title}</title>\n'
        f'<style>{_STYLE_CSS}{extra_style}</style>\n'
        f'{defs}'
        f'<rect class="table" x="0" y="0" width="{width}" height="{height}"/>\n'
        f"{elements}"
        f"{annotations}"
        '</svg>\n'
    )
