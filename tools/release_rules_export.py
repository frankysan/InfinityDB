"""Export staged rules without changing the active release schema or Restrictions."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

from infinity_db.rules_database import RulesDatabase, export_rules_database

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RULES = ROOT / "data/generated/rules.db"
RESTRICTIONS_CHART = ROOT / "config/validation/restrictions-source-chart.json"


def export_release_rules(
    documents: list, destination: Path, *, baseline: Path | None = None,
) -> None:
    """Preserve the active v8/v9 schema and reviewed Restrictions when staging."""
    source = baseline or RELEASE_RULES
    existing = RulesDatabase(source)
    existing.validate()
    with closing(sqlite3.connect(source)) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version not in (8, 9):
        raise ValueError("Cannot stage an unsupported release rules schema")
    manifest = (
        json.loads(RESTRICTIONS_CHART.read_text(encoding="utf-8"))
        if version == 9 else None
    )
    export_rules_database(documents, destination, restrictions_manifest=manifest)
    staged = RulesDatabase(destination)
    staged.validate()
    with closing(sqlite3.connect(destination)) as connection:
        staged_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if (
        staged_version != version
        or staged.restrictions_payload() != existing.restrictions_payload()
    ):
        raise ValueError("Staging changed release schema or reviewed Restrictions")


def same_logical_rules_contents(reference: Path, candidate: Path) -> bool:
    """Compare all SQLite schema objects and row multisets, not physical pages.

    SQLite minor versions may write different B-tree layouts and writer-version
    headers even when the curated rules database contains identical data.
    Match the complete schema (including indexes), version/identity pragmas
    and every table's exact stored rows, including optimizer statistics.
    This is a read-only *rebuild* check; it does not alter either release file.
    """
    with closing(sqlite3.connect(reference)) as old, closing(
        sqlite3.connect(candidate)
    ) as new:
        for pragma in ("application_id", "user_version", "encoding", "page_size"):
            if old.execute(f"PRAGMA {pragma}").fetchone() != new.execute(
                f"PRAGMA {pragma}"
            ).fetchone():
                return False
        schema = (
            "SELECT type, name, tbl_name, sql "
            "FROM sqlite_master ORDER BY type, name, tbl_name"
        )
        entries = old.execute(schema).fetchall()
        if entries != new.execute(schema).fetchall():
            return False
        for kind, name, _owner, _sql in entries:
            if kind != "table":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            query = f"SELECT * FROM {quoted}"
            if Counter(old.execute(query)) != Counter(new.execute(query)):
                return False
    return True
