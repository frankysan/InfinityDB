"""Validated semantic geometry for Infinity scenario maps."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

SCENARIO_GEOMETRY_FORMAT = "InfinityDB scenario geometry"
SCENARIO_GEOMETRY_VERSION = 1

_ELEMENT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SUPPORTED_STYLES = frozenset(
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


class ScenarioGeometryError(ValueError):
    """Raised when scenario geometry does not satisfy the versioned contract."""


@dataclass(frozen=True, slots=True)
class AnchorCoordinate:
    """One table-relative coordinate on a single axis."""

    anchor: str
    offset: float = 0.0


Coordinate: TypeAlias = float | AnchorCoordinate


@dataclass(frozen=True, slots=True)
class ScenarioTable:
    """Physical table dimensions in canonical inches."""

    width: float
    height: float


@dataclass(frozen=True, slots=True)
class RectangleElement:
    id: str
    style: str
    x1: Coordinate
    y1: Coordinate
    x2: Coordinate
    y2: Coordinate


@dataclass(frozen=True, slots=True)
class LineElement:
    id: str
    style: str
    x1: Coordinate
    y1: Coordinate
    x2: Coordinate
    y2: Coordinate


@dataclass(frozen=True, slots=True)
class MarkerElement:
    id: str
    style: str
    x: Coordinate
    y: Coordinate
    radius: float


@dataclass(frozen=True, slots=True)
class LabelElement:
    id: str
    style: str
    x: Coordinate
    y: Coordinate
    text: str
    align: Literal["start", "middle", "end"]


ScenarioElement: TypeAlias = RectangleElement | LineElement | MarkerElement | LabelElement


@dataclass(frozen=True, slots=True)
class ScenarioGeometry:
    """One validated scenario-map geometry definition."""

    title: str
    table: ScenarioTable
    elements: tuple[ScenarioElement, ...]


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioGeometryError(f"{context} must be an object")
    return value


def _only_keys(
    value: dict[str, Any], required: set[str], optional: set[str], context: str
) -> None:
    keys = set(value)
    missing = required - keys
    extra = keys - required - optional
    if missing:
        raise ScenarioGeometryError(
            f"{context} is missing required field(s): {', '.join(sorted(missing))}"
        )
    if extra:
        raise ScenarioGeometryError(
            f"{context} contains unsupported field(s): {', '.join(sorted(extra))}"
        )


def _finite_number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScenarioGeometryError(f"{context} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ScenarioGeometryError(f"{context} must be a finite number")
    return number


def _positive_number(value: Any, context: str) -> float:
    number = _finite_number(value, context)
    if number <= 0:
        raise ScenarioGeometryError(f"{context} must be greater than zero")
    return number


def _non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioGeometryError(f"{context} must be a non-empty string")
    if value != value.strip():
        raise ScenarioGeometryError(f"{context} must not have surrounding whitespace")
    return value


def _element_id(value: Any, context: str) -> str:
    element_id = _non_empty_string(value, context)
    if _ELEMENT_ID_RE.fullmatch(element_id) is None:
        raise ScenarioGeometryError(
            f"{context} must use lowercase kebab-case ASCII identity"
        )
    return element_id


def _style(value: Any, context: str) -> str:
    style = _non_empty_string(value, context)
    if style not in _SUPPORTED_STYLES:
        raise ScenarioGeometryError(
            f"{context} must be one of {sorted(_SUPPORTED_STYLES)}"
        )
    return style


def _coordinate(value: Any, axis: Literal["x", "y"], context: str) -> Coordinate:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _finite_number(value, context)

    raw = _object(value, context)
    _only_keys(raw, {"anchor"}, {"offset"}, context)
    anchor = _non_empty_string(raw.get("anchor"), f"{context}.anchor")
    allowed = {"left", "center", "right"} if axis == "x" else {"top", "center", "bottom"}
    if anchor not in allowed:
        raise ScenarioGeometryError(
            f"{context}.anchor must be one of {sorted(allowed)} for the {axis}-axis"
        )
    offset = _finite_number(raw.get("offset", 0), f"{context}.offset")
    return AnchorCoordinate(anchor=anchor, offset=offset)


def _parse_element(value: Any, index: int) -> ScenarioElement:
    context = f"scenario geometry.elements[{index}]"
    raw = _object(value, context)
    kind = _non_empty_string(raw.get("kind"), f"{context}.kind")
    common_required = {"id", "kind", "style"}

    if kind == "rectangle":
        required = common_required | {"x1", "y1", "x2", "y2"}
        _only_keys(raw, required, set(), context)
        return RectangleElement(
            id=_element_id(raw.get("id"), f"{context}.id"),
            style=_style(raw.get("style"), f"{context}.style"),
            x1=_coordinate(raw.get("x1"), "x", f"{context}.x1"),
            y1=_coordinate(raw.get("y1"), "y", f"{context}.y1"),
            x2=_coordinate(raw.get("x2"), "x", f"{context}.x2"),
            y2=_coordinate(raw.get("y2"), "y", f"{context}.y2"),
        )

    if kind == "line":
        required = common_required | {"x1", "y1", "x2", "y2"}
        _only_keys(raw, required, set(), context)
        return LineElement(
            id=_element_id(raw.get("id"), f"{context}.id"),
            style=_style(raw.get("style"), f"{context}.style"),
            x1=_coordinate(raw.get("x1"), "x", f"{context}.x1"),
            y1=_coordinate(raw.get("y1"), "y", f"{context}.y1"),
            x2=_coordinate(raw.get("x2"), "x", f"{context}.x2"),
            y2=_coordinate(raw.get("y2"), "y", f"{context}.y2"),
        )

    if kind == "marker":
        required = common_required | {"x", "y", "radius"}
        _only_keys(raw, required, set(), context)
        return MarkerElement(
            id=_element_id(raw.get("id"), f"{context}.id"),
            style=_style(raw.get("style"), f"{context}.style"),
            x=_coordinate(raw.get("x"), "x", f"{context}.x"),
            y=_coordinate(raw.get("y"), "y", f"{context}.y"),
            radius=_positive_number(raw.get("radius"), f"{context}.radius"),
        )

    if kind == "label":
        required = common_required | {"x", "y", "text"}
        _only_keys(raw, required, {"align"}, context)
        align = raw.get("align", "middle")
        if align not in {"start", "middle", "end"}:
            raise ScenarioGeometryError(
                f"{context}.align must be one of ['end', 'middle', 'start']"
            )
        return LabelElement(
            id=_element_id(raw.get("id"), f"{context}.id"),
            style=_style(raw.get("style"), f"{context}.style"),
            x=_coordinate(raw.get("x"), "x", f"{context}.x"),
            y=_coordinate(raw.get("y"), "y", f"{context}.y"),
            text=_non_empty_string(raw.get("text"), f"{context}.text"),
            align=align,
        )

    raise ScenarioGeometryError(
        f"{context}.kind must be one of ['label', 'line', 'marker', 'rectangle']"
    )


def resolve_coordinate(
    coordinate: Coordinate, *, axis: Literal["x", "y"], table: ScenarioTable
) -> float:
    """Resolve one absolute or table-relative coordinate to canonical inches."""

    if not isinstance(coordinate, AnchorCoordinate):
        return float(coordinate)

    limit = table.width if axis == "x" else table.height
    if coordinate.anchor in {"left", "top"}:
        base = 0.0
    elif coordinate.anchor == "center":
        base = limit / 2.0
    else:
        base = limit
    return base + coordinate.offset


def _validate_resolved_geometry(geometry: ScenarioGeometry) -> None:
    table = geometry.table

    def resolved(coordinate: Coordinate, axis: Literal["x", "y"], context: str) -> float:
        value = resolve_coordinate(coordinate, axis=axis, table=table)
        limit = table.width if axis == "x" else table.height
        if value < 0 or value > limit:
            raise ScenarioGeometryError(
                f"{context} resolves to {value:g} in outside table {axis}-range 0..{limit:g}"
            )
        return value

    for element in geometry.elements:
        context = f"scenario geometry element {element.id!r}"
        if isinstance(element, (RectangleElement, LineElement)):
            x1 = resolved(element.x1, "x", f"{context}.x1")
            y1 = resolved(element.y1, "y", f"{context}.y1")
            x2 = resolved(element.x2, "x", f"{context}.x2")
            y2 = resolved(element.y2, "y", f"{context}.y2")
            if isinstance(element, RectangleElement) and (x2 <= x1 or y2 <= y1):
                raise ScenarioGeometryError(
                    f"{context} rectangle must resolve to positive width and height"
                )
        elif isinstance(element, MarkerElement):
            x = resolved(element.x, "x", f"{context}.x")
            y = resolved(element.y, "y", f"{context}.y")
            if (
                x - element.radius < 0
                or x + element.radius > table.width
                or y - element.radius < 0
                or y + element.radius > table.height
            ):
                raise ScenarioGeometryError(
                    f"{context} marker radius extends outside the table"
                )
        else:
            resolved(element.x, "x", f"{context}.x")
            resolved(element.y, "y", f"{context}.y")


def parse_scenario_geometry(document: Any) -> ScenarioGeometry:
    """Validate and compile one scenario geometry v1 document."""

    root = _object(document, "scenario geometry")
    _only_keys(
        root,
        {"format", "formatVersion", "title", "table", "elements"},
        set(),
        "scenario geometry",
    )
    if root.get("format") != SCENARIO_GEOMETRY_FORMAT:
        raise ScenarioGeometryError(
            f"scenario geometry.format must be {SCENARIO_GEOMETRY_FORMAT!r}"
        )
    if root.get("formatVersion") != SCENARIO_GEOMETRY_VERSION:
        raise ScenarioGeometryError(
            f"scenario geometry.formatVersion must be {SCENARIO_GEOMETRY_VERSION}"
        )

    table_raw = _object(root.get("table"), "scenario geometry.table")
    _only_keys(table_raw, {"width", "height", "unit"}, set(), "scenario geometry.table")
    if table_raw.get("unit") != "in":
        raise ScenarioGeometryError("scenario geometry.table.unit must be 'in'")
    table = ScenarioTable(
        width=_positive_number(table_raw.get("width"), "scenario geometry.table.width"),
        height=_positive_number(table_raw.get("height"), "scenario geometry.table.height"),
    )

    elements_raw = root.get("elements")
    if not isinstance(elements_raw, list):
        raise ScenarioGeometryError("scenario geometry.elements must be an array")
    elements = tuple(_parse_element(value, index) for index, value in enumerate(elements_raw))
    ids = [element.id for element in elements]
    if len(set(ids)) != len(ids):
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        raise ScenarioGeometryError(
            "scenario geometry.elements contains duplicate id(s): " + ", ".join(duplicates)
        )

    geometry = ScenarioGeometry(
        title=_non_empty_string(root.get("title"), "scenario geometry.title"),
        table=table,
        elements=elements,
    )
    _validate_resolved_geometry(geometry)
    return geometry
