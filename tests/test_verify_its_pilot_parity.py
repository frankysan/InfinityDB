"""P3.3 acceptance of standalone ITS Battleground against the served baseline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from tools.verify_its_pilot_parity import ROOT, SOURCE, verify_pilot


def test_its_pilot_matches_independent_api_and_svg_variants() -> None:
    result = verify_pilot()
    assert result["result"] == "PASS"
    assert result["season"] == "its-18@2026.09.01"
    assert result["apiJsonComparisons"] == 6
    assert result["svgByteComparisons"] == 24
    assert result["sourceCitations"] == 3
    assert result["publicationSha256"] == (
        "2dd4ab5c9f7c83bcdc4f94e156f29c4b6c2d9e34770a03da85e8886f4c0d5b31"
    )


def test_its_pilot_detects_authored_mission_drift(tmp_path: Path) -> None:
    document = load_curated_document(SOURCE)
    document["records"][0]["summary"] = "An altered Battleground description"
    changed = tmp_path / "changed-its.json"
    changed.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    serving_artifact = ROOT / "data/generated/its_18.db"
    before_serving = serving_artifact.read_bytes()
    with pytest.raises(ValueError, match="differs from pinned pre-cutover publication"):
        verify_pilot(source=changed)
    assert serving_artifact.read_bytes() == before_serving
