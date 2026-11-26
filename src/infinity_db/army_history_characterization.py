"""Offline historical Army structure and identifier characterization.

Counts describe observed source records, not canonical identities or releases.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations, pairwise
from pathlib import Path
from typing import Any

from infinity_db.army_history_source import (
    Document,
    HistoricalArmySource,
    digest,
    read_history,
    verify_receipt,
)

LEVELS = ("unit", "group", "profile", "loadout", "unitOption")
IdKey = tuple[int, ...]


def fingerprint(value: Any) -> str:
    """Ignore JSON object key order, but retain types and all array ordering."""
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def label(row: Document) -> str | None:
    values = {key: row[key] for key in ("slug", "isc", "name") if row.get(key)}
    return fingerprint(values) if values else None


def shape(row: Document, level: str, fields: Counter[str]) -> None:
    for key, value in row.items():
        fields[f"{level}.{key}:{type(value).__name__}"] += 1


@dataclass
class FactionShape:
    full: str
    without_revision: str
    fields: Counter[str] = field(default_factory=Counter)
    issues: Counter[str] = field(default_factory=Counter)
    identities: dict[str, dict[IdKey, str | None]] = field(
        default_factory=lambda: {level: {} for level in LEVELS},
    )
    reference_ids: dict[str, set[int]] = field(default_factory=lambda: defaultdict(set))


def characterize_faction(data: Document) -> FactionShape:
    result = FactionShape(
        fingerprint(data), fingerprint({k: v for k, v in data.items() if k != "version"}),
    )
    shape(data, "faction", result.fields)

    def visit(value: Any, level: str, parent: IdKey | None) -> None:
        if not isinstance(value, list):
            result.issues[f"{level}.missingOrNonArray"] += 1
            return
        for row in value:
            if not isinstance(row, dict):
                result.issues[f"{level}.nonObject"] += 1
                continue
            shape(row, level, result.fields)
            identity = row.get("id")
            key = None
            if type(identity) is not int:
                result.issues[f"{level}.missingOrNonIntegerId"] += 1
            elif parent is not None:
                key = (*parent, identity)
                if key in result.identities[level]:
                    result.issues[f"{level}.duplicateScopedId"] += 1
                else:
                    result.identities[level][key] = label(row)
            if level in ("profile", "loadout", "unitOption"):
                for field_name, catalog in (("skills", "skills"), ("equip", "equips"),
                                            ("weapons", "weapons")):
                    references = row.get(field_name, [])
                    if not isinstance(references, list):
                        result.issues[f"{level}.{field_name}.nonArray"] += 1
                        continue
                    for reference in references:
                        if isinstance(reference, dict):
                            shape(reference, f"{level}.{field_name}[]", result.fields)
                        ref = reference.get("id") if isinstance(reference, dict) else reference
                        if type(ref) is int:
                            result.reference_ids[catalog].add(ref)
                        else:
                            result.issues[f"{level}.{field_name}.nonIntegerReference"] += 1
            if level == "unit":
                visit(row.get("profileGroups"), "group", key)
                if "options" in row:
                    visit(row["options"], "unitOption", key)
            elif level == "group":
                visit(row.get("profiles"), "profile", key)
                visit(row.get("options"), "loadout", key)

    visit(data.get("units"), "unit", ())
    return result


def compare_content(left: FactionShape, right: FactionShape) -> str:
    if left.full == right.full:
        return "parsedJsonEqual"
    if left.without_revision == right.without_revision:
        return "revisionFieldOnly"
    return "otherContentDifference"


def compare_identities(left: FactionShape, right: FactionShape) -> dict[str, Counter[str]]:
    """Compare scoped numeric keys, without asserting continuity of entities."""
    result = {}
    for level in LEVELS:
        counts: Counter[str] = Counter()
        ancestors = {
            "unit": ("unit",), "group": ("unit", "group"),
            "profile": ("unit", "group", "profile"),
            "loadout": ("unit", "group", "loadout"),
            "unitOption": ("unit", "unitOption"),
        }[level]
        if any(
            key.split(".")[0] in ancestors and key.count(".") == 1
            for source in (left, right) for key in source.issues
        ):
            counts["shapeIssueSkippedPairs"] += 1
        else:
            a, b = left.identities[level], right.identities[level]
            common = a.keys() & b.keys()
            counts["sharedKeys"] = len(common)
            counts["leftOnlyKeys"] = len(a.keys() - b.keys())
            counts["rightOnlyKeys"] = len(b.keys() - a.keys())
            for key in common:
                if a[key] is None or b[key] is None:
                    counts["sharedKeyMissingLabel"] += 1
                elif a[key] == b[key]:
                    counts["sharedKeyEqualLabel"] += 1
                else:
                    counts["sharedKeyChangedLabel"] += 1
            # Same label under the same parent is only a candidate for ID change.
            # Require uniqueness across both complete sibling sets.
            def labels(rows: dict[IdKey, str | None]) -> dict[tuple[IdKey, str], list[IdKey]]:
                found: dict[tuple[IdKey, str], list[IdKey]] = defaultdict(list)
                for key, name in rows.items():
                    if name is not None:
                        found[(key[:-1], name)].append(key)
                return found

            old, new = labels(a), labels(b)
            counts["uniqueSiblingLabelDifferentKey"] = sum(
                len(old[k]) == len(new[k]) == 1
                and old[k][0] not in b and new[k][0] not in a
                for k in old.keys() & new.keys()
            )
        result[level] = counts
    return result


def characterize(source: HistoricalArmySource) -> Document:
    rows = source.index["observations"]
    editions: dict[str, set[str]] = defaultdict(set)
    kinds = {}
    for row in rows:
        editions[row["edition"]].add(row["sha256"])
        kinds[row["sha256"]] = row["kind"]
    factions: dict[str, FactionShape] = {}
    metadata: dict[str, Document] = {}
    for sha in sorted(kinds):
        data = source.read_object(sha)
        if kinds[sha] == "faction":
            factions[sha] = characterize_faction(data)
        else:
            metadata[sha] = data

    reports = {}
    metadata_ids = {
        sha: {
            name: {row["id"] for row in values
                   if isinstance(row, dict) and type(row.get("id")) is int}
            for name, values in data.items() if isinstance(values, list)
        }
        for sha, data in metadata.items()
    }
    for edition, hashes in sorted(editions.items()):
        fields: Counter[str] = Counter()
        issues: Counter[str] = Counter()
        totals: Counter[str] = Counter()
        catalogs: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
        catalog_documents: Counter[str] = Counter()
        for sha in sorted(hashes):
            if sha in factions:
                item = factions[sha]
                fields.update(item.fields)
                issues.update(item.issues)
                totals.update({level: len(keys) for level, keys in item.identities.items()})
            else:
                data = metadata[sha]
                shape(data, "metadata", fields)
                for name, values in data.items():
                    if not isinstance(values, list):
                        continue
                    catalog_documents[name] += 1
                    for row in values:
                        if isinstance(row, dict):
                            shape(row, f"metadata.{name}[]", fields)
                            if type(row.get("id")) is int:
                                catalogs[name][row["id"]].add(fingerprint(row))
        sequences: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        context_counts: Counter[str] = Counter()
        reference_coverage: dict[str, Counter[str]] = defaultdict(Counter)
        for (ed, faction, day, sha), indices in source.groups.items():
            if ed != edition:
                continue
            sequences[faction][day].append(sha)
            refs = {ref for i in indices for ref in source.metadata_contexts[i] if ref is not None}
            context_counts["assignedContents"] += 1
            context_counts["withContext" if refs else "withoutContext"] += 1
            context_counts["multipleMetadataObjects"] += len(refs) > 1
            if refs:
                present = [
                    any(
                        isinstance(row, dict) and row.get("id") == faction
                        for row in metadata[ref]["factions"]
                    )
                    for ref in refs
                ]
                context_counts["factionIdInEveryContext"] += all(present)
                context_counts["factionIdInSomeButNotAllContexts"] += (
                    any(present) and not all(present)
                )
                context_counts["factionIdInNoContext"] += not any(present)
            for catalog, ids in factions[sha].reference_ids.items():
                counts = reference_coverage[catalog]
                for identity in ids:
                    if not refs:
                        counts["noContext"] += 1
                        continue
                    matches = [identity in metadata_ids[ref].get(catalog, set()) for ref in refs]
                    if all(matches):
                        counts["inEveryContext"] += 1
                    elif any(matches):
                        counts["inSomeContexts"] += 1
                    else:
                        counts["inNoContextCatalog"] += 1
        comparisons: Counter[str] = Counter()
        same_day: Counter[str] = Counter()
        identities: dict[str, Counter[str]] = {level: Counter() for level in LEVELS}
        examples: dict[str, list[Document]] = defaultdict(list)
        coverage = []
        for faction, days in sorted(sequences.items()):
            ordered = sorted(days)
            coverage.append({
                "factionId": faction, "firstObservedRevisionDate": ordered[0],
                "lastObservedRevisionDate": ordered[-1], "observedDates": len(ordered),
                "sameDayAlternativeDates": sum(len(v) > 1 for v in days.values()),
                "maximumObservedDateGapDays": max(
                    ((date.fromisoformat(b) - date.fromisoformat(a)).days
                     for a, b in pairwise(ordered)), default=0,
                ),
            })
            for day in ordered:
                for a, b in combinations(sorted(days[day]), 2):
                    same_day[compare_content(factions[a], factions[b])] += 1
            for first, last in pairwise(ordered):
                if len(days[first]) != 1 or len(days[last]) != 1:
                    comparisons["ambiguousEndpointSkipped"] += 1
                    continue
                a, b = days[first][0], days[last][0]
                category = compare_content(factions[a], factions[b])
                comparisons[category] += 1
                if len(examples[category]) < 5:
                    examples[category].append({
                        "factionId": faction, "earlierDate": first, "laterDate": last,
                        "earlierSha256": a, "laterSha256": b,
                    })
                for level, counts in compare_identities(factions[a], factions[b]).items():
                    identities[level].update(counts)
        reports[edition] = {
            "uniqueFactionObjects": len(hashes & factions.keys()),
            "uniqueMetadataObjects": len(hashes & metadata.keys()),
            "unresolvedContents": len({
                rows[i]["sha256"] for i in source.unresolved if rows[i]["edition"] == edition
            }),
            "recordFieldsByType": dict(fields),
            "shapeIssues": dict(issues), "uniqueObjectScopedKeyTotals": dict(totals),
            "metadataCatalogs": {
                name: {
                    "documentsWithArray": catalog_documents[name],
                    "distinctIntegerIds": len(catalogs[name]),
                    "idsWithMultipleRecordFingerprints": sum(
                        len(v) > 1 for v in catalogs[name].values()
                    ),
                }
                for name in sorted(catalog_documents)
            },
            "metadataContexts": dict(context_counts),
            "contextualReferenceIdCoverage": {
                name: dict(counts) for name, counts in reference_coverage.items()
            },
            "factionCoverage": coverage,
            "adjacentObservedDateComparisons": dict(comparisons),
            "unorderedSameDayPairs": dict(same_day),
            "scopedIdentityComparisons": {level: dict(c) for level, c in identities.items()},
            "comparisonExamples": dict(examples),
        }
    unit_keys = {
        edition: {
            key for sha in hashes & factions.keys() for key in factions[sha].identities["unit"]
        }
        for edition, hashes in editions.items()
    }
    return {
        "formatVersion": 1, "archiveSha256": source.sha256,
        "coverage": source.index["coverage"], "editions": reports,
        "crossEditionSharedUnitNumericIds": {
            f"{a}/{b}": len(unit_keys[a] & unit_keys[b])
            for a, b in combinations(sorted(unit_keys), 2)
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = read_history(args.archive, args.sha256)
    verify_receipt(source, args.receipt, args.receipt_sha256)
    report = characterize(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({
        "archiveSha256": report["archiveSha256"],
        "editions": {
            ed: {k: v for k, v in data.items() if k not in {
                "recordFieldsByType", "factionCoverage", "comparisonExamples", "metadataCatalogs",
            }}
            for ed, data in report["editions"].items()
        },
        "crossEditionSharedUnitNumericIds": report["crossEditionSharedUnitNumericIds"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
