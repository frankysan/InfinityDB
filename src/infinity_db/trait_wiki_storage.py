"""Reviewed Trait-to-Wiki links stored with N5 rule ownership, not runtime JSON."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from urllib.parse import urlsplit

TRAIT_LINK_SCHEMA_VERSION = 14
TRAIT_LINK_COMPATIBILITY_VERSION = 16
_TRAIT_ID = re.compile(r"trait:[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _fingerprint(entries: dict[str, dict[str, str]]) -> str:
    return hashlib.sha256(
        json.dumps(entries, sort_keys=True, ensure_ascii=False, allow_nan=False,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _current_traits(connection: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    rows = connection.execute(
        "SELECT r.id,r.collection_id,r.name FROM records r "
        "JOIN collections c ON c.id=r.collection_id "
        "WHERE c.status='current' AND r.kind='trait'"
    ).fetchall()
    if len(rows) != len({row[0] for row in rows}) or not rows:
        raise ValueError("Current Trait identities are missing or ambiguous")
    return {row[0]: (row[1], row[2]) for row in rows}


def _validate_entries(
    connection: sqlite3.Connection, entries: dict[str, dict[str, str]],
) -> dict[str, tuple[str, str]]:
    current = _current_traits(connection)
    if not isinstance(entries, dict) or set(entries) != set(current):
        raise ValueError("Reviewed Trait Wiki links must cover every current canonical Trait")
    for record_id, entry in entries.items():
        if not isinstance(record_id, str) or not _TRAIT_ID.fullmatch(record_id):
            raise ValueError("Invalid reviewed Trait Wiki identity")
        if not isinstance(entry, dict) or set(entry) != {"name", "url"}:
            raise ValueError(f"Invalid reviewed Trait Wiki link: {record_id}")
        name, url = entry["name"], entry["url"]
        if not isinstance(name, str) or name != current[record_id][1]:
            raise ValueError(f"Trait Wiki link name differs from canonical record: {record_id}")
        if not isinstance(url, str):
            raise ValueError(f"Invalid Trait Wiki destination: {record_id}")
        parts = urlsplit(url)
        if (parts.scheme, parts.netloc, parts.path, parts.query) != (
            "https", "infinitythewiki.com", "/Traits", "",
        ) or not parts.fragment:
            raise ValueError(f"Unreviewed Trait Wiki destination: {record_id}")
    return current


def stage_trait_wiki_links(
    connection: sqlite3.Connection, entries: dict[str, dict[str, str]],
) -> None:
    """Extend an in-progress v13 rules export with source-checked Trait links."""
    if connection.execute("PRAGMA user_version").fetchone()[0] != 13:
        raise ValueError("Embedded Trait Wiki links require the v13 Rules baseline")
    current = _validate_entries(connection, entries)
    schema = """
        CREATE TABLE trait_wiki_metadata (
            id INTEGER PRIMARY KEY CHECK (id=1),
            source_format TEXT NOT NULL,
            source_version INTEGER NOT NULL CHECK (source_version=1),
            link_count INTEGER NOT NULL CHECK (link_count>0),
            content_sha256 TEXT NOT NULL CHECK (length(content_sha256)=64)
        );
        CREATE TABLE trait_source_links (
            collection_id TEXT NOT NULL,
            trait_record_id TEXT NOT NULL,
            position INTEGER NOT NULL UNIQUE CHECK (position>=0),
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            PRIMARY KEY (collection_id,trait_record_id),
            UNIQUE (trait_record_id),
            FOREIGN KEY (collection_id,trait_record_id)
                REFERENCES records(collection_id,id)
        );
    """
    for statement in schema.split(";"):
        if statement.strip():
            connection.execute(statement)
    connection.execute(
        "INSERT INTO trait_wiki_metadata VALUES (1,?,?,?,?)",
        ("InfinityDB trait Wiki references", 1, len(entries), _fingerprint(entries)),
    )
    for position, record_id in enumerate(sorted(entries)):
        entry = entries[record_id]
        connection.execute(
            "INSERT INTO trait_source_links VALUES (?,?,?,?,?)",
            (current[record_id][0], record_id, position, entry["name"], entry["url"]),
        )
    read_trait_wiki_links(connection)


def read_trait_wiki_links(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, str]]:
    """Reconstruct exactly the reviewed mapping from Rules, rejecting missing/corrupt rows."""
    meta = connection.execute(
        "SELECT source_format,source_version,link_count,content_sha256 "
        "FROM trait_wiki_metadata WHERE id=1"
    ).fetchone()
    if meta is None or meta[0:2] != ("InfinityDB trait Wiki references", 1):
        raise ValueError("Invalid embedded Trait Wiki metadata")
    rows = connection.execute(
        "SELECT collection_id,trait_record_id,position,name,url "
        "FROM trait_source_links ORDER BY position"
    ).fetchall()
    if len(rows) != meta[2] or any(row[2] != pos for pos, row in enumerate(rows)):
        raise ValueError("Incomplete or unordered embedded Trait Wiki links")
    current = _current_traits(connection)
    entries = {row[1]: {"name": row[3], "url": row[4]} for row in rows}
    if any(current.get(row[1]) != (row[0], row[3]) for row in rows):
        raise ValueError("Trait Wiki links differ from current Rules identities")
    _validate_entries(connection, entries)
    if _fingerprint(entries) != meta[3]:
        raise ValueError("Embedded Trait Wiki link fingerprint differs")
    return entries


def validate_trait_wiki_snapshot(connection: sqlite3.Connection) -> None:
    read_trait_wiki_links(connection)
