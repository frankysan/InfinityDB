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


# Validate the database while the WSGI worker starts, rather than on its first request.
app = create_app(_database_path())
