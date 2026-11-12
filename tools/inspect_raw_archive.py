"""Inspect exact Infinity Army source rows from a verified development input.

By default use the legacy lossless raw sibling, with its validated export
pair. Explicit --normalized selects a complete normalized JSON document bound
to the application export generation; neither route mutates its inputs.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.database.normalized_source import verified_normalized_document
from infinity_db.database.paths import raw_database_path
from infinity_db.database.publication import validate_database_pair
from infinity_db.database.schema import METADATA_TABLE, RAW_ROWS_TABLE, ROW_JSON, TABLES, quote

DEFAULT_APPLICATION = Path("data/generated/army.db")
MAX_PAGE_SIZE = 100


def inspect_raw_archive(
    application: Path,
    raw: Path | None = None,
    *,
    normalized: Path | None = None,
    command: str = "tables",
    table: str | None = None,
    position: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Return bounded source evidence, never opening an unpaired archive."""
    if command not in {"verify", "tables", "rows", "row"}:
        raise ValueError(f"Unknown inspection command: {command}")
    if command in {"rows", "row"} and table not in TABLES:
        raise ValueError(f"Unknown normalized source table: {table}")
    if position < 0 or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError("Position must be nonnegative and page size must be 1..100")
    application = Path(application)
    if normalized is not None:
        if raw is not None:
            raise ValueError("Select exactly one raw or normalized source input")
        document, _columns, _metadata, generation = verified_normalized_document(
            application, Path(normalized),
        )
        identity = {
            "application": str(application),
            "normalized": str(normalized),
            "pairSha256": generation,
            "pairStatus": "verified",
        }
        if command == "verify":
            return identity
        tables = document["tables"]
        if command == "tables":
            return {
                **identity,
                "tables": [
                    {"name": name, "rawRows": len(rows)}
                    for name, rows in sorted(tables.items())
                ],
            }
        assert table is not None
        if table not in tables:
            raise ValueError(f"Source table not present in this export: {table}")
        source_rows = tables[table]
        if command == "row":
            if position >= len(source_rows):
                raise ValueError(f"Raw row absent: {table}[{position}]")
            return {**identity, "table": table, "position": position,
                    "row": source_rows[position]}
        return {
            **identity, "table": table, "start": position, "limit": limit,
            "rows": [
                {"position": index, "row": source_rows[index]}
                for index in range(position, min(position + limit, len(source_rows)))
            ],
        }
    raw = Path(raw) if raw is not None else raw_database_path(application)
    pair_hash = validate_database_pair(application, raw_path=raw)
    identity = {
        "application": str(application),
        "raw": str(raw),
        "pairSha256": pair_hash,
        "pairStatus": "verified",
    }
    if command == "verify":
        return identity
    with closing(sqlite3.connect(raw.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        record = db.execute(
            f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = 'imported_tables'"
        ).fetchone()
        imported = json.loads(record[0]) if record is not None else None
        if (
            not isinstance(imported, list) or not imported
            or any(not isinstance(name, str) or name not in TABLES for name in imported)
            or len(imported) != len(set(imported))
        ):
            raise ValueError("Raw archive has invalid imported source-table metadata")
        if command == "tables":
            source_rows = db.execute(
                f"SELECT table_name, COUNT(*) FROM {quote(RAW_ROWS_TABLE)} "
                "GROUP BY table_name ORDER BY table_name"
            ).fetchall()
            counts = {str(name): int(count) for name, count in source_rows}
            if not counts.keys() <= set(imported):
                raise ValueError("Raw row archive contains undeclared source tables")
            return {
                **identity,
                "tables": [
                    {"name": name, "rawRows": counts.get(name, 0)}
                    for name in sorted(imported)
                ],
            }
        assert table is not None
        if table not in imported:
            raise ValueError(f"Source table not present in this export: {table}")
        if command == "row":
            match = db.execute(
                f"SELECT {quote(ROW_JSON)} FROM {quote(RAW_ROWS_TABLE)} "
                "WHERE table_name = ? AND row_position = ?",
                (table, position),
            ).fetchone()
            if match is None:
                raise ValueError(f"Raw row absent: {table}[{position}]")
            return {
                **identity, "table": table, "position": position,
                "row": json.loads(match[0]),
            }
        source_rows = db.execute(
            f"SELECT row_position, {quote(ROW_JSON)} FROM {quote(RAW_ROWS_TABLE)} "
            "WHERE table_name = ? AND row_position >= ? "
            "ORDER BY row_position LIMIT ?",
            (table, position, limit),
        ).fetchall()
        return {
            **identity, "table": table, "start": position,
            "limit": limit,
            "rows": [
                {"position": int(index), "row": json.loads(payload)}
                for index, payload in source_rows
            ],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--application", type=Path, default=DEFAULT_APPLICATION,
        help="application army.db; its paired raw sibling is selected by default",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--raw", type=Path, help="explicit paired raw archive")
    source.add_argument(
        "--normalized", type=Path,
        help="explicit normalized.json verified against the Army export generation",
    )
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("verify", help="validate shared raw/application metadata")
    actions.add_parser("tables", help="list normalized source tables with exact row counts")
    row = actions.add_parser("row", help="read one raw JSON row by normalized position")
    row.add_argument("table")
    row.add_argument("position", type=int)
    rows = actions.add_parser("rows", help="list bounded rows of one normalized source table")
    rows.add_argument("table")
    rows.add_argument("--start", type=int, default=0)
    rows.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        result = inspect_raw_archive(
            args.application, args.raw, normalized=args.normalized, command=args.action,
            table=getattr(args, "table", None),
            position=getattr(args, "position", getattr(args, "start", 0)),
            limit=getattr(args, "limit", 20),
        )
    except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"Source inspection refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
