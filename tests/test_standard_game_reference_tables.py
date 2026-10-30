"""Review the printed N5.3 Retreat! and generic table-size source rows."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from infinity_db.curated import load_curated_document
from tools.audit_standard_game_reference_tables import (
    CURATED,
    MANIFEST,
    PDF,
    PINNED,
    audit_reference_tables,
    audit_source_files,
    main,
    verify_pinned_pdf,
)


def _inputs() -> tuple[dict, dict]:
    return (
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        load_curated_document(CURATED),
    )


def test_english_n53_standard_game_source_rows_are_pinned() -> None:
    report = audit_source_files()
    assert report["scope"] == "audit-only-army-session-threshold-and-advisory-setup"
    assert (report["retreatThresholdSourcePage"], report["tableSizeSourcePage"]) == (
        146, 147,
    )
    assert report["rowCount"] == 6
    assert report["tableSizeScope"] == "advisory-not-mandatory"
    assert report["tableSizeDomain"] == "generic-table-setup-not-scenario-override"
    assert report["thresholdDomain"] == "army-session-not-unit-or-trooper-attribute"
    assert report["thresholdComparison"] == (
        "current-victory-points-less-than-or-equal-to-threshold"
    )
    assert report["linkedMaintainedReferences"] == [
        "state:retreat", "term:victory-points",
    ]
    assert [
        (
            row["armyPoints"], row["retreatThresholdVictoryPoints"],
            tuple(row["recommendedTableInches"]),
        )
        for row in report["rows"]
    ] == list(PINNED)
    assert len(report["manifestSha256"]) == len(report["curatedSha256"]) == 64
    assert report["verifiedPdfSha256"] is None


def test_standard_game_source_rows_fail_closed_on_drifts() -> None:
    manifest, curated = _inputs()
    assert audit_reference_tables(manifest, curated)["rowCount"] == 6

    for index, field, replacement in (
        (0, "retreatThresholdVictoryPoints", 37),
        (2, "retreatThresholdVictoryPoints", 62),
        (4, "retreatThresholdVictoryPoints", 87),
        (4, "recommendedTableInches", [32, 48]),
        (1, "armyPoints", 201),
    ):
        changed = copy.deepcopy(manifest)
        changed["rows"][index][field] = replacement
        with pytest.raises(ValueError, match="row drift"):
            audit_reference_tables(changed, curated)

    changed = copy.deepcopy(manifest)
    changed["tableSizeRule"]["scope"] = "mandatory"
    with pytest.raises(ValueError, match="scope drift"):
        audit_reference_tables(changed, curated)

    changed = copy.deepcopy(curated)
    changed["records"] = [
        row for row in changed["records"] if row["id"] != "state:retreat"
    ]
    with pytest.raises(ValueError, match="state:retreat"):
        audit_reference_tables(manifest, changed)

    changed = copy.deepcopy(curated)
    changed["records"].append({
        "id": "rule:retreat-threshold", "kind": "rule",
        "name": "Retreat Threshold",
    })
    with pytest.raises(ValueError, match="needs explicit source review"):
        audit_reference_tables(manifest, changed)


def test_optional_pdf_check_validates_printed_source() -> None:
    pytest.importorskip("pymupdf")
    if not PDF.is_file():
        pytest.skip("Local N5.3 English PDF not present")
    result = audit_source_files(pdf_path=PDF)
    assert len(result["verifiedPdfSha256"]) == 64
    manifest, _ = _inputs()
    assert result["verifiedPdfSha256"] == verify_pinned_pdf(PDF, manifest)

    altered = copy.deepcopy(manifest)
    altered["rows"][0]["retreatThresholdVictoryPoints"] = 37
    with pytest.raises(ValueError, match="source table row mismatch"):
        verify_pinned_pdf(PDF, altered)


def test_standard_game_audit_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_standard_game_reference_tables"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Retreat! and table-setup source rows: 6" in output
    assert "150 Army Points: Retreat! <= 38 VP; advisory table 24 x 32 in" in output
    assert "250 Army Points: Retreat! <= 63 VP; advisory table 32 x 48 in" in output
    assert "350 Army Points: Retreat! <= 88 VP; advisory table 48 x 48 in" in output
    assert "not a Unit/Profile attribute" in output
    assert "not scenario overrides" in output
