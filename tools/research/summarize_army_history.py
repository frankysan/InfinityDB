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

from infinity_db.army_history_consolidation import record_at
from infinity_db.army_history_loadouts import composition
from infinity_db.army_history_pilot import (
    catalog_index,
    indexed,
    peripheral_definitions,
    peripheral_signature,
)
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


def include_rows(owner: Document, data: Document, unit: int) -> list[Document] | None:
    """Resolve direct Include edges in the endpoint Army and Unit namespace.

    Retain target identities and multiplicity, not a flattened target profile.
    """
    includes = owner.get("includes")
    if includes is None:
        return []
    if not isinstance(includes, list):
        return None
    result = []
    for edge in includes:
        if not isinstance(edge, dict) or set(edge) - {"group", "option", "q"}:
            return None
        group, option = edge.get("group"), edge.get("option")
        if type(group) is not int or type(option) is not int:
            return None
        quantity = edge.get("q")
        if quantity is None:
            quantity = 1
        if type(quantity) is not int or quantity < 1:
            return None
        found = get_group(data, unit, group)
        if found is None:
            return None
        target_group = found[1]
        options = indexed(target_group.get("options"))
        profiles = indexed(target_group.get("profiles"))
        if options is None or option not in options or not profiles:
            return None
        target = options[option]
        result.append({
            "group": group, "option": option, "quantity": quantity,
            "groupLabels": {k: target_group.get(k) for k in LABELS},
            "optionLabels": {k: target.get(k) for k in LABELS},
            "disabled": target.get("disabled"),
            "profiles": [{"id": identity, **{k: profiles[identity].get(k) for k in LABELS}}
                         for identity in sorted(profiles)],
        })
    return sorted(result, key=encode)


def include_signature(owner: Document, data: Document, unit: int) -> str | None:
    rows = include_rows(owner, data, unit)
    return None if rows is None else encode(rows)


def comparable_relationships(
    a: Document, b: Document, old: Document, new: Document, unit: int,
    allow_relationships: bool,
) -> bool:
    """Compare direct owners only; never flatten attached entities into a profile."""
    if a.get("includes") not in (None, []) or b.get("includes") not in (None, []):
        if not allow_relationships:
            return False
        first, second = include_signature(a, old, unit), include_signature(b, new, unit)
        if first is None or first != second:
            return False
    left, right = a.get("peripheral"), b.get("peripheral")
    left = [] if left is None else left
    right = [] if right is None else right
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    if not left and not right:
        return True
    if not allow_relationships:
        return False
    left_signature = peripheral_signature(left, peripheral_definitions(old))
    right_signature = peripheral_signature(right, peripheral_definitions(new))
    return left_signature is not None and left_signature == right_signature


def stable_context(
    old: Document, new: Document, unit: int, group: int, *, allow_empty: bool = False,
    profile_id: int | None = None, allow_stable_relationships: bool = False,
) -> tuple[tuple[Document, dict[int, Document], Document, dict[int, Document]] | None, str]:
    a, b = get_group(old, unit, group), get_group(new, unit, group)
    if a is None or b is None:
        return None, "missingGroup"
    if not same_labels(a[0], b[0]) or not same_labels(a[1], b[1]):
        return None, "changedLabels"
    profiles_a, profiles_b = indexed(a[1].get("profiles")), indexed(b[1].get("profiles"))
    if profiles_a is None or profiles_b is None:
        return None, "multiProfileOrChangedProfile"
    if profile_id is None:
        if len(profiles_a) != 1 or profiles_a.keys() != profiles_b.keys():
            return None, "multiProfileOrChangedProfile"
        profile_id = next(iter(profiles_a))
    if profile_id not in profiles_a or profile_id not in profiles_b:
        return None, "multiProfileOrChangedProfile"
    pa, pb = profiles_a[profile_id], profiles_b[profile_id]
    if not same_labels(pa, pb):
        return None, "changedLabels"
    oa, ob = indexed(a[1].get("options")), indexed(b[1].get("options"))
    if oa is None or ob is None or (not allow_empty and (not oa or not ob)):
        return None, "changedLoadoutKeys"
    if not comparable_relationships(pa, pb, old, new, unit, allow_stable_relationships):
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
    if not comparable_relationships(oa, ob, old, new, unit, True):
        return None, "includesOrPeripheral"
    if i != j:
        left, _ = composition(oa, old, contexts_a)
        right, _ = composition(ob, new, contexts_b)
        if left is None or right is None or encode(left) != encode(right):
            left = normalized_loadout(oa, old, unit, contexts_a)
            right = normalized_loadout(ob, new, unit, contexts_b)
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


def summarize_profile_group(
    old: Document, new: Document, unit: int, group: int, field: str,
    contexts_a: list[dict[str, dict[int, tuple[str, ...]]]],
    contexts_b: list[dict[str, dict[int, tuple[str, ...]]]],
    approved_paths: set[tuple[Any, ...]],
    rekeys: dict[int, int] | None = None, *, profile_id: int | None = None,
) -> tuple[list[Document] | None, str, Document]:
    context, status = stable_context(
        old, new, unit, group, profile_id=profile_id, allow_stable_relationships=True,
    )
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
        pair: Document = {"beforeOptionId": i, "afterOptionId": j}
        if delta is None:
            coverage["reviewPairs"].append({**pair, "reason": reason})
            continue
        relationship_fields = [
            field_name for field_name in ("includes", "peripheral")
            if any(owner.get(field_name) for owner in (pa, pb, oa[i], ob[j]))
        ]
        if relationship_fields:
            pair["relationshipScope"] = "directOwners"
            pair["relationshipFields"] = relationship_fields
        coverage["comparedPairs"].append({**pair, "changed": bool(delta)})
        if not delta:
            continue
        key = encode(delta)
        bucket = buckets.setdefault(key, {"field": field, **delta, "loadouts": []})
        target = {"optionId": i, "label": describe_option(oa[i], old, contexts_a)}
        if field in CATALOGS and relationship_fields:
            target["relationshipScope"] = "directOwners"
            target["relationshipFields"] = relationship_fields
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


def summarize_group(
    old: Document, new: Document, unit: int, group: int, field: str,
    contexts_a: list[dict[str, dict[int, tuple[str, ...]]]],
    contexts_b: list[dict[str, dict[int, tuple[str, ...]]]],
    approved_paths: set[tuple[Any, ...]],
    rekeys: dict[int, int] | None = None,
) -> tuple[list[Document] | None, str, Document]:
    a, b = get_group(old, unit, group), get_group(new, unit, group)
    if a is None or b is None:
        return None, "missingGroup", {"groupReview": "missingGroup"}
    pa, pb = indexed(a[1].get("profiles")), indexed(b[1].get("profiles"))
    if not pa or not pb or (len(pa) == len(pb) == 1 and pa.keys() == pb.keys()):
        return summarize_profile_group(
            old, new, unit, group, field, contexts_a, contexts_b, approved_paths, rekeys,
        )
    coverage: Document = {
        "beforeProfileIds": sorted(pa), "afterProfileIds": sorted(pb),
        "unpairedBeforeProfiles": sorted(pa.keys() - pb.keys()),
        "unpairedAfterProfiles": sorted(pb.keys() - pa.keys()),
        "profileComparisons": [],
    }
    buckets: dict[str, Document] = {}
    costs: dict[str, Document] = {}
    successful = 0
    complete = pa.keys() == pb.keys()
    for identity in sorted(pa.keys() & pb.keys()):
        rows, status, detail = summarize_profile_group(
            old, new, unit, group, field, contexts_a, contexts_b, approved_paths, rekeys,
            profile_id=identity,
        )
        coverage["profileComparisons"].append({
            "profileId": identity, "outcome": status, "coverage": detail,
        })
        complete &= status == "comparable"
        if rows is None:
            continue
        successful += 1
        for row in rows:
            # Costs belong to the shared loadout, not each individual profile.
            if field not in CATALOGS:
                cost = costs.setdefault(row["delta"], {
                    **row, "loadouts": [], "allGroupLoadouts": False,
                })
                for target in row["loadouts"]:
                    if target not in cost["loadouts"]:
                        cost["loadouts"].append(target)
                continue
            # For references, explicitly retain each affected profile.
            all_profile_loadouts = row.pop("allGroupLoadouts")
            row["allGroupLoadouts"] = False
            key = encode(row)
            summary = buckets.setdefault(key, {**row, "profiles": []})
            summary["profiles"].append({
                "profileId": identity, "name": pa[identity].get("name"),
                "allProfileLoadouts": all_profile_loadouts,
            })
    if not successful:
        return None, "noComparableProfiles", coverage
    result = list(buckets.values())
    for row in result:
        # Do not claim group-wide scope if any profile or loadout was not compared.
        row["allGroupLoadouts"] = (
            complete and len(row["profiles"]) == len(pa)
            and all(p["allProfileLoadouts"] for p in row["profiles"])
        )
    for row in costs.values():
        row["loadouts"].sort(key=lambda target: target["optionId"])
        row["allGroupLoadouts"] = complete and len(row["loadouts"]) == len(a[1]["options"])
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


def ava_display(record: Document) -> str | None:
    if not record["present"]:
        return None
    value = record.get("value")
    if type(value) not in (int, str):
        return None
    text = str(value).strip()
    if text.casefold() in {"t", "total"}:
        return "Total"
    try:
        number = int(text)
    except ValueError:
        return None
    if number < 0:
        return None
    return "Total" if number >= 100 else str(number)


def availability_payload(
    old: Document, new: Document, row: Document,
) -> tuple[Document | None, str]:
    """Describe Army-local observations without inferring selection eligibility."""
    path = row["path"]
    kind = row["kind"]
    if kind == "unitListMembership":
        if row["possibleReplacementIds"]:
            return None, "possibleReplacement"
        left, right = indexed(old.get("units")), indexed(new.get("units"))
        require(left is not None and right is not None, "Malformed Army lists")
        assert left is not None and right is not None
        unit = path[1]
        appeared = row["direction"] == "appeared"
        require((unit in left, unit in right) == (not appeared, appeared),
                "Unit list presence differs")
        source_row = right[unit] if appeared else left[unit]
        side = "after" if appeared else "before"
        require(encode(row[side]["value"]) == encode(source_row), "Unit list record differs")
        return {
            "kind": "armyListAppearance" if appeared else "armyListDisappearance",
            "summary": "Appeared in Army list" if appeared else "Disappeared from Army list",
            "sourceRole": row["sourceRole"], "declaredInThisArmy": row["declaredInThisArmy"],
            "sourcePath": path, "historicalName": source_row.get("name"),
        }, "observedListPresence"

    left_record, right_record = record_at(old, path), record_at(new, path)
    require(left_record is not None and right_record is not None, "Army field path differs")
    assert left_record is not None and right_record is not None
    field = path[-1]
    for record, side in ((left_record, "before"), (right_record, "after")):
        value = row[side]
        require(value["present"] == (field in record[0]), "Army field presence differs")
        if value["present"]:
            require(encode(value["value"]) == encode(record[0][field]), "Army field value differs")
    if kind == "ava":
        a, b = ava_display(row["before"]), ava_display(row["after"])
        if a is None or b is None:
            return None, "unresolvedAVA"
        if a == b:
            return None, "unchangedDisplay"
        summary = f"AVA: {a} → {b}"
    elif kind == "disabled":
        a, b = row["before"].get("value"), row["after"].get("value")
        if (not row["before"]["present"] or not row["after"]["present"]
                or type(a) is not bool or type(b) is not bool):
            return None, "unresolvedDisabledState"
        if a == b:
            return None, "unchangedDisplay"
        summary = "Disabled in Army source" if b else "Enabled in Army source"
    else:
        return None, "unsupportedAvailabilityField"
    labels = [
        {key: item[key] for key in ("id", *LABELS) if key in item}
        for item in left_record[1]
    ]
    return {
        "kind": kind, "summary": summary, "sourcePath": path,
        "historicalLabels": labels, "before": row["before"], "after": row["after"],
    }, "observedFieldChange"


def peripheral_rows(owner: Document, data: Document) -> list[Document] | None:
    refs = owner.get("peripheral", [])
    if not isinstance(refs, list):
        return None
    if not refs:
        return []
    filters = data.get("filters")
    definitions = indexed(filters.get("peripheral")) if isinstance(filters, dict) else None
    unique = peripheral_definitions(data)
    if definitions is None:
        return None
    result = []
    for ref in refs:
        if (not isinstance(ref, dict) or type(ref.get("id")) is not int
                or ref["id"] not in unique or set(ref) - {"id", "q", "order", "extra"}
                or ref.get("extra") not in (None, [])):
            return None
        quantity = ref.get("q")
        if quantity is None:
            quantity = 1
        if type(quantity) is not int or quantity < 1:
            return None
        result.append({
            "definition": {k: v for k, v in definitions[ref["id"]].items() if k != "id"},
            "quantity": quantity,
        })
    return sorted(result, key=encode)


def normalized_loadout(
    row: Document, data: Document, unit: int,
    contexts: list[dict[str, dict[int, tuple[str, ...]]]],
) -> Document | None:
    """Keep all non-cost source fields, normalizing only established equivalents."""
    payload = {k: v for k, v in row.items() if k not in {"id", "name", "points", "swc"}}
    for field in CATALOGS:
        refs, _ = resolve_references(row.get(field, []), field, data, contexts)
        if refs is None:
            return None
        normalized = []
        for ref in refs:
            occurrence = dict(ref["occurrence"])
            quantity = occurrence.get("q")
            if quantity is None or type(quantity) is int and quantity == 1:
                occurrence.pop("q", None)
            extras = occurrence.pop("extra", None)
            if extras:
                occurrence["extra"] = sorted(extras, key=encode)
            normalized.append({**ref, "occurrence": occurrence})
        payload[field] = sorted(normalized, key=encode)
    includes = include_rows(row, data, unit)
    peripherals = peripheral_rows(row, data)
    if includes is None or peripherals is None:
        return None
    payload["includes"] = includes
    payload["peripheral"] = peripherals
    return payload


def normalized_rekeys(
    old: Document, new: Document, unit: int, group: int,
    contexts_a: list[dict[str, dict[int, tuple[str, ...]]]],
    contexts_b: list[dict[str, dict[int, tuple[str, ...]]]],
) -> dict[int, int]:
    """Require unique full normalized composition, including surviving siblings."""
    a, b = get_group(old, unit, group), get_group(new, unit, group)
    if a is None or b is None or not all(same_labels(x, y) for x, y in zip(a, b, strict=True)):
        return {}
    pa, pb = indexed(a[1].get("profiles")), indexed(b[1].get("profiles"))
    if not pa or not pb or pa.keys() != pb.keys():
        return {}
    if any(not same_labels(pa[i], pb[i]) for i in pa):
        return {}
    oa, ob = indexed(a[1].get("options")), indexed(b[1].get("options"))
    if not oa or not ob or not (oa.keys() - ob.keys()) or not (ob.keys() - oa.keys()):
        return {}
    left = {i: normalized_loadout(row, old, unit, contexts_a) for i, row in oa.items()}
    right = {i: normalized_loadout(row, new, unit, contexts_b) for i, row in ob.items()}
    if any(v is None for v in (*left.values(), *right.values())):
        return {}
    lkeys, rkeys = {i: encode(v) for i, v in left.items()}, {i: encode(v) for i, v in right.items()}
    lc, rc = Counter(lkeys.values()), Counter(rkeys.values())
    by_signature = {v: i for i, v in rkeys.items() if rc[v] == 1}
    result = {}
    for i in sorted(oa.keys() - ob.keys()):
        payload = left[i]
        assert payload is not None
        if not any(payload.get(field) for field in (*CATALOGS, "includes", "peripheral")):
            continue
        signature = lkeys[i]
        j = by_signature.get(signature)
        if (lc[signature] == 1 and j is not None and j not in oa
                and same_labels(oa[i], ob[j])):
            result[i] = j
    return result


def relationship_label(row: Document, field: str) -> str:
    if field == "peripheral":
        name = row["definition"]["name"]
    else:
        names = [p.get("name") or p.get("isc") for p in row["profiles"]]
        name = " / ".join(n for n in names if n) or row["groupLabels"]["name"] or "Included profile"
        option = row["optionLabels"]["name"]
        if option and option != name:
            name += f" ({option})"
    return f"{row['quantity']} × {name}" if row["quantity"] != 1 else name


def relationship_payload(
    old: Document, new: Document, change: Document,
    target_rekeys: dict[tuple[int, int], int] | None = None,
) -> tuple[Document | None, str]:
    """Compare direct, explicitly owned attachment edges, not inherited capabilities."""
    path = change["path"]
    field = path[-1]
    if len(path) not in (5, 7) or field not in {"includes", "peripheral"}:
        return None, "unsupportedOwner"
    if change["ancestorOrRecordLabelChanged"]:
        return None, "changedLabels"
    a, b = record_at(old, path), record_at(new, path)
    if a is None or b is None:
        return None, "unresolvedOwner"
    if any(not same_labels(left, right) for left, right in zip(a[1], b[1], strict=True)):
        return None, "changedLabels"
    for record, side in ((a[0], "before"), (b[0], "after")):
        saved = change[side]
        require(saved["present"] == (field in record), "Attachment field presence differs")
        if saved["present"]:
            require(encode(saved["value"]) == encode(record[field]), "Attachment field differs")
        if saved["present"] and not isinstance(saved["value"], list):
            return None, "unresolvedAttachmentShape"
    if field == "includes":
        left, right = include_rows(a[0], old, path[1]), include_rows(b[0], new, path[1])
    else:
        left, right = peripheral_rows(a[0], old), peripheral_rows(b[0], new)
    if left is None or right is None:
        return None, "unresolvedAttachmentTarget"
    if field == "includes" and target_rekeys:
        right = [
            {**row, "option": target_rekeys.get((row["group"], row["option"]), row["option"])}
            for row in right
        ]
    lcount, rcount = Counter(map(encode, left)), Counter(map(encode, right))
    if lcount == rcount:
        return None, "unchangedRelationship"

    def target_key(row: Document) -> str:
        return encode({k: v for k, v in row.items() if k != "quantity"})

    lost = [json.loads(key) for key in sorted(lcount - rcount)
            for _ in range((lcount - rcount)[key])]
    gained = [json.loads(key) for key in sorted(rcount - lcount)
              for _ in range((rcount - lcount)[key])]
    # Simultaneous changes to different target identities are possible rekeys
    # or replacements. Only a shared exact target can be called a change.
    if lost and gained and {target_key(r) for r in lost} != {target_key(r) for r in gained}:
        return None, "possibleAttachmentReplacement"
    label = "Include" if field == "includes" else "Peripheral attachment"
    parts = []
    if lost and gained:
        parts.append(f"Changed {label}: " + ", ".join(relationship_label(r, field) for r in lost)
                     + " → " + ", ".join(relationship_label(r, field) for r in gained))
    elif gained:
        parts.append(f"Added {label}: " + ", ".join(relationship_label(r, field) for r in gained))
    else:
        parts.append(f"Removed {label}: " + ", ".join(relationship_label(r, field) for r in lost))
    return {
        "field": field, "sourcePath": path,
        "historicalLabels": [{k: r[k] for k in ("id", *LABELS) if k in r} for r in a[1]],
        "summary": "; ".join(parts), "lost": lost, "gained": gained,
        "relationshipScope": "directOwner", "status": "observedCandidate",
    }, "changedRelationship"


def build(preview: Document, archive: Path, *, history_path: Path = HISTORY) -> Document:
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
    availability_rows = []
    declaration_rows = []
    relationship_rows = []
    with closing(read_only(history_path)) as db:
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
        availability_rows = [
            (stream, pos, json.loads(raw)) for stream, pos, raw in db.execute(
                "SELECT stream,position,body FROM history_record "
                "WHERE stream IN ('armyFieldOccurrence','structuralOccurrence') "
                "ORDER BY stream,position"
            ) if stream == "armyFieldOccurrence" or json.loads(raw)["kind"] == "unitListMembership"
        ]
        declaration_rows = [
            (pos, json.loads(raw)) for pos, raw in db.execute(
                "SELECT position,body FROM history_record "
                "WHERE stream='declaredMembershipClaim' ORDER BY position"
            )
        ]
        relationship_rows = [
            (ci, index, unit, json.loads(raw), json.loads(comparison))
            for ci, index, unit, raw, comparison in db.execute(
                "SELECT c.comparison_index,c.change_index,c.unit_id,c.body,p.body "
                "FROM comparison_change c JOIN comparison p USING(comparison_index) "
                "WHERE c.unit_id IS NOT NULL "
                "AND json_extract(c.body,'$.path[#-1]') IN ('includes','peripheral') "
                "ORDER BY c.comparison_index,c.change_index"
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
    normalized_matches = []
    normalized_positions: dict[int, Document] = {}
    unresolved_collections: dict[
        tuple[int, int, int], dict[tuple[str, int], tuple[int, Document]]
    ] = {}
    for pos, row in lifecycle_rows:
        occurrence = row["occurrence"]
        path, ev = occurrence["path"], occurrence["evidence"]
        if len(path) != 6 or path[1] not in current:
            continue
        key = (ev["comparisonIndex"], path[1], path[3])
        side = "after" if occurrence["direction"] == "appeared" else "before"
        unresolved_collections.setdefault(key, {})[(side, path[-1])] = (pos, row)
    for (ci, unit, group), rows in sorted(unresolved_collections.items()):
        if {side for side, _ in rows} != {"before", "after"}:
            continue
        ev = next(iter(rows.values()))[1]["occurrence"]["evidence"]
        a, b = ev["earlier"], ev["later"]
        old, new = data(a["sha256"]), data(b["sha256"])
        pairs = normalized_rekeys(
            old, new, unit, group,
            [metadata(sha) for sha in a["metadataSha256"]],
            [metadata(sha) for sha in b["metadataSha256"]],
        )
        for i, j in sorted(pairs.items()):
            if ("before", i) not in rows or ("after", j) not in rows:
                continue
            before_pos, before = rows[("before", i)]
            after_pos, after = rows[("after", j)]
            mapping = rekeys.setdefault((ci, unit, group), {})
            require(i not in mapping and j not in mapping.values(), "Conflicting normalized rekey")
            mapping[i] = j
            match = {
                "comparisonIndex": ci, "armyId": ev["factionId"], "sourceUnitId": unit,
                "groupId": group, "beforeOptionId": i, "afterOptionId": j,
                "beforeUnpairedPosition": before_pos, "afterUnpairedPosition": after_pos,
                "kind": "normalizedSameComposition",
            }
            normalized_matches.append(match)
            normalized_positions[before_pos] = normalized_positions[after_pos] = match
            for field in ("points", "swc"):
                left = before["occurrence"]["before"]["value"]
                right = after["occurrence"]["after"]["value"]
                if encode(left.get(field)) != encode(right.get(field)):
                    work.setdefault((ci, unit, group, field), {
                        "evidence": ev, "paths": [], "positions": [],
                    })
    normalized_by_group: dict[tuple[int, int, int], list[Document]] = {}
    for match in normalized_matches:
        key = (match["comparisonIndex"], match["sourceUnitId"], match["groupId"])
        normalized_by_group.setdefault(key, []).append(match)
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
            "normalizedRekeys": normalized_by_group.get((ci, unit, group), []),
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
        profile_comparisons = coverage.get("profileComparisons")
        if profile_comparisons is not None:
            counts["multiProfileGroupFieldComparisons"] += 1
            counts["multiProfile:" + outcome] += 1
        details = [p["coverage"] for p in profile_comparisons] if (
            profile_comparisons is not None
        ) else [coverage]
        for detail in details:
            for pair in detail.get("reviewPairs", []):
                counts[f"pairReview:{pair['reason']}"] += 1
            counts["unpairedBefore"] += len(detail.get("unpairedBefore", []))
            counts["unpairedAfter"] += len(detail.get("unpairedAfter", []))
            for relationship, label in (("peripheral", "Peripheral"), ("includes", "Include")):
                counts[f"stable{label}PairComparisons"] += sum(
                    relationship in pair.get("relationshipFields", [])
                    for pair in detail.get("comparedPairs", [])
                )
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
        if pos in normalized_positions:
            payload, status = None, "normalizedSameComposition"
            evidence["normalizedRekey"] = normalized_positions[pos]
        elif unit not in current:
            payload, status = None, "unresolvedUnitIdentity"
        else:
            payload, status = lifecycle_payload(
                data(a["sha256"]), data(b["sha256"]), occurrence, row["reason"],
                [metadata(sha) for sha in a["metadataSha256"]],
                [metadata(sha) for sha in b["metadataSha256"]],
            )
        outcome = (
            status if status == "normalizedSameComposition"
            else "review:" + status if payload is None else payload["kind"]
        )
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
    availability: dict[str, Document] = {}
    availability_outcomes = []
    claims_by_comparison: dict[tuple[int, int], list[int]] = {}
    declarations = []
    for pos, row in declaration_rows:
        linked = row["listEvidence"]
        for ev in linked:
            key = (ev["comparisonIndex"], ev["changeIndex"])
            claims_by_comparison.setdefault(key, []).append(pos)
        declarations.append({
            "position": pos, "logicalUnitId": current.get(row["unitId"]),
            "sourceUnitId": row["unitId"], "declaredArmyId": row["declaredFactionId"],
            "direction": row["direction"],
            "earlierObservedDate": row["earlierObservedDate"],
            "laterObservedDate": row["laterObservedDate"],
            "status": "corroboratedListObservation" if linked else "declarationOnly",
            "listComparisonIndices": sorted({ev["comparisonIndex"] for ev in linked}),
        })
    for stream, pos, row in availability_rows:
        ev = row["evidence"]
        a, b = ev["earlier"], ev["later"]
        unit = row["unitId"]
        identity = {
            "logicalUnitId": current.get(unit), "sourceUnitId": unit,
            "earlierObservedDate": a["encodedRevisionDate"],
            "laterObservedDate": b["encodedRevisionDate"],
        }
        evidence = {
            "stream": stream, "position": pos, "comparisonIndex": ev["comparisonIndex"],
            "armyId": ev["factionId"],
            "declarationPositions": claims_by_comparison.get(
                (ev["comparisonIndex"], ev["changeIndex"]), [],
            ),
        }
        if unit not in current:
            payload, status = None, "unresolvedUnitIdentity"
        else:
            payload, status = availability_payload(data(a["sha256"]), data(b["sha256"]), row)
        counts[f"availability:{status}"] += 1
        availability_outcomes.append({
            **identity, **evidence, "sourcePath": row["path"], "outcome": status,
        })
        if payload is not None:
            key = encode({**identity, **payload})
            summary = availability.setdefault(key, {
                **identity, **payload, "status": "observedCandidate", "evidence": [],
            })
            summary["evidence"].append(evidence)
    relationships: dict[str, Document] = {}
    relationship_outcomes = []
    for ci, index, unit, change, ev in relationship_rows:
        a, b = ev["earlier"], ev["later"]
        identity = {
            "logicalUnitId": current.get(unit), "sourceUnitId": unit,
            "earlierObservedDate": a["encodedRevisionDate"],
            "laterObservedDate": b["encodedRevisionDate"],
        }
        evidence = {
            "comparisonIndex": ci, "changeIndex": index, "armyId": ev["factionId"],
            "category": change["category"],
        }
        if unit not in current:
            payload, status = None, "unresolvedUnitIdentity"
        else:
            target_rekeys = {
                (g, later): earlier
                for (comparison, source_unit, g), mapping in rekeys.items()
                if comparison == ci and source_unit == unit
                for earlier, later in mapping.items()
            } if change["path"][-1] == "includes" else {}
            payload, status = relationship_payload(
                data(a["sha256"]), data(b["sha256"]), change, target_rekeys,
            )
            if target_rekeys:
                evidence["targetRekeys"] = [
                    {"groupId": g, "beforeOptionId": i, "afterOptionId": j}
                    for (g, j), i in sorted(target_rekeys.items())
                ]
        field = change["path"][-1]
        counts[f"relationship:{field}:{status}"] += 1
        relationship_outcomes.append({
            **identity, **evidence, "sourcePath": change["path"], "outcome": status,
        })
        if payload is not None:
            key = encode({**identity, **payload})
            summary = relationships.setdefault(key, {**identity, **payload, "evidence": []})
            summary["evidence"].append(evidence)
    counts["relationshipOccurrences"] = len(relationship_rows)
    counts["relationshipConsolidatedSummaries"] = len(relationships)
    counts["relationshipMultiArmySummaries"] = sum(
        len({ev["armyId"] for ev in e["evidence"]}) > 1 for e in relationships.values()
    )
    counts["availabilityOccurrences"] = len(availability_rows)
    counts["availabilityConsolidatedSummaries"] = len(availability)
    counts["availabilityMultiArmySummaries"] = sum(
        len({ev["armyId"] for ev in e["evidence"]}) > 1 for e in availability.values()
    )
    counts["declaredMembershipClaims"] = len(declarations)
    counts["corroboratedMembershipClaims"] = sum(
        d["status"] == "corroboratedListObservation" for d in declarations
    )
    counts["lifecycleUnpairedOccurrences"] = len(lifecycle_rows)
    counts["lifecycleRekeyOccurrences"] = 2 * len(lifecycle_rekeys)
    counts["lifecycleConsolidatedSummaries"] = len(lifecycle)
    counts["lifecycleMultiArmySummaries"] = sum(len(e["evidence"]) > 1 for e in lifecycle.values())
    counts["normalizedRekeyMatches"] = len(normalized_matches)
    counts["acceptedRekeyCollections"] = len(rekeys)
    counts["outsidePilotScopeCandidates"] = len(outside_scope)
    counts["sourceGroupFieldComparisons"] = len(work)
    counts["consolidatedSummaries"] = len(events)
    counts["allGroupLoadoutSummaries"] = sum(e["allGroupLoadouts"] for e in events.values())
    counts["multiArmySummaries"] = sum(len(e["evidence"]) > 1 for e in events.values())
    return {
        "formatVersion": 7, "publicationStatus": "privateResearchOnly", "edition": "n5",
        "archiveSha256": ARCHIVE_PIN, "armyDatabaseSha256": preview["armyDatabaseSha256"],
        "historyDatabaseSha256": preview["historyDatabaseSha256"],
        "counts": dict(counts), "summaries": list(events.values()), "outcomes": outcomes,
        "outsidePilotScope": outside_scope,
        "lifecycleSummaries": list(lifecycle.values()), "lifecycleOutcomes": lifecycle_outcomes,
        "lifecycleRekeys": lifecycle_rekeys, "normalizedRekeys": normalized_matches,
        "availabilitySummaries": list(availability.values()),
        "availabilityOutcomes": availability_outcomes, "membershipDeclarations": declarations,
        "relationshipSummaries": list(relationships.values()),
        "relationshipOutcomes": relationship_outcomes,
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
