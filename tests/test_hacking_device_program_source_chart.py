"""N5.3 hacking device-to-Program source chart and maintained access sets."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.database.repository import Database
from tools.audit_hacking_device_program_source_chart import (
    CURATED,
    MANIFEST,
    PDF,
    PINNED,
    PROGRAMS,
    audit_device_program_chart,
    audit_source_files,
    main,
    verify_pinned_pdf,
)
from tools.audit_hacking_program_statistics_chart import (
    ARMY_DB,
    ROOT,
    audit_files,
    audit_statistics,
    program_key,
    verify_pdf,
)
from tools.audit_hacking_program_statistics_chart import MANIFEST as STATISTICS
from tools.audit_hacking_program_statistics_chart import PDF as STATISTICS_PDF


def _inputs() -> tuple[dict, dict, dict]:
    return (
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        load_curated_document(CURATED),
        load_curated_document(PROGRAMS),
    )


def test_n53_device_chart_exactly_reconciles_maintained_program_sets() -> None:
    report = audit_source_files()
    assert report["scope"] == (
        "equipment-granted-program-sets-not-individual-program-statistics"
    )
    assert report["sourcePage"] == 58
    assert report["deviceCount"] == 4
    assert report["distinctProgramCount"] == 11
    assert report["programStatisticsIncluded"] is False
    assert report["missingMaintainedN53ChartCitations"] in (
        [],
        [row[0] for row in PINNED],
    )
    assert [
        (row["deviceId"], row["name"],
         tuple(program_id.removeprefix("hacking-program:") for program_id in row["programIds"]))
        for row in report["deviceRows"]
    ] == list(PINNED)
    assert [len(row["programIds"]) for row in report["deviceRows"]] == [4, 6, 2, 4]
    assert report["verifiedPdfSha256"] is None
    assert all(
        len(report[name]) == 64
        for name in ("manifestSha256", "curatedSha256", "programsSha256")
    )


def test_device_chart_rejects_unreviewed_changes_or_program_gaps() -> None:
    manifest, curated, programs = _inputs()
    assert audit_device_program_chart(manifest, curated, programs)["deviceCount"] == 4

    mutation = copy.deepcopy(manifest)
    mutation["deviceRows"][1]["programIds"].remove("hacking-program:cybermask")
    with pytest.raises(ValueError, match="row drift"):
        audit_device_program_chart(mutation, curated, programs)

    mutation = copy.deepcopy(manifest)
    mutation["classification"]["scope"] = "all-program-statistics"
    with pytest.raises(ValueError, match="source/scope drift"):
        audit_device_program_chart(mutation, curated, programs)

    altered = copy.deepcopy(curated)
    record = next(
        row for row in altered["records"]
        if row["id"] == "equipment:evo-hacking-device"
    )
    record["facts"]["effects"][0] = record["facts"]["effects"][0].replace(
        "[[hacking-program:fairy-dust]]", "[[hacking-program:spotlight]]",
    )
    with pytest.raises(ValueError, match="Program access drift"):
        audit_device_program_chart(manifest, altered, programs)

    altered = copy.deepcopy(programs)
    altered["records"] = [
        row for row in altered["records"] if row["id"] != "hacking-program:trinity"
    ]
    with pytest.raises(ValueError, match="Missing canonical Program"):
        audit_device_program_chart(manifest, curated, altered)


def test_device_chart_rejects_partial_or_incorrect_citation_migration() -> None:
    manifest, curated, programs = _inputs()
    target = next(
        record for record in curated["records"]
        if record["id"] == "equipment:hacking-device-plus"
    )
    source_citation = {"sourceId": "n5-core-v5.3-pdf", "page": 58}
    if not any(cite["sourceId"] == source_citation["sourceId"] for cite in target["citations"]):
        target["citations"].append(source_citation)
        with pytest.raises(ValueError, match="Partial Hacking Device"):
            audit_device_program_chart(manifest, curated, programs)
    target["citations"] = [
        cite for cite in target["citations"] if cite["sourceId"] != source_citation["sourceId"]
    ] + [{**source_citation, "page": 57}]
    with pytest.raises(ValueError, match="Unreviewed N5.3"):
        audit_device_program_chart(manifest, curated, programs)


def test_device_chart_optional_pinned_pdf_evidence() -> None:
    pytest.importorskip("pymupdf")
    if not PDF.is_file():
        pytest.skip("Local pinned English N5.3 PDF unavailable")
    result = audit_source_files(pdf_path=PDF)
    assert len(result["verifiedPdfSha256"]) == 64
    manifest, _, _ = _inputs()
    assert verify_pinned_pdf(PDF, manifest) == result["verifiedPdfSha256"]


def test_device_chart_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_hacking_device_program_source_chart"])
    assert main() == 0
    out = capsys.readouterr().out
    assert "4 devices; 11 distinct Programs" in out
    assert "Hacking Device Plus: 6 Programs" in out
    assert "Killer Hacking Device: 2 Programs" in out
    assert "no Program statistics or Unit carriers" in out


def test_adjacent_statistics_cli_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys, "argv",
        ["audit_hacking_device_program_source_chart", "--statistics-chart", "--json"],
    )
    assert main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rowCount"] == 12
    assert report["statisticsMismatches"] == []


# The independent statistics chart shares N5.3 p. 58 with the device matrix,
# but is never interpreted as a second Equipment entitlement source.
def test_n53_program_statistics_match_published_army_metadata() -> None:
    manifest = json.loads(STATISTICS.read_text(encoding="utf-8"))
    rows = Database(STATISTICS.parents[2] / "data/generated/infinity.db").list_hacking_programs()
    report = audit_statistics(manifest, rows)
    assert report["rowCount"] == 12
    assert report["statisticsMismatches"] == []
    assert report["orderDiffers"] is True
    assert report["sourceOrder"][7:10] == [
        "total-control", "trinity", "spotlight",
    ]
    assert report["armyOrder"][7:10] == [
        "spotlight", "total-control", "trinity",
    ]
    assert report["deviceEntitlementsIncluded"] is False
    assert len({program_key(row["name"]) for row in rows}) == 12


def test_n53_statistics_fail_closed_on_changed_columns_and_source_scope() -> None:
    manifest = json.loads(STATISTICS.read_text(encoding="utf-8"))
    rows = Database(ARMY_DB).list_hacking_programs()
    for field, replacement in (
        ("attackMod", "+3"),
        ("opponentMod", "-3"),
        ("ps", "8"),
        ("burst", "3"),
        ("targets", ["TAG"]),
        ("skillTypes", ["aro"]),
        ("specialEvidence", [{"pdf": "MARKSMANSHIP", "army": "UNSUPPORTED"}]),
    ):
        altered = copy.deepcopy(manifest)
        altered["rows"][0][field] = replacement
        report = audit_statistics(altered, rows)
        assert report["statisticsMismatches"], field

    altered = copy.deepcopy(manifest)
    altered["rows"][7], altered["rows"][8] = altered["rows"][8], altered["rows"][7]
    with pytest.raises(ValueError, match="row count/order"):
        audit_statistics(altered, rows)
    altered = copy.deepcopy(manifest)
    altered["classification"]["scope"] = "hacking-device-entitlements"
    with pytest.raises(ValueError, match="provenance"):
        audit_statistics(altered, rows)
    altered = copy.deepcopy(rows)
    altered[0]["name"] = "Fictional Program"
    with pytest.raises(ValueError, match="identities"):
        audit_statistics(manifest, altered)


def test_n53_program_statistics_pinned_archive_and_pdf_evidence() -> None:
    manifest = json.loads(STATISTICS.read_text(encoding="utf-8"))
    archive = ROOT / manifest["armyArchive"]
    if not archive.is_file() or not STATISTICS_PDF.is_file():
        pytest.skip("Optional pinned N5.3 PDF / Army archive unavailable")
    pytest.importorskip("pymupdf")
    report = audit_files(archive_path=archive, pdf_path=STATISTICS_PDF)
    assert report["archiveReconciled"] is True
    assert report["statisticsMismatches"] == []
    assert report["verifiedPdfSha256"] == manifest["sourcePdfSha256"]
    assert report["armyArchiveSha256"] == manifest["armyArchiveSha256"]
    altered = copy.deepcopy(manifest)
    altered["rows"][1]["ps"] = "8"
    with pytest.raises(ValueError, match="printed ps cell mismatch"):
        verify_pdf(STATISTICS_PDF, altered)
    altered = copy.deepcopy(manifest)
    altered["rows"][1]["specialEvidence"][0]["pdf"] = "MISSING CLAUSE"
    with pytest.raises(ValueError, match="printed Special clause drift"):
        verify_pdf(STATISTICS_PDF, altered)
