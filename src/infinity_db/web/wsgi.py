"""Production WSGI entry point for Gunicorn and other WSGI servers."""

from __future__ import annotations

from infinity_db.database_set import select_database_directory

from .app import create_app_from_database_set

# Resolve and validate the same complete set used by checkout serving.
app = create_app_from_database_set(select_database_directory(required_environment=True))
