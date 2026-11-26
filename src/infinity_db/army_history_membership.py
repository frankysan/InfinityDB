"""Observed N5 army membership and nested record lifecycle evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any

from infinity_db.army_history_characterization import fingerprint
from infinity_db.army_history_consolidation import (
    identity_inventory,
    merge_compatible_intervals,
    record_at,
)
from infinity_db.army_history_pilot import (
    LABELS,
    indexed,
    peripheral_definitions,
    peripheral_signature,
)
from infinity_db.army_history_source import (
    Document,
    HistoricalArmySource,
    digest,
    document,
    read_history,
    require,
    verify_receipt,
)


def declared_armies(unit: Document) -> set[int] | None:
    values = unit.get("factions")
    if not isinstance(values, list) or any(type(x) is not int for x in values):
        return None
    if len(set(values)) != len(values):
        return None
    return set(values)


def source_role(unit: Document) -> str:
    """Apply explicit current-source markers, not source-ID arithmetic."""
    slug = unit.get("slug")
    armies = declared_armies(unit)
    canonical = unit.get("canonical")
    if not isinstance(slug, str) or armies is None or type(canonical) is not int:
        return "unknown"
    if slug.startswith("merc-"):
        return "mercenaryVariant" if canonical == 1 and not armies else "unknown"
    return "unknown" if canonical == 1 and not armies else "standardSourceRecord"


def child_collection(data: Document, path: list[Any]) -> dict[int, Document] | None:
    """Resolve a child collection without confusing a missing collection with absence."""
    if len(path) == 2 and path[0] == "units":
        return indexed(data.get("units"))
    if len(path) < 4 or len(path) % 2:
        return None
    parent = record_at(data, path[:-1])
    if parent is None:
        return None
    return indexed(parent[0].get(path[-2]))


def possible_rekey(
    row: Document, same_side: dict[int, Document], opposite: dict[int, Document],
) -> list[int]:
    """Retain possible replacement keys, not an inferred logical match."""
    labels = {k: row[k] for k in LABELS if isinstance(row.get(k), str) and row[k]}
    payload = fingerprint({k: v for k, v in row.items() if k != "id"})
    matches = []
    for key in sorted(opposite.keys() - same_side.keys()):
        other = opposite[key]
        other_payload = fingerprint({k: v for k, v in other.items() if k != "id"})
        if payload == other_payload or any(other.get(k) == v for k, v in labels.items()):
            matches.append(key)
    return matches


def replacement_signature(row: Document, data: Document) -> str | None:
    """Exact source record except its sibling key and resolved Peripheral IDs."""
    payload = {k: v for k, v in row.items() if k != "id"}
    if "peripheral" in payload:
        signature = peripheral_signature(payload["peripheral"], peripheral_definitions(data))
        if signature is None:
            return None
        payload["peripheral"] = signature
    return fingerprint(payload)


def exact_replacement(
    identity: int, present: dict[int, Document], absent: dict[int, Document],
    present_data: Document, absent_data: Document,
) -> int | None:
    """Require unique, mutual exact matching among disappearing/appearing siblings."""
    signature = replacement_signature(present[identity], present_data)
    if signature is None:
        return None
    same = [
        key for key in present.keys() - absent.keys()
        if replacement_signature(present[key], present_data) == signature
    ]
    other = [
        key for key in absent.keys() - present.keys()
        if replacement_signature(absent[key], absent_data) == signature
    ]
    return other[0] if same == [identity] and len(other) == 1 else None


def nested_signature(data: Document, path: list[Any], row: Document) -> str | None:
    """Exact parent labels and record shape, with local Peripheral rekeys normalized."""
    parent = record_at(data, path[:-1])
    if parent is None or not any(
        isinstance(row.get(k), str) and row[k] for k in ("name", "isc")
    ):
        return None
    parents = [
        {k: value[k] for k in ("id", "slug", "name", "isc", "category") if k in value}
        for value in parent[1]
    ]
    target = dict(row)
    if "peripheral" in target:
        signature = peripheral_signature(target["peripheral"], peripheral_definitions(data))
        if signature is None:
            return None
        target["peripheral"] = signature
    return fingerprint({"parents": parents, "target": target})


def group_nested(records: list[Document]) -> tuple[list[Document], Counter[str]]:
    buckets: dict[str, Document] = {}
    counts: Counter[str] = Counter()
    for record in records:
        if record["kind"] == "unitListMembership":
            continue
        signature = record.get("nestedSignature")
        if record["possibleReplacementIds"] or signature is None:
            counts["nestedNotGrouped"] += 1
            continue
        appeared = record["direction"] == "appeared"
        ev = record["evidence"]
        key_data = {
            "edition": "n5", "path": record["path"],
            "earlierObservedDate": ev["earlier"]["encodedRevisionDate"],
            "laterObservedDate": ev["later"]["encodedRevisionDate"],
            "before": {"present": not appeared}, "after": {"present": appeared},
            "earlierTargetFingerprint": None if appeared else signature,
            "laterTargetFingerprint": signature if appeared else None,
        }
        key = fingerprint(key_data)
        group = buckets.setdefault(key, {
            **key_data, "candidateId": key, "evidence": [],
        })
        require(all(e["factionId"] != ev["factionId"] for e in group["evidence"]),
                "Duplicate nested army evidence")
        group["evidence"].append(ev)
        counts["nestedGroupedOccurrences"] += 1
    groups, interval_counts = merge_compatible_intervals(list(buckets.values()))
    require(sum(len(g["evidence"]) for g in groups) == counts["nestedGroupedOccurrences"],
            "Nested evidence count differs")
    counts["nestedCandidateGroups"] = len(groups)
    counts.update({f"nestedWindow:{k}": v for k, v in interval_counts.items()})
    return groups, counts


def membership(source: HistoricalArmySource, pilot: Document, inventory: Document) -> Document:
    require(pilot.get("archiveSha256") == source.sha256, "Pilot archive pin differs")
    require(pilot.get("edition") == "n5" and pilot.get("formatVersion") == 1,
            "Unsupported pilot format")
    eligible = set(inventory["eligibleUnitIds"])
    dates: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for edition, army, day, sha in source.groups:
        if edition == "n5":
            dates[army][day].append(sha)
    expected = {
        (army, a, b) for army, days in dates.items()
        for a, b in pairwise(sorted(days)) if len(days[a]) == len(days[b]) == 1
    }
    seen = set()

    @lru_cache(maxsize=32)
    def data(sha: str) -> Document:
        return source.read_object(sha)

    # Full assigned inventory, including ambiguous same-day alternatives.
    observed: dict[int, dict[int, list[Document]]] = defaultdict(lambda: defaultdict(list))
    for unit in inventory["candidates"]:
        for slug in unit["slugEvidence"]:
            for item in slug["occurrences"]:
                observed[unit["unitId"]][item["factionId"]].append(item)

    records: list[Document] = []
    review: list[Document] = []
    declarations: list[Document] = []
    army_fields: list[Document] = []
    counts: Counter[str] = Counter()
    for ci, comparison in enumerate(pilot["comparisons"]):
        army = comparison["factionId"]
        earlier, later = comparison["earlier"], comparison["later"]
        start, end = earlier["encodedRevisionDate"], later["encodedRevisionDate"]
        pair = (army, start, end)
        require(pair in expected and pair not in seen, "Unexpected or repeated comparison")
        seen.add(pair)
        for endpoint in (earlier, later):
            key = ("n5", army, endpoint["encodedRevisionDate"], endpoint["sha256"])
            require(key in source.groups, "Unknown comparison endpoint")
            require(list(source.groups[key]) == endpoint["observationIndices"],
                    "Comparison observation evidence differs")
        old, new = data(earlier["sha256"]), data(later["sha256"])
        for ei, change in enumerate(comparison["changes"]):
            path = change["path"]
            category = change["category"]
            structural = category in {"observedKeyAppearance", "observedKeyDisappearance"}
            relevant = (
                structural or (
                    len(path) >= 3 and path[0] == "units"
                    and path[-1] in {"factions", "canonical", "idArmy", "ava", "disabled"}
                )
            )
            if not relevant:
                continue
            evidence = {
                "factionId": army, "comparisonIndex": ci, "changeIndex": ei,
                "earlier": earlier, "later": later,
            }
            event = {
                "unitId": path[1], "path": path, "before": change["before"],
                "after": change["after"], "evidence": evidence,
            }
            if path[1] not in eligible or change["ancestorOrRecordLabelChanged"]:
                review.append({**event, "reason": "identityReview"})
                counts["identityReview"] += 1
                continue
            if structural:
                a, b = child_collection(old, path), child_collection(new, path)
                require(a is not None and b is not None, "Unresolved child collection")
                assert a is not None and b is not None
                appeared = category == "observedKeyAppearance"
                identity = path[-1]
                present, absent = (b, a) if appeared else (a, b)
                side = "after" if appeared else "before"
                other_side = "before" if appeared else "after"
                require(identity in present and identity not in absent, "Presence differs")
                require(change[side]["present"] and not change[other_side]["present"],
                        "Recorded presence differs")
                row = present[identity]
                require(fingerprint(row) == fingerprint(change[side]["value"]),
                        "Structural evidence differs")
                replacements = possible_rekey(row, present, absent)
                kind = ("unitListMembership" if len(path) == 2 else
                        "profileGroup" if path[-2] == "profileGroups" else
                        "profile" if path[-2] == "profiles" else "loadout")
                event.update(kind=kind, direction="appeared" if appeared else "disappeared",
                             possibleReplacementIds=replacements)
                if kind == "unitListMembership":
                    event["sourceRole"] = source_role(row)
                    event["declaredInThisArmy"] = (
                        army in declared if (declared := declared_armies(row)) is not None else None
                    )
                    # Positive evidence only: absence from other lists is not established.
                    others = [
                        (other_army, item) for other_army, items in observed[path[1]].items()
                        if other_army != army for item in items
                        if (item["date"] <= start if appeared else item["date"] >= end)
                    ]
                    event["otherArmyEvidence"] = [{
                        "factionId": other_army, "date": item["date"], "sha256": item["sha256"],
                        "observationIndices": item["observationIndices"],
                    } for other_army, item in sorted(
                        others, key=lambda x: (x[1]["date"], x[0], x[1]["sha256"]),
                    )[:1]]
                else:
                    present_data, absent_data = (new, old) if appeared else (old, new)
                    exact = exact_replacement(identity, present, absent, present_data, absent_data)
                    event["exactRecordReplacementId"] = exact
                    if exact is not None:
                        event["possibleReplacementIds"] = sorted(set(replacements) | {exact})
                        counts["exactRecordReplacementOccurrence"] += 1
                    event["nestedSignature"] = nested_signature(present_data, path, row)
                records.append(event)
                counts[f"{kind}:{event['direction']}"] += 1
                if event["possibleReplacementIds"]:
                    counts["possibleReplacement"] += 1
                continue

            a, b = record_at(old, path), record_at(new, path)
            require(a is not None and b is not None, "Unresolved field path")
            assert a is not None and b is not None
            field = path[-1]
            for row, side in ((a[0], "before"), (b[0], "after")):
                saved = change[side]
                require((field in row) == saved["present"], "Field presence differs")
                if saved["present"]:
                    require(fingerprint(row[field]) == fingerprint(saved["value"]),
                            "Field evidence differs")
            if len(path) == 3 and field == "factions":
                before, after = declared_armies(a[0]), declared_armies(b[0])
                if before is None or after is None:
                    review.append({**event, "reason": "declaredMembershipShape"})
                    counts["declaredMembershipShape"] += 1
                    continue
                if before == after:
                    counts["declaredMembershipOrderOnly"] += 1
                    continue
                for direction, ids in (("added", after - before), ("removed", before - after)):
                    for target in sorted(ids):
                        declarations.append({
                            **event, "direction": direction, "declaredFactionId": target,
                        })
                        counts[f"declaredMembership:{direction}"] += 1
            elif field in {"ava", "disabled"}:
                army_fields.append({**event, "kind": field})
                counts[f"armyField:{field}"] += 1
            else:
                review.append({**event, "reason": "canonicalOrSourceIdentity"})
                counts["canonicalOrSourceIdentity"] += 1
    require(seen == expected, "Comparison coverage differs")

    # Declaration claims are not availability events. Corroborate only against
    # the actual list's matching directional observation window.
    list_events: dict[tuple[int, int, str], list[Document]] = defaultdict(list)
    for row in records:
        if row["kind"] == "unitListMembership" and not row["possibleReplacementIds"]:
            list_events[(row["unitId"], row["evidence"]["factionId"], row["direction"])].append(row)
    claims: dict[str, Document] = {}
    for row in declarations:
        ev = row["evidence"]
        start, end = ev["earlier"]["encodedRevisionDate"], ev["later"]["encodedRevisionDate"]
        key_data = {
            "unitId": row["unitId"], "declaredFactionId": row["declaredFactionId"],
            "direction": row["direction"], "earlierObservedDate": start,
            "laterObservedDate": end,
        }
        key = fingerprint(key_data)
        claim = claims.setdefault(key, {**key_data, "evidence": [], "listEvidence": []})
        claim["evidence"].append(ev)
        direction = "appeared" if row["direction"] == "added" else "disappeared"
        for candidate in list_events[(row["unitId"], row["declaredFactionId"], direction)]:
            other = candidate["evidence"]
            a, b = other["earlier"]["encodedRevisionDate"], other["later"]["encodedRevisionDate"]
            if max(a, start) < min(b, end) and other not in claim["listEvidence"]:
                claim["listEvidence"].append(other)
    counts["declaredClaimGroups"] = len(claims)
    counts["declaredClaimGroupsWithListEvidence"] = sum(
        bool(c["listEvidence"]) for c in claims.values()
    )
    counts["unitMembershipWithOtherArmyEvidence"] = sum(
        bool(e.get("otherArmyEvidence")) for e in records
    )
    groups, group_counts = group_nested(records)
    counts.update(group_counts)
    return {
        "formatVersion": 2, "archiveSha256": source.sha256, "edition": "n5",
        "comparedPairs": len(seen), "counts": dict(counts),
        "nestedCandidateGroups": groups,
        "structuralOccurrences": records, "declaredMembershipClaims": list(claims.values()),
        "armyFieldOccurrences": army_fields, "review": review,
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
    report = membership(source, document(raw), identity_inventory(source))
    report["pilotSha256"] = args.pilot_sha256
    summary = {k: v for k, v in report.items() if k not in {
        "structuralOccurrences", "declaredMembershipClaims", "armyFieldOccurrences", "review",
        "nestedCandidateGroups",
    }}
    summary["sourceRoleCounts"] = dict(Counter(
        e["sourceRole"] for e in report["structuralOccurrences"] if "sourceRole" in e
    ))
    summary["reviewExamples"] = report["review"][:5]
    summary["possibleReplacementExamples"] = [
        {k: v for k, v in e.items() if k not in {"before", "after"}}
        for e in report["structuralOccurrences"] if e["possibleReplacementIds"]
    ][:10]
    for path, payload in ((args.output, report), (args.summary_output, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if not k.endswith("Examples")},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
