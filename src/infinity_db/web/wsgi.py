"""Production WSGI entry point for Gunicorn and other WSGI servers."""

from __future__ import annotations

import os
from pathlib import Path

from .app import create_app


def _database_path() -> Path:
    """Return the explicitly configured, immutable production database path."""
    value = os.environ.get("INFINITY_DB_DATABASE")
    if not value:
        raise RuntimeError("INFINITY_DB_DATABASE must name the SQLite database to serve")
    return Path(value)


def _rules_database_path() -> Path | None:
    """Return the optional explicitly configured production rules database path."""
    value = os.environ.get("INFINITY_DB_RULES_DATABASE")
    return Path(value) if value else None


# Validate explicitly configured databases while the WSGI worker starts, rather
# than on its first request. An explicitly configured rules database is required
# to exist and validate; omitting the setting preserves optional local behavior.
app = create_app(_database_path(), _rules_database_path())
