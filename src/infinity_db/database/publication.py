"""Published application-database integrity helpers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping

from .schema import PUBLISHED_DATABASE_TABLES, Table, quote

PUBLISHED_CONTENT_SHA256_KEY = "published_content_sha256"


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def published_content_sha256(
    connection: sqlite3.Connection,
    *,
    definitions: Mapping[str, Table] = PUBLISHED_DATABASE_TABLES,
) -> str:
    """Hash every published table deterministically, independent of indexes/statistics."""

    digest = hashlib.sha256()
    for name, definition in definitions.items():
        columns = tuple(
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({quote(name)})")
        )
        if not columns:
            raise ValueError(f"Published database is missing table {name}")
        digest.update(_json_bytes([name, list(columns)]))
        fields = ", ".join(map(quote, columns))
        order = ", ".join(map(quote, definition.key))
        for row in connection.execute(
            f"SELECT {fields} FROM {quote(name)} ORDER BY {order}"
        ):
            digest.update(_json_bytes(list(row)))
    return digest.hexdigest()
