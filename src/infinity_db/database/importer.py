"""Validate normalized data and atomically publish a complete SQLite database."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from infinity_army_data.metadata import MetadataError, validate_metadata_envelope
from infinity_army_data.normalize import FORMAT_NAME, FORMAT_VERSION, validate_normalized

from .schema import (
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    ROW_JSON,
    TABLES,
    columns_for,
    create_schema,
    quote,
)


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def validate_input(data: dict[str, Any]) -> None:
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
    for name, rows in tables.items():
        if name not in TABLES:
            raise ValueError(f"Unsupported normalized table: {name}")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Normalized table {name} must be an array of objects")
        columns_for(name, rows)
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


def sql_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json_text(value)
    # SQLite's integer range is narrower than JSON's; the original row remains exact.
    if type(value) is int and not -(2**63) <= value < 2**63:
        return str(value)
    return value


def export_database(data: dict[str, Any], path: Path) -> None:
    """Replace ``path`` only after the complete normalized import passes validation.

    Each normalized table is a SQLite table with the same field names. Object and
    array fields are JSON text. ``__row_json`` preserves exact values and absent
    versus null fields; metadata and warnings live in ``__infinity_metadata``.
    """
    validate_input(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(filename)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                create_schema(connection, data["tables"])
                metadata = {key: value for key, value in data.items() if key != "tables"}
                metadata["imported_tables"] = list(data["tables"])
                metadata[DATABASE_COMPATIBILITY_KEY] = DATABASE_COMPATIBILITY_VERSION
                connection.executemany(
                    f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
                    [(key, json_text(value)) for key, value in metadata.items()],
                )
                for name, rows in data["tables"].items():
                    columns = columns_for(name, rows)
                    fields = ", ".join(map(quote, (*columns, ROW_JSON)))
                    placeholders = ", ".join("?" for _ in range(len(columns) + 1))
                    connection.executemany(
                        f"INSERT INTO {quote(name)} ({fields}) VALUES ({placeholders})",
                        [
                            (*[sql_value(row.get(field)) for field in columns], json_text(row))
                            for row in rows
                        ],
                    )
        except (sqlite3.IntegrityError, OverflowError) as exc:
            raise ValueError(f"Invalid normalized database data: {exc}") from exc
        finally:
            connection.close()
        from .repository import Database

        Database(temporary).validate()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
