"""Read-only logical SQLite comparisons for source and publication rebuilds.

Byte-identical SQLite files are not required: cross-host writer headers and
page layouts may differ even when the schema and stored data are equivalent.
This module does not stage, promote, or modify database artifacts.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path


def same_logical_rules_contents(reference: Path, candidate: Path) -> bool:
    """Compare SQLite schema, identity pragmas, and every table row multiset.

    Includes application-owned indexes and optimizer statistics; ignores
    physical page order and incidental SQLite writer-header differences.
    Missing or invalid files fail closed without creating database files.
    """
    try:
        with (
            closing(sqlite3.connect(
                reference.resolve().as_uri() + "?mode=ro", uri=True,
            )) as old,
            closing(sqlite3.connect(
                candidate.resolve().as_uri() + "?mode=ro", uri=True,
            )) as new,
        ):
            for pragma in ("application_id", "user_version", "encoding", "page_size"):
                if old.execute(f"PRAGMA {pragma}").fetchone() != new.execute(
                    f"PRAGMA {pragma}",
                ).fetchone():
                    return False
            schema_sql = (
                "SELECT type, name, tbl_name, sql "
                "FROM sqlite_master ORDER BY type, name, tbl_name"
            )
            entries = old.execute(schema_sql).fetchall()
            if entries != new.execute(schema_sql).fetchall():
                return False
            for kind, name, _owner, _sql in entries:
                if kind != "table":
                    continue
                quoted = '"' + name.replace('"', '""') + '"'
                query = f"SELECT * FROM {quoted}"
                if Counter(old.execute(query)) != Counter(new.execute(query)):
                    return False
            return bool(entries)
    except sqlite3.DatabaseError:
        return False
