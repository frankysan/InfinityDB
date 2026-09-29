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
REVIEW_POLICY_FILENAME = "maintained-text-link-reviews.json"
REVIEW_POLICY_FORMAT_VERSION = 1
_CONTEXT_INDEX = re.compile(
    r"^(?P<section>records|labels|skillTypes)\[(?P<index>\d+)\](?P<field>.*)$"
)
_LIST_INDEX = re.compile(r"\[\d+\]")

CandidateKey = tuple[str, str, tuple[str, ...]]
OwnerCandidates = dict[str, Counter[CandidateKey]]
ReviewNeededKey = tuple[str, str, str | None]
OwnerReviewNeeded = dict[str, Counter[ReviewNeededKey]]
ReviewedBatchResidualKey = tuple[str, str, str, tuple[str, ...]]
OwnerReviewedBatchResiduals = dict[str, Counter[ReviewedBatchResidualKey]]


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


def _pluralize_review_surface(value: str) -> str:
    """Return the same conservative plural shape supported by maintained links."""

    if not value:
        return value
    lower = value.casefold()
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return f"{value}es"
    if len(value) > 1 and lower.endswith("y") and lower[-2] not in "aeiou":
        return f"{value[:-1]}ies"
    return f"{value}s"


def _load_review_policy(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read maintained-text review policy {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"Maintained-text review policy {path} must contain an object")
    if document.get("formatVersion") != REVIEW_POLICY_FORMAT_VERSION:
        raise ValueError(
            "Unsupported maintained-text review policy version: "
            f"{document.get('formatVersion')!r}"
        )
    if document.get("policy") != "reviewed-maintained-text-link-batches":
        raise ValueError(
            f"Maintained-text review policy {path} has unsupported policy "
            f"{document.get('policy')!r}"
        )
    batches = document.get("batches")
    if not isinstance(batches, list) or not batches:
        raise ValueError(f"Maintained-text review policy {path} must contain batches")

    seen_ids: set[str] = set()
    validated: list[dict[str, Any]] = []
    required = {
        "id",
        "namespace",
        "includeAliases",
        "includeSimplePlurals",
        "caseInsensitive",
        "reviewedOn",
    }
    for index, batch in enumerate(batches):
        context = f"{path} batches[{index}]"
        if not isinstance(batch, dict):
            raise ValueError(f"{context} must be an object")
        missing = required - batch.keys()
        unknown = batch.keys() - (required | {"note", "extraSurfaces"})
        if missing:
            raise ValueError(f"{context} missing fields {sorted(missing)}")
        if unknown:
            raise ValueError(f"{context} has unsupported fields {sorted(unknown)}")
        batch_id = batch["id"]
        namespace = batch["namespace"]
        reviewed_on = batch["reviewedOn"]
        if not isinstance(batch_id, str) or not batch_id.strip():
            raise ValueError(f"{context}.id must be a non-empty string")
        if batch_id in seen_ids:
            raise ValueError(f"{context}.id duplicates {batch_id!r}")
        seen_ids.add(batch_id)
        if not isinstance(namespace, str) or namespace not in MAINTAINED_REFERENCE_KINDS:
            raise ValueError(
                f"{context}.namespace must be one of "
                f"{sorted(MAINTAINED_REFERENCE_KINDS)}"
            )
        for field in ("includeAliases", "includeSimplePlurals", "caseInsensitive"):
            if not isinstance(batch[field], bool):
                raise ValueError(f"{context}.{field} must be a boolean")
        if batch["caseInsensitive"] is not True:
            raise ValueError(
                f"{context}.caseInsensitive must be true so reviewed batches catch "
                "case-only omissions"
            )
        if not isinstance(reviewed_on, str) or not reviewed_on.strip():
            raise ValueError(f"{context}.reviewedOn must be a non-empty string")
        note = batch.get("note")
        if note is not None and (not isinstance(note, str) or not note.strip()):
            raise ValueError(f"{context}.note must be a non-empty string when present")
        extra_surfaces = batch.get("extraSurfaces", [])
        if not isinstance(extra_surfaces, list):
            raise ValueError(f"{context}.extraSurfaces must be an array when present")
        for surface_index, surface in enumerate(extra_surfaces):
            surface_context = f"{context}.extraSurfaces[{surface_index}]"
            if not isinstance(surface, dict) or set(surface) != {"target", "text"}:
                raise ValueError(
                    f"{surface_context} must contain exactly target and text"
                )
            target = surface["target"]
            text = surface["text"]
            if not isinstance(target, str) or not target.startswith(f"{namespace}:"):
                raise ValueError(
                    f"{surface_context}.target must belong to {namespace!r}"
                )
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{surface_context}.text must be a non-empty string")
        validated.append(batch)
    return validated


def _reviewed_batch_vocabulary(
    documents: list[tuple[Path, dict[str, Any]]], batch: dict[str, Any]
) -> dict[str, frozenset[str]]:
    namespace = batch["namespace"]
    labels: dict[str, set[str]] = {}
    current_record_ids: set[str] = set()

    def add_surface(surface: str, target: str) -> None:
        labels.setdefault(surface.casefold(), set()).add(target)
        if batch["includeSimplePlurals"]:
            plural = _pluralize_review_surface(surface)
            labels.setdefault(plural.casefold(), set()).add(target)

    for _, document in documents:
        if document["collection"]["status"] != "current":
            continue
        for record in document["records"]:
            if record["kind"] != namespace:
                continue
            record_id = record["id"]
            current_record_ids.add(record_id)
            add_surface(record["name"], record_id)
            if batch["includeAliases"]:
                for alias in record.get("aliases") or []:
                    add_surface(alias, record_id)

    for extra in batch.get("extraSurfaces", []):
        target = extra["target"]
        if target not in current_record_ids:
            raise ValueError(
                f"Maintained-text review batch {batch['id']!r} extra surface target "
                f"{target!r} is not a current {namespace} record"
            )
        add_surface(extra["text"], target)

    return {label: frozenset(targets) for label, targets in labels.items()}


def collect_reviewed_batch_residuals(
    documents: list[tuple[Path, dict[str, Any]]], review_policy_path: Path
) -> OwnerReviewedBatchResiduals:
    """Return plain references that survive a batch recorded as fully reviewed.

    This audit is deliberately broader than the migration baseline: reviewed batches are
    rescanned case-insensitively and may include conservative plural forms. Review-needed
    markers and semantic tokens are excluded, so unresolved reviewed text must be explicit.
    """

    result: OwnerReviewedBatchResiduals = {}
    for batch in _load_review_policy(review_policy_path):
        vocabulary = _reviewed_batch_vocabulary(documents, batch)
        if not vocabulary:
            continue
        labels = sorted(vocabulary, key=lambda value: (-len(value), value))
        pattern = re.compile(
            r"(?<![\w-])(?:"
            + "|".join(re.escape(label) for label in labels)
            + r")(?![\w-])",
            re.IGNORECASE,
        )
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
                        targets = set(vocabulary[match.group(0).casefold()])
                        if current_record_id is not None:
                            targets.discard(current_record_id)
                        if targets:
                            counter[
                                (
                                    batch["id"],
                                    field,
                                    match.group(0),
                                    tuple(sorted(targets)),
                                )
                            ] += 1
    return {owner: counter for owner, counter in result.items() if counter}


def validate_reviewed_batch_coverage(
    documents: list[tuple[Path, dict[str, Any]]], review_policy_path: Path
) -> None:
    """Reject a plain semantic mention inside a batch already declared reviewed."""

    residuals = collect_reviewed_batch_residuals(documents, review_policy_path)
    if not residuals:
        return
    details: list[str] = []
    for owner, values in sorted(residuals.items())[:5]:
        rendered = ", ".join(
            f"{text!r} -> {'/'.join(targets)} [{batch_id}] x{count}"
            for (batch_id, _, text, targets), count in values.most_common(3)
        )
        details.append(f"{owner}: {rendered}")
    suffix = "" if len(residuals) <= 5 else f"; plus {len(residuals) - 5} more owner(s)"
    raise ValueError(
        "Reviewed maintained-text batch still contains unmarked semantic references: "
        + "; ".join(details)
        + suffix
    )


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
    documents: list[tuple[Path, dict[str, Any]]],
    baseline_path: Path,
    *,
    review_policy_path: Path | None = None,
) -> None:
    """Reject unreviewed changes to legacy debt or already completed review batches."""

    if review_policy_path is None:
        review_policy_path = baseline_path.with_name(REVIEW_POLICY_FILENAME)
    validate_reviewed_batch_coverage(documents, review_policy_path)

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
