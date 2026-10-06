"""Published application-database integrity helpers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .paths import raw_database_path
from .schema import METADATA_TABLE, PUBLISHED_DATABASE_TABLES, Table, quote

PUBLISHED_CONTENT_SHA256_KEY = "published_content_sha256"
EXPORT_PAIR_SHA256_KEY = "export_pair_sha256"


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def export_pair_sha256(data: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    """Identify one complete application/raw export generation deterministically."""

    shared_metadata = {
        key: value for key, value in metadata.items() if key != EXPORT_PAIR_SHA256_KEY
    }
    return hashlib.sha256(
        _canonical_json_bytes({"data": data, "metadata": shared_metadata})
    ).hexdigest()


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


def _database_metadata(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"Database sibling does not exist: {path}")
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            return {
                str(key): str(value)
                for key, value in connection.execute(
                    f"SELECT key, value FROM {quote(METADATA_TABLE)} ORDER BY key"
                )
            }
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise ValueError(f"Could not read database sibling metadata: {path}: {exc}") from exc


def _pair_sha256(metadata: Mapping[str, str], path: Path) -> str | None:
    raw_value = metadata.get(EXPORT_PAIR_SHA256_KEY)
    if raw_value is None:
        return None
    try:
        value = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Database sibling has invalid export-pair metadata: {path}") from exc
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"Database sibling has invalid export-pair metadata: {path}")
    return value


def validate_database_pair(path: Path, *, raw_path: Path | None = None) -> str | None:
    """Validate that application and raw siblings belong to the same export generation.

    New exports carry a deterministic full-export fingerprint that covers source-only
    rows as well as shared metadata. Legacy pairs without that fingerprint remain
    accepted when their complete metadata dictionaries match.
    """

    application_path = Path(path)
    selected_raw_path = Path(raw_path) if raw_path is not None else raw_database_path(path)
    application_metadata = _database_metadata(application_path)
    raw_metadata = _database_metadata(selected_raw_path)
    application_pair_sha256 = _pair_sha256(application_metadata, application_path)
    raw_pair_sha256 = _pair_sha256(raw_metadata, selected_raw_path)

    if application_pair_sha256 != raw_pair_sha256:
        raise ValueError(
            "Application and raw database siblings were produced by different exports; "
            "rerun the database export to recover the pair"
        )
    if application_metadata != raw_metadata:
        raise ValueError(
            "Application and raw database sibling metadata differ; "
            "rerun the database export to recover the pair"
        )
    return application_pair_sha256
