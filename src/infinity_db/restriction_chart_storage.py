"""Relational N5 Restrictions chart publication, separate from prohibition constraints."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

CHART_SCHEMA_VERSION = 13
CHART_COMPATIBILITY_VERSION = 15
CHART_SCOPE = "reviewed-negative-conditions-not-action-legality"
CHART_COLLECTION = "n5-core-v5.3"
CHART_SOURCE = "n5-core-v5.3-pdf"
CHART_PAGE = 194


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                   allow_nan=False).encode("utf-8")
    ).hexdigest()


def _source_row(connection: sqlite3.Connection) -> sqlite3.Row | tuple:
    row = connection.execute(
        "SELECT s.id,s.url,s.sha256,s.page_count FROM sources s "
        "JOIN collections c ON c.id=s.collection_id "
        "WHERE s.collection_id=? AND s.id=? AND c.status='current' "
        "AND s.authority='primary' AND s.kind='pdf'",
        (CHART_COLLECTION, CHART_SOURCE),
    ).fetchone()
    if row is None:
        raise ValueError("Restrictions chart requires the current primary core PDF")
    return row


def _constraint_rows(connection: sqlite3.Connection) -> dict[tuple[str, str], tuple]:
    rows = connection.execute(
        "SELECT subject,subject_kind,owner_record_id,action,operation_kind,"
        "target_record_id,scope,qualifier_json,source_id,source_page,"
        "source_pdf_sha256 FROM restriction_constraints ORDER BY position"
    ).fetchall()
    if len(rows) != 14:
        raise ValueError("Restrictions chart requires 14 normalized source constraints")
    return {(row[0], row[3]): tuple(row) for row in rows}


def _validate_chart_document(
    connection: sqlite3.Connection, chart: dict[str, Any],
) -> None:
    source = _source_row(connection)
    constraints = _constraint_rows(connection)
    if (
        not isinstance(chart, dict)
        or type(chart.get("formatVersion")) is not int
        or chart["formatVersion"] != 1
        or chart.get("scope") != CHART_SCOPE
        or chart.get("source") != {
            "id": CHART_SOURCE, "page": CHART_PAGE, "url": source[1],
        }
        or not isinstance(chart.get("rows"), list)
        or len(chart["rows"]) != 6
        or not isinstance(source[2], str)
        or len(source[2]) != 64
        or type(source[3]) is not int
        or source[3] < CHART_PAGE
    ):
        raise ValueError("Restrictions chart source, version or row inventory differs")
    seen_rows: set[str] = set()
    seen_conditions: set[tuple[str, str]] = set()
    for row in chart["rows"]:
        if not isinstance(row, dict) or set(row) != {
            "id", "name", "category", "subjectKind", "ownerHref",
            "ownerRecordId", "sourceSubject", "conditions",
        }:
            raise ValueError("Invalid Restrictions chart row structure")
        if any(not isinstance(row[key], str) or not row[key]
               for key in ("id", "name", "category", "subjectKind", "sourceSubject")):
            raise ValueError("Incomplete Restrictions chart row")
        if row["id"] in seen_rows or not isinstance(row["conditions"], list):
            raise ValueError("Duplicate Restrictions chart row or missing conditions")
        seen_rows.add(row["id"])
        if not row["conditions"]:
            raise ValueError("Restrictions chart row cannot be empty")
        for optional in ("ownerHref", "ownerRecordId"):
            if row[optional] is not None and not isinstance(row[optional], str):
                raise ValueError("Invalid Restrictions chart owner reference")
        for condition in row["conditions"]:
            if not isinstance(condition, dict) or set(condition) != {
                "action", "label", "scope", "href", "targetRecordId", "operation", "note",
            }:
                raise ValueError("Invalid Restrictions chart condition structure")
            if any(not isinstance(condition[key], str) or not condition[key]
                   for key in ("action", "label", "scope")):
                raise ValueError("Incomplete Restrictions chart condition")
            for optional in ("href", "targetRecordId", "note"):
                if condition[optional] is not None and not isinstance(condition[optional], str):
                    raise ValueError("Invalid Restrictions chart condition annotation")
            operation = condition["operation"]
            if (
                not isinstance(operation, dict) or set(operation) != {"kind", "qualifier"}
                or not isinstance(operation["kind"], str) or not operation["kind"]
                or not isinstance(operation["qualifier"], dict)
                or any(not isinstance(key, str) or not isinstance(value, str)
                       for key, value in operation["qualifier"].items())
            ):
                raise ValueError("Invalid Restrictions chart operation/qualifier")
            identity = (row["sourceSubject"], condition["action"])
            if identity in seen_conditions or identity not in constraints:
                raise ValueError("Unknown or repeated Restrictions chart source condition")
            seen_conditions.add(identity)
            expected = constraints[identity]
            try:
                expected_qualifier = json.loads(expected[7])
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid Restrictions source constraint qualifier") from exc
            if (
                (row["subjectKind"], row["ownerRecordId"], condition["action"],
                 operation["kind"], condition["targetRecordId"], condition["scope"],
                 operation["qualifier"])
                != (expected[1], expected[2], expected[3], expected[4], expected[5],
                    expected[6], expected_qualifier)
                or (expected[8], expected[9], expected[10])
                != (CHART_SOURCE, CHART_PAGE, source[2])
            ):
                raise ValueError("Restrictions chart differs from normalized source constraints")
    if seen_conditions != set(constraints):
        raise ValueError("Restrictions chart does not cover all normalized source conditions")


def _read_unchecked(connection: sqlite3.Connection) -> dict[str, Any]:
    meta = connection.execute(
        "SELECT source_id,source_page,scope,format_version,content_sha256,"
        "row_count,condition_count FROM restriction_chart_metadata WHERE id=1"
    ).fetchone()
    if meta is None:
        raise ValueError("Missing Restrictions chart publication")
    collection = connection.execute(
        "SELECT source_collection_id FROM restriction_chart_metadata WHERE id=1"
    ).fetchone()
    source = _source_row(connection)
    if (
        collection is None or collection[0] != CHART_COLLECTION
        or (meta[0], meta[1], meta[2], meta[3]) != (CHART_SOURCE, CHART_PAGE, CHART_SCOPE, 1)
        or source[0] != CHART_SOURCE
    ):
        raise ValueError("Invalid Restrictions chart metadata")
    chart: dict[str, Any] = {
        "formatVersion": meta[3],
        "scope": meta[2],
        "source": {"id": meta[0], "page": meta[1], "url": source[1]},
        "rows": [],
    }
    for row in connection.execute(
        "SELECT id,name,category,subject_kind,owner_href,owner_record_id,source_subject "
        "FROM restriction_chart_rows ORDER BY position"
    ):
        item = {
            "id": row[0], "name": row[1], "category": row[2],
            "subjectKind": row[3], "ownerHref": row[4],
            "ownerRecordId": row[5], "sourceSubject": row[6],
            "conditions": [],
        }
        for condition in connection.execute(
            "SELECT position,action,label,scope,href,target_record_id,operation_kind,note "
            "FROM restriction_chart_conditions WHERE row_id=? ORDER BY position",
            (row[0],),
        ):
            qualifier_rows = connection.execute(
                "SELECT name,value FROM restriction_chart_qualifiers "
                "WHERE row_id=? AND condition_position=? ORDER BY position",
                (row[0], condition[0]),
            ).fetchall()
            item["conditions"].append({
                "action": condition[1], "label": condition[2], "scope": condition[3],
                "href": condition[4], "targetRecordId": condition[5],
                "operation": {
                    "kind": condition[6], "qualifier": dict(qualifier_rows),
                },
                "note": condition[7],
            })
        chart["rows"].append(item)
    if len(chart["rows"]) != meta[5] or (
        sum(len(row["conditions"]) for row in chart["rows"]) != meta[6]
    ):
        raise ValueError("Restrictions chart inventory is incomplete")
    if _digest(chart) != meta[4]:
        raise ValueError("Restrictions chart content fingerprint differs")
    _validate_chart_document(connection, chart)
    return chart


def read_restriction_chart(connection: sqlite3.Connection) -> dict[str, Any]:
    """Read and fully validate the published chart; never read a static JSON file."""
    return _read_unchecked(connection)


def validate_restriction_chart_snapshot(connection: sqlite3.Connection) -> None:
    read_restriction_chart(connection)


def stage_restriction_chart(
    connection: sqlite3.Connection, chart: dict[str, Any],
) -> None:
    """Stage a source-checked chart in the v12 export transaction."""
    if connection.execute("PRAGMA user_version").fetchone()[0] != 12:
        raise ValueError("Embedded Restrictions chart requires Rules v12 baseline")
    _validate_chart_document(connection, chart)
    schema_sql = """
        CREATE TABLE restriction_chart_metadata (
            id INTEGER PRIMARY KEY CHECK (id=1),
            source_collection_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_page INTEGER NOT NULL CHECK (source_page>0),
            scope TEXT NOT NULL,
            format_version INTEGER NOT NULL CHECK (format_version=1),
            content_sha256 TEXT NOT NULL CHECK (length(content_sha256)=64),
            row_count INTEGER NOT NULL CHECK (row_count>0),
            condition_count INTEGER NOT NULL CHECK (condition_count>0),
            FOREIGN KEY(source_collection_id,source_id)
                REFERENCES sources(collection_id,id)
        );
        CREATE TABLE restriction_chart_rows (
            id TEXT PRIMARY KEY,
            position INTEGER NOT NULL UNIQUE CHECK (position>=0),
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subject_kind TEXT NOT NULL,
            owner_href TEXT,
            owner_record_id TEXT,
            source_subject TEXT NOT NULL
        );
        CREATE TABLE restriction_chart_conditions (
            row_id TEXT NOT NULL,
            position INTEGER NOT NULL CHECK (position>=0),
            action TEXT NOT NULL,
            label TEXT NOT NULL,
            scope TEXT NOT NULL,
            href TEXT,
            target_record_id TEXT,
            operation_kind TEXT NOT NULL,
            note TEXT,
            PRIMARY KEY(row_id,position),
            UNIQUE(row_id,action),
            FOREIGN KEY(row_id) REFERENCES restriction_chart_rows(id)
        );
        CREATE TABLE restriction_chart_qualifiers (
            row_id TEXT NOT NULL,
            condition_position INTEGER NOT NULL,
            position INTEGER NOT NULL CHECK (position>=0),
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY(row_id,condition_position,position),
            UNIQUE(row_id,condition_position,name),
            FOREIGN KEY(row_id,condition_position)
                REFERENCES restriction_chart_conditions(row_id,position)
        );
        """
    for statement in schema_sql.split(";"):
        if statement.strip():
            connection.execute(statement)
    connection.execute(
        "INSERT INTO restriction_chart_metadata VALUES (1,?,?,?,?,?,?,?,?)",
        (CHART_COLLECTION, CHART_SOURCE, CHART_PAGE, CHART_SCOPE, 1,
         _digest(chart), len(chart["rows"]),
         sum(len(row["conditions"]) for row in chart["rows"])),
    )
    for position, row in enumerate(chart["rows"]):
        connection.execute(
            "INSERT INTO restriction_chart_rows VALUES (?,?,?,?,?,?,?,?)",
            (row["id"], position, row["name"], row["category"], row["subjectKind"],
             row["ownerHref"], row["ownerRecordId"], row["sourceSubject"]),
        )
        for condition_position, condition in enumerate(row["conditions"]):
            operation = condition["operation"]
            connection.execute(
                "INSERT INTO restriction_chart_conditions VALUES (?,?,?,?,?,?,?,?,?)",
                (row["id"], condition_position, condition["action"], condition["label"],
                 condition["scope"], condition["href"], condition["targetRecordId"],
                 operation["kind"], condition["note"]),
            )
            for qualifier_position, (name, value) in enumerate(
                sorted(operation["qualifier"].items())
            ):
                connection.execute(
                    "INSERT INTO restriction_chart_qualifiers VALUES (?,?,?,?,?)",
                    (row["id"], condition_position, qualifier_position, name, value),
                )
    read_restriction_chart(connection)
