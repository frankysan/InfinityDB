"""Source-reviewed ITS 17/18 reuse boundaries; no historical publication is synthesized.

ITS 17 original: official Seekers V0.2 / URL v1.0.2, SHA-256
73a184b80535f23499000bb81112d95168c12f970fa14a30050a95ec51cdfe71.
Cross-check with ITS 18 2026.09.11 English original (current curated source).
The historical PDF is ignored evidence and is not needed to run these regressions.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf
import pytest

from infinity_db.curated import load_curated_document
from tools.research import acquire_its_pdf
from tools.research.render_its_source_pages import SOURCE_SETS

ROOT = Path(__file__).resolve().parents[1]
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"


def _scenario(slug: str) -> dict:
    document = load_curated_document(ITS18)
    return next(row for row in document["records"] if row["id"] == f"scenario:{slug}")


def test_evacuation_geometry_is_a_reviewed_its17_reuse_candidate() -> None:
    """ITS 17 p55 map and p56 placements match ITS 18 pp88-89 maps for all sizes."""
    record = _scenario("evacuation")
    assert record["facts"]["playRequirements"] == {
        "classifiedObjectives": 2, "tacticalObjectives": 0, "hvts": 2,
    }
    objectives = {row["id"]: row for row in record["facts"]["mission"]["objectives"]}
    assert {key: row["maximumPoints"] for key, row in objectives.items()} == {
        "extracted-civilians": 4,
        "extracted-enemy-hvts": 2,
        "classified-objectives": 4,
    }
    assert {key: row["awards"][0]["objectivePoints"] for key, row in objectives.items()} == {
        "extracted-civilians": 1,
        "extracted-enemy-hvts": 1,
        "classified-objectives": 2,
    }

    # (table width, height, deployment depth, Civilian positions, Console positions)
    # Positions in inches; checked against both publishers' maps, not inferred
    # from matching scenario names.
    expected = {
        "150-points": (
            24, 32, 8,
            {(6, 12), (18, 12), (6, 20), (18, 20)},
            {(8, 16), (16, 16)},
        ),
        "200-250-points": (
            32, 48, 12,
            {(6, 16), (26, 16), (6, 32), (26, 32)},
            {(12, 24), (20, 24)},
        ),
        "300-400-points": (
            48, 48, 12,
            {(6, 16), (42, 16), (6, 32), (42, 32)},
            {(16, 24), (32, 24)},
        ),
    }
    configurations = record["facts"]["configurations"]
    assert {row["id"] for row in configurations} == set(expected)
    for config in configurations:
        width, height, depth, civilians, consoles = expected[config["id"]]
        geometry = config["geometry"]
        assert (geometry["table"]["width"], geometry["table"]["height"]) == (
            width, height,
        )
        elements = {row["id"]: row for row in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        for kind, positions in (("civilian", civilians), ("console", consoles)):
            assert {
                (row["x"], row["y"]) for row in elements.values()
                if row["kind"] == "marker" and row["markerType"] == kind
            } == positions


def test_battleground_scoring_requires_distinct_its17_scenario_version() -> None:
    """ITS 17 pp83-85 includes Key Ops and scores sectors 1/3/4, unlike ITS 18 pp129-131."""
    record = _scenario("battleground")
    objectives = {
        row["id"]: row["maximumPoints"]
        for row in record["facts"]["mission"]["objectives"]
    }
    assert objectives == {
        "near-sector-a": 2, "near-sector-b": 2,
        "central-sector": 3,
        "far-sector-a": 5, "far-sector-b": 5,
    }
    assert not any("key-ops" in identifier for identifier in objectives)
    assert (objectives["near-sector-a"], objectives["central-sector"],
            objectives["far-sector-a"]) != (1, 3, 4)
    # Identical sector dimensions alone are insufficient to reuse whole scenario facts.


def test_its17_revision_inventory_uses_canonical_ignored_source_path() -> None:
    assert set(acquire_its_pdf.PINNED_REVISIONS) == {
        "v0.0-en", "v0.0-es", "v0.1-en", "v0.1-es", "v0.2-en", "v0.2-es",
    }
    assert acquire_its_pdf.DESTINATION == (
        ROOT / "local/data/pdf/legacy/its_17"
    )
    assert SOURCE_SETS["its17"] == acquire_its_pdf.DESTINATION
    assert acquire_its_pdf.SOURCES["its-17-en-v1.0.2"][1:] == (
        "its-rules-season-17-v0.2-en.pdf",
        acquire_its_pdf.PINNED_REVISIONS["v0.2-en"][0],
    )


def test_its17_revision_inventory_verifies_exact_bytes_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pymupdf.open() as pdf:
        for _ in range(51):
            pdf.new_page()
        payload = pdf.tobytes()
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(
        acquire_its_pdf, "PINNED_REVISIONS",
        {"v0.1-en": (digest, len(payload), 51)},
    )
    source = tmp_path / "its-rules-season-17-v0.1-en.pdf"
    source.write_bytes(payload)
    assert acquire_its_pdf.verify_revision_set(tmp_path) == [
        (source.name, digest, len(payload), 51),
    ]
    changed = bytearray(payload)
    changed[0] = ord("X")
    source.write_bytes(changed)
    with pytest.raises(ValueError, match="SHA-256"):
        acquire_its_pdf.verify_revision_set(tmp_path)
    source.unlink()
    with pytest.raises(ValueError, match="Missing ITS 17 edition"):
        acquire_its_pdf.verify_revision_set(tmp_path)
