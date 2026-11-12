"""Paired source/application read-only auditing of current split exports."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from infinity_db.database import raw_database_path
from tests.test_audit_runtime_database_surface import _runtime_database
from tools.audit_normalization_links import audit_database as audit_normalization
from tools.audit_normalization_links import main as normalization_main
from tools.audit_peripheral_semantics import audit_database as audit_peripherals
from tools.audit_peripheral_semantics import main as peripherals_main
from tools.audit_relationship_semantics import audit_database as audit_relationships
from tools.audit_relationship_semantics import main as relationships_main
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


def test_verified_normalized_source_views_match_raw_sqlite_without_retained_sibling(
    tmp_path: Path,
) -> None:
    normalized = tmp_path / "normalized.json"
    path = _runtime_database(tmp_path, normalized_output=normalized)
    raw = raw_database_path(path)
    required = (
        "profiles", "profile_includes", "option_includes", "profile_peripherals",
        "option_peripherals", "army_units", "loadout_options",
        "profile_payload_occurrences", "application_armies",
    )
    with closing(open_paired_audit_connection(path, required)) as legacy:
        expected = {
            table: [tuple(row) for row in legacy.execute(f'SELECT * FROM "{table}"')]
            for table in required
        }
    source_bytes = (path.read_bytes(), normalized.read_bytes())
    assert "profile_includes" not in json.loads(
        normalized.read_text(encoding="utf-8")
    )["tables"]
    raw.unlink()

    connection = open_paired_audit_connection(path, required, normalized=normalized)
    try:
        for table, rows in expected.items():
            assert [tuple(row) for row in connection.execute(
                f'SELECT * FROM "{table}"'
            )] == rows, table
        assert connection.execute(
            "SELECT name FROM temp.sqlite_master WHERE name='profiles'"
        ).fetchone()[0] == "profiles"
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM profiles")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM application_armies")
    finally:
        connection.close()
    assert not raw.exists()
    assert (path.read_bytes(), normalized.read_bytes()) == source_bytes


def test_normalized_source_matches_all_three_semantic_audits_without_raw(
    tmp_path: Path,
) -> None:
    normalized = tmp_path / "normalized.json"
    path = _runtime_database(tmp_path, normalized_output=normalized)
    legacy = (
        audit_normalization(path),
        audit_peripherals(path, include_details=True),
        audit_relationships(path, current_only=True, include_details=True),
    )
    raw_database_path(path).unlink()
    result = (
        audit_normalization(path, normalized=normalized),
        audit_peripherals(path, include_details=True, normalized=normalized),
        audit_relationships(
            path, current_only=True, include_details=True, normalized=normalized,
        ),
    )
    assert result == legacy
    assert not raw_database_path(path).exists()


def test_normalized_semantic_audit_cli_routes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    normalized = tmp_path / "normalized.json"
    path = _runtime_database(tmp_path, normalized_output=normalized)
    raw_database_path(path).unlink()
    arguments = [str(path), "--normalized", str(normalized)]

    assert normalization_main(arguments) == 0
    assert "Source filter joins:" in capsys.readouterr().out
    assert peripherals_main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["controllerEligibility"][
        "curatedDataRequired"
    ] is True
    assert relationships_main([*arguments, "--current-only"]) == 0
    assert json.loads(capsys.readouterr().out)["historicalReviewMode"] == (
        "not-applied-current-only"
    )


@pytest.mark.parametrize("tamper", ("row", "generation", "missing"))
def test_explicit_normalized_input_rejects_provenance_drift_without_raw_fallback(
    tmp_path: Path, tamper: str,
) -> None:
    normalized = tmp_path / "normalized.json"
    path = _runtime_database(tmp_path, normalized_output=normalized)
    if tamper == "row":
        document = json.loads(normalized.read_text(encoding="utf-8"))
        document["tables"]["units"][0]["name"] = "changed without review"
        normalized.write_text(json.dumps(document), encoding="utf-8")
    elif tamper == "generation":
        with sqlite3.connect(path) as database:
            database.execute(
                "UPDATE __infinity_metadata SET value=? WHERE key='export_pair_sha256'",
                (json.dumps("0" * 64),),
            )
    else:
        normalized.unlink()
    expected = FileNotFoundError if tamper == "missing" else ValueError
    with pytest.raises(expected):
        open_paired_audit_connection(path, ("profiles",), normalized=normalized)


def test_explicit_normalized_source_is_verified_even_when_no_table_is_missing(
    tmp_path: Path,
) -> None:
    normalized = tmp_path / "normalized.json"
    path = _runtime_database(tmp_path, normalized_output=normalized)
    with closing(open_paired_audit_connection(
        path, ("application_armies",), normalized=normalized,
    )) as connection:
        assert connection.execute("SELECT COUNT(*) FROM application_armies").fetchone()[0]
    document = json.loads(normalized.read_text(encoding="utf-8"))
    document["tables"]["units"][0]["name"] = "changed without review"
    normalized.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        open_paired_audit_connection(
            path, ("application_armies",), normalized=normalized,
        )


def test_paired_connection_rejects_mismatched_source_sibling(tmp_path: Path) -> None:
    path = _runtime_database(tmp_path)
    with sqlite3.connect(raw_database_path(path)) as raw:
        raw.execute(
            "UPDATE __infinity_metadata SET value = ? WHERE key = 'warnings'",
            ('"stale"',),
        )
    with pytest.raises(ValueError, match="metadata differ"):
        open_paired_audit_connection(path, ("profiles",))
