#!/usr/bin/env python3
"""Compare N5 v5.3 Weapon Chart Traits and inventory special-weapon prose.

Read-only and intentionally source-scoped. A printed trait match does not mean
that its underlying rule is curated or that its browser presentation is complete.
The core PDF is required only when this offline audit is explicitly invoked.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from tools.audit_weapon_chart_profiles import (
    PDF_PAGES,
    WeaponChartAuditError,
    _identity,
    _mode_identity,
    _sha256,
    rows_from_words,
)

FORMAT = "InfinityDB N5 v5.3 Weapon Traits and prose evidence"
FORMAT_VERSION = 1
# Printed N5 v5.3 Weaponry section headings, with their printed pages.
# These are an inventory of source sections, not invented rule definitions.
SPECIAL_SECTIONS = (
    (68, "Mixed Weapons"),
    (69, "Perimeter Weapons"),
    (70, "Armed Turret"),
    (70, "D-Charges"),
    (71, "Disco Baller"),
    (71, "Drop Bears"),
    (72, "Mine Dispenser"),
    (72, "Mines"),
    (73, "Pitcher"),
    (73, "Sepsitor"),
    (74, "SymbioBomb"),
    (74, "WildParrot"),
)


def _traits(value: str) -> list[str]:
    """Tokenize commas outside parentheses; retain source trait identities."""
    chunks: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            chunks.append(value[start:index])
            start = index + 1
    chunks.append(value[start:])
    return [item for chunk in chunks if (item := chunk.strip().rstrip("."))]


def _normalized_traits(items: list[str]) -> list[str]:
    """Compare spelling, case and whitespace, not source ordering."""
    return sorted(
        re.sub(r"\s+", "", unicodedata.normalize("NFKC", item).casefold())
        .replace("−", "-").replace("–", "-")
        for item in items
    )


def _trait_cell(
    words: list[tuple[float, float, str]], y: float,
    previous_y: float | None, next_y: float | None,
) -> str:
    """Read only the printed Traits column within this anchored chart row.

    Multiline traits can extend 24pt from a Burst anchor in tall rows.
    Midpoint clipping limits leakage, while the shorter 20pt cap on closely
    spaced rows avoids absorbing neighboring unanchored profile entries.
    """
    spacious = (previous_y is None or y - previous_y > 40) and (
        next_y is None or next_y - y > 40
    )
    cap = 25 if spacious else 20
    lower = max(y - cap, (previous_y + y) / 2 if previous_y is not None else y - cap)
    upper = min(y + cap, (next_y + y) / 2 if next_y is not None else y + cap)
    selected = [
        (wy, x, word) for x, wy, word in words
        if 460 <= x < 595 and lower <= wy < upper and word.upper() != "TRAITS"
    ]
    return " ".join(
        word for wy, x, word in sorted(selected, key=lambda item: (round(item[0] / 4.8), item[1]))
    ).strip()


def _source_traits_by_chart_row(doc: Any) -> dict[tuple[int, str], str]:
    rows: dict[tuple[int, str], str] = {}
    for page_number in PDF_PAGES:
        words = [
            (float(word[0]), float(word[1]), str(word[4]))
            for word in doc[page_number - 1].get_text("words")
        ]
        chart_rows = rows_from_words(words, page_number)
        anchors = sorted(
            y for x, y, word in words
            if 294 <= x <= 310 and 175 < y < 800
            and re.fullmatch(r"(?:[1-9]|10|--)", word)
        )
        if len(chart_rows) != len(anchors):
            raise WeaponChartAuditError(f"Ambiguous row anchors on page {page_number}")
        for index, row in enumerate(chart_rows):
            key = (page_number, row["name"])
            if key in rows:
                raise WeaponChartAuditError(f"Duplicate printed chart identity: {key}")
            rows[key] = _trait_cell(
                words, anchors[index],
                anchors[index - 1] if index else None,
                anchors[index + 1] if index + 1 < len(anchors) else None,
            )
    return rows


def compare_traits(
    compared: list[dict[str, Any]],
    printed: dict[tuple[int, str], str],
    properties: dict[tuple[str, str], list[str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in compared:
        key = (row["page"], row["printedName"])
        source = printed.get(key)
        # Do not equate absent/unextractable source rows with an empty Traits cell.
        if source is None or ". " in source:
            reason = "deferred-source-layout" if source is not None else "deferred-source"
            result.append({
                "page": row["page"], "name": row["name"],
                "mode": row["mode"], "status": reason,
            })
            continue
        matches = [
            value for (name, mode), value in properties.items()
            if _identity(name) == _identity(row["name"])
            and _mode_identity(mode) == _mode_identity(row["mode"])
        ]
        if len(matches) != 1:
            result.append({"page": row["page"], "name": row["name"],
                           "mode": row["mode"], "status": "deferred-army"})
            continue
        pdf_tokens = _traits(source)
        army_tokens = matches[0]
        status = (
            "traits-match" if _normalized_traits(pdf_tokens) == _normalized_traits(army_tokens)
            else "candidate-discrepancy"
        )
        result.append({
            "page": row["page"], "name": row["name"], "mode": row["mode"],
            "printedTraits": pdf_tokens, "armyProperties": army_tokens,
            "status": status,
        })
    return result


def _weapon_properties(army_db: Path) -> dict[tuple[str, str], list[str]]:
    uri = f"file:{army_db.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute("SELECT name, mode, properties FROM metadata_weapons").fetchall()
    props: dict[tuple[str, str], list[str]] = {}
    for name, mode, raw in rows:
        key = (str(name), str(mode or ""))
        parsed = json.loads(raw or "[]")
        if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
            raise WeaponChartAuditError(f"Invalid weapon properties for {key}")
        if key in props:
            raise WeaponChartAuditError(f"Duplicate weapon properties identity: {key}")
        props[key] = parsed
    return props


def prose_inventory(doc: Any, rules_db: Path) -> list[dict[str, Any]]:
    uri = f"file:{rules_db.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        curated = {
            _identity(name) for (name,) in conn.execute(
                "SELECT name FROM records WHERE kind = 'weapon'"
            )
        }
    sections: list[dict[str, Any]] = []
    for page, title in SPECIAL_SECTIONS:
        # Exact text on the named printed page establishes presence, not rule equivalence.
        source_present = bool(doc[page - 1].search_for(title))
        sections.append({
            "page": page, "section": title,
            "sourcePresent": source_present,
            "namedCuratedWeaponDefinition": _identity(title) in curated,
            "status": (
                "source-heading-unverified" if not source_present
                else "named-weapon-definition-present" if _identity(title) in curated
                else "no-named-curated-weapon-definition"
            ),
        })
    return sections


def audit_traits_and_prose(pdf: Path, army_db: Path, rules_db: Path) -> dict[str, Any]:
    try:
        import fitz  # type: ignore[import-untyped]  # Optional offline PDF dependency.
    except ImportError as exc:
        raise WeaponChartAuditError("PDF audit requires PyMuPDF") from exc
    from tools.audit_weapon_chart_profiles import audit_chart

    with fitz.open(pdf) as doc:
        if len(doc) < 188:
            raise WeaponChartAuditError("Expected N5 v5.3 PDF with Weapon Chart pp. 176-188")
        printed = _source_traits_by_chart_row(doc)
        sections = prose_inventory(doc, rules_db)
    baseline = audit_chart(pdf, army_db)
    if len(printed) != baseline["comparison"]["chartRowsLocated"]:
        raise WeaponChartAuditError("Trait evidence and existing chart row count disagree")
    traits = compare_traits(
        baseline["comparison"]["compared"], printed, _weapon_properties(army_db)
    )
    return {
        "format": FORMAT, "formatVersion": FORMAT_VERSION,
        "status": "partial-trait-and-prose-inventory-not-rule-completeness",
        "corePdfSha256": _sha256(pdf),
        "armyDbSha256": _sha256(army_db),
        "rulesDbSha256": _sha256(rules_db),
        "traitRows": len(traits),
        "traitMatches": sum(row["status"] == "traits-match" for row in traits),
        "traitCandidates": sum(row["status"] == "candidate-discrepancy" for row in traits),
        "traitDeferred": sum(row["status"].startswith("deferred") for row in traits),
        "traits": traits,
        "specialWeaponSections": sections,
        "limitations": [
            "PDF Trait cells are positionally reconstructed; candidates require visual review.",
            "Matching trait identities do not prove complete rules or links.",
            "A named curated weapon definition is not the only possible rules representation.",
            "Special-weapon prose is indexed, not compared clause by clause with curated rules.",
            "Auxiliary deployable/object profiles, API and browser completeness remain unverified.",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# 1.0 N5 v5.3 Weapon Traits and special-weapon prose inventory", "",
        "**Partial source evidence, not a completeness verdict.**",
        "No gameplay data is changed by this audit.", "",
        f"- PDF SHA-256: `{report['corePdfSha256']}`",
        f"- Army database SHA-256: `{report.get('armyDbSha256', 'not recorded')}`",
        f"- Rules database SHA-256: `{report.get('rulesDbSha256', 'not recorded')}`",
        f"- Weapon Chart Trait rows checked: **{report['traitRows']}**.",
        f"- Matching: **{report['traitMatches']}**; candidates: **{report['traitCandidates']}**; "
        f"deferred: **{report['traitDeferred']}**.",
        "", "## Trait comparison candidates", "",
    ]
    for row in report["traits"]:
        if row["status"] == "candidate-discrepancy":
            lines.append(
                f"- **{row['name']}** ({row['mode'] or 'standard'}, p. {row['page']}): "
                f"PDF `{row['printedTraits']}`; Army `{row['armyProperties']}`."
            )
    if not report["traitCandidates"]:
        lines.append("- None in the current comparison subset.")
    lines.extend(["", "## Special-weapon prose section inventory (pp. 68-74)", ""])
    for item in report["specialWeaponSections"]:
        lines.append(
            f"- p. {item['page']}: **{item['section']}** — {item['status']}."
        )
    lines.extend(["", "## Limitations and next verification", ""])
    lines.extend(f"- {text}" for text in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-pdf", required=True, type=Path)
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument("--rules-db", type=Path, default=Path("data/generated/rules.db"))
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        report = audit_traits_and_prose(args.core_pdf, args.army_db, args.rules_db)
    except (OSError, sqlite3.Error, WeaponChartAuditError) as exc:
        parser.error(str(exc))
    result = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(result, encoding="utf-8", newline="\n")
    else:
        print(result, end="")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
