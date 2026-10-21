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
import sys
from collections import Counter
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from infinity_army_data.merge import load_sources
from infinity_db.application_domains import application_domain, semantic_record_domain

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_FORMAT = "InfinityDB 1.0 reference evidence baseline"
REPORT_VERSION = 2


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
        or bool(PureWindowsPath(relative).drive)
        or ".." in candidate.parts
        or ".." in PureWindowsPath(relative).parts
        or not (root / candidate).resolve().is_relative_to(root.resolve())
    ):
        return "unsafe-declared-path"
    return "available" if (root / candidate).is_file() else "missing-local-artifact"


def _verify_army_archive_sources(
    archive: Path, metadata: dict[str, Any], army: sqlite3.Connection
) -> dict[str, Any]:
    """Match individual raw Army source identities to the published list rows.

    The enclosing caller verifies the archive SHA-256 first. This check only
    certifies IDs, source version counts and document cardinality, not the
    contents of every source field.
    """
    try:
        sources, skipped = load_sources(archive)
    except (OSError, ValueError) as exc:
        raise ReferenceBaselineError(f"Army archive cannot be parsed: {exc}") from exc

    if sorted(skipped) != ["metadata.json"]:
        raise ReferenceBaselineError(
            f"Army archive expected one metadata.json document, got {sorted(skipped)!r}"
        )
    declared_count = metadata.get("sourceFileCount")
    if type(declared_count) is not int or len(sources) != declared_count:
        raise ReferenceBaselineError(
            f"Army source count differs from published metadata: "
            f"{len(sources)} != {declared_count!r}"
        )
    versions = dict(sorted(Counter(str(s.data.get("version")) for s in sources).items()))
    if any(s.data.get("version") is None for s in sources):
        raise ReferenceBaselineError("Army source archive contains a missing version")
    if versions != metadata.get("sourceVersions"):
        raise ReferenceBaselineError(
            f"Army source versions differ from published metadata: "
            f"{versions!r} != {metadata.get('sourceVersions')!r}"
        )
    source_ids = {s.faction_id for s in sources}
    stored_ids = {int(row[0]) for row in army.execute("SELECT id FROM army_lists")}
    if source_ids != stored_ids:
        raise ReferenceBaselineError(
            f"Published Army list identities differ from the source archive: "
            f"missing={sorted(source_ids - stored_ids)!r}, "
            f"extra={sorted(stored_ids - source_ids)!r}"
        )
    return {
        "status": "source-identities-match-published-army-lists",
        "archiveJsonDocuments": len(sources) + len(skipped),
        "sourceFileCount": len(sources),
        "sourceVersions": versions,
        "matchedArmyListIds": len(source_ids),
    }


def _revision_oldid(url: str | None) -> str | None:
    """Identify an exact Wiki oldid pin without accessing the network."""
    if not url:
        return None
    values = parse_qs(urlsplit(url).query).get("oldid", [])
    if len(values) == 1 and values[0].isascii() and values[0].isdigit():
        return values[0]
    return None


def _artifact_evidence(
    root: Path, local_path: str | None, url: str | None, hashes: set[str]
) -> dict[str, Any]:
    """Compare exact local bytes when possible; never equate an oldid URL with a file."""
    location = _source_location(root, local_path)
    actual_sha: str | None = None
    matches: bool | None = None
    oldid = _revision_oldid(url) if local_path is None else None
    if location == "available" and local_path is not None:
        actual_sha = _sha256(root / local_path)
        if len(hashes) > 1:
            status = "conflicting-source-hashes"
        elif hashes:
            matches = actual_sha in hashes
            status = "hash-matched" if matches else "hash-mismatch-needs-review"
        else:
            status = "local-file-no-hash-pin"
    elif location == "url-backed/no-local-artifact":
        status = "revision-url-pinned" if oldid else "url-without-revision-pin"
    else:
        status = location
    return {
        "verificationStatus": status,
        "artifactSha256": actual_sha,
        "declaredHashMatches": matches,
        "revisionOldid": oldid,
    }


def _route_hint(key: str) -> dict[str, str] | None:
    """Locate an existing discovery surface, without asserting per-row coverage."""

    if key in {"army:profiles", "army:loadouts"}:
        return {
            "mode": "nested-unit",
            "browser": "/units/:id",
            "api": "/api/units/:id",
        }

    if key.startswith("army:catalog:"):
        domain_slug = key.removeprefix("army:catalog:")
    elif key in {"army:armies", "army:units", "army:fireteams"}:
        domain_slug = key.removeprefix("army:")
    elif key.startswith("rules:"):
        domain = semantic_record_domain(key.removeprefix("rules:"))
        if domain is None:
            return None
        domain_slug = domain.slug
    else:
        return None

    try:
        domain = application_domain(domain_slug)
    except ValueError:
        return None
    if not domain.published:
        return None
    if domain.route is None:
        if domain.glossary:
            return {"mode": "embedded-glossary", "browser": "/glossary", "api": "/api/glossary"}
        return None
    mode = "nested-scoped" if domain.scoped else domain.presentation
    return {
        "mode": mode,
        "browser": domain.route,
        "api": f"/api/{domain.slug}",
    }


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
        "routeHint": _route_hint(key),
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
        archive_evidence: dict[str, Any] | None = None
        if army_archive is None:
            archive_status = "not-supplied"
        else:
            if not army_archive.is_file():
                raise ReferenceBaselineError(f"Army archive is unavailable: {army_archive}")
            if _sha256(army_archive) != archive_sha:
                raise ReferenceBaselineError("Army archive SHA-256 differs from published metadata")
            archive_evidence = _verify_army_archive_sources(army_archive, raw_army, army)
            archive_status = "hash-verified-source-identities"

        # Each URL revision is a separate source identity. Only a genuinely shared
        # local archive should be aggregated across curated collections.
        source_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
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
            locator_type = "file" if record["local_path"] else "url"
            locator = record["local_path"] or record["url"] or record["id"]
            group_key = (record["kind"], locator_type, locator)
            if group_key not in source_groups:
                source_groups[group_key] = {
                    "kind": record["kind"],
                    "versions": set(),
                    "localPath": record["local_path"],
                    "url": record["url"] if locator_type == "url" else None,
                    "localStatus": _source_location(root, record["local_path"]),
                    "sourceRows": 0,
                    "sourceIds": set(),
                    "titles": set(),
                    "collections": set(),
                    "publishedDates": set(),
                    "retrievedDates": set(),
                    "acquiredAt": set(),
                    "declaredSha256": set(),
                }
            group = source_groups[group_key]
            group["sourceRows"] += 1
            group["versions"].add(record["version"])
            group["sourceIds"].add(record["id"])
            group["titles"].add(record["title"])
            group["collections"].add(record["collection_id"])
            for field, column in (
                ("publishedDates", "published_date"),
                ("retrievedDates", "retrieved_date"),
                ("acquiredAt", "acquired_at"),
            ):
                if record[column]:
                    group[field].add(record[column])
            if record["sha256"]:
                group["declaredSha256"].add(record["sha256"])

        source_inventory = [dict(row) for row in source_records]
        sources = []
        for group in source_groups.values():
            hashes = group["declaredSha256"]
            sources.append({
                **{k: v for k, v in group.items() if k not in
                   {"sourceIds", "titles", "collections", "declaredSha256", "versions",
                    "publishedDates", "retrievedDates", "acquiredAt"}},
                "uniqueSourceIds": len(group["sourceIds"]),
                "titles": sorted(group["titles"]),
                "versions": sorted(group["versions"]),
                "collections": sorted(group["collections"]),
                "publishedDates": sorted(group["publishedDates"]),
                "retrievedDates": sorted(group["retrievedDates"]),
                "acquiredAt": sorted(group["acquiredAt"]),
                "declaredSha256": sorted(hashes),
                **_artifact_evidence(root, group["localPath"], group["url"], hashes),
            })
        verification_counts: dict[str, int] = {}
        for source in sources:
            status = source["verificationStatus"]
            verification_counts[status] = verification_counts.get(status, 0) + 1

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
            scenario_memberships = [
                {
                    "collectionId": row["collection_id"],
                    "collectionRevision": row["collection_revision"],
                    "position": row["position"],
                    "scenarioId": row["scenario_id"],
                    "publicationCollectionId": row["publication_collection_id"],
                }
                for row in rules.execute(
                    "SELECT collection_id, collection_revision, position, "
                    "scenario_id, publication_collection_id "
                    "FROM scenario_memberships "
                    "ORDER BY collection_id, collection_revision, position"
                )
            ]
        except sqlite3.DatabaseError as exc:
            raise ReferenceBaselineError(f"Published catalog is unreadable: {exc}") from exc

    # The runtime publishes SHA256("<army database sha>:<rules database sha>").
    # Preserve the exact pair used by the release evidence, rather than merely
    # comparing source archive or individual database hashes independently.
    army_sha = _sha256(army_database)
    rules_sha = _sha256(rules_database)
    runtime_revision = hashlib.sha256(f"{army_sha}:{rules_sha}".encode()).hexdigest()
    return {
        "format": REPORT_FORMAT,
        "formatVersion": REPORT_VERSION,
        "status": "initial-evidence-only-not-a-completeness-verdict",
        "runtimeSnapshotRevision": runtime_revision,
        "armySnapshot": {
            "archiveSha256": archive_sha,
            "publishedDatabaseSha256": army_sha,
            "archiveVerification": archive_status,
            "sourceIdentityEvidence": archive_evidence,
            "sourceFileCount": raw_army.get("sourceFileCount"),
            "sourceVersions": raw_army.get("sourceVersions"),
            "sourceDataChangedOn": raw_army.get("sourceDataChangedOn"),
            "snapshotDownloadedOn": raw_army.get("snapshotDownloadedOn"),
        },
        "rulesPublication": {
            "publishedDatabaseSha256": rules_sha,
            "metadata": rules_meta, "collections": collections,
        },
        "sourceGroups": sources,
        "sourceVerificationCounts": dict(sorted(verification_counts.items())),
        "sourceInventory": source_inventory,
        "scenarioMembershipCount": len(scenario_memberships),
        "scenarioMemberships": scenario_memberships,
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


def verify_served_revision(report: dict[str, Any], base_url: str) -> dict[str, str]:
    """Require the running server to publish exactly the inventoried database pair.

    This validates the immutable database bytes used by the app; it does not
    verify external source artifacts, rules semantics, or browser rendering.
    """
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ReferenceBaselineError(
            "Server base URL must be an HTTP(S) origin without credentials, path or query"
        )
    version_url = base_url.rstrip("/") + "/api/version"
    try:
        request = Request(version_url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise ReferenceBaselineError(
                    f"Runtime version endpoint returned HTTP {response.status}"
                )
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise ReferenceBaselineError(f"Could not verify runtime version: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReferenceBaselineError("Runtime version endpoint did not return an object")
    actual = payload.get("snapshot_revision")
    expected = report["runtimeSnapshotRevision"]
    if not isinstance(actual, str) or actual != expected:
        raise ReferenceBaselineError(
            f"Runtime snapshot revision does not match inventoried databases: "
            f"expected {expected}, received {actual!r}"
        )
    return {
        "versionUrl": version_url,
        "snapshotRevision": actual,
        "appVersion": str(payload.get("version", "")),
        "staticRevision": str(payload.get("static_revision", "")),
        "status": "exact-database-pair-match-not-source-completeness",
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
        *(
            [f"- Verified Army source identities: "
             f"{snapshot['sourceIdentityEvidence']['archiveJsonDocuments']} archive JSON documents "
             f"(including metadata.json), "
             f"{snapshot['sourceIdentityEvidence']['matchedArmyListIds']} matched "
             "published Army-list IDs with matching version counts."]
            if snapshot.get("sourceIdentityEvidence") else []
        ),
        f"- Published Army database SHA-256: `{snapshot['publishedDatabaseSha256']}`.",
        f"- Published rules database SHA-256: "
        f"`{report['rulesPublication']['publishedDatabaseSha256']}`.",
        f"- Combined runtime snapshot revision: `{report['runtimeSnapshotRevision']}` "
        "(exact published Army + rules database bytes; not source completeness).",
        *(
            [f"- Served runtime: {report['servedSnapshot']['status']} "
             f"at `{report['servedSnapshot']['versionUrl']}`."]
            if report.get("servedSnapshot") else []
        ),
        f"- Army source data changed: {snapshot['sourceDataChangedOn']}; "
        f"snapshot acquired: {snapshot['snapshotDownloadedOn']} "
        "(separate from publication dates).",
        "- Rules collections: " + ", ".join(
            f"`{item['id']}` ({item['status']})"
            for item in report["rulesPublication"]["collections"]
        ) + ".",
        f"- Published scenario collection memberships: {report['scenarioMembershipCount']} "
        "(all collections; not just core missions).",
        "- Source evidence statuses: " + ", ".join(
            f"{count} {status}"
            for status, count in report["sourceVerificationCounts"].items()
        ) + ".",
        "",
        "## Published scenario memberships by collection",
        "",
        "These are source-scoped membership facts, **not a core-only scenario count "
        "or a browser-completeness verdict**. ITS memberships remain separate "
        "from the N5 core mission scope.",
        "",
        "| Collection | Revision | Position | Scenario ID | Source collection |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for membership in report["scenarioMemberships"]:
        lines.append(
            f"| `{membership['collectionId']}` | "
            f"`{membership['collectionRevision']}` | "
            f"{membership['position']} | `{membership['scenarioId']}` | "
            f"`{membership['publicationCollectionId']}` |"
        )
    lines.extend([
        "",
        "## Source artifacts referenced by rules publication",
        "",
        "| Kind | Version | Curated rows | Source identity | Evidence |",
        "| --- | --- | ---: | --- | --- |",
    ])
    for source in report["sourceGroups"]:
        versions = source["versions"]
        version_label = versions[0] if len(versions) == 1 else f"{len(versions)} versions"
        if source["localPath"] is not None:
            locator = f"`{source['localPath']}`"
        else:
            title = source["titles"][0]
            locator = f"[{title}]({source['url']})" if source["url"] else title
            if source["revisionOldid"]:
                locator += f" (`oldid={source['revisionOldid']}`)"
        escaped_locator = locator.replace("|", "\\|")
        lines.append(
            f"| {source['kind']} | {version_label} | {source['sourceRows']} | "
            f"{escaped_locator} | {source['verificationStatus']} |"
        )
    lines.extend([
        "",
        "The complete source inventory JSON retains individual collection/source IDs, "
        "publication and acquisition dates, declared SHA-256 values, and URLs. "
        "The report does not fetch URLs or reinterpret acquisition dates as publication dates.",
        "",
        "The current source table is not an exhaustive publication inventory: "
        "FAQ/errata and annex scope must be reconciled separately.",
        "",
        "A local hash match checks exact file bytes against the declared SHA-256, "
        "but does not verify the source contents. A mismatch may mean a logical "
        "rather than byte-level hash pin and requires review. URL `oldid=` pins "
        "identify revisions, not offline content verification. A local PDF without "
        "a declared SHA-256 cannot be hash-verified.",
        "",
        "## Published category inventory (verification pending)",
        "",
        "Route hints identify possible *starting surfaces* from the current "
        "application-domain registry. They are not source-to-API parity or "
        "browser-acceptance evidence: nested Unit data, embedded Glossary "
        "vocabularies, scoped references and curated Weapons may not have "
        "one direct page per source row.",
        "",
        "| Source/category | Canonical identity | Maintained input | Storage | Rows | "
        "Cited | Candidate browser / API | Review |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ])
    for item in report["inventory"]:
        cited = item["rowsWithCitations"]
        hint = item["routeHint"]
        candidate = (
            f"`{hint['browser']}` / `{hint['api']}` ({hint['mode']}; unverified)"
            if hint else "not identified"
        )
        lines.append(
            f"| `{item['id']}` | `{item['canonicalIdentity']}` | "
            f"{item['maintainedInput']} | `{item['generatedStorage']}` | "
            f"{item['publishedRows']} | {cited if cited is not None else '—'} | "
            f"{candidate} | pending source/API/browser review |"
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
    parser.add_argument(
        "--verify-server", metavar="BASE_URL",
        help="Check that the server uses this exact Army/rules database pair",
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)
    report = build_baseline(
        args.army_db, args.rules_db, army_archive=args.army_archive,
    )
    if args.verify_server:
        try:
            report["servedSnapshot"] = verify_served_revision(report, args.verify_server)
        except ReferenceBaselineError as exc:
            print(f"Release snapshot mismatch: {exc}", file=sys.stderr)
            return 1
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
