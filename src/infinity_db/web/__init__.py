"""Web delivery layer, independent of ingestion and database schema details."""

from .app import create_app

__all__ = ["create_app"]
