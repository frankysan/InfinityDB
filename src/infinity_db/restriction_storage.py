"""Opt-in SQLite v9 candidate for source-scoped restriction constraints.

This is deliberately not called by the released v8 exporter or runtime API.
It proves an additive, negative-only storage/read contract before promotion.
"""
from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from infinity_db.restriction_conditions import (
    ACTION_OPERATIONS,
    CONDITION_SCOPES,
    SUBJECT_SELECTORS,
    compile_restriction_conditions,
)
from infinity_db.rules_database import RULES_APPLICATION_ID

CANDIDATE_TABLE = "restriction_constraints"
CANDIDATE_SCHEMA_VERSION = 9
CANDIDATE_COMPATIBILITY_VERSION = 11

_CREATE_SQL = """
CREATE TABLE restriction_constraints (
    source_id TEXT NOT NULL,
    source_page INTEGER NOT NULL CHECK (source_page > 0),
    source_pdf_sha256 TEXT NOT NULL CHECK (length(source_pdf_sha256) = 64),
    position INTEGER NOT NULL CHECK (position >= 0),
    subject TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    owner_record_id TEXT,
    polarity TEXT NOT NULL CHECK (polarity = 'prohibition'),
    action TEXT NOT NULL,
    operation_kind TEXT NOT NULL CHECK (operation_kind IN (
        'state-entry', 'skill-declaration', 'terrain-traversal',
        'directional-skill-movement', 'army-role-selection'
    )),
    target_record_id TEXT,
    scope TEXT NOT NULL,
    qualifier_json TEXT NOT NULL,
    PRIMARY KEY (source_id, source_page, subject, action),
    UNIQUE (source_id, source_page, position),
    CHECK (
        (subject_kind = 'troop-type' AND owner_record_id IS NULL)
        OR (subject_kind <> 'troop-type' AND owner_record_id IS NOT NULL)
    ),
    CHECK (
        (operation_kind = 'terrain-traversal' AND target_record_id IS NULL)
        OR (operation_kind <> 'terrain-traversal' AND target_record_id IS NOT NULL)
    )
);
CREATE INDEX restriction_constraints_owner
    ON restriction_constraints(owner_record_id);
CREATE INDEX restriction_constraints_target
    ON restriction_constraints(target_record_id);
"""


def stage_candidate_restrictions(
    connection: sqlite3.Connection,
    manifest: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> int:
    """Stage a v9 candidate atomically; leave all legacy tables and rows alone.

    Call only on a disposable copied v8 database. This is not a runtime
    migration/upgrade path and does not change PRAGMA user_version or metadata.
    """
    conditions = compile_restriction_conditions(manifest, records)
    digest = manifest.get("sourcePdfSha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("Restriction candidate requires a pinned source fingerprint")

    if connection.execute("PRAGMA application_id").fetchone()[0] != RULES_APPLICATION_ID:
        raise ValueError("Restriction candidate requires an InfinityDB rules database")
    if connection.execute("PRAGMA user_version").fetchone()[0] != 8:
        raise ValueError("Restriction candidate requires a v8 staging copy")
    base_compat = connection.execute(
        "SELECT value FROM __rules_metadata WHERE key = ?",
        ("databaseCompatibilityVersion",),
    ).fetchone()
    if base_compat is None or json.loads(base_compat[0]) != 10:
        raise ValueError("Restriction candidate requires compatibility revision 10")
    existing = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (CANDIDATE_TABLE,),
    ).fetchone()
    if existing is not None:
        raise ValueError("Restriction candidate already staged")

    connection.execute("SAVEPOINT stage_restriction_candidate")
    try:
        for statement in _CREATE_SQL.split(";"):
            if statement.strip():
                connection.execute(statement)
        for position, restriction in enumerate(conditions):
            connection.execute(
                "INSERT INTO restriction_constraints "
                "(source_id, source_page, source_pdf_sha256, position, subject, "
                "subject_kind, owner_record_id, polarity, action, operation_kind, "
                "target_record_id, scope, qualifier_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    manifest["sourceId"], manifest["sourcePage"], digest, position,
                    restriction.subject, restriction.subject_kind, restriction.owner_record_id,
                    "prohibition", restriction.action, restriction.operation_kind,
                    restriction.target_record_id, restriction.scope,
                    json.dumps(restriction.qualifier, sort_keys=True, separators=(",", ":")),
                ),
            )
        count = connection.execute(
            "SELECT COUNT(*) FROM restriction_constraints"
        ).fetchone()[0]
        if count != 14:
            raise ValueError("Restriction candidate incomplete")
        connection.execute("RELEASE SAVEPOINT stage_restriction_candidate")
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT stage_restriction_candidate")
        connection.execute("RELEASE SAVEPOINT stage_restriction_candidate")
        raise
    return count


def validate_restriction_filters(
    subject: str | None, record_id: str | None,
) -> None:
    """Validate filters for both v8-unavailable and v9-supported read models."""
    if subject is not None and (
        not isinstance(subject, str) or subject not in SUBJECT_SELECTORS
    ):
        raise ValueError("Unknown Restrictions source subject")
    if record_id is not None and (
        not isinstance(record_id, str)
        or re.fullmatch(r"[a-z][a-z0-9-]*:[a-z0-9-]+", record_id) is None
    ):
        raise ValueError("Invalid Restrictions record identifier")


def validate_restriction_snapshot(connection: sqlite3.Connection) -> None:
    """Reject incomplete, mismatched, or broadened v9-only constraint snapshots."""
    rows = connection.execute(
        "SELECT source_id, source_page, source_pdf_sha256, subject, subject_kind, "
        "owner_record_id, polarity, action, operation_kind, target_record_id, "
        "scope, qualifier_json FROM restriction_constraints ORDER BY position"
    ).fetchall()
    if len(rows) != 14:
        raise ValueError("Invalid v9 Restrictions snapshot: expected 14 conditions")
    provenance = {(row[0], row[1], row[2]) for row in rows}
    if len(provenance) != 1:
        raise ValueError("Invalid v9 Restrictions snapshot: mixed provenance")
    source_id, page, sha = next(iter(provenance))
    if (source_id, page) != ("n5-core-v5.3-pdf", 194) or (
        not isinstance(sha, str) or re.fullmatch(r"[a-f0-9]{64}", sha) is None
    ):
        raise ValueError("Invalid v9 Restrictions snapshot: source provenance drift")
    expected = [
        (subject, kind, owner, action, target, scope, operation, qualifier)
        for subject, (kind, owner) in SUBJECT_SELECTORS.items()
        for action, scope in CONDITION_SCOPES[subject].items()
        for operation, target, qualifier in (ACTION_OPERATIONS[action],)
    ]
    for row, (subject, kind, owner, action, target, scope, operation, qualifier) in zip(
        rows, expected, strict=True,
    ):
        try:
            stored_qualifier = json.loads(row[11])
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid v9 Restrictions snapshot: qualifier JSON") from exc
        if (
            (row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10])
            != (subject, kind, owner, "prohibition", action, operation, target, scope)
            or stored_qualifier != qualifier
        ):
            raise ValueError(
                f"Invalid v9 Restrictions snapshot: source condition drift: {subject}"
            )
    # This validates bounded source semantics, not live action legality.


def candidate_restrictions_payload(
    connection: sqlite3.Connection,
    *,
    subject: str | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    """Future additive API shape; no permission inference or generic relation changes.

    Subject and record filters are conjunctive. A record matches either endpoint;
    source-only Troop Types never acquire artificial canonical IDs.
    """
    validate_restriction_filters(subject, record_id)
    where = []
    params: list[str] = []
    if subject is not None:
        where.append("subject = ?")
        params.append(subject)
    if record_id is not None:
        where.append("(owner_record_id = ? OR target_record_id = ?)")
        params.extend((record_id, record_id))
    sql = (
        "SELECT source_id, source_page, source_pdf_sha256, subject, subject_kind, "
        "owner_record_id, polarity, action, operation_kind, target_record_id, "
        "scope, qualifier_json FROM restriction_constraints"
        + (f" WHERE {' AND '.join(where)}" if where else "")
        + " ORDER BY position"
    )
    rows = connection.execute(sql, tuple(params)).fetchall()
    source = connection.execute(
        "SELECT source_id, source_page, source_pdf_sha256 "
        "FROM restriction_constraints ORDER BY position LIMIT 1"
    ).fetchone()
    if source is None:
        raise ValueError("Restriction candidate contains no source-reviewed constraints")
    # A filtered empty result is not evidence of positive legality.
    items = [
        {
            "subject": row[3],
            "subjectKind": row[4],
            "ownerRecordId": row[5],
            "polarity": row[6],
            "action": row[7],
            "operation": {"kind": row[8], "qualifier": json.loads(row[11])},
            "targetRecordId": row[9],
            "scope": row[10],
        }
        for row in rows
    ]
    return {
        "formatVersion": 1,
        "source": {
            "id": source[0],
            "page": source[1],
            "pdfSha256": source[2],
        },
        "polarity": "prohibition",
        "items": items,
        "evaluationSupported": False,
    }
