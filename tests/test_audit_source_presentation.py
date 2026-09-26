from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_audit_runtime_database_surface import _runtime_database
from tools import audit_source_presentation as audit

ROOT = Path(__file__).resolve().parents[1]


def _field(report: dict, table: str, field: str) -> dict:
    table_item = next(item for item in report["inventory"] if item["table"] == table)
    return next(item for item in table_item["fields"] if item["field"] == field)


def test_source_presentation_audit_covers_complete_source_schema(tmp_path: Path) -> None:
    report = audit.audit_database(_runtime_database(tmp_path))

    assert report["summary"]["sourceTableCount"] == 70
    assert report["summary"]["sourceFieldCount"] == 441
    assert report["summary"]["confirmedGapCount"] == 8
    assert report["summary"]["reviewQueueCount"] == 2
    assert sum(report["summary"]["fieldStatusCounts"].values()) == 441
    assert report["rawEvidence"]["status"] == "available"
    assert report["rawEvidence"]["normalizedTableCount"] == 70

    assert _field(report, "profiles", "move_1")["status"] == audit.EXPLICIT
    assert _field(report, "units", "notes")["status"] == audit.UNREPRESENTED
    assert _field(report, "profiles", "is_structure")["status"] == audit.EXPLICIT
    assert (
        _field(report, "metadata_hacking_programs", "position")["status"]
        == audit.EXPLICIT
    )
    assert _field(report, "army_skills", "item_id")["status"] == audit.NORMALIZATION


def test_source_presentation_audit_records_expected_gap_families(tmp_path: Path) -> None:
    report = audit.audit_database(_runtime_database(tmp_path))
    gap_ids = {item["id"] for item in report["confirmedGaps"]}

    assert gap_ids == {
        "declared_faction_membership",
        "fireteams",
        "includes",
        "peripheral_controller_links",
        "reinforcement_parentage",
        "selection_dependencies",
        "unit_notes",
        "unit_options",
    }
    fireteams = next(item for item in report["confirmedGaps"] if item["id"] == "fireteams")
    assert fireteams["layer"] == "application_database_only"
    assert fireteams["tables"] == [
        "application_fireteams",
        "application_fireteam_types",
        "application_fireteam_members",
    ]
    assert report["applicationEvidence"]["declaredFactionMembershipCount"] == 1
    assert report["applicationEvidence"]["unitOptionCount"] == 1


def test_source_presentation_policy_fails_closed_on_unclassified_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(audit.TABLE_POLICY, "units")

    with pytest.raises(audit.SourcePresentationAuditError, match="policy is stale"):
        audit._validate_policy()


def test_source_presentation_cli_writes_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _runtime_database(tmp_path)
    output = tmp_path / "report.json"

    assert audit.main([str(database), "--output", str(output)]) == 0
    captured = capsys.readouterr().out
    assert audit.FORMAT in captured
    assert "70 tables | 441 fields" in captured
    assert json.loads(output.read_text(encoding="utf-8"))["formatVersion"] == 1
