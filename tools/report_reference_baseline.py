#!/usr/bin/env python3
"""Report 1.0 source/publication evidence without declaring reference completeness.

This is a read-only cross-source inventory, not a new coverage classification
policy. Source-to-API/browser decisions must be reviewed against the pinned inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path, PureWindowsPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_FORMAT = "InfinityDB 1.0 reference evidence baseline"
REPORT_VERSION = 1


class ReferenceBaselineError(ValueError):
    """The supplied published data cannot provide a trustworthy baseline."""


def _connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ReferenceBaselineError(f"Published database is unavailable: {path}")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _metadata(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    try:
        rows = connection.execute(f'SELECT key, value FROM "{table}"').fetchall()
    except sqlite3.DatabaseError as exc:
        raise ReferenceBaselineError(f"Missing or unreadable {table}: {exc}") from exc
    try:
        return {row["key"]: json.loads(row["value"]) for row in rows}
    except (json.JSONDecodeError, TypeError) as exc:
        raise ReferenceBaselineError(f"Invalid JSON in {table}: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_location(root: Path, relative: str | None) -> str:
    if relative is None:
        return "url-backed/no-local-artifact"
    candidate = Path(relative)
    if (
        candidate.is_absolute()
        or PureWindowsPath(relative).is_absolute()
        or ".." in candidate.parts
    ):
        return "unsafe-declared-path"
    return "available" if (root / candidate).is_file() else "missing-local-artifact"


def _row(
    key: str,
    source: str,
    canonical: str,
    maintained: str,
    database: str,
    count: int,
    *,
    citations: int | None = None,
) -> dict[str, Any]:
    return {
        "id": key,
        "source": source,
        "canonicalIdentity": canonical,
        "maintainedInput": maintained,
        "generatedStorage": database,
        "publishedRows": count,
        "rowsWithCitations": citations,
        "apiReadPath": None,
        "browserEntryPoint": None,
        "rulesContext": None,
        "factCoverage": "not-reviewed-against-source",
        "relationshipCoverage": "not-reviewed",
        "presentationCoverage": "not-reviewed",
        "scopeDecision": "pending",
    }


def build_baseline(
    army_database: Path,
    rules_database: Path,
    *,
    root: Path = PROJECT_ROOT,
    army_archive: Path | None = None,
) -> dict[str, Any]:
    """Inventory published identities; intentionally make no completeness claims."""
    with (
        closing(_connect(army_database)) as army,
        closing(_connect(rules_database)) as rules,
    ):
        army_meta = _metadata(army, "__infinity_metadata")
        rules_meta = _metadata(rules, "__rules_metadata")
        raw_army = army_meta.get("_meta")
        if not isinstance(raw_army, dict):
            raise ReferenceBaselineError("Army publication lacks normalized source metadata")
        archive_sha = raw_army.get("snapshotArchiveSha256")
        if not isinstance(archive_sha, str) or len(archive_sha) != 64:
            raise ReferenceBaselineError("Army publication lacks a pinned archive SHA-256")
        if army_archive is None:
            archive_status = "not-supplied"
        else:
            if not army_archive.is_file():
                raise ReferenceBaselineError(f"Army archive is unavailable: {army_archive}")
            if _sha256(army_archive) != archive_sha:
                raise ReferenceBaselineError("Army archive SHA-256 differs from published metadata")
            archive_status = "hash-verified"

        source_groups: dict[tuple[str, str | None], dict[str, Any]] = {}
        try:
            source_records = rules.execute(
                "SELECT collection_id, id, kind, title, version, published_date, "
                "retrieved_date, acquired_at, local_path, url, sha256 "
                "FROM sources ORDER BY kind, version, local_path, collection_id, id"
            ).fetchall()
            collections = [dict(x) for x in rules.execute(
                "SELECT id, title, domain, status, effective_from "
                "FROM collections ORDER BY id"
            )]
        except sqlite3.DatabaseError as exc:
            raise ReferenceBaselineError(f"Rules source catalog is unreadable: {exc}") from exc
        for record in source_records:
            group_key = (record["kind"], record["local_path"])
            if group_key not in source_groups:
                source_groups[group_key] = {
                    "kind": record["kind"],
                    "versions": set(),
                    "localPath": record["local_path"],
                    "localStatus": _source_location(root, record["local_path"]),
                    "sourceRows": 0,
                    "sourceIds": set(),
                    "collections": set(),
                    "declaredSha256": set(),
                }
            group = source_groups[group_key]
            group["sourceRows"] += 1
            group["versions"].add(record["version"])
            group["sourceIds"].add(record["id"])
            group["collections"].add(record["collection_id"])
            if record["sha256"]:
                group["declaredSha256"].add(record["sha256"])

        source_inventory = [dict(row) for row in source_records]
        sources = []
        for group in source_groups.values():
            sources.append({
                **{k: v for k, v in group.items() if k not in
                   {"sourceIds", "collections", "declaredSha256", "versions"}},
                "uniqueSourceIds": len(group["sourceIds"]),
                "versions": sorted(group["versions"]),
                "collections": sorted(group["collections"]),
                "declaredSha256": sorted(group["declaredSha256"]),
            })

        evidence_rows: list[dict[str, Any]] = []
        army_families = (
            ("armies", "army_lists"),
            ("units", "logical_units"),
            ("profiles", "profile_payloads"),
            ("loadouts", "loadout_payloads"),
            ("fireteams", "application_fireteams"),
            ("peripherals", "application_peripheral_entities"),
        )
        try:
            for category, table in army_families:
                count = army.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                evidence_rows.append(_row(
                    f"army:{category}", "Infinity Army snapshot", table,
                    "pinned Army snapshot + reviewed identity configuration",
                    f"infinity.db::{table}", count,
                ))
            catalogs = army.execute(
                "SELECT catalog, COUNT(*) AS count FROM application_catalog_items "
                "GROUP BY catalog ORDER BY catalog"
            ).fetchall()
            for catalog in catalogs:
                evidence_rows.append(_row(
                    f"army:catalog:{catalog['catalog']}", "Infinity Army snapshot",
                    f"application catalog {catalog['catalog']}",
                    "pinned Army snapshot + reviewed catalog configuration",
                    "infinity.db::application_catalog_items", catalog["count"],
                ))
            records = rules.execute(
                "SELECT r.kind AS kind, COUNT(*) AS count, "
                "SUM(CASE WHEN EXISTS (SELECT 1 FROM record_citations AS c "
                "WHERE c.collection_id = r.collection_id "
                "AND c.record_id = r.id) THEN 1 ELSE 0 END) AS cited "
                "FROM records AS r GROUP BY r.kind ORDER BY r.kind"
            ).fetchall()
            for item in records:
                evidence_rows.append(_row(
                    f"rules:{item['kind']}", "Curated N5 rules and wiki evidence",
                    f"rules record kind {item['kind']}", "data/curated/rules/",
                    "rules.db::records", item["count"], citations=item["cited"],
                ))
            scenario_count = rules.execute(
                "SELECT COUNT(*) FROM scenario_memberships"
            ).fetchone()[0]
        except sqlite3.DatabaseError as exc:
            raise ReferenceBaselineError(f"Published catalog is unreadable: {exc}") from exc

    return {
        "format": REPORT_FORMAT,
        "formatVersion": REPORT_VERSION,
        "status": "initial-evidence-only-not-a-completeness-verdict",
        "armySnapshot": {
            "archiveSha256": archive_sha,
            "publishedDatabaseSha256": _sha256(army_database),
            "archiveVerification": archive_status,
            "sourceFileCount": raw_army.get("sourceFileCount"),
            "sourceVersions": raw_army.get("sourceVersions"),
            "sourceDataChangedOn": raw_army.get("sourceDataChangedOn"),
            "snapshotDownloadedOn": raw_army.get("snapshotDownloadedOn"),
        },
        "rulesPublication": {
            "publishedDatabaseSha256": _sha256(rules_database),
            "metadata": rules_meta, "collections": collections,
        },
        "sourceGroups": sources,
        "sourceInventory": source_inventory,
        "scenarioMembershipCount": scenario_count,
        "inventory": evidence_rows,
        "remainingEvidence": [
            "Confirm source archive hashes, publication identities, and PDF/wiki local inputs",
            "Review official PDF/FAQ/annex sections and wiki material against record families",
            "Reconcile source semantics and rule relationships, not just record counts",
            "Check normal API/browser paths and rules context for each inventory row",
            "Reconcile existing Army source-presentation, enrichment, "
            "and interaction audits",
            "Classify every concrete gap with a scope decision and owning 1.0 task",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    snapshot = report["armySnapshot"]
    lines = [
        "# 1.0 current-reference baseline (initial evidence)",
        "",
        "**Status: not a completeness verdict.** Counts prove only published rows; "
        "citations prove only citation presence. Source facts, relations, scope, and "
        "normal browser access still require review.",
        "",
        "## Published source identities",
        "",
        f"- Army: {snapshot['sourceFileCount']} source documents; "
        f"versions `{json.dumps(snapshot['sourceVersions'], sort_keys=True)}`; "
        f"archive SHA-256 `{snapshot['archiveSha256']}` "
        f"({snapshot['archiveVerification']}).",
        f"- Published Army database SHA-256: `{snapshot['publishedDatabaseSha256']}`.",
        f"- Published rules database SHA-256: "
        f"`{report['rulesPublication']['publishedDatabaseSha256']}`.",
        f"- Army source data changed: {snapshot['sourceDataChangedOn']}; "
        f"snapshot acquired: {snapshot['snapshotDownloadedOn']} "
        "(separate from publication dates).",
        "- Rules collections: " + ", ".join(
            f"`{item['id']}` ({item['status']})"
            for item in report["rulesPublication"]["collections"]
        ) + ".",
        f"- Published scenario collection memberships: {report['scenarioMembershipCount']}.",
        "",
        "## Source artifacts referenced by rules publication",
        "",
        "| Kind | Version | Curated source rows | Local path | Availability |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for source in report["sourceGroups"]:
        versions = source["versions"]
        version_label = versions[0] if len(versions) == 1 else f"{len(versions)} versions"
        lines.append(
            f"| {source['kind']} | {version_label} | {source['sourceRows']} | "
            f"`{source['localPath'] or 'URL-backed entries'}` | "
            f"{source['localStatus']} |"
        )
    lines.extend([
        "",
        "The current source table is not an exhaustive publication inventory: "
        "FAQ/errata and annex scope must be reconciled separately.",
        "",
        "A curated source SHA may identify a logical archive/snapshot, not the exact "
        "file bytes. Availability alone does not verify any source's identity.",
        "",
        "## Published category inventory (verification pending)",
        "",
        "| Source/category | Canonical identity | Maintained input | Storage | Rows | "
        "Cited | API / browser / rules context |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ])
    for item in report["inventory"]:
        cited = item["rowsWithCitations"]
        lines.append(
            f"| `{item['id']}` | `{item['canonicalIdentity']}` | "
            f"{item['maintainedInput']} | `{item['generatedStorage']}` | "
            f"{item['publishedRows']} | {cited if cited is not None else '—'} | "
            "not audited |"
        )
    lines.extend(["", "## Outstanding 1.0 evidence", ""])
    lines.extend(f"- [ ] {item}." for item in report["remainingEvidence"])
    lines.extend([
        "",
        "This baseline is a starting inventory; it does not replace "
        "`audit_source_presentation.py`, `audit_enrichment_coverage.py`, "
        "or `audit_rules_interactions.py`. Missing sources and unreviewed browser "
        "paths must not be interpreted as either completeness or confirmed defects.",
        "",
    ])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=REPORT_FORMAT)
    parser.add_argument("--army-db", type=Path, default=PROJECT_ROOT / "data/generated/infinity.db")
    parser.add_argument("--rules-db", type=Path, default=PROJECT_ROOT / "data/generated/rules.db")
    parser.add_argument("--army-archive", type=Path, help="Verify exact ZIP bytes against Army pin")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)
    report = build_baseline(
        args.army_db, args.rules_db, army_archive=args.army_archive,
    )
    for path, content in (
        (args.json_output, json.dumps(report, indent=2, sort_keys=True) + "\n"),
        (args.markdown_output, render_markdown(report)),
    ):
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print(f"{REPORT_FORMAT}: {len(report['inventory'])} category rows, "
          f"{len(report['sourceGroups'])} source groups; all require review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
