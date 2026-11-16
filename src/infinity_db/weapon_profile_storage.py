"""Relational storage for reviewed, source-pinned Weapon Chart profile citations.

The curated JSON remains a build input; no JSON sidecar is needed to read
citations from this model. A named mode and an unqualified mode have distinct,
non-null SQL identities.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .database.repository import Database
from .weapon_profile_publication import (
    PROFILE_CITATION_SCOPE,
    ProfileCitations,
    file_sha256,
    profile_sha256,
)

WEAPON_CITATION_SCHEMA_VERSION = 12
WEAPON_CITATION_COMPATIBILITY_VERSION = 14
_HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SCHEMA = (
    """CREATE TABLE weapon_chart_profile_metadata (
        id INTEGER PRIMARY KEY CHECK(id=1),
        army_database_sha256 TEXT NOT NULL CHECK(length(army_database_sha256)=64),
        reviews_sha256 TEXT NOT NULL CHECK(length(reviews_sha256)=64),
        source_collection_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        page_start INTEGER NOT NULL CHECK(page_start>0),
        page_end INTEGER NOT NULL CHECK(page_end>=page_start),
        weapon_count INTEGER NOT NULL CHECK(weapon_count>0),
        profile_count INTEGER NOT NULL CHECK(profile_count>0),
        content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
        FOREIGN KEY(source_collection_id,source_id)
            REFERENCES sources(collection_id,id)
    )""",
    """CREATE TABLE weapon_chart_profile_citations (
        weapon_id INTEGER NOT NULL CHECK(weapon_id>0),
        source_profile_id INTEGER NOT NULL CHECK(source_profile_id>0),
        mode_key TEXT NOT NULL CHECK(mode_key='' OR
            (substr(mode_key,1,5)='mode:' AND length(mode_key)>5)),
        weapon_slug TEXT NOT NULL CHECK(length(weapon_slug)>0),
        weapon_name TEXT NOT NULL CHECK(length(weapon_name)>0),
        profile_sha256 TEXT NOT NULL CHECK(length(profile_sha256)=64),
        profile_ordinal INTEGER NOT NULL CHECK(profile_ordinal>=0),
        page INTEGER NOT NULL CHECK(page>0),
        publication_id INTEGER NOT NULL DEFAULT 1 CHECK(publication_id=1)
            REFERENCES weapon_chart_profile_metadata(id),
        PRIMARY KEY(weapon_id,source_profile_id,mode_key),
        UNIQUE(weapon_id,profile_ordinal)
    )""",
    """CREATE INDEX weapon_chart_profile_slug
       ON weapon_chart_profile_citations(weapon_slug,weapon_id,profile_ordinal)""",
)


def _mode_key(mode: str | None) -> str:
    if mode is None:
        return ""
    if not isinstance(mode, str) or not mode:
        raise ValueError("Invalid reviewed Weapon mode")
    return "mode:" + mode


def _digest(document: dict[str, Any]) -> str:
    """Do not hash final Rules bytes into a database that contains this digest."""
    snapshot = dict(document["sourceSnapshot"])
    snapshot.pop("rulesDatabaseSha256", None)
    canonical = json.dumps(
        {**document, "sourceSnapshot": snapshot},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _source(connection: sqlite3.Connection, collection: str, source_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT s.title,s.version,s.url,s.sha256,s.page_count "
        "FROM sources AS s JOIN collections AS c ON c.id=s.collection_id "
        "WHERE s.collection_id=? AND s.id=? AND c.status='current' "
        "AND s.kind='pdf' AND s.authority='primary'",
        (collection, source_id),
    ).fetchone()
    if row is None:
        raise ValueError("Reviewed Weapon Chart source is not a current primary PDF")
    title, version, url, digest, count = row
    source = {
        "collectionId": collection, "id": source_id, "title": title,
        "version": version, "url": url, "sha256": digest, "pageCount": count,
    }
    if (
        any(not isinstance(source[key], str) or not source[key]
            for key in ("collectionId", "id", "title", "version", "url"))
        or not isinstance(digest, str) or _HEX_SHA.fullmatch(digest) is None
        or type(count) is not int or count <= 0
    ):
        raise ValueError("Reviewed Weapon Chart source has incomplete provenance")
    return source


def _validated_document(
    connection: sqlite3.Connection, document: dict[str, Any],
    army: Path,
) -> list[tuple[Any, ...]]:
    if (
        not isinstance(document, dict)
        or document.get("formatVersion") != 1
        or document.get("scope") != PROFILE_CITATION_SCOPE
        or not isinstance(document.get("source"), dict)
        or not isinstance(document.get("weapons"), list)
        or not document["weapons"]
    ):
        raise ValueError("Invalid reviewed Weapon citation document")
    source_ref = document["source"]
    source = _source(connection, source_ref.get("collectionId"), source_ref.get("id"))
    if source_ref != source:
        raise ValueError("Reviewed Weapon citation source differs from current Rules")
    page_range = document.get("chartPageRange")
    if (
        not isinstance(page_range, list) or len(page_range) != 2
        or any(type(page) is not int for page in page_range)
        or not 1 <= page_range[0] <= page_range[1] <= source["pageCount"]
    ):
        raise ValueError("Invalid reviewed Weapon Chart page range")
    snapshot = document.get("sourceSnapshot")
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("armyDatabaseSha256") != file_sha256(army)
        or not isinstance(snapshot.get("reviewsSha256"), str)
        or _HEX_SHA.fullmatch(snapshot["reviewsSha256"]) is None
    ):
        raise ValueError("Reviewed Weapon citations do not match Army/review provenance")
    database = Database(army)
    seen_weapons: set[int] = set()
    rows: list[tuple[Any, ...]] = []
    for weapon in document["weapons"]:
        if not isinstance(weapon, dict):
            raise ValueError("Invalid reviewed Weapon identity")
        weapon_id, slug, name = weapon.get("id"), weapon.get("slug"), weapon.get("name")
        digest, profiles = weapon.get("profileSha256"), weapon.get("profiles")
        if (
            type(weapon_id) is not int or weapon_id <= 0 or weapon_id in seen_weapons
            or not isinstance(slug, str) or not slug
            or not isinstance(name, str) or not name
            or not isinstance(digest, str) or _HEX_SHA.fullmatch(digest) is None
            or not isinstance(profiles, list) or not profiles
        ):
            raise ValueError("Invalid or duplicate reviewed Weapon identity")
        seen_weapons.add(weapon_id)
        details = database.get_catalog_item("weapons", weapon_id)
        if (
            details is None or details["name"] != name
            or database.application_slug("weapons", weapon_id) != slug
            or profile_sha256(details["profiles"]) != digest
        ):
            raise ValueError(f"Reviewed Weapon profile identity changed: {slug}")
        expected = {(profile["id"], profile.get("mode")) for profile in details["profiles"]}
        if len(expected) != len(details["profiles"]):
            raise ValueError(f"Ambiguous Army Weapon profile identities: {slug}")
        actual: set[tuple[int, str | None]] = set()
        for ordinal, profile in enumerate(profiles):
            if not isinstance(profile, dict):
                raise ValueError(f"Invalid reviewed Weapon profile: {slug}")
            profile_id, mode, page = (
                profile.get("sourceId"), profile.get("mode"), profile.get("page"),
            )
            if (
                type(profile_id) is not int or profile_id <= 0
                or (mode is not None and (not isinstance(mode, str) or not mode))
                or type(page) is not int or not page_range[0] <= page <= page_range[1]
                or (profile_id, mode) in actual
            ):
                raise ValueError(f"Invalid or duplicate reviewed Weapon mode: {slug}")
            actual.add((profile_id, mode))
            rows.append((
                weapon_id, profile_id, _mode_key(mode), slug, name, digest,
                ordinal, page,
            ))
        if actual != expected:
            raise ValueError(f"Reviewed Weapon modes do not match the Army database: {slug}")
    return rows


def stage_weapon_profile_citations(
    connection: sqlite3.Connection, document: dict[str, Any], army: Path,
) -> None:
    """Stage an exact reviewed chart into a Rules export transaction."""
    rows = _validated_document(connection, document, army)
    for statement in _SCHEMA:
        connection.execute(statement)
    source = document["source"]
    snapshot = document["sourceSnapshot"]
    start, end = document["chartPageRange"]
    connection.execute(
        "INSERT INTO weapon_chart_profile_metadata VALUES (1,?,?,?,?,?,?,?,?,?)",
        (
            snapshot["armyDatabaseSha256"], snapshot["reviewsSha256"],
            source["collectionId"], source["id"], start, end,
            len(document["weapons"]), len(rows), _digest(document),
        ),
    )
    connection.executemany(
        "INSERT INTO weapon_chart_profile_citations "
        "(weapon_id,source_profile_id,mode_key,weapon_slug,weapon_name,"
        "profile_sha256,profile_ordinal,page) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )


def _read_document(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        "SELECT army_database_sha256,reviews_sha256,source_collection_id,source_id,"
        "page_start,page_end,weapon_count,profile_count,content_sha256 "
        "FROM weapon_chart_profile_metadata WHERE id=1",
    ).fetchone()
    if row is None:
        raise ValueError("Embedded Weapon citations lack provenance metadata")
    (army_sha, review_sha, collection, source_id, start, end,
     weapon_count, profile_count, digest) = row
    if (
        any(not isinstance(value, str) or _HEX_SHA.fullmatch(value) is None
            for value in (army_sha, review_sha, digest))
        or type(start) is not int or type(end) is not int
    ):
        raise ValueError("Embedded Weapon citation provenance is invalid")
    source = _source(connection, collection, source_id)
    if not 1 <= start <= end <= source["pageCount"]:
        raise ValueError("Embedded Weapon citation page range is invalid")
    rows = connection.execute(
        "SELECT weapon_id,source_profile_id,mode_key,weapon_slug,weapon_name,"
        "profile_sha256,profile_ordinal,page FROM weapon_chart_profile_citations "
        "ORDER BY weapon_slug,weapon_id,profile_ordinal",
    ).fetchall()
    weapons: list[dict[str, Any]] = []
    seen: set[int] = set()
    for weapon_id, profile_id, mode_key, slug, name, fingerprint, ordinal, page in rows:
        if (
            not isinstance(mode_key, str)
            or (mode_key and (not mode_key.startswith("mode:") or len(mode_key) <= 5))
            or type(ordinal) is not int or ordinal < 0
            or type(page) is not int or not start <= page <= end
        ):
            raise ValueError("Embedded Weapon citation mode/page is invalid")
        if weapon_id not in seen:
            if ordinal != 0:
                raise ValueError("Embedded Weapon profiles are not contiguous")
            seen.add(weapon_id)
            weapons.append({
                "id": weapon_id, "slug": slug, "name": name,
                "profileSha256": fingerprint, "profiles": [],
            })
        weapon = weapons[-1]
        if (
            weapon["id"] != weapon_id or weapon["slug"] != slug
            or weapon["name"] != name or weapon["profileSha256"] != fingerprint
            or ordinal != len(weapon["profiles"])
        ):
            raise ValueError("Embedded Weapon profile grouping is inconsistent")
        weapon["profiles"].append({
            "sourceId": profile_id,
            "mode": mode_key[5:] if mode_key else None,
            "page": page,
        })
    if len(weapons) != weapon_count or len(rows) != profile_count or not rows:
        raise ValueError("Embedded Weapon citation inventory differs")
    document = {
        "formatVersion": 1, "scope": PROFILE_CITATION_SCOPE,
        "sourceSnapshot": {
            "armyDatabaseSha256": army_sha, "reviewsSha256": review_sha,
        },
        "source": source, "chartPageRange": [start, end], "weapons": weapons,
    }
    if _digest(document) != digest:
        raise ValueError("Embedded Weapon citation fingerprint differs")
    return document


def validate_weapon_profile_snapshot(connection: sqlite3.Connection) -> None:
    """Check relational completeness and source identity without an Army file."""
    _read_document(connection)


def read_weapon_profile_citations(
    connection: sqlite3.Connection, army: Path,
) -> ProfileCitations:
    """Return the unchanged public citation shape for the selected Army source."""
    document = _read_document(connection)
    rows = _validated_document(connection, document, army)
    source = document["source"]
    return {
        (weapon_id, profile_id, mode_key[5:] if mode_key else None): {
            "source_id": source["id"],
            "source_title": source["title"],
            "source_version": source["version"],
            "source_url": source["url"],
            "source_sha256": source["sha256"],
            "source_collection_id": source["collectionId"],
            "page": page,
        }
        for weapon_id, profile_id, mode_key, _slug, _name, _digest, _ordinal, page in rows
    }
