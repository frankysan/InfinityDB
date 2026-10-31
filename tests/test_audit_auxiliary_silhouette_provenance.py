"""Focused tests for cross-publication auxiliary Silhouette provenance."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.audit_auxiliary_silhouette_provenance import (
    audit,
    html_rows,
    markdown_report,
    pdf_object_s,
    wiki_chart_s,
    wiki_dazer_s,
)
from tools.audit_weapon_chart_profiles import WeaponChartAuditError


class FakePage:
    def __init__(self, words: list[tuple[float, float, str]]):
        self.words = [(x, y, x + 8, y + 7, label, 0, 0, 0) for x, y, label in words]

    def get_text(self, kind: str) -> list:
        assert kind == "words"
        return self.words


def test_pdf_silhouette_matches_only_the_named_object_and_language() -> None:
    page = FakePage(
        [
            (30, 202, "AP"),
            (48, 202, "MINES"),
            (124, 202, "ARM=0"),
            (214, 202, "S=0"),
            (37, 238, "DAZER"),
            (125, 238, "ARM=0"),
            (215, 238, "S=1"),
        ]
    )
    assert pdf_object_s(page, "AP MINES", spanish=False) == 0
    assert pdf_object_s(page, "DAZER", spanish=False) == 1
    with pytest.raises(WeaponChartAuditError, match="Expected one"):
        pdf_object_s(page, "E/M MINES", spanish=False)

    spanish = FakePage(
        [
            (35, 183, "DAZER"),
            (142, 183, "BLI=0"),
            (222, 183, "S=0"),
        ]
    )
    assert pdf_object_s(spanish, "DAZER", spanish=True) == 0


def test_ambiguous_pdf_attribute_rejected() -> None:
    page = FakePage(
        [
            (37, 238, "DAZER"),
            (125, 238, "ARM=0"),
            (215, 238, "S=1"),
            (230, 238, "S=0"),
        ]
    )
    with pytest.raises(WeaponChartAuditError, match="Ambiguous"):
        pdf_object_s(page, "DAZER", spanish=False)


def test_wiki_profile_parsers_preserve_chart_vs_dedicated_context() -> None:
    chart = """
    <table><tr><th>Deployable</th><th>ARM</th><th>BTS</th><th>STR</th><th>S</th></tr>
    <tr><td>AP MINE</td><td>0</td><td>0</td><td>1</td><td>0</td></tr>
    <tr><td>DAZER</td><td>0</td><td>0</td><td>1</td><td>1</td></tr></table>
    """
    assert len(html_rows(chart)) == 3
    assert wiki_chart_s(chart, "AP MINE") == 0
    assert wiki_chart_s(chart, "DAZER") == 1
    with pytest.raises(WeaponChartAuditError, match="Expected one"):
        wiki_chart_s(chart, "SHOCK MINE")

    dedicated_en = """
    <table><tr><th>ARM</th><th>BTS</th><th>STR</th><th>S</th></tr>
    <tr><td>0</td><td>0</td><td>1</td><td>0</td></tr></table>
    """
    dedicated_es = """
    <table><tr><th>Posicionable</th><th>BLI</th><th>PB</th>
    <th>EST</th><th>S</th></tr>
    <tr><td>DAZER</td><td>0</td><td>0</td><td>1</td><td>1</td></tr></table>
    """
    assert wiki_dazer_s(dedicated_en) == 0
    assert wiki_dazer_s(dedicated_es) == 1


def test_pinned_object_matrix_if_source_archives_available() -> None:
    pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    inputs = [
        root / "data/pdf/rules/n5-rules-v5-3-en.pdf",
        root / "data/pdf/rules/esp-n5-update-5-3.pdf",
        root / "data/wiki/WIKI-en 20260926-200832.zip",
        root / "data/wiki/WIKI-es 20261009-211304.zip",
        root / "data/generated/infinity.db",
    ]
    if not all(path.exists() for path in inputs):
        pytest.skip("Pinned source archives not present in this checkout")
    report = audit(*inputs)
    rows = report["profiles"]
    assert len(rows) == 7
    assert len({row["armyName"] for row in rows}) == 7
    for row in rows[:6]:
        assert (
            row["pdfEn"]["S"],
            row["pdfEs"]["S"],
            row["wikiChartEn"],
            row["wikiChartEs"],
            row["army"],
        ) == (0, 0, 0, 0, 1)
        assert row["status"] == "pdf-and-wiki-chart-agree; army-differs"
    dazer = rows[6]
    assert dazer["armyName"] == "Dazer"
    assert (
        dazer["pdfEn"]["S"],
        dazer["pdfEs"]["S"],
        dazer["wikiChartEn"],
        dazer["wikiChartEs"],
        dazer["army"],
    ) == (1, 0, 1, 1, 0)
    assert dazer["wikiDedicated"] == {"en": 0, "es": 1}
    assert dazer["status"] == "cross-publication-conflict"
    assert "S0/S1" in markdown_report(report)
    assert all(report["inputs"][key]["sha256"] for key in ("pdfEn", "pdfEs", "armyDb"))
