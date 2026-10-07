"""Validated maintained scenario definitions that own scenario geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_slugs import require_domain_slug, validate_typed_domain_id
from .scenario_geometry import ScenarioGeometry, parse_scenario_geometry
from .scenario_mission import ScenarioMission, parse_scenario_mission

SCENARIO_DEFINITION_VERSION = 1


class ScenarioDefinitionError(ValueError):
    """Raised when maintained scenario facts do not satisfy the typed contract."""


@dataclass(frozen=True, slots=True)
class ScenarioConfiguration:
    """One geometry-bearing scenario configuration selected by Army Points."""

    id: str
    army_points: tuple[int, ...]
    geometry: ScenarioGeometry


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    """One maintained scenario definition compiled from a curated scenario record."""

    id: str
    name: str
    configurations: tuple[ScenarioConfiguration, ...]
    mission: ScenarioMission | None = None


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioDefinitionError(f"{context} must be an object")
    return value


def _only_keys(value: dict[str, Any], required: set[str], optional: set[str], context: str) -> None:
    keys = set(value)
    missing = required - keys
    extra = keys - required - optional
    if missing:
        raise ScenarioDefinitionError(
            f"{context} is missing required field(s): {', '.join(sorted(missing))}"
        )
    if extra:
        raise ScenarioDefinitionError(
            f"{context} contains unsupported field(s): {', '.join(sorted(extra))}"
        )


def _positive_int(value: Any, context: str) -> int:
    if type(value) is not int or value <= 0:
        raise ScenarioDefinitionError(f"{context} must be a positive integer")
    return value


def parse_scenario_definition_record(record: Any) -> ScenarioDefinition:
    """Validate the typed v1 facts of one curated scenario definition record."""

    root = _object(record, "scenario record")
    if root.get("kind") != "scenario":
        raise ScenarioDefinitionError("scenario record.kind must be 'scenario'")

    scenario_id = root.get("id")
    try:
        validate_typed_domain_id(
            scenario_id, expected_domain="scenario", context="scenario record.id"
        )
    except ValueError as exc:
        raise ScenarioDefinitionError(str(exc)) from exc
    assert isinstance(scenario_id, str)

    name = root.get("name")
    if not isinstance(name, str) or not name.strip() or name != name.strip():
        raise ScenarioDefinitionError("scenario record.name must be a non-empty trimmed string")

    facts = _object(root.get("facts"), "scenario record.facts")
    _only_keys(
        facts,
        {"definitionVersion", "configurations"},
        {"relatedCategories", "mission"},
        "scenario record.facts",
    )
    if (
        type(facts.get("definitionVersion")) is not int
        or facts["definitionVersion"] != SCENARIO_DEFINITION_VERSION
    ):
        raise ScenarioDefinitionError(
            f"scenario record.facts.definitionVersion must be {SCENARIO_DEFINITION_VERSION}"
        )

    raw_configurations = facts.get("configurations")
    if not isinstance(raw_configurations, list) or not raw_configurations:
        raise ScenarioDefinitionError(
            "scenario record.facts.configurations must be a non-empty array"
        )

    seen_ids: set[str] = set()
    seen_army_points: set[int] = set()
    configurations: list[ScenarioConfiguration] = []
    for index, value in enumerate(raw_configurations):
        context = f"scenario record.facts.configurations[{index}]"
        raw = _object(value, context)
        _only_keys(raw, {"id", "armyPoints", "geometry"}, set(), context)

        try:
            config_id = require_domain_slug(raw.get("id"), context=f"{context}.id")
        except ValueError as exc:
            raise ScenarioDefinitionError(str(exc)) from exc
        if config_id in seen_ids:
            raise ScenarioDefinitionError(f"{context}.id duplicates {config_id!r}")
        seen_ids.add(config_id)

        raw_points = raw.get("armyPoints")
        if not isinstance(raw_points, list) or not raw_points:
            raise ScenarioDefinitionError(f"{context}.armyPoints must be a non-empty array")
        army_points = tuple(
            _positive_int(point, f"{context}.armyPoints[{point_index}]")
            for point_index, point in enumerate(raw_points)
        )
        if len(set(army_points)) != len(army_points):
            raise ScenarioDefinitionError(f"{context}.armyPoints must not contain duplicates")
        duplicate_points = seen_army_points.intersection(army_points)
        if duplicate_points:
            duplicates = ", ".join(str(point) for point in sorted(duplicate_points))
            raise ScenarioDefinitionError(
                f"{context}.armyPoints overlaps another configuration: {duplicates}"
            )
        seen_army_points.update(army_points)

        try:
            geometry = parse_scenario_geometry(raw.get("geometry"))
        except ValueError as exc:
            raise ScenarioDefinitionError(f"{context}.geometry: {exc}") from exc
        if geometry.title != name:
            raise ScenarioDefinitionError(
                f"{context}.geometry.title must match scenario record.name {name!r}"
            )
        configurations.append(
            ScenarioConfiguration(
                id=config_id,
                army_points=army_points,
                geometry=geometry,
            )
        )

    mission = None
    if "mission" in facts:
        try:
            mission = parse_scenario_mission(facts["mission"], tuple(configurations))
        except ValueError as exc:
            raise ScenarioDefinitionError(str(exc)) from exc

    return ScenarioDefinition(
        id=scenario_id,
        name=name,
        configurations=tuple(configurations),
        mission=mission,
    )


def scenario_definition_from_curated_document(
    document: Any, scenario_id: str
) -> ScenarioDefinition:
    """Resolve one maintained scenario definition from a validated curated document."""

    root = _object(document, "curated document")
    records = root.get("records")
    if not isinstance(records, list):
        raise ScenarioDefinitionError("curated document.records must be an array")

    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("kind") == "scenario"
        and record.get("id") == scenario_id
    ]
    if not matches:
        raise ScenarioDefinitionError(f"unknown scenario definition {scenario_id!r}")
    if len(matches) != 1:
        raise ScenarioDefinitionError(f"duplicate scenario definition {scenario_id!r}")
    return parse_scenario_definition_record(matches[0])


def select_scenario_geometry(definition: ScenarioDefinition, army_points: int) -> ScenarioGeometry:
    """Select the maintained geometry applicable to one Army Points value."""

    _positive_int(army_points, "army_points")
    for configuration in definition.configurations:
        if army_points in configuration.army_points:
            return configuration.geometry
    supported = sorted(
        point for configuration in definition.configurations for point in configuration.army_points
    )
    raise ScenarioDefinitionError(
        f"scenario {definition.id!r} does not support {army_points} Army Points; "
        f"supported values: {supported}"
    )
