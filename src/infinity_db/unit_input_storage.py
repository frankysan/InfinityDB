"""Snapshot-dependent scoped Unit filter input publication.

Only the invariant input data is projected; selection and counting stay in
the canonical repository and evaluator.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .database.publication import PUBLISHED_CONTENT_SHA256_KEY, published_content_sha256
from .database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE, Table
from .database.unit_filter_matching import MatchContext, Token
from .general_profile_storage import ARMY_SCHEMA_VERSION as PREVIOUS_SCHEMA_VERSION
from .general_profile_storage import ARMY_V33_PUBLISHED_TABLES
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite

ARMY_SCHEMA_VERSION = 34
ARMY_COMPATIBILITY_VERSION = 43
ARMY_V34_PUBLISHED_TABLES = {
    **ARMY_V33_PUBLISHED_TABLES,
    "unit_filter_contexts": Table(("id",), ("body",)),
}
SCOPES = ("profile", "loadout", "unit")


def encode_contexts(contexts: dict[str, tuple[MatchContext, ...]]) -> str:
    """Intern property sets and identical contexts without merging occurrences."""
    properties: dict[frozenset[Token], int] = {}
    positions: dict[MatchContext, int] = {}
    rows: list[list[Any]] = []
    scopes: dict[str, list[int]] = {}
    for scope in SCOPES:
        indices = []
        for context in contexts[scope]:
            if context not in positions:
                positions[context] = len(rows)
                property_id = properties.setdefault(context.properties, len(properties))
                rows.append([
                    context.logical_id, context.source_unit_id, context.source_army_id,
                    context.group_id, context.option_id, context.profile_id, property_id,
                    context.ava_values, context.points, context.swc,
                ])
            indices.append(positions[context])
        scopes[scope] = indices
    return json.dumps({
        "properties": [sorted(tokens) for tokens in properties],
        "contexts": rows,
        "scopes": scopes,
    }, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def decode_contexts(body: str) -> dict[str, tuple[MatchContext, ...]]:
    document = json.loads(body)
    properties = [
        frozenset((kind, value) for kind, value in tokens)
        for tokens in document["properties"]
    ]
    contexts = [
        MatchContext(
            logical_id, unit, army, group, option, profile, properties[property_id],
            tuple(ava), points, swc,
        )
        for logical_id, unit, army, group, option, profile, property_id, ava, points, swc
        in document["contexts"]
    ]
    return {
        scope: tuple(contexts[index] for index in document["scopes"][scope])
        for scope in SCOPES
    }


def stage_filter_contexts(db: sqlite3.Connection, body: str) -> None:
    db.execute(
        "CREATE TABLE unit_filter_contexts (id INTEGER PRIMARY KEY CHECK(id=1), "
        "body TEXT NOT NULL)"
    )
    db.execute("INSERT INTO unit_filter_contexts VALUES (1,?)", (body,))


def validate_filter_contexts(db: sqlite3.Connection) -> None:
    """Check the required row and JSON envelope; the Army checksum binds its contents."""
    rows = db.execute(
        "SELECT id,json_valid(body) FROM unit_filter_contexts"
    ).fetchall()
    if len(rows) != 1 or tuple(rows[0]) != (1, 1):
        raise ValueError("Invalid Unit filter context projection")


def read_filter_contexts(db: sqlite3.Connection) -> dict[str, tuple[MatchContext, ...]]:
    row = db.execute("SELECT body FROM unit_filter_contexts WHERE id=1").fetchone()
    if row is None:
        raise ValueError("Missing Unit filter context projection")
    return decode_contexts(row[0])


def publish_filter_contexts(army: Path) -> None:
    """Publish the canonical source-owned context index before Rules binds Army."""
    from .database.repository import Database

    database = Database(army)
    body = encode_contexts(database._compose_scoped_unit_filter_contexts())
    with closing(sqlite3.connect(army)) as db:
        if db.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Unit filter context publication requires Army v33")
        with db:
            stage_filter_contexts(db, body)
            validate_filter_contexts(db)
            checksum = published_content_sha256(db, definitions=ARMY_V34_PUBLISHED_TABLES)
            db.executemany(
                f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                [(json.dumps(checksum), PUBLISHED_CONTENT_SHA256_KEY),
                 (json.dumps(ARMY_COMPATIBILITY_VERSION), DATABASE_COMPATIBILITY_KEY)],
            )
            db.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(db)
    normalize_sqlite_header(army)
