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
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlsplit

try:
    from tools.audit_enrichment_coverage import audit_coverage
except ModuleNotFoundError:  # Executing this file directly from the tools directory.
    from audit_enrichment_coverage import audit_coverage

FORMAT = "InfinityDB 1.0 reference source evidence"
VERSION = 4
ROOT = Path(__file__).resolve().parents[1]
REINFORCEMENTS_INVENTORY = ROOT / "config/validation/reinforcements-source-inputs.json"
FAQ_INVENTORY = ROOT / "config/validation/n5-faq-v0.1-question-inventory.json"
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


def verify_reinforcements_inputs(
    inventory_path: Path, source_root: Path = ROOT,
) -> dict[str, Any]:
    """Verify reviewed historical bytes without granting current N5 authority.

    Edition identity comes from the maintained cover review and its byte pin,
    not a filename or PDF metadata. Missing ignored files are not verified.
    """
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceEvidenceError("Cannot read Reinforcements source inventory") from exc
    scope = "historical-source-identity-not-n5-authority"
    if (not isinstance(inventory, dict) or set(inventory) != {"formatVersion", "scope", "sources"}
            or type(inventory.get("formatVersion")) is not int
            or inventory.get("formatVersion") != 1
            or inventory.get("scope") != scope):
        raise SourceEvidenceError("Unsupported Reinforcements inventory contract")
    sources = inventory.get("sources")
    if not isinstance(sources, list) or len(sources) != 2:
        raise SourceEvidenceError("Expected two historical Reinforcements sources")
    seen_ids: set[str] = set()
    seen_languages: set[str] = set()
    items = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {
            "id", "language", "edition", "applicability", "localPath", "sha256",
            "sourceUrl", "publishedDate",
        }:
            raise SourceEvidenceError("Invalid Reinforcements source fields")
        source_id = source["id"]
        language = source["language"]
        if (not isinstance(source_id, str) or not source_id
                or source_id in seen_ids or not isinstance(language, str)
                or language not in {"en", "es"}
                or language in seen_languages):
            raise SourceEvidenceError("Invalid or duplicate Reinforcements source identity")
        if (source["edition"] != "N4" or source["applicability"] != "historical-only"
                or source["publishedDate"] is not None):
            raise SourceEvidenceError(
                "Reinforcements inventory cannot establish N5 authority or dates"
            )
        relative = source["localPath"]
        if (not isinstance(relative, str) or "\\" in relative
                or not relative.startswith("data/pdf/rules/")
                or ".." in PurePosixPath(relative).parts
                or not relative.endswith(".pdf")):
            raise SourceEvidenceError("Unsafe Reinforcements source path")
        digest = source["sha256"]
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise SourceEvidenceError("Invalid Reinforcements source fingerprint")
        url = source["sourceUrl"]
        if (not isinstance(url, str) or urlsplit(url).scheme != "https"
                or urlsplit(url).netloc != "downloads.corvusbelli.com"):
            raise SourceEvidenceError("Expected an official Reinforcements source URL")
        path = (source_root / relative).resolve()
        if not path.is_relative_to(source_root.resolve()):
            raise SourceEvidenceError("Reinforcements source escapes the research root")
        actual = None
        if path.exists():
            try:
                actual = _sha256(path)
            except OSError as exc:
                raise SourceEvidenceError(
                    f"Cannot read Reinforcements source: {source_id}"
                ) from exc
            if actual != digest:
                raise SourceEvidenceError(f"Reinforcements source hash mismatch: {source_id}")
        items.append({
            **source,
            "actualSha256": actual,
            "status": "verified-pinned-historical-bytes" if actual else "not-supplied",
        })
        seen_ids.add(source_id)
        seen_languages.add(language)
    return {
        "scope": scope,
        "declaredCount": len(items),
        "verifiedCount": sum(item["actualSha256"] is not None for item in items),
        "n5AuthorityVerified": False,
        "items": items,
    }


def _oldid_pin(url: str) -> tuple[str, int] | None:
    parts = urlsplit(url)
    params = parse_qs(parts.query)
    title, oldids = params.get("title", []), params.get("oldid", [])
    if len(title) != 1 or len(oldids) != 1 or not oldids[0].isascii():
        return None
    if not oldids[0].isdigit():
        return None
    return title[0].replace(" ", "_"), int(oldids[0])


def _wiki_history_language(url: str) -> str:
    """Select a history archive by Wiki URL path, not by translated page title."""
    path = urlsplit(url).path
    return "es" if path.startswith(("/wiki-es/", "/es/")) else "en"


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


class _WikiHeadings(HTMLParser):
    """Read rendered heading text rather than matching unrelated page chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._inside = False
        self._fragments: list[str] = []
        self.headings: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._inside = True
            self._fragments = []

    def handle_data(self, data: str) -> None:
        if self._inside:
            self._fragments.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._inside and tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings.add(_normalized("".join(self._fragments)))
            self._inside = False


class _WikiErrataLabels(HTMLParser):
    """Recognize dated, bold-labelled Wiki errata, not arbitrary body text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._border_depth = 0
        self._title = False
        self._highlight = False
        self._bold = False
        self._title_text: list[str] = []
        self._bold_text: list[str] = []
        self._first_label = ""
        self.labels: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set((dict(attrs).get("class") or "").split())
        if tag == "div" and "errata_border" in classes:
            self._border_depth = 1
            self._title = False
            self._highlight = False
            self._bold = False
            self._title_text = []
            self._bold_text = []
            self._first_label = ""
            return
        if not self._border_depth:
            return
        if tag == "div":
            self._border_depth += 1
            if "errata_highlightblock" in classes:
                self._highlight = True
        elif tag == "span" and "errata_title" in classes:
            self._title = True
        elif tag == "b" and self._highlight and not self._first_label:
            self._bold = True
            self._bold_text = []

    def handle_data(self, data: str) -> None:
        if self._title:
            self._title_text.append(data)
        if self._bold:
            self._bold_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "b" and self._bold:
            self._first_label = _normalized("".join(self._bold_text))
            self._bold = False
        if tag == "span" and self._title:
            self._title = False
        if tag == "div" and self._border_depth:
            if self._highlight and self._border_depth == 2:
                self._highlight = False
            self._border_depth -= 1
            if not self._border_depth:
                title = _normalized("".join(self._title_text))
                dated = re.search(r"(\w+\s+20\d{2})$", title)
                if self._first_label and dated:
                    self.labels.add(f"{self._first_label}: {dated.group(1)}")


def verify_curated_wiki_snapshot(
    snapshot: Path,
    history: zipfile.ZipFile,
    sources: list[dict[str, Any]],
    references: list[dict[str, str | None]],
) -> dict[str, Any]:
    """Verify the declared ZIP and every citation/vocabulary locator against local bytes.

    Identical member revision IDs in the later history archive corroborate the
    chosen capture; they do not authenticate an unavailable earlier capture.
    """
    identities = {
        (source["id"], source["localPath"], source["sha256"], source["documentCount"])
        for source in sources
    }
    if len(identities) != 1:
        raise SourceEvidenceError("Expected one consistent local Wiki snapshot pin")
    source_id, local_path, declared_hash, document_count = identities.pop()
    if (
        not isinstance(source_id, str)
        or not isinstance(local_path, str)
        or not isinstance(declared_hash, str)
        or not isinstance(document_count, int)
    ):
        raise SourceEvidenceError("Incomplete curated Wiki snapshot source identity")
    if snapshot.name != Path(local_path).name:
        raise SourceEvidenceError("Supplied Wiki snapshot does not match curated archive name")
    if not snapshot.is_file():
        raise SourceEvidenceError(f"Wiki snapshot unavailable: {snapshot}")
    archive_hash = _sha256(snapshot)
    if archive_hash != declared_hash:
        raise SourceEvidenceError("Wiki snapshot SHA-256 differs from curated source pin")
    if not references:
        raise SourceEvidenceError("No archived Wiki references found in curated database")

    checked_headings = 0
    checked_revisions: set[str] = set()
    seen_pages: set[str] = set()
    try:
        with zipfile.ZipFile(snapshot) as archive:
            if len(archive.namelist()) != document_count:
                raise SourceEvidenceError("Wiki snapshot member count differs from source pin")
            members = set(archive.namelist())
            heading_cache: dict[str, set[str]] = {}
            for reference in references:
                member = reference["member"]
                if reference["sourceId"] != source_id or not member or member not in members:
                    raise SourceEvidenceError(f"Unresolvable Wiki citation member: {member!r}")
                if member not in heading_cache:
                    page = archive.read(member)
                    html = page.decode("utf-8", "replace")
                    headings = _WikiHeadings()
                    headings.feed(html)
                    errata = _WikiErrataLabels()
                    errata.feed(html)
                    heading_cache[member] = headings.headings | errata.labels
                    if member not in history.namelist():
                        raise SourceEvidenceError(f"Wiki history has no matching page: {member}")
                    historical_page = history.read(member)
                    current_revision = REVISION_ID.search(
                        page[:8192].decode("utf-8", "replace")
                    )
                    historical_revision = REVISION_ID.search(
                        historical_page[:8192].decode("utf-8", "replace")
                    )
                    if (
                        current_revision is None
                        or historical_revision is None
                        or current_revision.group(1) != historical_revision.group(1)
                    ):
                        raise SourceEvidenceError(f"Wiki page revision mismatch: {member}")
                    checked_revisions.add(member)
                seen_pages.add(member)
                heading = reference["heading"]
                if heading:
                    checked_headings += 1
                    if _normalized(heading) not in heading_cache[member]:
                        raise SourceEvidenceError(
                            f"Wiki citation heading not present: {member} / {heading}"
                        )
    except (OSError, zipfile.BadZipFile, UnicodeError, KeyError) as exc:
        raise SourceEvidenceError(f"Cannot verify Wiki snapshot: {exc}") from exc

    return {
        "sourceId": source_id,
        "archiveName": snapshot.name,
        "archiveSha256": archive_hash,
        "sourceDeclarations": len(sources),
        "references": len(references),
        "uniquePages": len(seen_pages),
        "headingsVerified": checked_headings,
        "matchingHistoryPageRevisions": len(checked_revisions),
        "status": "verified-local-source-and-locators",
    }


def verify_curated_wiki_snapshots(
    sources: list[dict[str, Any]],
    references: list[dict[str, str | None]],
    snapshots: dict[str, Path],
    histories: dict[str, zipfile.ZipFile],
) -> dict[str, dict[str, Any]]:
    """Verify every pinned language independently, with its own history evidence."""
    by_language: dict[str, list[dict[str, Any]]] = {}
    source_language: dict[str, str] = {}
    for source in sources:
        language = source.get("language")
        source_id = source.get("id")
        if language not in {"en", "es"} or not isinstance(source_id, str):
            raise SourceEvidenceError("Wiki snapshot requires explicit en/es language and ID")
        if source_id in source_language and source_language[source_id] != language:
            raise SourceEvidenceError(f"Wiki snapshot source ID spans languages: {source_id}")
        source_language[source_id] = language
        by_language.setdefault(language, []).append(source)
    if set(by_language) != set(snapshots):
        raise SourceEvidenceError(
            "Supplied Wiki snapshots must match pinned languages: "
            f"pinned {sorted(by_language)}, supplied {sorted(snapshots)}"
        )
    if set(snapshots) - set(histories):
        raise SourceEvidenceError("Each Wiki snapshot needs matching-language history")
    by_reference: dict[str, list[dict[str, str | None]]] = {
        language: [] for language in snapshots
    }
    for reference in references:
        language = source_language.get(str(reference["sourceId"]))
        if language is None:
            raise SourceEvidenceError(
                f"Wiki citation references unpinned source: {reference['sourceId']!r}"
            )
        by_reference[language].append(reference)
    return {
        language: verify_curated_wiki_snapshot(
            snapshot, histories[language], by_language[language], by_reference[language]
        )
        for language, snapshot in snapshots.items()
    }


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


def faq_pdf_pin_evidence(
    catalog: list[dict[str, Any]], actual_hash: str, inventory_path: Path = FAQ_INVENTORY,
) -> dict[str, Any]:
    """Match supplied bytes to reviewed FAQ identities without inferring applicability."""
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceEvidenceError("Cannot read FAQ source inventory") from exc
    artifacts = inventory.get("sourceArtifacts") if isinstance(inventory, dict) else None
    if not isinstance(artifacts, dict) or not artifacts:
        raise SourceEvidenceError("FAQ inventory requires reviewed source artifacts")
    reviewed = {}
    for source_id, artifact in artifacts.items():
        digest = artifact.get("sha256") if isinstance(artifact, dict) else None
        if (not isinstance(source_id, str) or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None):
            raise SourceEvidenceError("Invalid FAQ source fingerprint")
        reviewed[source_id] = digest.lower()
    declared: dict[str, str | None] = {}
    for source in catalog:
        source_id = source["id"]
        if source_id not in reviewed:
            continue
        digest = source["sha256"]
        if digest is not None:
            if not isinstance(digest, str) or digest.lower() != reviewed[source_id]:
                raise SourceEvidenceError(
                    f"FAQ source pin differs from reviewed bytes: {source_id}"
                )
            digest = digest.lower()
        if source_id in declared and declared[source_id] != digest:
            raise SourceEvidenceError(f"Conflicting FAQ source declarations: {source_id}")
        declared[source_id] = digest
    matches = sorted(source_id for source_id, digest in declared.items() if digest == actual_hash)
    status = (
        "declared-hash-match" if matches else "not-in-rules-source-catalog" if not declared
        else "version-declared-hash-unpinned" if None in declared.values()
        else "declared-hash-mismatch"
    )
    return {"status": status, "matchedSourceIds": matches,
            "publicationScope": "not-verified-by-byte-check"}


def build_report(
    army_database: Path,
    rules_database: Path,
    wiki_history: Path,
    core_pdf: Path,
    faq_pdf: Path,
    wiki_snapshot: Path | None = None,
    wiki_history_es: Path | None = None,
    wiki_snapshot_es: Path | None = None,
    reinforcements_inventory: Path = REINFORCEMENTS_INVENTORY,
    faq_inventory: Path = FAQ_INVENTORY,
) -> dict[str, Any]:
    for path in (army_database, rules_database, wiki_history, core_pdf, faq_pdf):
        if not path.is_file():
            raise SourceEvidenceError(f"Input unavailable: {path}")
    with sqlite3.connect(rules_database) as connection:
        pdf_pins: list[dict[str, Any]] = [
            dict(zip(("id", "title", "version", "sha256"), row, strict=True))
                    for row in connection.execute(
                        "SELECT id, title, version, sha256 FROM sources WHERE kind = 'pdf'"
                    )]
        records = [
            {"id": row[0], "url": row[1]}
            for row in connection.execute(
                "SELECT DISTINCT id, url FROM sources WHERE url LIKE '%oldid=%' ORDER BY id"
            )
        ]
        english_records = [
            record for record in records if _wiki_history_language(record["url"]) == "en"
        ]
        spanish_records = [
            record for record in records if _wiki_history_language(record["url"]) == "es"
        ]
        local_sources: list[dict[str, Any]] = []
        archived_references: list[dict[str, str | None]] = []
        if wiki_snapshot is not None or wiki_snapshot_es is not None:
            local_sources = [
                {
                    "id": row[0],
                    "localPath": row[1],
                    "sha256": row[2],
                    "documentCount": row[3],
                    "language": row[4],
                }
                for row in connection.execute(
                    "SELECT id, local_path, sha256, document_count, language "
                    "FROM sources WHERE kind = 'wiki' AND local_path IS NOT NULL"
                )
            ]
            for table in ("record_citations", "vocabulary_sources"):
                archived_references.extend(
                    {"sourceId": row[0], "member": row[1], "heading": row[2]}
                    for row in connection.execute(
                        f"SELECT r.source_id, r.member, r.heading FROM {table} AS r "
                        "JOIN sources AS s ON r.collection_id = s.collection_id "
                        "AND r.source_id = s.id WHERE s.kind = 'wiki' "
                        "AND s.local_path IS NOT NULL"
                    )
                )
    reinforcements = verify_reinforcements_inputs(reinforcements_inventory)
    enrichment = audit_coverage(army_database, rules_database)
    weapon_items = enrichment["domains"]["weapons"]["items"]
    weapon_names = [entry["name"] for entry in weapon_items]
    snapshots = {
        language: path for language, path in (
            ("en", wiki_snapshot), ("es", wiki_snapshot_es)
        ) if path is not None
    }
    if wiki_snapshot_es is not None and wiki_history_es is None:
        raise SourceEvidenceError("Spanish Wiki snapshot requires Spanish history archive")
    try:
        with zipfile.ZipFile(wiki_history) as archive:
            revisions = verify_wiki_revisions(archive, english_records)
            try:
                chart = archive.read("Weapon_Chart").decode("utf-8")
                commlink = archive.read("Commlink").decode("utf-8")
            except KeyError as exc:
                raise SourceEvidenceError(f"Wiki archive missing source page: {exc}") from exc
    except (zipfile.BadZipFile, OSError) as exc:
        raise SourceEvidenceError(f"Invalid Wiki archive: {exc}") from exc
    if wiki_history_es is not None:
        if not wiki_history_es.is_file():
            raise SourceEvidenceError(f"Spanish Wiki history unavailable: {wiki_history_es}")
        try:
            with zipfile.ZipFile(wiki_history_es) as spanish_archive:
                revisions.extend(verify_wiki_revisions(spanish_archive, spanish_records))
        except (zipfile.BadZipFile, OSError) as exc:
            raise SourceEvidenceError(f"Invalid Spanish Wiki archive: {exc}") from exc
    else:
        for record in spanish_records:
            pin = _oldid_pin(record["url"])
            if pin is None:
                raise SourceEvidenceError("Invalid Spanish Wiki revision source URL")
            revisions.append({
                "sourceId": record["id"],
                "wikiPage": pin[0],
                "oldid": pin[1],
                "archiveMember": None,
                "status": "spanish-history-not-supplied",
            })
    snapshot_evidence_by_language: dict[str, dict[str, Any]] = {}
    if snapshots:
        try:
            with zipfile.ZipFile(wiki_history) as english_archive:
                if wiki_history_es is not None:
                    with zipfile.ZipFile(wiki_history_es) as spanish_archive:
                        snapshot_evidence_by_language = verify_curated_wiki_snapshots(
                            local_sources, archived_references, snapshots,
                            {"en": english_archive, "es": spanish_archive},
                        )
                else:
                    snapshot_evidence_by_language = verify_curated_wiki_snapshots(
                        local_sources, archived_references, snapshots,
                        {"en": english_archive},
                    )
        except (zipfile.BadZipFile, OSError) as exc:
            raise SourceEvidenceError(f"Invalid Wiki history archive: {exc}") from exc
    snapshot_evidence = snapshot_evidence_by_language.get("en")
    spanish_snapshot_evidence = snapshot_evidence_by_language.get("es")
    weapons = chart_name_evidence(chart, weapon_names)
    core_hash = _sha256(core_pdf)
    faq_hash = _sha256(faq_pdf)
    core_sources = [pin for pin in pdf_pins
                    if pin["title"] == "N5 Core Rules" and pin["version"] == "5.3"]
    core_hashes = {pin["sha256"].lower() if pin["sha256"] else None for pin in core_sources}
    if not core_sources or len(core_hashes) != 1:
        raise SourceEvidenceError("Expected consistent N5 Core Rules v5.3 source pins")
    declared_core_hash = next(iter(core_hashes))
    core_status = (
        "declared-hash-match" if declared_core_hash == core_hash
        else "declared-hash-mismatch" if declared_core_hash
        else "version-declared-hash-unpinned"
    )
    faq_evidence = faq_pdf_pin_evidence(pdf_pins, faq_hash, faq_inventory)
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
            "wikiSpanishHistorySha256": (
                _sha256(wiki_history_es) if wiki_history_es is not None else None
            ),
            "coreRulesPdfPinStatus": core_status,
            "faqPdfPinStatus": faq_evidence["status"],
            "faqPdfMatchedSourceIds": faq_evidence["matchedSourceIds"],
            "faqPublicationScope": faq_evidence["publicationScope"],
            "wikiHistoryPinStatus": "separate-historical-revision-evidence",
            "wikiSnapshotPinStatus": (
                "verified" if snapshot_evidence_by_language else "not-checked"
            ),
        },
        "wikiSnapshotEvidence": snapshot_evidence,
        "wikiSpanishSnapshotEvidence": spanish_snapshot_evidence,
        "reinforcementsSourceEvidence": reinforcements,
        "wikiRevisionEvidence": {
            "exact": exact,
            "total": len(revisions),
            "notChecked": sum(
                row["status"] == "spanish-history-not-supplied" for row in revisions
            ),
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
            "reinforcementsAnnexPdfSupplied": reinforcements["verifiedCount"] > 0,
            "reinforcementsN5AuthorityVerified": False,
        },
    }


def report_markdown(report: dict[str, Any]) -> str:
    artifacts = report["suppliedArtifacts"]
    wiki = report["wikiRevisionEvidence"]
    snapshot = report["wikiSnapshotEvidence"]
    spanish_snapshot = report.get("wikiSpanishSnapshotEvidence")
    gaps = report["enrichmentGapEvidence"]
    reinforcements = report["reinforcementsSourceEvidence"]
    reinforcement_lines = [
        "## Historical Reinforcements source identity",
        "",
        f"- Verified pinned historical PDFs: **{reinforcements['verifiedCount']}/"
        f"{reinforcements['declaredCount']}**.",
        "- These are reviewed N4 inputs, not verified N5 procedural authority.",
        "- Edition identity follows the maintained cover review and matching byte pin;",
        "  this check does not parse the PDFs or verify current online publications.",
    ]
    for item in reinforcements["items"]:
        reinforcement_lines.append(
            f"- `{item['localPath']}`: **{item['status']}**; declared SHA-256 "
            f"`{item['sha256']}`; publication date unestablished."
        )
    snapshot_lines = (
        [
            f"- Verified pinned archive: `{snapshot['archiveName']}`",
            f"  (SHA-256: `{snapshot['archiveSha256']}`).",
            f"- Checked {snapshot['references']} citation/vocabulary references across",
            f"  {snapshot['uniquePages']} distinct Wiki pages,",
            f"  {snapshot['headingsVerified']} rendered headings, and",
            f"  {snapshot['matchingHistoryPageRevisions']} matching history-page revisions.",
        ] if snapshot is not None else [
            "- Not checked: pass `--wiki-snapshot` to verify the curated source ZIP",
            "  and all cited page members/headings against the source declarations.",
        ]
    )
    if spanish_snapshot is not None:
        snapshot_lines.extend([
            f"- Verified Spanish archive: `{spanish_snapshot['archiveName']}`",
            f"  (SHA-256: `{spanish_snapshot['archiveSha256']}`).",
            f"- Checked {spanish_snapshot['references']} Spanish citation/vocabulary references",
            f"  across {spanish_snapshot['uniquePages']} pages,",
            f"  {spanish_snapshot['headingsVerified']} headings and",
            f"  {spanish_snapshot['matchingHistoryPageRevisions']} matching historical revisions.",
        ])
    lines = [
        "# 1.0 source evidence — input reconciliation",
        "",
        "This is an **evidence inventory**, not a gameplay-data completeness verdict.",
        "Do not add the supplied third-party PDFs or Wiki archive to the repository.",
        "",
        "## Exact Wiki revisions",
        "",
        f"- Exact historical revision payloads: **{wiki['exact']}/{wiki['total']}**.",
        f"- Revision identities not checked: **{wiki['notChecked']}**",
        "  (provide the language-matched Spanish history archive when applicable).",
        "- Each match validates page identity and `wgRevisionId` against an indexed",
        "  historical payload.",
        "- A match does **not** validate InfinityDB's curated interpretation or relationships.",
        "",
        "## Curated Wiki snapshot",
        "",
        *snapshot_lines,
        "",
        "## Supplied artifact hashes (SHA-256)",
        "",
        f"- Core N5 v5.3 PDF: `{artifacts['coreRulesPdfSha256']}`",
        f"  (pin status: {artifacts['coreRulesPdfPinStatus']}).",
        f"- Supplied FAQ PDF: `{artifacts['faqPdfSha256']}`",
        f"  (pin status: {artifacts['faqPdfPinStatus']}; matched sources: "
        + (", ".join(artifacts["faqPdfMatchedSourceIds"]) or "none") + ").",
        "  Byte identity does not establish publication dates or gameplay applicability.",
        f"- English Wiki history ZIP: `{artifacts['wikiHistorySha256']}`",
        "  (separate historical-revision evidence; not interchangeable with the curated snapshot).",
        f"- Spanish Wiki history ZIP: `{artifacts['wikiSpanishHistorySha256']}`"
        if artifacts["wikiSpanishHistorySha256"] else "- Spanish Wiki history ZIP: not supplied.",
        "",
        "## Weapon and Commlink triage",
        "",
        f"- **{gaps['weaponMissingRuleDefinitions']}** Weapons lack a curated rule definition.",
        f"- **{gaps['weaponNamesSeenInWikiChartText']}** names occur as text in the",
        "  Wiki Weapon Chart's tables;",
        f"  **{gaps['weaponNamesNotSeenInWikiChartText']}** do not. These are",
        "  **candidate matches**, not profile-fact coverage.",
        "- Weapon profile storage and missing *rule definitions* are separate audit dimensions.",
        "- Commlink lacks a curated rule definition; a related Wiki page is available.",
        "  Historical N4 PDF availability and verified N5 authority are separate below.",
        "",
        *reinforcement_lines,
        "",
        "## Follow-up",
        "",
        "- Verify Weapon Chart rows, modes, ammunition, ranges, saves and Traits against the",
        "  core PDF pages 176–188 and published weapon profiles; review unmatched names/aliases.",
        "- Reconcile the FAQ v0.1 as its own publication and review scope for core/ITS questions.",
        "- Establish an N5-applicable Annex revision or explicit adoption ruling before",
        "  curating Commlink/Request Reinforcements separately as current N5 procedures.",
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
    parser.add_argument("--wiki-history-es", type=Path)
    parser.add_argument("--wiki-snapshot", type=Path)
    parser.add_argument("--wiki-snapshot-es", type=Path)
    parser.add_argument("--core-pdf", type=Path, required=True)
    parser.add_argument("--faq-pdf", type=Path, required=True)
    parser.add_argument("--reinforcements-inventory", type=Path, default=REINFORCEMENTS_INVENTORY)
    parser.add_argument("--faq-inventory", type=Path, default=FAQ_INVENTORY)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        result = build_report(
            args.army_db, args.rules_db, args.wiki_history, args.core_pdf, args.faq_pdf,
            args.wiki_snapshot, args.wiki_history_es, args.wiki_snapshot_es,
            args.reinforcements_inventory,
            args.faq_inventory,
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
