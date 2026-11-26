"""Private N5 identity inventory and conservative cross-army candidate consolidation."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any

from infinity_db.army_history_characterization import fingerprint
from infinity_db.army_history_pilot import (
    CHILDREN,
    catalog_index,
    indexed,
    peripheral_definitions,
    peripheral_signature,
)
from infinity_db.army_history_references import CATALOGS, resolve_references
from infinity_db.army_history_source import (
    Document,
    HistoricalArmySource,
    digest,
    document,
    read_history,
    require,
    verify_receipt,
)

# Only self-contained scalar/ordered-stat fields are eligible. AVA and
# referenced catalog IDs, membership and army-specific structures are not.
FIELDS = frozenset({"arm", "bs", "bts", "cc", "move", "ph", "s", "str", "w", "wip",
                    "points", "swc"})

# Reviewed against the pinned N5 archive in n5-identity-review-v1.json.
# Match exact observed scopes; a future change reopens identity review.
REVIEWED_SEPARATE = {
    1635: ("reinf-wardrivers-mercenary-hackers", 399, (399,), (1635, 1691)),
    1691: ("reinf-wardrivers-mercenary-hackers", 998, (998, 999), (1635, 1691)),
    1718: ("reinf-yaoxie-rui-shi", 299, (299,), (1718, 1800)),
    1800: ("reinf-yaoxie-rui-shi", 1199, (1199,), (1718, 1800)),
}
REVIEWED_ALIASES = {
    1852: (("zaybak-aero-unit", "zeybek-aero-unit"), 401, (401, 403)),
}


def scope_matches(
    identity: int, slugs: dict[str, list[Document]], canonical: int, factions: tuple[int, ...],
) -> bool:
    return all(
        e["canonical"] == canonical and e["idArmy"] == identity
        and isinstance(e["factions"], list)
        and e["factions"] == list(factions) and e["factionId"] in factions
        for values in slugs.values() for e in values
    )


def identity_inventory(source: HistoricalArmySource) -> Document:
    """Inventory assigned N5 contents, including unordered same-day alternatives."""
    occurrences: dict[int, dict[str, list[Document]]] = defaultdict(lambda: defaultdict(list))
    slug_ids: dict[str, set[int]] = defaultdict(set)
    missing_slugs: set[int] = set()
    malformed = []
    for edition, army, day, sha in sorted(source.groups):
        if edition != "n5":
            continue
        units = indexed(source.read_object(sha).get("units"))
        if units is None:
            malformed.append({"factionId": army, "date": day, "sha256": sha})
            continue
        for identity, unit in units.items():
            slug = unit.get("slug")
            if not isinstance(slug, str) or not slug.strip():
                missing_slugs.add(identity)
                slug = ""
            else:
                slug_ids[slug].add(identity)
            occurrences[identity][slug].append({
                "factionId": army, "date": day, "sha256": sha,
                "observationIndices": list(source.groups[(edition, army, day, sha)]),
                "name": unit.get("name"), "isc": unit.get("isc"),
                "canonical": unit.get("canonical"), "idArmy": unit.get("idArmy"),
                "factions": unit.get("factions"),
            })
    candidates = []
    eligible = []
    for identity, slugs in sorted(occurrences.items()):
        reasons = []
        if identity in missing_slugs:
            reasons.append("missingSlug")
        if len(slugs) > 1:
            reasons.append("multipleSlugsForId")
        if any(len(slug_ids[s]) > 1 for s in slugs if s):
            reasons.append("slugSharedByMultipleIds")
        if malformed:
            reasons.append("incompleteIdentityScan")
        status = "review" if reasons else "consistentObservedIdAndSlug"
        disposition = None
        separate = REVIEWED_SEPARATE.get(identity)
        alias = REVIEWED_ALIASES.get(identity)

        if separate is not None and reasons == ["slugSharedByMultipleIds"]:
            slug, canonical, factions, ids = separate
            if set(slugs) == {slug} and slug_ids[slug] == set(ids) and scope_matches(
                identity, slugs, canonical, factions,
            ):
                status = "reviewedSeparateArmyIdentity"
                disposition = "keepDistinctNumericId"
        if alias is not None and reasons == ["multipleSlugsForId"]:
            aliases, canonical, factions = alias
            if set(slugs) == set(aliases) and scope_matches(identity, slugs, canonical, factions):
                old_dates = [e["date"] for e in slugs[aliases[0]]]
                new_dates = [e["date"] for e in slugs[aliases[1]]]
                if max(old_dates) < min(new_dates):
                    status = "reviewedSpellingAlias"
                    disposition = "retainNumericIdAcrossAlias"
        if status != "review":
            eligible.append(identity)
        candidates.append({
            "unitId": identity,
            "candidateKey": f"n5:{identity}",
            "status": status, "disposition": disposition,
            "reasons": reasons,
            "slugEvidence": [
                {"slug": slug, "occurrences": values} for slug, values in sorted(slugs.items())
            ],
        })
    return {"edition": "n5", "eligibleUnitIds": eligible, "candidates": candidates,
            "malformedDocuments": malformed}


def record_at(data: Document, path: list[Any]) -> tuple[Document, list[Document]] | None:
    """Resolve nested numeric keys, never positional indexes."""
    if len(path) < 3 or len(path) % 2 != 1:
        return None
    row = data
    level = "faction"
    ancestors = []
    for collection, identity in zip(path[:-1:2], path[1:-1:2], strict=True):
        child = CHILDREN.get(level, {}).get(collection)
        if child is None or type(identity) is not int:
            return None
        rows = indexed(row.get(collection))
        if rows is None or identity not in rows:
            return None
        row = rows[identity]
        ancestors.append(row)
        level = child
    return row, ancestors


def target_signature(
    data: Document, path: list[Any], resolved: list[Document] | None = None,
) -> str | None:
    """Require matching labels, group context and exact target record contents.

    Full target rows deliberately retain unrelated fields, except that
    Peripheral references must resolve to unique local definitions. This
    is conservative and can leave equivalent changes separate.
    """
    found = record_at(data, path)
    if found is None:
        return None
    row, ancestors = found
    if len(ancestors) < 2:
        return None
    unit = ancestors[0]
    if not isinstance(unit.get("slug"), str) or not unit["slug"]:
        return None
    parents = [
        {k: parent[k] for k in ("id", "name", "isc", "category", "slug") if k in parent}
        for parent in ancestors[:-1]
    ]
    # A label-less leaf is insufficient evidence of cross-army continuity.
    if not isinstance(row.get("name"), str) or not row["name"]:
        return None
    target = dict(row)
    if resolved is not None:
        target[path[-1]] = resolved
    if "peripheral" in target:
        signature = peripheral_signature(target["peripheral"], peripheral_definitions(data))
        if signature is None:
            return None
        target["peripheral"] = signature
    return fingerprint({"parents": parents, "target": target})


def merge_compatible_intervals(events: list[Document]) -> tuple[list[Document], Counter[str]]:
    """Combine exact transitions only when their full component has a common window.

    Do not choose among overlapping alternatives, merge chains without a common
    intersection, or assume that an observation window is a publication date.
    """
    def transition(event: Document) -> str:
        return fingerprint({
            k: event[k] for k in (
                "edition", "path", "before", "after",
                "earlierTargetFingerprint", "laterTargetFingerprint",
            )
        })

    def overlap(a: Document, b: Document) -> bool:
        return (
            max(a["earlierObservedDate"], b["earlierObservedDate"])
            < min(a["laterObservedDate"], b["laterObservedDate"])
        )

    by_transition: dict[str, list[Document]] = defaultdict(list)
    by_path: dict[tuple[Any, ...], list[Document]] = defaultdict(list)
    for event in events:
        by_transition[transition(event)].append(event)
        by_path[tuple(event["path"])].append(event)
    merged = []
    counts: Counter[str] = Counter()

    def finish(component: list[Document]) -> None:
        if len(component) == 1:
            merged.extend(component)
            return
        start = max(e["earlierObservedDate"] for e in component)
        end = min(e["laterObservedDate"] for e in component)
        evidence = [item for e in component for item in e["evidence"]]
        armies = [item["factionId"] for item in evidence]
        first = component[0]
        window = {"earlierObservedDate": start, "laterObservedDate": end}
        reason = None
        if start >= end:
            reason = "noCommonWindow"
        elif len(armies) != len(set(armies)):
            reason = "repeatedArmy"
        elif any(
            transition(other) != transition(first) and overlap(window, other)
            for other in by_path[tuple(first["path"])]
        ):
            reason = "competingTransition"
        if reason is not None:
            counts[reason] += 1
            merged.extend(component)
            return
        payload = {k: v for k, v in first.items() if k not in {"candidateId", "evidence"}}
        payload.update(window)
        merged.append({
            **payload, "candidateId": fingerprint(payload),
            "evidence": sorted(evidence, key=lambda e: e["comparisonIndex"]),
        })
        counts["mergedComponents"] += 1
        counts["removedDuplicateCandidates"] += len(component) - 1

    for key in sorted(by_transition):
        rows = sorted(by_transition[key], key=lambda e: (
            e["earlierObservedDate"], e["laterObservedDate"], e["candidateId"],
        ))
        component: list[Document] = []
        right = ""
        for row in rows:
            if component and row["earlierObservedDate"] >= right:
                finish(component)
                component = []
                right = ""
            component.append(row)
            right = max(right, row["laterObservedDate"])
        if component:
            finish(component)
    return sorted(merged, key=lambda e: e["candidateId"]), counts


def consolidate(source: HistoricalArmySource, report: Document, inventory: Document) -> Document:
    require(report.get("archiveSha256") == source.sha256, "Pilot archive pin differs")
    require(report.get("edition") == "n5" and report.get("formatVersion") == 1,
            "Unsupported pilot format")
    eligible = set(inventory["eligibleUnitIds"])

    @lru_cache(maxsize=32)
    def data(sha: str) -> Document:
        return source.read_object(sha)

    @lru_cache(maxsize=64)
    def metadata(sha: str) -> dict[str, dict[int, tuple[str, ...]]]:
        return catalog_index(data(sha))

    buckets: dict[str, Document] = {}
    excluded: Counter[str] = Counter()
    included: Counter[str] = Counter()
    reference_outcomes: Counter[str] = Counter()
    reference_examples: dict[str, Document] = {}

    def reject(reason: str, reference_field: str | None, evidence: Document) -> None:
        excluded[reason] += 1
        if reference_field is not None:
            key = f"{reference_field}:{reason}"
            reference_outcomes[key] += 1
            reference_examples.setdefault(key, evidence)

    seen_comparisons = set()
    dates: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for edition, army, day, sha in source.groups:
        if edition == "n5":
            dates[army][day].append(sha)
    expected_pairs = {
        (army, a, b)
        for army, sequence in dates.items()
        for a, b in pairwise(sorted(sequence))
        if len(sequence[a]) == len(sequence[b]) == 1
    }
    for ci, comparison in enumerate(report["comparisons"]):
        army = comparison["factionId"]
        earlier, later = comparison["earlier"], comparison["later"]
        days = [earlier["encodedRevisionDate"], later["encodedRevisionDate"]]
        require(days[0] < days[1], "Non-directional comparison")
        pair = (army, *days)
        require(pair in expected_pairs, "Unexpected or ambiguous comparison")
        require(pair not in seen_comparisons, "Duplicate comparison")
        seen_comparisons.add(pair)
        for endpoint in (earlier, later):
            key = ("n5", army, endpoint["encodedRevisionDate"], endpoint["sha256"])
            require(key in source.groups, "Unknown comparison endpoint")
            require(list(source.groups[key]) == endpoint["observationIndices"],
                    "Comparison observation evidence differs")
        old, new = data(earlier["sha256"]), data(later["sha256"])

        def endpoint_context(endpoint: Document) -> list[dict[str, dict[int, tuple[str, ...]]]]:
            refs = sorted({
                sha for i in endpoint["observationIndices"]
                for sha in source.metadata_contexts.get(i, ()) if sha is not None
            })
            require(refs == endpoint["metadataSha256"], "Metadata context evidence differs")
            return [metadata(sha) for sha in refs]

        old_context, new_context = endpoint_context(earlier), endpoint_context(later)
        for ei, change in enumerate(comparison["changes"]):
            path = change["path"]
            category = change["category"]
            field = path[-1]
            is_reference = category == "referenceContentReview" and field in CATALOGS
            if not is_reference and (category != "gameplayFieldCandidate" or field not in FIELDS):
                excluded[category] += 1
                continue

            reference_field = field if is_reference else None
            evidence = {
                "factionId": army, "comparisonIndex": ci, "changeIndex": ei,
                "path": path, "earlier": earlier, "later": later,
            }
            if change["ancestorOrRecordLabelChanged"]:
                reject("changedIdentityLabel", reference_field, evidence)
                continue
            if len(path) < 3 or path[0] != "units" or path[1] not in eligible:
                reject("unitIdentityReview", reference_field, evidence)
                continue
            before, after = record_at(old, path), record_at(new, path)
            require(before is not None and after is not None, "Unresolved pilot record path")
            assert before is not None and after is not None
            field = path[-1]
            for target, side in ((before[0], "before"), (after[0], "after")):
                require(field in target and change[side]["present"], "Pilot field missing")
                require(fingerprint(target[field]) == fingerprint(change[side]["value"]),
                        "Pilot field value differs")
            left_resolved = right_resolved = None
            left_status = right_status = ""
            old_value, new_value = change["before"], change["after"]
            if is_reference:
                left_resolved, left_status = resolve_references(
                    before[0][field], field, old, old_context,
                )
                right_resolved, right_status = resolve_references(
                    after[0][field], field, new, new_context,
                )
                if left_resolved is None or right_resolved is None:
                    reason = left_status if left_resolved is None else right_status
                    reject(reason, reference_field, evidence)
                    continue
                if fingerprint(left_resolved) == fingerprint(right_resolved):
                    reject("resolvedReferenceEquivalent", reference_field, evidence)
                    continue
                old_value = {"present": True, "value": left_resolved}
                new_value = {"present": True, "value": right_resolved}
            left_sig = target_signature(old, path, left_resolved)
            right_sig = target_signature(new, path, right_resolved)
            if left_sig is None or right_sig is None:
                reject("targetIdentityReview", reference_field, evidence)
                continue
            if is_reference:
                status = (
                    "filterOnly" if "filterOnly" in (left_status, right_status)
                    else "withMetadata"
                )
                reference_outcomes[f"{field}:{status}"] += 1
            key_data = {
                "edition": "n5", "path": path, "earlierObservedDate": days[0],
                "laterObservedDate": days[1], "before": old_value,
                "after": new_value, "earlierTargetFingerprint": left_sig,
                "laterTargetFingerprint": right_sig,
            }
            key = fingerprint(key_data)
            bucket = buckets.setdefault(key, {
                "candidateId": key, **key_data, "evidence": [],
            })
            require(all(e["factionId"] != army for e in bucket["evidence"]),
                    "Duplicate army evidence for change candidate")
            bucket["evidence"].append({
                "factionId": army, "comparisonIndex": ci, "changeIndex": ei,
                "earlier": earlier, "later": later,
            })
            included[field] += 1
    require(seen_comparisons == expected_pairs, "Pilot comparison coverage differs")
    require(sum(included.values()) + sum(excluded.values()) ==
            sum(len(c["changes"]) for c in report["comparisons"]), "Change coverage differs")
    exact_events = sorted(buckets.values(), key=lambda e: e["candidateId"])
    events, interval_counts = merge_compatible_intervals(exact_events)
    require(sum(len(e["evidence"]) for e in events) == sum(included.values()),
            "Consolidated evidence count differs")
    event_counts = Counter(e["path"][-1] for e in events)
    multi = [e for e in events if len(e["evidence"]) > 1]
    return {
        "edition": "n5", "archiveSha256": source.sha256, "formatVersion": 3,
        "referenceOutcomes": dict(reference_outcomes),
        "referenceReviewExamples": reference_examples,
        "comparedPairs": len(seen_comparisons),
        "exactWindowCandidateCount": len(exact_events),
        "intervalConsolidation": dict(interval_counts),
        "includedOccurrencesByField": dict(included),
        "excludedOccurrencesByReason": dict(excluded),
        "candidateCountsByField": dict(event_counts),
        "candidateCount": len(events),
        "multiArmyCandidateCount": len(multi),
        "multiArmyOccurrenceCount": sum(len(e["evidence"]) for e in multi),
        "retainedOccurrenceCount": sum(len(e["evidence"]) for e in events),
        "identityInventory": inventory, "candidates": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--pilot-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.pilot.read_bytes()
    require(digest(raw) == args.pilot_sha256, "Pilot report SHA-256 differs")
    source = read_history(args.archive, args.sha256)
    verify_receipt(source, args.receipt, args.receipt_sha256)
    inventory = identity_inventory(source)
    report = consolidate(source, document(raw), inventory)
    report["pilotSha256"] = args.pilot_sha256
    summary = {k: v for k, v in report.items() if k not in {"identityInventory", "candidates"}}
    summary["identityStatusCounts"] = dict(Counter(
        row["status"] for row in inventory["candidates"]
    ))
    summary["identityReview"] = [
        {"unitId": row["unitId"], "status": row["status"],
         "disposition": row["disposition"], "reasons": row["reasons"],
         "slugs": [s["slug"] for s in row["slugEvidence"]]}
        for row in inventory["candidates"] if row["reasons"]
    ]
    summary["multiArmyExamples"] = sorted(
        (row for row in report["candidates"] if len(row["evidence"]) > 1),
        key=lambda row: (-len(row["evidence"]), row["candidateId"]),
    )[:5]
    for path, payload in ((args.output, report), (args.summary_output, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in {"multiArmyExamples", "referenceReviewExamples"}},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
