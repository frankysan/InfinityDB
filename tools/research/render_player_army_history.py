"""Render an offline, private player-facing N5 Unit history preview."""

from __future__ import annotations

import argparse
import importlib
import json
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Callable
from contextlib import closing
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from infinity_db.army_history_pilot import catalog_index
from infinity_db.army_history_references import resolve_references
from infinity_db.army_history_source import Document, digest, file_digest, read_history, require
from infinity_db.database.repository import Database, identity_config_from_connection
from infinity_db.identities import normalized_profile_identity
from infinity_db.maintained_text import DISTANCE_CENTIMETERS_PER_INCH
from infinity_db.unit_history import army_history_key
from infinity_db.unit_presentation import (
    OPTIONAL_AVAILABILITY_FLAGS,
    _classify_skill_source_presentations,
    _common_bases_with_varying_extras,
    _common_items,
    _general_profile_skills,
    _general_stats,
    _item_identity,
    _normalized_name,
    _unique_items,
)
from tools.research.build_army_history_database import ARCHIVE_PIN, encode
from tools.research.project_army_history import ARMY, HISTORY, ROOT, read_only
from tools.research.render_army_history import FIELDS, details, esc, raw, value_text
from tools.research.summarize_army_history import (
    compact_reference,
    comparable_relationships,
    get_group,
    indexed,
    occurrence_key,
    reference_summary,
    same_labels,
    stable_context,
)

SCALARS = frozenset({"arm", "bs", "bts", "cc", "move", "ph", "s", "str", "w", "wip"})
STREAMS = ("summaries", "lifecycleSummaries", "availabilitySummaries", "relationshipSummaries")
ScopeResolver = Callable[[Document, Document, str], str]

STYLE = """
* {box-sizing:border-box}
:root {
  color-scheme:light dark;--bg:#f5f6f8;--surface:#fff;--ink:#19212d;
  --muted:#526174;--line:#d2dae2;--accent:#245b8e;
}
@media(prefers-color-scheme:dark) {
  :root {--bg:#151c26;--surface:#202a37;--ink:#eef2f6;
    --muted:#b4c2d1;--line:#465564;--accent:#a8d1ff}
}
body {max-width:1240px;margin:0 auto;padding:24px 20px;font:16px/1.5 system-ui;
  color:var(--ink);background:var(--bg);overflow-wrap:anywhere}
h1,h2,h3,h4 {line-height:1.25;margin:0 0 .55em}
h1 {font-size:1.55rem} h2 {font-size:1.5rem} h3 {font-size:1.05rem}
h4 {font-size:.9rem;font-weight:600}
p {margin:.4em 0}
header {border-bottom:1px solid var(--line);padding-bottom:1em}
.notice,.armies,.scope,#shown {font-size:.875rem;color:var(--muted)}
input,select {font:inherit;padding:.5em;max-width:100%;width:100%}
input[type=checkbox] {width:auto}
label {display:block;margin-top:.6em}
.layout {display:grid;grid-template-columns:minmax(0,270px) minmax(0,1fr);
  gap:24px;align-items:start;margin-top:20px}
nav {position:sticky;top:16px;display:grid;gap:.25em}
#unit-select {height:clamp(150px,42vh,380px)}
#unit-select.compact {height:auto}
main {min-width:0}
article {margin:0 0 16px;padding:16px 18px;background:var(--surface);
  border:1px solid var(--line);border-radius:8px}
article h3 {color:var(--accent)}
.army-group {border-top:1px solid var(--line);padding-top:.65em;margin-top:.65em}
.armies {margin:0 0 .6em}
.change-group + .change-group {margin-top:.8em}
.scope {margin:0 0 .15em}
ul {padding-left:1.3em;margin:.15em 0 .3em}
li {margin:.2em 0}
details {margin:.3em 0;font-size:.9em}
summary {cursor:pointer}
pre {white-space:pre-wrap;overflow-wrap:anywhere}
[hidden] {display:none!important}
body:not(.technical) .technical-only {display:none}
:focus-visible {outline:2px solid Highlight;outline-offset:3px}
@media(max-width:720px) {
  body {padding:14px 12px}
  .layout {display:block;margin-top:12px}
  nav {position:static;margin-bottom:1.25em}
  #unit-select {height:8em}
  article {padding:12px}
}
"""
SCRIPT = """
const search = document.querySelector('#search');
const select = document.querySelector('#unit-select');
const options = [...select.options];
const only = document.querySelector('#with-history');
const units = [...document.querySelectorAll('.unit')];
function show() {
  for (const unit of units) unit.hidden = unit.id !== select.value;
  document.querySelector('#empty').hidden = Boolean(select.value);
}
function filter() {
  const query = search.value.trim().toLowerCase();
  const prior = select.value;
  const matches = options.filter(o => o.dataset.search.includes(query) &&
    (!only.checked || o.dataset.history === 'yes'));
  select.replaceChildren(...matches);
  select.classList.toggle('compact', matches.length <= 4);
  select.size = Math.max(1, Math.min(6, matches.length));
  select.value = matches.some(o => o.value === prior) ? prior : (matches[0]?.value ?? '');
  document.querySelector('#shown').textContent =
    matches.length + (matches.length === 1 ? ' Unit found' : ' Units found');
  show();
}
search.addEventListener('input', filter);
select.addEventListener('change', show);
only.addEventListener('change', filter);
document.querySelector('#technical').addEventListener('change', event => {
  document.body.classList.toggle('technical', event.target.checked);
});
filter();
"""


def name(row: Document, fallback: str) -> str:
    return str(row.get("name") or row.get("isc") or fallback).strip()


def labels_scope(labels: list[Document], owner: str) -> str:
    group = name(labels[1], "Profile group")
    target = name(labels[-1], "Unnamed " + owner)
    return f"{target} ({owner})" if group.casefold() == target.casefold() else (
        f"{group} / {target} ({owner})"
    )


def scalar_text(field: str, record: Document) -> str:
    value = record.get("value")
    if field == "move":
        if isinstance(value, list) and len(value) == 2 and all(
            type(v) is int and v >= 0 for v in value
        ):
            distances = [
                format((Decimal(v) / DISTANCE_CENTIMETERS_PER_INCH).normalize(), "f")
                for v in value
            ]
            return "-".join(distances) + '"'
        if value == [-1, -1]:
            return "—"
    if type(value) is int and value == -1:
        return "—"
    return value_text(field, record)


def scalar_rows(unit: Document) -> list[Document]:
    rows = []
    for group in unit["composition"]:
        path = group["sourcePath"]
        if len(path) != 6 or path[4] != "profiles":
            continue
        for change in group["changes"]:
            field = change["field"]
            if field not in SCALARS:
                continue
            require(group["status"] == "observedCandidate", "Unexpected scalar disposition")
            before, after = change["before"], change["after"]
            scopes = sorted({
                labels_scope(labels, "profile") for labels in group["historicalLabels"]
            })
            rows.append({
                "kind": "characteristic", "earlierObservedDate": group["earlierObservedDate"],
                "laterObservedDate": group["laterObservedDate"], "armyIds": group["armyIds"],
                "scope": " / ".join(scopes),
                "text": f"{FIELDS[field]}: {scalar_text(field, before)} → "
                        f"{scalar_text(field, after)}",
                "identity": [path, field, before, after],
                "evidence": {"group": group, "change": change},
            })
    return rows


def summary_text(row: Document, stream: str) -> str:
    if stream == "lifecycleSummaries":
        action = "Added" if row["kind"] == "loadoutAdded" else "Removed"
        return f"{action} loadout · {row['points']} Points, {row['swc']} SWC"
    if stream == "summaries" and row["field"] in {"points", "swc"}:
        targets = row["loadouts"]
        pairs = {(str(t["before"]), str(t["after"])) for t in targets}
        if len(pairs) == 1:
            before, after = next(iter(pairs))
            return f"{FIELDS[row['field']]}: {before} → {after}"
    return str(row["summary"])


def effective_scope(row: Document, group: str) -> str:
    profiles = row.get("profiles", [])
    targets = row["loadouts"]
    if row["allGroupLoadouts"]:
        scope = f"{group} · All loadouts in this group"
    elif profiles and all(p["allProfileLoadouts"] for p in profiles):
        scope = f"{group} · All loadouts for " + ", ".join(
            name(p, "Unnamed profile") for p in profiles
        )
    else:
        scope = f"{group} · " + " / ".join(str(t["label"]) for t in targets)
        if profiles:
            scope += " · Profiles: " + ", ".join(name(p, "Unnamed profile") for p in profiles)
    if any(t.get("relationshipScope") == "directOwners" for t in targets):
        scope += " · Own capabilities only"
    return scope


def compact_option_labels(
    options: dict[int, Document], army: Document,
    contexts: list[dict[str, dict[int, tuple[str, ...]]]],
) -> dict[int, str]:
    """Shorten display labels only; never use them as historical identities."""
    references: dict[int, list[str]] = {}
    complete = True
    for identity, option in options.items():
        parts = []
        for field in ("weapons", "skills", "equip"):
            rows, _ = resolve_references(option.get(field, []), field, army, contexts)
            if rows is None:
                complete = False
                parts.append("Unresolved " + FIELDS[field])
            else:
                parts.extend(compact_reference(row) for row in rows)
        references[identity] = parts
    common: Counter[str] = Counter()
    if complete and len(references) > 1:
        common = Counter(next(iter(references.values())))
        for parts in references.values():
            common &= Counter(parts)

    labels = {}
    for identity, option in options.items():
        remaining = common.copy()
        distinct = []
        for part in references[identity]:
            if remaining[part]:
                remaining[part] -= 1
            else:
                distinct.append(part)
        label = name(option, "Loadout")
        shown = distinct or references[identity]
        if shown:
            label += " — " + "; ".join(shown)
        labels[identity] = label

    # Same-name siblings can differ only in shared references or cost.
    repeated = Counter(labels.values())
    for identity, label in labels.items():
        if repeated[label] > 1:
            option = options[identity]
            label += f" ({option.get('points', '?')} Points, {option.get('swc', '?')} SWC)"
            labels[identity] = label
    repeated = Counter(labels.values())
    return {
        identity: label + (" (not uniquely distinguished)" if repeated[label] > 1 else "")
        for identity, label in labels.items()
    }


def historical_scopes(db: sqlite3.Connection, archive: Path) -> ScopeResolver:
    """Resolve historical group/owner labels at the exact evidence endpoint."""
    source = read_history(archive, ARCHIVE_PIN)
    comparisons = dict(db.execute("SELECT comparison_index,body FROM comparison"))

    @lru_cache(maxsize=48)
    def data(sha: str) -> Document:
        return source.read_object(sha)

    @lru_cache(maxsize=64)
    def metadata(sha: str) -> dict[str, dict[int, tuple[str, ...]]]:
        return catalog_index(data(sha))

    @lru_cache(maxsize=512)
    def option_labels(
        sha: str, metadata_shas: tuple[str, ...], source_unit: int, group_id: int,
    ) -> dict[int, str]:
        army = data(sha)
        result = get_group(army, source_unit, group_id)
        require(result is not None, "Historical summary group no longer resolves")
        assert result is not None
        return compact_option_labels(
            indexed(result[1].get("options")) or {}, army,
            [metadata(value) for value in metadata_shas],
        )

    def resolve(row: Document, evidence: Document, stream: str) -> str:
        if stream == "availabilitySummaries" and row["kind"].startswith("armyList"):
            return ""
        side = "later" if row.get("kind") == "loadoutAdded" else "earlier"
        endpoint = json.loads(comparisons[evidence["comparisonIndex"]])[side]
        army = data(endpoint["sha256"])
        path = row.get("sourcePath", [])
        group_id = row["groupId"] if "groupId" in row else path[3]
        result = get_group(army, row["sourceUnitId"], group_id)
        require(result is not None, "Historical summary group no longer resolves")
        assert result is not None
        unit, group = result
        group_name = name(group, name(unit, "Profile group"))
        options = indexed(group.get("options")) or {}
        if stream == "summaries":
            profiles = indexed(group.get("profiles")) or {}
            if len(profiles) == 1:
                profile = name(next(iter(profiles.values())), "Unnamed profile")
                if profile.casefold() != group_name.casefold():
                    group_name += " / " + profile
            if not row["allGroupLoadouts"]:
                labels = option_labels(
                    endpoint["sha256"], tuple(endpoint["metadataSha256"]),
                    row["sourceUnitId"], group_id,
                )
                row = {**row, "loadouts": [
                    {**target, "label": labels[target["optionId"]]}
                    for target in row["loadouts"]
                ]}
            return effective_scope(row, group_name)
        if stream == "lifecycleSummaries":
            profile = str(row["profileName"] or "Unnamed profile").strip()
            prefix = group_name if profile.casefold() == group_name.casefold() else (
                group_name + " / " + profile
            )
            labels = option_labels(
                endpoint["sha256"], tuple(endpoint["metadataSha256"]),
                row["sourceUnitId"], group_id,
            )
            return prefix + " · " + labels[row["optionId"]]
        owner = path[4]
        if owner == "options":
            require(path[5] in options, "Historical loadout no longer resolves")
            labels = option_labels(
                endpoint["sha256"], tuple(endpoint["metadataSha256"]),
                row["sourceUnitId"], group_id,
            )
            return group_name + " · " + labels[path[5]] + " (loadout)"
        require(owner == "profiles", "Unsupported historical owner")
        profiles = indexed(group.get("profiles")) or {}
        require(path[5] in profiles, "Historical profile no longer resolves")
        return labels_scope([unit, group, profiles[path[5]]], "profile")

    return resolve


def classification_rows(rows: list[Document]) -> list[Document]:
    """Describe exact same-scope cross-catalog transitions without inferring mechanics."""
    candidates: dict[str, list[tuple[int, str, Document]]] = defaultdict(list)
    for index, row in enumerate(rows):
        if row["kind"] != "summaries":
            continue
        identity = row["identity"]
        if identity["field"] not in {"skills", "equip", "weapons"}:
            continue
        lost, gained = identity.get("lost", []), identity.get("gained", [])
        if len(lost) + len(gained) != 1:
            continue
        direction = "lost" if lost else "gained"
        reference = (lost or gained)[0]
        target = reference["filter"]
        if not target.get("name") or not target.get("wiki"):
            continue
        context = {
            k: v for k, v in identity.items() if k not in {"field", "lost", "gained", "summary"}
        }
        # Candidate positions differ by field; all comparison and pair coverage must agree.
        evidence = sorted(
            encode({k: v for k, v in item.items() if k != "candidatePositions"})
            for item in row["evidence"]["evidence"]
        )
        key = encode({
            "context": context, "scope": row["scope"], "armyIds": row["armyIds"],
            "evidence": evidence, "name": target["name"], "wiki": target["wiki"],
            "occurrence": reference["occurrence"],
        })
        candidates[key].append((index, direction, reference))

    replacements: dict[int, Document] = {}
    consumed: set[int] = set()
    for matches in candidates.values():
        if len(matches) != 2 or {m[1] for m in matches} != {"lost", "gained"}:
            continue
        (a, _, before), (b, _, after) = sorted(matches, key=lambda m: m[1], reverse=True)
        left, right = rows[a], rows[b]
        old, new = left["identity"]["field"], right["identity"]["field"]
        if old == new:
            continue
        identity = {
            k: v for k, v in left["identity"].items()
            if k not in {"field", "lost", "gained", "summary"}
        }
        replacements[min(a, b)] = {
            **left, "kind": "classification",
            "text": f"{compact_reference(before)}: {FIELDS[old]} → {FIELDS[new]} (classification)",
            "identity": {**identity, "beforeField": old, "afterField": new,
                         "beforeReference": before, "afterReference": after},
            "evidence": {"from": left["evidence"], "to": right["evidence"]},
        }
        consumed.update((a, b))
    return [replacements[i] if i in replacements else row
            for i, row in enumerate(rows) if i in replacements or i not in consumed]


def effect_identity(row: Document) -> Document | list:
    identity = row["identity"]
    if row["kind"] == "summaries" and identity["allGroupLoadouts"]:
        # The same group-wide effect may cover different loadout definitions.
        loadouts = identity["loadouts"]
        identity = {k: v for k, v in identity.items() if k != "loadouts"}
        if identity["field"] in {"points", "swc"}:
            # A shared delta is not sufficient if the actual costs differ.
            identity["costPairs"] = sorted({
                encode([target["before"], target["after"]]) for target in loadouts
            })
    return identity


def model(
    preview: Document, semantic: Document, resolve: ScopeResolver,
) -> tuple[list[Document], dict[str, int]]:
    units = {
        u["logicalUnitId"]: {**u, "entries": scalar_rows(u), "semanticReview": {}}
        for u in preview["units"]
    }
    for stream, supported in (
        ("outcomes", {"changedEffective", "unchangedEffective"}),
        ("lifecycleOutcomes", {"loadoutAdded", "loadoutRemoved", "normalizedSameComposition"}),
        ("availabilityOutcomes", {"observedFieldChange", "observedListPresence"}),
        ("relationshipOutcomes", {"changedRelationship", "unchangedRelationship"}),
    ):
        for row in semantic[stream]:
            if row["logicalUnitId"] in units and row["outcome"] not in supported:
                unit = units[row["logicalUnitId"]]
                unit["semanticReview"].setdefault(stream, []).append(row)
    counts: Counter[str] = Counter()
    counts["scalarCandidates"] = sum(len(u["entries"]) for u in units.values())
    for stream in STREAMS:
        for row in semantic[stream]:
            require(row["logicalUnitId"] in units, "Summary has no logical Unit")
            # A consolidated summary can cover different historical group names.
            scopes: dict[str, list[Document]] = defaultdict(list)
            for evidence in row["evidence"]:
                scopes[resolve(row, evidence, stream)].append(evidence)
            require(bool(scopes), "Summary has no evidence")
            for scope, evidence_rows in scopes.items():
                units[row["logicalUnitId"]]["entries"].append({
                    "kind": stream, "earlierObservedDate": row["earlierObservedDate"],
                    "laterObservedDate": row["laterObservedDate"],
                    "armyIds": sorted({e["armyId"] for e in evidence_rows}),
                    "scope": scope, "text": summary_text(row, stream),
                    "identity": {k: v for k, v in row.items() if k != "evidence"},
                    "evidence": {**row, "evidence": evidence_rows},
                })
            counts[stream] += 1
    for unit in units.values():
        # Merge only identical semantic targets and windows; display text alone
        # is not an identity. Preserve all original evidence.
        merged: dict[str, Document] = {}
        for row in classification_rows(unit["entries"]):
            identity = effect_identity(row)
            key = encode({
                **{k: v for k, v in row.items() if k not in {"armyIds", "evidence", "identity"}},
                "identity": identity,
            })
            target = merged.setdefault(key, {**row, "armyIds": [], "evidence": []})
            target["armyIds"] = sorted(set(target["armyIds"]) | set(row["armyIds"]))
            target["evidence"].append(row["evidence"])
        unit["entries"] = sorted(merged.values(), key=lambda row: (
            row["laterObservedDate"], row["earlierObservedDate"],
            row["scope"], row["text"], encode(row["identity"]),
        ), reverse=True)
    counts["units"] = len(units)
    counts["unitsWithHistory"] = sum(bool(u["entries"]) for u in units.values())
    counts["timelineEntries"] = sum(len(u["entries"]) for u in units.values())
    return sorted(units.values(), key=lambda u: (
        (u["name"] or "").casefold(), u["logicalUnitId"],
    )), dict(counts)


def presentation_rows(rows: list[Document]) -> list[Document]:
    """Share equivalent dated changes across disjoint Army scopes, not source windows."""
    candidates: dict[str, list[Document]] = defaultdict(list)
    for row in rows:
        identity = effect_identity(row)
        if isinstance(identity, dict):
            identity = {k: v for k, v in identity.items() if k != "earlierObservedDate"}
        key = encode({
            "kind": row["kind"], "date": row["laterObservedDate"], "scope": row["scope"],
            "text": row["text"], "identity": identity,
        })
        candidates[key].append(row)

    result = []
    for changes in candidates.values():
        army_ids = [army for row in changes for army in row["armyIds"]]
        if len(army_ids) != len(set(army_ids)):
            # Multiple observations for one Army may represent alternatives or
            # distinct transitions. Do not hide them in a combined display.
            result.extend({**row, "observations": [row]} for row in changes)
        else:
            result.append({
                **changes[0], "armyIds": sorted(army_ids), "observations": changes,
            })
    return result


CONTEXT_STYLE = """
.profile-card,.army-card {background:var(--surface);border:1px solid var(--line);
  border-radius:8px;padding:14px 16px;margin:0 0 12px}
.army-card>summary,.history>summary {font-size:1rem;font-weight:600}
.history {border-top:1px solid var(--line);padding-top:10px;margin-top:12px}
.history article {margin:10px 0;padding:12px;background:var(--bg)}
.history .change-group {padding:9px 0;border-top:1px solid var(--line)}
.history .scope {font-weight:600;color:var(--ink)}
.history-category {font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;
  color:var(--muted);margin:9px 0 4px}
.history-list {list-style:none;padding:0;margin:0}
.history-list li {border-left:3px solid var(--line);padding:5px 9px;margin:3px 0}
.history-list .costs {border-color:var(--accent)}
.history-list .classification {border-style:dashed}
.history-list .action {font-size:.75rem;color:var(--muted);font-weight:600;
  display:inline-block;margin-right:6px}
.history-list .change-line {padding:3px 0 3px 8px;border-left:3px solid var(--line)}
.history-list .action-gained,.history-list .action-added {border-left-color:#31956b}
.history-list .action-lost,.history-list .action-removed {border-left-color:#c95b60}
.history-list .action-changed {border-left-color:var(--accent)}
.history-list .action-classification {border-left-style:dashed}
.history-list .change-line+.change-line {margin-top:3px}
.history-list li {border-left:0;padding:2px 0}
.history-list .technical-only {padding-left:11px}
.statline {display:flex;flex-wrap:wrap;gap:6px 12px;margin:8px 0}
.statline span {min-width:30px;text-align:center}
.statline small {display:block;color:var(--muted)}
.current-items {font-size:.9rem;margin:7px 0}
.current-loadouts {font-size:.85rem}
.current-loadouts li {margin:4px 0}
"""

GENERAL_STAT_FIELDS = {
    "arm": "arm", "bs": "bs", "bts": "bts", "cc": "cc",
    "ph": "ph", "wip": "wip", "s": "silhouette",
}


def scalar_general_target(
    row: Document, source_ids: list[int], general: list[Document],
    known_armies: set[int], endpoints: list[tuple[int, Document, Document]],
    profile_identity: Callable[[object], str],
) -> str | None:
    """Pilot: unanimous scalar transitions on a single stable source Unit.

    Every known list context must end on the same encoded revision date.
    No missing, ambiguous, extra or moved profile occurrence is promoted.
    """
    if row["kind"] != "characteristic" or len(source_ids) != 1:
        return None
    path, field, before, after = row["identity"]
    if field not in GENERAL_STAT_FIELDS or path[1] != source_ids[0]:
        return None
    if set(row["armyIds"]) != known_armies or not known_armies:
        return None
    if {army for army, _, _ in endpoints} != known_armies or len(endpoints) != len(known_armies):
        return None
    if not all(record.get("present") and type(record.get("value")) is int
               for record in (before, after)):
        return None
    identities = set()
    values: list[list[Document]] = [[], []]
    prop = GENERAL_STAT_FIELDS[field]
    for _, earlier, later in endpoints:
        for side, army in enumerate((earlier, later)):
            found = get_group(army, path[1], path[3])
            if found is None:
                return None
            unit, group = found
            profiles = indexed(group.get("profiles")) or {}
            target = profiles.get(path[5])
            if target is None or not target.get("name"):
                return None
            identity = profile_identity(target["name"])
            identities.add(identity)
            groups = indexed(unit.get("profileGroups"))
            if groups is None:
                return None
            occurrences = []
            for group_id, candidate_group in groups.items():
                candidates = indexed(candidate_group.get("profiles"))
                if candidates is None:
                    return None
                occurrences.extend(
                    (group_id, profile_id) for profile_id, profile in candidates.items()
                    if profile_identity(profile.get("name")) == identity
                )
            if occurrences != [(path[3], path[5])]:
                return None
            expected = (before, after)[side]["value"]
            if target.get(field) != expected:
                return None
            values[side].append({prop: expected})
    if len(identities) != 1:
        return None
    identity = next(iter(identities))
    if not identity or sum(g["profile_identity"] == identity for g in general) != 1:
        return None
    if [_general_stats(value)[prop] for value in values] != [before["value"], after["value"]]:
        return None
    return identity


ITEM_FIELDS = {"skills": "skills", "equip": "equipment", "weapons": "weapons"}


def historical_items(
    owner: Document, field: str, army: Document, metadata: list,
) -> list[Document] | None:
    refs, _ = resolve_references(owner.get(field, []), field, army, metadata)
    if refs is None:
        return None
    items = []
    for ref in refs:
        occurrence = ref["occurrence"]
        quantity = occurrence.get("q")
        if set(occurrence) - {"q", "extra"} or (
            quantity is not None and (type(quantity) is not int or quantity < 1)
        ):
            return None
        items.append({
            "id": ref["filter"]["id"], "name": ref["filter"]["name"],
            "quantity": quantity, "extras": occurrence.get("extra") or [],
            "reference": ref,
        })
    return items


def projected_items(
    profiles: list[Document], loadouts: list[Document], field: str,
) -> list[Document]:
    """Reuse the same shared-item composition as current General profiles."""
    prop = ITEM_FIELDS[field]
    if field == "skills":
        return _general_profile_skills(profiles, loadouts)
    owners = loadouts if field == "weapons" else profiles
    return _unique_items([
        *_common_items(owners, prop), *_common_bases_with_varying_extras(loadouts, prop),
    ])


def historical_shared_delta(
    rows: list[Document], source_id: int, general: list[Document],
    endpoints: list[tuple[int, Document, Document, list, list]],
    profile_identity: Callable[[object], str],
    excluded: set[tuple[str, int]], aliases: set[tuple[str, int]],
    equipment_classes: dict[int, tuple[str, str]] | None = None,
    target_profile_id: int | None = None,
) -> tuple[str, Document] | None:
    """Compare exact endpoint projections for one uniquely identified profile.

    Only accepted effective occurrence changes can be promoted. A synthetic
    common base with differing extras is not an exact source occurrence.
    """
    sample = rows[0]["identity"]
    group_id, field = sample["groupId"], sample["field"]
    prop = ITEM_FIELDS[field]
    if target_profile_id is not None:
        # Group-owned loadout effects must not be attributed to just one form.
        if field == "weapons" or any(
            [p["profileId"] for p in row["identity"].get("profiles", [])]
            != [target_profile_id] for row in rows
        ):
            return None
    equipment_classes = equipment_classes or {}
    # Current presentation classification is not a historical gameplay claim.
    # Reject a classified occurrence if its native counterpart may also exist.
    counterpart_names: set[str] = set()
    invalid_classified_ids: set[int] = set()
    counterpart_complete = True
    identities = set()
    owner_profiles: list[list[Document]] = [[], []]
    owner_options: list[list[Document]] = [[], []]
    for _, old, new, meta_old, meta_new in endpoints:
        context, _ = stable_context(
            old, new, source_id, group_id, profile_id=target_profile_id,
            allow_stable_relationships=True,
        )
        if context is None:
            return None
        pa, oa, pb, ob = context
        if target_profile_id is not None:
            first, second = get_group(old, source_id, group_id), get_group(new, source_id, group_id)
            assert first is not None and second is not None
            siblings_a = indexed(first[1].get("profiles"))
            siblings_b = indexed(second[1].get("profiles"))
            if (not siblings_a or not siblings_b or len(siblings_a) < 2
                    or siblings_a.keys() != siblings_b.keys()
                    or any(not same_labels(siblings_a[i], siblings_b[i]) for i in siblings_a)):
                return None
            if any(
                profile_identity(p.get("name")) != profile_identity(pa["name"])
                for row in rows for p in row["identity"]["profiles"]
            ):
                return None
        if any(
            not comparable_relationships(oa[i], ob[i], old, new, source_id, True)
            or (any(o.get("includes") or o.get("peripheral") for o in (oa[i], ob[i]))
                and not same_labels(oa[i], ob[i]))
            for i in oa.keys() & ob.keys()
        ):
            return None
        if any(
            option.get("includes") or option.get("peripheral")
            for options, other in ((oa, ob), (ob, oa))
            for i, option in options.items() if i not in other
        ):
            return None
        for side, (army, meta, profile, options) in enumerate((
            (old, meta_old, pa, oa), (new, meta_new, pb, ob),
        )):
            if not profile.get("name") or any(o.get("disabled") for o in options.values()):
                return None
            identity = profile_identity(profile["name"])
            identities.add(identity)
            found = get_group(army, source_id, group_id)
            assert found is not None
            groups = indexed(found[0].get("profileGroups"))
            if groups is None:
                return None
            occurrences = []
            for gid, group in groups.items():
                candidates = indexed(group.get("profiles"))
                if candidates is None:
                    return None
                occurrences.extend(
                    (gid, pid) for pid, candidate in candidates.items()
                    if profile_identity(candidate.get("name")) == identity
                )
            if occurrences != [(group_id, profile["id"])]:
                return None
            for owner, destination in (
                (profile, owner_profiles[side]),
                *((o, owner_options[side]) for o in options.values()),
            ):
                items = historical_items(owner, field, army, meta)
                if items is None or any((field, item["id"]) in aliases for item in items):
                    return None
                destination.append({prop: items})
                if field == "skills":
                    invalid_classified_ids.update(
                        item["id"] for item in items if item["id"] in equipment_classes
                        and item["name"] != equipment_classes[item["id"]][0]
                    )
                if equipment_classes and field in {"skills", "equip"}:
                    other = "equip" if field == "skills" else "skills"
                    counterpart = historical_items(owner, other, army, meta)
                    if counterpart is None:
                        counterpart_complete = False
                    else:
                        counterpart_names.update(
                            _normalized_name(item["name"]) for item in counterpart
                            if other == "equip" or item["id"] in equipment_classes
                        )
    if len(identities) != 1:
        return None
    identity = next(iter(identities))
    if not identity or sum(g["profile_identity"] == identity for g in general) != 1:
        return None
    # Compute both shared projections, including options entering or leaving the list.
    before, after = [
        {_item_identity(item): item for item in projected_items(p, o, field)}
        for p, o in zip(owner_profiles, owner_options, strict=True)
    ]
    # In a multi-profile Group, only promote direct profile-owned changes.
    # The same loadout is part of every sibling's canonical projection.
    profile_items = [
        {_item_identity(item) for item in _common_items(profiles, prop)}
        for profiles in owner_profiles
    ]
    loadout_ids = {
        item["id"] for options in owner_options for option in options for item in option[prop]
    }
    delta: Document = {"lost": [], "gained": []}
    for direction, own, other in (("lost", before, after), ("gained", after, before)):
        accepted = {
            occurrence_key(ref)
            for row in rows for ref in row["identity"][direction]
        }
        for key in own.keys() - other.keys():
            item = own[key]
            if target_profile_id is not None and (
                key not in profile_items[0 if direction == "lost" else 1]
                or item["id"] in loadout_ids
            ):
                continue
            ref = item["reference"]
            original = {
                "id": ref["filter"]["id"], "quantity": ref["occurrence"].get("q"),
                "extras": ref["occurrence"].get("extra") or [],
            }
            if _item_identity(original) != key or occurrence_key(ref) not in accepted:
                continue
            classification = equipment_classes.get(item["id"]) if field == "skills" else None
            if (field, item["id"]) in excluded:
                if classification is None or not counterpart_complete:
                    continue
                source_name, slug = classification
                if (item["id"] in invalid_classified_ids or item["name"] != source_name
                        or _normalized_name(source_name) in counterpart_names
                        or _normalized_name(slug) in counterpart_names):
                    continue
                # Use the actual presentation policy rather than a history-only category.
                buckets = {"skills": [{**item, "slug": slug}], "equipment": [], "weapons": []}
                _classify_skill_source_presentations(buckets, {slug: "equipment"})
                if len(buckets["equipment"]) != 1:
                    continue
            elif field == "equip" and equipment_classes:
                classified_names = {
                    _normalized_name(name) for name, _ in equipment_classes.values()
                } | {_normalized_name(slug) for _, slug in equipment_classes.values()}
                if _normalized_name(item["name"]) in classified_names and (
                    not counterpart_complete or _normalized_name(item["name"]) in counterpart_names
                ):
                    continue
            delta[direction].append(ref)
        delta[direction].sort(key=occurrence_key)
    return (identity, delta) if delta["lost"] or delta["gained"] else None


def subtract_shared(row: Document, delta: Document) -> Document | None:
    """Keep nonshared effects and original evidence; remove one occurrence per key."""
    identity = row["identity"]
    residual = {}
    for direction in ("lost", "gained"):
        remaining = Counter(map(occurrence_key, delta[direction]))
        refs = []
        for ref in identity[direction]:
            key = occurrence_key(ref)
            if remaining[key]:
                remaining[key] -= 1
            else:
                refs.append(ref)
        residual[direction] = refs
    if not residual["lost"] and not residual["gained"]:
        return None
    return {**row, "identity": {**identity, **residual},
            "text": reference_summary(residual)}


def common_revision_records(
    comparisons: dict[tuple[int, str], list[tuple[str, Document]]],
    armies: set[int], later: str, rows: list[Document],
) -> list[tuple[int, str, Document]] | None:
    """Select one unambiguous comparison ending at the same revision per Army."""
    if not armies:
        return None
    records = []
    windows = {}
    for army in sorted(armies):
        choices = comparisons.get((army, later), [])
        if len(choices) != 1:
            return None
        earlier, record = choices[0]
        if earlier >= later:
            return None
        windows[army] = earlier
        records.append((army, earlier, record))
    if any(
        row["laterObservedDate"] != later
        or any(windows.get(army) != row["earlierObservedDate"] for army in row["armyIds"])
        for row in rows
    ):
        return None
    return records


def same_revision_scalars(entries: list[Document]) -> list[list[int]]:
    """Group equal scalar transitions by later revision, not acquisition window."""
    buckets: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(entries):
        if row["kind"] == "characteristic":
            key = encode([row["laterObservedDate"], row["identity"]])
            buckets[key].append(index)
    return list(buckets.values())


def unanimous_revision_delta(
    rows: list[Document], source_id: int, general: list[Document],
    endpoints: list[tuple[int, Document, Document, list, list]],
    profile_identity: Callable[[object], str],
    excluded: set[tuple[str, int]], aliases: set[tuple[str, int]],
    equipment_classes: dict[int, tuple[str, str]], profile_id: int | None,
) -> tuple[str, Document] | None:
    """Require each Army to independently support the promoted item transition."""
    result = historical_shared_delta(
        rows, source_id, general, endpoints, profile_identity, excluded, aliases,
        equipment_classes, target_profile_id=profile_id,
    )
    if result is None:
        return None
    target, delta = result
    supported = {direction: {occurrence_key(ref) for ref in delta[direction]}
                 for direction in ("lost", "gained")}
    for endpoint in endpoints:
        local_rows = [row for row in rows if endpoint[0] in row["armyIds"]]
        if not local_rows:
            return None
        local = historical_shared_delta(
            local_rows, source_id, general, [endpoint], profile_identity, excluded, aliases,
            equipment_classes, target_profile_id=profile_id,
        )
        if local is None or local[0] != target:
            return None
        for direction in supported:
            supported[direction] &= {occurrence_key(ref) for ref in local[1][direction]}
    delta = {direction: [ref for ref in delta[direction]
                        if occurrence_key(ref) in supported[direction]]
             for direction in supported}
    return (target, delta) if delta["lost"] or delta["gained"] else None


def contextual_model(
    units: list[Document], history: sqlite3.Connection, archive: Path,
) -> dict[str, int]:
    """Attach current card contexts and promote fully covered shared changes."""
    database = Database(ARMY)
    general = database.general_profiles(
        [u["logicalUnitId"] for u in units], frozenset(OPTIONAL_AVAILABILITY_FLAGS),
    )
    require(general is not None, "Current General-profile projection unavailable")
    assert general is not None
    with closing(read_only(ARMY)) as db:
        db.row_factory = sqlite3.Row
        config = identity_config_from_connection(db)
        source_armies = defaultdict(set)
        for app, source in db.execute(
            "SELECT application_army_id,source_army_id FROM application_army_sources "
            "WHERE has_army_list=1"
        ):
            source_armies[source].add(app)
        memberships = set(
            tuple(row) for row in db.execute("SELECT unit_id,army_id FROM army_units")
        )
        source_fields = {v: k for k, v in ITEM_FIELDS.items()}
        aliases = {
            (source_fields[catalog], source_id)
            for catalog, source_id, app_id in db.execute(
                "SELECT catalog,source_item_id,application_item_id "
                "FROM application_catalog_sources"
            )
            if catalog in source_fields and source_id != app_id
        }
        excluded = {
            ("skills", source_id) for (source_id,) in db.execute(
                "SELECT s.source_item_id FROM application_catalog_sources s "
                "JOIN skill_source_classifications c "
                "ON s.application_item_id=c.application_skill_id "
                "WHERE s.catalog='skills'"
            )
        }
        equipment_classes = {
            source_id: (source_name, slug)
            for source_id, source_name, slug in db.execute(
                "SELECT s.source_item_id,s.source_name,d.slug "
                "FROM application_catalog_sources s "
                "JOIN skill_source_classifications c "
                "ON s.application_item_id=c.application_skill_id "
                "JOIN application_domain_slugs d "
                "ON d.domain='skills' AND d.application_id=s.application_item_id "
                "WHERE s.catalog='skills' AND c.classification='equipment' "
                "AND d.status='resolved' AND d.slug IS NOT NULL "
                "AND s.source_item_id=s.application_item_id"
            )
        }
        # Do not retrospectively project snapshot-bound reviewed capabilities.
        from infinity_db.database.reviewed_loadout_capabilities import (
            published_reviewed_loadout_capabilities,
        )
        reviewed_units = {fact["unit_id"] for fact in published_reviewed_loadout_capabilities(db)}
    comparisons: dict[tuple[int, str], list[tuple[str, Document]]] = defaultdict(list)
    for army, earlier, later, body in history.execute(
        "SELECT army_id,earlier_date,later_date,body FROM comparison"
    ):
        comparisons[(army, later)].append((earlier, json.loads(body)))
    inventory = dict(history.execute("SELECT unit_id,body FROM unit_identity"))
    source = read_history(archive, ARCHIVE_PIN)

    @lru_cache(maxsize=48)
    def endpoint(sha: str) -> Document:
        return source.read_object(sha)

    @lru_cache(maxsize=64)
    def metadata(sha: str) -> dict:
        return catalog_index(endpoint(sha))

    counts: Counter[str] = Counter()
    for unit in units:
        logical = unit["logicalUnitId"]
        current = database.get_unit(logical)
        require(current is not None, "Current logical Unit missing")
        assert current is not None
        source_ids = current["source_ids"]
        profiles = [p for p in general[logical] if p.get("presentation_visible") is not False]
        unit["currentGeneral"] = profiles
        unit["currentArmies"] = current["armies"]
        unit["generalHistory"] = defaultdict(list)
        unit["armyHistory"] = defaultdict(list)
        unit["unmatchedHistory"] = defaultdict(list)
        known_armies: set[int] = set()
        declared_armies: set[int] = set()
        declared_complete = True
        if len(source_ids) == 1 and source_ids[0] in inventory:
            for slug in json.loads(inventory[source_ids[0]])["slugEvidence"]:
                for item in slug["occurrences"]:
                    known_armies.add(item["factionId"])
                    factions = item.get("factions")
                    if isinstance(factions, list) and all(type(i) is int for i in factions):
                        declared_armies.update(factions)
                    else:
                        declared_complete = False
        current_source_armies = {army for source_id, army in memberships if source_id in source_ids}
        entries = unit["entries"]
        residuals: dict[int, Document | None] = {}
        if (len(source_ids) == 1 and source_ids[0] not in reviewed_units
                and declared_complete and known_armies
                and declared_armies <= known_armies and current_source_armies <= known_armies):
            buckets: dict[tuple, list[int]] = defaultdict(list)
            blocked: set[tuple] = set()
            multi_target: dict[tuple, set[int]] = defaultdict(set)
            for index, row in enumerate(entries):
                identity = row["identity"]
                if row["kind"] not in {"summaries", "classification"}:
                    continue
                pair = (row["laterObservedDate"], identity["groupId"])
                if row["kind"] == "classification":
                    blocked.update((*pair, identity[f]) for f in ("beforeField", "afterField"))
                elif identity["field"] in ITEM_FIELDS and identity["sourceUnitId"] == source_ids[0]:
                    key = (*pair, identity["field"])
                    targets = identity.get("profiles", [])
                    if len(targets) > 1:
                        multi_target[key].update(p["profileId"] for p in targets)
                    else:
                        profile_id = targets[0]["profileId"] if targets else None
                        buckets[(*key, profile_id)].append(index)
            for key, indexes in buckets.items():
                later, group, field, profile_id = key
                if key[:-1] in blocked or profile_id in multi_target[key[:-1]]:
                    continue
                candidates = [entries[i] for i in indexes]
                selected = common_revision_records(comparisons, known_armies, later, candidates)
                if selected is None:
                    continue
                earlier = min(start for _, start, _ in selected)
                asynchronous = len({start for _, start, _ in selected}) > 1
                records = [record for _, _, record in selected]
                item_endpoints = [
                    (army, endpoint(record["earlier"]["sha256"]),
                     endpoint(record["later"]["sha256"]),
                     [metadata(sha) for sha in record["earlier"]["metadataSha256"]],
                     [metadata(sha) for sha in record["later"]["metadataSha256"]])
                    for army, _, record in selected
                ]
                def identity_for(label: object) -> str:
                    return normalized_profile_identity(label, config)

                if asynchronous:
                    result = unanimous_revision_delta(
                        candidates, source_ids[0], profiles, item_endpoints, identity_for,
                        excluded, aliases, equipment_classes, profile_id,
                    )
                else:
                    result = historical_shared_delta(
                        candidates, source_ids[0], profiles, item_endpoints, identity_for,
                        excluded, aliases, equipment_classes, target_profile_id=profile_id,
                    )
                if result is None:
                    continue
                target, delta = result
                display_deltas: dict[str, Document] = {}
                for direction in ("lost", "gained"):
                    for ref in delta[direction]:
                        classified = field == "skills" and ref["filter"]["id"] in equipment_classes
                        display_field = "equip" if classified else field
                        display_deltas.setdefault(
                            display_field, {"lost": [], "gained": []},
                        )[direction].append(ref)
                for display_field, display_delta in display_deltas.items():
                    unit["generalHistory"][target].append({
                        "kind": "summaries", "scope": "",
                        "earlierObservedDate": earlier, "laterObservedDate": later,
                        "armyIds": sorted(known_armies), "text": reference_summary(display_delta),
                        "identity": {"field": display_field, "sourceUnitId": source_ids[0],
                                     "groupId": group, **display_delta},
                        "evidence": {
                            "observations": [row["evidence"] for row in candidates],
                            "generalAttribution": {
                                "profileIdentity": target,
                                "method": ("sharedItemsCommonRevision" if asynchronous
                                           else "sharedItemsExactWindows"),
                                "comparisonEndpoints": records, "sourceField": field,
                                "comparisonWindows": [
                                    {"armyId": army, "earlier": start, "later": later}
                                    for army, start, _ in selected
                                ],
                                "sourceProfileId": profile_id, "delta": display_delta,
                            },
                        },
                    })
                    counts["generalEntries"] += 1
                    counts["generalItemEntries"] += 1
                    if asynchronous:
                        counts["commonRevisionItemEntries"] += 1
                    if profile_id is not None:
                        counts["multiProfileItemEntries"] += 1
                    if field != display_field:
                        counts["classifiedEquipmentEntries"] += 1
                for index in indexes:
                    residual = subtract_shared(entries[index], delta)
                    residuals[index] = residual
                    if residual is None:
                        counts["fullyPromotedItemRows"] += 1
            entries = [residuals.get(i, row) for i, row in enumerate(entries)]
            entries = [row for row in entries if row is not None]
        promoted_scalars: set[int] = set()
        if (declared_complete and declared_armies <= known_armies
                and current_source_armies <= known_armies):
            for indexes in same_revision_scalars(entries):
                candidates = [entries[i] for i in indexes]
                row = candidates[0]
                army_ids = [army for candidate in candidates for army in candidate["armyIds"]]
                if set(army_ids) != known_armies or len(army_ids) != len(known_armies):
                    continue
                later = row["laterObservedDate"]
                selected = common_revision_records(comparisons, known_armies, later, candidates)
                if selected is None:
                    continue
                endpoints = [
                    (army, endpoint(record["earlier"]["sha256"]),
                     endpoint(record["later"]["sha256"]))
                    for army, _, record in selected
                ]
                merged = {**row, "armyIds": sorted(army_ids),
                          "earlierObservedDate": min(start for _, start, _ in selected)}
                target = scalar_general_target(
                    merged, source_ids, profiles, known_armies, endpoints,
                    lambda label: normalized_profile_identity(label, config),
                )
                if target is None:
                    continue
                asynchronous = len({start for _, start, _ in selected}) > 1
                unit["generalHistory"][target].append({
                    **merged, "evidence": {
                        "observations": [candidate["evidence"] for candidate in candidates],
                        "generalAttribution": {
                            "profileIdentity": target, "knownArmyIds": sorted(known_armies),
                            "declaredArmyIds": sorted(declared_armies),
                            "method": ("unanimousScalarCommonRevision" if asynchronous
                                       else "unanimousScalarExactWindows"),
                            "comparisonWindows": [
                                {"armyId": army, "earlier": start, "later": later}
                                for army, start, _ in selected
                            ],
                        },
                    },
                })
                counts["generalEntries"] += 1
                if asynchronous:
                    counts["commonRevisionScalarEntries"] += 1
                promoted_scalars.update(indexes)
        for index, row in enumerate(entries):
            if index in promoted_scalars:
                continue
            identity = row["identity"]
            source_id = identity[0][1] if isinstance(identity, list) else identity["sourceUnitId"]
            for army in row["armyIds"]:
                matches = [
                    i for i, card in enumerate(current["armies"])
                    if card["id"] in source_armies[army] and (source_id, army) in memberships
                ]
                if len(matches) == 1:
                    unit["armyHistory"][matches[0]].append(row)
                    counts["armyEntries"] += 1
                else:
                    unit["unmatchedHistory"][army].append(row)
                    counts["unmatchedEntries"] += 1
    return dict(counts)


def category(row: Document) -> str:
    kind, identity = row["kind"], row["identity"]
    if kind == "characteristic":
        return "Characteristics"
    if kind == "classification":
        return "Classification"
    if kind == "lifecycleSummaries":
        return "Loadout lifecycle"
    if kind == "availabilitySummaries":
        return "Availability"
    if kind == "relationshipSummaries":
        return "Relationships"
    return {"points": "Costs", "swc": "Costs", "skills": "Skills",
            "equip": "Equipment", "weapons": "Weapons"}.get(identity["field"], "Other changes")


CATEGORY_ORDER = ("Characteristics", "Skills", "Equipment", "Weapons", "Costs",
                  "Availability", "Loadout lifecycle", "Relationships", "Classification",
                  "Other changes")


def action_text(row: Document) -> tuple[str, str]:
    text = row["text"]
    for action in ("Changed", "Gained", "Lost", "Added", "Removed", "Appeared", "Disappeared"):
        if text.startswith(action + " "):
            return action, text[len(action) + 1:]
    if row["kind"] == "classification":
        return "Classification", text.removesuffix(" (classification)")
    return "Changed", text


def action_rows(row: Document) -> list[tuple[str, str]]:
    """Split structured reference deltas without parsing player-facing strings."""
    identity = row["identity"]
    if row["kind"] != "summaries" or identity["field"] not in {"skills", "equip", "weapons"}:
        return [action_text(row)]
    lost, gained = identity["lost"], identity["gained"]
    ids = {ref["filter"]["id"] for ref in lost} & {ref["filter"]["id"] for ref in gained}
    result = []
    for item_id in sorted(ids):
        a = ", ".join(compact_reference(ref) for ref in lost if ref["filter"]["id"] == item_id)
        b = ", ".join(compact_reference(ref) for ref in gained if ref["filter"]["id"] == item_id)
        result.append(("Changed", f"{a} → {b}"))
    for action, references in (("Gained", gained), ("Lost", lost)):
        remaining = [compact_reference(ref) for ref in references if ref["filter"]["id"] not in ids]
        if remaining:
            result.append((action, ", ".join(remaining)))
    return result or [action_text(row)]


def history_projection(units: list[Document], names: dict[int, str], sha: str) -> Document:
    """Export compact player-facing changes, not the private research evidence."""
    def changes(rows: list[Document], *, general: bool = False) -> list[Document]:
        return [{
            "date": row["laterObservedDate"],
            "scope": "" if general else row["scope"].removesuffix(" · Own capabilities only"),
            "category": category(row),
            "actions": [{"action": action, "text": body} for action, body in action_rows(row)],
        } for row in rows]

    result = {}
    for unit in units:
        armies = unit["currentArmies"]
        keys = [army_history_key(army) for army in armies]
        require(len(keys) == len(set(keys)), "Ambiguous current Army history card")
        result[str(unit["logicalUnitId"])] = {
            "general": {
                profile["profile_identity"]: changes(
                    unit["generalHistory"].get(profile["profile_identity"], []), general=True,
                )
                for profile in unit["currentGeneral"]
            },
            "armies": {
                key: changes(unit["armyHistory"].get(index, []))
                for index, key in enumerate(keys)
            },
            "unmatched": [
                {"name": names.get(army, f"Army #{army}"), "changes": changes(rows)}
                for army, rows in sorted(unit["unmatchedHistory"].items())
            ],
        }
    return {"formatVersion": 1, "armyDatabaseSha256": sha, "units": result}


def context_history(rows: list[Document], names: dict[int, str], *, general: bool = False) -> str:
    if not rows:
        note = (
            "No changes to this General profile, shared across its Army profiles and loadouts, "
            "have been confirmed in the available history. Individual changes belong to the "
            "respective Army histories."
            if general else "No supported changes found in the available history for this Army."
        )
        return ('<details class="history"><summary>History</summary>'
                f'<p class="notice">{note}</p></details>')
    dates: dict[str, list[Document]] = defaultdict(list)
    for row in rows:
        dates[row["laterObservedDate"]].append(row)
    articles = []
    for date in sorted(dates, reverse=True):
        scopes: dict[str, list[Document]] = defaultdict(list)
        for row in dates[date]:
            # Direct-owner scope qualifies the evidence, not the visible loadout heading.
            scope = row["scope"].removesuffix(" · Own capabilities only")
            scopes["" if general else scope].append(row)
        groups = []
        for scope, changes in scopes.items():
            categories: dict[str, list[Document]] = defaultdict(list)
            for row in changes:
                categories[category(row)].append(row)
            blocks = []
            for label in CATEGORY_ORDER:
                if label not in categories:
                    continue
                items = []
                for row in categories[label]:
                    lines = "".join(
                        f'<div class="change-line action-{esc(action.lower())}">'
                        f'<span class="action">{esc(action)}</span>{esc(body)}</div>'
                        for action, body in action_rows(row)
                    )
                    armies = ", ".join(names.get(i, f"Army #{i}") for i in row["armyIds"])
                    windows = row["evidence"].get("generalAttribution", {}).get(
                        "comparisonWindows", [],
                    ) if isinstance(row["evidence"], dict) else []
                    window_text = (
                        "<p>Comparison windows: " + "; ".join(
                            f"{esc(names.get(w['armyId'], str(w['armyId'])))}: "
                            f"{esc(w['earlier'])} – {esc(w['later'])}" for w in windows
                        ) + "</p>" if windows else
                        f"<p>Observation window: {esc(row['earlierObservedDate'])} – "
                        f"{esc(row['laterObservedDate'])}</p>"
                    )
                    evidence = (
                        f"<p>{esc(armies)}</p>" + window_text
                        + ("<p>Scope: Own capabilities only (excluding attached entities).</p>"
                           if row["scope"].endswith(" · Own capabilities only") else "")
                        + f"<pre>{raw(row['evidence'])}</pre>"
                    )
                    review = details("Evidence", evidence)
                    items.append(
                        f'<li class="{esc(label.lower().replace(" ", "-"))}">'
                        f'{lines}<div class="technical-only">{review}</div></li>'
                    )
                blocks.append(f'<h5 class="history-category">{esc(label)}</h5>'
                              f'<ul class="history-list">{"".join(items)}</ul>')
            heading = f'<h4 class="scope">{esc(scope)}</h4>' if scope else ""
            groups.append(f'<div class="change-group">{heading}{"".join(blocks)}</div>')
        articles.append(f'<article><h3><time datetime="{esc(date)}">{esc(date)}</time></h3>'
                        f'{"".join(groups)}</article>')
    return ('<details class="history"><summary>History</summary>'
            + "".join(articles) + "</details>")


def statline(stats: Document) -> str:
    movement = scalar_text("move", {"present": True, "value": [
        stats.get("move_1"), stats.get("move_2"),
    ]})
    values = [("MOV", movement), *[
        (label, stats.get(key)) for label, key in (
            ("CC", "cc"), ("BS", "bs"), ("PH", "ph"), ("WIP", "wip"),
            ("ARM", "arm"), ("BTS", "bts"), ("STR" if stats.get("is_structure") else "VITA",
                                           "vitality"), ("S", "silhouette"),
        )
    ]]
    return '<div class="statline">' + "".join(
        f"<span><small>{label}</small>{esc('—' if value is None or value == -1 else value)}</span>"
        for label, value in values
    ) + "</div>"


def current_item_text(items: list[Document]) -> str:
    result = []
    for item in items:
        label = str(item.get("name") or "Unnamed item")
        if item.get("quantity") not in (None, 1):
            label = f"{item['quantity']} × {label}"
        extras = [str(extra.get("name") or "?") for extra in item.get("extras", [])]
        if extras:
            label += " (" + ", ".join(extras) + ")"
        result.append(label)
    return ", ".join(result)


def contextual_sections(unit: Document, names: dict[int, str]) -> str:
    profiles = []
    for profile in unit["currentGeneral"]:
        items = "".join(
            f'<p class="current-items"><strong>{label}:</strong> '
            f'{esc(current_item_text(values))}</p>'
            for key, label in (
                ("skills", "Skills"), ("equipment", "Equipment"), ("weapons", "Weapons"),
            )
            if (values := profile["shared_items"].get(key, []))
        )
        history = context_history(unit["generalHistory"].get(profile["profile_identity"], []),
                                  names, general=True)
        profiles.append(f'<section class="profile-card"><h3>{esc(profile["display_name"])}</h3>'
                        f'{statline(profile["stats"])}{items}{history}</section>')
    armies = []
    for index, army in enumerate(unit["currentArmies"]):
        current = "".join(
            f'<h4>{esc(profile.get("display_name") or profile["name"])}</h4>{statline(profile)}'
            for profile in army["profiles"]
        )
        loadouts = []
        for option in army["loadouts"]:
            label = option["name"]
            items = "; ".join(
                current_item_text(option[field]) for field in ("weapons", "skills", "equipment")
                if option.get(field)
            )
            if items:
                label += " — " + items
            loadouts.append(
                f'<li>{esc(label)} <strong>· {esc(option["points"])} Points, '
                f'{esc(option["swc"])} SWC</strong></li>'
            )
        if loadouts:
            current += f'<h4>Loadouts</h4><ul class="current-loadouts">{"".join(loadouts)}</ul>'
        history = context_history(unit["armyHistory"].get(index, []), names)
        flags = ", ".join(army.get("availability_flags", []))
        label = army["name"] + (f" ({flags})" if flags else "")
        armies.append(f'<details class="army-card"{" open" if index == 0 else ""}>'
                      f'<summary>{esc(label)}</summary>{current}{history}</details>')
    unmatched = "".join(
        f'<section class="profile-card"><h3>{esc(names.get(army, f"Army #{army}"))}</h3>'
        f'{context_history(rows, names)}</section>'
        for army, rows in sorted(unit["unmatchedHistory"].items())
    )
    if unmatched:
        unmatched = ('<details class="army-card"><summary>Other historical contexts</summary>'
                     + unmatched + "</details>")
    return ('<h3>General profiles</h3>' + "".join(profiles)
            + '<h3>Army profiles</h3>' + "".join(armies) + unmatched)


def render(units: list[Document], names: dict[int, str], coverage: Document,
           *, contextual: bool = False) -> str:
    options, sections = [], []
    for unit in units:
        title = (unit["name"] or "Unnamed Unit").strip()
        slug = unit["slug"] or str(unit["logicalUnitId"])
        anchor = f"unit-{unit['logicalUnitId']}"
        options.append(
            f'<option value="{esc(anchor)}" data-search="{esc((title + " " + slug).lower())}" '
            f'data-history="{"yes" if unit["entries"] else "no"}">'
            f"{esc(title)}</option>"
        )
        if contextual:
            evidence = {k: unit[k] for k in (
                "reviewEvidence", "catalogEvidence", "sourceIdentities", "semanticReview",
            )}
            review = details(
                "Additional review and catalog evidence", f"<pre>{raw(evidence)}</pre>",
            )
            sections.append(
                f'<section class="unit" id="{esc(anchor)}" hidden><h2>{esc(title)}</h2>'
                + contextual_sections(unit, names)
                + f'<div class="technical-only">{review}</div></section>'
            )
            continue
        dates: dict[str, list[Document]] = defaultdict(list)
        for row in unit["entries"]:
            dates[row["laterObservedDate"]].append(row)
        articles = []
        for observed in sorted(dates, reverse=True):
            rows = presentation_rows(dates[observed])
            army_groups: dict[tuple[int, ...], list[Document]] = defaultdict(list)
            for row in rows:
                army_groups[tuple(row["armyIds"])].append(row)
            blocks = []
            for ids, entries in army_groups.items():
                armies = ", ".join(names.get(i, f"Army #{i}") for i in ids)
                scopes: dict[str, list[Document]] = defaultdict(list)
                for row in entries:
                    scopes[row["scope"]].append(row)
                groups = []
                for scope, changes in scopes.items():
                    # Only share headings, not event identities or evidence.
                    for separator in (" · ", " / "):
                        prefix = title + separator
                        if scope.casefold().startswith(prefix.casefold()):
                            scope = scope[len(prefix):]
                            break
                    heading = f'<h4 class="scope">{esc(scope)}</h4>' if scope else ""
                    items = []
                    for row in changes:
                        observations = []
                        for source in row["observations"]:
                            window = (
                                f"{source['earlierObservedDate']} – {source['laterObservedDate']}"
                            )
                            source_armies = ", ".join(
                                names.get(i, f"Army #{i}") for i in source["armyIds"]
                            )
                            observations.append(
                                f"<p>{esc(source_armies)}</p>"
                                f"<p>Observation window: {esc(window)}</p>"
                                f"<pre>{raw(source['evidence'])}</pre>"
                            )
                        review = details("Evidence", "".join(observations))
                        items.append(
                            f"<li><strong>{esc(row['text'])}</strong>"
                            f'<div class="technical-only">{review}</div></li>'
                        )
                    groups.append(
                        f'<div class="change-group">{heading}<ul>{"".join(items)}</ul></div>'
                    )
                blocks.append(
                    f'<div class="army-group"><p class="armies">{esc(armies)}</p>'
                    + "".join(groups) + "</div>"
                )
            articles.append(
                f'<article><h3><time datetime="{esc(observed)}">{esc(observed)}</time></h3>'
                f"{''.join(blocks)}</article>"
            )
        evidence = {k: unit[k] for k in (
            "reviewEvidence", "catalogEvidence", "sourceIdentities", "semanticReview",
        )}
        review = details("Additional review and catalog evidence", f"<pre>{raw(evidence)}</pre>")
        sections.append(
            f'<section class="unit" id="{esc(anchor)}" hidden><h2>{esc(title)}</h2>'
            + ("".join(articles) or "<p>No supported changes found in the available history.</p>")
            + f'<div class="technical-only">{review}</div></section>'
        )
    coverage_details = details("Coverage and provenance", f"<pre>{raw(coverage)}</pre>")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Unit version history — private preview</title>'
        f"<style>{STYLE + (CONTEXT_STYLE if contextual else '')}</style></head>"
        "<body><header><h1>"
        + ("Unit details · History preview" if contextual else "Unit version history")
        + "</h1>"
        '<p class="notice">Private N5 preview · '
        "Dates come from the later Army JSON revision identifiers. "
        "History is incomplete; dates are not independently confirmed publication dates. "
        "Army list presence does not establish playable availability. "
        "Army names use current labels. MOV is displayed in inches. "
        + ("Current cards show all optional Unit categories. General history is a conservative "
           "shared-revision attribution pilot for characteristics and shared items; "
           "other changes remain in their observed Army contexts. "
           "Capability changes describe the listed profiles and loadouts, not attached entities. "
           if contextual else "")
        + "</p>"
        '<label><input type="checkbox" id="technical"> Show technical evidence</label>'
        f'<div class="technical-only">{coverage_details}</div>'
        '</header><div class="layout"><nav aria-label="Unit navigation">'
        '<label for="search">Find a Unit</label>'
        '<input id="search" type="search" placeholder="Unit name or slug">'
        '<label><input type="checkbox" id="with-history" checked> Only Units with changes</label>'
        '<label for="unit-select">Unit</label><select id="unit-select" size="6">'
        + "".join(options) + '</select><p id="shown" aria-live="polite"></p></nav>'
        '<main><p id="empty" hidden>No matching Units.</p>'
        + "".join(sections) + f"</main></div><script>{SCRIPT}</script></body></html>"
    )


def browser_review(output: Path, units: list[Document], selected: list[int],
                   *, contextual: bool = False) -> None:
    """Exercise the exact private HTML locally, including responsive navigation."""
    playwright = importlib.import_module("playwright.sync_api")
    available = {u["logicalUnitId"]: u for u in units if u["entries"]}
    selected = selected or [next(iter(available))]
    require(all(i in available for i in selected), "Select Units with history for browser review")
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            for width, height, theme in ((1280, 900, "light"), (390, 844, "dark")):
                page = browser.new_page(
                    viewport={"width": width, "height": height}, color_scheme=theme,
                )
                errors: list[str] = []
                requests: list[str] = []
                page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                page.on("request", lambda request, requests=requests: requests.append(request.url))
                page.goto(output.resolve().as_uri())
                require(page.locator(".unit:visible").count() == 1, "Initial selection differs")
                page.locator("#search").fill("no-matching-unit-xyz")
                require(page.locator("#empty").is_visible(), "Missing empty-search state")
                page.locator("#search").fill("")
                page.locator("#with-history").uncheck()
                require(page.locator("#unit-select option").count() == len(units),
                        "All-Unit navigation differs")
                page.locator("#with-history").check()
                for identity in selected:
                    unit = available[identity]
                    page.locator("#search").fill(unit["slug"] or unit["name"])
                    page.locator("#unit-select").select_option(f"unit-{identity}")
                    target = page.locator(f"#unit-{identity}")
                    require(target.is_visible(), "Selected Unit is hidden")
                    require(page.locator(".unit:visible").count() == 1, "Unit selection differs")
                    require(target.locator("article").count() > 0, "Missing selected timeline")
                    if contextual:
                        require(target.locator("details.history[open]").count() == 0,
                                "History must be collapsed by default")
                        page.evaluate("window.scrollTo(0, 0)")
                        closed = output.with_name(
                            f"{output.stem}-{identity}-{width}-{theme}-closed.png"
                        )
                        require(not closed.exists(), "Screenshot already exists")
                        page.screenshot(path=closed)
                        disclosure = target.locator("details.history:has(article)").first
                        disclosure.evaluate("""element => {
                            for (let parent = element.parentElement; parent;
                                 parent = parent.parentElement)
                                if (parent.tagName === 'DETAILS') parent.open = true;
                        }""")
                        disclosure.locator(":scope > summary").click()
                        require(disclosure.locator("article").first.is_visible(),
                                "History disclosure did not open")
                    technical = target.locator(".technical-only:visible")
                    require(technical.count() == 0,
                            "Technical evidence visible by default")
                    page.locator("#technical").check()
                    require(technical.count() > 0, "Technical evidence toggle differs")
                    technical.first.locator("summary").first.click()
                    require(technical.first.locator("details[open] pre").first.is_visible(),
                            "Evidence disclosure did not open")
                    page.locator("#technical").uncheck()
                    if contextual:
                        target.locator("details.history[open]>summary").first.evaluate(
                            "element => element.scrollIntoView({block: 'start'})"
                        )
                    else:
                        page.evaluate("window.scrollTo(0, 0)")
                    require(page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
                            "Preview overflows viewport")
                    screenshot = output.with_name(f"{output.stem}-{identity}-{width}-{theme}.png")
                    require(not screenshot.exists(), "Screenshot already exists")
                    page.screenshot(path=screenshot)
                require(not errors, f"Browser errors: {errors}")
                require(not any(url.startswith(("http:", "https:")) for url in requests),
                        "Unexpected network requests")
                page.close()
                print(f"Browser review: {width}px {theme}, {len(selected)} Units: PASS")
        finally:
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("preview", "semantic", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    for arg in ("preview", "semantic"):
        parser.add_argument("--" + arg + "-sha256", required=True)
    parser.add_argument("--inspect-unit", type=int, action="append", default=[])
    parser.add_argument("--inspect-name", action="append", default=[],
                        help="Select a uniquely matching Unit name for review.")
    parser.add_argument("--inspect-general", action="store_true",
                        help="Include one Unit with confirmed General-profile history.")
    parser.add_argument("--inspect-multi-profile", action="store_true",
                        help="Include Units with promoted multi-profile Group changes.")
    parser.add_argument("--web-projection", type=Path,
                        help="Export snapshot-bound contextual player history JSON.")
    parser.add_argument("--contextual", action="store_true",
                        help="Render current profile cards with scoped historical disclosures.")
    parser.add_argument("--browser-review", action="store_true",
                        help="Check the generated HTML in Chromium and save private screenshots.")
    args = parser.parse_args()
    private = (ROOT / "generated").resolve()
    for path in (args.preview, args.semantic, args.output):
        require(path.resolve().is_relative_to(private), "Use private history directory")
    require(not args.output.exists(), "Preview output already exists")
    if args.web_projection:
        require(args.contextual, "Web projection requires contextual mode")
        require(
            args.web_projection.resolve().is_relative_to(private), "Use private history directory",
        )
        require(not args.web_projection.exists(), "Web projection already exists")
    preview_bytes, semantic_bytes = args.preview.read_bytes(), args.semantic.read_bytes()
    require(digest(preview_bytes) == args.preview_sha256, "Preview SHA-256 differs")
    require(digest(semantic_bytes) == args.semantic_sha256, "Semantic SHA-256 differs")
    preview, semantic = json.loads(preview_bytes), json.loads(semantic_bytes)
    require(preview["publicationStatus"] == "privatePreviewOnly"
            and preview["formatVersion"] == 1 and semantic["formatVersion"] == 7
            and semantic["publicationStatus"] == "privateResearchOnly"
            and preview["edition"] == semantic["edition"] == "n5", "Unexpected history format")
    require(semantic["previewSha256"] == args.preview_sha256, "Semantic preview differs")
    for key in ("archiveSha256", "armyDatabaseSha256", "historyDatabaseSha256"):
        require(preview[key] == semantic[key], f"Linked {key} differs")
    require(preview["archiveSha256"] == ARCHIVE_PIN, "Archive pin differs")
    require(file_digest(ARMY) == preview["armyDatabaseSha256"], "Army database differs")
    require(file_digest(HISTORY) == preview["historyDatabaseSha256"], "History database differs")
    with closing(read_only(ARMY)) as db:
        names = dict(db.execute("SELECT id,name FROM army_lists WHERE name IS NOT NULL"))
    with closing(read_only(HISTORY)) as db:
        units, counts = model(preview, semantic, historical_scopes(
            db, ROOT / "archive/army-history-v1.zip",
        ))
        if args.contextual:
            counts.update(contextual_model(units, db, ROOT / "archive/army-history-v1.zip"))
    for query in args.inspect_name:
        matches = [u["logicalUnitId"] for u in units
                   if query.casefold() in u["name"].casefold() and u["entries"]]
        require(len(matches) == 1, f"Inspect name must match one Unit with history: {query}")
        args.inspect_unit.extend(matches)
    if args.inspect_general:
        require(args.contextual, "General history review requires contextual mode")
        candidates = [u["logicalUnitId"] for u in units if u["generalHistory"]]
        require(bool(candidates), "No confirmed General-profile history for review")
        args.inspect_unit = list(dict.fromkeys([*args.inspect_unit, candidates[0]]))
    if args.inspect_multi_profile:
        require(args.contextual, "Multi-profile review requires contextual mode")
        for unit in units:
            for target, rows in unit["generalHistory"].items():
                changes = [row for row in rows if row["evidence"].get("generalAttribution", {}).get(
                    "sourceProfileId",
                ) is not None]
                if changes:
                    args.inspect_unit.append(unit["logicalUnitId"])
                    print(json.dumps({
                        "unit": unit["name"], "profileIdentity": target,
                        "multiProfileChanges": [row["text"] for row in changes],
                    }, ensure_ascii=True))
        args.inspect_unit = list(dict.fromkeys(args.inspect_unit))
    coverage = {
        "previewSha256": args.preview_sha256, "semanticSha256": args.semantic_sha256,
        **{k: preview[k] for k in ("archiveSha256", "armyDatabaseSha256",
                                   "historyDatabaseSha256", "coverage", "unresolvedIdentities",
                                   "ambiguousArmyWindows")},
        "semanticCounts": semantic["counts"], "presentationCounts": counts,
        "reviewInputs": [args.preview.name, args.semantic.name],
    }
    html = render(units, names, coverage, contextual=args.contextual)
    require(file_digest(ARMY) == preview["armyDatabaseSha256"], "Army database changed")
    require(file_digest(HISTORY) == preview["historyDatabaseSha256"], "History database changed")
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(html)
    if args.web_projection:
        projection = history_projection(units, names, preview["armyDatabaseSha256"])
        with args.web_projection.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(encode(projection))
        print(f"Web history projection: {args.web_projection}")
    print(json.dumps(counts, indent=2, sort_keys=True))
    for unit in units:
        if unit["logicalUnitId"] in args.inspect_unit:
            # JSON escapes non-ASCII diagnostics for Windows console encodings.
            print(json.dumps({
                "unit": unit["name"],
                "entries": [
                    {**{k: row[k] for k in ("earlierObservedDate", "laterObservedDate",
                                             "scope", "text")},
                     "armies": [names.get(i, str(i)) for i in row["armyIds"]]}
                    for row in unit["entries"]
                ],
            }, ensure_ascii=True))
    print(f"Private player-facing preview: {args.output}")
    if args.browser_review:
        browser_review(args.output, units, args.inspect_unit, contextual=args.contextual)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
