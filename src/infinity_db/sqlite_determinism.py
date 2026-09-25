"""Canonical SQLite artifact settings for byte-reproducible generated databases."""

from __future__ import annotations

import sqlite3
from pathlib import Path

CANONICAL_PAGE_SIZE = 4096
CANONICAL_CACHE_KIB = 64 * 1024
CANONICAL_FILE_CHANGE_COUNTER = 1
_SQLITE_HEADER_SIZE = 100
_SQLITE_MAGIC = b"SQLite format 3\x00"
_FILE_CHANGE_COUNTER_OFFSET = 24
_VERSION_VALID_FOR_OFFSET = 92


def configure_deterministic_sqlite(connection: sqlite3.Connection) -> None:
    """Remove host SQLite defaults that can change generated database bytes.

    Call this before creating schema objects in a new generated database. The
    settings cover persistent file-format choices and build-time choices that
    can otherwise vary with the SQLite library's compile-time defaults.
    """
    if connection.in_transaction:
        raise ValueError("Deterministic SQLite configuration requires no active transaction")

    connection.execute(f"PRAGMA page_size = {CANONICAL_PAGE_SIZE}")
    connection.execute("PRAGMA auto_vacuum = NONE")
    connection.execute("PRAGMA encoding = 'UTF-8'")
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.execute("PRAGMA secure_delete = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute(f"PRAGMA cache_size = -{CANONICAL_CACHE_KIB}")
    connection.execute("PRAGMA mmap_size = 0")
    connection.execute("PRAGMA threads = 1")


def vacuum_deterministic_sqlite(connection: sqlite3.Connection) -> None:
    """Repack a committed generated database using the canonical file settings."""
    if connection.in_transaction:
        raise ValueError("Deterministic SQLite finalization requires a committed database")

    connection.execute(f"PRAGMA page_size = {CANONICAL_PAGE_SIZE}")
    connection.execute("PRAGMA auto_vacuum = NONE")
    connection.execute("PRAGMA secure_delete = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute(f"PRAGMA cache_size = -{CANONICAL_CACHE_KIB}")
    connection.execute("PRAGMA mmap_size = 0")
    connection.execute("PRAGMA threads = 1")
    connection.execute("VACUUM")


def normalize_sqlite_header(path: Path) -> None:
    """Normalize transaction-history-only fields in a closed SQLite artifact.

    SQLite's file change counter (offset 24) and version-valid-for value (offset
    92) reflect how many write transactions happened while the file was built.
    They are not application data, but different SQLite builds can arrive at a
    different counter for an otherwise byte-identical final database. Keeping
    both values equal preserves validity of the in-header database-size field.
    """
    path = Path(path)
    with path.open("r+b") as handle:
        header = handle.read(_SQLITE_HEADER_SIZE)
        if len(header) < _SQLITE_HEADER_SIZE or not header.startswith(_SQLITE_MAGIC):
            raise ValueError(f"Not a SQLite format 3 database: {path}")
        counter = CANONICAL_FILE_CHANGE_COUNTER.to_bytes(4, "big")
        handle.seek(_FILE_CHANGE_COUNTER_OFFSET)
        handle.write(counter)
        handle.seek(_VERSION_VALID_FOR_OFFSET)
        handle.write(counter)
