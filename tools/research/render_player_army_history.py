"""Render an offline, private player-facing N5 Unit history preview."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Callable
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from infinity_db.army_history_pilot import catalog_index
from infinity_db.army_history_source import Document, digest, file_digest, read_history, require
from tools.research.build_army_history_database import ARCHIVE_PIN, encode
from tools.research.project_army_history import ARMY, HISTORY, ROOT, read_only
from tools.research.render_army_history import FIELDS, details, esc, raw, value_text
from tools.research.summarize_army_history import describe_option, get_group, indexed

SCALARS = frozenset({"arm", "bs", "bts", "cc", "move", "ph", "s", "str", "w", "wip"})
STREAMS = ("summaries", "lifecycleSummaries", "availabilitySummaries", "relationshipSummaries")
ScopeResolver = Callable[[Document, Document, str], str]

STYLE = """
* {box-sizing:border-box}
:root {color-scheme:light dark}
body {max-width:960px;margin:0 auto;padding:24px 18px;font:16px/1.5 system-ui}
h1,h2,h3 {line-height:1.2;margin:0 0 .6em}
p {margin:.5em 0}
header {border-bottom:1px solid GrayText;padding-bottom:1em}
input,select {font:inherit;padding:.5em;max-width:100%;width:100%}
input[type=checkbox] {width:auto}
label {display:block;margin-top:.8em}
nav {margin:1em 0;display:grid;gap:.4em}
article {margin:1.3em 0;padding-top:1em;border-top:1px solid GrayText}
h3 {font-size:1rem}
.armies {font-size:.85em;color:GrayText;margin-top:.7em}
ul {padding-left:1.4em;margin:.4em 0 1em}
li {margin:.4em 0}
.scope {font-size:.9em;color:GrayText}
details {margin:.3em 0;font-size:.9em}
summary {cursor:pointer}
pre {white-space:pre-wrap;overflow-wrap:anywhere}
[hidden] {display:none!important}
body:not(.technical) .technical-only {display:none}
:focus-visible {outline:2px solid Highlight;outline-offset:3px}
"""
SCRIPT = """
const search = document.querySelector('#search');
const select = document.querySelector('#unit-select');
const options = [...select.options];
const only = document.querySelector('#with-history');
const units = [...document.querySelectorAll('.unit')];
function show() {
  for (const unit of units) unit.hidden = unit.id !== select.value;
}
function filter() {
  const query = search.value.trim().toLowerCase();
  const prior = select.value;
  const matches = options.filter(o => o.dataset.search.includes(query) &&
    (!only.checked || o.dataset.history === 'yes'));
  select.replaceChildren(...matches);
  if (matches.some(o => o.value === prior)) select.value = prior;
  document.querySelector('#shown').textContent = matches.length + ' Units found';
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
            return value_text(field, record) + " cm"
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
        return f"{row['summary']} ({row['points']} Points, {row['swc']} SWC)"
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
        if stream == "summaries":
            profiles = indexed(group.get("profiles")) or {}
            if len(profiles) == 1:
                profile = name(next(iter(profiles.values())), "Unnamed profile")
                if profile.casefold() != group_name.casefold():
                    group_name += " / " + profile
            return effective_scope(row, group_name)
        if stream == "lifecycleSummaries":
            profile = str(row["profileName"] or "Unnamed profile").strip()
            return group_name if profile.casefold() == group_name.casefold() else (
                group_name + " / " + profile
            )
        owner = path[4]
        if owner == "options":
            options = indexed(group.get("options")) or {}
            require(path[5] in options, "Historical loadout no longer resolves")
            label = describe_option(
                options[path[5]], army, [metadata(sha) for sha in endpoint["metadataSha256"]],
            )
            return group_name + " · " + label + " (loadout)"
        require(owner == "profiles", "Unsupported historical owner")
        profiles = indexed(group.get("profiles")) or {}
        require(path[5] in profiles, "Historical profile no longer resolves")
        return labels_scope([unit, group, profiles[path[5]]], "profile")

    return resolve


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
        for row in unit["entries"]:
            identity = row["identity"]
            if row["kind"] == "summaries" and identity["allGroupLoadouts"]:
                # Equivalent group-wide changes need not have identical loadout
                # definitions in every Army. The full scope, effect and display
                # (including any exact cost pair) must still match.
                identity = {k: v for k, v in identity.items() if k != "loadouts"}
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
        windows: dict[tuple[str, str], list[Document]] = defaultdict(list)
        for row in unit["entries"]:
            windows[(row["earlierObservedDate"], row["laterObservedDate"])].append(row)
        articles = []
        for (earlier, later), rows in windows.items():
            army_groups: dict[tuple[int, ...], list[Document]] = defaultdict(list)
            for row in rows:
                army_groups[tuple(row["armyIds"])].append(row)
            blocks = []
            for ids, entries in army_groups.items():
                armies = ", ".join(names.get(i, f"Army #{i}") for i in ids)
                items = []
                for row in entries:
                    scope = (f'<span class="scope">{esc(row["scope"])}</span> · '
                             if row["scope"] else "")
                    review = details("Evidence", f"<pre>{raw(row['evidence'])}</pre>")
                    items.append(
                        f"<li>{scope}<strong>{esc(row['text'])}</strong>"
                        f'<div class="technical-only">{review}</div></li>'
                    )
                blocks.append(
                    f'<p class="armies">{esc(armies)}</p><ul>{"".join(items)}</ul>'
                )
            articles.append(
                f"<article><h3>{esc(earlier)} – {esc(later)}</h3>{''.join(blocks)}</article>"
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
        "<p>Private N5 preview · Changes observed between the listed dates. "
        "History is incomplete; dates are not confirmed publication dates. "
        "Army list presence does not establish playable availability. "
        "Army names use current labels.</p>"
        '<label><input type="checkbox" id="technical"> Show technical evidence</label>'
        f'<div class="technical-only">{coverage_details}</div>'
        '</header><nav aria-label="Unit navigation"><label for="search">Find a Unit</label>'
        '<input id="search" type="search" placeholder="Unit name or slug">'
        '<label><input type="checkbox" id="with-history" checked> Only Units with changes</label>'
        '<label for="unit-select">Unit</label><select id="unit-select" size="6">'
        + "".join(options) + '</select><p id="shown" aria-live="polite"></p></nav>'
        '<main>' + "".join(sections) + f"</main><script>{SCRIPT}</script></body></html>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("preview", "semantic", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    for arg in ("preview", "semantic"):
        parser.add_argument("--" + arg + "-sha256", required=True)
    parser.add_argument("--inspect-unit", type=int, action="append", default=[])
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
