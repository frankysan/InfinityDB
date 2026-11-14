"""Army v29 storage for reviewed Unit Explorer filter overlays.

Only complete builds extend the disposable matched Army/raw export pair.
Source characteristics and classifications remain unchanged.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .database.normalized_source import verified_army_export_generation
from .database.publication import (
    PUBLISHED_CONTENT_SHA256_KEY,
    published_content_sha256,
    validate_database_pair,
)
from .database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE, Table
from .domain_slugs import resolve_domain_slug_candidates
from .skill_classification_storage import (
    ARMY_SCHEMA_VERSION as PREVIOUS_SCHEMA_VERSION,
)
from .skill_classification_storage import ARMY_V28_PUBLISHED_TABLES, read_skill_classifications
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from .unit_filter_config import (
    UNIT_FILTER_CONFIG_FORMAT,
    UNIT_FILTER_CONFIG_VERSION,
    UnitFilterConfig,
    parse_unit_filter_config,
)

ARMY_SCHEMA_VERSION = 29
ARMY_COMPATIBILITY_VERSION = 38
UNIT_FILTER_TABLES = {
    "unit_filter_metadata": Table(
        ("id",), ("format", "version", "source_sha256", "export_pair_sha256",
                  "hidden_count", "membership_count", "match_count", "content_sha256"),
    ),
    "hidden_unit_characteristics": Table(
        ("slug",), ("characteristic_id", "position", "reason"),
    ),
    "source_classification_memberships": Table(
        ("source_slug",), ("category_id", "position", "reason"),
    ),
    "source_classification_matches": Table(
        ("source_slug", "match_slug"), ("category_id", "position"),
    ),
}
ARMY_V29_PUBLISHED_TABLES = {**ARMY_V28_PUBLISHED_TABLES, **UNIT_FILTER_TABLES}


def _fingerprint(document: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        document, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _resolve(connection: sqlite3.Connection, table: str, slug: str) -> int:
    domain = "classifications" if table == "categories" else "characteristics"
    rows = connection.execute(
        f"SELECT id,name FROM {table} WHERE name IS NOT NULL AND TRIM(name)<>'' ORDER BY id"
    ).fetchall()
    resolutions = resolve_domain_slug_candidates(
        ((row[0], row[1]) for row in rows), domain=domain, reject_numeric=True,
    )
    matches = [key for key, item in resolutions.items() if item.slug == slug]
    if len(matches) != 1:
        raise ValueError(f"Unit filter overlay lacks unique {domain} source: {slug!r}")
    return matches[0]


def _ordered(rows: list, position: int) -> None:
    if any(row[position] != index for index, row in enumerate(rows)):
        raise ValueError("Unit filter overlay rows are unordered or incomplete")


def read_unit_filter_semantics(connection: sqlite3.Connection) -> UnitFilterConfig:
    """Validate source-bound relational rows and return the existing filter model."""
    meta = connection.execute(
        "SELECT format,version,source_sha256,export_pair_sha256,hidden_count,"
        "membership_count,match_count,content_sha256 FROM unit_filter_metadata WHERE id=1"
    ).fetchone()
    pair = connection.execute(
        f"SELECT value FROM {METADATA_TABLE} WHERE key='export_pair_sha256'"
    ).fetchone()
    generation = json.loads(pair[0]) if pair else None
    if (
        meta is None
        or tuple(meta[:2]) != (UNIT_FILTER_CONFIG_FORMAT, UNIT_FILTER_CONFIG_VERSION)
        or any(
            not isinstance(value, str) or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            for value in (meta[2], meta[3], meta[7])
        )
        or meta[3] != generation
    ):
        raise ValueError("Unit filter overlay metadata does not match its Army source")
    hidden = connection.execute(
        "SELECT slug,characteristic_id,position,reason FROM hidden_unit_characteristics "
        "ORDER BY position"
    ).fetchall()
    memberships = connection.execute(
        "SELECT source_slug,category_id,position,reason "
        "FROM source_classification_memberships ORDER BY position"
    ).fetchall()
    all_matches = connection.execute(
        "SELECT source_slug,match_slug,category_id,position FROM source_classification_matches "
        "ORDER BY source_slug,position"
    ).fetchall()
    if tuple(meta[4:7]) != (len(hidden), len(memberships), len(all_matches)):
        raise ValueError("Unit filter overlay inventory differs from its publication")
    _ordered(hidden, 2)
    _ordered(memberships, 2)
    document: dict[str, Any] = {
        "format": UNIT_FILTER_CONFIG_FORMAT,
        "formatVersion": UNIT_FILTER_CONFIG_VERSION,
        "hiddenCharacteristics": [], "classificationMemberships": [],
    }
    for slug, source_id, _position, reason in hidden:
        if _resolve(connection, "characteristics", slug) != source_id:
            raise ValueError("Hidden characteristic source identity differs")
        document["hiddenCharacteristics"].append({"characteristic": slug, "reason": reason})
    known_sources = {row[0] for row in memberships}
    if any(row[0] not in known_sources for row in all_matches):
        raise ValueError("Unit filter match lacks its source membership")
    for slug, source_id, _position, reason in memberships:
        if _resolve(connection, "categories", slug) != source_id:
            raise ValueError("Combined classification source identity differs")
        matches = [row for row in all_matches if row[0] == slug]
        _ordered(matches, 3)
        for _source, match, match_id, _index in matches:
            if _resolve(connection, "categories", match) != match_id:
                raise ValueError("Classification component source identity differs")
        document["classificationMemberships"].append({
            "sourceClassification": slug, "matches": [row[1] for row in matches],
            "reason": reason,
        })
    config = parse_unit_filter_config(document)
    if _fingerprint(document) != meta[7]:
        raise ValueError("Unit filter overlay content fingerprint differs")
    return config


def publish_unit_filter_semantics(
    army: Path, raw: Path | None, source: Path, *, normalized: Path | None = None,
) -> None:
    """Publish v29 from an explicitly verified raw or normalized Army source."""
    source_bytes = source.read_bytes()
    document = json.loads(source_bytes)
    expected = parse_unit_filter_config(document)
    generation = verified_army_export_generation(army, raw, normalized)
    with closing(sqlite3.connect(army)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Unit filter publication requires Army v28")
        read_skill_classifications(connection)
        hidden = [
            (row["characteristic"], _resolve(connection, "characteristics", row["characteristic"]),
             index, row["reason"])
            for index, row in enumerate(document["hiddenCharacteristics"])
        ]
        memberships = [
            (row["sourceClassification"],
             _resolve(connection, "categories", row["sourceClassification"]), index, row["reason"])
            for index, row in enumerate(document["classificationMemberships"])
        ]
        matches = [
            (row["sourceClassification"], slug, _resolve(connection, "categories", slug), index)
            for row in document["classificationMemberships"]
            for index, slug in enumerate(row["matches"])
        ]
        with connection:
            connection.execute("""CREATE TABLE unit_filter_metadata (
                id INTEGER PRIMARY KEY CHECK(id=1), format TEXT NOT NULL,
                version INTEGER NOT NULL CHECK(version=1),
                source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
                export_pair_sha256 TEXT NOT NULL CHECK(length(export_pair_sha256)=64),
                hidden_count INTEGER NOT NULL CHECK(hidden_count>=0),
                membership_count INTEGER NOT NULL CHECK(membership_count>=0),
                match_count INTEGER NOT NULL CHECK(match_count>=0),
                content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64)
            )""")
            connection.execute("""CREATE TABLE hidden_unit_characteristics (
                slug TEXT PRIMARY KEY NOT NULL, characteristic_id INTEGER NOT NULL UNIQUE,
                position INTEGER NOT NULL UNIQUE CHECK(position>=0),
                reason TEXT NOT NULL CHECK(length(reason)>0),
                FOREIGN KEY(characteristic_id) REFERENCES characteristics(id)
            )""")
            connection.execute("""CREATE TABLE source_classification_memberships (
                source_slug TEXT PRIMARY KEY NOT NULL, category_id INTEGER NOT NULL UNIQUE,
                position INTEGER NOT NULL UNIQUE CHECK(position>=0),
                reason TEXT NOT NULL CHECK(length(reason)>0),
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )""")
            connection.execute("""CREATE TABLE source_classification_matches (
                source_slug TEXT NOT NULL, match_slug TEXT NOT NULL,
                category_id INTEGER NOT NULL, position INTEGER NOT NULL CHECK(position>=0),
                PRIMARY KEY(source_slug,match_slug), UNIQUE(source_slug,position),
                FOREIGN KEY(source_slug) REFERENCES source_classification_memberships(source_slug),
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )""")
            connection.execute("INSERT INTO unit_filter_metadata VALUES (1,?,?,?,?,?,?,?,?)", (
                UNIT_FILTER_CONFIG_FORMAT, UNIT_FILTER_CONFIG_VERSION,
                hashlib.sha256(source_bytes).hexdigest(), generation,
                len(hidden), len(memberships), len(matches), _fingerprint(document),
            ))
            connection.executemany(
                "INSERT INTO hidden_unit_characteristics VALUES (?,?,?,?)", hidden,
            )
            connection.executemany(
                "INSERT INTO source_classification_memberships VALUES (?,?,?,?)", memberships,
            )
            connection.executemany(
                "INSERT INTO source_classification_matches VALUES (?,?,?,?)", matches,
            )
            if read_unit_filter_semantics(connection) != expected:
                raise ValueError("Embedded Unit filter overlays differ from reviewed input")
            metadata = {
                PUBLISHED_CONTENT_SHA256_KEY: published_content_sha256(
                    connection, definitions=ARMY_V29_PUBLISHED_TABLES,
                ),
                DATABASE_COMPATIBILITY_KEY: ARMY_COMPATIBILITY_VERSION,
            }
            for key, value in metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?", (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(army)
    if raw is None:
        return
    with closing(sqlite3.connect(raw)) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Unit filter raw export requires Army v28")
        with connection:
            for key, value in metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?", (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(raw)
    validate_database_pair(army, raw_path=raw)
