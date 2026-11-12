"""Verified normalized Army source tables for transient variant publication.

Materialize queryable normalized relations only in memory. The source document
must reproduce the base export-generation hash recorded in the selected Army
application database, even after later schema overlays update its checksum.
No raw archive file or lossless duplicate row JSON is constructed.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from .database.importer import insert_batched, sql_value
from .database.normalized_source import verified_normalized_document
from .database.schema import METADATA_TABLE, TABLES, create_schema, quote


@contextmanager
def normalized_source_connection(
    application_path: Path, normalized_path: Path,
) -> Iterator[tuple[sqlite3.Connection, str]]:
    """Open a verified, read-only normalized source projection with its export ID."""
    document, table_columns, rows, generation = verified_normalized_document(
        application_path, normalized_path,
    )
    with closing(sqlite3.connect(":memory:")) as source:
        source.row_factory = sqlite3.Row
        create_schema(
            source, document["tables"], table_columns=table_columns, definitions=TABLES,
        )
        source.executemany(
            f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
            rows,
        )
        for name, items in document["tables"].items():
            columns = table_columns[name]
            fields = ", ".join(map(quote, columns))
            placeholders = ", ".join("?" for _ in columns)
            insert_batched(
                source,
                f"INSERT INTO {quote(name)} ({fields}) VALUES ({placeholders})",
                (tuple(sql_value(item.get(field)) for field in columns) for item in items),
            )
        violation = source.execute("PRAGMA foreign_key_check").fetchone()
        if violation is not None:
            raise ValueError("Normalized variant source violates source relationships")
        source.commit()
        source.execute("PRAGMA query_only = ON")
        yield source, generation
