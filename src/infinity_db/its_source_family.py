"""Revision-tagged ITS source-family curation and deterministic projection.

Only the current revision is published. Earlier facts and source provenance
remain in the same curated file for a future, separate history capability.
"""
from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from typing import Any


def validate_reviewed_revision_evidence(document: dict[str, Any]) -> None:
    """Validate historical source observations without granting publication.

    Partial earlier-revision reviews are not equivalent to complete historical
    scenario projections. Their source- and language-specific facts stay in the
    single season source file but never enter the composed SQLite record set.
    """
    evidence = document.get("historicalEvidence")
    if evidence is None:
        return
    from .domain_slugs import require_domain_slug, validate_typed_domain_id

    if (
        not isinstance(evidence, dict)
        or set(evidence) != {"mode", "sources", "facts"}
        or evidence["mode"] != "review-only-not-projected"
    ):
        raise ValueError("ITS historical evidence must be explicitly review-only")
    season = document["scenarioCollection"]
    season_id = require_domain_slug(season["id"], context="historical evidence season")
    current = season["revision"]
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", current) is None:
        raise ValueError("ITS historical evidence needs a numeric current revision")
    current_version = tuple(int(p) for p in current.split("."))
    sources = evidence["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValueError("ITS historical evidence requires pinned older PDF sources")
    by_source: dict[str, dict[str, Any]] = {}
    editions: set[tuple[str, str]] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {
            "id", "revision", "language", "sha256", "pageCount", "localPath",
        }:
            raise ValueError("ITS historical evidence has invalid source descriptor")
        revision, language = source["revision"], source["language"]
        if (
            not isinstance(revision, str)
            or re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", revision) is None
            or tuple(int(p) for p in revision.split(".")) >= current_version
            or language not in {"en", "es"}
            or source["id"] != f"its-season-{season_id[4:]}-v{revision}-{language}-pdf"
            or (revision, language) in editions
            or not isinstance(source["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is None
            or type(source["pageCount"]) is not int or source["pageCount"] < 1
            or source["localPath"] != (
                f"data/pdf/legacy/its_{season_id[4:]}/"
                f"its-rules-season-{season_id[4:]}-v{revision}-{language}.pdf"
            )
        ):
            raise ValueError("ITS historical evidence source identity or pin is invalid")
        by_source[source["id"]] = source
        editions.add((revision, language))
    records = {record["id"] for record in document["records"]}
    facts = evidence["facts"]
    if not isinstance(facts, list) or not facts:
        raise ValueError("ITS historical evidence requires reviewed facts")
    seen_facts: set[str] = set()
    for fact in facts:
        required = {"id", "aspect", "observations", "review"}
        if not isinstance(fact, dict) or set(fact) not in (
            required | {"recordId"}, required | {"seasonId"},
        ):
            raise ValueError("ITS historical evidence fact has invalid fields")
        identity = require_domain_slug(fact["id"], context="historical fact id")
        if identity in seen_facts or not isinstance(fact["aspect"], str):
            raise ValueError("ITS historical evidence fact has invalid target")
        seen_facts.add(identity)
        if "recordId" in fact:
            record_id = fact["recordId"]
            if not isinstance(record_id, str) or record_id not in records:
                raise ValueError("ITS historical evidence fact has invalid target")
            kind = record_id.partition(":")[0]
            validate_typed_domain_id(
                record_id, expected_domain=kind, context="historical fact record",
            )
        elif fact["seasonId"] != season_id:
            raise ValueError("ITS historical evidence fact has invalid season target")
        require_domain_slug(fact["aspect"], context="historical fact aspect")
        review = fact["review"]
        if not isinstance(review, dict) or set(review) != {"status", "reviewedOn"}:
            raise ValueError("ITS historical fact requires review metadata")
        if review["status"] != "reviewed" or not isinstance(review["reviewedOn"], str):
            raise ValueError("ITS historical fact must be reviewed")
        try:
            if date.fromisoformat(review["reviewedOn"]).isoformat() != review["reviewedOn"]:
                raise ValueError("noncanonical review date")
        except ValueError as exc:
            raise ValueError("ITS historical fact needs ISO review date") from exc
        observations = fact["observations"]
        if not isinstance(observations, list) or not observations:
            raise ValueError("ITS historical fact needs source observations")
        seen_sources: set[str] = set()
        for observation in observations:
            if not isinstance(observation, dict) or set(observation) != {
                "sourceId", "page", "value",
            }:
                raise ValueError("ITS historical observation has invalid fields")
            source_id = observation["sourceId"]
            if (
                not isinstance(source_id, str)
                or source_id not in by_source or source_id in seen_sources
                or type(observation["page"]) is not int
                or not 1 <= observation["page"] <= by_source[source_id]["pageCount"]
                or not isinstance(observation["value"], str)
                or not observation["value"].strip()
            ):
                raise ValueError("ITS historical observation must be uniquely source-bound")
            seen_sources.add(source_id)


def project_its_source_family(
    document: dict[str, Any], *, revision: str | None = None,
) -> dict[str, Any]:
    """Project one tagged revision; older projections are internal, not served.

    Standalone single-revision fixtures remain supported for test/research builds.
    Normal curated-document and ITS semantics are validated by the caller.
    """
    validate_reviewed_revision_evidence(document)
    family = document.get("sourceFamily")
    current = document["scenarioCollection"]["revision"]
    if family is None:
        if revision is not None and revision != current:
            raise ValueError("Unregistered ITS source revision")
        return deepcopy({
            key: value for key, value in document.items()
            if key != "historicalEvidence"
        })
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
    result = deepcopy({
        key: value for key, value in document.items()
        if key not in {"sourceFamily", "historicalEvidence"}
    })
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
