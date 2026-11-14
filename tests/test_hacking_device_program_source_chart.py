"""Current Hacking Device access and independent N5.3 Program statistics checks."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sqlite3
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.database.repository import Database
from tools.research.audit_hacking_program_statistics_chart import (
    ARMY_DB,
    ROOT,
    audit_files,
    audit_statistics,
    program_key,
    verify_pdf,
)
from tools.research.audit_hacking_program_statistics_chart import MANIFEST as STATISTICS
from tools.research.source_paths import SourcePathError, pinned_pdf_path

MANIFEST = ROOT / "config/validation/hacking-device-program-source-chart.json"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
PROGRAMS = ROOT / "data/curated/rules/n5-hacking-programs-v5.3.json"
PROGRAM_LINKS = re.compile(r"\[\[hacking-program:([a-z0-9-]+)(?:\|[^\]]*)?\]\]")
PDF_LABEL = "data/pdf/rules/n5-rules-v5.3-en.pdf"
PDF_PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"


def _selected_statistics_pdf(
    manifest: dict, *, layout: str = "local", root: Path = ROOT,
) -> Path | None:
    """Only exact N5.3 source evidence; never trust an amended manifest pin."""
    assert manifest["sourcePdfSha256"] == PDF_PIN
    return pinned_pdf_path(root, PDF_LABEL, PDF_PIN, layout=layout, missing_ok=True)


EXPECTED_DEVICES = (
    ("equipment:hacking-device", "Hacking Device",
     ("carbonite", "spotlight", "total-control", "oblivion")),
    ("equipment:hacking-device-plus", "Hacking Device Plus",
     ("carbonite", "spotlight", "total-control", "oblivion", "white-noise", "cybermask")),
    ("equipment:killer-hacking-device", "Killer Hacking Device",
     ("trinity", "cybermask")),
    ("equipment:evo-hacking-device", "EVO Hacking Device",
     ("assisted-fire", "enhanced-reaction", "fairy-dust", "controlled-jump")),
)


def _inputs() -> tuple[dict, dict, dict]:
    return (
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        load_curated_document(CURATED),
        load_curated_document(PROGRAMS),
    )


def _assert_current_device_source_parity(
    manifest: dict, curated: dict, programs: dict,
) -> None:
    """Pin reviewed access sets against their actual current Rules definitions."""
    assert set(manifest) == {
        "formatVersion", "sourceId", "sourcePage", "reviewStatus",
        "classification", "deviceRows",
    }
    assert type(manifest["formatVersion"]) is int and manifest["formatVersion"] == 1
    assert manifest["sourceId"] == "n5-core-v5.3-pdf"
    assert manifest["sourcePage"] == 58
    assert manifest["reviewStatus"] == "source-reviewed-audit-only"
    assert manifest["classification"] == {
        "domain": "hacking-device-program-access",
        "scope": "equipment-granted-program-sets-not-individual-program-statistics",
        "relationship": "device-to-program-entitlement-not-army-carrier-or-target",
        "order": "printed-chart-column-order",
        "authority": "source-chart-versus-maintained-device-definitions",
    }
    expected_rows = [
        {
            "deviceId": device_id, "name": name,
            "programIds": [f"hacking-program:{slug}" for slug in slugs],
        }
        for device_id, name, slugs in EXPECTED_DEVICES
    ]
    assert manifest["deviceRows"] == expected_rows
    assert [len(row["programIds"]) for row in expected_rows] == [4, 6, 2, 4]
    assert len({program_id for row in expected_rows for program_id in row["programIds"]}) == 11

    records = {record["id"]: record for record in curated["records"]}
    program_records = {record["id"]: record for record in programs["records"]}
    assert len(records) == len(curated["records"])
    assert len(program_records) == len(programs["records"])
    for device_id, name, slugs in EXPECTED_DEVICES:
        device = records[device_id]
        assert device["kind"] == "equipment"
        assert device["name"] == name
        assert device["composition"]["role"] == "definition"
        citations = [
            citation for citation in device["citations"]
            if citation["sourceId"] == "n5-core-v5.3-pdf"
        ]
        assert citations == [{"sourceId": "n5-core-v5.3-pdf", "page": 58}]
        effects = device["facts"]["effects"]
        assert len(effects) == 1 and isinstance(effects[0], str)
        actual_slugs = PROGRAM_LINKS.findall(effects[0])
        assert len(actual_slugs) == len(set(actual_slugs)) == len(slugs)
        assert set(actual_slugs) == set(slugs)
        for slug in slugs:
            program = program_records[f"hacking-program:{slug}"]
            assert program["kind"] == "hacking-program"
            assert program["composition"]["role"] == "definition"


def test_current_device_access_matches_reviewed_source() -> None:
    manifest, curated, programs = _inputs()
    _assert_current_device_source_parity(manifest, curated, programs)


def test_current_device_access_fails_closed_on_drift() -> None:
    manifest, curated, programs = _inputs()

    changed = copy.deepcopy(manifest)
    changed["deviceRows"][1]["programIds"].remove("hacking-program:cybermask")
    with pytest.raises(AssertionError):
        _assert_current_device_source_parity(changed, curated, programs)

    changed = copy.deepcopy(manifest)
    changed["classification"]["scope"] = "program-statistics"
    with pytest.raises(AssertionError):
        _assert_current_device_source_parity(changed, curated, programs)

    changed = copy.deepcopy(curated)
    device = next(
        item for item in changed["records"]
        if item["id"] == "equipment:evo-hacking-device"
    )
    device["facts"]["effects"][0] = device["facts"]["effects"][0].replace(
        "[[hacking-program:fairy-dust]]", "[[hacking-program:spotlight]]",
    )
    with pytest.raises(AssertionError):
        _assert_current_device_source_parity(manifest, changed, programs)

    changed = copy.deepcopy(curated)
    device = next(
        item for item in changed["records"]
        if item["id"] == "equipment:hacking-device-plus"
    )
    device["citations"] = [
        citation for citation in device["citations"]
        if citation["sourceId"] != "n5-core-v5.3-pdf"
    ]
    with pytest.raises(AssertionError):
        _assert_current_device_source_parity(manifest, changed, programs)

    changed = copy.deepcopy(programs)
    changed["records"] = [
        item for item in changed["records"]
        if item["id"] != "hacking-program:trinity"
    ]
    with pytest.raises((AssertionError, KeyError)):
        _assert_current_device_source_parity(manifest, curated, changed)


def test_published_p58_device_citations_match_current_rules_database() -> None:
    manifest, curated, programs = _inputs()
    _assert_current_device_source_parity(manifest, curated, programs)
    device_ids = [item[0] for item in EXPECTED_DEVICES]
    expected = sorted((record_id, "n5-core-v5.3-pdf", 58) for record_id in device_ids)
    with sqlite3.connect(ROOT / "data/generated/rules_n5.db") as connection:
        actual = connection.execute(
            "SELECT record_id, source_id, page FROM record_citations "
            "WHERE record_id IN (?, ?, ?, ?) AND source_id = ? "
            "ORDER BY record_id, page",
            (*device_ids, "n5-core-v5.3-pdf"),
        ).fetchall()
    assert actual == expected


# The independent statistics chart shares N5.3 p. 58 with the device matrix,
# but is never interpreted as a second Equipment entitlement source.
def test_n53_program_statistics_match_published_army_metadata() -> None:
    manifest = json.loads(STATISTICS.read_text(encoding="utf-8"))
    rows = Database(STATISTICS.parents[2] / "data/generated/army.db").list_hacking_programs()
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


def test_n53_statistics_pdf_layout_is_pinned_and_never_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"%PDF synthetic source for path-selection testing only"
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setitem(globals(), "PDF_PIN", digest)
    manifest = {"sourcePdfSha256": digest}
    legacy = tmp_path / PDF_LABEL
    local = tmp_path / "local/data/pdf" / Path(PDF_LABEL).relative_to("data/pdf")
    for path in (legacy, local):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    assert _selected_statistics_pdf(manifest, root=tmp_path) == local
    assert _selected_statistics_pdf(manifest, layout="legacy", root=tmp_path) == legacy
    local.write_bytes(b"unexpected source revision")
    with pytest.raises(SourcePathError, match="hash mismatch"):
        _selected_statistics_pdf(manifest, layout="local", root=tmp_path)
    local.unlink()
    assert _selected_statistics_pdf(manifest, layout="local", root=tmp_path) is None
    assert _selected_statistics_pdf(manifest, root=tmp_path) is None
    assert _selected_statistics_pdf(manifest, layout="legacy", root=tmp_path) == legacy
    with pytest.raises(AssertionError):
        _selected_statistics_pdf({"sourcePdfSha256": "0" * 64}, root=tmp_path)
    with pytest.raises(SourcePathError, match="Unknown research source layout"):
        _selected_statistics_pdf(manifest, layout="automatic", root=tmp_path)


def test_n53_program_statistics_pinned_archive_and_pdf_evidence(
    reference_pdf_layout: str,
) -> None:
    manifest = json.loads(STATISTICS.read_text(encoding="utf-8"))
    pdf = _selected_statistics_pdf(manifest, layout=reference_pdf_layout)
    archive = ROOT / "local/data/raw/army" / Path(manifest["armyArchive"]).name
    if pdf is None or not archive.is_file():
        pytest.skip("Optional pinned N5.3 PDF / Army archive unavailable")
    pytest.importorskip("pymupdf")
    report = audit_files(archive_path=archive, pdf_path=pdf)
    assert report["archiveReconciled"] is True
    assert report["statisticsMismatches"] == []
    assert report["verifiedPdfSha256"] == manifest["sourcePdfSha256"]
    assert report["armyArchiveSha256"] == manifest["armyArchiveSha256"]
    altered = copy.deepcopy(manifest)
    altered["rows"][1]["ps"] = "8"
    with pytest.raises(ValueError, match="printed ps cell mismatch"):
        verify_pdf(pdf, altered)
    altered = copy.deepcopy(manifest)
    altered["rows"][1]["specialEvidence"][0]["pdf"] = "MISSING CLAUSE"
    with pytest.raises(ValueError, match="printed Special clause drift"):
        verify_pdf(pdf, altered)


def test_n53_unlisted_program_troop_types_have_distinct_source_scope(
    reference_pdf_layout: str,
) -> None:
    """A blank Target cell is not a uniform 'no valid target' rule."""
    manifest = json.loads(STATISTICS.read_text(encoding="utf-8"))
    source = _selected_statistics_pdf(manifest, layout=reference_pdf_layout)
    if source is None:
        pytest.skip("Optional pinned N5.3 PDF unavailable")
    pymupdf = pytest.importorskip("pymupdf")
    with pymupdf.open(source) as pdf:
        pages = {
            number: " ".join(pdf[number - 1].get_text("text").upper().split())
            for number in (57, 59, 60, 61)
        }
    assert "TARGET. THE TROOP TYPE THAT CAN BE TARGETED" in pages[57]
    assert "PROGRAM AFFECTS ONLY THE HACKER HIMSELF" in pages[59]
    assert "THE TARGET OF THIS HACKING PROGRAM DOES NOT NEED TO HAVE THE HACKABLE" in (
        pages[60]
    )
    assert "GENERATES A WHITE NOISE ZONE" in pages[61]
    unlisted = {
        program_key(row["name"]) for row in manifest["rows"] if not row["targets"]
    }
    assert unlisted == {
        "controlled-jump", "cybermask", "spotlight", "white-noise", "zero-pain"
    }
