"""Build-time, version-pinned reuse of ITS scenario definitions.

The library is an authoring input, never a runtime database dependency. A
season supplies its own citations and review for every reused publication.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
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


def materialize_shared_scenarios(
    document: dict[str, Any], library_path: Path | None,
) -> dict[str, Any]:
    """Expand explicit memberships before normal curated and scenario validation."""
    declaration = document.get("sharedScenarioLibrary")
    if declaration is None:
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
    _exact(library, {"format", "formatVersion", "id", "definitions"},
           "shared scenario library")
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
        origin = _exact(
            entry["origin"],
            {"sourceCollectionId", "seasonId", "revision", "sourceIds"},
            "shared scenario origin",
        )
        _text(origin["sourceCollectionId"], "shared scenario origin collection")
        require_domain_slug(origin["seasonId"], context="shared scenario origin season")
        _text(origin["revision"], "shared scenario origin revision")
        sources = origin["sourceIds"]
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(s, str) or not s.strip() for s in sources)
                or len(set(sources)) != len(sources)):
            raise ValueError("Shared scenario origin requires distinct source identities")
        record = entry["record"]
        if (not isinstance(record, dict) or record.get("id") != identifier
                or record.get("kind") != "scenario"
                or record.get("composition", {}).get("role") != "definition"
                or origin["seasonId"] not in record.get("scope", {}).get("seasons", [])):
            raise ValueError("Shared scenario definition has incompatible record identity or scope")
        _citations(record.get("citations"), set(sources), "shared scenario origin")
        if record.get("review", {}).get("status") != "reviewed":
            raise ValueError("Shared scenario origin requires reviewed evidence")
        if not isinstance(entry["components"], list):
            raise ValueError("Shared scenario components must be an array")
        for component in entry["components"]:
            if not isinstance(component, dict) or "version" not in component:
                raise ValueError("Shared scenario components require pinned versions")
            _text(component["version"], "shared scenario component version")
            validate_typed_domain_id(
                component.get("id"), expected_domain=component.get("kind"),
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
        if not isinstance(binding["review"], dict) or (
            binding["review"].get("status") != "reviewed"
        ):
            raise ValueError("Shared scenario season membership requires reviewed evidence")
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
    if not components["definitions"]:
        result.pop("scenarioComponents")
    return result
