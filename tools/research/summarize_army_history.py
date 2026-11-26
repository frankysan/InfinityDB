"""Private effective-loadout history pilot, derived from accepted N5 evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from contextlib import closing
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

from infinity_db.army_history_loadouts import composition
from infinity_db.army_history_pilot import catalog_index, indexed
from infinity_db.army_history_references import CATALOGS, resolve_references
from infinity_db.army_history_source import Document, digest, file_digest, read_history, require
from tools.research.build_army_history_database import ARCHIVE_PIN, encode
from tools.research.project_army_history import ARMY, HISTORY, ROOT, read_only
from tools.research.render_army_history import FIELDS

FIELDS_SUPPORTED = frozenset((*CATALOGS, "points", "swc"))
LABELS = ("name", "isc", "iscAbbr", "slug", "category")


def same_labels(a: Document, b: Document) -> bool:
    return all(a.get(key) == b.get(key) for key in LABELS)


def get_group(data: Document, unit_id: int, group_id: int) -> tuple[Document, Document] | None:
    units = indexed(data.get("units"))
    if units is None or unit_id not in units:
        return None
    unit = units[unit_id]
    groups = indexed(unit.get("profileGroups"))
    if groups is None or group_id not in groups:
        return None
    return unit, groups[group_id]


def stable_context(
    old: Document, new: Document, unit: int, group: int, *, allow_empty: bool = False,
) -> tuple[tuple[Document, dict[int, Document], Document, dict[int, Document]] | None, str]:
    a, b = get_group(old, unit, group), get_group(new, unit, group)
    if a is None or b is None:
        return None, "missingGroup"
    if not same_labels(a[0], b[0]) or not same_labels(a[1], b[1]):
        return None, "changedLabels"
    profiles_a, profiles_b = indexed(a[1].get("profiles")), indexed(b[1].get("profiles"))
    if (profiles_a is None or profiles_b is None or len(profiles_a) != 1
            or profiles_a.keys() != profiles_b.keys()):
        return None, "multiProfileOrChangedProfile"
    pa, pb = next(iter(profiles_a.values())), next(iter(profiles_b.values()))
    if not same_labels(pa, pb):
        return None, "changedLabels"
    oa, ob = indexed(a[1].get("options")), indexed(b[1].get("options"))
    if oa is None or ob is None or (not allow_empty and (not oa or not ob)):
        return None, "changedLoadoutKeys"
    if any(row.get(key) not in (None, []) for row in (pa, pb)
           for key in ("includes", "peripheral")):
        return None, "includesOrPeripheral"
    return (pa, oa, pb, ob), "comparable"


def loadout_pairs(
    old: dict[int, Document], new: dict[int, Document], rekeys: dict[int, int],
) -> dict[int, int] | None:
    """Pair surviving keys and accepted rekeys; leave other keys unpaired."""
    shared = old.keys() & new.keys()
    removed, added = old.keys() - shared, new.keys() - shared
    if not set(rekeys) <= removed or not set(rekeys.values()) <= added:
        return None
    if len(set(rekeys.values())) != len(rekeys):
        return None
    return {**{i: i for i in shared}, **rekeys}


def occurrence_key(row: Document) -> str:
    """Source occurrence identity; definition-only changes belong to catalog history."""
    occurrence = dict(row["occurrence"])
    extras = occurrence.pop("extra", None)
    if occurrence.get("q") is None or type(occurrence.get("q")) is int and occurrence["q"] == 1:
        occurrence.pop("q", None)
    if extras:
        occurrence["extraIds"] = sorted(item["id"] for item in extras)
    return encode([row["filter"]["id"], occurrence])


def effective(
    profile: Document, option: Document, field: str, data: Document,
    contexts: list[dict[str, dict[int, tuple[str, ...]]]],
) -> tuple[list[Document] | None, str]:
    """Union exact occurrences across owners, preserving within-owner multiplicity."""
    layers = []
    for owner in (profile, option):
        value = owner.get(field, [])
        resolved, status = resolve_references(value, field, data, contexts)
        if resolved is None:
            return None, status
        layers.append(resolved)
    # Do not guess whether overlapping identical occurrences stack. The raw
    # evidence remains visible in the review when a duplicate spans owners.
    keys = [{occurrence_key(row) for row in layer} for layer in layers]
    if keys[0] & keys[1]:
        return None, "overlappingOwners"
    return layers[0] + layers[1], "comparable"


def effective_delta(before: list[Document], after: list[Document]) -> Document:
    left, right = Counter(map(occurrence_key, before)), Counter(map(occurrence_key, after))

    def rows(values: list[Document], remaining: Counter[str]) -> list[Document]:
        result = []
        for row in sorted(values, key=encode):
            key = occurrence_key(row)
            if remaining[key]:
                result.append(row)
                remaining[key] -= 1
        return result

    return {"lost": rows(before, left - right), "gained": rows(after, right - left)}


def cost_delta(a: Any, b: Any) -> str | None:
    try:
        if type(a) not in (int, float, str) or type(b) not in (int, float, str):
            return None
        delta = Decimal(str(b)) - Decimal(str(a))
        if not delta.is_finite():
            return None
        return format(delta.normalize(), "f")
    except InvalidOperation:
        return None


def compact_reference(row: Document) -> str:
    name = row["filter"]["name"]
    occurrence = row["occurrence"]
    quantity = occurrence.get("q")
    if quantity not in (None, 1):
        name = f"{quantity} × {name}"
    extras = occurrence.get("extra") or []
    if extras:
        name += " (" + ", ".join(item["name"] for item in extras) + ")"
    if set(occurrence) - {"q", "extra"}:
        name += " (additional source modifiers)"
    return name


def reference_summary(delta: Document) -> str:
    lost, gained = delta["lost"], delta["gained"]
    ids = {row["filter"]["id"] for row in lost} & {row["filter"]["id"] for row in gained}
    parts = []
    for identity in sorted(ids):
        a = ", ".join(compact_reference(r) for r in lost if r["filter"]["id"] == identity)
        b = ", ".join(compact_reference(r) for r in gained if r["filter"]["id"] == identity)
        parts.append(f"Changed {a} → {b}")
    for action, rows in (("Gained", gained), ("Lost", lost)):
        remaining = [compact_reference(r) for r in rows if r["filter"]["id"] not in ids]
        if remaining:
            parts.append(action + " " + ", ".join(remaining))
    return "; ".join(parts)


def describe_option(option: Document, data: Document,
                    contexts: list[dict[str, dict[int, tuple[str, ...]]]]) -> str:
    # Only label with resolved option-owned references; never use current names.
    parts = []
    for field in ("weapons", "skills", "equip"):
        values, _ = resolve_references(option.get(field, []), field, data, contexts)
        if values is None:
            continue
        parts.extend(compact_reference(row) for row in values)
    name = option.get("name") or "Loadout"
    return name + (" — " + "; ".join(parts) if parts else "")


def pair_delta(
    pa: Document, pb: Document, oa: Document, ob: Document,
    old: Document, new: Document, unit: int, group: int, field: str,
    contexts_a: list[dict[str, dict[int, tuple[str, ...]]]],
    contexts_b: list[dict[str, dict[int, tuple[str, ...]]]],
    approved_paths: set[tuple[Any, ...]],
) -> tuple[Document | None, str]:
    i, j = oa["id"], ob["id"]
    if i == j and not same_labels(oa, ob):
        return None, "changedLoadoutLabels"
    if oa.get("disabled") or ob.get("disabled"):
        return None, "disabledLoadout"
    if any(row.get(key) not in (None, []) for row in (oa, ob)
           for key in ("includes", "peripheral")):
        return None, "includesOrPeripheral"
    if i != j:
        left, _ = composition(oa, old, contexts_a)
        right, _ = composition(ob, new, contexts_b)
        if left is None or right is None or encode(left) != encode(right):
            return None, "rekeyCompositionConflict"
    if field in CATALOGS:
        a, status_a = effective(pa, oa, field, old, contexts_a)
        b, status_b = effective(pb, ob, field, new, contexts_b)
        if a is None or b is None:
            return None, status_a if a is None else status_b
        for left_owner, right_owner, path in (
            (pa, pb, ("units", unit, "profileGroups", group, "profiles", pa["id"], field)),
            (oa, ob, ("units", unit, "profileGroups", group, "options", i, field)),
        ):
            if left_owner is oa and i != j:
                continue  # rekey composition was checked above
            if path not in approved_paths:
                left_refs, _ = resolve_references(
                    left_owner.get(field, []), field, old, contexts_a,
                )
                right_refs, _ = resolve_references(
                    right_owner.get(field, []), field, new, contexts_b,
                )
                if left_refs is None or right_refs is None:
                    return None, "unresolvedOwner"
                if Counter(map(occurrence_key, left_refs)) != Counter(
                    map(occurrence_key, right_refs)
                ):
                    return None, "unacceptedReferenceChange"
        delta = effective_delta(a, b)
        return (delta if delta["lost"] or delta["gained"] else {}), "comparable"
    if field not in oa or field not in ob:
        return None, "missingCost"
    a, b = oa[field], ob[field]
    if a == b:
        return {}, "comparable"
    if (i == j and ("units", unit, "profileGroups", group, "options", i, field)
            not in approved_paths):
        return None, "unacceptedCostChange"
    change = cost_delta(a, b)
    if change is None:
        return None, "invalidCost"
    return ({"delta": change} if Decimal(change) else {}), "comparable"


def summarize_group(
    old: Document, new: Document, unit: int, group: int, field: str,
    contexts_a: list[dict[str, dict[int, tuple[str, ...]]]],
    contexts_b: list[dict[str, dict[int, tuple[str, ...]]]],
    approved_paths: set[tuple[Any, ...]],
    rekeys: dict[int, int] | None = None,
) -> tuple[list[Document] | None, str, Document]:
    context, status = stable_context(old, new, unit, group)
    if context is None:
        return None, status, {"groupReview": status}
    pa, oa, pb, ob = context
    pairs = loadout_pairs(oa, ob, rekeys or {})
    if pairs is None:
        return None, "invalidRekeyMapping", {"groupReview": "invalidRekeyMapping"}
    coverage: Document = {
        "beforeOptionIds": sorted(oa), "afterOptionIds": sorted(ob),
        "unpairedBefore": sorted(oa.keys() - pairs.keys()),
        "unpairedAfter": sorted(ob.keys() - set(pairs.values())),
        "comparedPairs": [], "reviewPairs": [],
    }
    buckets: dict[str, Document] = {}
    for i, j in sorted(pairs.items()):
        delta, reason = pair_delta(
            pa, pb, oa[i], ob[j], old, new, unit, group, field,
            contexts_a, contexts_b, approved_paths,
        )
        pair = {"beforeOptionId": i, "afterOptionId": j}
        if delta is None:
            coverage["reviewPairs"].append({**pair, "reason": reason})
            continue
        coverage["comparedPairs"].append({**pair, "changed": bool(delta)})
        if not delta:
            continue
        key = encode(delta)
        bucket = buckets.setdefault(key, {"field": field, **delta, "loadouts": []})
        target = {"optionId": i, "label": describe_option(oa[i], old, contexts_a)}
        if i != j:
            target["laterOptionId"] = j
        if field not in CATALOGS:
            target.update(before=oa[i][field], after=ob[j][field])
        bucket["loadouts"].append(target)
    compared = len(coverage["comparedPairs"])
    if not compared:
        reasons = {pair["reason"] for pair in coverage["reviewPairs"]}
        status = next(iter(reasons)) if len(reasons) == 1 else (
            "noComparableLoadouts" if pairs else "changedLoadoutKeys"
        )
        return None, status, coverage
    complete = compared == len(oa) == len(ob)
    result = []
    for key in sorted(buckets):
        row = buckets[key]
        row["allGroupLoadouts"] = complete and len(row["loadouts"]) == compared
        if field in CATALOGS:
            row["summary"] = reference_summary(row)
        else:
            sign = "+" if Decimal(row["delta"]) > 0 else ""
            row["summary"] = f"{sign}{row['delta']} {FIELDS[field]}"
        result.append(row)
    return result, "comparable" if complete else "partial", coverage


def lifecycle_payload(
    old: Document, new: Document, event: Document, reason: str,
    contexts_a: list[dict[str, dict[int, tuple[str, ...]]]],
    contexts_b: list[dict[str, dict[int, tuple[str, ...]]]],
) -> tuple[Document | None, str]:
    """Summarize a one-sided occurrence in its observed Army and Group only."""
    path = event["path"]
    require(len(path) == 6 and path[::2] == ["units", "profileGroups", "options"],
            "Unexpected loadout path")
    unit, group, identity = path[1::2]
    direction = event["direction"]
    require(direction in {"appeared", "disappeared"}, "Unexpected lifecycle direction")
    if reason != "noOppositeKey" or event["possibleReplacementIds"]:
        return None, "possibleReplacement" if event["possibleReplacementIds"] else reason
    context, status = stable_context(old, new, unit, group, allow_empty=True)
    if context is None:
        return None, status
    pa, oa, pb, ob = context
    appeared = direction == "appeared"
    present, absent = (ob, oa) if appeared else (oa, ob)
    require(identity in present and identity not in absent, "Lifecycle presence differs")
    if absent.keys() - present.keys():
        return None, "opposingKeyChanges"
    option = present[identity]
    side = "after" if appeared else "before"
    require(event[side]["present"] and encode(event[side]["value"]) == encode(option),
            "Lifecycle source record differs")
    require(not event["before" if appeared else "after"]["present"], "Lifecycle absence differs")
    if option.get("disabled"):
        return None, "disabledLoadout"
    if any(option.get(key) not in (None, []) for key in ("includes", "peripheral")):
        return None, "includesOrPeripheral"
    profile, data, contexts = (pb, new, contexts_b) if appeared else (pa, old, contexts_a)
    resolved = {}
    for field in CATALOGS:
        values, status = effective(profile, option, field, data, contexts)
        if values is None:
            return None, status
        resolved[field] = sorted(values, key=encode)
    if any(cost_delta(option.get(field), option.get(field)) is None for field in ("points", "swc")):
        return None, "invalidCost"
    # Preserve full option-owned data for review and conservative Army grouping.
    # A one-sided source appearance is not proof of an official release or of
    # absence from another Group or Army.
    action = "Added" if appeared else "Removed"
    label = describe_option(option, data, contexts)
    return {
        "kind": "loadoutAdded" if appeared else "loadoutRemoved",
        "summary": f"{action} loadout: {label}",
        "label": label, "optionId": identity,
        "profileId": profile["id"], "profileName": profile.get("name"),
        "points": option["points"], "swc": option["swc"],
        "effectiveReferences": resolved, "sourceOption": option,
        "status": "observedCandidate",
    }, "oneSided"


def build(preview: Document, archive: Path) -> Document:
    require(preview["publicationStatus"] == "privatePreviewOnly"
            and preview["archiveSha256"] == ARCHIVE_PIN and preview["edition"] == "n5",
            "Unexpected private preview")
    source = read_history(archive, ARCHIVE_PIN)

    @lru_cache(maxsize=48)
    def data(sha: str) -> Document:
        return source.read_object(sha)

    @lru_cache(maxsize=64)
    def metadata(sha: str) -> dict[str, dict[int, tuple[str, ...]]]:
        return catalog_index(data(sha))

    work: dict[tuple[int, int, int, str], Document] = {}
    outside_scope = []
    current = {
        i["sourceUnitId"]: unit["logicalUnitId"]
        for unit in preview["units"] for i in unit["sourceIdentities"]
    }
    rekeys: dict[tuple[int, int, int], dict[int, int]] = {}
    rekey_positions: dict[tuple[int, int, int], list[int]] = {}
    lifecycle_rows = []
    lifecycle_rekeys = []
    with closing(read_only(HISTORY)) as db:
        for pos, raw in db.execute(
            "SELECT position,body FROM history_record WHERE stream='loadoutMatch' "
            "ORDER BY position"
        ):
            row = json.loads(raw)
            if row["kind"] != "sameComposition":
                continue
            path = row["parentPath"]
            if len(path) != 5 or path[1] not in current:
                continue
            ev = row["before"]["evidence"]
            ci, unit, group = ev["comparisonIndex"], path[1], path[3]
            key = (ci, unit, group)
            mapping = rekeys.setdefault(key, {})
            require(row["beforeId"] not in mapping, "Duplicate accepted rekey")
            mapping[row["beforeId"]] = row["afterId"]
            rekey_positions.setdefault(key, []).append(pos)
            lifecycle_rekeys.append({"loadoutMatchPosition": pos, "comparisonIndex": ci,
                                     "sourceUnitId": unit, "groupId": group,
                                     "beforeOptionId": row["beforeId"],
                                     "afterOptionId": row["afterId"]})
            for field in ("points", "swc"):
                if field in row["changedNonCompositionFields"]:
                    work.setdefault((ci, unit, group, field), {
                        "evidence": ev, "paths": [], "positions": [],
                    })
        lifecycle_rows = [
            (pos, json.loads(raw)) for pos, raw in db.execute(
                "SELECT position,body FROM history_record WHERE stream='loadoutUnpaired' "
                "ORDER BY position"
            )
        ]
        structural_count = sum(
            json.loads(raw)["kind"] == "loadout" for (raw,) in db.execute(
                "SELECT body FROM history_record WHERE stream='structuralOccurrence'"
            )
        )
        require(len(lifecycle_rows) + 2 * len(lifecycle_rekeys) == structural_count,
                "Incomplete lifecycle evidence accounting")
        for pos, raw in db.execute(
            "SELECT position,body FROM history_record WHERE stream='compositionCandidate' "
            "ORDER BY position"
        ):
            row = json.loads(raw)
            path = row["path"]
            field = path[-1]
            if (field not in FIELDS_SUPPORTED or len(path) != 7 or path[1] not in current
                    or path[2] != "profileGroups"):
                outside_scope.append({"candidatePosition": pos, "path": path})
                continue
            for ev in row["evidence"]:
                ci = ev["comparisonIndex"]
                key = (ci, path[1], path[3], field)
                entry = work.setdefault(key, {"evidence": ev, "paths": [], "positions": []})
                entry["paths"].append(path)
                entry["positions"].append(pos)

    counts: Counter[str] = Counter()
    events: dict[str, Document] = {}
    outcomes = []
    for (ci, unit, group, field), entry in sorted(work.items()):
        ev = entry["evidence"]
        a, b = ev["earlier"], ev["later"]
        old, new = data(a["sha256"]), data(b["sha256"])
        result, status, coverage = summarize_group(
            old, new, unit, group, field,
            [metadata(sha) for sha in a["metadataSha256"]],
            [metadata(sha) for sha in b["metadataSha256"]],
            {tuple(path) for path in entry["paths"]}, rekeys.get((ci, unit, group)),
        )
        evidence = {
            "comparisonIndex": ci, "armyId": ev["factionId"],
            "candidatePositions": sorted(set(entry["positions"])),
            "loadoutMatchPositions": rekey_positions.get((ci, unit, group), []),
            "coverage": coverage,
        }
        identity = {
            "logicalUnitId": current[unit], "sourceUnitId": unit, "groupId": group,
            "field": field, "earlierObservedDate": a["encodedRevisionDate"],
            "laterObservedDate": b["encodedRevisionDate"],
        }
        if result is None:
            counts[f"review:{status}"] += 1
            outcome = "review:" + status
        elif not result:
            outcome = "partialNoChange" if status == "partial" else "unchangedEffective"
            counts[outcome] += 1
        else:
            outcome = "partialChanged" if status == "partial" else "changedEffective"
            counts[outcome] += 1
            for change in result:
                payload = {**identity, **change}
                key = encode(payload)
                event = events.setdefault(key, {**payload, "evidence": []})
                event["evidence"].append(evidence)
                counts["armyScopedSummaries"] += 1
        outcomes.append({**identity, **evidence, "outcome": outcome})
        for pair in coverage.get("reviewPairs", []):
            counts[f"pairReview:{pair['reason']}"] += 1
        counts["unpairedBefore"] += len(coverage.get("unpairedBefore", []))
        counts["unpairedAfter"] += len(coverage.get("unpairedAfter", []))
    lifecycle: dict[str, Document] = {}
    lifecycle_outcomes = []
    for pos, row in lifecycle_rows:
        occurrence = row["occurrence"]
        path = occurrence["path"]
        ev = occurrence["evidence"]
        a, b = ev["earlier"], ev["later"]
        unit, group = path[1], path[3]
        identity = {
            "logicalUnitId": current.get(unit), "sourceUnitId": unit, "groupId": group,
            "earlierObservedDate": a["encodedRevisionDate"],
            "laterObservedDate": b["encodedRevisionDate"],
        }
        evidence = {
            "comparisonIndex": ev["comparisonIndex"], "armyId": ev["factionId"],
            "loadoutUnpairedPosition": pos,
        }
        if unit not in current:
            payload, status = None, "unresolvedUnitIdentity"
        else:
            payload, status = lifecycle_payload(
                data(a["sha256"]), data(b["sha256"]), occurrence, row["reason"],
                [metadata(sha) for sha in a["metadataSha256"]],
                [metadata(sha) for sha in b["metadataSha256"]],
            )
        outcome = "review:" + status if payload is None else payload["kind"]
        counts[f"lifecycle:{outcome}"] += 1
        lifecycle_outcomes.append({
            **identity, **evidence, "optionId": path[-1],
            "direction": occurrence["direction"], "outcome": outcome,
            "reconciliationReason": row["reason"],
        })
        if payload is not None:
            key = encode({**identity, **payload})
            summary = lifecycle.setdefault(key, {**identity, **payload, "evidence": []})
            summary["evidence"].append(evidence)
    counts["lifecycleUnpairedOccurrences"] = len(lifecycle_rows)
    counts["lifecycleRekeyOccurrences"] = 2 * len(lifecycle_rekeys)
    counts["lifecycleConsolidatedSummaries"] = len(lifecycle)
    counts["lifecycleMultiArmySummaries"] = sum(len(e["evidence"]) > 1 for e in lifecycle.values())
    counts["acceptedRekeyCollections"] = len(rekeys)
    counts["outsidePilotScopeCandidates"] = len(outside_scope)
    counts["sourceGroupFieldComparisons"] = len(work)
    counts["consolidatedSummaries"] = len(events)
    counts["allGroupLoadoutSummaries"] = sum(e["allGroupLoadouts"] for e in events.values())
    counts["multiArmySummaries"] = sum(len(e["evidence"]) > 1 for e in events.values())
    return {
        "formatVersion": 3, "publicationStatus": "privateResearchOnly", "edition": "n5",
        "archiveSha256": ARCHIVE_PIN, "armyDatabaseSha256": preview["armyDatabaseSha256"],
        "historyDatabaseSha256": preview["historyDatabaseSha256"],
        "counts": dict(counts), "summaries": list(events.values()), "outcomes": outcomes,
        "outsidePilotScope": outside_scope,
        "lifecycleSummaries": list(lifecycle.values()), "lifecycleOutcomes": lifecycle_outcomes,
        "lifecycleRekeys": lifecycle_rekeys,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--preview-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = (ROOT / "generated").resolve()
    require(args.preview.resolve().is_relative_to(private), "Use private preview")
    require(args.output.resolve().is_relative_to(private), "Use private output")
    require(not args.output.exists(), "Summary already exists")
    raw = args.preview.read_bytes()
    require(digest(raw) == args.preview_sha256, "Preview hash differs")
    preview = json.loads(raw)
    require(file_digest(HISTORY) == preview["historyDatabaseSha256"], "History database differs")
    require(file_digest(ARMY) == preview["armyDatabaseSha256"], "Army database differs")
    result = build(preview, ROOT / "archive/army-history-v1.zip")
    require(file_digest(HISTORY) == preview["historyDatabaseSha256"], "History database changed")
    require(file_digest(ARMY) == preview["armyDatabaseSha256"], "Army database changed")
    result["previewSha256"] = args.preview_sha256
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(encode(result) + "\n")
    print(json.dumps(result["counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
