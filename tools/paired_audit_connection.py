"""Read-only audit connection spanning matched application/raw Army siblings.

Existing semantic audits were written against a combined SQLite schema. Current
exports split source-only normalized tables into the ignored raw sibling. Expose
only the missing, explicitly requested source tables as temporary views; never
modify either input database or permit an unmatched raw archive.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from infinity_db.database.paths import raw_database_path
from infinity_db.database.publication import validate_database_pair
from infinity_db.database.schema import quote


def open_paired_audit_connection(
    path: Path,
    required_tables: Iterable[str],
) -> sqlite3.Connection:
    """Open read-only published or legacy-combined inputs for an audit."""
    database = path.resolve()
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        present = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM main.sqlite_master WHERE type='table'"
            )
        }
        missing = set(required_tables) - present
        raw_path = raw_database_path(database)
        if missing and raw_path.is_file():
            validate_database_pair(database, raw_path=raw_path)
            connection.execute(
                "ATTACH DATABASE ? AS source_archive",
                (raw_path.resolve().as_uri() + "?mode=ro",),
            )
            raw_tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM source_archive.sqlite_master WHERE type='table'"
                )
            }
            for table in sorted(missing & raw_tables):
                connection.execute(
                    f"CREATE TEMP VIEW {quote(table)} AS "
                    f"SELECT * FROM source_archive.{quote(table)}"
                )
        connection.execute("PRAGMA query_only = ON")
        return connection
    except BaseException:
        connection.close()
        raise
