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


def _changed_fields(
    before: Any, after: Any, path: str = "$", *, limit: int = 24,
) -> list[dict[str, Any]]:
    """Bounded key/index-level report for a changed structured JSON value."""
    if before == after or limit <= 0:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        result: list[dict[str, Any]] = []
        for key in sorted(before.keys() | after.keys()):
            if len(result) >= limit:
                break
            result.extend(_changed_fields(
                before.get(key), after.get(key), f"{path}.{key}",
                limit=limit - len(result),
            ))
        return result
    if isinstance(before, list) and isinstance(after, list):
        result = []
        for index in range(max(len(before), len(after))):
            if len(result) >= limit:
                break
            result.extend(_changed_fields(
                before[index] if index < len(before) else None,
                after[index] if index < len(after) else None,
                f"{path}[{index}]", limit=limit - len(result),
            ))
        return result
    return [{"path": path, "tracked": str(before)[:160], "rebuilt": str(after)[:160]}]


def _record_field_changes(
    old: sqlite3.Connection, new: sqlite3.Connection,
) -> list[dict[str, Any]]:
    columns = [row[1] for row in old.execute("PRAGMA table_info(records)")]
    query = "SELECT * FROM records ORDER BY collection_id, id"
    before = {(row[0], row[1]): row for row in old.execute(query)}
    after = {(row[0], row[1]): row for row in new.execute(query)}
    result = []
    for key in sorted(before.keys() | after.keys()):
        if before.get(key) == after.get(key):
            continue
        fields: list[dict[str, Any]] = []
        for column, left, right in zip(
            columns, before.get(key) or (), after.get(key) or (), strict=False,
        ):
            if left == right:
                continue
            if column.endswith("_json") and isinstance(left, str) and isinstance(right, str):
                fields.extend(_changed_fields(
                    json.loads(left), json.loads(right), column,
                ))
            else:
                fields.append({
                    "path": column, "tracked": str(left)[:160], "rebuilt": str(right)[:160],
                })
        result.append({"identity": key, "fieldChanges": fields[:32]})
        if len(result) >= 10:
            break
    return result


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
            if any(item["table"] == "records" for item in table_diffs):
                report["recordFieldDifferences"] = _record_field_changes(before, after)
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


def audit_v10_candidate(
    candidate: Path, release: Path = RULES,
) -> dict[str, Any]:
    """Compare v9's common rules data with staged v10 without rebuilding either."""
    from infinity_db.rules_database import RulesDatabase

    RulesDatabase(release).validate()
    RulesDatabase(candidate).validate()
    with closing(sqlite3.connect(release)) as old, closing(
        sqlite3.connect(candidate)
    ) as new:
        old_version = old.execute("PRAGMA user_version").fetchone()[0]
        new_version = new.execute("PRAGMA user_version").fetchone()[0]
        if (old_version, new_version) != (9, 10):
            raise ValueError("v10 parity requires a tracked v9 release and v10 candidate")
        previous = _tables(old)
        incoming = _tables(new)
        shared = sorted(set(previous) & set(incoming))
        new_tables = sorted(set(incoming) - set(previous))
        removed_tables = sorted(set(previous) - set(incoming))
        schema_changed = [
            table for table in shared if previous[table] != incoming[table]
        ]
        changed = []
        for table in shared:
            if table.startswith("sqlite_stat"):
                continue
            left, right = _logical_rows(old, table), _logical_rows(new, table)
            if left != right:
                changed.append({
                    "table": table, "beforeRows": len(left), "afterRows": len(right),
                })
        query = "SELECT * FROM records WHERE id = 'scenario:battleground'"
        record_before = old.execute(query).fetchall()
        record_after = new.execute(query).fetchall()
        if len(record_before) != 1 or len(record_after) != 1:
            raise ValueError("Expected one Battleground record in each schema")
        columns = [row[1] for row in old.execute("PRAGMA table_info(records)")]
        changes = {}
        for index, column in enumerate(columns):
            a, b = record_before[0][index], record_after[0][index]
            if a == b:
                continue
            changes[column] = (
                _changed_fields(json.loads(a), json.loads(b), limit=40)
                if column.endswith("_json") else [str(a)[:90], str(b)[:90]]
            )
        report = {
            "oldVersion": old_version, "newVersion": new_version,
            "removedTables": removed_tables, "addedTables": new_tables,
            "commonSchemaChanges": schema_changed,
            "commonRowChanges": changed,
            "battlegroundFieldChanges": changes,
        }
        expected_new = {
            "deployed_objects", "deployed_object_attributes",
            "deployed_object_attribute_sources", "deployed_object_deliveries",
            "deployed_object_unit_uses", "deployed_object_unresolved",
            "deployed_object_metadata",
        }
        if removed_tables or schema_changed or set(new_tables) != expected_new:
            raise ValueError("v10 changed an unexpected rules table or shared schema")
        if {item["table"] for item in changed} != {
            "__rules_metadata", "records", "scenario_publications",
        }:
            raise ValueError("v10 changed unexpected existing rules data")
        old_metadata = dict(old.execute("SELECT key,value FROM __rules_metadata"))
        new_metadata = dict(new.execute("SELECT key,value FROM __rules_metadata"))
        if (
            set(old_metadata) != set(new_metadata)
            or json.loads(old_metadata["formatVersion"]) != 9
            or json.loads(new_metadata["formatVersion"]) != 10
            or any(
                old_metadata[key] != new_metadata[key]
                for key in old_metadata
                if key not in {"formatVersion", "databaseCompatibilityVersion"}
            )
        ):
            raise ValueError("v10 changed unexpected rules metadata")
        old_records = {
            (row[0], row[1]): row
            for row in old.execute("SELECT * FROM records")
        }
        new_records = {
            (row[0], row[1]): row
            for row in new.execute("SELECT * FROM records")
        }
        if set(old_records) != set(new_records):
            raise ValueError("v10 added or removed legacy rules records")
        changed_ids = [
            key for key in old_records
            if old_records[key] != new_records[key]
        ]
        battleground = ("its-season-18-2026.09.01", "scenario:battleground")
        if changed_ids != [battleground] or set(changes) != {"facts_json"}:
            raise ValueError(
                f"v10 changed rules beyond Battleground geometry: "
                f"changed IDs={changed_ids[:12]!r}, columns={sorted(changes)!r}"
            )
        previous_facts = json.loads(old_records[battleground][columns.index("facts_json")])
        current_facts = json.loads(new_records[battleground][columns.index("facts_json")])
        before_configs = previous_facts.get("configurations", [])
        after_configs = current_facts.get("configurations", [])
        if len(before_configs) != 3 or len(after_configs) != 3:
            raise ValueError("Unexpected Battleground configuration count")
        for earlier, updated in zip(before_configs, after_configs, strict=True):
            old_geo = earlier["geometry"]
            new_geo = updated["geometry"]
            annotations = new_geo.pop("annotations", None)
            if not isinstance(annotations, list) or not annotations:
                raise ValueError("Battleground dimension annotations missing")
            old_elements = old_geo["elements"]
            new_elements = new_geo["elements"]
            added = new_elements[len(old_elements):]
            if (
                new_elements[:len(old_elements)] != old_elements
                or {item.get("id") for item in added} != {
                    "table-center-line", "deployment-a-label",
                    "deployment-b-label", "sector-near-a-label",
                    "sector-near-b-label", "sector-center-label",
                }
            ):
                raise ValueError("Unexpected Battleground geometry change")
            new_geo["elements"] = old_elements
        if previous_facts != current_facts:
            raise ValueError("Battleground changed beyond map annotations and labels")
        old_publications = {
            (row[0], row[1]): row
            for row in old.execute("SELECT * FROM scenario_publications")
        }
        new_publications = {
            (row[0], row[1]): row
            for row in new.execute("SELECT * FROM scenario_publications")
        }
        if (
            set(old_publications) != set(new_publications)
            or [key for key in old_publications
                if old_publications[key] != new_publications[key]] != [battleground]
        ):
            raise ValueError("Unexpected scenario publication content drift")
        report["parity"] = "passed"
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--v10-candidate", type=Path,
        help="Read-only comparison of tracked v9 against an existing v10 rules.db",
    )
    args = parser.parse_args(argv)
    report = audit_v10_candidate(args.v10_candidate) if args.v10_candidate else audit()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
