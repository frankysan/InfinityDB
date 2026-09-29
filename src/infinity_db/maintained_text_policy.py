"""Audit unlinked semantic references in maintained rules prose."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from infinity_db.maintained_text import (
    MAINTAINED_REFERENCE_KINDS,
    maintained_text_fields,
    parse_maintained_text,
)

BASELINE_FORMAT_VERSION = 1
BASELINE_FILENAME = "maintained-text-link-baseline.json"
_CONTEXT_INDEX = re.compile(
    r"^(?P<section>records|labels|skillTypes)\[(?P<index>\d+)\](?P<field>.*)$"
)
_LIST_INDEX = re.compile(r"\[\d+\]")

CandidateKey = tuple[str, str, tuple[str, ...]]
OwnerCandidates = dict[str, Counter[CandidateKey]]
ReviewNeededKey = tuple[str, str, str | None]
OwnerReviewNeeded = dict[str, Counter[ReviewNeededKey]]


def _stable_owner(
    document: dict[str, Any], context: str
) -> tuple[str, str, str | None]:
    match = _CONTEXT_INDEX.match(context)
    if match is None:
        raise ValueError(f"Unsupported maintained-text context {context!r}")
    section = match.group("section")
    index = int(match.group("index"))
    field = _LIST_INDEX.sub("[]", match.group("field").lstrip("."))
    if section == "records":
        record_id = document["records"][index]["id"]
        return record_id, field, record_id
    if section == "labels":
        return f"label:{document['labels'][index]['id']}", field, None
    return f"skill-type:{document['skillTypes'][index]['id']}", field, None


def _reference_vocabulary(
    documents: list[tuple[Path, dict[str, Any]]],
) -> dict[str, frozenset[str]]:
    labels: dict[str, set[str]] = {}
    for _, document in documents:
        if document["collection"]["status"] != "current":
            continue
        for record in document["records"]:
            if record["kind"] not in MAINTAINED_REFERENCE_KINDS:
                continue
            record_id = record["id"]
            for label in (record["name"], *(record.get("aliases") or [])):
                if isinstance(label, str) and label:
                    labels.setdefault(label, set()).add(record_id)
    return {label: frozenset(targets) for label, targets in labels.items()}


def collect_unlinked_reference_candidates(
    documents: list[tuple[Path, dict[str, Any]]],
) -> OwnerCandidates:
    """Return plain canonical/alias references that remain outside semantic tokens.

    Matching is case-sensitive and longest-first. Existing semantic/distance tokens are
    excluded from the plain-text scan, and a record is not required to link to itself.
    """

    vocabulary = _reference_vocabulary(documents)
    if not vocabulary:
        return {}
    labels = sorted(vocabulary, key=lambda value: (-len(value), value))
    pattern = re.compile(
        r"(?<![\w-])(?:" + "|".join(re.escape(label) for label in labels) + r")(?![\w-])"
    )
    result: OwnerCandidates = {}
    for _, document in documents:
        if document["collection"]["status"] != "current":
            continue
        collection_id = document["collection"]["id"]
        for context, text in maintained_text_fields(document):
            owner_id, field, current_record_id = _stable_owner(document, context)
            owner_key = f"{collection_id}|{owner_id}"
            counter = result.setdefault(owner_key, Counter())
            for token in parse_maintained_text(text, context=context):
                if token["type"] != "text":
                    continue
                for match in pattern.finditer(token["text"]):
                    targets = set(vocabulary[match.group(0)])
                    if current_record_id is not None:
                        targets.discard(current_record_id)
                    if targets:
                        counter[(field, match.group(0), tuple(sorted(targets)))] += 1
    return {owner: counter for owner, counter in result.items() if counter}


def collect_review_needed_markers(
    documents: list[tuple[Path, dict[str, Any]]],
) -> OwnerReviewNeeded:
    """Return explicitly flagged maintained-text passages awaiting manual review."""

    result: OwnerReviewNeeded = {}
    for _, document in documents:
        if document["collection"]["status"] != "current":
            continue
        collection_id = document["collection"]["id"]
        for context, text in maintained_text_fields(document):
            owner_id, field, _ = _stable_owner(document, context)
            owner_key = f"{collection_id}|{owner_id}"
            counter = result.setdefault(owner_key, Counter())
            for token in parse_maintained_text(text, context=context):
                if token["type"] != "review-needed":
                    continue
                counter[(field, token["reason"], token.get("text"))] += 1
    return {owner: counter for owner, counter in result.items() if counter}


def _candidate_payload(candidates: Counter[CandidateKey]) -> list[dict[str, Any]]:
    return [
        {
            "field": field,
            "text": text,
            "targets": list(targets),
            "count": count,
        }
        for (field, text, targets), count in sorted(candidates.items())
    ]


def _owner_summary(candidates: Counter[CandidateKey]) -> dict[str, Any]:
    payload = _candidate_payload(candidates)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "candidateCount": sum(candidates.values()),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def build_maintained_text_link_baseline(
    documents: list[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    """Build the temporary legacy-debt baseline for unlinked maintained references."""

    candidates = collect_unlinked_reference_candidates(documents)
    collection_ids = sorted(
        document["collection"]["id"]
        for _, document in documents
        if document["collection"]["status"] == "current"
    )
    return {
        "formatVersion": BASELINE_FORMAT_VERSION,
        "policy": "legacy-unlinked-maintained-text-references",
        "collections": collection_ids,
        "candidateOwners": len(candidates),
        "candidateOccurrences": sum(sum(values.values()) for values in candidates.values()),
        "owners": {
            owner: _owner_summary(values) for owner, values in sorted(candidates.items())
        },
    }


def _load_baseline(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read maintained-text link baseline {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"Maintained-text link baseline {path} must contain an object")
    if document.get("formatVersion") != BASELINE_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported maintained-text link baseline version: "
            f"{document.get('formatVersion')!r}"
        )
    owners = document.get("owners")
    if not isinstance(owners, dict):
        raise ValueError(f"Maintained-text link baseline {path} must contain an owners object")
    return document


def validate_maintained_text_link_baseline(
    documents: list[tuple[Path, dict[str, Any]]], baseline_path: Path
) -> None:
    """Reject unreviewed changes to the legacy unlinked-reference inventory."""

    baseline = _load_baseline(baseline_path)
    current = build_maintained_text_link_baseline(documents)
    baseline_owners = baseline["owners"]
    current_owners = current["owners"]
    changed = sorted(
        owner
        for owner in set(baseline_owners) | set(current_owners)
        if baseline_owners.get(owner) != current_owners.get(owner)
    )
    if not changed:
        return

    candidates = collect_unlinked_reference_candidates(documents)
    details: list[str] = []
    for owner in changed[:5]:
        values = candidates.get(owner)
        if not values:
            details.append(f"{owner}: legacy candidates were removed; shrink the baseline")
            continue
        rendered = ", ".join(
            f"{text!r} -> {'/'.join(targets)} x{count}"
            for (_, text, targets), count in values.most_common(3)
        )
        details.append(f"{owner}: {rendered}")
    suffix = "" if len(changed) <= 5 else f"; plus {len(changed) - 5} more owner(s)"
    raise ValueError(
        "Maintained-text semantic-link coverage changed outside the reviewed legacy baseline: "
        + "; ".join(details)
        + suffix
    )


def inferred_baseline_path(
    documents: list[tuple[Path, dict[str, Any]]],
) -> Path | None:
    """Return the sibling project baseline when all rule documents share one directory."""

    parents = {path.parent for path, _ in documents}
    if len(parents) != 1:
        return None
    candidate = next(iter(parents)).parent / BASELINE_FILENAME
    if not candidate.is_file():
        return None
    baseline = _load_baseline(candidate)
    baseline_collections = baseline.get("collections")
    if not isinstance(baseline_collections, list) or not all(
        isinstance(value, str) for value in baseline_collections
    ):
        raise ValueError(
            f"Maintained-text link baseline {candidate} must contain a collections array"
        )
    document_collections = {
        document["collection"]["id"]
        for _, document in documents
        if document["collection"]["status"] == "current"
    }
    if not set(baseline_collections).issubset(document_collections):
        return None
    return candidate
