from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from infinity_db.sqlite_determinism import (
    CANONICAL_FILE_CHANGE_COUNTER,
    CANONICAL_PAGE_SIZE,
    configure_deterministic_sqlite,
    normalize_sqlite_header,
    vacuum_deterministic_sqlite,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _database(path: Path, *, page_size: int, auto_vacuum: str, secure_delete: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"PRAGMA page_size = {page_size}")
        connection.execute(f"PRAGMA auto_vacuum = {auto_vacuum}")
        connection.execute(f"PRAGMA secure_delete = {secure_delete}")
        connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany(
            "INSERT INTO items (id, value) VALUES (?, ?)",
            [(number, f"value-{number:04d}") for number in range(1, 800)],
        )
        connection.commit()
        connection.execute("DELETE FROM items WHERE id % 7 = 0")
        connection.commit()
        connection.execute("CREATE INDEX items_value ON items(value)")
        connection.execute("ANALYZE")
        connection.commit()
        vacuum_deterministic_sqlite(connection)
    finally:
        connection.close()
    normalize_sqlite_header(path)


def test_sqlite_finalization_normalizes_physical_file_layout(tmp_path: Path) -> None:
    first = tmp_path / "first.db"
    second = tmp_path / "second.db"

    _database(first, page_size=4096, auto_vacuum="NONE", secure_delete="OFF")
    _database(second, page_size=8192, auto_vacuum="FULL", secure_delete="ON")

    assert _sha256(first) == _sha256(second)
    with sqlite3.connect(first) as connection:
        assert connection.execute("PRAGMA page_size").fetchone()[0] == CANONICAL_PAGE_SIZE
        assert connection.execute("PRAGMA auto_vacuum").fetchone()[0] == 0
        assert connection.execute("PRAGMA freelist_count").fetchone()[0] == 0
        assert connection.execute("PRAGMA encoding").fetchone()[0] == "UTF-8"
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"

    header = first.read_bytes()[:100]
    expected = CANONICAL_FILE_CHANGE_COUNTER.to_bytes(4, "big")
    assert header[24:28] == expected
    assert header[92:96] == expected


def test_normalized_sqlite_header_remains_writable(tmp_path: Path) -> None:
    path = tmp_path / "writable.db"
    _database(path, page_size=8192, auto_vacuum="FULL", secure_delete="ON")

    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO items (id, value) VALUES (1000, 'after-normalization')")
        connection.commit()
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT value FROM items WHERE id = 1000").fetchone()[0] == (
            "after-normalization"
        )


def test_configure_deterministic_sqlite_requires_no_transaction() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE items (id INTEGER)")
        connection.execute("INSERT INTO items VALUES (1)")
        with pytest.raises(ValueError, match="no active transaction"):
            configure_deterministic_sqlite(connection)


def test_vacuum_deterministic_sqlite_requires_committed_database() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE items (id INTEGER)")
        connection.execute("INSERT INTO items VALUES (1)")
        with pytest.raises(ValueError, match="committed database"):
            vacuum_deterministic_sqlite(connection)


def test_normalize_sqlite_header_rejects_non_database(tmp_path: Path) -> None:
    path = tmp_path / "not.db"
    path.write_bytes(b"not sqlite")
    with pytest.raises(ValueError, match="Not a SQLite format 3 database"):
        normalize_sqlite_header(path)
