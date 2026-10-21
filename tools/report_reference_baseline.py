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

from infinity_army_data.merge import SourceDocument, load_sources
from infinity_db.application_domains import application_domain, semantic_record_domain
from infinity_db.database.paths import raw_database_path
from infinity_db.database.publication import validate_database_pair

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


_NESTED_SOURCE_FIELDS = {
    "profile_groups": (
        ("army_id", "unit_id", "group_id"),
        ("position", "category_id", "isc", "notes"),
    ),
    "profiles": (
        ("army_id", "unit_id", "group_id", "profile_id"),
        (
            "position", "name", "logo", "type_id", "move_1", "move_2",
            "cc", "bs", "ph", "wip", "arm", "bts", "vitality",
            "silhouette", "ava", "is_structure", "notes",
        ),
    ),
    "loadout_options": (
        ("army_id", "unit_id", "group_id", "option_id"),
        ("position", "name", "points", "swc", "minis", "disabled"),
    ),
}


def _verify_nested_source_rows(
    army: sqlite3.Connection, table: str, expected: list[tuple[Any, ...]]
) -> int:
    """Verify source-native keys, positions and scalar facts without reconstruction."""
    identity_columns, value_columns = _NESTED_SOURCE_FIELDS[table]
    columns = (*identity_columns, *value_columns)
    actual: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    for row in army.execute(f"SELECT {', '.join(columns)} FROM {table}"):
        key = tuple(row[:len(identity_columns)])
        if key in actual:
            raise ReferenceBaselineError(f"{table}: duplicate published identity {key!r}")
        actual[key] = tuple(row[len(identity_columns):])

    original: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    for row in expected:
        key = row[:len(identity_columns)]
        if key in original:
            raise ReferenceBaselineError(f"{table}: duplicate source identity {key!r}")
        original[key] = row[len(identity_columns):]

    missing = sorted(original.keys() - actual.keys())
    extra = sorted(actual.keys() - original.keys())
    if missing or extra:
        raise ReferenceBaselineError(
            f"{table} source identities differ from published storage: "
            f"missing={missing[:10]!r}, extra={extra[:10]!r}"
        )
    for key in sorted(original):
        if original[key] != actual[key]:
            columns_changed = [
                name for name, expected_value, actual_value
                in zip(value_columns, original[key], actual[key], strict=True)
                if expected_value != actual_value
            ]
            raise ReferenceBaselineError(
                f"{table} source facts differ at {key!r}: "
                f"fields={columns_changed!r}, expected={original[key]!r}, "
                f"actual={actual[key]!r}"
            )
    return len(original)


def _collect_source_profile_references(
    expected: dict[tuple[str, str], list[tuple[Any, ...]]],
    kind: str, parent: tuple[int, int, int, int], source: dict[str, Any],
) -> None:
    for field, source_field in (
        ("skills", "skills"), ("equipment", "equip"), ("weapons", "weapons"),
    ):
        for position, reference in enumerate(source.get(source_field) or [], start=1):
            if not isinstance(reference, dict):
                raise ReferenceBaselineError(
                    f"{kind}.{field} has non-object source occurrence at "
                    f"{parent!r}, position {position}"
                )
            expected[(kind, field)].append((
                *parent, position, reference.get("id"),
                reference.get("order"), reference.get("q"),
            ))


def _verify_published_profile_references(
    army: sqlite3.Connection,
    sources: list[SourceDocument],
) -> dict[str, int]:
    """Check source reference occurrences against the actual reusable payload views."""
    expected: dict[tuple[str, str], list[tuple[Any, ...]]] = {
        (kind, field): []
        for kind in ("profile", "loadout")
        for field in ("skills", "equipment", "weapons")
    }
    for source in sources:
        for unit in source.data["units"]:
            for group in unit.get("profileGroups") or []:
                parent = (source.faction_id, unit["id"], group["id"])
                for profile in group.get("profiles") or []:
                    _collect_source_profile_references(
                        expected, "profile", (*parent, profile["id"]), profile,
                    )
                for loadout in group.get("options") or []:
                    _collect_source_profile_references(
                        expected, "loadout", (*parent, loadout["id"]), loadout,
                    )
    result: dict[str, int] = {}
    for (kind, field), rows in sorted(expected.items()):
        payload_type = "profile" if kind == "profile" else "loadout"
        identity = "profile_id" if kind == "profile" else "option_id"
        occurrence_table = f"{payload_type}_payload_occurrences"
        reference_table = f"{payload_type}_payload_{field}"
        query = (
            f"SELECT o.army_id, o.unit_id, o.group_id, o.{identity}, "
            "r.position, r.item_id, r.display_order, r.quantity "
            f"FROM {occurrence_table} o JOIN {reference_table} r "
            f"ON r.{payload_type}_payload_id = o.{payload_type}_payload_id"
        )
        actual = [tuple(row) for row in army.execute(query)]
        source_by_key = {row[:5]: row[5:] for row in rows}
        published_by_key = {row[:5]: row[5:] for row in actual}
        if len(source_by_key) != len(rows) or len(published_by_key) != len(actual):
            raise ReferenceBaselineError(
                f"{kind}.{field}: duplicate source or published occurrence position"
            )
        missing = sorted(source_by_key.keys() - published_by_key.keys())
        extra = sorted(published_by_key.keys() - source_by_key.keys())
        if missing or extra:
            raise ReferenceBaselineError(
                f"{kind}.{field}: source/published reference identities differ: "
                f"missing={missing[:10]!r}, extra={extra[:10]!r}"
            )
        for key in sorted(source_by_key):
            if source_by_key[key] != published_by_key[key]:
                raise ReferenceBaselineError(
                    f"{kind}.{field}: published reference differs at {key!r}: "
                    f"source={source_by_key[key]!r}, published={published_by_key[key]!r}"
                )
        result[f"{kind}.{field}"] = len(rows)
    return result


def _verify_army_archive_sources(
    archive: Path, metadata: dict[str, Any], army: sqlite3.Connection,
    raw_army: sqlite3.Connection | None = None,
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
    stored = {
        int(row[0]): {
            "version": row[1], "kind": row[2],
            "source_file": row[3], "source_sha256": row[4],
        }
        for row in army.execute(
            "SELECT id, version, kind, source_file, source_sha256 FROM army_lists"
        )
    }
    stored_ids = set(stored)
    if source_ids != stored_ids:
        raise ReferenceBaselineError(
            f"Published Army list identities differ from the source archive: "
            f"missing={sorted(source_ids - stored_ids)!r}, "
            f"extra={sorted(stored_ids - source_ids)!r}"
        )
    expected_memberships: list[tuple[int, int, int]] = []
    expected_nested: dict[str, list[tuple[Any, ...]]] = {
        table: [] for table in _NESTED_SOURCE_FIELDS
    }
    for source in sources:
        fields = {
            "version": source.data["version"],
            "kind": "army" if "reinforcements" in source.data else "reinforcement",
            "source_file": source.filename,
            "source_sha256": source.sha256,
        }
        if stored[source.faction_id] != fields:
            raise ReferenceBaselineError(
                f"Army {source.faction_id} published source provenance differs "
                f"from the archived source: expected {fields!r}, "
                f"actual {stored[source.faction_id]!r}"
            )
        unit_ids: set[int] = set()
        for position, unit in enumerate(source.data["units"], start=1):
            unit_id = unit.get("id") if isinstance(unit, dict) else None
            if type(unit_id) is not int or unit_id in unit_ids:
                raise ReferenceBaselineError(
                    f"Army {source.faction_id} has invalid or duplicate "
                    f"source Unit ID at position {position}: {unit_id!r}"
                )
            unit_ids.add(unit_id)
            expected_memberships.append((source.faction_id, unit_id, position))
            for group_position, group in enumerate(
                unit.get("profileGroups") or [], start=1
            ):
                group_id = group.get("id")
                if type(group_id) is not int:
                    raise ReferenceBaselineError(
                        f"Army {source.faction_id} Unit {unit_id} has "
                        f"invalid profile group identity {group_id!r}"
                    )
                parent = (source.faction_id, unit_id, group_id)
                expected_nested["profile_groups"].append((
                    *parent, group_position, group.get("category"),
                    group.get("isc"), group.get("notes"),
                ))
                for profile_position, profile in enumerate(
                    group.get("profiles") or [], start=1
                ):
                    profile_id = profile.get("id")
                    if type(profile_id) is not int:
                        raise ReferenceBaselineError(
                            f"Army {source.faction_id} Unit {unit_id} group {group_id} "
                            f"has invalid profile identity {profile_id!r}"
                        )
                    move = profile.get("move") or []
                    expected_nested["profiles"].append((
                        *parent, profile_id, profile_position,
                        profile.get("name"), profile.get("logo"), profile.get("type"),
                        move[0] if len(move) > 0 else None,
                        move[1] if len(move) > 1 else None,
                        profile.get("cc"), profile.get("bs"), profile.get("ph"),
                        profile.get("wip"), profile.get("arm"), profile.get("bts"),
                        profile.get("w"), profile.get("s"), profile.get("ava"),
                        profile.get("str"), profile.get("notes"),
                    ))
                for option_position, option in enumerate(
                    group.get("options") or [], start=1
                ):
                    option_id = option.get("id")
                    if type(option_id) is not int:
                        raise ReferenceBaselineError(
                            f"Army {source.faction_id} Unit {unit_id} group {group_id} "
                            f"has invalid loadout identity {option_id!r}"
                        )
                    expected_nested["loadout_options"].append((
                        *parent, option_id, option_position,
                        option.get("name"), option.get("points"), option.get("swc"),
                        option.get("minis"), option.get("disabled"),
                    ))
    published_memberships = [
        (int(row[0]), int(row[1]), int(row[2]))
        for row in army.execute(
            "SELECT army_id, unit_id, position FROM army_units "
            "ORDER BY army_id, position, unit_id"
        )
    ]
    expected_memberships.sort()
    published_memberships.sort()
    if expected_memberships != published_memberships:
        expected_set = set(expected_memberships)
        published_set = set(published_memberships)
        raise ReferenceBaselineError(
            "Published Army Unit memberships/positions differ from raw source: "
            f"missing={sorted(expected_set - published_set)[:10]!r}, "
            f"extra={sorted(published_set - expected_set)[:10]!r}"
        )
    nested_counts = {
        table: _verify_nested_source_rows(
            army if table == "profile_groups" else (raw_army or army),
            table, rows,
        )
        for table, rows in expected_nested.items()
    }
    return {
        "status": "source-identities-match-published-army-lists",
        "archiveJsonDocuments": len(sources) + len(skipped),
        "sourceFileCount": len(sources),
        "sourceVersions": versions,
        "matchedArmyListIds": len(source_ids),
        "matchedSourceProvenanceRows": len(sources),
        "matchedUnitMembershipOccurrences": len(expected_memberships),
        "matchedNestedSourceRows": nested_counts,
        "nestedStorage": {
            "profile_groups": "published-infinity.db",
            "profiles": "paired-infinity.raw.db",
            "loadout_options": "paired-infinity.raw.db",
        },
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
            raw_path = raw_database_path(army_database)
            try:
                validate_database_pair(army_database, raw_path=raw_path)
            except ValueError as exc:
                raise ReferenceBaselineError(
                    f"Published Army/raw source database pair is invalid: {exc}"
                ) from exc
            with closing(_connect(raw_path)) as raw_connection:
                archive_evidence = _verify_army_archive_sources(
                    army_archive, raw_army, army, raw_connection,
                )
                sources, _ = load_sources(army_archive)
                archive_evidence["matchedPublishedReferences"] = (
                    _verify_published_profile_references(army, sources)
                )
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
             "published Army-list IDs with matching version counts, "
             f"{snapshot['sourceIdentityEvidence']['matchedSourceProvenanceRows']} "
             "matched per-file provenance records and "
             f"{snapshot['sourceIdentityEvidence']['matchedUnitMembershipOccurrences']} "
             "ordered Unit membership occurrences."]
            if snapshot.get("sourceIdentityEvidence") else []
        ),
        *(
            [f"- Nested Army source row parity: "
             f"{snapshot['sourceIdentityEvidence']['matchedNestedSourceRows']['profile_groups']} "
             "profile groups in published infinity.db; "
             f"{snapshot['sourceIdentityEvidence']['matchedNestedSourceRows']['profiles']} "
             "profiles and "
             f"{snapshot['sourceIdentityEvidence']['matchedNestedSourceRows']['loadout_options']} "
             "loadouts in export-paired infinity.raw.db. "
             "Derived runtime payloads and browser presentation remain unverified."]
            if (snapshot.get("sourceIdentityEvidence") or {}).get("matchedNestedSourceRows")
            else []
        ),
        *(
            ["- Published profile/loadout Skill, Equipment and Weapon occurrences: "
             + ", ".join(
                 f"{name}={count}"
                 for name, count in sorted(
                     snapshot["sourceIdentityEvidence"]["matchedPublishedReferences"].items()
                 )
             )
             + " (source ID, position, display order and quantity; "
             "not nested extras or browser rendering)."]
            if (snapshot.get("sourceIdentityEvidence") or {}).get("matchedPublishedReferences")
            else []
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
