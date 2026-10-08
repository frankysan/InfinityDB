#!/usr/bin/env python3
"""Cross-check unresolved Weapon Traits with the exact archived N5 Wiki chart.

Offline research tool: accepts local PDF/database/archived-Wiki inputs and never
modifies published gameplay data. The Wiki's old revision blocks are excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from tools.audit_weapon_traits_prose import (
    _review_policy,
    _reviewed_tokens,
    _traits,
    audit_traits_and_prose,
)

REVIEW_PATH = Path("config/validation/weapon-trait-wiki-review.json")
WIKI_MEMBER = "Weapon_Chart"


class WeaponTraitWikiError(ValueError):
    """Source archive or maintained review is incomplete or ambiguous."""


class _ChartTableReader(HTMLParser):
    """Read chart cells without treating collapsed, superseded rows as current."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.divs: list[bool] = []
        self.rows: list[tuple[list[str], bool]] = []
        self.cells: list[str] | None = None
        self.cell: list[str] | None = None
        self.historical = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div":
            classes = dict(attrs).get("class") or ""
            self.divs.append("original_border" in classes.split())
        elif tag == "tr":
            self.cells = []
            self.historical = any(self.divs)
        elif tag in ("td", "th") and self.cells is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            if self.divs:
                self.divs.pop()
        elif tag in ("td", "th") and self.cell is not None:
            if self.cells is not None:
                self.cells.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr":
            if self.cells is not None:
                self.rows.append((self.cells, self.historical))
            self.cells = None
            self.cell = None


def wiki_chart_rows(
    payload: bytes, wanted: set[str],
) -> tuple[int, dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    """Return current chart rows; ignore superseded Wiki original_border tables."""
    content = payload.decode("utf-8")
    revision = re.search(r'"wgRevisionId":(\d+)', content)
    if revision is None:
        raise WeaponTraitWikiError("Wiki chart lacks a revision ID")
    reader = _ChartTableReader()
    reader.feed(content)
    rows: dict[str, dict[str, str]] = {}
    superseded: dict[str, list[dict[str, str]]] = {}
    for cells, historical in reader.rows:
        if len(cells) != 14:
            continue
        name = cells[0]
        if name not in wanted:
            continue
        fields = {
            "ammunition": cells[-4], "savingRolls": cells[-2], "traits": cells[-1]
        }
        if historical:
            superseded.setdefault(name, []).append(fields)
            continue
        if name in rows:
            raise WeaponTraitWikiError(f"Ambiguous current Wiki chart row: {name}")
        rows[name] = fields
    if not rows:
        raise WeaponTraitWikiError("No current Wiki chart rows")
    return int(revision.group(1)), rows, superseded


def reconcile_candidates(
    candidates: list[dict[str, Any]],
    wiki_rows: dict[str, dict[str, str]],
    mapping: list[dict[str, Any]],
    trait_review: dict[str, Any],
    superseded: dict[str, list[dict[str, str]]] | None = None,
) -> list[dict[str, Any]]:
    """Match each current discrepancy to one specifically reviewed Wiki row."""
    identities = {(row["name"], row["mode"]) for row in candidates}
    mapped = {(row["name"], row["mode"]) for row in mapping}
    if len(mapped) != len(mapping) or identities != mapped:
        raise WeaponTraitWikiError("Wiki review identities no longer match the candidate set")
    results = []
    for entry in mapping:
        candidate = next(row for row in candidates if (
            row["name"], row["mode"]
        ) == (entry["name"], entry["mode"]))
        wiki_name = entry["wikiName"]
        if wiki_name not in wiki_rows:
            raise WeaponTraitWikiError(f"Missing Wiki chart identity: {wiki_name}")
        wiki = wiki_rows[wiki_name]
        wiki_traits = _traits(wiki["traits"])
        wiki_normalized = Counter(_reviewed_tokens(wiki_traits, trait_review))
        pdf_match = wiki_normalized == Counter(
            _reviewed_tokens(candidate["printedTraits"], trait_review)
        )
        army_match = wiki_normalized == Counter(
            _reviewed_tokens(candidate["armyProperties"], trait_review)
        )
        if pdf_match and army_match:
            status = "wiki-agrees-with-both"
        elif pdf_match:
            status = "wiki-agrees-with-pdf"
        elif army_match:
            status = "wiki-agrees-with-army"
        else:
            status = "three-way-trait-disagreement"
        record: dict[str, Any] = {
            "name": entry["name"], "mode": entry["mode"], "page": candidate["page"],
            "wikiName": wiki_name, "wikiTraits": wiki_traits,
            "wikiSavingRolls": wiki["savingRolls"],
            "pdfTraits": candidate["printedTraits"],
            "armyTraits": candidate["armyProperties"],
            "status": status, "reviewNote": entry["reviewNote"],
        }
        if superseded and wiki_name in superseded:
            record["supersededWikiRows"] = superseded[wiki_name]
        if "officialUpdate" in entry:
            record["officialUpdate"] = entry["officialUpdate"]
        if "semanticReview" in entry:
            record["semanticReview"] = entry["semanticReview"]
        results.append(record)
    return results


def _load_review(path: Path, pdf_hash: str) -> list[dict[str, Any]]:
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("formatVersion") != 1 or review.get("corePdfSha256") != pdf_hash:
        raise WeaponTraitWikiError("Wiki review is not pinned to this PDF")
    mapping = review.get("candidates")
    if not isinstance(mapping, list) or not mapping:
        raise WeaponTraitWikiError("Invalid Wiki review candidates")
    if not isinstance(review.get("wikiRevisionId"), int) or not isinstance(
        review.get("wikiMemberSha256"), str
    ) or not re.fullmatch(r"[a-f0-9]{64}", review["wikiMemberSha256"]):
        raise WeaponTraitWikiError("Wiki review lacks its exact source revision/hash")
    for item in mapping:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(key), str) and item[key]
            for key in ("name", "wikiName", "reviewNote")
        ) or not isinstance(item.get("mode"), str):
            raise WeaponTraitWikiError("Invalid Wiki review candidate")
        if "officialUpdate" in item:
            update = item["officialUpdate"]
            if not isinstance(update, dict) or not all(
                isinstance(update.get(key), str) and update[key]
                for key in ("date", "url", "claim")
            ) or not update["url"].startswith("https://infinityuniverse.com/en/news/"):
                raise WeaponTraitWikiError("Invalid official update evidence")
    for item in mapping:
        semantic = item.get("semanticReview")
        if not isinstance(semantic, dict) or semantic.get("state") not in (
            "explained", "partial"
        ) or not all(
            isinstance(semantic.get(key), str) and semantic[key]
            for key in ("classification", "finding", "remaining")
        ) or not isinstance(semantic.get("pdfPages"), list) or not semantic["pdfPages"] or not all(
            isinstance(page, int) and not isinstance(page, bool) and 1 <= page <= 196
            for page in semantic["pdfPages"]
        ):
            raise WeaponTraitWikiError("Invalid semantic review evidence")
    return mapping


def audit_cross_sources(
    pdf: Path, army_db: Path, rules_db: Path, wiki_archive: Path,
    review_path: Path = REVIEW_PATH,
) -> dict[str, Any]:
    pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    mapping = _load_review(review_path, pdf_hash)
    with zipfile.ZipFile(wiki_archive) as archive:
        payload = archive.read(WIKI_MEMBER)
    pinned = json.loads(review_path.read_text(encoding="utf-8"))
    if hashlib.sha256(payload).hexdigest() != pinned["wikiMemberSha256"]:
        raise WeaponTraitWikiError("Wiki chart payload differs from reviewed revision")
    revision, wiki_rows, superseded = wiki_chart_rows(
        payload, {entry["wikiName"] for entry in mapping}
    )
    if revision != pinned["wikiRevisionId"]:
        raise WeaponTraitWikiError("Wiki chart revision differs from reviewed source")
    reviewed = _review_policy(
        Path("config/validation/weapon-trait-source-review.json"), pdf_hash
    )
    base = audit_traits_and_prose(pdf, army_db, rules_db)
    candidates = [
        row for row in base["traits"] if row["status"] == "candidate-discrepancy"
    ]
    result = reconcile_candidates(
        candidates, wiki_rows, mapping, reviewed, superseded
    )
    return {
        "format": "InfinityDB N5 weapon-trait Wiki cross-source evidence",
        "formatVersion": 1,
        "status": "source-comparison-only-not-curation",
        "corePdfSha256": pdf_hash,
        "armyDbSha256": base["armyDbSha256"],
        "wikiArchiveSha256": hashlib.sha256(wiki_archive.read_bytes()).hexdigest(),
        "wikiMember": WIKI_MEMBER,
        "wikiRevisionId": revision,
        "wikiMemberSha256": hashlib.sha256(payload).hexdigest(),
        "reviewPolicySha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
        "candidates": result,
        "limitations": [
            "The archived Wiki page and Army metadata corroborate source claims, not authority.",
            "Current Wiki chart rows exclude superseded original-border revisions.",
            "Blog posts describe revisions but do not silently supersede the PDF or Army.",
            "Source differences remain visible even when their semantics have been reviewed.",
            "Reviewed interpretation does not alter raw Army metadata or source charts.",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    counts = Counter(row["status"] for row in report["candidates"])
    semantic_counts = Counter(
        row["semanticReview"]["state"] for row in report["candidates"]
        if "semanticReview" in row
    )
    lines = [
        "# 1.0 Weapon Trait cross-source review", "",
        "**Read-only source comparisons and reviewed interpretations; no gameplay data changed.**", "",
        f"- Core PDF SHA-256: `{report['corePdfSha256']}`",
        f"- Wiki history ZIP SHA-256: `{report['wikiArchiveSha256']}`",
        f"- Wiki `Weapon_Chart` revision: `{report['wikiRevisionId']}`",
        f"- Wiki member SHA-256: `{report['wikiMemberSha256']}`",
        f"- Army database SHA-256: `{report['armyDbSha256']}`",
        f"- Reviewed candidates: **{len(report['candidates'])}**.",
        f"- Wiki agrees with PDF: **{counts['wiki-agrees-with-pdf']}**; "
        f"with Army: **{counts['wiki-agrees-with-army']}**; "
        f"both: **{counts['wiki-agrees-with-both']}**; "
        f"neither: **{counts['three-way-trait-disagreement']}**.",
        f"- Semantic interpretations explained: **{semantic_counts['explained']}**; "
        f"partial: **{semantic_counts['partial']}**. "
        "Raw source differences remain intact.", "",
        "## Individual findings", "",
    ]
    for row in report["candidates"]:
        lines.extend([
            f"### {row['name']} ({row['mode'] or 'standard'}) — p. {row['page']}", "",
            f"- Comparison: **{row['status']}**; Wiki name: `{row['wikiName']}`.",
            f"- PDF Traits: `{row['pdfTraits']}`.",
            f"- Army Traits: `{row['armyTraits']}`.",
            f"- Archived Wiki Traits: `{row['wikiTraits']}`; "
            f"Wiki Saving Rolls: `{row['wikiSavingRolls']}`.",
            f"- Review: {row['reviewNote']}",
        ])
        if "semanticReview" in row:
            semantic = row["semanticReview"]
            lines.extend([
                f"- Semantic review: **{semantic['state']}** "
                f"(`{semantic['classification']}`); PDF pp. "
                + ", ".join(str(page) for page in semantic["pdfPages"]) + ".",
                f"- Finding: {semantic['finding']}",
                f"- Remaining: {semantic['remaining']}",
            ])
        if "supersededWikiRows" in row:
            lines.append(
                f"- Superseded Wiki chart row (not current): "
                f"`{row['supersededWikiRows']}`."
            )
        if "officialUpdate" in row:
            source = row["officialUpdate"]
            lines.append(
                f"- Official change ({source['date']}): {source['claim']} "
                f"[Source]({source['url']})."
            )
        lines.append("")
    lines.extend(["## Boundaries", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-pdf", type=Path, required=True)
    parser.add_argument("--wiki-history", type=Path, required=True)
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument("--rules-db", type=Path, default=Path("data/generated/rules.db"))
    parser.add_argument("--review", type=Path, default=REVIEW_PATH)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        report = audit_cross_sources(
            args.core_pdf, args.army_db, args.rules_db, args.wiki_history, args.review
        )
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        parser.error(str(exc))
    content = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(content, encoding="utf-8", newline="\n")
    else:
        print(content, end="")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
