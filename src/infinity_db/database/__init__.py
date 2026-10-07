"""SQLite export and read-only repositories for the InfinityDB application."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .health import database_health_report
from .paths import raw_database_path
from .publication import validate_database_pair
from .repository import ArmySelectionError, Database
from .schema import DATABASE_COMPATIBILITY_VERSION, SCHEMA_VERSION

if TYPE_CHECKING:
    from .importer import export_database

__all__ = [
    "DATABASE_COMPATIBILITY_VERSION",
    "SCHEMA_VERSION",
    "ArmySelectionError",
    "Database",
    "database_health_report",
    "export_database",
    "raw_database_path",
    "validate_database_pair",
]


def __getattr__(name: str) -> Any:
    """Load build-only database helpers only when callers request them."""
    if name == "export_database":
        from .importer import export_database

        globals()[name] = export_database
        return export_database
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
