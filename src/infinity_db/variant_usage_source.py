"""Verified normalized Army source tables for transient variant publication.

Materialize queryable normalized relations only in memory. The source document
must reproduce the base export-generation hash recorded in the selected Army
application database, even after later schema overlays update its checksum.
No raw archive file or lossless duplicate row JSON is constructed.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from .database.importer import insert_batched, sql_value, validate_input
from .database.publication import (
    EXPORT_PAIR_SHA256_KEY,
    PUBLISHED_CONTENT_SHA256_KEY,
    export_pair_sha256,
    published_content_sha256,
)
from .database.schema import (
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    TABLES,
    create_schema,
    quote,
)


@contextmanager
def normalized_source_connection(
    application_path: Path, normalized_path: Path,
) -> Iterator[tuple[sqlite3.Connection, str]]:
    """Open a verified, read-only normalized source projection with its export ID."""
    with normalized_path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    table_columns = validate_input(document)

    # Overlay publishers change only the compatibility and publication-content
    # fingerprints in this shared metadata. Restore the base export's values
    # before verifying every normalized source row against its generation pin.
    with closing(
        sqlite3.connect(application_path.resolve().as_uri() + "?mode=ro", uri=True)
    ) as app:
        rows = app.execute(f"SELECT key, value FROM {quote(METADATA_TABLE)}").fetchall()
        try:
            metadata = {str(key): json.loads(value) for key, value in rows}
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid published Army export metadata") from exc
        generation = metadata.get(EXPORT_PAIR_SHA256_KEY)
        if (
            not isinstance(generation, str)
            or len(generation) != 64
            or any(char not in "0123456789abcdef" for char in generation)
        ):
            raise ValueError("Normalized variant source requires a pinned Army export")
        base_metadata = {
            **metadata,
            DATABASE_COMPATIBILITY_KEY: DATABASE_COMPATIBILITY_VERSION,
            PUBLISHED_CONTENT_SHA256_KEY: published_content_sha256(app),
        }
        if export_pair_sha256(document, base_metadata) != generation:
            raise ValueError(
                "Normalized source does not match the published Army export generation"
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
