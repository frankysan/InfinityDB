"""Reconcile observed loadout key changes using endpoint-specific composition."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from infinity_db.army_history_characterization import fingerprint
from infinity_db.army_history_membership import child_collection
from infinity_db.army_history_pilot import (
    catalog_index,
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

NON_COMPOSITION = frozenset({"id", "name", "points", "swc"})
REFERENCE_FIELDS = frozenset(CATALOGS)


def composition(
    row: Document, data: Document, contexts: list[dict[str, dict[int, tuple[str, ...]]]],
) -> tuple[Document | None, str]:
    """Compare all fields except source ID, display name and costs.

    Nonempty includes depend on other scoped keys and are not yet resolved.
    Other unknown fields remain in the comparison.
    """
    payload = {k: v for k, v in row.items() if k not in NON_COMPOSITION}
    if payload.get("includes") not in (None, []):
        return None, "unresolvedIncludes"
    filter_only = False
    for field in CATALOGS:
        if field not in payload:
            continue
        value = payload[field]
        if isinstance(value, list):
            # Current normalization treats absent and null extra as no extras.
            value = [
                {k: v for k, v in item.items() if not (k == "extra" and v is None)}
                if isinstance(item, dict) else item for item in value
            ]
        resolved, status = resolve_references(value, field, data, contexts)
        if resolved is None:
            return None, status
        payload[field] = resolved
        filter_only |= status == "filterOnly"
    if "peripheral" in payload:
        signature = peripheral_signature(payload["peripheral"], peripheral_definitions(data))
        if signature is None:
            return None, "unresolvedPeripheral"
        payload["peripheral"] = signature
    return payload, "filterOnly" if filter_only else "withMetadata"


def reference_tokens(payload: Document) -> set[str]:
    return {
        fingerprint([field, item])
        for field in REFERENCE_FIELDS
        for item in payload.get(field, [])
    }


def changed_fields(a: Document, b: Document) -> list[str]:
    return sorted(
        k for k in a.keys() | b.keys()
        if fingerprint([k in a, a.get(k)]) != fingerprint([k in b, b.get(k)])
    )


def match_siblings(
    old: dict[int, Document], new: dict[int, Document],
    left: dict[int, tuple[Document | None, str]],
    right: dict[int, tuple[Document | None, str]],
) -> tuple[list[Document], dict[tuple[str, int], str]]:
    """Unique composition continuity, plus explicitly nonbinding modification hints."""
    removed, added = old.keys() - new.keys(), new.keys() - old.keys()
    reasons = {
        (side, identity): status if payload is None else "noUniqueCompositionMatch"
        for side, ids, values in (("before", removed, left), ("after", added, right))
        for identity in ids for payload, status in [values[identity]]
    }
    matches = []
    if not removed or not added:
        return matches, {k: "noOppositeKey" for k in reasons}
    if any(v is None for v, _ in left.values()) or any(v is None for v, _ in right.values()):
        return matches, {
            key: "unresolvedSibling" if value == "noUniqueCompositionMatch" else value
            for key, value in reasons.items()
        }
    for a in sorted(removed):
        payload, status = left[a]
        if payload is None or not reference_tokens(payload):
            continue
        sig = fingerprint(payload)
        # Include surviving siblings in uniqueness checks: a duplicate new
        # option must not steal continuity from an existing option.
        left_ids = [i for i, (v, _) in left.items() if v is not None and fingerprint(v) == sig]
        right_ids = [i for i, (v, _) in right.items() if v is not None and fingerprint(v) == sig]
        if left_ids != [a] or len(right_ids) != 1 or right_ids[0] not in added:
            continue
        b = right_ids[0]
        changes = changed_fields(
            {k: v for k, v in old[a].items() if k in NON_COMPOSITION - {"id"}},
            {k: v for k, v in new[b].items() if k in NON_COMPOSITION - {"id"}},
        )
        matches.append({
            "beforeId": a, "afterId": b, "kind": "sameComposition",
            "definitionEvidence": (
                "filterOnly" if "filterOnly" in (status, right[b][1]) else "withMetadata"
            ),
            "changedNonCompositionFields": changes,
            "compositionFingerprint": sig,
        })
        reasons.pop(("before", a))
        reasons.pop(("after", b))

    # Suggest modifications only when a reference occurrence distinguishes
    # this pair from every other sibling on both sides. Hints do not consume
    # or replace structural evidence, even when mutually unique.
    def distinctive(values: dict[int, tuple[Document | None, str]]) -> dict[int, set[str]]:
        tokens = {i: reference_tokens(v) for i, (v, _) in values.items() if v is not None}
        totals = Counter(token for group in tokens.values() for token in group)
        return {i: {token for token in group if totals[token] == 1}
                for i, group in tokens.items()}

    lt, rt = distinctive(left), distinctive(right)
    edges = []
    for a in sorted(removed):
        if ("before", a) not in reasons:
            continue
        for b in sorted(added):
            if ("after", b) not in reasons or old[a].get("name") != new[b].get("name"):
                continue
            overlap = lt.get(a, set()) & rt.get(b, set())
            av, bv = left[a][0], right[b][0]
            if not overlap or av is None or bv is None:
                continue
            changed = changed_fields(av, bv)
            if not changed or not set(changed) <= REFERENCE_FIELDS:
                continue
            edges.append({
                "beforeId": a, "afterId": b, "kind": "modificationReview",
                "changedCompositionFields": changed,
                "sharedDistinctiveReferenceCount": len(overlap),
            })
    left_degree = Counter(e["beforeId"] for e in edges)
    right_degree = Counter(e["afterId"] for e in edges)
    for edge in edges:
        a, b = edge["beforeId"], edge["afterId"]
        if left_degree[a] == right_degree[b] == 1:
            matches.append(edge)
            reasons[("before", a)] = "modificationReview"
            reasons[("after", b)] = "modificationReview"
        else:
            reasons[("before", a)] = "ambiguousModification"
            reasons[("after", b)] = "ambiguousModification"
    return matches, reasons


def reconcile(source: HistoricalArmySource, membership: Document) -> Document:
    require(membership.get("archiveSha256") == source.sha256, "Membership archive pin differs")
    require(membership.get("edition") == "n5" and membership.get("formatVersion") == 2,
            "Unsupported membership report")
    collections: dict[tuple[Any, ...], list[Document]] = defaultdict(list)
    for event in membership["structuralOccurrences"]:
        if event["kind"] == "loadout":
            ev = event["evidence"]
            collections[(ev["comparisonIndex"], *event["path"][:-1])].append(event)

    @lru_cache(maxsize=32)
    def data(sha: str) -> Document:
        return source.read_object(sha)

    @lru_cache(maxsize=64)
    def metadata(sha: str) -> dict[str, dict[int, tuple[str, ...]]]:
        return catalog_index(data(sha))

    def contexts(endpoint: Document, army: int):
        key = ("n5", army, endpoint["encodedRevisionDate"], endpoint["sha256"])
        require(key in source.groups, "Unknown membership endpoint")
        require(list(source.groups[key]) == endpoint["observationIndices"],
                "Observation evidence differs")
        refs = sorted({
            sha for i in source.groups[key] for sha in source.metadata_contexts.get(i, ())
            if sha is not None
        })
        require(refs == endpoint["metadataSha256"], "Metadata evidence differs")
        return [metadata(sha) for sha in refs]

    counts: Counter[str] = Counter()
    results = []
    unresolved = []
    review_groups: dict[str, Document] = {}
    for key, events in sorted(collections.items()):
        ev = events[0]["evidence"]
        earlier, later = ev["earlier"], ev["later"]
        army = ev["factionId"]
        old_data, new_data = data(earlier["sha256"]), data(later["sha256"])
        old, new = child_collection(old_data, events[0]["path"]), child_collection(
            new_data, events[0]["path"],
        )
        require(old is not None and new is not None, "Unknown loadout collection")
        assert old is not None and new is not None
        old_context, new_context = contexts(earlier, army), contexts(later, army)
        by_key = {}
        for event in events:
            evidence = event["evidence"]
            require(all(evidence[k] == ev[k] for k in ("factionId", "earlier", "later")),
                    "Inconsistent collection evidence")
            side = "after" if event["direction"] == "appeared" else "before"
            identity = event["path"][-1]
            present, absent = (new, old) if side == "after" else (old, new)
            require(identity in present and identity not in absent, "Loadout presence differs")
            require(fingerprint(present[identity]) == fingerprint(event[side]["value"]),
                    "Loadout record differs")
            require((side, identity) not in by_key, "Duplicate lifecycle evidence")
            by_key[(side, identity)] = event
        require(set(by_key) == (
            {("before", i) for i in old.keys() - new.keys()}
            | {("after", i) for i in new.keys() - old.keys()}
        ), "Incomplete collection lifecycle evidence")
        left = {i: composition(row, old_data, old_context) for i, row in old.items()}
        right = {i: composition(row, new_data, new_context) for i, row in new.items()}
        matches, reasons = match_siblings(old, new, left, right)
        for match in matches:
            a, b = match["beforeId"], match["afterId"]
            before, after = by_key[("before", a)], by_key[("after", b)]
            results.append({
                **match, "parentPath": list(key[1:]),
                "before": before, "after": after,
                "rawChangedFields": changed_fields(old[a], new[b]),
            })
            counts[match["kind"]] += 1
            if match["kind"] == "modificationReview":
                # Group identical review questions, not historical events:
                # different observation windows remain independent evidence.
                payload = {
                    "parentPath": list(key[1:]), "beforeId": a, "afterId": b,
                    "beforeComposition": left[a][0], "afterComposition": right[b][0],
                    "beforeOtherFields": {k: v for k, v in old[a].items() if k in NON_COMPOSITION},
                    "afterOtherFields": {k: v for k, v in new[b].items() if k in NON_COMPOSITION},
                }
                group_id = fingerprint(payload)
                group = review_groups.setdefault(group_id, {
                    "reviewId": group_id, **payload, "evidence": [],
                })
                group["evidence"].append({
                    "before": before["evidence"], "after": after["evidence"],
                })
            if match["kind"] == "sameComposition":
                counts["sameCompositionOccurrences"] += 2
                if before["possibleReplacementIds"]:
                    counts["previousReviewResolved"] += 1
                if after["possibleReplacementIds"]:
                    counts["previousReviewResolved"] += 1
        for (side, identity), reason in sorted(reasons.items()):
            event = by_key[(side, identity)]
            unresolved.append({"reason": reason, "occurrence": event})
            counts[f"unpaired:{reason}"] += 1
            if event["possibleReplacementIds"]:
                counts[f"previousReviewUnpaired:{reason}"] += 1
    counts["modificationReviewGroups"] = len(review_groups)
    total = sum(len(rows) for rows in collections.values())
    require(counts["sameCompositionOccurrences"] + len(unresolved) == total,
            "Lifecycle occurrence accounting differs")
    return {
        "formatVersion": 2, "archiveSha256": source.sha256, "edition": "n5",
        "loadoutOccurrences": total, "collectionComparisons": len(collections),
        "counts": dict(counts), "matches": results, "unpaired": unresolved,
        "modificationReviewGroups": list(review_groups.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--membership-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.membership.read_bytes()
    require(digest(raw) == args.membership_sha256, "Membership report SHA-256 differs")
    source = read_history(args.archive, args.sha256)
    verify_receipt(source, args.receipt, args.receipt_sha256)
    result = reconcile(source, document(raw))
    result["membershipSha256"] = args.membership_sha256
    summary = {k: v for k, v in result.items() if k not in {
        "matches", "unpaired", "modificationReviewGroups",
    }}
    summary["examples"] = [
        {k: v for k, v in row.items() if k not in {"before", "after"}}
        | {"evidence": row["before"]["evidence"]}
        for kind in ("sameComposition", "modificationReview")
        for row in [m for m in result["matches"] if m["kind"] == kind][:5]
    ]
    for path, payload in ((args.output, result), (args.summary_output, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "examples"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
