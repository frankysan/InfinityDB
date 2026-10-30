"""Source-exact N5.3 Game Modes table and independent setup reconciliation."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from tools.audit_game_mode_source_table import (
    MANIFEST,
    PDF,
    PINNED,
    SETUP_MANIFEST,
    audit_game_mode_source,
    audit_source_files,
    main,
    verify_pinned_pdf,
)
from tools.audit_restrictions_source_chart import (
    CURATED as RESTRICTIONS_CURATED,
)
from tools.audit_restrictions_source_chart import (
    MANIFEST as RESTRICTIONS_MANIFEST,
)
from tools.audit_restrictions_source_chart import (
    PDF as RESTRICTIONS_PDF,
)
from tools.audit_restrictions_source_chart import (
    audit_source_files as audit_restrictions_files,
)
from tools.audit_restrictions_source_chart import (
    main as restrictions_main,
)
from tools.audit_restrictions_source_chart import (
    restrictions_audit,
)
from tools.audit_restrictions_source_chart import (
    verify_pinned_pdf as verify_restrictions_pdf,
)


def _inputs() -> tuple[dict, dict]:
    return (
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        json.loads(SETUP_MANIFEST.read_text(encoding="utf-8")),
    )


def test_game_mode_chart_corresponds_to_independent_setup_tables() -> None:
    result = audit_source_files()
    assert result["scope"] == "recommended-game-modes-not-mandatory-scenario-rules"
    assert result["sourcePage"] == 6
    assert result["corroboratingSourcePages"] == [146, 147]
    assert result["rowCount"] == 6
    assert result["durationScope"] == "recommended-minutes-not-round-count"
    assert result["swcScope"] == "base-allowance-excludes-unit-specific-bonuses"
    assert result["deploymentZoneScope"] == "two-dimensional-per-player-inches"
    assert [
        (
            r["name"], r["armyPoints"], r["swc"], tuple(r["tableInches"]),
            tuple(r["deploymentZoneInches"]), r["durationMinutes"],
        )
        for r in result["rows"]
    ] == list(PINNED)
    assert len(result["gameModesSha256"]) == 64
    assert len(result["independentSetupSha256"]) == 64


def test_game_mode_chart_rejects_drift_or_scenario_overrides() -> None:
    chart, setup = _inputs()
    assert audit_game_mode_source(chart, setup)["rowCount"] == 6
    for row_index, field, substitute in (
        (0, "swc", 4),
        (1, "deploymentZoneInches", [12, 32]),
        (2, "durationMinutes", 90),
        (3, "tableInches", [32, 48]),
        (4, "armyPoints", 300),
        (5, "name", "New Game"),
    ):
        changed = copy.deepcopy(chart)
        changed["rows"][row_index][field] = substitute
        with pytest.raises(ValueError, match="chart drift"):
            audit_game_mode_source(changed, setup)
    mandatory = copy.deepcopy(chart)
    mandatory["classification"]["scope"] = "mandatory-scenario-rule"
    with pytest.raises(ValueError, match="scope drift"):
        audit_game_mode_source(mandatory, setup)
    changed_setup = copy.deepcopy(setup)
    changed_setup["rows"][0]["recommendedTableInches"] = [48, 48]
    with pytest.raises(ValueError, match="cross-check failed"):
        audit_game_mode_source(chart, changed_setup)


def test_optional_pdf_check_verifies_game_mode_rows() -> None:
    pytest.importorskip("pymupdf")
    if not PDF.is_file():
        pytest.skip("Pinned local N5.3 PDF not available")
    report = audit_source_files(pdf_path=PDF)
    assert len(report["verifiedPdfSha256"]) == 64
    chart, _ = _inputs()
    assert verify_pinned_pdf(PDF, chart) == report["verifiedPdfSha256"]
    changed = copy.deepcopy(chart)
    changed["rows"][0]["durationMinutes"] = 70
    with pytest.raises(ValueError, match="source row mismatch"):
        verify_pinned_pdf(PDF, changed)
    changed = copy.deepcopy(chart)
    changed["rows"][0]["deploymentZoneInches"] = [12, 24]
    with pytest.raises(ValueError, match="source dimensions mismatch"):
        verify_pinned_pdf(PDF, changed)


def test_game_mode_chart_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_game_mode_source_table"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Game Modes source rows: 6" in output
    assert "150 pts: Beginner Games; SWC 3; 40 minutes" in output
    assert "400 pts: Large-Scale Games; SWC 8; 120 minutes" in output
    assert "scenario-specific setup and forces take precedence" in output


def _restriction_inputs() -> tuple[dict, dict]:
    manifest = json.loads(RESTRICTIONS_MANIFEST.read_text(encoding="utf-8"))
    curated = json.loads(RESTRICTIONS_CURATED.read_text(encoding="utf-8"))
    return manifest, {row["id"]: row for row in curated["records"]}


def test_n53_restrictions_chart_six_subjects_and_fourteen_prohibitions() -> None:
    report = audit_restrictions_files()
    assert report["rowCount"] == 6
    assert report["negativeConditionCount"] == 14
    assert report["scope"] == "source-restriction-conditions-not-live-action-legality"
    assert report["sourceOnlyTroopTypeSubjects"] == ["TAG", "VH", "REM"]
    assert len(report["missingTypedRelations"]) == 7
    assert report["automaticLegalityInference"] is False
    assert {
        (entry["subject"], entry["action"])
        for entry in report["conditionalRelationWarnings"]
    } == {
        ("Motorcycle", "upward-jump"),
        ("Irregular", "lieutenant-selection"),
    }
    assert {entry["action"] for entry in report["missingTypedRelations"]} >= {
        "enter-prone", "declare-cautious-movement", "use-ladders", "lieutenant-selection"
    }
    assert len(report["manifestSha256"]) == 64
    assert len(report["curatedSha256"]) == 64


def test_n53_restrictions_chart_rejects_changed_scope_actions_and_relations() -> None:
    chart, records = _restriction_inputs()
    assert restrictions_audit(chart, records)["negativeConditionCount"] == 14
    for row_index, field, replacement in (
        (0, "subjectKind", "skill"),
        (1, "ownerRecordId", "skill:jump"),
        (3, "subject", "HI"),
    ):
        edited = copy.deepcopy(chart)
        edited["rows"][row_index][field] = replacement
        with pytest.raises(ValueError, match="Restrictions Chart"):
            restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["classification"]["action"] = "permission-to-act"
    with pytest.raises(ValueError, match="provenance/scope"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["rows"][1]["restrictions"][4]["scope"] = "while-mounted"
    with pytest.raises(ValueError, match="action-scope drift"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["rows"][1]["restrictions"][4]["action"] = "declare-climb"
    with pytest.raises(ValueError, match="repeated action"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["rows"][1]["restrictions"][4]["targetRecordId"] = "skill:climb"
    with pytest.raises(ValueError, match="target identity drift"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(records)
    edited["equipment:motorcycle"]["facts"]["restrictions"] = []
    with pytest.raises(ValueError, match="Motorcycle maintained restriction"):
        restrictions_audit(chart, edited)


def test_n53_restrictions_optional_pinned_pdf_exact_six_lines() -> None:
    pytest.importorskip("pymupdf")
    if not RESTRICTIONS_PDF.is_file():
        pytest.skip("Pinned N5.3 PDF unavailable")
    report = audit_restrictions_files(pdf_path=RESTRICTIONS_PDF)
    assert report["verifiedPdfSha256"] == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    chart, _ = _restriction_inputs()
    edited = copy.deepcopy(chart)
    edited["rows"][1]["sourceText"] = edited["rows"][1]["sourceText"].replace(
        "an upwards Jump", "any Jump",
    )
    with pytest.raises(ValueError, match="printed line mismatch"):
        verify_restrictions_pdf(RESTRICTIONS_PDF, edited)


def test_n53_restrictions_chart_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_restrictions_source_chart"])
    assert restrictions_main() == 0
    output = capsys.readouterr().out
    assert "6 rows, 14 negative conditions" in output
    assert "Source-only: no action-legality" in output
