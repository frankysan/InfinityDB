"""Validation of authored, source-selected FAQ/errata facts.

This module validates the curation contract and selects reviewed, explicitly
applicable FAQ records at query time. It never rewrites canonical definitions,
invents season applicability, or chooses a source by publication recency.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .domain_slugs import validate_typed_domain_id


def _object(value: object, required: set[str], optional: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or required - value.keys() or value.keys() - required - optional:
        raise ValueError(f"{context}: expected {sorted(required)}, optional {sorted(optional)}")
    return value


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{context}: expected non-empty trimmed text")
    return value


def _date(value: object, context: str) -> str:
    text = _text(value, context)
    try:
        if date.fromisoformat(text).isoformat() != text:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"{context}: expected valid YYYY-MM-DD date") from exc
    return text


def _ids(
    value: object, context: str, *, domain: str | None = None, empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or (not value and not empty):
        raise ValueError(f"{context}: expected {'possibly empty' if empty else 'non-empty'} array")
    result: list[str] = []
    for index, item in enumerate(value):
        text = _text(item, f"{context}[{index}]")
        prefix = domain or text.split(":", 1)[0]
        validate_typed_domain_id(text, expected_domain=prefix, context=f"{context}[{index}]")
        result.append(text)
    if len(set(result)) != len(result):
        raise ValueError(f"{context}: duplicate identities")
    return result


def _citation(value: object, context: str, citations: list[dict[str, Any]]) -> tuple[str, int]:
    obj = _object(value, {"sourceId", "page"}, set(), context)
    source_id = _text(obj["sourceId"], f"{context}.sourceId")
    page = obj["page"]
    if type(page) is not int or page < 1:
        raise ValueError(f"{context}.page: expected positive printed page")
    if not any(c.get("sourceId") == source_id and c.get("page") == page for c in citations):
        raise ValueError(f"{context}: source/page is not in the record citations")
    return source_id, page


def validate_faq_ruling_facts(
    facts: object,
    *,
    record_id: str,
    record_role: str,
    citations: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    context: str,
) -> None:
    """Fail closed on implicit scope, document selection or lost original provenance."""
    if record_role != "definition":
        raise ValueError(
            f"{context}: FAQ rulings require a definition; cross-posted evidence is separate"
        )
    obj = _object(
        facts,
        {"question", "answer", "topicIds", "applicability", "originalPublication",
         "selectedCitation", "selectionReason", "supersedes", "conflictingCitations"},
        set(),
        context,
    )
    _text(obj["question"], f"{context}.question")
    _text(obj["answer"], f"{context}.answer")
    topics = _ids(obj["topicIds"], f"{context}.topicIds")
    topic_domains = {
        "ammunition", "attribute", "equipment", "fireteam", "hacking-program",
        "rule", "scenario", "skill", "state", "term", "trait", "weapon",
    }
    for topic in topics:
        if topic.split(":", 1)[0] not in topic_domains:
            raise ValueError(f"{context}.topicIds: unsupported reference {topic!r}")

    applicability = obj["applicability"]
    if not isinstance(applicability, list) or not applicability:
        raise ValueError(f"{context}.applicability: expected explicit non-empty scopes")
    seen: set[tuple[str, str | None, str | None, tuple[str, ...]]] = set()
    for index, item in enumerate(applicability):
        scope_context = f"{context}.applicability[{index}]"
        scope = _object(
            item,
            {"rulesRevision", "effectiveFrom"},
            {"season", "scenarioIds", "effectiveUntil"},
            scope_context,
        )
        version = _text(scope["rulesRevision"], f"{scope_context}.rulesRevision")
        starts = _date(scope["effectiveFrom"], f"{scope_context}.effectiveFrom")
        if "effectiveUntil" in scope:
            ends = _date(scope["effectiveUntil"], f"{scope_context}.effectiveUntil")
            if ends < starts:
                raise ValueError(f"{scope_context}: effectiveUntil precedes effectiveFrom")
        season = scope.get("season")
        season_id: str | None = None
        season_rev: str | None = None
        if season is not None:
            season_obj = _object(season, {"id", "revision"}, set(), f"{scope_context}.season")
            season_id = _text(season_obj["id"], f"{scope_context}.season.id")
            season_rev = _text(season_obj["revision"], f"{scope_context}.season.revision")
        scenario_ids = _ids(
            scope.get("scenarioIds", []),
            f"{scope_context}.scenarioIds", domain="scenario", empty=True,
        )
        key = (version, season_id, season_rev, tuple(sorted(scenario_ids)))
        if key in seen:
            raise ValueError(f"{scope_context}: duplicate applicability")
        seen.add(key)

    original = _object(
        obj["originalPublication"],
        {"collectionId", "sourceId", "version", "publishedDate", "page"},
        set(),
        f"{context}.originalPublication",
    )
    _text(original["collectionId"], f"{context}.originalPublication.collectionId")
    origin = _citation(
        {"sourceId": original["sourceId"], "page": original["page"]},
        f"{context}.originalPublication",
        citations,
    )
    _text(original["version"], f"{context}.originalPublication.version")
    _date(original["publishedDate"], f"{context}.originalPublication.publishedDate")
    original_source = next((s for s in sources if s["id"] == origin[0]), None)
    if original_source is None or original_source.get("kind") != "pdf":
        raise ValueError(f"{context}.originalPublication: must cite a PDF source")
    if (original_source.get("version"), original_source.get("publishedDate")) != (
        original["version"], original["publishedDate"]
    ):
        raise ValueError(f"{context}.originalPublication: source version/date mismatch")

    selected = _citation(obj["selectedCitation"], f"{context}.selectedCitation", citations)
    selected_source = next((s for s in sources if s["id"] == selected[0]), None)
    if (
        selected_source is None
        or selected_source.get("kind") != "pdf"
        or selected_source.get("authority") != "primary"
    ):
        raise ValueError(f"{context}.selectedCitation: requires official primary PDF source")
    _text(obj["selectionReason"], f"{context}.selectionReason")
    conflicting = obj["conflictingCitations"]
    if not isinstance(conflicting, list):
        raise ValueError(f"{context}.conflictingCitations: expected array")
    other = [
        _citation(item, f"{context}.conflictingCitations[{index}]", citations)
        for index, item in enumerate(conflicting)
    ]
    if selected in other or len(other) != len(set(other)):
        raise ValueError(f"{context}.conflictingCitations: duplicate or selected source")
    supersedes = _ids(obj["supersedes"], f"{context}.supersedes", domain="faq-ruling", empty=True)
    if record_id in supersedes:
        raise ValueError(f"{context}.supersedes: cannot supersede itself")


def _scope_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    """Whether a successor and predecessor could apply in the same context."""
    if first["rulesRevision"] != second["rulesRevision"]:
        return False
    first_season = first.get("season")
    second_season = second.get("season")
    if first_season is not None and second_season is not None:
        if first_season != second_season:
            return False
    first_scenarios = set(first.get("scenarioIds", []))
    second_scenarios = set(second.get("scenarioIds", []))
    if first_scenarios and second_scenarios and not first_scenarios & second_scenarios:
        return False
    if first.get("effectiveUntil", "9999-12-31") < second["effectiveFrom"]:
        return False
    if second.get("effectiveUntil", "9999-12-31") < first["effectiveFrom"]:
        return False
    return True


def validate_faq_ruling_references(
    documents: list[tuple[Path, dict[str, Any]]],
    current_definitions: dict[str, tuple[Path, dict[str, Any]]],
) -> None:
    """Validate publication-wide FAQ target identities and explicit supersession graph.

    Current FAQ topics must resolve to a current canonical definition. Historic
    FAQ predecessors may be retained in superseded collections as evidence.
    Nothing here selects a ruling for a particular reader, date or game context.
    """
    historical: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    current_rulings: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path, document in documents:
        for record in document["records"]:
            if record["kind"] != "faq-ruling" or record["composition"]["role"] != "definition":
                continue
            historical.setdefault(record["id"], []).append((path, record))
            if document["collection"]["status"] == "current":
                current_rulings[record["id"]] = (path, record)

    # One carried-forward identity may appear across archived editions. Its
    # original publication must not silently drift when the citation is reposted.
    for ruling_id, versions in historical.items():
        origins = {
            (
                item["facts"]["originalPublication"]["collectionId"],
                item["facts"]["originalPublication"]["sourceId"],
                item["facts"]["originalPublication"]["version"],
                item["facts"]["originalPublication"]["publishedDate"],
                item["facts"]["originalPublication"]["page"],
            )
            for _, item in versions
        }
        if len(origins) != 1:
            raise ValueError(
                f"FAQ ruling {ruling_id!r} has conflicting originalPublication across collections"
            )

    edges: dict[str, set[str]] = {ruling_id: set() for ruling_id in historical}
    for ruling_id, versions in historical.items():
        for path, record in versions:
            facts = record["facts"]
            if ruling_id in current_rulings:
                # A current ruling must refer to current topics, not a leftover
                # obsolete skill or a scenario from a missing ITS collection.
                if record is current_rulings[ruling_id][1]:
                    for topic in facts["topicIds"]:
                        if topic not in current_definitions:
                            raise ValueError(
                                f"FAQ ruling {ruling_id!r} in {path} topic {topic!r} "
                                "does not resolve to a current canonical definition"
                            )
                    for scope in facts["applicability"]:
                        for scenario_id in scope.get("scenarioIds", []):
                            target = current_definitions.get(scenario_id)
                            if target is None or target[1]["kind"] != "scenario":
                                raise ValueError(
                                    f"FAQ ruling {ruling_id!r} in {path} scenario "
                                    f"{scenario_id!r} is not a current published Scenario"
                                )
            for predecessor_id in facts["supersedes"]:
                earlier = historical.get(predecessor_id)
                if earlier is None:
                    raise ValueError(
                        f"FAQ ruling {ruling_id!r} in {path} supersedes "
                        f"missing ruling {predecessor_id!r}"
                    )
                if not any(
                    _scope_overlap(new_scope, old_scope)
                    for new_scope in facts["applicability"]
                    for _, preceding in earlier
                    for old_scope in preceding["facts"]["applicability"]
                ):
                    raise ValueError(
                        f"FAQ ruling {ruling_id!r} in {path} supersedes "
                        f"{predecessor_id!r} without overlapping applicability"
                    )
                edges[ruling_id].add(predecessor_id)

    visiting: set[str] = set()
    completed: set[str] = set()

    def visit(ruling_id: str) -> None:
        if ruling_id in visiting:
            raise ValueError(f"FAQ supersession cycle involving {ruling_id!r}")
        if ruling_id in completed:
            return
        visiting.add(ruling_id)
        for predecessor_id in sorted(edges[ruling_id]):
            visit(predecessor_id)
        visiting.remove(ruling_id)
        completed.add(ruling_id)

    for ruling_id in sorted(edges):
        visit(ruling_id)


def select_applicable_faq_rulings(
    records: list[dict[str, Any]],
    *,
    topic_id: str,
    rules_revision: str,
    as_of: str,
    season_id: str | None = None,
    season_revision: str | None = None,
    scenario_id: str | None = None,
) -> list[dict[str, Any]]:
    """Select only reviewed, currently applicable rulings for an explicit context.

    Candidates must include selected_source with the verified source's
    publication date. Do not infer context from the newest source or today.
    Historical editions are not part of the default current read model.
    """
    topic = _ids([topic_id], "topic_id")[0]
    revision = _text(rules_revision, "rules_revision")
    date_str = _date(as_of, "as_of")
    if (season_id is None) != (season_revision is None):
        raise ValueError("season_id and season_revision must be provided together")
    if season_id is not None:
        _text(season_id, "season_id")
        _text(season_revision, "season_revision")
    if scenario_id is not None:
        _ids([scenario_id], "scenario_id", domain="scenario")

    applicable: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for record in records:
        if record["kind"] != "faq-ruling" or record["composition"]["role"] != "definition":
            continue
        if (record.get("review") or {}).get("status") != "reviewed":
            continue
        facts = record["facts"]
        # The selected source is an explicit reviewed choice. If its date
        # is unknown or later than the requested date, it is not eligible.
        selected = record.get("selected_source")
        if not isinstance(selected, dict) or not selected.get("published_date"):
            continue
        if selected["published_date"] > date_str:
            continue
        if facts["originalPublication"]["publishedDate"] > date_str:
            continue
        # Do not serve a carried-forward current collection as if its
        # publication had existed before its effective date.
        if record.get("collection", {}).get("effective_from", "9999-12-31") > date_str:
            continue

        matches = []
        for scope in facts["applicability"]:
            if scope["rulesRevision"] != revision:
                continue
            if not (scope["effectiveFrom"] <= date_str <= scope.get(
                "effectiveUntil", "9999-12-31"
            )):
                continue
            season = scope.get("season")
            if season is not None and (
                season_id != season["id"] or season_revision != season["revision"]
            ):
                continue
            scenarios = scope.get("scenarioIds", [])
            if scenarios and scenario_id not in scenarios:
                continue
            matches.append(scope)
        if matches:
            applicable.append((record, matches))

    # Supersession is explicit, never inferred from publication recency.
    # Only another active, reviewed ruling for this same topic can conceal
    # a predecessor, preserving visibility when the replacement is out of scope.
    relevant = [(record, matches) for record, matches in applicable
                if topic in record["facts"]["topicIds"]]
    hidden = {
        predecessor
        for record, _ in relevant
        for predecessor in record["facts"]["supersedes"]
    }
    return [
        {
            "id": record["id"],
            "question": record["facts"]["question"],
            "answer": record["facts"]["answer"],
            "topic_ids": record["facts"]["topicIds"],
            "matched_applicability": matches,
            "original_publication": record["facts"]["originalPublication"],
            "selected_citation": record["facts"]["selectedCitation"],
            "selected_source": record["selected_source"],
            "selection_reason": record["facts"]["selectionReason"],
            "conflicting_citations": record["facts"]["conflictingCitations"],
            "supersedes": record["facts"]["supersedes"],
            "citations": record["citations"],
        }
        for record, matches in sorted(relevant, key=lambda item: item[0]["id"])
        if record["id"] not in hidden
    ]
