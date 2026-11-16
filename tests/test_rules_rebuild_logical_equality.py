"""Cross-host rules rebuilds must compare semantic SQLite content, not B-tree bytes."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from infinity_db.sqlite_comparison import same_logical_rules_contents


def _make_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA application_id = 1229214257")
        db.execute("PRAGMA user_version = 9")
        db.execute("CREATE TABLE reference (id INTEGER PRIMARY KEY, description TEXT)")
        db.executemany(
            "INSERT INTO reference VALUES (?, ?)",
            [(1, "N5.3 ARO"), (2, "Deployment Phase")],
        )
        db.execute("CREATE INDEX reference_description ON reference(description)")
        db.execute("ANALYZE")


def test_rules_rebuild_ignores_writer_version_header_without_ignoring_rows(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "tracked.db", tmp_path / "rebuilt.db"
    _make_database(first)
    shutil.copyfile(first, second)
    altered = bytearray(second.read_bytes())
    altered[99] ^= 1  # SQLite header: version of last writer, not game rules.
    second.write_bytes(altered)

    assert first.read_bytes() != second.read_bytes()
    assert same_logical_rules_contents(first, second)

    with sqlite3.connect(second) as db:
        db.execute("UPDATE reference SET description = ? WHERE id = 2", ("changed",))
    assert not same_logical_rules_contents(first, second)


def test_rules_rebuild_rejects_changed_index_schema_and_database_identity(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "tracked.db", tmp_path / "rebuilt.db"
    _make_database(first)
    shutil.copyfile(first, second)
    assert same_logical_rules_contents(first, second)

    with sqlite3.connect(second) as db:
        db.execute("CREATE INDEX reference_id_desc ON reference(id, description)")
    assert not same_logical_rules_contents(first, second)

    shutil.copyfile(first, second)
    with sqlite3.connect(second) as db:
        db.execute("PRAGMA user_version = 8")
    assert not same_logical_rules_contents(first, second)


def test_rules_rebuild_ignores_row_insertion_order_but_not_content(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "first.db", tmp_path / "second.db"
    for path, values in (
        (first, [("a", 1), ("b", 2)]),
        (second, [("b", 2), ("a", 1)]),
    ):
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA application_id = 12345")
            db.execute("PRAGMA user_version = 17")
            db.execute("CREATE TABLE example (label TEXT, count INTEGER)")
            db.executemany("INSERT INTO example VALUES (?, ?)", values)
    assert first.read_bytes() != second.read_bytes()
    assert same_logical_rules_contents(first, second)

    with sqlite3.connect(second) as db:
        db.execute("UPDATE example SET count = 5 WHERE label = 'a'")
    assert not same_logical_rules_contents(first, second)


def test_rules_rebuild_missing_or_invalid_candidate_does_not_create_file(
    tmp_path: Path,
) -> None:
    first, missing = tmp_path / "first.db", tmp_path / "missing.db"
    _make_database(first)
    assert not same_logical_rules_contents(first, missing)
    assert not missing.exists()

    broken = tmp_path / "invalid.db"
    broken.write_bytes(b"not a sqlite database")
    assert not same_logical_rules_contents(first, broken)
    assert broken.read_bytes() == b"not a sqlite database"
