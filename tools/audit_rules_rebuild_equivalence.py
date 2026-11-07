"""Compare a rebuilt v9 rules database with the tracked release by logical rows.

Read-only diagnostic: the candidate is exported under ignored local/ and is removed.
Reports the SQLite versions, byte hashes, schema and per-table logical drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from tools.release_rules_export import export_release_rules

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data/generated/rules.db"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha(path.read_bytes())


def _tables(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        name: sql or ""
        for name, sql in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
        )
    }


def _row_bytes(row: tuple[Any, ...]) -> bytes:
    def encode(value: Any) -> Any:
        if isinstance(value, bytes):
            return {"binaryHex": value.hex()}
        return value

    return json.dumps(
        [encode(value) for value in row],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _logical_rows(conn: sqlite3.Connection, name: str) -> list[bytes]:
    quoted = '"' + name.replace('"', '""') + '"'
    return sorted(_row_bytes(row) for row in conn.execute(f"SELECT * FROM {quoted}"))


def audit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    release = root / "data/generated/rules.db"
    documents = load_curated_directory(root / "data/curated/rules")
    staging = root / "local"
    if not staging.is_dir():
        raise ValueError("The ignored local/ staging directory must exist")
    with tempfile.TemporaryDirectory(prefix="rules-rebuild-audit-", dir=staging) as temp:
        candidate = Path(temp) / "candidate.db"
        export_release_rules(documents, candidate, baseline=release)
        reference_bytes, candidate_bytes = release.read_bytes(), candidate.read_bytes()
        report: dict[str, Any] = {
            "sqliteVersion": sqlite3.sqlite_version,
            "sqlitePythonVersion": sqlite3.version if hasattr(sqlite3, "version") else None,
            "trackedSha256": _sha(reference_bytes),
            "rebuiltSha256": _sha(candidate_bytes),
            "sameBytes": reference_bytes == candidate_bytes,
            "trackedBytes": len(reference_bytes),
            "rebuiltBytes": len(candidate_bytes),
        }
        with closing(sqlite3.connect(release)) as before, closing(
            sqlite3.connect(candidate)
        ) as after:
            report["pragmas"] = {
                key: [before.execute(f"PRAGMA {key}").fetchone()[0],
                      after.execute(f"PRAGMA {key}").fetchone()[0]]
                for key in ("application_id", "user_version", "page_size",
                            "page_count", "freelist_count", "encoding")
            }
            schema_before, schema_after = _tables(before), _tables(after)
            report["sameTableSchema"] = schema_before == schema_after
            table_diffs: list[dict[str, Any]] = []
            for name in sorted(set(schema_before) | set(schema_after)):
                if name not in schema_before or name not in schema_after:
                    table_diffs.append({"table": name, "missing": True})
                    continue
                old, new = _logical_rows(before, name), _logical_rows(after, name)
                if old != new:
                    table_diffs.append({
                        "table": name,
                        "beforeRows": len(old),
                        "afterRows": len(new),
                        "beforeSha256": _sha(b"\n".join(old)),
                        "afterSha256": _sha(b"\n".join(new)),
                        "firstBefore": next((line.decode("utf-8")[:300]
                                             for line in old if line not in new), None),
                        "firstAfter": next((line.decode("utf-8")[:300]
                                            for line in new if line not in old), None),
                    })
            report["logicalDifferences"] = table_diffs
            report["sameLogicalRows"] = not table_diffs and report["sameTableSchema"]
        mismatches = [
            index for index, (left, right) in enumerate(
                zip(reference_bytes, candidate_bytes, strict=False)
            ) if left != right
        ]
        report["firstByteMismatchOffsets"] = mismatches[:12]
        report["byteMismatchCount"] = len(mismatches) + abs(
            len(reference_bytes) - len(candidate_bytes)
        )
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(audit(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
