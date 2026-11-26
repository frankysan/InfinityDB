"""Private N5 observed-source comparison pilot, not a canonical change log."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any

from infinity_db.army_history_characterization import fingerprint
from infinity_db.army_history_source import (
    Document,
    GroupKey,
    HistoricalArmySource,
    read_history,
    verify_receipt,
)

CHILDREN = {
    "faction": {"units": "unit"},
    "unit": {"profileGroups": "group", "options": "unitOption"},
    "group": {"profiles": "profile", "options": "loadout"},
}
LABELS = frozenset({"name", "isc", "iscAbbr", "slug"})
PRESENTATION = frozenset({"logo", "notes"})
STATS = frozenset({"arm", "bs", "bts", "cc", "move", "ph", "s", "str", "w", "wip"})
REFERENCES = {"skills": "skills", "equip": "equips", "weapons": "weapons"}
GAME_FIELDS = {
    "profile": STATS | {"ava", "chars", "type", "includes"},
    "group": {"category"},
    "loadout": {"points", "swc", "chars", "orders", "includes"},
    "unitOption": {"points", "swc", "chars", "orders", "includes"},
}
MISSING = object()


def same(left: Any, right: Any) -> bool:
    if left is MISSING or right is MISSING:
        return left is right
    # Preserve JSON types (True != 1) and array ordering.
    return fingerprint(left) == fingerprint(right)


def recorded(value: Any) -> Document:
    return {"present": False} if value is MISSING else {"present": True, "value": value}


def indexed(value: Any) -> dict[int, Document] | None:
    if not isinstance(value, list):
        return None
    result: dict[int, Document] = {}
    for item in value:
        if not isinstance(item, dict) or type(item.get("id")) is not int:
            return None
        if item["id"] in result:
            return None
        result[item["id"]] = item
    return result


def ref_content(value: Any) -> Counter[str] | None:
    """Recognize pure reference display ordering without removing quantities/extras."""
    if not isinstance(value, list):
        return None
    if any(not isinstance(v, dict) or type(v.get("id")) is not int for v in value):
        return None
    return Counter(fingerprint({k: x for k, x in v.items() if k != "order"}) for v in value)


def field_category(level: str, key: str, a: Any, b: Any) -> str:
    if a is MISSING or b is MISSING:
        return "fieldPresenceReview"
    if key in LABELS and level != "faction":
        return "identityLabelReview"
    if key in PRESENTATION and level != "faction":
        return "presentationReview"
    if level == "unit" and key in {"canonical", "idArmy", "factions"}:
        return "availabilityOrIdentityReview"
    if level != "faction" and key == "peripheral":
        # Peripheral IDs are army-local; do not infer a gameplay change from a
        # changed reference without resolving its army-specific definition.
        return "peripheralReferenceReview"
    if level != "faction" and key in REFERENCES:
        left, right = ref_content(a), ref_content(b)
        if left is None or right is None:
            return "referenceShapeReview"
        if left == right:
            return "referenceDisplayOrderOnly"
        return "referenceContentReview"
    if key in GAME_FIELDS.get(level, frozenset()):
        return "gameplayFieldCandidate"
    if key == "filters":
        return "filterReview"
    return "unclassifiedFieldReview"


def peripheral_definitions(data: Document) -> dict[int, str]:
    """Use exact, unique army-local definitions, ignoring their source ID only."""
    filters = data.get("filters")
    rows = indexed(filters.get("peripheral")) if isinstance(filters, dict) else None
    if rows is None:
        return {}
    values = {
        identity: fingerprint({k: v for k, v in row.items() if k != "id"})
        for identity, row in rows.items() if isinstance(row.get("name"), str) and row["name"]
    }
    counts = Counter(values.values())
    return {identity: value for identity, value in values.items() if counts[value] == 1}


def peripheral_signature(value: Any, definitions: dict[int, str]) -> str | None:
    if not isinstance(value, list):
        return None
    normalized = []
    for row in value:
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            return None
        definition = definitions.get(row["id"])
        if definition is None:
            return None
        normalized.append({
            "definition": definition, "reference": {k: v for k, v in row.items() if k != "id"},
        })
    return fingerprint(normalized)


def compare_faction(left: Document, right: Document) -> list[Document]:
    """Emit changed-field evidence, without assuming logical identity."""
    changes: list[Document] = []
    left_peripherals = peripheral_definitions(left)
    right_peripherals = peripheral_definitions(right)

    def emit(category: str, path: list[Any], a: Any, b: Any, label_changed: bool) -> None:
        changes.append({
            "category": category, "path": path,
            "before": recorded(a), "after": recorded(b),
            "ancestorOrRecordLabelChanged": label_changed,
        })

    def visit(a: Document, b: Document, level: str, path: list[Any],
              ancestor_changed: bool = False) -> None:
        if same(a, b):
            return
        label_changed = ancestor_changed or (
            level != "faction" and any(
                not same(a.get(k, MISSING), b.get(k, MISSING)) for k in LABELS
            )
        )
        for key in sorted(a.keys() | b.keys()):
            av, bv = a.get(key, MISSING), b.get(key, MISSING)
            if same(av, bv):
                continue
            child = CHILDREN.get(level, {}).get(key)
            if child is not None:
                old, new = indexed(av), indexed(bv)
                if old is None or new is None:
                    emit("childShapeReview", [*path, key], av, bv, label_changed)
                    continue
                for identity in sorted(old.keys() | new.keys()):
                    child_path = [*path, key, identity]
                    if identity not in old:
                        emit("observedKeyAppearance", child_path, MISSING,
                             new[identity], label_changed)
                    elif identity not in new:
                        emit("observedKeyDisappearance", child_path, old[identity],
                             MISSING, label_changed)
                    else:
                        visit(old[identity], new[identity], child, child_path, label_changed)
                old_order = [k for k in old if k in new]
                new_order = [k for k in new if k in old]
                if old_order != new_order:
                    emit("sharedChildOrderChanged", [*path, key],
                         old_order, new_order, label_changed)
            elif level == "faction" and key == "version":
                emit("sourceRevisionField", [key], av, bv, False)
            else:
                category = field_category(level, key, av, bv)
                if category == "peripheralReferenceReview":
                    old_signature = peripheral_signature(av, left_peripherals)
                    new_signature = peripheral_signature(bv, right_peripherals)
                    if old_signature is not None and old_signature == new_signature:
                        category = "peripheralDefinitionEquivalentRekey"
                emit(category, [*path, key], av, bv, label_changed)

    visit(left, right, "faction", [])
    return changes


def collect_references(
    data: Document, examples: list[Document] | None = None,
) -> tuple[dict[str, set[int]], Counter[str]]:
    ids: dict[str, set[int]] = defaultdict(set)
    issues: Counter[str] = Counter()

    def visit(row: Document, level: str, path: list[Any]) -> None:
        for field, catalog in REFERENCES.items():
            if level not in {"profile", "loadout", "unitOption"} or field not in row:
                continue
            values = row[field]
            if not isinstance(values, list):
                issues[f"{level}.{field}.notArray"] += 1
                continue
            for position, value in enumerate(values):
                if isinstance(value, dict) and type(value.get("id")) is int:
                    ids[catalog].add(value["id"])
                else:
                    # Distinguish anonymous objects from malformed IDs.
                    issue = ("anonymous" if isinstance(value, dict) and value.get("id") is None
                             else "otherShape")
                    issues[f"{level}.{field}.{issue}"] += 1
                    if examples is not None and len(examples) < 3:
                        examples.append({
                            "path": [*path, field, position], "value": value, "issue": issue,
                        })
        for field, child in CHILDREN.get(level, {}).items():
            values = row.get(field, [])
            if isinstance(values, list):
                for position, item in enumerate(values):
                    if isinstance(item, dict):
                        visit(item, child, [*path, field, position])

    visit(data, "faction", [])
    return ids, issues


def catalog_index(data: Document) -> dict[str, dict[int, tuple[str, ...]]]:
    result: dict[str, dict[int, tuple[str, ...]]] = {}
    for catalog in REFERENCES.values():
        groups: dict[int, list[str]] = defaultdict(list)
        values = data.get(catalog)
        if isinstance(values, list):
            for row in values:
                if isinstance(row, dict) and type(row.get("id")) is int:
                    groups[row["id"]].append(fingerprint(row))
        result[catalog] = {k: tuple(sorted(v)) for k, v in groups.items()}
    return result


def faction_filter_ids(data: Document) -> dict[str, set[int]]:
    filters = data.get("filters")
    if not isinstance(filters, dict):
        return {}
    result = {}
    for source, catalog in REFERENCES.items():
        values = filters.get(source)
        if isinstance(values, list):
            result[catalog] = {
                row["id"] for row in values
                if isinstance(row, dict) and type(row.get("id")) is int
            }
    return result


def compare_catalog_contexts(
    left_refs: dict[str, set[int]], right_refs: dict[str, set[int]],
    left: list[dict[str, dict[int, tuple[str, ...]]]],
    right: list[dict[str, dict[int, tuple[str, ...]]]],
) -> tuple[list[Document], Counter[str]]:
    """Only compare shared referenced IDs; never select a preferred metadata context."""
    findings = []
    counts: Counter[str] = Counter()
    for catalog in sorted(REFERENCES.values()):
        for identity in sorted(left_refs.get(catalog, set()) & right_refs.get(catalog, set())):
            a = {x[catalog].get(identity) for x in left}
            b = {x[catalog].get(identity) for x in right}
            if not left or not right:
                category = "noContext"
            elif None in a or None in b:
                category = "missingCatalogId"
            elif len(a) != 1 or len(b) != 1:
                category = "ambiguousContext"
            elif a != b:
                category = "catalogRecordDifference"
            else:
                counts["unchangedCatalogRecord"] += 1
                continue
            counts[category] += 1
            findings.append({
                "catalog": catalog, "id": identity, "category": category,
                "beforeFingerprints": sorted(a, key=str),
                "afterFingerprints": sorted(b, key=str),
            })
    return findings, counts


def pilot(source: HistoricalArmySource) -> Document:
    sequences: dict[int, dict[str, list[GroupKey]]] = defaultdict(lambda: defaultdict(list))
    for key in source.groups:
        edition, faction, day, _ = key
        if edition == "n5":
            sequences[faction][day].append(key)

    @lru_cache(maxsize=32)
    def faction_object(sha: str) -> Document:
        return source.read_object(sha)

    @lru_cache(maxsize=64)
    def metadata_object(sha: str) -> dict[str, dict[int, tuple[str, ...]]]:
        return catalog_index(source.read_object(sha))

    def context(key: GroupKey) -> list[str]:
        return sorted({
            sha for i in source.groups[key] for sha in source.metadata_contexts[i]
            if sha is not None
        })

    def endpoint(key: GroupKey) -> Document:
        return {
            "encodedRevisionDate": key[2], "sha256": key[3],
            "observationIndices": list(source.groups[key]),
            "metadataSha256": context(key),
        }

    results = []
    skipped = []
    counts: Counter[str] = Counter()
    metadata_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    missing_metadata_filters: Counter[str] = Counter()
    reference_shape_counts: Counter[str] = Counter()
    reference_shape_examples: list[Document] = []
    seen_reference_documents: set[str] = set()
    examples: dict[str, list[Document]] = defaultdict(list)
    for faction, days in sorted(sequences.items()):
        for a, b in pairwise(sorted(days)):
            if len(days[a]) != 1 or len(days[b]) != 1:
                skipped.append({
                    "factionId": faction,
                    "earlier": [endpoint(k) for k in sorted(days[a])],
                    "later": [endpoint(k) for k in sorted(days[b])],
                })
                continue
            old_key, new_key = days[a][0], days[b][0]
            old, new = faction_object(old_key[3]), faction_object(new_key[3])
            changes = compare_faction(old, new)
            def references(key: GroupKey, data: Document):
                samples: list[Document] = []
                ids, issues = collect_references(data, samples)
                if key[3] not in seen_reference_documents:
                    seen_reference_documents.add(key[3])
                    reference_shape_counts.update(issues)
                    for sample in samples:
                        if len(reference_shape_examples) < 8:
                            reference_shape_examples.append({
                                "endpoint": endpoint(key), **sample,
                            })
                return ids, issues

            old_refs, old_issues = references(old_key, old)
            new_refs, new_issues = references(new_key, new)
            metadata, mc = compare_catalog_contexts(
                old_refs, new_refs,
                [metadata_object(s) for s in context(old_key)],
                [metadata_object(s) for s in context(new_key)],
            )
            old_filters, new_filters = faction_filter_ids(old), faction_filter_ids(new)
            for finding in metadata:
                if finding["category"] != "missingCatalogId":
                    continue
                catalog, identity = finding["catalog"], finding["id"]
                a_has = identity in old_filters.get(catalog, set())
                b_has = identity in new_filters.get(catalog, set())
                finding["inEarlierFactionFilter"] = a_has
                finding["inLaterFactionFilter"] = b_has
                status = ("both" if a_has and b_has else "one" if a_has or b_has else "neither")
                missing_metadata_filters[f"{catalog}:{status}"] += 1
            counts.update(c["category"] for c in changes)
            for change in changes:
                category = change["category"]
                path = change["path"]
                field = path[-1] if isinstance(path[-1], str) else path[-2]
                field_key = f"{category}:{field}"
                field_counts[field_key] += 1
                if len(examples[field_key]) >= 2:
                    continue
                example = {
                    "factionId": faction, "earlier": a, "later": b,
                    "earlierSha256": old_key[3], "laterSha256": new_key[3],
                    "path": path,
                }
                for side in ("before", "after"):
                    value = change[side]
                    if len(json.dumps(value)) <= 250:
                        example[side] = value
                examples[field_key].append(example)
            metadata_counts.update(mc)
            results.append({
                "factionId": faction, "earlier": endpoint(old_key), "later": endpoint(new_key),
                "changes": changes, "sharedReferenceMetadataFindings": metadata,
                "earlierReferenceShapeIssues": dict(old_issues),
                "laterReferenceShapeIssues": dict(new_issues),
            })
    return {
        "formatVersion": 1, "archiveSha256": source.sha256, "edition": "n5",
        "coverage": source.index["coverage"], "comparisonCount": len(results),
        "ambiguousEndpointPairs": len(skipped),
        "changeCounts": dict(counts), "sharedReferenceMetadataCounts": dict(metadata_counts),
        "fieldCounts": dict(field_counts), "examples": dict(examples),
        "missingMetadataFactionFilterMembership": dict(missing_metadata_filters),
        "comparedUniqueFactionDocuments": len(seen_reference_documents),
        "comparedUniqueDocumentReferenceShapeIssues": dict(reference_shape_counts),
        "referenceShapeExamples": reference_shape_examples,
        "comparisons": results, "skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()
    source = read_history(args.archive, args.sha256)
    verify_receipt(source, args.receipt, args.receipt_sha256)
    report = pilot(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
    summary = {k: v for k, v in report.items() if k not in {"comparisons", "skipped"}}
    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        with args.summary_output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps({
        k: v for k, v in summary.items() if k not in {"examples", "referenceShapeExamples"}
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
