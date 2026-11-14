"""Read-only audit connection exposing source-only Army tables as temp views.

Legacy combined databases require no extra source. Split exports can use their
verified raw sibling, or an explicitly supplied normalized JSON document whose
complete contents match the published Army export generation. Normalized
source tables live only in an attached in-memory database; neither input is
modified.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from infinity_db.database.importer import insert_batched, sql_value
from infinity_db.database.normalized_source import verified_normalized_document
from infinity_db.database.paths import raw_database_path
from infinity_db.database.publication import validate_database_pair
from infinity_db.database.schema import TABLES, columns_for, quote


def _attach_normalized_tables(
    connection: sqlite3.Connection,
    application: Path,
    normalized: Path,
    missing: set[str],
) -> None:
    """Project only required source tables into a disposable attached database."""
    document, columns_by_table, _metadata, _generation = verified_normalized_document(
        application, normalized,
    )
    selected = sorted(missing & TABLES.keys())
    if not selected:
        return
    connection.execute("ATTACH DATABASE ':memory:' AS source_archive")
    for name in selected:
        definition = TABLES[name]
        columns = columns_by_table.get(name, columns_for(name, []))
        column_sql = ", ".join(
            quote(column) + (" NOT NULL" if column in definition.key else "")
            for column in columns
        )
        key_sql = ", ".join(map(quote, definition.key))
        connection.execute(
            f"CREATE TABLE source_archive.{quote(name)} "
            f"({column_sql}, PRIMARY KEY ({key_sql}))"
        )
        fields = ", ".join(map(quote, columns))
        placeholders = ", ".join("?" for _ in columns)
        insert_batched(
            connection,
            f"INSERT INTO source_archive.{quote(name)} ({fields}) "
            f"VALUES ({placeholders})",
            (
                tuple(sql_value(row.get(column)) for column in columns)
                for row in document["tables"].get(name, [])
            ),
        )
        connection.execute(
            f"CREATE TEMP VIEW {quote(name)} AS "
            f"SELECT * FROM source_archive.{quote(name)}"
        )


def open_paired_audit_connection(
    path: Path,
    required_tables: Iterable[str],
    *,
    normalized: Path | None = None,
) -> sqlite3.Connection:
    """Open a read-only combined, raw-paired or verified normalized Army audit."""
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
        if normalized is not None:
            _attach_normalized_tables(connection, database, normalized, missing)
        else:
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
