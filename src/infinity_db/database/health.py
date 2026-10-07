"""Operational health reporting for published InfinityDB databases."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .paths import raw_database_path
from .publication import validate_database_pair
from .repository import Database
from .schema import (
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    SCHEMA_VERSION,
    quote,
)

HEALTH_REPORT_FORMAT = "InfinityDB database health"
HEALTH_REPORT_FORMAT_VERSION = 1


def _read_revisions(path: Path) -> tuple[int, int | None]:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        schema_revision = int(connection.execute("PRAGMA user_version").fetchone()[0])
        try:
            row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?",
                (DATABASE_COMPATIBILITY_KEY,),
            ).fetchone()
        except sqlite3.Error:
            return schema_revision, None
        if row is None:
            return schema_revision, None
        try:
            value = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return schema_revision, None
        compatibility_revision = value if type(value) is int else None
        return schema_revision, compatibility_revision
    finally:
        connection.close()


def database_health_report(path: Path, *, require_raw: bool = False) -> dict[str, Any]:
    """Validate one application database and optionally its expected raw sibling."""

    database_path = Path(path)
    raw_path = raw_database_path(database_path)
    application: dict[str, Any] = {
        "path": str(database_path),
        "bytes": database_path.stat().st_size if database_path.is_file() else None,
        "schemaRevision": None,
        "expectedSchemaRevision": SCHEMA_VERSION,
        "compatibilityRevision": None,
        "expectedCompatibilityRevision": DATABASE_COMPATIBILITY_VERSION,
        "status": "invalid",
        "validationMs": None,
    }

    try:
        schema_revision, compatibility_revision = _read_revisions(database_path)
        application["schemaRevision"] = schema_revision
        application["compatibilityRevision"] = compatibility_revision
    except (OSError, sqlite3.Error, json.JSONDecodeError, TypeError, ValueError):
        pass

    started = time.perf_counter()
    try:
        Database(database_path).validate()
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        application["error"] = str(exc)
    else:
        application["status"] = "valid"
    application["validationMs"] = (time.perf_counter() - started) * 1000

    raw_archive: dict[str, Any] = {
        "required": require_raw,
        "path": str(raw_path),
        "bytes": raw_path.stat().st_size if raw_path.is_file() else None,
        "status": "not-checked",
        "pairSha256": None,
        "validationMs": None,
    }
    if require_raw:
        raw_started = time.perf_counter()
        try:
            pair_sha256 = validate_database_pair(database_path, raw_path=raw_path)
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            raw_archive["status"] = "invalid"
            raw_archive["error"] = str(exc)
        else:
            raw_archive["status"] = "valid"
            raw_archive["pairSha256"] = pair_sha256
        raw_archive["validationMs"] = (time.perf_counter() - raw_started) * 1000

    healthy = application["status"] == "valid" and (
        not require_raw or raw_archive["status"] == "valid"
    )
    return {
        "format": HEALTH_REPORT_FORMAT,
        "formatVersion": HEALTH_REPORT_FORMAT_VERSION,
        "status": "healthy" if healthy else "unhealthy",
        "application": application,
        "rawArchive": raw_archive,
    }
