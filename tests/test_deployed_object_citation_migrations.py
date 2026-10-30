"""Preflight all three audit-only N5.3 citation migrations together."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from tools.audit_deployed_object_citation_migrations import (
    CURATED,
    MANIFEST_PATHS,
    audit_citations,
    build_citation_migration_plan,
    main,
)


def _inputs() -> tuple[dict, dict[str, dict]]:
    return (
        json.loads(CURATED.read_text(encoding="utf-8")),
        {
            key: json.loads(path.read_text(encoding="utf-8"))
            for key, path in MANIFEST_PATHS.items()
        },
    )


def test_pinned_citation_migration_preflight_preserves_provenance() -> None:
    report = audit_citations()
    assert report["scope"] == "citation-preflight-only-no-source-or-runtime-modification"
    assert report["source"] == "n5-core-v5.3-pdf"
    assert report["pendingCount"] == 14
    assert report["countsByManifest"] == {
        "non-catalog": 6, "expanded": 5, "source-domain": 3,
    }
    assert len(report["curatedSourceSha256"]) == 64
    assert set(report["reviewManifestSha256"]) == set(MANIFEST_PATHS)
    assert all(len(digest) == 64 for digest in report["reviewManifestSha256"].values())
    assert len({row["recordId"] for row in report["pending"]}) == 14
    assert all(
        row["proposedCitation"]["sourceId"] == "n5-core-v5.3-pdf"
        and isinstance(row["proposedCitation"]["page"], int)
        and row["pdfExcerpt"]
        for row in report["pending"]
    )
    assert {
        row["recordId"]: row["proposedCitation"]["page"]
        for row in report["pending"]
    } == {
        "skill:frenzy": 93,
        "state:possessed": 169,
        "rule:command-token-strategic-use": 128,
        "skill:counterintelligence": 90,
        "skill:inspiring-leadership": 99,
        "skill:transmutation": 117,
        "state:decoy": 159,
        "trait:concealed": 175,
        "skill:mnemonica": 103,
        "skill:tactical-awareness": 115,
        "skill:explode": 92,
        "equipment:escape-system": 117,
        "equipment:holomask": 124,
        "equipment:holoprojector": 124,
    }
    assert not any(
        key in row for row in report["pending"]
        for key in ("objectProfile", "delivery", "sourceProfile", "unitCarriers")
    )


def test_preflight_rejects_lost_review_and_stale_or_published_citation() -> None:
    curated, manifests = _inputs()
    assert build_citation_migration_plan(curated, manifests)["pendingCount"] == 14
    missing = copy.deepcopy(manifests)
    missing["expanded"]["reviews"] = [
        row for row in missing["expanded"]["reviews"]
        if row["recordId"] != "state:decoy"
    ]
    with pytest.raises(ValueError, match="PDF-only review inventory changed"):
        build_citation_migration_plan(curated, missing)

    wrong_page = copy.deepcopy(manifests)
    entry = next(
        row for row in wrong_page["non-catalog"]["reviews"]
        if row["recordId"] == "skill:frenzy"
    )
    entry["sourcePages"] = [888]
    with pytest.raises(ValueError, match="PDF-only provenance"):
        build_citation_migration_plan(curated, wrong_page)

    cited = copy.deepcopy(curated)
    target = next(
        row for row in cited["records"] if row["id"] == "equipment:holomask"
    )
    target["citations"].append({"sourceId": "n5-core-v5.3-pdf", "page": 124})
    with pytest.raises(ValueError, match="PDF-only provenance"):
        build_citation_migration_plan(cited, manifests)


def test_optional_pdf_check_uses_pinned_source_text() -> None:
    pytest.importorskip("pymupdf")
    pdf = CURATED.parents[2] / "pdf/rules/n5-rules-v5-3-en.pdf"
    if not pdf.is_file():
        pytest.skip("Locally pinned N5.3 English PDF unavailable")
    report = audit_citations(pdf_path=pdf)
    assert len(report["verifiedPdfSha256"]) == 64


def test_preflight_does_not_write_sources(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    original = CURATED.read_bytes()
    monkeypatch.setattr(sys, "argv", ["audit_deployed_object_citation_migrations"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Audit-only citations pending migration: 14" in output
    assert "No curated sources, generated databases" in output
    assert CURATED.read_bytes() == original

    # A copy of the curated document is accepted as input; it is never edited.
    copied = tmp_path / "curated.json"
    copied.write_bytes(original)
    assert audit_citations(copied)["pendingCount"] == 14
    assert copied.read_bytes() == original
