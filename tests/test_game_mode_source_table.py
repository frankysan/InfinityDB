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
