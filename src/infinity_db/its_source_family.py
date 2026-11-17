"""Revision-tagged ITS source-family curation and deterministic projection.

Only the current revision is published. Earlier facts and source provenance
remain in the same curated file for a future, separate history capability.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def project_its_source_family(
    document: dict[str, Any], *, revision: str | None = None,
) -> dict[str, Any]:
    """Project one tagged revision; older projections are internal, not served.

    Standalone single-revision fixtures remain supported for test/research builds.
    Normal curated-document and ITS semantics are validated by the caller.
    """
    family = document.get("sourceFamily")
    current = document["scenarioCollection"]["revision"]
    if family is None:
        if revision is not None and revision != current:
            raise ValueError("Unregistered ITS source revision")
        return deepcopy(document)
    if not isinstance(family, dict) or set(family) != {
        "currentRevision", "historicalRevisions", "factRevisions",
        "historicalOverrides",
    } or family["currentRevision"] != current:
        raise ValueError("Invalid ITS source-family current revision")
    sources = document.get("sources")
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(source, dict)
                   or source.get("version") != current for source in sources)):
        raise ValueError("ITS source family current sources must be revision-matched")
    archives = family["historicalRevisions"]
    tags = family["factRevisions"]
    overrides = family["historicalOverrides"]
    if (not isinstance(archives, list) or not archives
            or not isinstance(tags, dict) or set(tags) != {"records", "seasonPolicies"}
            or not isinstance(overrides, list)):
        raise ValueError("Incomplete ITS source-family revision tags")

    archived: dict[str, dict[str, Any]] = {}
    for entry in archives:
        if not isinstance(entry, dict) or set(entry) != {
            "revision", "collection", "scenarioCollection", "sources",
            "originalDocumentSha256",
        }:
            raise ValueError("Invalid ITS archived source descriptor")
        value = entry["revision"]
        if (not isinstance(value, str) or not value or value == current
                or value in archived or not isinstance(entry["scenarioCollection"], dict)
                or entry["scenarioCollection"].get("revision") != value
                or entry["scenarioCollection"].get("id") != document["scenarioCollection"]["id"]
                or not isinstance(entry["sources"], list) or not entry["sources"]
                or not isinstance(entry["originalDocumentSha256"], str)
                or len(entry["originalDocumentSha256"]) != 64):
            raise ValueError("Conflicting ITS archived revision")
        if any(not isinstance(source, dict) or source.get("version") != value
               for source in entry["sources"]):
            raise ValueError("ITS archived source version mismatch")
        archived[value] = entry

    versions = {current, *archived}
    for category in ("records", "seasonPolicies"):
        authored = {item["id"] for item in document.get(category, [])}
        if len(authored) != len(document.get(category, [])):
            raise ValueError("Duplicate ITS source-family fact identity")
        entries = tags[category]
        if not isinstance(entries, dict) or set(entries) != authored:
            raise ValueError(f"ITS {category} requires exact version tags")
        for identity, applicable in entries.items():
            if (not isinstance(applicable, list) or not applicable
                    or any(not isinstance(value, str) for value in applicable)
                    or len(set(applicable)) != len(applicable)
                    or current not in applicable
                    or not set(applicable) <= versions):
                raise ValueError(f"Invalid ITS fact revision tags: {identity}")

    selected = current if revision is None else revision
    if selected not in versions:
        raise ValueError(f"Unregistered ITS source revision: {selected}")
    result = deepcopy({key: value for key, value in document.items() if key != "sourceFamily"})
    if selected != current:
        historical = archived[selected]
        for field in ("collection", "scenarioCollection", "sources"):
            result[field] = deepcopy(historical[field])
        for category in ("records", "seasonPolicies"):
            result[category] = [
                item for item in result.get(category, [])
                if selected in tags[category][item["id"]]
            ]
    selected_by_id = {
        category: {item["id"]: item for item in result.get(category, [])}
        for category in ("records", "seasonPolicies")
    }
    current_by_id = {
        category: {item["id"]: item for item in document.get(category, [])}
        for category in ("records", "seasonPolicies")
    }
    seen: set[tuple[str, str, str, str]] = set()
    for entry in overrides:
        if not isinstance(entry, dict) or set(entry) != {
            "revision", "category", "id", "fields",
        }:
            raise ValueError("Invalid ITS historical field override")
        r, category, identity, fields = (
            entry["revision"], entry["category"], entry["id"], entry["fields"],
        )
        if (r not in archived or category not in selected_by_id
                or identity not in tags[category] or r not in tags[category][identity]
                or not isinstance(fields, dict) or not fields):
            raise ValueError("ITS historical override has no tagged target")
        for path, value in fields.items():
            if (not isinstance(path, str) or not path
                    or any(not part for part in path.split("."))):
                raise ValueError("Invalid ITS historical fact path")
            key = (r, category, identity, path)
            if key in seen:
                raise ValueError("Overlapping ITS historical fact variants")
            seen.add(key)
            # No historical override may introduce an unreviewed field.
            node = current_by_id[category][identity]
            for component in path.split("."):
                if not isinstance(node, dict) or component not in node:
                    raise ValueError("ITS historical override targets missing current field")
                node = node[component]
            if r != selected:
                continue
            target = selected_by_id[category][identity]
            parts = path.split(".")
            for component in parts[:-1]:
                target = target[component]
            target[parts[-1]] = deepcopy(value)

    for historical_revision, descriptor in archived.items():
        members = {member["scenarioId"] for member in descriptor["scenarioCollection"]["members"]}
        tagged = {
            item["id"] for item in document["records"]
            if item["kind"] == "scenario"
            and historical_revision in tags["records"][item["id"]]
        }
        if members != tagged:
            raise ValueError("ITS archived membership differs from revision-tagged facts")
    if selected != current:
        source_ids = {source["id"] for source in result["sources"]}
        if any(citation["sourceId"] not in source_ids
               for item in (*result["records"], *result["seasonPolicies"])
               for citation in item["citations"]):
            raise ValueError("ITS historical citation is not source-bound")
        if any(policy["applicability"]["revision"] != selected
               for policy in result["seasonPolicies"]):
            raise ValueError("ITS historical policy revision mismatch")
    return result
