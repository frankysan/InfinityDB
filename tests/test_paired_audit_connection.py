"""Paired source/application read-only auditing of current split exports."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database import raw_database_path
from tests.test_audit_runtime_database_surface import _runtime_database
from tools.audit_normalization_links import audit_database as audit_normalization
from tools.audit_peripheral_semantics import audit_database as audit_peripherals
from tools.audit_relationship_semantics import audit_database as audit_relationships
from tools.paired_audit_connection import open_paired_audit_connection


def test_paired_connection_reads_source_views_without_modifying_siblings(
    tmp_path: Path,
) -> None:
    path = _runtime_database(tmp_path)
    raw = raw_database_path(path)
    before = tuple(hashlib.sha256(file.read_bytes()).hexdigest() for file in (path, raw))

    connection = open_paired_audit_connection(
        path, ("units", "profiles", "profile_payload_occurrences"),
    )
    try:
        assert connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM profile_payload_occurrences"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT name FROM temp.sqlite_master WHERE name = 'profiles'"
        ).fetchone()[0] == "profiles"
        with pytest.raises(sqlite3.OperationalError, match="view"):
            connection.execute("DELETE FROM profiles")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM logical_units")
    finally:
        connection.close()

    assert tuple(hashlib.sha256(file.read_bytes()).hexdigest() for file in (path, raw)) == before


def test_split_export_supports_all_three_relationship_audits(tmp_path: Path) -> None:
    path = _runtime_database(tmp_path)
    assert audit_relationships(path, current_only=True)["historicalReviewMode"] == (
        "not-applied-current-only"
    )
    assert audit_peripherals(path)["controllerEligibility"]["curatedDataRequired"] is True
    assert audit_normalization(path)["canonicalizationLinks"]["linkCount"] == 7


def test_paired_connection_rejects_mismatched_source_sibling(tmp_path: Path) -> None:
    path = _runtime_database(tmp_path)
    with sqlite3.connect(raw_database_path(path)) as raw:
        raw.execute(
            "UPDATE __infinity_metadata SET value = ? WHERE key = 'warnings'",
            ('"stale"',),
        )
    with pytest.raises(ValueError, match="metadata differ"):
        open_paired_audit_connection(path, ("profiles",))
