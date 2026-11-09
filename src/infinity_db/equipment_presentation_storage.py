"""Opt-in Army v27 publication of reviewed Equipment presentation encodings.

The base Army exporter and tracked v26 release remain unchanged. A completed
two-file build extends only its disposable, matched application/raw export pair.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .database.publication import (
    PUBLISHED_CONTENT_SHA256_KEY,
    published_content_sha256,
    validate_database_pair,
)
from .database.schema import (
    DATABASE_COMPATIBILITY_KEY,
    METADATA_TABLE,
    PUBLISHED_DATABASE_TABLES,
    Table,
)
from .equipment_config import (
    EQUIPMENT_PRESENTATION_CONFIG_FORMAT,
    EQUIPMENT_PRESENTATION_CONFIG_VERSION,
    EquipmentPresentationEncoding,
    load_equipment_presentation_config,
    parse_equipment_presentation_config,
)
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite

ARMY_SCHEMA_VERSION = 27
ARMY_COMPATIBILITY_VERSION = 36
BASE_SCHEMA_VERSION = 26
BASE_COMPATIBILITY_VERSION = 35

EQUIPMENT_TABLES = {
    "equipment_presentation_metadata": Table(
        ("id",),
        ("format", "version", "source_sha256", "export_pair_sha256",
         "row_count", "content_sha256"),
    ),
    "equipment_presentation_encodings": Table(
        ("equipment_id",),
        ("position", "characteristic_id", "characteristic", "reason"),
    ),
}
ARMY_V27_PUBLISHED_TABLES = {**PUBLISHED_DATABASE_TABLES, **EQUIPMENT_TABLES}


def _fingerprint(encodings: tuple[EquipmentPresentationEncoding, ...]) -> str:
    document = [
        {"equipment_id": entry.equipment_id, "characteristic": entry.characteristic,
         "reason": entry.reason}
        for entry in encodings
    ]
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _source_characteristics(
    connection: sqlite3.Connection,
    encodings: tuple[EquipmentPresentationEncoding, ...],
) -> tuple[Any, ...]:
    rows = connection.execute("SELECT id,name FROM characteristics").fetchall()
    matches: list[Any] = []
    for entry in encodings:
        found = [
            row[0] for row in rows
            if str(row[1]).casefold() == entry.characteristic.casefold()
        ]
        if len(found) != 1:
            raise ValueError(
                f"Equipment presentation characteristic {entry.characteristic!r} "
                "does not uniquely match the selected Army source"
            )
        matches.append(found[0])
    return tuple(matches)


def read_equipment_encodings(
    connection: sqlite3.Connection,
) -> tuple[EquipmentPresentationEncoding, ...]:
    """Validate the complete v27 read model without accessing authored JSON."""
    meta = connection.execute(
        "SELECT format,version,source_sha256,export_pair_sha256,row_count,content_sha256 "
        "FROM equipment_presentation_metadata WHERE id=1"
    ).fetchone()
    pair_row = connection.execute(
        f"SELECT value FROM {METADATA_TABLE} WHERE key='export_pair_sha256'"
    ).fetchone()
    try:
        pair = json.loads(pair_row[0]) if pair_row else None
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid Equipment presentation Army source identity") from exc
    if (
        meta is None or len(meta[2]) != 64 or len(meta[5]) != 64
        or tuple(meta[:2]) != (
            EQUIPMENT_PRESENTATION_CONFIG_FORMAT,
            EQUIPMENT_PRESENTATION_CONFIG_VERSION,
        )
        or meta[3] != pair
        or not isinstance(pair, str)
        or len(pair) != 64
        or meta[4] != 2
    ):
        raise ValueError("Invalid Equipment presentation source metadata")
    rows = connection.execute(
        "SELECT equipment_id,position,characteristic_id,characteristic,reason "
        "FROM equipment_presentation_encodings ORDER BY position"
    ).fetchall()
    if len(rows) != meta[4] or any(row[1] != idx for idx, row in enumerate(rows)):
        raise ValueError("Incomplete or unordered Equipment presentation mappings")
    document = {
        "format": EQUIPMENT_PRESENTATION_CONFIG_FORMAT,
        "formatVersion": EQUIPMENT_PRESENTATION_CONFIG_VERSION,
        "encodings": [
            {"equipment_id": row[0], "characteristic": row[3], "reason": row[4]}
            for row in rows
        ],
    }
    encodings = parse_equipment_presentation_config(document)
    if _fingerprint(encodings) != meta[5]:
        raise ValueError("Equipment presentation content fingerprint differs")
    expected_ids = _source_characteristics(connection, encodings)
    if any(row[2] != expected_ids[index] for index, row in enumerate(rows)):
        raise ValueError("Equipment presentation characteristic source identity differs")
    return encodings


def publish_equipment_encodings(
    army: Path, raw: Path, source: Path,
) -> None:
    """Extend a matched disposable v26 pair; keep raw/published metadata identical."""
    encodings = load_equipment_presentation_config(source)
    if len(encodings) != 2:
        raise ValueError("Reviewed Equipment presentation inventory requires two entries")
    pair = validate_database_pair(army, raw_path=raw)
    if pair is None:
        raise ValueError("Equipment presentation publication requires pinned Army generation")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    with closing(sqlite3.connect(army)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA user_version").fetchone()[0] != BASE_SCHEMA_VERSION:
            raise ValueError("Equipment presentation publication requires Army v26")
        characteristic_ids = _source_characteristics(connection, encodings)
        with connection:
            connection.execute(
                """CREATE TABLE equipment_presentation_metadata (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    format TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
                    export_pair_sha256 TEXT NOT NULL CHECK(length(export_pair_sha256)=64),
                    row_count INTEGER NOT NULL CHECK(row_count>0),
                    content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64)
                )"""
            )
            connection.execute(
                """CREATE TABLE equipment_presentation_encodings (
                    equipment_id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL UNIQUE CHECK(position>=0),
                    characteristic_id NOT NULL UNIQUE REFERENCES characteristics(id),
                    characteristic TEXT NOT NULL,
                    reason TEXT NOT NULL
                )"""
            )
            connection.execute(
                "INSERT INTO equipment_presentation_metadata VALUES (1,?,?,?,?,?,?)",
                (
                    EQUIPMENT_PRESENTATION_CONFIG_FORMAT,
                    EQUIPMENT_PRESENTATION_CONFIG_VERSION, source_sha, pair,
                    len(encodings), _fingerprint(encodings),
                ),
            )
            connection.executemany(
                "INSERT INTO equipment_presentation_encodings VALUES (?,?,?,?,?)",
                (
                    (entry.equipment_id, index, characteristic_ids[index],
                     entry.characteristic, entry.reason)
                    for index, entry in enumerate(encodings)
                ),
            )
            read_equipment_encodings(connection)
            checksum = published_content_sha256(
                connection, definitions=ARMY_V27_PUBLISHED_TABLES,
            )
            new_metadata: dict[str, object] = {
                PUBLISHED_CONTENT_SHA256_KEY: checksum,
                DATABASE_COMPATIBILITY_KEY: ARMY_COMPATIBILITY_VERSION,
            }
            for key, value in new_metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                    (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(army)
    with closing(sqlite3.connect(raw)) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != BASE_SCHEMA_VERSION:
            raise ValueError("Equipment presentation raw export requires Army v26")
        with connection:
            for key, value in new_metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                    (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(raw)
    validate_database_pair(army, raw_path=raw)
