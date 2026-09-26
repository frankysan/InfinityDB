from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database import raw_database_path
from tests.test_audit_runtime_database_surface import _runtime_database
from tools.audit_database_separation import (
    CANONICAL,
    CONTEXTUAL,
    SOURCE_ONLY,
    DatabaseSeparationAuditError,
    audit_database,
)

ROOT = Path(__file__).resolve().parents[1]


def _item(report: dict, table: str) -> dict:
    return next(item for item in report["inventory"] if item["table"] == table)


def test_database_separation_audit_classifies_complete_frontend_schema(tmp_path: Path) -> None:
    path = _runtime_database(tmp_path)

    report = audit_database(path, project_root=ROOT)

    assert report["summary"]["canonicalApplicationTableCount"] == 29
    assert report["summary"]["contextualApplicationTableCount"] == 53
    assert report["summary"]["sourceProvenanceOnlyTableCount"] == 47
    assert report["summary"]["runtimeSourceOnlyViolationCount"] == 0
    assert report["summary"]["foreignKeyBlockerCount"] == 0
    assert report["summary"]["validationSourceOnlyDependencyCount"] == 0
    assert report["summary"]["sourceOnlyStorageBytes"] == 0
    assert len(report["inventory"]) == 129
    assert report["database"]["tableCount"] == 82
    assert report["database"]["logicalInventoryTableCount"] == 129

    assert _item(report, "logical_units")["classification"] == CANONICAL
    assert _item(report, "application_army_sources")["classification"] == CONTEXTUAL
    assert _item(report, "application_fireteams")["classification"] == CANONICAL
    assert _item(report, "application_fireteam_charts")["classification"] == CONTEXTUAL
    assert _item(report, "army_units")["classification"] == CONTEXTUAL
    assert _item(report, "units")["classification"] == CONTEXTUAL
    assert _item(report, "profiles")["classification"] == SOURCE_ONLY
    assert _item(report, "profiles")["published"] is False
    assert _item(report, "profiles")["rawStored"] is True
    assert _item(report, "loadout_options")["classification"] == SOURCE_ONLY
    assert _item(report, "fireteams")["classification"] == SOURCE_ONLY
    assert _item(report, "relations")["classification"] == SOURCE_ONLY


def test_database_separation_audit_validates_lossless_raw_sibling(tmp_path: Path) -> None:
    path = _runtime_database(tmp_path)

    report = audit_database(path, project_root=ROOT)
    raw = report["rawArchive"]

    assert raw["status"] == "complete"
    assert raw["supportedNormalizedTableCount"] == 70
    assert raw["relationalNormalizedTableCount"] == 70
    assert raw["importedNormalizedTableCount"] == 54
    assert raw["storedRowCount"] == sum(raw["losslessTableRowCounts"].values())
    assert raw["tableRowCounts"] == raw["losslessTableRowCounts"]
    assert raw["metadataMatchesApplication"] is True


def test_database_separation_audit_rejects_raw_metadata_drift(tmp_path: Path) -> None:
    path = _runtime_database(tmp_path)
    raw_path = raw_database_path(path)
    connection = sqlite3.connect(raw_path)
    try:
        connection.execute(
            "UPDATE __infinity_metadata SET value = ? WHERE key = 'warnings'",
            (json.dumps(["drift"]),),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(DatabaseSeparationAuditError, match="metadata differ"):
        audit_database(path, project_root=ROOT)


def test_database_separation_audit_is_deterministic_and_read_only(tmp_path: Path) -> None:
    path = _runtime_database(tmp_path)
    raw_path = raw_database_path(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    raw_before = hashlib.sha256(raw_path.read_bytes()).hexdigest()

    first = audit_database(path, project_root=ROOT)
    second = audit_database(path, project_root=ROOT)

    assert first == second
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == raw_before
