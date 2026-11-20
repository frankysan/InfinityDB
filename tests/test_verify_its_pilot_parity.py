"""Standalone current ITS Battleground parity against the published runtime."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from tools.data.verify_its_pilot_parity import ROOT, SOURCE, verify_pilot


def test_its_pilot_matches_independent_api_and_svg_variants() -> None:
    result = verify_pilot()
    assert result["result"] == "PASS"
    assert result["season"] == "its-18@2026.09.11"
    assert result["apiJsonComparisons"] == 6
    assert result["svgByteComparisons"] == 24
    assert result["sourceCitations"] == 3
    assert result["publicationSha256"] == (
        "96f5ffea6e1b00fd22716f2c37d5d11f7aa42904f604e9fc3b213b9928f6ea08"
    )


def test_its_pilot_detects_authored_mission_drift(tmp_path: Path) -> None:
    document = load_curated_document(SOURCE)
    next(row for row in document["records"] if row["id"] == "scenario:battleground")[
        "summary"
    ] = "An altered Battleground description"
    changed = tmp_path / "changed-its.json"
    changed.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    serving_artifact = ROOT / "data/generated/its_18.db"
    before_serving = serving_artifact.read_bytes()
    with pytest.raises(
        ValueError, match="ITS HTTP scenario list differs from independent publication",
    ):
        verify_pilot(source=changed)
    assert serving_artifact.read_bytes() == before_serving
