"""Typed reference facts for scenario setup, scoring, and mission end conditions.

This is a reference model, not a match-state evaluator. Source ambiguities remain
explicit and reviewed prose is retained where executable predicates would guess.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .domain_slugs import require_domain_slug, validate_typed_domain_id
from .scenario_geometry import MarkerElement, RectangleElement

if TYPE_CHECKING:
    from .scenario_definition import ScenarioConfiguration


class ScenarioMissionError(ValueError):
    """Raised when scenario reference facts violate their typed contract."""


@dataclass(frozen=True, slots=True)
class ScenarioSide:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class ScenarioDeployment:
    side_id: str
    element_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioGameSize:
    army_points: int
    swc: float
    configuration_id: str
    deployments: tuple[ScenarioDeployment, ...]
    minimum_victory_points: int | None = None


@dataclass(frozen=True, slots=True)
class NumericRangeCondition:
    metric: str
    minimum: int
    maximum: int | None


@dataclass(frozen=True, slots=True)
class MetricComparison:
    metric: str
    comparison: str


@dataclass(frozen=True, slots=True)
class ProseCondition:
    text: str


@dataclass(frozen=True, slots=True)
class DominatedRegionComparison:
    element_ids: tuple[str, ...]
    comparison: str
    minimum: int | None


@dataclass(frozen=True, slots=True)
class ElementStatusCount:
    element_ids: tuple[str, ...]
    status: str


@dataclass(frozen=True, slots=True)
class ElementStatusComparison:
    element_ids: tuple[str, ...]
    status: str
    comparison: str


ScenarioScoreCondition = (
    NumericRangeCondition
    | MetricComparison
    | ProseCondition
    | DominatedRegionComparison
    | ElementStatusCount
    | ElementStatusComparison
)


@dataclass(frozen=True, slots=True)
class ScenarioAward:
    army_points: tuple[int, ...]
    objective_points: int
    condition: ScenarioScoreCondition


@dataclass(frozen=True, slots=True)
class ScenarioObjective:
    id: str
    name: str
    side_ids: tuple[str, ...]
    timing: str
    aggregation: str
    maximum_points: int
    awards: tuple[ScenarioAward, ...]
    maximum_points_per_round: int | None = None


@dataclass(frozen=True, slots=True)
class ScenarioRule:
    id: str
    name: str
    paragraphs: tuple[str, ...]
    definition_id: str | None = None
    skill_ids: tuple[str, ...] = ()
    specialist_skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScenarioEndCondition:
    id: str
    check_at: str
    finish_at: str
    rounds: int | None
    description: str | None
    uses_minimum_victory_points: bool = False


@dataclass(frozen=True, slots=True)
class ScenarioSourceIssue:
    id: str
    army_points: tuple[int, ...]
    objective_id: str | None
    description: str
    status: str = "needs-verification"
    game_size_field: str | None = None
    geometry_element_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScenarioMission:
    sides: tuple[ScenarioSide, ...]
    game_sizes: tuple[ScenarioGameSize, ...]
    objectives: tuple[ScenarioObjective, ...]
    rules: tuple[ScenarioRule, ...]
    end_conditions: tuple[ScenarioEndCondition, ...]
    source_issues: tuple[ScenarioSourceIssue, ...]
    skill_ids: tuple[str, ...] = ()


def _object(value: Any, required: set[str], optional: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioMissionError(f"{context} must be an object")
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing:
        raise ScenarioMissionError(f"{context} is missing required fields: {sorted(missing)}")
    if extra:
        raise ScenarioMissionError(f"{context} contains unsupported fields: {sorted(extra)}")
    return value


def _array(value: Any, context: str, *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "an" if allow_empty else "a non-empty"
        raise ScenarioMissionError(f"{context} must be {qualifier} array")
    return value


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ScenarioMissionError(f"{context} must be a non-empty trimmed string")
    return value


def _slug(value: Any, context: str) -> str:
    try:
        return require_domain_slug(value, context=context)
    except ValueError as exc:
        raise ScenarioMissionError(str(exc)) from exc


def _integer(value: Any, context: str, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise ScenarioMissionError(f"{context} must be an integer >= {minimum}")
    return value


def _choice(value: Any, choices: set[str], context: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ScenarioMissionError(f"{context} must be one of {sorted(choices)}")
    return value


def _references(value: Any, known: set[str], context: str) -> tuple[str, ...]:
    result = tuple(_slug(item, context) for item in _array(value, context))
    if len(set(result)) != len(result):
        raise ScenarioMissionError(f"{context} contains duplicate references")
    unknown = set(result) - known
    if unknown:
        raise ScenarioMissionError(f"{context} contains unknown references: {sorted(unknown)}")
    return result


def _points(value: Any, known: set[int], context: str) -> tuple[int, ...]:
    result = tuple(_integer(item, context) for item in _array(value, context))
    if len(set(result)) != len(result):
        raise ScenarioMissionError(f"{context} contains duplicate Army Points")
    if set(result) - known:
        raise ScenarioMissionError(f"{context} contains unsupported Army Points")
    return result


def _unique(identifier: str, seen: set[str], context: str) -> None:
    if identifier in seen:
        raise ScenarioMissionError(f"{context} duplicates {identifier!r}")
    seen.add(identifier)


def _condition(value: Any, context: str) -> ScenarioScoreCondition:
    if not isinstance(value, dict):
        raise ScenarioMissionError(f"{context} must be an object")
    kind = value.get("kind")
    if kind == "numeric-range":
        raw = _object(value, {"kind", "metric", "minimum", "maximum"}, set(), context)
        metric = _choice(
            raw["metric"],
            {"enemy-army-points-killed", "surviving-victory-points"},
            f"{context}.metric",
        )
        minimum = _integer(raw["minimum"], f"{context}.minimum", minimum=0)
        maximum = raw["maximum"]
        if maximum is not None:
            maximum = _integer(maximum, f"{context}.maximum", minimum=minimum)
        return NumericRangeCondition(metric, minimum, maximum)
    if kind == "metric-comparison":
        raw = _object(value, {"kind", "metric", "comparison"}, set(), context)
        metric = _choice(
            raw["metric"],
            {
                "surviving-specialist-troops",
                "enemy-specialist-troops-killed",
                "enemy-lieutenants-killed",
                "enemy-army-points-killed",
            },
            f"{context}.metric",
        )
        comparison = _choice(raw["comparison"], {"greater"}, f"{context}.comparison")
        return MetricComparison(metric, comparison)
    if kind == "reviewed-prose":
        raw = _object(value, {"kind", "text"}, set(), context)
        return ProseCondition(_text(raw["text"], f"{context}.text"))
    if isinstance(kind, str) and kind in {
        "dominated-region-comparison",
        "element-status-count",
        "element-status-comparison",
    }:
        required = {"kind", "elementIds"}
        required.add("comparison" if kind == "dominated-region-comparison" else "status")
        if kind == "element-status-comparison":
            required.add("comparison")
        raw = _object(
            value,
            required,
            {"minimum"} if kind == "dominated-region-comparison" else set(),
            context,
        )
        elements = tuple(
            _slug(item, f"{context}.elementIds")
            for item in _array(raw["elementIds"], f"{context}.elementIds")
        )
        if len(set(elements)) != len(elements):
            raise ScenarioMissionError(f"{context}.elementIds contains duplicate references")
        if kind in {"element-status-count", "element-status-comparison"}:
            status = _choice(raw["status"], {"hacked", "controlled"}, f"{context}.status")
            if kind == "element-status-count":
                return ElementStatusCount(elements, status)
            comparison = _choice(raw["comparison"], {"greater", "all"}, f"{context}.comparison")
            return ElementStatusComparison(elements, status, comparison)
        comparison = _choice(raw["comparison"], {"equal", "greater"}, f"{context}.comparison")
        minimum = None
        if "minimum" in raw:
            minimum = _integer(raw["minimum"], f"{context}.minimum", minimum=0)
            if minimum > len(elements):
                raise ScenarioMissionError(f"{context}.minimum exceeds the number of regions")
        return DominatedRegionComparison(elements, comparison, minimum)
    raise ScenarioMissionError(f"{context} contains unsupported condition kind {kind!r}")


def _validate_score_geometry(
    condition: ScenarioScoreCondition,
    points: tuple[int, ...],
    configurations: tuple[ScenarioConfiguration, ...],
    context: str,
) -> None:
    if not isinstance(
        condition, (DominatedRegionComparison, ElementStatusCount, ElementStatusComparison)
    ):
        return
    expected = (
        RectangleElement if isinstance(condition, DominatedRegionComparison) else MarkerElement
    )
    for configuration in configurations:
        if not set(points).intersection(configuration.army_points):
            continue
        elements = {element.id: element for element in configuration.geometry.elements}
        for identifier in condition.element_ids:
            element = elements.get(identifier)
            if not isinstance(element, expected):
                raise ScenarioMissionError(
                    f"{context} references missing or incompatible scoring element {identifier!r} "
                    f"in configuration {configuration.id!r}"
                )


def parse_scenario_mission(
    value: Any, configurations: tuple[ScenarioConfiguration, ...]
) -> ScenarioMission:
    """Validate the optional reference component of a maintained scenario definition."""

    context = "scenario record.facts.mission"
    raw = _object(
        value,
        {"sides", "gameSizes", "objectives", "rules", "endConditions", "sourceIssues"},
        {"skills"},
        context,
    )
    side_ids: set[str] = set()
    sides: list[ScenarioSide] = []
    for index, item in enumerate(_array(raw["sides"], f"{context}.sides")):
        ctx = f"{context}.sides[{index}]"
        side = _object(item, {"id", "name"}, set(), ctx)
        identifier = _slug(side["id"], f"{ctx}.id")
        _unique(identifier, side_ids, ctx)
        sides.append(ScenarioSide(identifier, _text(side["name"], f"{ctx}.name")))

    configs = {config.id: config for config in configurations}
    supported_points = {point for config in configurations for point in config.army_points}
    seen_points: set[int] = set()
    game_sizes: list[ScenarioGameSize] = []
    for index, item in enumerate(_array(raw["gameSizes"], f"{context}.gameSizes")):
        ctx = f"{context}.gameSizes[{index}]"
        size = _object(
            item,
            {"armyPoints", "swc", "configurationId", "deployments"},
            {"minimumVictoryPoints"},
            ctx,
        )
        points = _integer(size["armyPoints"], f"{ctx}.armyPoints")
        if points in seen_points:
            raise ScenarioMissionError(f"{ctx} duplicates Army Points {points}")
        seen_points.add(points)
        config_id = _slug(size["configurationId"], f"{ctx}.configurationId")
        config = configs.get(config_id)
        if config is None or points not in config.army_points:
            raise ScenarioMissionError(
                f"{ctx} does not reference the geometry for {points} Army Points"
            )
        swc = size["swc"]
        if type(swc) not in (int, float) or not math.isfinite(swc) or swc < 0:
            raise ScenarioMissionError(f"{ctx}.swc must be a finite non-negative number")
        regions = {
            element.id
            for element in config.geometry.elements
            if isinstance(element, RectangleElement)
        }
        deployments: list[ScenarioDeployment] = []
        deployed_sides: set[str] = set()
        used_regions: set[str] = set()
        for deployment_index, deployment in enumerate(_array(size["deployments"], ctx)):
            dep_ctx = f"{ctx}.deployments[{deployment_index}]"
            dep = _object(deployment, {"sideId", "elementIds"}, set(), dep_ctx)
            side_id = _slug(dep["sideId"], f"{dep_ctx}.sideId")
            if side_id not in side_ids:
                raise ScenarioMissionError(f"{dep_ctx} references unknown side {side_id!r}")
            _unique(side_id, deployed_sides, dep_ctx)
            region_ids = _references(dep["elementIds"], regions, f"{dep_ctx}.elementIds")
            if used_regions.intersection(region_ids):
                raise ScenarioMissionError(
                    f"{dep_ctx} assigns a deployment region to multiple sides"
                )
            used_regions.update(region_ids)
            deployments.append(ScenarioDeployment(side_id, region_ids))
        if deployed_sides != side_ids:
            raise ScenarioMissionError(f"{ctx} must define deployment for every side")
        minimum_vp = None
        if "minimumVictoryPoints" in size:
            minimum_vp = _integer(size["minimumVictoryPoints"], f"{ctx}.minimumVictoryPoints")
            if minimum_vp > points:
                raise ScenarioMissionError(f"{ctx}.minimumVictoryPoints exceeds Army Points")
        game_sizes.append(
            ScenarioGameSize(points, float(swc), config_id, tuple(deployments), minimum_vp)
        )
    if seen_points != supported_points:
        raise ScenarioMissionError(
            f"{context}.gameSizes must cover every configured Army Points value"
        )

    objectives: list[ScenarioObjective] = []
    objective_ids: set[str] = set()
    for index, item in enumerate(_array(raw["objectives"], f"{context}.objectives")):
        ctx = f"{context}.objectives[{index}]"
        objective = _object(
            item,
            {"id", "name", "sideIds", "timing", "aggregation", "maximumPoints", "awards"},
            {"maximumPointsPerRound"},
            ctx,
        )
        identifier = _slug(objective["id"], f"{ctx}.id")
        _unique(identifier, objective_ids, ctx)
        name = _text(objective["name"], f"{ctx}.name")
        references = _references(objective["sideIds"], side_ids, f"{ctx}.sideIds")
        timing = _choice(objective["timing"], {"immediate", "end-of-round", "end-of-game"}, ctx)
        aggregation = _choice(objective["aggregation"], {"exclusive", "cumulative"}, ctx)
        maximum = _integer(objective["maximumPoints"], f"{ctx}.maximumPoints")
        per_round = None
        if "maximumPointsPerRound" in objective:
            per_round = _integer(objective["maximumPointsPerRound"], f"{ctx}.maximumPointsPerRound")
            if timing != "end-of-round" or per_round > maximum:
                raise ScenarioMissionError(f"{ctx} has an invalid maximumPointsPerRound")
        awards: list[ScenarioAward] = []
        covered: set[int] = set()
        for award_index, item in enumerate(_array(objective["awards"], f"{ctx}.awards")):
            award_ctx = f"{ctx}.awards[{award_index}]"
            award = _object(item, {"armyPoints", "objectivePoints", "condition"}, set(), award_ctx)
            army_points = _points(award["armyPoints"], supported_points, f"{award_ctx}.armyPoints")
            covered.update(army_points)
            objective_points = _integer(award["objectivePoints"], f"{award_ctx}.objectivePoints")
            if objective_points > (per_round if per_round is not None else maximum):
                cap_name = "maximumPointsPerRound" if per_round is not None else "maximumPoints"
                raise ScenarioMissionError(f"{award_ctx} exceeds the objective's {cap_name}")
            condition = _condition(award["condition"], f"{award_ctx}.condition")
            _validate_score_geometry(condition, army_points, configurations, award_ctx)
            if isinstance(condition, ElementStatusCount) and aggregation != "cumulative":
                raise ScenarioMissionError(
                    f"{award_ctx} per-element awards require cumulative aggregation"
                )
            awards.append(ScenarioAward(army_points, objective_points, condition))
        if covered != supported_points:
            raise ScenarioMissionError(
                f"{ctx}.awards must cover every configured Army Points value"
            )
        objectives.append(
            ScenarioObjective(
                identifier, name, references, timing, aggregation, maximum, tuple(awards), per_round
            )
        )

    rules: list[ScenarioRule] = []
    rule_ids: set[str] = set()
    for index, item in enumerate(_array(raw["rules"], f"{context}.rules", allow_empty=True)):
        ctx = f"{context}.rules[{index}]"
        rule = _object(
            item, {"id", "name", "paragraphs"}, {"definitionId", "skillIds", "specialists"}, ctx
        )
        identifier = _slug(rule["id"], f"{ctx}.id")
        _unique(identifier, rule_ids, ctx)
        definition_id = rule.get("definitionId")
        if definition_id is not None:
            validate_typed_domain_id(
                definition_id, expected_domain="rule", context=f"{ctx}.definitionId"
            )
        defined_skills = tuple(
            validate_typed_domain_id(value, expected_domain="skill", context=ctx)
            for value in _array(rule.get("skillIds", []), ctx, allow_empty=True)
        )
        specialists = rule.get("specialists", {})
        _object(specialists, set(), {"anyOfSkills"}, f"{ctx}.specialists")
        qualifiers = tuple(
            validate_typed_domain_id(value, expected_domain="skill", context=ctx)
            for value in _array(specialists.get("anyOfSkills", []), ctx, allow_empty=True)
        )
        rules.append(
            ScenarioRule(
                identifier,
                _text(rule["name"], f"{ctx}.name"),
                tuple(
                    _text(paragraph, f"{ctx}.paragraphs")
                    for paragraph in _array(
                        rule["paragraphs"], f"{ctx}.paragraphs", allow_empty=True
                    )
                ),
                definition_id,
                defined_skills,
                qualifiers,
            )
        )

    ends: list[ScenarioEndCondition] = []
    end_ids: set[str] = set()
    for index, item in enumerate(_array(raw["endConditions"], f"{context}.endConditions")):
        ctx = f"{context}.endConditions[{index}]"
        end = _object(item, {"id", "checkAt", "finishAt", "condition"}, set(), ctx)
        identifier = _slug(end["id"], f"{ctx}.id")
        _unique(identifier, end_ids, ctx)
        check_at = _choice(end["checkAt"], {"immediate", "tactical-phase", "end-of-round"}, ctx)
        finish_at = _choice(
            end["finishAt"], {"immediate", "end-of-player-turn", "end-of-round"}, ctx
        )
        condition = end["condition"]
        uses_minimum_vp = False
        if isinstance(condition, dict) and condition.get("kind") == "round-limit":
            condition = _object(condition, {"kind", "rounds"}, set(), f"{ctx}.condition")
            rounds = _integer(condition["rounds"], f"{ctx}.condition.rounds")
            if check_at != "end-of-round" or finish_at != "end-of-round":
                raise ScenarioMissionError(
                    f"{ctx} round-limit must be checked/finished at end-of-round"
                )
            description = None
        elif isinstance(condition, dict) and condition.get("kind") == "minimum-victory-points":
            condition = _object(condition, {"kind", "text"}, set(), f"{ctx}.condition")
            if any(size.minimum_victory_points is None for size in game_sizes):
                raise ScenarioMissionError(
                    f"{ctx} requires minimumVictoryPoints for every game size"
                )
            if check_at != "tactical-phase" or finish_at != "end-of-player-turn":
                raise ScenarioMissionError(
                    f"{ctx} minimum-victory-points requires Tactical Phase/Player Turn timing"
                )
            rounds = None
            description = _text(condition["text"], f"{ctx}.condition.text")
            uses_minimum_vp = True
        else:
            parsed = _condition(condition, f"{ctx}.condition")
            if not isinstance(parsed, ProseCondition):
                raise ScenarioMissionError(f"{ctx} score conditions cannot end a mission")
            rounds, description = None, parsed.text
        ends.append(
            ScenarioEndCondition(
                identifier, check_at, finish_at, rounds, description, uses_minimum_vp
            )
        )

    issues: list[ScenarioSourceIssue] = []
    issue_ids: set[str] = set()
    for index, item in enumerate(
        _array(raw["sourceIssues"], f"{context}.sourceIssues", allow_empty=True)
    ):
        ctx = f"{context}.sourceIssues[{index}]"
        issue = _object(
            item,
            {"id", "armyPoints", "status", "description"},
            {"objectiveId", "gameSizeField", "geometryElementIds"},
            ctx,
        )
        identifier = _slug(issue["id"], f"{ctx}.id")
        _unique(identifier, issue_ids, ctx)
        points = _points(issue["armyPoints"], supported_points, f"{ctx}.armyPoints")
        if sum(key in issue for key in ("objectiveId", "gameSizeField", "geometryElementIds")) != 1:
            raise ScenarioMissionError(
                f"{ctx} must target exactly one objectiveId, gameSizeField, or geometryElementIds"
            )
        objective_id = None
        game_size_field = None
        geometry_ids: tuple[str, ...] = ()
        if "objectiveId" in issue:
            objective_id = _slug(issue["objectiveId"], f"{ctx}.objectiveId")
            if objective_id not in objective_ids:
                raise ScenarioMissionError(f"{ctx} references unknown objective {objective_id!r}")
        elif "gameSizeField" in issue:
            game_size_field = _choice(
                issue["gameSizeField"], {"swc", "minimumVictoryPoints"}, f"{ctx}.gameSizeField"
            )
            if game_size_field == "minimumVictoryPoints" and any(
                size.minimum_victory_points is None and size.army_points in points
                for size in game_sizes
            ):
                raise ScenarioMissionError(f"{ctx} references absent minimumVictoryPoints")
        else:
            for configuration in configurations:
                if not set(points).intersection(configuration.army_points):
                    continue
                known = {element.id for element in configuration.geometry.elements}
                geometry_ids = _references(
                    issue["geometryElementIds"],
                    known,
                    f"{ctx}.geometryElementIds in {configuration.id}",
                )
        _choice(issue["status"], {"needs-verification"}, f"{ctx}.status")
        issues.append(
            ScenarioSourceIssue(
                identifier,
                points,
                objective_id,
                _text(issue["description"], f"{ctx}.description"),
                game_size_field=game_size_field,
                geometry_element_ids=geometry_ids,
            )
        )

    for objective in objectives:
        if objective.aggregation != "exclusive":
            continue
        for index, award in enumerate(objective.awards):
            condition = award.condition
            if not isinstance(condition, NumericRangeCondition):
                continue
            for other in objective.awards[index + 1 :]:
                other_condition = other.condition
                if (
                    not isinstance(other_condition, NumericRangeCondition)
                    or condition.metric != other_condition.metric
                ):
                    continue
                overlaps = (
                    condition.maximum is None or other_condition.minimum <= condition.maximum
                ) and (
                    other_condition.maximum is None or condition.minimum <= other_condition.maximum
                )
                shared = set(award.army_points).intersection(other.army_points)
                for point in shared if overlaps else ():
                    if not any(
                        issue.objective_id == objective.id and point in issue.army_points
                        for issue in issues
                    ):
                        raise ScenarioMissionError(
                            f"{context} exclusive objective {objective.id!r} has overlapping "
                            f"score ranges for {point} without a source issue"
                        )

    skill_ids = tuple(
        validate_typed_domain_id(value, expected_domain="skill", context="mission.skills")
        for value in _array(raw.get("skills", []), "mission.skills", allow_empty=True)
    )
    if len(set(skill_ids)) != len(skill_ids):
        raise ScenarioMissionError("mission.skills contains duplicate references")
    return ScenarioMission(
        tuple(sides),
        tuple(game_sizes),
        tuple(objectives),
        tuple(rules),
        tuple(ends),
        tuple(issues),
        skill_ids,
    )
