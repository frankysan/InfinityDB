"""Private comparison of historical definitions behind persistent reference occurrences."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any

from infinity_db.army_history_characterization import fingerprint
from infinity_db.army_history_pilot import CHILDREN, LABELS, indexed
from infinity_db.army_history_references import CATALOGS, CONTEXT_FLAGS
from infinity_db.army_history_source import (
    Document,
    HistoricalArmySource,
    digest,
    document,
    read_history,
    require,
    verify_receipt,
)

LOCAL_FIELDS = (*CATALOGS, "peripheral", "extras")
WEAPON_FIELDS = frozenset({
    "ammunition", "burst", "damage", "saving", "savingNum", "properties", "distance",
})


def catalog_rows(data: Document, field: str, *, local: bool) -> dict[int, list[Document]]:
    rows = data.get(field)
    groups: dict[int, list[Document]] = defaultdict(list)
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and type(row.get("id")) is int:
                value = {k: v for k, v in row.items() if not local or k not in CONTEXT_FLAGS}
                groups[row["id"]].append(value)
    return {i: sorted(values, key=fingerprint) for i, values in groups.items()}


def consensus(
    contexts: list[dict[int, list[Document]]], identity: int,
) -> tuple[list[Document] | None, str]:
    if not contexts:
        return None, "noContext"
    variants = {fingerprint(c.get(identity)): c.get(identity) for c in contexts}
    if len(variants) != 1:
        return None, "ambiguousContext"
    value = next(iter(variants.values()))
    return (value, "resolved") if value is not None else (None, "missingCatalogId")


def changed_columns(a: list[Document], b: list[Document]) -> list[str]:
    """Compare per-column multisets without guessing a weapon-mode pairing."""
    keys = {k for row in a + b for k in row}
    return sorted(k for k in keys if
                  Counter(fingerprint([k in row, row.get(k)]) for row in a) !=
                  Counter(fingerprint([k in row, row.get(k)]) for row in b))


def classify(field: str, origin: str, a: list[Document], b: list[Document]) -> str:
    fields = set(changed_columns(a, b))
    if len(a) != len(b):
        return "recordMultiplicityReview"
    if not fields:
        return "recordAssociationReview"
    if fields <= {"wiki", "logo"}:
        return "linkOrPresentationReview"
    if fields & {"name", "slug", "isc", "type"}:
        return "definitionIdentityReview"
    if origin == "metadata" and field == "weapons" and fields <= WEAPON_FIELDS:
        return "weaponMechanicsCandidate"
    return "definitionContentReview"


def persistent_references(
    left: Document, right: Document,
) -> dict[tuple[str, int], list[Document]]:
    """Shared typed reference occurrences on stable, same-key record paths."""
    result: dict[tuple[str, int], list[Document]] = defaultdict(list)

    def refs(row: Document, field: str) -> dict[str, tuple[int, Document]]:
        values = row.get(field)
        if not isinstance(values, list):
            return {}
        found = {}
        for item in values:
            if isinstance(item, dict) and type(item.get("id")) is int:
                occurrence = {k: v for k, v in item.items() if k != "order"}
                found[fingerprint(occurrence)] = (item["id"], occurrence)
        return found

    def visit(a: Document, b: Document, level: str, path: list[Any]) -> None:
        if level != "faction" and any(
            fingerprint([k in a, a.get(k)]) != fingerprint([k in b, b.get(k)])
            for k in LABELS
        ):
            return
        if level in {"profile", "loadout", "unitOption"}:
            for field in (*CATALOGS, "peripheral"):
                old, new = refs(a, field), refs(b, field)
                for signature in sorted(old.keys() & new.keys()):
                    identity, value = old[signature]
                    evidence = {"path": [*path, field], "reference": value}
                    result[(field, identity)].append(evidence)
                    if field in CATALOGS and isinstance(value.get("extra"), list):
                        for extra in sorted({i for i in value["extra"] if type(i) is int}):
                            result[("extras", extra)].append(evidence)
        for field, child in CHILDREN.get(level, {}).items():
            old, new = indexed(a.get(field)), indexed(b.get(field))
            if old is not None and new is not None:
                for identity in sorted(old.keys() & new.keys()):
                    visit(old[identity], new[identity], child, [*path, field, identity])

    visit(left, right, "faction", [])
    return result


def compare_definitions(
    source: HistoricalArmySource, pilot: Document,
) -> Document:
    require(pilot.get("archiveSha256") == source.sha256, "Pilot archive pin differs")
    require(pilot.get("edition") == "n5" and pilot.get("formatVersion") == 1,
            "Unsupported pilot format")
    dates: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for edition, army, day, sha in source.groups:
        if edition == "n5":
            dates[army][day].append(sha)
    expected = {
        (army, a, b) for army, days in dates.items()
        for a, b in pairwise(sorted(days)) if len(days[a]) == len(days[b]) == 1
    }

    @lru_cache(maxsize=32)
    def data(sha: str) -> Document:
        return source.read_object(sha)

    @lru_cache(maxsize=64)
    def metadata(sha: str, field: str) -> dict[int, list[Document]]:
        return catalog_rows(data(sha), CATALOGS[field], local=False)

    def endpoint_context(endpoint: Document, army: int) -> list[str]:
        key = ("n5", army, endpoint["encodedRevisionDate"], endpoint["sha256"])
        require(key in source.groups, "Unknown comparison endpoint")
        require(list(source.groups[key]) == endpoint["observationIndices"],
                "Observation evidence differs")
        refs = sorted({
            sha for i in source.groups[key] for sha in source.metadata_contexts.get(i, ())
            if sha is not None
        })
        require(refs == endpoint["metadataSha256"], "Metadata evidence differs")
        return refs

    seen = set()
    groups: dict[str, Document] = {}
    counts: Counter[str] = Counter()
    review: list[Document] = []
    for ci, comparison in enumerate(pilot["comparisons"]):
        army = comparison["factionId"]
        earlier, later = comparison["earlier"], comparison["later"]
        start, end = earlier["encodedRevisionDate"], later["encodedRevisionDate"]
        pair = (army, start, end)
        require(pair in expected and pair not in seen, "Unexpected or repeated comparison")
        seen.add(pair)
        old_context, new_context = endpoint_context(earlier, army), endpoint_context(later, army)
        old, new = data(earlier["sha256"]), data(later["sha256"])
        refs = persistent_references(old, new)
        old_filters, new_filters = old.get("filters", {}), new.get("filters", {})
        require(isinstance(old_filters, dict) and isinstance(new_filters, dict),
                "Invalid faction filters")
        evidence = {"factionId": army, "comparisonIndex": ci,
                    "earlier": earlier, "later": later}

        for field in LOCAL_FIELDS:
            a_local, b_local = (catalog_rows(f, field, local=True)
                                for f in (old_filters, new_filters))
            a_meta = [metadata(sha, field) for sha in old_context] if field in CATALOGS else []
            b_meta = [metadata(sha, field) for sha in new_context] if field in CATALOGS else []
            for (ref_field, identity), usages in refs.items():
                if ref_field != field:
                    continue
                for origin in ("factionFilter", "metadata"):
                    if origin == "metadata" and field not in CATALOGS:
                        continue
                    if origin == "factionFilter":
                        a, b = a_local.get(identity), b_local.get(identity)
                        if a is None or b is None:
                            status = "missingLocalDefinition"
                        elif len(a) != 1 or len(b) != 1:
                            status = "duplicateLocalDefinition"
                        else:
                            status = "resolved"
                    else:
                        a, a_status = consensus(a_meta, identity)
                        b, b_status = consensus(b_meta, identity)
                        status = (
                            "ambiguousContext" if "ambiguousContext" in (a_status, b_status)
                            else a_status if a_status != "resolved" else b_status
                        )
                    prefix = f"{origin}:{field}"
                    if status != "resolved":
                        counts[f"{prefix}:{status}"] += 1
                        # Missing entries at both endpoints are coverage gaps,
                        # not definition changes. Retain other unresolved cases.
                        if status != "missingCatalogId" or a is not None or b is not None:
                            review.append({**evidence, "origin": origin, "field": field,
                                           "id": identity, "status": status, "usages": usages})
                        continue
                    assert a is not None and b is not None
                    if fingerprint(a) == fingerprint(b):
                        counts[f"{prefix}:unchanged"] += 1
                        continue
                    category = classify(field, origin, a, b)
                    counts[f"{prefix}:{category}"] += 1
                    # Local Peripheral and extra IDs may be army-scoped.
                    # Scope all local definitions; only metadata transitions
                    # with identical before/after records can group across armies.
                    payload = {
                        "origin": origin, "field": field, "id": identity,
                        "scopeArmyId": army if origin == "factionFilter" else None,
                        "before": a, "after": b, "category": category,
                        "changedFields": changed_columns(a, b),
                    }
                    key = fingerprint(payload)
                    group = groups.setdefault(key, {
                        **payload, "definitionTransitionId": key, "evidence": [],
                    })
                    group["evidence"].append({**evidence, "usages": usages})
    require(seen == expected, "Comparison coverage differs")
    transitions = sorted(groups.values(), key=lambda g: g["definitionTransitionId"])
    return {
        "formatVersion": 1, "archiveSha256": source.sha256, "edition": "n5",
        "comparedPairs": len(seen), "counts": dict(counts),
        "transitionGroups": transitions, "review": review,
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
    result = compare_definitions(source, document(raw))
    result["pilotSha256"] = args.pilot_sha256
    groups = result["transitionGroups"]
    summary = {k: v for k, v in result.items() if k not in {"transitionGroups", "review"}}
    summary["groupsByOriginField"] = dict(Counter(
        f"{g['origin']}:{g['field']}" for g in groups
    ))
    summary["groupsByCategory"] = dict(Counter(g["category"] for g in groups))
    summary["changedDefinitionComparisons"] = sum(len(g["evidence"]) for g in groups)
    summary["affectedReferenceLocations"] = sum(
        len(e["usages"]) for g in groups for e in g["evidence"]
    )
    summary["reviewCount"] = len(result["review"])
    summary["examples"] = [
        {k: v for k, v in g.items() if k != "evidence"}
        | {"exampleEvidence": {k: v for k, v in g["evidence"][0].items() if k != "usages"}}
        for g in groups[:10]
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
