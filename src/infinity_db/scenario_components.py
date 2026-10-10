"""Resolve explicitly identified reusable scenario components at build time.

Semantic Rules and Skills use the normal curated record envelope. Geometry,
setups, objectives, and endings are typed reusable payloads in the same collection.
Resolution preserves ordering and provenance and never matches display names.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .domain_slugs import validate_typed_domain_id
from .scenario_geometry import parse_scenario_geometry
from .scenario_mission import _choice, _condition, _integer

COMPONENT_KINDS = frozenset({"setup", "geometry", "objective", "end-condition"})


def _object(value: Any, required: set[str], optional: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or required - value.keys() or value.keys() - required - optional:
        raise ValueError(
            f"{context} must contain {sorted(required)} and only optional {sorted(optional)}"
        )
    return value


def _array(value: Any, context: str, *, empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not value and not empty):
        raise ValueError(f"{context} must be {'an' if empty else 'a non-empty'} array")
    return value


def _ids(value: Any, kind: str, context: str, *, empty: bool = False) -> list[str]:
    result = [
        validate_typed_domain_id(item, expected_domain=kind, context=context)
        for item in _array(value, context, empty=empty)
    ]
    if len(result) != len(set(result)):
        raise ValueError(f"{context} contains duplicate references")
    return result


def scenario_typed_id(value: str) -> str:
    """Resolve a scenario's simple slug or typed identity centrally."""
    if not isinstance(value, str):
        raise ValueError("scenario reference must be a slug or typed identity")
    identifier = value if value.startswith("scenario:") else f"scenario:{value}"
    return validate_typed_domain_id(
        identifier, expected_domain="scenario", context="scenario reference"
    )


class ScenarioComponents:
    """One collection's validated, explicitly scoped authoring library."""

    def __init__(self, document: dict[str, Any]) -> None:
        self.used: set[str] = set()
        self.records: dict[str, dict[str, Any]] = {}
        for record in document.get("records", []):
            if record["id"] in self.records:
                raise ValueError(f"Duplicate semantic record {record['id']!r}")
            self.records[record["id"]] = record
        self.definitions: dict[str, dict[str, Any]] = {}
        library = document.get("scenarioComponents")
        if library is None:
            return
        library = _object(library, {"formatVersion", "definitions"}, set(), "scenarioComponents")
        if type(library["formatVersion"]) is not int or library["formatVersion"] != 1:
            raise ValueError("Unsupported scenarioComponents formatVersion")
        for entry in _array(library["definitions"], "scenarioComponents.definitions"):
            entry = _object(
                entry,
                {"id", "kind", "payload", "citations", "scenarios"},
                set(),
                "scenario component",
            )
            kind = entry["kind"]
            if not isinstance(kind, str) or kind not in COMPONENT_KINDS:
                raise ValueError(f"Unsupported scenario component kind {kind!r}")
            identifier = validate_typed_domain_id(
                entry["id"], expected_domain=kind, context="scenario component.id"
            )
            if identifier in self.definitions:
                raise ValueError(f"Duplicate scenario component {identifier!r}")
            self._scope(entry["scenarios"], "scenario component.scenarios")
            _array(entry["citations"], f"{identifier}.citations")
            self.definitions[identifier] = entry
        # Validate even unused references, cycles, and geometry. Other component
        # payloads are validated in their complete scenario context on composition.
        for entry in self.definitions.values():
            for scenario_id in entry["scenarios"]:
                payload = self.resolve({"ref": entry["id"]}, entry["kind"], scenario_id)
                if entry["kind"] == "geometry":
                    parse_scenario_geometry(payload)

    def _scope(self, value: Any, context: str) -> list[str]:
        identifiers = _ids(value, "scenario", context)
        for identifier in identifiers:
            if self.records.get(identifier, {}).get("kind") != "scenario":
                raise ValueError(f"{context} references unknown scenario {identifier!r}")
        return identifiers

    def record(self, identifier: str, kind: str, scenario_id: str) -> dict[str, Any]:
        validate_typed_domain_id(
            identifier, expected_domain=kind, context="scenario record reference"
        )
        record = self.records.get(identifier)
        if record is None or record.get("kind") != kind:
            raise ValueError(f"Unknown {kind} definition {identifier!r}")
        scope = record.get("scope", {}).get("scenarios")
        if scope is None or scenario_id not in scope:
            raise ValueError(f"Definition {identifier!r} is not applicable to {scenario_id!r}")
        return record

    def resolve(
        self, value: Any, kind: str, scenario_id: str, stack: tuple[str, ...] = ()
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{kind} inclusion must be an object")
        if "ref" not in value:
            return deepcopy(value)
        inclusion = _object(
            value, {"ref"}, {"gameSizeOverrides"} if kind == "setup" else set(), f"{kind} inclusion"
        )
        identifier = validate_typed_domain_id(
            inclusion["ref"], expected_domain=kind, context=f"{kind} inclusion.ref"
        )
        if identifier in stack:
            raise ValueError(
                f"Cyclic scenario component reference: {' -> '.join((*stack, identifier))}"
            )
        entry = self.definitions.get(identifier)
        if entry is None or entry["kind"] != kind:
            raise ValueError(f"Unknown {kind} component {identifier!r}")
        if scenario_id not in entry["scenarios"]:
            raise ValueError(f"Component {identifier!r} is not applicable to {scenario_id!r}")
        self.used.add(identifier)
        result = self.resolve(entry["payload"], kind, scenario_id, (*stack, identifier))
        if kind == "setup":
            _object(result, {"sides", "gameSizes"}, set(), "setup component")
            _array(result["sides"], "setup sides")
            _array(result["gameSizes"], "setup game sizes")
        elif kind == "objective":
            _object(
                result,
                {"id", "name", "sideIds", "timing", "aggregation", "maximumPoints", "awards"},
                {"maximumPointsPerRound"},
                "objective component",
            )
            for award in _array(result["awards"], "objective awards"):
                _object(
                    award, {"armyPoints", "objectivePoints", "condition"}, set(), "objective award"
                )
                _condition(award["condition"], "objective component condition")
                _integer(award["objectivePoints"], "objective points")
        elif kind == "end-condition":
            _object(result, {"id", "checkAt", "finishAt", "condition"}, set(), "ending component")
            condition = result["condition"]
            if not isinstance(condition, dict):
                raise ValueError("Ending component condition must be an object")
            if condition.get("kind") == "round-limit":
                _object(condition, {"kind", "rounds"}, set(), "round-limit component")
                _integer(condition["rounds"], "round limit")
            elif condition.get("kind") == "minimum-victory-points":
                _object(condition, {"kind", "text"}, set(), "minimum-VP component")
                if not isinstance(condition["text"], str) or not condition["text"].strip():
                    raise ValueError("Minimum-VP component requires procedure text")
            elif (
                not isinstance(condition.get("kind"), str) or condition["kind"] != "reviewed-prose"
            ):
                raise ValueError("Unsupported ending component condition")
            else:
                _condition(condition, "ending component")
            _choice(
                result["checkAt"], {"immediate", "tactical-phase", "end-of-round"}, "ending checkAt"
            )
            _choice(
                result["finishAt"],
                {"immediate", "end-of-player-turn", "end-of-round"},
                "ending finishAt",
            )
        if "gameSizeOverrides" in inclusion:
            rows = {row["armyPoints"]: row for row in result["gameSizes"]}
            seen: set[int] = set()
            for override in _array(inclusion["gameSizeOverrides"], "gameSizeOverrides", empty=True):
                override = _object(
                    override, {"armyPoints"}, {"swc", "minimumVictoryPoints"}, "game-size override"
                )
                point = override["armyPoints"]
                if type(point) is not int or point not in rows or point in seen:
                    raise ValueError("Game-size override has unknown/duplicate Army Points")
                if len(override) == 1:
                    raise ValueError("Game-size override must change a declared field")
                seen.add(point)
                rows[point].update(deepcopy(override))
        return result

    def compose(self, record: dict[str, Any]) -> dict[str, Any]:
        if (
            record.get("kind") != "scenario"
            or record.get("facts", {}).get("definitionVersion") != 2
        ):
            return deepcopy(record)
        self.used.clear()
        scenario_id = record["id"]
        facts = _object(
            record["facts"],
            {"definitionVersion", "configurations", "mission"},
            {"relatedCategories"},
            f"{scenario_id}.facts",
        )
        result = deepcopy(record)
        configurations = []
        for config in _array(facts["configurations"], "scenario configurations"):
            config = _object(
                config, {"id", "armyPoints", "geometry"}, set(), "scenario configuration"
            )
            geometry = self.resolve(config["geometry"], "geometry", scenario_id)
            # Title is presentation owned by the including scenario, not geometry.
            geometry["title"] = record["name"]
            configurations.append({**deepcopy(config), "geometry": geometry})
        raw = _object(
            facts["mission"],
            {"setup", "objectives", "rules", "endConditions", "sourceIssues"},
            set(),
            f"{scenario_id}.mission",
        )
        setup = _object(
            self.resolve(raw["setup"], "setup", scenario_id),
            {"sides", "gameSizes"},
            set(),
            "scenario setup",
        )
        rules = []
        skills: list[str] = []
        for inclusion in _array(raw["rules"], "scenario rules", empty=True):
            inclusion = _object(
                inclusion, {"id", "ref"}, {"addSkills", "removeSkills"}, "rule inclusion"
            )
            rule = self.record(inclusion["ref"], "rule", scenario_id)
            rule_facts = rule["facts"]
            skill_ids = _ids(
                rule_facts.get("definesSkills", []), "skill", "defined Skills", empty=True
            )
            for skill_id in skill_ids:
                self.record(skill_id, "skill", scenario_id)
                if skill_id not in skills:
                    skills.append(skill_id)
            compiled = {
                "id": inclusion["id"],
                "name": rule["name"],
                "paragraphs": deepcopy(
                    rule_facts.get("effects", []) + rule_facts.get("restrictions", [])
                ),
                "definitionId": rule["id"],
                "skillIds": skill_ids,
            }
            base = rule_facts.get("specialists")
            if base is not None:
                base = _object(base, {"anyOfSkills"}, set(), "Specialist baseline")
                qualifying = _ids(base["anyOfSkills"], "skill", "Specialist baseline.anyOfSkills")
                adds = _ids(inclusion.get("addSkills", []), "skill", "addSkills", empty=True)
                removes = _ids(
                    inclusion.get("removeSkills", []), "skill", "removeSkills", empty=True
                )
                if set(adds).intersection(qualifying) or set(adds).intersection(removes):
                    raise ValueError("Specialist additions conflict with baseline or removals")
                if set(removes) - set(qualifying):
                    raise ValueError("Specialist removals must reference baseline qualifiers")
                qualifying = [item for item in qualifying if item not in removes] + adds
                if not qualifying:
                    raise ValueError("Specialist inclusion must retain at least one qualifier")
                for skill_id in qualifying:
                    qualifier = self.records.get(skill_id, {})
                    scope = qualifier.get("scope", {}).get("scenarios")
                    if qualifier.get("kind") != "skill" or (
                        scope is not None and scenario_id not in scope
                    ):
                        raise ValueError(f"Unknown Specialist Skill {skill_id!r}")
                compiled["specialists"] = {"anyOfSkills": qualifying}
            elif "addSkills" in inclusion or "removeSkills" in inclusion:
                raise ValueError("Skill-list overrides require a Specialist rule")
            rules.append(compiled)
        result["facts"] = {
            **deepcopy(facts),
            "definitionVersion": 1,
            "configurations": configurations,
            "mission": {
                **setup,
                "rules": rules,
                "skills": skills,
                "objectives": [
                    self.resolve(item, "objective", scenario_id)
                    for item in _array(raw["objectives"], "objectives")
                ],
                "endConditions": [
                    self.resolve(item, "end-condition", scenario_id)
                    for item in _array(raw["endConditions"], "end conditions")
                ],
                "sourceIssues": deepcopy(raw["sourceIssues"]),
            },
        }
        result["facts"]["componentSources"] = [
            {"id": entry["id"], "citations": deepcopy(entry["citations"])}
            for entry in self.definitions.values()
            if entry["id"] in self.used
        ]
        return result


def compose_scenario_record(record: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    """Compose one source record without mutating its maintained definitions."""
    return ScenarioComponents(document).compose(record)


def compose_scenario_document(document: dict[str, Any]) -> dict[str, Any]:
    """Materialize scenario authoring references into self-contained runtime payloads."""
    registry = ScenarioComponents(document)
    result = deepcopy(document)
    result["records"] = [registry.compose(record) for record in document["records"]]
    return result
