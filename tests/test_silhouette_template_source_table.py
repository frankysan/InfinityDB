"""N5.3 Silhouette table versus player-facing browser diagrams, fail closed."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from infinity_db.curated import load_curated_document
from tools.audit_silhouette_template_source_table import (
    CURATED,
    MANIFEST,
    PDF,
    PINNED,
    RENDERER,
    audit_silhouette_table,
    audit_source_files,
    main,
    verify_pinned_pdf,
)


def _inputs() -> tuple[dict, dict, str]:
    return (
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        load_curated_document(CURATED),
        RENDERER.read_text(encoding="utf-8"),
    )


def test_silhouette_table_matches_browser_diagrams_and_prone_exception() -> None:
    report = audit_source_files()
    assert report["scope"] == (
        "trooper-geometry-reference-not-deployed-object-profile"
    )
    assert report["sourcePage"] == 18
    assert report["rowCount"] == 10
    assert report["fixedTemplateCount"] == 9
    assert report["browserDiagramCount"] == 8
    assert [
        (row["id"], row["template"], row["baseMm"], row["heightMm"])
        for row in report["sourceRows"]
    ] == list(PINNED)
    assert report["specialTemplate"] == {
        "template": "SX",
        "heightMm": 3,
        "baseWidthRule": "retain-trooper-original-silhouette-base-width",
        "context": "prone-state",
        "fixedBaseMm": None,
    }
    assert all(
        len(report[key]) == 64
        for key in ("manifestSha256", "curatedSha256", "rendererSha256")
    )
    assert report["verifiedPdfSha256"] is None


def test_silhouette_audit_rejects_numeric_geometry_and_policy_drift() -> None:
    manifest, curated, renderer = _inputs()
    assert audit_silhouette_table(manifest, curated, renderer)["rowCount"] == 10

    changed = copy.deepcopy(manifest)
    changed["rows"][0]["baseMm"] = 25
    with pytest.raises(ValueError, match="source drift"):
        audit_silhouette_table(changed, curated, renderer)

    changed = copy.deepcopy(manifest)
    changed["rows"][4]["heightMm"] = 40
    with pytest.raises(ValueError, match="source drift"):
        audit_silhouette_table(changed, curated, renderer)

    changed = copy.deepcopy(manifest)
    changed["proneSilhouette"]["fixedBaseMm"] = 25
    with pytest.raises(ValueError, match="scope/provenance drift"):
        audit_silhouette_table(changed, curated, renderer)

    altered_renderer = renderer.replace(
        "id: 3, widthMm: 40, heightMm: 32",
        "id: 3, widthMm: 40, heightMm: 40",
    )
    with pytest.raises(ValueError, match="diagram dimensions"):
        audit_silhouette_table(manifest, curated, altered_renderer)
    altered_renderer = renderer.replace("No supplied source SVG for S0/SX", "S0 is SVG")
    with pytest.raises(ValueError, match="representation drift"):
        audit_silhouette_table(manifest, curated, altered_renderer)

    altered_curated = copy.deepcopy(curated)
    altered_curated["records"] = [
        record for record in altered_curated["records"]
        if record["id"] != "attribute:s"
    ]
    with pytest.raises(ValueError, match="attribute/Prone"):
        audit_silhouette_table(manifest, altered_curated, renderer)


def test_silhouette_table_pinned_pdf_evidence() -> None:
    pytest.importorskip("pymupdf")
    if not PDF.is_file():
        pytest.skip("Pinned local English N5.3 PDF unavailable")
    report = audit_source_files(pdf_path=PDF)
    assert len(report["verifiedPdfSha256"]) == 64
    manifest, _, _ = _inputs()
    assert verify_pinned_pdf(PDF, manifest) == report["verifiedPdfSha256"]

    changed = copy.deepcopy(manifest)
    changed["rows"][2]["baseMm"] = 30
    with pytest.raises(ValueError, match="Printed Silhouette table mismatch"):
        verify_pinned_pdf(PDF, changed)


def test_silhouette_source_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_silhouette_template_source_table"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Silhouette source rows: 10" in output
    assert "Browser S1-S8 diagrams: 8" in output
    assert "SX: dynamic base / 3 mm high (Prone)" in output
