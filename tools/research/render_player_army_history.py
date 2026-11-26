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
from infinity_db.maintained_text import DISTANCE_CENTIMETERS_PER_INCH
from tools.research.build_army_history_database import ARCHIVE_PIN, encode
from tools.research.project_army_history import ARMY, HISTORY, ROOT, read_only
from tools.research.render_army_history import FIELDS, details, esc, raw, value_text
from tools.research.summarize_army_history import compact_reference, get_group, indexed

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


def render(units: list[Document], names: dict[int, str], coverage: Document) -> str:
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
        f"<style>{STYLE}</style></head><body><header><h1>Unit version history</h1>"
        '<p class="notice">Private N5 preview · '
        "Dates indicate when each change was first observed. "
        "History is incomplete; dates are not confirmed publication dates. "
        "Army list presence does not establish playable availability. "
        "Army names use current labels. MOV is displayed in inches.</p>"
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


def browser_review(output: Path, units: list[Document], selected: list[int]) -> None:
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
                    require(not target.locator(".technical-only").first.is_visible(),
                            "Technical evidence visible by default")
                    page.locator("#technical").check()
                    require(target.locator(".technical-only").first.is_visible(),
                            "Technical evidence toggle differs")
                    target.locator(".technical-only summary").first.click()
                    require(target.locator("details[open] pre").first.is_visible(),
                            "Evidence disclosure did not open")
                    page.locator("#technical").uncheck()
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
    parser.add_argument("--browser-review", action="store_true",
                        help="Check the generated HTML in Chromium and save private screenshots.")
    args = parser.parse_args()
    private = (ROOT / "generated").resolve()
    for path in (args.preview, args.semantic, args.output):
        require(path.resolve().is_relative_to(private), "Use private history directory")
    require(not args.output.exists(), "Preview output already exists")
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
    coverage = {
        "previewSha256": args.preview_sha256, "semanticSha256": args.semantic_sha256,
        **{k: preview[k] for k in ("archiveSha256", "armyDatabaseSha256",
                                   "historyDatabaseSha256", "coverage", "unresolvedIdentities",
                                   "ambiguousArmyWindows")},
        "semanticCounts": semantic["counts"], "presentationCounts": counts,
        "reviewInputs": [args.preview.name, args.semantic.name],
    }
    html = render(units, names, coverage)
    require(file_digest(ARMY) == preview["armyDatabaseSha256"], "Army database changed")
    require(file_digest(HISTORY) == preview["historyDatabaseSha256"], "History database changed")
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(html)
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
        browser_review(args.output, units, args.inspect_unit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
