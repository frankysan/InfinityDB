"""Deterministic, snapshot-bound Unit history publication and lookup."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .build_provenance import file_sha256
from .database.publication import PUBLISHED_CONTENT_SHA256_KEY, published_content_sha256
from .database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE, Table
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from .unit_input_storage import ARMY_SCHEMA_VERSION as PREVIOUS_SCHEMA_VERSION
from .unit_input_storage import ARMY_V34_PUBLISHED_TABLES

ARMY_SCHEMA_VERSION = 35
ARMY_COMPATIBILITY_VERSION = 44
ARMY_V35_PUBLISHED_TABLES = {
    **ARMY_V34_PUBLISHED_TABLES,
    "unit_history_payloads": Table(("unit_id",), ("body",)),
}
# Accepted research inputs; refresh deliberately when the corpus is extended.
HISTORY_ARCHIVE_SHA256 = "08978b9bbf3fffa3184f6153fa4dd05a1931482742f08ee5de7a6df4f4a3c5c5"
HISTORY_DATABASE_SHA256 = "631eee9a821132f5f16dd4989a8631908f5e1d2cad6eacd4dca49b9ba2b42795"


def history_inputs(root: Path) -> tuple[Path, Path]:
    return (root / "archive/army-history-v1.zip", root / "generated/army_history_n5.db")


def history_input_identity(root: Path) -> dict[str, str]:
    archive, database = history_inputs(root)
    if (file_sha256(archive) != HISTORY_ARCHIVE_SHA256
            or file_sha256(database) != HISTORY_DATABASE_SHA256):
        raise ValueError("Selected Army history inputs differ from the accepted corpus")
    return {"archiveSha256": HISTORY_ARCHIVE_SHA256, "databaseSha256": HISTORY_DATABASE_SHA256}


def validate_unit_history(db: sqlite3.Connection) -> None:
    if db.execute(
        "SELECT 1 FROM unit_history_payloads h LEFT JOIN logical_units u ON u.id=h.unit_id "
        "WHERE u.id IS NULL OR NOT json_valid(h.body) OR json_type(h.body) != 'object' "
        "OR json_type(h.body,'$.general') IS NOT 'object' "
        "OR json_type(h.body,'$.armies') IS NOT 'object' "
        "OR json_type(h.body,'$.unmatched') IS NOT 'array' LIMIT 1"
    ).fetchone() is not None:
        raise ValueError("Invalid Unit history projection")


def read_unit_history(db: sqlite3.Connection, unit_id: int) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT body FROM unit_history_payloads WHERE unit_id=?", (unit_id,),
    ).fetchone()
    return json.loads(row[0]) if row is not None else None


def write_unit_history(army: Path, projection: dict[str, Any]) -> None:
    """Bind an exact pre-publication Army generation; never overlay a serving set."""
    if (projection.get("formatVersion") != 1
            or projection.get("armyDatabaseSha256") != file_sha256(army)):
        raise ValueError("Unit history projection does not match the selected Army database")
    with closing(sqlite3.connect(army)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Unit history publication requires Army v34")
        with db:
            db.execute("""CREATE TABLE unit_history_payloads (
                unit_id INTEGER PRIMARY KEY REFERENCES logical_units(id),
                body TEXT NOT NULL
            )""")
            db.executemany(
                "INSERT INTO unit_history_payloads VALUES (?,?)",
                [(int(key), json.dumps(body, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":"), allow_nan=False))
                 for key, body in sorted(projection["units"].items(), key=lambda p: int(p[0]))],
            )
            validate_unit_history(db)
            checksum = published_content_sha256(db, definitions=ARMY_V35_PUBLISHED_TABLES)
            db.executemany(
                f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                [(json.dumps(checksum), PUBLISHED_CONTENT_SHA256_KEY),
                 (json.dumps(ARMY_COMPATIBILITY_VERSION), DATABASE_COMPATIBILITY_KEY)],
            )
            db.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(db)
    normalize_sqlite_header(army)


def publish_unit_history(army: Path, root: Path) -> None:
    """Compose from pinned offline research against the staged current Army."""
    from tools.research.project_army_history import build as project
    from tools.research.project_army_history import read_only
    from tools.research.render_player_army_history import (
        contextual_model,
        historical_scopes,
        history_projection,
        model,
    )
    from tools.research.summarize_army_history import build as summarize

    from .database.repository import Database

    pins = history_input_identity(root)
    archive, history = history_inputs(root)
    army_sha = file_sha256(army)
    Database(army).validate()
    with closing(read_only(history)) as db, closing(read_only(army)) as current:
        preview = project(db, current, archive)
        preview.update(armyDatabaseSha256=army_sha, historyDatabaseSha256=pins["databaseSha256"])
        semantic = summarize(preview, archive, history_path=history)
        units, _ = model(preview, semantic, historical_scopes(db, archive))
        contextual_model(units, db, archive, army_path=army)
        names = dict(current.execute("SELECT id,name FROM army_lists WHERE name IS NOT NULL"))
        projection = history_projection(units, names, army_sha)
    if history_input_identity(root) != pins:
        raise ValueError("History inputs changed during publication")
    write_unit_history(army, projection)
