"""Build-time, version-pinned reuse of ITS scenario definitions.

The library is an authoring input, never a runtime database dependency. A
season supplies its own citations and review for every reused publication.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from .domain_slugs import require_domain_slug, validate_typed_domain_id

LIBRARY_FORMAT = "InfinityDB shared scenario library"
OVERRIDE_FIELDS = frozenset({
    "summary",
    "facts.playRequirements.classifiedObjectives",
    "facts.playRequirements.tacticalObjectives",
    "facts.playRequirements.hvts",
    "facts.playRequirements.sharedClassifiedObjectivesPerRound",
})
SKILL_OVERRIDE_FIELDS = frozenset({
    "skillFacts.requirements", "skillFacts.effects", "skillFacts.restrictions",
})


def _exact(value: Any, keys: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{context} requires exactly {sorted(keys)}")
    return value


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{context} requires non-empty trimmed text")
    return value


def _citations(value: Any, source_ids: set[str], context: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{context} requires source citations")
    for citation in value:
        if not isinstance(citation, dict) or citation.get("sourceId") not in source_ids:
            raise ValueError(f"{context} references a source outside its publication")
    return deepcopy(value)


def _reviewed(value: Any, context: str) -> dict[str, str]:
    review = _exact(value, {"status", "reviewedOn"}, context)
    if review["status"] != "reviewed":
        raise ValueError(f"{context} requires reviewed evidence")
    reviewed_on = _text(review["reviewedOn"], f"{context}.reviewedOn")
    try:
        if date.fromisoformat(reviewed_on).isoformat() != reviewed_on:
            raise ValueError("noncanonical date")
    except ValueError as exc:
        raise ValueError(f"{context} requires an ISO review date") from exc
    return review


def _origin(value: Any, context: str) -> dict[str, Any]:
    origin = _exact(
        value, {"sourceCollectionId", "seasonId", "revision", "sourceIds"}, context,
    )
    _text(origin["sourceCollectionId"], f"{context}.sourceCollectionId")
    require_domain_slug(origin["seasonId"], context=f"{context}.seasonId")
    _text(origin["revision"], f"{context}.revision")
    sources = origin["sourceIds"]
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(source, str) or not source.strip() for source in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError(f"{context} requires distinct source IDs")
    return origin


def _apply_overrides(record: dict[str, Any], entries: Any) -> None:
    if not isinstance(entries, list):
        raise ValueError("Scenario reuse overrides must be an array")
    seen: set[str] = set()
    for entry in entries:
        _exact(entry, {"target", "field", "value"}, "scenario reuse override")
        if entry["target"] != record["id"]:
            raise ValueError("Scenario reuse override has unknown target")
        field = entry["field"]
        if field not in OVERRIDE_FIELDS:
            raise ValueError(f"Unsupported scenario reuse override field {field!r}")
        if field in seen:
            raise ValueError(f"Conflicting scenario reuse overrides for {field!r}")
        seen.add(field)
        node: Any = record
        segments = field.split(".")
        for segment in segments[:-1]:
            if not isinstance(node, dict) or segment not in node:
                raise ValueError(f"Scenario reuse override has missing field {field!r}")
            node = node[segment]
        if not isinstance(node, dict) or segments[-1] not in node:
            raise ValueError(f"Scenario reuse override has missing field {field!r}")
        value = entry["value"]
        if field == "summary":
            _text(value, field)
        elif type(value) is not int or value < 0:
            raise ValueError(f"Scenario reuse override {field!r} must be a non-negative integer")
        node[segments[-1]] = deepcopy(value)


def _bind_skill_overrides(
    scenarios: dict[str, dict[str, Any]], available: list[str],
    skill_id: str, version: str, entries: Any,
) -> None:
    """Attach narrowly scoped, reviewed Skill variants to exact scenario actions."""
    if not isinstance(entries, list):
        raise ValueError("Shared Skill overrides must be an array")
    seen: set[tuple[str, str, str]] = set()
    for entry in entries:
        _exact(entry, {"scenarioId", "ruleId", "field", "value"}, "shared Skill override")
        scenario_id = validate_typed_domain_id(
            entry["scenarioId"], expected_domain="scenario", context="Skill override",
        )
        rule_id = require_domain_slug(entry["ruleId"], context="Skill override rule")
        field = entry["field"]
        if scenario_id not in available or field not in SKILL_OVERRIDE_FIELDS:
            raise ValueError("Shared Skill override has unsupported scope or field")
        key = (scenario_id, rule_id, field)
        if key in seen:
            raise ValueError("Conflicting shared Skill overrides for one action field")
        seen.add(key)
        values = entry["value"]
        if (not isinstance(values, list)
                or (not values and field != "skillFacts.restrictions")):
            raise ValueError(f"Shared Skill override {field!r} requires an array of prose")
        for value in values:
            _text(value, f"shared Skill override {field}")
        rules = [
            rule for rule in scenarios[scenario_id]["facts"]["mission"]["rules"]
            if rule.get("id") == rule_id
            and rule.get("skillDefinition") == {"ref": skill_id, "version": version}
        ]
        if len(rules) != 1:
            raise ValueError("Shared Skill override references unknown action or Skill")
        rules[0].setdefault("skillOverrides", []).append({
            "field": field, "value": deepcopy(values),
        })


def materialize_shared_scenarios(
    document: dict[str, Any], library_path: Path | None,
) -> dict[str, Any]:
    """Expand explicit memberships before normal curated and scenario validation."""
    declaration = document.get("sharedScenarioLibrary")
    if declaration is None:
        if "sharedSkillBindings" in document or "sharedSeasonSkillBindings" in document:
            raise ValueError("Shared Skill bindings require a pinned shared scenario library")
        if library_path is not None:
            raise ValueError("Unreferenced shared scenario library supplied")
        return document
    _exact(declaration, {"id", "sha256"}, "sharedScenarioLibrary")
    library_id = require_domain_slug(declaration["id"], context="shared scenario library")
    if library_path is None:
        raise ValueError("Shared scenario library path is required")
    raw = library_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != declaration["sha256"]:
        raise ValueError("Shared scenario library SHA-256 does not match pinned source")
    try:
        library = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Shared scenario library is not valid JSON") from exc
    if (not isinstance(library, dict)
            or set(library) - {"format", "formatVersion", "id", "definitions", "skills"}
            or {"format", "formatVersion", "id", "definitions"} - set(library)):
        raise ValueError("Shared scenario library has unsupported fields")
    if library["format"] != LIBRARY_FORMAT or type(library["formatVersion"]) is not int or (
        library["formatVersion"] != 1 or library["id"] != library_id
    ):
        raise ValueError("Unsupported shared scenario library identity or format")
    if not isinstance(library["definitions"], list):
        raise ValueError("Shared scenario definitions must be an array")

    definitions: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in library["definitions"]:
        _exact(entry, {"id", "version", "origin", "record", "components"},
               "shared scenario definition")
        identifier = validate_typed_domain_id(
            entry["id"], expected_domain="scenario", context="shared scenario definition"
        )
        version = _text(entry["version"], "shared scenario definition version")
        key = (identifier, version)
        if key in definitions:
            raise ValueError(f"Duplicate shared scenario definition {key!r}")
        origin = _origin(entry["origin"], "shared scenario origin")
        sources = origin["sourceIds"]
        record = entry["record"]
        if (not isinstance(record, dict) or record.get("id") != identifier
                or record.get("kind") != "scenario"
                or record.get("composition", {}).get("role") != "definition"
                or origin["seasonId"] not in record.get("scope", {}).get("seasons", [])):
            raise ValueError("Shared scenario definition has incompatible record identity or scope")
        _citations(record.get("citations"), set(sources), "shared scenario origin")
        _reviewed(record.get("review"), "Shared scenario origin")
        if not isinstance(entry["components"], list):
            raise ValueError("Shared scenario components must be an array")
        for component in entry["components"]:
            if not isinstance(component, dict) or "version" not in component:
                raise ValueError("Shared scenario components require pinned versions")
            _text(component["version"], "shared scenario component version")
            kind = component.get("kind")
            if not isinstance(kind, str):
                raise ValueError("Shared scenario component kind must be a string")
            validate_typed_domain_id(
                component.get("id"), expected_domain=kind,
                context="shared scenario component",
            )
            _citations(component.get("citations"), set(sources), "shared component origin")
            if identifier not in component.get("scenarios", []):
                raise ValueError("Shared scenario component has incompatible scenario scope")
        definitions[key] = entry

    result = deepcopy(document)
    season = result["scenarioCollection"]["id"]
    sources = {item["id"] for item in result["sources"]}
    existing_ids = {record["id"] for record in result["records"]}
    components = result.setdefault("scenarioComponents", {"formatVersion": 1, "definitions": []})
    if not isinstance(components, dict) or components.get("formatVersion") != 1:
        raise ValueError("Incompatible season scenario component library")
    component_ids = {item["id"] for item in components["definitions"]}
    for member in result["scenarioCollection"]["members"]:
        if "sharedDefinition" not in member:
            continue
        _exact(member, {"scenarioId", "sharedDefinition"}, "shared scenario membership")
        identity = validate_typed_domain_id(
            member["scenarioId"], expected_domain="scenario", context="shared scenario membership"
        )
        binding = _exact(
            member["sharedDefinition"],
            {"version", "citations", "review", "componentCitations", "overrides"},
            "shared scenario binding",
        )
        entry = definitions.get((identity, _text(binding["version"], "shared definition version")))
        if entry is None:
            raise ValueError(f"Unknown pinned shared scenario definition {identity!r}")
        if identity in existing_ids:
            raise ValueError(f"Shared scenario {identity!r} conflicts with a local record")
        existing_ids.add(identity)
        record = deepcopy(entry["record"])
        record["scope"]["seasons"] = [season]
        record["citations"] = _citations(binding["citations"], sources, "season scenario")
        _reviewed(binding["review"], "Shared scenario season membership")
        record["review"] = deepcopy(binding["review"])
        _apply_overrides(record, binding["overrides"])
        record["sharedDefinition"] = {
            "libraryId": library_id, "id": identity, "version": entry["version"],
            "origin": deepcopy(entry["origin"]),
        }

        citation_map = binding["componentCitations"]
        if not isinstance(citation_map, dict):
            raise ValueError("Shared scenario component citations must be an object")
        expected_components = {item["id"] for item in entry["components"]}
        if set(citation_map) != expected_components:
            raise ValueError("Shared component citations must match pinned component identities")
        for component in entry["components"]:
            comp_id = validate_typed_domain_id(
                component["id"], expected_domain=component["kind"],
                context="shared scenario component",
            )
            if comp_id in component_ids:
                raise ValueError(f"Shared component {comp_id!r} conflicts with a local component")
            component_ids.add(comp_id)
            materialized = deepcopy(component)
            materialized["scenarios"] = [identity]
            materialized["citations"] = _citations(
                citation_map[comp_id], sources, f"season component {comp_id}"
            )
            components["definitions"].append(materialized)
        result["records"].append(record)
        member.clear()
        member["scenarioId"] = identity

    # Skills are independent reusable components. Season-specific bindings own
    # applicability, review, and citations; library origin is only provenance.
    skill_definitions: dict[tuple[str, str], dict[str, Any]] = {}
    skills = library.get("skills", [])
    if not isinstance(skills, list):
        raise ValueError("Shared scenario library Skills must be an array")
    for entry in skills:
        _exact(entry, {"id", "version", "origin", "payload", "citations", "review"},
               "shared Skill definition")
        skill_id = validate_typed_domain_id(
            entry["id"], expected_domain="skill", context="shared Skill definition",
        )
        version = _text(entry["version"], "shared Skill version")
        key = (skill_id, version)
        if key in skill_definitions:
            raise ValueError(f"Duplicate shared Skill definition {key!r}")
        origin = _origin(entry["origin"], "shared Skill origin")
        _citations(entry["citations"], set(origin["sourceIds"]), "shared Skill origin")
        _reviewed(entry["review"], "Shared Skill origin")
        if not isinstance(entry["payload"], dict):
            raise ValueError("Shared Skill payload must be an object")
        skill_definitions[key] = entry

    bindings = result.pop("sharedSkillBindings", [])
    if not isinstance(bindings, list):
        raise ValueError("Shared Skill bindings must be an array")
    bound_ids: set[str] = set()
    scenarios = {record["id"]: record for record in result["records"]}
    for binding in bindings:
        fields = {"id", "version", "scenarios", "citations", "review"}
        if (not isinstance(binding, dict) or fields - binding.keys()
                or binding.keys() - (fields | {"overrides"})):
            raise ValueError(
                "Shared Skill binding requires identity, sources and optional overrides"
            )
        skill_id = validate_typed_domain_id(
            binding["id"], expected_domain="skill", context="shared Skill binding",
        )
        version = _text(binding["version"], "shared Skill binding version")
        entry = skill_definitions.get((skill_id, version))
        if entry is None:
            raise ValueError(f"Unknown pinned shared Skill {skill_id!r}")
        if skill_id in bound_ids or skill_id in component_ids:
            raise ValueError(f"Conflicting shared Skill binding {skill_id!r}")
        bound_ids.add(skill_id)
        component_ids.add(skill_id)
        available = binding["scenarios"]
        if (not isinstance(available, list) or not available
                or any(not isinstance(ref, str) for ref in available)
                or len(available) != len(set(available))):
            raise ValueError("Shared Skill scenario applicability must be distinct and nonempty")
        for ref in available:
            validate_typed_domain_id(
                ref, expected_domain="scenario", context="shared Skill scenario applicability",
            )
            if ref not in scenarios:
                raise ValueError(f"Shared Skill references unknown season scenario {ref!r}")
            uses = [
                rule for rule in scenarios[ref]["facts"]["mission"]["rules"]
                if rule.get("skillDefinition") == {"ref": skill_id, "version": version}
            ]
            if not uses:
                raise ValueError(f"Shared Skill binding is unused by scenario {ref!r}")
        _reviewed(binding["review"], "Shared Skill season membership")
        _bind_skill_overrides(
            scenarios, available, skill_id, version, binding.get("overrides", []),
        )
        materialized = {
            "id": skill_id, "kind": "skill", "version": version,
            "payload": deepcopy(entry["payload"]),
            "scenarios": deepcopy(available),
            "citations": _citations(binding["citations"], sources, "season Skill"),
            "origin": deepcopy(entry["origin"]),
            "review": deepcopy(binding["review"]),
        }
        components["definitions"].append(materialized)
    season_bindings = result.pop("sharedSeasonSkillBindings", [])
    if not isinstance(season_bindings, list):
        raise ValueError("Shared season Skill bindings must be an array")
    for binding in season_bindings:
        _exact(
            binding,
            {"id", "version", "name", "summary", "category", "applicability",
             "citations", "review"},
            "shared season Skill membership",
        )
        skill_id = validate_typed_domain_id(
            binding["id"], expected_domain="skill", context="season Skill",
        )
        version = _text(binding["version"], "season Skill version")
        entry = skill_definitions.get((skill_id, version))
        if entry is None:
            raise ValueError(f"Unknown pinned season Skill {skill_id!r}")
        if skill_id in component_ids or skill_id in existing_ids:
            raise ValueError(f"Conflicting shared season Skill {skill_id!r}")
        component_ids.add(skill_id)
        existing_ids.add(skill_id)
        name = _text(binding["name"], "season Skill name")
        summary = _text(binding["summary"], "season Skill summary")
        category = binding["category"]
        if category not in {"common-skill", "special-skill"}:
            raise ValueError("Shared season Skill must be Common or Special")
        applicability = _exact(
            binding["applicability"], {"context", "revision"},
            "season Skill applicability",
        )
        if (
            applicability["context"] not in {"season", "team-ops-extra"}
            or applicability["revision"] != result["scenarioCollection"]["revision"]
        ):
            raise ValueError("Shared season Skill applicability must match selected revision")
        payload = _exact(
            entry["payload"], {"skillTypeIds", "skillFacts"}, "shared season Skill payload",
        )
        facts = payload["skillFacts"]
        if (
            not isinstance(facts, dict)
            or {"requirements", "effects"} - set(facts)
            or set(facts) - {"requirements", "effects", "restrictions", "clarifications"}
        ):
            raise ValueError("Shared season Skill has unsupported facts")
        materialized = {
            "id": skill_id, "kind": "skill", "name": name, "summary": summary,
            "composition": {"role": "definition"},
            "scope": {"game": "N5", "seasons": [season]},
            "facts": {
                "category": category,
                "typeIds": deepcopy(payload["skillTypeIds"]),
                **deepcopy(facts),
                "applicability": deepcopy(applicability),
                "restrictions": deepcopy(facts.get("restrictions", [])),
            },
            "labelIds": [],
            "citations": _citations(binding["citations"], sources, "season-wide Skill"),
            "review": deepcopy(_reviewed(binding["review"], "Shared season Skill")),
            "sharedSkill": {
                "id": skill_id, "version": version, "origin": deepcopy(entry["origin"]),
            },
        }
        result["records"].append(materialized)
    if not components["definitions"]:
        result.pop("scenarioComponents")
    # Maintain the source family's scenario ordering when definitions are
    # replaced by library memberships; append-only imports would otherwise
    # change current and historical projections.
    member_order = {
        member["scenarioId"]: index
        for index, member in enumerate(result["scenarioCollection"]["members"])
    }
    scenario_records = iter(sorted(
        (record for record in result["records"] if record["kind"] == "scenario"),
        key=lambda record: member_order.get(record["id"], len(member_order)),
    ))
    result["records"] = [
        next(scenario_records) if record["kind"] == "scenario" else record
        for record in result["records"]
    ]
    return result
