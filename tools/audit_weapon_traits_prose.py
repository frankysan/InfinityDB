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
from collections import Counter
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
FORMAT_VERSION = 3
DEFAULT_REVIEW = Path("config/validation/weapon-trait-source-review.json")
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


def _review_policy(path: Path, pdf_sha256: str) -> dict[str, Any]:
    """Load reviewed, source-version-pinned notation and PDF cell exceptions."""
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("formatVersion") != 1 or review.get("corePdfSha256") != pdf_sha256:
        raise WeaponChartAuditError("Weapon Trait review is not pinned to this PDF")
    aliases = review.get("traitAliases")
    footnotes = review.get("combinedFootnotes")
    cells = review.get("verifiedSourceCells")
    if not all(isinstance(item, dict) for item in (aliases, footnotes, cells)):
        raise WeaponChartAuditError("Invalid Weapon Trait review mappings")
    if not all(isinstance(a, str) and isinstance(b, str) for a, b in aliases.items()):
        raise WeaponChartAuditError("Invalid Weapon Trait alias")
    if not all(isinstance(k, str) and isinstance(v, list) and v
               and all(isinstance(t, str) for t in v)
               for mapping in (footnotes, cells) for k, v in mapping.items()):
        raise WeaponChartAuditError("Invalid reviewed Weapon Trait tokens")
    return review


def _reviewed_tokens(items: list[str], review: dict[str, Any]) -> list[str]:
    """Normalize reviewed shorthand only, never infer or drop missing Traits."""
    replacements = review["traitAliases"]
    combined = review["combinedFootnotes"]
    expanded = [part for item in items for part in combined.get(item, [item])]
    return _normalized_traits([replacements.get(item, item) for item in expanded])


def _trait_cell(
    words: list[tuple[float, float, str]], y: float,
    previous_y: float | None, next_y: float | None,
) -> str:
    """Read only the printed Traits column within this anchored chart row.

    Exceptionally tall rows need a larger window: Cybermines on p.181 spans
    seven lines, including words outside both anchor midpoints. Only widen
    when both neighboring Burst anchors are over 50pt away; shorter rows
    retain the original 20/25pt limits to avoid consuming neighboring Traits.
    """
    spacious = (previous_y is None or y - previous_y > 40) and (
        next_y is None or next_y - y > 40
    )
    tall = (previous_y is None or y - previous_y > 50) and (
        next_y is None or next_y - y > 50
    )
    cap = 30 if tall else 25 if spacious else 20
    margin = 4 if tall else 0
    lower = max(
        y - cap,
        (previous_y + y) / 2 - margin if previous_y is not None else y - cap,
    )
    upper = min(
        y + cap,
        (next_y + y) / 2 + margin if next_y is not None else y + cap,
    )
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
    review: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in compared:
        key = (row["page"], row["printedName"])
        source = printed.get(key)
        source_reviewed = False
        if review is not None:
            source_key = f"{row['page']}:{row['printedName']}"
            if source_key in review["verifiedSourceCells"]:
                # The edited cell is valid only for the exact, pinned PDF SHA-256.
                source = ", ".join(review["verifiedSourceCells"][source_key])
                source_reviewed = True
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
        exact = _normalized_traits(pdf_tokens) == _normalized_traits(army_tokens)
        equivalent = bool(review) and (
            _reviewed_tokens(pdf_tokens, review) == _reviewed_tokens(army_tokens, review)
        )
        status = (
            "source-reviewed-match" if source_reviewed and (exact or equivalent)
            else "traits-match" if exact
            else "notation-equivalent" if equivalent
            else "candidate-discrepancy"
        )
        item: dict[str, Any] = {
            "page": row["page"], "name": row["name"], "mode": row["mode"],
            "printedTraits": pdf_tokens, "armyProperties": army_tokens,
            "status": status,
        }
        if source_reviewed:
            item["sourceCellReviewed"] = True
        if status == "candidate-discrepancy" and review is not None:
            pdf_counts = Counter(_reviewed_tokens(pdf_tokens, review))
            army_counts = Counter(_reviewed_tokens(army_tokens, review))
            item["sourceOnlyTraits"] = sorted((pdf_counts - army_counts).elements())
            item["armyOnlyTraits"] = sorted((army_counts - pdf_counts).elements())
        result.append(item)
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



def prose_reference_coverage(
    sections: list[dict[str, Any]], army_db: Path, rules_db: Path,
) -> list[dict[str, Any]]:
    """Inventory exact-name links, not inferred family/prose rule completeness.

    A source citation must name the section on its printed page. A matching
    Army weapon profile is source metadata, not a curated Weaponry definition.
    """
    army_uri = f"file:{army_db.resolve().as_posix()}?mode=ro"
    rules_uri = f"file:{rules_db.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(army_uri, uri=True) as connection:
        army_rows = connection.execute(
            "SELECT name, COALESCE(mode, '') FROM metadata_weapons"
        ).fetchall()
    with sqlite3.connect(rules_uri, uri=True) as connection:
        rules_rows = connection.execute(
            "SELECT collection_id, id, kind, name FROM records"
        ).fetchall()
        citations = connection.execute(
            "SELECT collection_id, record_id, page, section FROM record_citations "
            "WHERE source_id = 'n5-core-v5.3-pdf'"
        ).fetchall()
        relations = connection.execute(
            "SELECT collection_id, record_id FROM record_relations"
        ).fetchall()
        army_links = connection.execute(
            "SELECT collection_id, record_id FROM record_army_links"
        ).fetchall()
    coverage: list[dict[str, Any]] = []
    for section in sections:
        title = section["section"]
        title_id = _identity(title)
        matched_army = sorted(
            ({"name": str(name), "mode": str(mode)} for name, mode in army_rows
             if _identity(str(name)) == title_id),
            key=lambda row: (row["name"], row["mode"]),
        )
        matched_rules = sorted(
            ({"collectionId": str(collection), "id": str(record_id),
              "kind": str(kind), "name": str(name)}
             for collection, record_id, kind, name in rules_rows
             if _identity(str(name)) == title_id),
            key=lambda row: (row["collectionId"], row["id"]),
        )
        ids = {(row["collectionId"], row["id"]) for row in matched_rules}
        cited = sorted({
            (str(collection), str(record_id))
            for collection, record_id, page, name in citations
            if page == section["page"] and isinstance(name, str)
            and title_id in _identity(name)
        })
        coverage.append({
            "page": section["page"], "section": title,
            "sourcePresent": section["sourcePresent"],
            "exactArmyWeaponProfiles": matched_army,
            "exactCuratedRecords": matched_rules,
            "sectionCitedRecordIds": [
                f"{collection}/{record_id}" for collection, record_id in cited
            ],
            "exactRecordRelationCount": sum((str(c), str(r)) in ids for c, r in relations),
            "exactRecordArmyLinkCount": sum((str(c), str(r)) in ids for c, r in army_links),
        })
    return coverage

def audit_traits_and_prose(
    pdf: Path, army_db: Path, rules_db: Path,
    review_path: Path = DEFAULT_REVIEW,
) -> dict[str, Any]:
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
    review = _review_policy(review_path, _sha256(pdf))
    traits = compare_traits(
        baseline["comparison"]["compared"], printed, _weapon_properties(army_db), review
    )
    prose_coverage = prose_reference_coverage(sections, army_db, rules_db)
    reviewed_rows = {
        f"{row['page']}:{row['printedName']}" for row in baseline["comparison"]["compared"]
    }
    if not set(review["verifiedSourceCells"]).issubset(reviewed_rows):
        raise WeaponChartAuditError("Reviewed source cell not found in this Weapon Chart")
    return {
        "format": FORMAT, "formatVersion": FORMAT_VERSION,
        "status": "partial-trait-and-prose-inventory-not-rule-completeness",
        "corePdfSha256": _sha256(pdf),
        "armyDbSha256": _sha256(army_db),
        "rulesDbSha256": _sha256(rules_db),
        "traitRows": len(traits),
        "traitMatches": sum(row["status"] == "traits-match" for row in traits),
        "traitCandidates": sum(row["status"] == "candidate-discrepancy" for row in traits),
        "traitNotationEquivalent": sum(row["status"] == "notation-equivalent" for row in traits),
        "traitReviewedCells": sum(row["status"] == "source-reviewed-match" for row in traits),
        "reviewPolicySha256": _sha256(review_path),
        "traitDeferred": sum(row["status"].startswith("deferred") for row in traits),
        "traits": traits,
        "specialWeaponSections": sections,
        "specialWeaponReferenceCoverage": prose_coverage,
        "limitations": [
            "Notation equivalence covers only maintained source spelling and shorthand aliases.",
            "Two ambiguous PDF cells are hash-pinned and visually reviewed.",
            "Cybermine's tall seven-line Trait cell is captured using its printed row spacing.",
            "Residual Trait differences require source/Army review; not confirmed errors.",
            "Matching trait identities do not prove complete rules or links.",
            "A named curated weapon definition is not the only possible rules representation.",
            "Special-weapon prose is indexed, not compared clause by clause with curated rules.",
            "Reference coverage checks exact named Army profiles, curated records, "
            "N5 source-section citations and relations only; family/mode aliases "
            "remain unreviewed.",
            "Auxiliary deployable/object profiles, API and browser completeness remain unverified.",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# 1.0 N5 v5.3 Weapon Traits and special-weapon prose inventory", "",
        "**Partial source evidence, not a completeness verdict.**",
        "No gameplay data is changed by this audit.", "",
        f"- PDF SHA-256: `{report['corePdfSha256']}`",
        f"- Source-review policy SHA-256: `{report.get('reviewPolicySha256', 'unreviewed')}`",
        f"- Army database SHA-256: `{report.get('armyDbSha256', 'not recorded')}`",
        f"- Rules database SHA-256: `{report.get('rulesDbSha256', 'not recorded')}`",
        f"- Weapon Chart Trait rows checked: **{report['traitRows']}**.",
        f"- Literal matches: **{report['traitMatches']}**; reviewed notation: "
        f"**{report.get('traitNotationEquivalent', 0)}**; reviewed source cells: "
        f"**{report.get('traitReviewedCells', 0)}**; remaining candidates: "
        f"**{report['traitCandidates']}**; deferred: **{report['traitDeferred']}**.",
        "", "## Trait comparison candidates", "",
    ]
    for row in report["traits"]:
        if row["status"] == "candidate-discrepancy":
            lines.append(
                f"- **{row['name']}** ({row['mode'] or 'standard'}, p. {row['page']}): "
                f"PDF `{row['printedTraits']}`; Army `{row['armyProperties']}`; "
                f"source-only `{row.get('sourceOnlyTraits', [])}`, "
                f"Army-only `{row.get('armyOnlyTraits', [])}`."
            )
    if not report["traitCandidates"]:
        lines.append("- None in the current comparison subset.")
    lines.extend(["", "## Reviewed notation and source cells", ""])
    for row in report["traits"]:
        if row["status"] in ("notation-equivalent", "source-reviewed-match"):
            lines.append(
                f"- **{row['name']}** ({row['mode'] or 'standard'}, p. {row['page']}): "
                f"{row['status']}; PDF `{row['printedTraits']}`; Army `{row['armyProperties']}`."
            )
    lines.extend(["", "## Special-weapon prose section inventory (pp. 68-74)", ""])
    for item in report["specialWeaponSections"]:
        lines.append(
            f"- p. {item['page']}: **{item['section']}** — {item['status']}."
        )
    if "specialWeaponReferenceCoverage" in report:
        lines.extend(["", "## Exact-name Weaponry reference coverage", ""])
        for item in report["specialWeaponReferenceCoverage"]:
            names = [f"{row['name']} ({row['mode'] or 'standard'})"
                     for row in item["exactArmyWeaponProfiles"]]
            records = [f"{row['kind']}:{row['id']}" for row in item["exactCuratedRecords"]]
            lines.append(
                f"- p. {item['page']} **{item['section']}**: "
                f"Army profiles {names}; curated records {records}; "
                f"source-section citations {item['sectionCitedRecordIds']}; "
                f"record relations {item['exactRecordRelationCount']}; "
                f"Army links {item['exactRecordArmyLinkCount']}."
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
    parser.add_argument("--trait-review", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()
    try:
        report = audit_traits_and_prose(
            args.core_pdf, args.army_db, args.rules_db, args.trait_review
        )
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
