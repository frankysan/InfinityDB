#!/usr/bin/env python3
"""Reconcile supplied 1.0 review inputs without importing or updating upstream sources.

This is an *evidence* report. It does not establish rule/weapon fact completeness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

try:
    from tools.audit_enrichment_coverage import audit_coverage
except ModuleNotFoundError:  # Executing this file directly from the tools directory.
    from audit_enrichment_coverage import audit_coverage

FORMAT = "InfinityDB 1.0 reference source evidence"
VERSION = 1
REVISION_ID = re.compile(r'"wgRevisionId":(\d+)')
PAGE_NAME = re.compile(r'"wgPageName":"([^"\\]*(?:\\.[^"\\]*)*)"')
HISTORY_PATH = re.compile(r"_history/oldid/(\d+)\.html")


class SourceEvidenceError(ValueError):
    """Source/archive data cannot be reconciled safely."""


class _TableCells(HTMLParser):
    """Collect chart-cell text, not navigation, page metadata, or script contents."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.table_depth = 0
        self.cell_depth = 0
        self.fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table_depth += 1
        elif tag in {"td", "th"} and self.table_depth:
            self.cell_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell_depth:
            self.cell_depth -= 1
        elif tag == "table" and self.table_depth:
            self.table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.cell_depth:
            self.fragments.append(data)


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip().casefold()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _oldid_pin(url: str) -> tuple[str, int] | None:
    parts = urlsplit(url)
    params = parse_qs(parts.query)
    title, oldids = params.get("title", []), params.get("oldid", [])
    if len(title) != 1 or len(oldids) != 1 or not oldids[0].isascii():
        return None
    if not oldids[0].isdigit():
        return None
    return title[0].replace(" ", "_"), int(oldids[0])


def _history_index(archive: zipfile.ZipFile) -> dict[tuple[str, int], str]:
    try:
        document = json.loads(archive.read("_history/index.json"))
    except (KeyError, ValueError) as exc:
        raise SourceEvidenceError("Missing or invalid Wiki history index") from exc
    if document.get("format") != "InfinityDB wiki revision history":
        raise SourceEvidenceError("Unexpected Wiki history index format")
    entries: dict[tuple[str, int], str] = {}
    for page in document.get("pages", []):
        for record in page.get("revisions", []):
            pin = _oldid_pin(record.get("url", ""))
            path = record.get("path")
            if pin is None or not isinstance(path, str):
                raise SourceEvidenceError("Invalid Wiki history revision metadata")
            match = HISTORY_PATH.fullmatch(path)
            if not match or int(match.group(1)) != pin[1]:
                raise SourceEvidenceError("Unsafe or inconsistent Wiki revision path")
            if pin in entries and entries[pin] != path:
                raise SourceEvidenceError("Conflicting Wiki history revision entry")
            entries[pin] = path
    return entries


def verify_wiki_revisions(
    archive: zipfile.ZipFile, sources: list[dict[str, str]]
) -> list[dict[str, str | int | None]]:
    """Verify exact historical payload IDs, never substitute current Wiki content."""
    entries = _history_index(archive)
    results: list[dict[str, str | int | None]] = []
    for source in sources:
        pin = _oldid_pin(source["url"])
        if pin is None:
            continue
        page, oldid = pin
        path = entries.get(pin)
        status = "not-in-history-index"
        if path is not None:
            try:
                html = archive.read(path)[:8192].decode("utf-8", "replace")
            except KeyError:
                status = "indexed-payload-missing"
            else:
                revision_match = REVISION_ID.search(html)
                name_match = PAGE_NAME.search(html)
                if (
                    revision_match
                    and name_match
                    and int(revision_match.group(1)) == oldid
                    and _normalized(json.loads('"' + name_match.group(1) + '"'))
                    == _normalized(page)
                ):
                    status = "exact-revision-payload"
                else:
                    status = "payload-identity-mismatch"
        results.append({
            "sourceId": source["id"],
            "wikiPage": page,
            "oldid": oldid,
            "archiveMember": path,
            "status": status,
        })
    return results


def chart_name_evidence(chart_html: str, names: list[str]) -> list[dict[str, str]]:
    """Candidate textual name evidence only; *not* verified weapon-profile coverage."""
    parser = _TableCells()
    parser.feed(chart_html)
    text = _normalized(" ".join(parser.fragments))
    items = []
    for name in names:
        needle = _normalized(name)
        found = bool(re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", text))
        items.append({"name": name, "evidence": "name-in-chart-text" if found else "not-seen"})
    return items


def build_report(
    army_database: Path,
    rules_database: Path,
    wiki_history: Path,
    core_pdf: Path,
    faq_pdf: Path,
) -> dict[str, Any]:
    for path in (army_database, rules_database, wiki_history, core_pdf, faq_pdf):
        if not path.is_file():
            raise SourceEvidenceError(f"Input unavailable: {path}")
    with sqlite3.connect(rules_database) as connection:
        pdf_pins = [dict(zip(("title", "version", "sha256"), row, strict=True))
                    for row in connection.execute(
                        "SELECT title, version, sha256 FROM sources WHERE kind = 'pdf'"
                    )]
        records = [
            {"id": row[0], "url": row[1]}
            for row in connection.execute(
                "SELECT DISTINCT id, url FROM sources WHERE url LIKE '%oldid=%' ORDER BY id"
            )
        ]
    enrichment = audit_coverage(army_database, rules_database)
    weapon_items = enrichment["domains"]["weapons"]["items"]
    weapon_names = [entry["name"] for entry in weapon_items]
    try:
        with zipfile.ZipFile(wiki_history) as archive:
            revisions = verify_wiki_revisions(archive, records)
            try:
                chart = archive.read("Weapon_Chart").decode("utf-8")
                commlink = archive.read("Commlink").decode("utf-8")
            except KeyError as exc:
                raise SourceEvidenceError(f"Wiki archive missing source page: {exc}") from exc
    except (zipfile.BadZipFile, OSError) as exc:
        raise SourceEvidenceError(f"Invalid Wiki archive: {exc}") from exc
    weapons = chart_name_evidence(chart, weapon_names)
    core_hash = _sha256(core_pdf)
    faq_hash = _sha256(faq_pdf)
    core_sources = [pin for pin in pdf_pins
                    if pin["title"] == "N5 Core Rules" and pin["version"] == "5.3"]
    faq_sources = [pin for pin in pdf_pins if "faq" in pin["title"].casefold()]
    if len(core_sources) != 1:
        raise SourceEvidenceError("Expected one N5 Core Rules v5.3 source pin")
    declared_core_hash = core_sources[0]["sha256"]
    core_status = (
        "declared-hash-match" if declared_core_hash == core_hash
        else "declared-hash-mismatch" if declared_core_hash
        else "version-declared-hash-unpinned"
    )
    faq_status = "cataloged-needs-revision-review" if faq_sources else "not-in-rules-source-catalog"
    exact = sum(record["status"] == "exact-revision-payload" for record in revisions)
    chart_names = sum(row["evidence"] == "name-in-chart-text" for row in weapons)
    return {
        "format": FORMAT,
        "formatVersion": VERSION,
        "status": "source-evidence-only-not-completeness",
        "suppliedArtifacts": {
            "coreRulesPdfSha256": core_hash,
            "faqPdfSha256": faq_hash,
            "wikiHistorySha256": _sha256(wiki_history),
            "coreRulesPdfPinStatus": core_status,
            "faqPdfPinStatus": faq_status,
            "wikiHistoryPinStatus": "distinct-from-declared-20260918-wiki-snapshot",
        },
        "wikiRevisionEvidence": {
            "exact": exact,
            "total": len(revisions),
            "items": revisions,
        },
        "enrichmentGapEvidence": {
            "weaponMissingRuleDefinitions": len(weapon_items),
            "weaponNamesSeenInWikiChartText": chart_names,
            "weaponNamesNotSeenInWikiChartText": len(weapons) - chart_names,
            "weaponItems": weapons,
            "commlinkMissingRuleDefinition": any(
                item["name"] == "Commlink" for item in enrichment["domains"]["skills"]["items"]
            ),
            "commlinkSupportingWikiPageAvailable": "Commlink" in commlink,
            "reinforcementsAnnexPdfSupplied": False,
        },
    }


def report_markdown(report: dict[str, Any]) -> str:
    artifacts = report["suppliedArtifacts"]
    wiki = report["wikiRevisionEvidence"]
    gaps = report["enrichmentGapEvidence"]
    lines = [
        "# 1.0 source evidence — input reconciliation",
        "",
        "This is an **evidence inventory**, not a gameplay-data completeness verdict.",
        "Do not add the supplied third-party PDFs or Wiki archive to the repository.",
        "",
        "## Exact Wiki revisions",
        "",
        f"- Exact historical revision payloads: **{wiki['exact']}/{wiki['total']}**.",
        "- Each match validates page identity and `wgRevisionId` against an indexed",
        "  historical payload.",
        "- A match does **not** validate InfinityDB's curated interpretation or relationships.",
        "",
        "## Supplied artifact hashes (SHA-256)",
        "",
        f"- Core N5 v5.3 PDF: `{artifacts['coreRulesPdfSha256']}`",
        "  (no declared SHA in current catalog).",
        f"- FAQ v0.1 PDF: `{artifacts['faqPdfSha256']}` (not yet independently cataloged).",
        f"- Wiki history ZIP: `{artifacts['wikiHistorySha256']}`",
        "  (different from pinned 2026-09-18 snapshot).",
        "",
        "## Weapon and Commlink triage",
        "",
        f"- **{gaps['weaponMissingRuleDefinitions']}** Weapons lack a curated rule definition.",
        f"- **{gaps['weaponNamesSeenInWikiChartText']}** names occur as text in the",
        "  Wiki Weapon Chart's tables;",
        f"  **{gaps['weaponNamesNotSeenInWikiChartText']}** do not. These are",
        "  **candidate matches**, not profile-fact coverage.",
        "- Weapon profile storage and missing *rule definitions* are separate audit dimensions.",
        "- Commlink lacks a curated rule definition; a related Wiki page is available,",
        "  but the official separately scoped Reinforcements Extra PDF has not been supplied.",
        "",
        "## Follow-up",
        "",
        "- Verify Weapon Chart rows, modes, ammunition, ranges, saves and Traits against the",
        "  core PDF pages 176–188 and published weapon profiles; review unmatched names/aliases.",
        "- Reconcile the FAQ v0.1 as its own publication and review scope for core/ITS questions.",
        "- Obtain the exact Reinforcements Extra and curate Commlink/Request",
        "  Reinforcements separately.",
        "- Review all 1.0 deferred gap classifications; do not promote every missing definition to",
        "  a core-rule defect without checking its source ownership.",
        "",
        "## Weapon names not seen verbatim in Wiki Weapon Chart table text",
        "",
    ]
    for item in gaps["weaponItems"]:
        if item["evidence"] == "not-seen":
            lines.append(f"- {item['name']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument("--rules-db", type=Path, default=Path("data/generated/rules.db"))
    parser.add_argument("--wiki-history", type=Path, required=True)
    parser.add_argument("--core-pdf", type=Path, required=True)
    parser.add_argument("--faq-pdf", type=Path, required=True)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        result = build_report(
            args.army_db, args.rules_db, args.wiki_history, args.core_pdf, args.faq_pdf
        )
    except (SourceEvidenceError, sqlite3.DatabaseError) as exc:
        parser.error(str(exc))
    payload = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(
            report_markdown(result), encoding="utf-8", newline="\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
