"""Shared helpers for canonical profile/loadout runtime audits."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def canonical_json(value: Any, *, allow_nan: bool = True) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=allow_nan,
    )


def decode_raw(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")'))


def validate_schema(
    connection: sqlite3.Connection,
    expected_columns: Mapping[str, tuple[str, ...]],
    error_type: type[ValueError],
) -> None:
    for table, expected in expected_columns.items():
        actual = columns(connection, table)
        if not actual:
            raise error_type(f"Required table is missing: {table}")
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        if missing or unexpected:
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if unexpected:
                details.append(f"unclassified {', '.join(unexpected)}")
            raise error_type(
                f"Audit field classification for {table} is stale ({'; '.join(details)})"
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', ("_meta",)
    ).fetchone()
    if row is None:
        return {}
    try:
        value = json.loads(row["value"])
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def metadata_value(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', (key,)
    ).fetchone()
    return None if row is None else str(row["value"])


def database_identity(connection: sqlite3.Connection, path: Path) -> dict[str, Any]:
    meta = metadata(connection)
    return {
        "sha256": sha256_file(path),
        "applicationId": connection.execute("PRAGMA application_id").fetchone()[0],
        "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
        "compatibilityVersion": metadata_value(connection, "database_compatibility_version"),
        "snapshotArchiveSha256": meta.get("snapshotArchiveSha256"),
        "snapshotDownloadedOn": meta.get("snapshotDownloadedOn"),
    }


def extras_by_payload(
    connection: sqlite3.Connection,
    table: str,
    payload_id_field: str,
) -> dict[tuple[int, int], list[int]]:
    result: dict[tuple[int, int], list[int]] = defaultdict(list)
    query = (
        f'SELECT {payload_id_field}, occurrence_position, position, extra_id '
        f'FROM "{table}" ORDER BY {payload_id_field}, occurrence_position, position'
    )
    for row in connection.execute(query):
        result[(int(row[payload_id_field]), int(row["occurrence_position"]))].append(
            int(row["extra_id"])
        )
    return result


def item_relationships(
    connection: sqlite3.Connection,
    table: str,
    payload_id_field: str,
    extras: Mapping[tuple[int, int], list[int]] | None = None,
) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    query = f'SELECT * FROM "{table}" ORDER BY {payload_id_field}, position'
    for row in connection.execute(query):
        payload_id = int(row[payload_id_field])
        position = int(row["position"])
        item = {
            "item_id": row["item_id"],
            "display_order": row["display_order"],
            "quantity": row["quantity"],
            "raw": decode_raw(row["raw"]),
        }
        if extras is not None:
            item["extras"] = list(extras.get((payload_id, position), ()))
        result[payload_id].append(item)
    return result


def characteristic_relationships(
    connection: sqlite3.Connection,
    table: str,
    payload_id_field: str,
) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    query = f'SELECT * FROM "{table}" ORDER BY {payload_id_field}, position'
    for row in connection.execute(query):
        result[int(row[payload_id_field])].append(
            {"characteristic_id": row["characteristic_id"]}
        )
    return result


def variation_count(
    groups: Mapping[tuple[Any, ...], list[Mapping[str, Any]]], field: str
) -> int:
    count = 0
    for rows in groups.values():
        values = {canonical_json(row[field]) for row in rows}
        if len(values) > 1:
            count += 1
    return count


def grouped_rows(
    rows: Iterable[Mapping[str, Any]], fields: tuple[str, ...]
) -> dict[tuple[Any, ...], list[Mapping[str, Any]]]:
    result: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        result[tuple(row[field] for field in fields)].append(row)
    return result
