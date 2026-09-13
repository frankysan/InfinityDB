"""Validate normalized data and atomically publish a complete SQLite database."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from itertools import islice
from pathlib import Path
from typing import Any

from infinity_army_data.metadata import MetadataError, validate_metadata_envelope
from infinity_army_data.normalize import FORMAT_NAME, FORMAT_VERSION, validate_normalized

from .schema import (
    APPLICATION_ID,
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    RAW_ROWS_TABLE,
    ROW_JSON,
    TABLES,
    columns_for,
    create_indexes,
    create_schema,
    quote,
)

BATCH_SIZE = 1_000


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def validate_input(data: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    if not isinstance(data, dict) or not isinstance(data.get("_meta"), dict):
        raise ValueError("Normalized data must contain a _meta object")
    meta = data["_meta"]
    if meta.get("format") != FORMAT_NAME or type(meta.get("formatVersion")) is not int:
        raise ValueError(f"Expected {FORMAT_NAME!r}, version {FORMAT_VERSION}")
    if meta["formatVersion"] != FORMAT_VERSION:
        raise ValueError(f"Unsupported normalized format version: {meta['formatVersion']}")
    metadata = data.get("armyMetadata")
    if metadata is None:
        raise ValueError("Normalized data must contain required Army metadata")
    try:
        validate_metadata_envelope(metadata)
    except MetadataError as exc:
        raise ValueError(f"Invalid Army metadata: {exc}") from exc
    tables = data.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Normalized data must contain a tables object")
    table_columns: dict[str, tuple[str, ...]] = {}
    for name, rows in tables.items():
        if name not in TABLES:
            raise ValueError(f"Unsupported normalized table: {name}")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Normalized table {name} must be an array of objects")
        table_columns[name] = columns_for(name, rows)
        for row in rows:
            for field in TABLES[name].key:
                if type(row.get(field)) not in (int, str):
                    raise ValueError(f"{name}.{field} must be a non-null integer or string key")
                if type(row[field]) is int and not -(2**63) <= row[field] < 2**63:
                    raise ValueError(f"{name}.{field} exceeds SQLite's integer key range")
            for field in ("army_id", "unit_id"):
                if field in row and row[field] is not None and type(row[field]) is not int:
                    raise ValueError(f"{name}.{field} must be an integer")
            if name in ("units", "army_lists", "factions") and type(row["id"]) is not int:
                raise ValueError(f"{name}.id must be an integer")
            if "name" in row and row["name"] is not None and not isinstance(row["name"], str):
                raise ValueError(f"{name}.name must be a string or null")
            if name == "army_lists":
                for field in ("slug", "kind"):
                    if row.get(field) is not None and not isinstance(row[field], str):
                        raise ValueError(f"army_lists.{field} must be a string or null")
            if name == "units" and type(row.get("source_defined")) is not bool:
                raise ValueError("units.source_defined must be a boolean")
    try:
        json_text(data)
        validate_normalized(data)
    except (KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError(f"Invalid normalized data: {exc}") from exc
    return table_columns


def sql_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json_text(value)
    # SQLite's integer range is narrower than JSON's; the original row remains exact.
    if type(value) is int and not -(2**63) <= value < 2**63:
        return str(value)
    return value


def raw_database_path(path: Path) -> Path:
    """Return the development archive path associated with a frontend database."""
    return path.with_name(f"{path.stem}.raw{path.suffix}")


def batched(
    rows: Iterable[tuple[Any, ...]], size: int = BATCH_SIZE
) -> Iterator[list[tuple[Any, ...]]]:
    """Yield bounded parameter batches without retaining an entire table."""
    iterator = iter(rows)
    while batch := list(islice(iterator, size)):
        yield batch


def insert_batched(
    connection: sqlite3.Connection, statement: str, rows: Iterable[tuple[Any, ...]]
) -> None:
    for batch in batched(rows):
        connection.executemany(statement, batch)


def create_raw_archive(connection: sqlite3.Connection, data: dict[str, Any]) -> None:
    """Store lossless normalized records outside the frontend database."""
    connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    connection.execute(
        f"CREATE TABLE {quote(METADATA_TABLE)} (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        f"CREATE TABLE {quote(RAW_ROWS_TABLE)} ("
        "table_name TEXT NOT NULL, row_position INTEGER NOT NULL, "
        f"{quote(ROW_JSON)} TEXT NOT NULL, "
        "PRIMARY KEY (table_name, row_position))"
    )
    metadata = {key: value for key, value in data.items() if key != "tables"}
    metadata["imported_tables"] = list(data["tables"])
    metadata[DATABASE_COMPATIBILITY_KEY] = DATABASE_COMPATIBILITY_VERSION
    insert_batched(
        connection,
        f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
        [(key, json_text(value)) for key, value in metadata.items()],
    )
    insert_batched(
        connection,
        f"INSERT INTO {quote(RAW_ROWS_TABLE)} (table_name, row_position, {quote(ROW_JSON)}) "
        "VALUES (?, ?, ?)",
        (
            (name, position, json_text(row))
            for name, rows in data["tables"].items()
            for position, row in enumerate(rows)
        ),
    )


def export_database(data: dict[str, Any], path: Path) -> None:
    """Replace ``path`` only after the complete normalized import passes validation.

    The frontend database contains queryable normalized columns only. A sibling
    ``.raw`` database preserves exact normalized rows, including absent versus
    null fields, for development use.
    """
    table_columns = validate_input(data)
    path = Path(path)
    archive_path = raw_database_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(filename)
    archive_descriptor, archive_filename = tempfile.mkstemp(
        prefix=f".{archive_path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(archive_descriptor)
    archive_temporary = Path(archive_filename)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                create_schema(connection, data["tables"], table_columns=table_columns)
                metadata = {key: value for key, value in data.items() if key != "tables"}
                metadata["imported_tables"] = list(data["tables"])
                metadata[DATABASE_COMPATIBILITY_KEY] = DATABASE_COMPATIBILITY_VERSION
                insert_batched(
                    connection,
                    f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
                    [(key, json_text(value)) for key, value in metadata.items()],
                )
                for name, rows in data["tables"].items():
                    columns = table_columns[name]
                    fields = ", ".join(map(quote, columns))
                    placeholders = ", ".join("?" for _ in columns)
                    insert_batched(
                        connection,
                        f"INSERT INTO {quote(name)} ({fields}) VALUES ({placeholders})",
                        (
                            tuple(sql_value(row.get(field)) for field in columns) for row in rows
                        ),
                    )
                create_indexes(connection)
                # The frontend database is an immutable snapshot. Persist planner
                # statistics at build time so read-only connections make informed
                # join-order choices without request-time analysis.
                connection.execute("ANALYZE")
        except (sqlite3.IntegrityError, OverflowError) as exc:
            raise ValueError(f"Invalid normalized database data: {exc}") from exc
        finally:
            connection.close()
        from .repository import Database

        Database(temporary).validate()
        archive_connection = sqlite3.connect(archive_temporary)
        try:
            with archive_connection:
                create_raw_archive(archive_connection, data)
            if archive_connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Raw archive integrity check failed")
        finally:
            archive_connection.close()
        os.replace(archive_temporary, archive_path)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
        archive_temporary.unlink(missing_ok=True)
