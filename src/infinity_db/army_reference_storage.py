"""Army v30 relational editorial summaries and explicit historical Army identities."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .army_overview_copy import (
    ARMY_OVERVIEW_COPY_FORMAT,
    ARMY_OVERVIEW_COPY_FORMAT_VERSION,
    parse_army_overview_copy,
)
from .database.publication import (
    PUBLISHED_CONTENT_SHA256_KEY,
    published_content_sha256,
    validate_database_pair,
)
from .database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE, Table
from .legacy_armies import (
    LEGACY_ARMY_FORMAT,
    LEGACY_ARMY_FORMAT_VERSION,
    LegacyArmy,
    parse_legacy_armies,
)
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from .unit_filter_storage import ARMY_SCHEMA_VERSION as PREVIOUS_SCHEMA_VERSION
from .unit_filter_storage import ARMY_V29_PUBLISHED_TABLES, read_unit_filter_semantics

ARMY_SCHEMA_VERSION = 30
ARMY_COMPATIBILITY_VERSION = 39
ARMY_REFERENCE_TABLES = {
    "army_reference_metadata": Table(
        ("id",), ("overview_format", "overview_version", "overview_sha256",
                  "legacy_format", "legacy_version", "legacy_sha256", "export_pair_sha256",
                  "overview_count", "legacy_count", "content_sha256"),
    ),
    "legacy_army_identities": Table(
        ("source_context", "id"),
        ("slug", "position", "name", "role", "group_id", "group_name", "group_slug",
         "logo", "reason"),
    ),
    "army_overview_text": Table(
        ("slug", "text_role"),
        ("position", "application_army_id", "legacy_context", "legacy_army_id", "text"),
    ),
}
ARMY_V30_PUBLISHED_TABLES = {**ARMY_V29_PUBLISHED_TABLES, **ARMY_REFERENCE_TABLES}
_LEGACY_COLUMNS = (
    "id", "name", "slug", "role", "group_id", "group_name", "group_slug", "logo", "reason",
)
_LEGACY_FIELDS = (
    "id", "name", "slug", "role", "groupId", "groupName", "groupSlug", "logo", "reason",
)


def _fingerprint(overview: dict, legacy: dict) -> str:
    return hashlib.sha256(json.dumps(
        {"overview": overview, "legacy": legacy}, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _current_identities(connection: sqlite3.Connection) -> dict[str, tuple[int, str, str]]:
    """Use the published central Army slug registry, without deriving new slugs."""
    rows = connection.execute(
        "SELECT s.slug,a.id,a.name,a.role FROM application_armies AS a "
        "JOIN application_domain_slugs AS s ON s.domain='armies' AND s.application_id=a.id "
        "WHERE s.status='resolved' ORDER BY a.id"
    ).fetchall()
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError("Army reference has ambiguous current Army slugs")
    if len(rows) != connection.execute("SELECT COUNT(*) FROM application_armies").fetchone()[0]:
        raise ValueError("Army reference requires resolved current Army identities")
    return {row[0]: (row[1], row[2], row[3]) for row in rows}


def _validate_identities(
    connection: sqlite3.Connection, summaries: dict[str, str], legacy: tuple[LegacyArmy, ...],
) -> dict[str, tuple[int, str, str]]:
    current = _current_identities(connection)
    current_ids = {row[0] for row in current.values()}
    for army in legacy:
        if army.id in current_ids or army.slug in current:
            raise ValueError("Legacy Army identity overlaps a current Army")
        if army.group_id is not None:
            group = current.get(army.group_slug or "")
            if group is None or group[:2] != (army.group_id, army.group_name):
                raise ValueError("Legacy Army group does not match its explicit current identity")
    expected = {slug for slug, row in current.items() if row[2] != "grouping"}
    expected.update(army.slug for army in legacy)
    if set(summaries) != expected:
        raise ValueError("Army overview must cover exactly the current and curated legacy Armies")
    return current


def read_army_reference_data(
    connection: sqlite3.Connection,
) -> tuple[dict[str, str], tuple[LegacyArmy, ...]]:
    """Read the source-bound projection without opening either authored JSON input."""
    meta = connection.execute(
        "SELECT overview_format,overview_version,overview_sha256,legacy_format,legacy_version,"
        "legacy_sha256,export_pair_sha256,overview_count,legacy_count,content_sha256 "
        "FROM army_reference_metadata WHERE id=1"
    ).fetchone()
    pair = connection.execute(
        f"SELECT value FROM {METADATA_TABLE} WHERE key='export_pair_sha256'"
    ).fetchone()
    if (
        meta is None
        or tuple(meta[:2]) != (ARMY_OVERVIEW_COPY_FORMAT, ARMY_OVERVIEW_COPY_FORMAT_VERSION)
        or tuple(meta[3:5]) != (LEGACY_ARMY_FORMAT, LEGACY_ARMY_FORMAT_VERSION)
        or any(
            not isinstance(value, str) or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            for value in (meta[2], meta[5], meta[6], meta[9])
        )
        or meta[6] != (json.loads(pair[0]) if pair else None)
    ):
        raise ValueError("Army reference metadata differs from its source context")
    legacy_rows = connection.execute(
        "SELECT source_context,position," + ",".join(_LEGACY_COLUMNS)
        + " FROM legacy_army_identities ORDER BY position"
    ).fetchall()
    overview_rows = connection.execute(
        "SELECT slug,text_role,position,application_army_id,legacy_context,legacy_army_id,text "
        "FROM army_overview_text ORDER BY position"
    ).fetchall()
    if (len(overview_rows), len(legacy_rows)) != tuple(meta[7:9]):
        raise ValueError("Army reference inventory is incomplete")
    if any(row[1] != i or row[0] != 1 for i, row in enumerate(legacy_rows)) or any(
        row[2] != i or row[1] != "summary" for i, row in enumerate(overview_rows)
    ):
        raise ValueError("Army reference ordering, text role or source context differs")
    legacy_document = {
        "format": LEGACY_ARMY_FORMAT, "formatVersion": LEGACY_ARMY_FORMAT_VERSION,
        "armies": [dict(zip(_LEGACY_FIELDS, row[2:], strict=True)) for row in legacy_rows],
    }
    overview_document = {
        "format": ARMY_OVERVIEW_COPY_FORMAT, "formatVersion": ARMY_OVERVIEW_COPY_FORMAT_VERSION,
        "armies": [{"slug": row[0], "summary": row[6]} for row in overview_rows],
    }
    legacy = parse_legacy_armies(legacy_document)
    summaries = parse_army_overview_copy(overview_document)
    current = _validate_identities(connection, summaries, legacy)
    historical = {army.slug: army.id for army in legacy}
    for slug, _role, _position, current_id, context, legacy_id, _text in overview_rows:
        identity = (current_id, context, legacy_id)
        expected = (
            (current[slug][0], None, None) if slug in current else (None, 1, historical[slug])
        )
        if identity != expected:
            raise ValueError("Army overview text points at a different Army identity")
    if _fingerprint(overview_document, legacy_document) != meta[9]:
        raise ValueError("Army reference content fingerprint differs")
    return summaries, legacy


def publish_army_reference_data(
    army: Path, raw: Path, overview_source: Path, legacy_source: Path,
) -> None:
    """Extend the disposable matched v29 pair with both authored Army datasets."""
    overview_bytes, legacy_bytes = overview_source.read_bytes(), legacy_source.read_bytes()
    overview_document, legacy_document = json.loads(overview_bytes), json.loads(legacy_bytes)
    summaries = parse_army_overview_copy(overview_document)
    legacy = parse_legacy_armies(legacy_document)
    generation = validate_database_pair(army, raw_path=raw)
    if generation is None:
        raise ValueError("Army reference publication requires a paired Army source")
    with closing(sqlite3.connect(army)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Army reference publication requires Army v29")
        read_unit_filter_semantics(connection)
        current = _validate_identities(connection, summaries, legacy)
        historical = {item.slug: item.id for item in legacy}
        with connection:
            connection.execute("""CREATE TABLE army_reference_metadata (
                id INTEGER PRIMARY KEY CHECK(id=1),
                overview_format TEXT NOT NULL,
                overview_version INTEGER NOT NULL CHECK(overview_version=1),
                overview_sha256 TEXT NOT NULL CHECK(length(overview_sha256)=64),
                legacy_format TEXT NOT NULL,
                legacy_version INTEGER NOT NULL CHECK(legacy_version=1),
                legacy_sha256 TEXT NOT NULL CHECK(length(legacy_sha256)=64),
                export_pair_sha256 TEXT NOT NULL CHECK(length(export_pair_sha256)=64),
                overview_count INTEGER NOT NULL CHECK(overview_count>=0),
                legacy_count INTEGER NOT NULL CHECK(legacy_count>=0),
                content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64)
            )""")
            connection.execute("""CREATE TABLE legacy_army_identities (
                source_context INTEGER NOT NULL, id INTEGER NOT NULL UNIQUE CHECK(id>0),
                slug TEXT NOT NULL UNIQUE, position INTEGER NOT NULL UNIQUE CHECK(position>=0),
                name TEXT NOT NULL, role TEXT NOT NULL, group_id INTEGER,
                group_name TEXT, group_slug TEXT, logo TEXT NOT NULL, reason TEXT NOT NULL,
                PRIMARY KEY(source_context,id),
                FOREIGN KEY(source_context) REFERENCES army_reference_metadata(id),
                FOREIGN KEY(group_id) REFERENCES application_armies(id)
            )""")
            connection.execute("""CREATE TABLE army_overview_text (
                slug TEXT NOT NULL, text_role TEXT NOT NULL CHECK(text_role='summary'),
                position INTEGER NOT NULL UNIQUE CHECK(position>=0),
                application_army_id INTEGER, legacy_context INTEGER, legacy_army_id INTEGER,
                text TEXT NOT NULL CHECK(length(text)>0), PRIMARY KEY(slug,text_role),
                CHECK((application_army_id IS NOT NULL AND legacy_context IS NULL
                        AND legacy_army_id IS NULL)
                    OR (application_army_id IS NULL AND legacy_context IS NOT NULL
                        AND legacy_army_id IS NOT NULL)),
                FOREIGN KEY(application_army_id) REFERENCES application_armies(id),
                FOREIGN KEY(legacy_context,legacy_army_id)
                    REFERENCES legacy_army_identities(source_context,id)
            )""")
            connection.execute(
                "INSERT INTO army_reference_metadata VALUES (1,?,?,?,?,?,?,?,?,?,?)", (
                ARMY_OVERVIEW_COPY_FORMAT, ARMY_OVERVIEW_COPY_FORMAT_VERSION,
                hashlib.sha256(overview_bytes).hexdigest(), LEGACY_ARMY_FORMAT,
                LEGACY_ARMY_FORMAT_VERSION, hashlib.sha256(legacy_bytes).hexdigest(), generation,
                len(summaries), len(legacy), _fingerprint(overview_document, legacy_document),
                ),
            )
            for index, row in enumerate(legacy_document["armies"]):
                connection.execute(
                    "INSERT INTO legacy_army_identities "
                    "(source_context,position," + ",".join(_LEGACY_COLUMNS) + ") "
                    "VALUES (1,?,?,?,?,?,?,?,?,?,?)",
                    (index, *(row[field] for field in _LEGACY_FIELDS)),
                )
            for index, row in enumerate(overview_document["armies"]):
                slug = row["slug"]
                identity = (
                    (current[slug][0], None, None) if slug in current
                    else (None, 1, historical[slug])
                )
                connection.execute(
                    "INSERT INTO army_overview_text VALUES (?,'summary',?,?,?,?,?)",
                    (slug, index, *identity, row["summary"]),
                )
            if read_army_reference_data(connection) != (summaries, legacy):
                raise ValueError("Embedded Army reference differs from reviewed inputs")
            metadata: dict[str, Any] = {
                PUBLISHED_CONTENT_SHA256_KEY: published_content_sha256(
                    connection, definitions=ARMY_V30_PUBLISHED_TABLES,
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
    with closing(sqlite3.connect(raw)) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Army reference raw export requires Army v29")
        with connection:
            for key, value in metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?", (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(raw)
    validate_database_pair(army, raw_path=raw)
