"""Render a private, offline, human-readable Unit history review."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from contextlib import closing
from html import escape
from pathlib import Path
from typing import Any

from infinity_db.army_history_source import Document, digest, file_digest, require
from tools.research.build_army_history_database import ARCHIVE_PIN, encode
from tools.research.project_army_history import ARMY, HISTORY, ROOT, read_only

FIELDS = {
    "arm": "ARM", "bs": "BS", "bts": "BTS", "cc": "CC", "move": "MOV",
    "ph": "PH", "s": "S", "str": "STR", "w": "W", "wip": "WIP",
    "points": "Points", "swc": "SWC", "skills": "Skills",
    "equip": "Equipment", "weapons": "Weapons", "ava": "AVA", "disabled": "Disabled",
}
REFERENCES = frozenset({"skills", "equip", "weapons"})
STYLE = """
* {box-sizing:border-box}
body {max-width:1100px;margin:24px auto;padding:0 18px;font:16px/1.5 system-ui;
 color:#e6e9ed;background:#18202a}
h1,h2,h3 {line-height:1.25}
a {color:#a8d1ff}
small,.muted {color:#b8c5d3}
input {font:inherit;padding:8px;width:min(100%,440px);border-radius:5px}
label {display:inline-block;margin:8px 0}
details {margin:8px 0;padding:8px 12px;background:#222e3b;border-radius:6px}
summary {cursor:pointer}
article {border-top:1px solid #4d5b6b;padding:8px 0}
ul {margin:6px 0;padding-left:24px}
.before {color:#f6b1b1}.after {color:#a6e5c1}
pre {white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}
[hidden] {display:none!important}
"""
SCRIPT = """
const search = document.querySelector('#search');
const only = document.querySelector('#with-history');
const units = [...document.querySelectorAll('.unit')];
function filter() {
  const query = search.value.trim().toLowerCase();
  let shown = 0;
  for (const unit of units) {
    unit.hidden = !unit.dataset.search.includes(query) ||
      (only.checked && unit.dataset.timeline !== 'yes');
    if (!unit.hidden) shown++;
  }
  document.querySelector('#shown').textContent = shown + ' Units shown';
}
search.addEventListener('input', filter);
only.addEventListener('change', filter);
filter();
"""


def esc(value: Any) -> str:
    return escape(str(value), quote=True)


def raw(value: Any) -> str:
    return esc(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def value_text(field: str, recorded: Document) -> str:
    if not recorded["present"]:
        return "Not present in source"
    value = recorded["value"]
    if value is None:
        return "Null (source value)"
    if type(value) is bool:
        return "Yes" if value else "No"
    if field == "move" and isinstance(value, list) and all(type(v) is int for v in value):
        return "-".join(str(v) for v in value)
    if isinstance(value, (dict, list)):
        return encode(value)
    return str(value)


def reference_text(row: Document) -> str:
    definition = row["filter"]
    occurrence = row["occurrence"]
    name = definition["name"]
    extras = occurrence.get("extra")
    modifiers = [
        str(item.get("name") or f"Extra #{item.get('id')}")
        for item in extras or []
    ]
    if modifiers:
        name += " (" + ", ".join(modifiers) + ")"
    # Preserve unfamiliar source modifiers rather than guess their meaning.
    remaining = {k: v for k, v in occurrence.items() if k != "extra"}
    if remaining:
        name += " · " + encode(remaining)
    name += f" [source #{definition['id']}]"
    if row["metadataFingerprints"] is None:
        name += " (filter-only evidence)"
    return name


def reference_changes(before: list[Document], after: list[Document]) -> list[Document]:
    """Diff exact multisets, without pairing different IDs or changed definitions."""
    a, b = Counter(map(encode, before)), Counter(map(encode, after))
    removed = [json.loads(item) for item in sorted((a - b).elements())]
    added = [json.loads(item) for item in sorted((b - a).elements())]
    ids = sorted({r["filter"]["id"] for r in removed + added})
    result = []
    for identity in ids:
        left = [r for r in removed if r["filter"]["id"] == identity]
        right = [r for r in added if r["filter"]["id"] == identity]
        same_occurrences = Counter(encode(r["occurrence"]) for r in left) == Counter(
            encode(r["occurrence"]) for r in right
        )
        kind = ("definitionChanged" if same_occurrences else "changed") if left and right else (
            "removed" if left else "added"
        )
        result.append({
            "kind": kind,
            "before": left, "after": right,
        })
    return result


def historical_target(group: Document) -> str:
    labels = []
    for context in group["historicalLabels"]:
        parts = []
        for item in context:
            label = item.get("name") or item.get("isc") or item.get("slug")
            # Source keys remain visible even where names repeat.
            parts.append(f"{label or 'Record'} [#{item['id']}]")
        labels.append(" / ".join(parts))
    return " | ".join(dict.fromkeys(labels))


def ref_label(ref: Document) -> str:
    return f"{ref['stream']}:{ref['position']} (source Unit #{ref['sourceUnitId']})"


def details(label: str, body: str) -> str:
    return f"<details><summary>{esc(label)}</summary>{body}</details>"


def render_change(change: Document) -> tuple[str, Counter[str]]:
    field = change["field"]
    require(field in FIELDS, f"Unsupported composition field: {field}")
    label = esc(FIELDS[field])
    before, after = change["before"], change["after"]
    counts: Counter[str] = Counter()
    if field in REFERENCES:
        require(before["present"] and after["present"], "Missing reference side")
        changes = reference_changes(before["value"], after["value"])
        require(bool(changes), "Empty reference change")
        parts = []
        for item in changes:
            kind = item["kind"]
            counts[f"{field}:{kind}"] += 1
            a = "; ".join(reference_text(row) for row in item["before"])
            b = "; ".join(reference_text(row) for row in item["after"])
            if kind in {"changed", "definitionChanged"}:
                description = ("Definition/context changed; same occurrences: "
                               if kind == "definitionChanged" else "Changed source occurrence: ")
                text = (
                    description +
                    f'<span class="before">{esc(a)}</span> → '
                    f'<span class="after">{esc(b)}</span>'
                )
            elif kind == "added":
                text = f'Added occurrence: <span class="after">{esc(b)}</span>'
            else:
                text = f'Removed occurrence: <span class="before">{esc(a)}</span>'
            parts.append(f"<li>{text}</li>")
        text = f"<strong>{label}</strong><ul>{''.join(parts)}</ul>"
    else:
        counts[f"{field}:changed"] += 1
        text = (
            f'<strong>{label}:</strong> <span class="before">'
            f'{esc(value_text(field, before))}</span> → '
            f'<span class="after">{esc(value_text(field, after))}</span>'
        )
    evidence = details(ref_label(change["evidenceRecord"]), f"<pre>{raw(change)}</pre>")
    return f"<li>{text}{evidence}</li>", counts


def army_label(army: int, names: dict[int, str]) -> str:
    # Current labels are navigation aids, not claims about historical names.
    return f"{names[army]} [#{army}, current label]" if army in names else f"Army #{army}"


def window(row: Document) -> str:
    return f"Observed between {row['earlierObservedDate']} and {row['laterObservedDate']}"


def render_army(row: Document, names: dict[int, str]) -> str:
    kind = row["kind"]
    if kind == "unitListMembership":
        direction = row["direction"]
        require(direction in {"appeared", "disappeared"}, "Unknown membership direction")
        text = ("Appeared in source list" if direction == "appeared"
                else "Disappeared from source list")
    else:
        require(kind in {"ava", "disabled"}, "Unknown Army field")
        text = (
            f"{FIELDS[kind]}: {value_text(kind, row['before'])} → "
            f"{value_text(kind, row['after'])}"
        )
    return (
        f"<article><strong>{esc(army_label(row['armyId'], names))}</strong> · "
        f"{esc(text)}<br><small>{esc(window(row))} · "
        f"{esc(encode(row['sourcePath']))}</small>"
        + details(ref_label(row["evidenceRecord"]), f"<pre>{raw(row)}</pre>")
        + "</article>"
    )


def render(preview: Document, names: dict[int, str]) -> tuple[str, dict[str, int]]:
    require(preview["publicationStatus"] == "privatePreviewOnly"
            and preview["edition"] == "n5" and preview["formatVersion"] == 1
            and preview["archiveSha256"] == ARCHIVE_PIN, "Unexpected history preview")
    counts: Counter[str] = Counter()
    units = []
    for unit in sorted(preview["units"], key=lambda row: (
        (row["name"] or "").casefold(), row["logicalUnitId"],
    )):
        groups = []
        for group in unit["composition"]:
            items = []
            for change in group["changes"]:
                html, tally = render_change(change)
                items.append(html)
                counts.update(tally)
                counts["compositionFields"] += 1
            armies = ", ".join(army_label(i, names) for i in group["armyIds"])
            groups.append(
                f"<article><strong>{esc(historical_target(group))}</strong><br>"
                f"<small>{esc(window(group))} · {esc(armies)}</small>"
                f"<ul>{''.join(items)}</ul></article>"
            )
            counts["compositionGroups"] += 1
        army_rows = [render_army(row, names) for row in unit["armyObservations"]]
        counts["armyObservations"] += len(army_rows)
        timeline = bool(groups or army_rows)
        counts["units"] += 1
        counts["unitsWithTimeline"] += int(timeline)
        reviews = {
            "reviewEvidence": unit["reviewEvidence"],
            "catalogEvidence": unit["catalogEvidence"],
            "rawChangeCategories": unit["rawChangeCategories"],
            "sourceIdentities": unit["sourceIdentities"],
        }
        review_count = sum(len(rows) for rows in unit["reviewEvidence"].values())
        catalog_count = sum(len(rows) for rows in unit["catalogEvidence"].values())
        counts["reviewLinks"] += review_count
        counts["catalogLinks"] += catalog_count
        search = " ".join([unit["name"] or "", unit["slug"] or "",
                           str(unit["logicalUnitId"]),
                           *(str(i["sourceUnitId"]) for i in unit["sourceIdentities"])])
        body = (
            f"<h3>Composition ({len(groups)})</h3>"
            + ("".join(groups) or "<p>No grouped composition candidates.</p>")
            + f"<h3>Army observations ({len(army_rows)})</h3>"
            + ("".join(army_rows) or "<p>No selected Army observations.</p>")
            + details(f"Review evidence ({review_count}) / catalog evidence ({catalog_count})",
                      f"<pre>{raw(reviews)}</pre>")
        )
        units.append(
            f'<details class="unit" data-search="{esc(search.lower())}" '
            f'data-timeline="{"yes" if timeline else "no"}">'
            f"<summary><strong>{esc(unit['name'] or 'Unnamed Unit')}</strong> "
            f"[#{unit['logicalUnitId']}] · {len(groups)} composition / "
            f"{len(army_rows)} Army observations</summary>{body}</details>"
        )
    coverage = {
        k: preview[k] for k in ("coverage", "ambiguousArmyWindows", "unresolvedIdentities",
                                "identityCounts", "recordLinkCounts")
    }
    header = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Private N5 Unit history review</title>'
        f"<style>{STYLE}</style></head><body><h1>Private N5 Unit history review</h1>"
        "<p>Research preview only. Entries are observed change candidates, not confirmed "
        "publication events. Observation gaps do not imply absence or unchanged data. "
        "Catalog transitions and unresolved records are not included as composition changes. "
        "Army labels refer to the current catalog; historical source IDs are preserved.</p>"
        f"<p>{counts['units']} Units · {counts['compositionGroups']} composition groups · "
        f"{counts['armyObservations']} Army observations</p>"
        + details("Coverage and unresolved identities", f"<pre>{raw(coverage)}</pre>")
        + '<label for="search">Filter Units</label><br>'
        '<input id="search" type="search" placeholder="Name, slug or ID">'
        '<br><label><input type="checkbox" id="with-history" checked '
        'style="width:auto"> Only Units with timeline entries</label>'
        '<p id="shown" aria-live="polite"></p>'
    )
    return header + "".join(units) + f"<script>{SCRIPT}</script></body></html>", dict(counts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--preview-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = (ROOT / "generated").resolve()
    output = args.output.resolve()
    require(output.is_relative_to(private), "Use the private history directory")
    require(args.preview.resolve().is_relative_to(private), "Use the private preview directory")
    require(not output.exists(), "Review output already exists")
    preview_bytes = args.preview.read_bytes()
    require(digest(preview_bytes) == args.preview_sha256, "Preview SHA-256 differs")
    preview = json.loads(preview_bytes)
    require(file_digest(ARMY) == preview["armyDatabaseSha256"], "Army database differs")
    require(file_digest(HISTORY) == preview["historyDatabaseSha256"], "History database differs")
    with closing(read_only(ARMY)) as db:
        names = dict(db.execute("SELECT id,name FROM army_lists WHERE name IS NOT NULL"))
    html, counts = render(preview, names)
    require(file_digest(ARMY) == preview["armyDatabaseSha256"], "Army database changed")
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(html)
    print(json.dumps(counts, indent=2, sort_keys=True))
    print(f"Private review: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
