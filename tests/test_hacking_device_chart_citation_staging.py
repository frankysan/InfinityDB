"""Coordinated N5.3 p. 58 device citation staging and promotion safeguards."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from tools.audit_hacking_device_program_source_chart import (
    CURATED,
    MANIFEST,
    PDF,
    PINNED,
    PROGRAMS,
    audit_device_program_chart,
)
from tools.stage_hacking_device_chart_citations import (
    ARMY,
    PUBLICATION,
    SOURCE_CITATION,
    STAGED_PATHS,
    _replace_staged_batch,
    prepare_chart_citations,
    stage_hacking_device_chart_citations,
)


def _inputs() -> tuple[dict, dict, dict]:
    return (
        load_curated_document(CURATED),
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        load_curated_document(PROGRAMS),
    )


def _is_promoted(curated: dict) -> bool:
    return audit_device_program_chart(
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        curated,
        load_curated_document(PROGRAMS),
    )["missingMaintainedN53ChartCitations"] == []


def test_staging_adds_only_four_exact_citations_and_preserves_wiki() -> None:
    curated, chart, programs = _inputs()
    if _is_promoted(curated):
        pytest.skip("Four citations already promoted")
    updated, entries = prepare_chart_citations(curated, chart, programs)
    assert [entry["recordId"] for entry in entries] == [row[0] for row in PINNED]
    assert all(entry["proposedCitation"] == SOURCE_CITATION for entry in entries)
    indexed = {record["id"]: record for record in curated["records"]}
    updated_index = {record["id"]: record for record in updated["records"]}
    for record_id, old in indexed.items():
        after = copy.deepcopy(updated_index[record_id])
        if record_id in {row[0] for row in PINNED}:
            assert after["citations"].pop() == SOURCE_CITATION
        assert after == old
    with pytest.raises(ValueError, match="all four device citations pending"):
        prepare_chart_citations(updated, chart, programs)
    partial = copy.deepcopy(curated)
    next(
        row for row in partial["records"]
        if row["id"] == PINNED[0][0]
    )["citations"].append(dict(SOURCE_CITATION))
    with pytest.raises(ValueError, match="Partial Hacking Device"):
        prepare_chart_citations(partial, chart, programs)


def test_staging_builds_paired_binaries_without_touching_checkout(
    tmp_path: Path,
) -> None:
    curated, _, _ = _inputs()
    if _is_promoted(curated):
        pytest.skip("Four citations already promoted")
    tracked_rules_db = CURATED.parents[2] / "generated/rules.db"
    inputs = (CURATED, tracked_rules_db, PUBLICATION)
    before = [path.read_bytes() for path in inputs]
    stage = tmp_path / "hacking-stage"
    report = stage_hacking_device_chart_citations(
        stage, pdf_path=PDF if PDF.exists() else None,
    )
    assert report["scope"] == "staged-only-hacking-device-p58-citations-not-applied"
    assert report["sourcePage"] == 58
    assert report["migratedDeviceIds"] == [row[0] for row in PINNED]
    assert report["stagedPaths"] == list(STAGED_PATHS)
    assert report["reviewedObjects"] == 17
    assert report["sourceSha256"] == hashlib.sha256(before[0]).hexdigest()
    assert report["armySha256"] == hashlib.sha256(ARMY.read_bytes()).hexdigest()
    if PDF.exists():
        assert len(report["verifiedPdfSha256"]) == 64
    else:
        assert report["verifiedPdfSha256"] is None
    for key, relative in zip(
        ("curated", "rulesDatabase", "deployedObjects"),
        STAGED_PATHS,
        strict=True,
    ):
        staged = (stage / relative).read_bytes()
        assert len(staged) > 0
        assert hashlib.sha256(staged).hexdigest() == report["stagedSha256"][key]
    staged_source = load_curated_document(stage / STAGED_PATHS[0])
    assert _is_promoted(staged_source)
    assert staged_source["records"] != curated["records"]
    with sqlite3.connect(stage / STAGED_PATHS[1]) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM records WHERE id IN (?, ?, ?, ?)",
            tuple(row[0] for row in PINNED),
        ).fetchone()
    assert count == (4,)
    published = json.loads((stage / STAGED_PATHS[2]).read_text(encoding="utf-8"))
    original_published = json.loads(before[2])
    assert published["objects"] == original_published["objects"]
    assert published["sourceSnapshot"]["rulesDatabaseSha256"] == (
        report["stagedSha256"]["rulesDatabase"]
    )
    assert [path.read_bytes() for path in inputs] == before
    assert (stage / "staging-report.json").is_file()
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        stage_hacking_device_chart_citations(stage)


def test_promoted_citations_are_consistent_with_rules_database() -> None:
    curated, _, _ = _inputs()
    if not _is_promoted(curated):
        pytest.skip("Four citations not yet promoted")
    rules_db = CURATED.parents[2] / "generated/rules.db"
    published = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    assert published["sourceSnapshot"]["rulesDatabaseSha256"] == hashlib.sha256(
        rules_db.read_bytes()
    ).hexdigest()
    stage = CURATED.parents[3] / "local/hacking-device-citations-n53"
    report_file = stage / "staging-report.json"
    if report_file.is_file():
        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert report["migratedDeviceIds"] == [row[0] for row in PINNED]
        assert report["sourcePage"] == 58
        for key, relative in zip(
            ("curated", "rulesDatabase", "deployedObjects"),
            STAGED_PATHS,
            strict=True,
        ):
            promoted_bytes = (CURATED.parents[3] / relative).read_bytes()
            assert promoted_bytes == (stage / relative).read_bytes()
            assert hashlib.sha256(promoted_bytes).hexdigest() == (
                report["stagedSha256"][key]
            )


def test_staging_rejects_overlapping_output_directory() -> None:
    # No source changes are needed to check the rejection ordering.
    with pytest.raises(ValueError, match="overlaps tracked inputs"):
        stage_hacking_device_chart_citations(CURATED.parent)


@pytest.mark.parametrize("fail_validation", [False, True])
def test_coordinated_promotion_retains_recovery_and_rolls_back(
    tmp_path: Path, fail_validation: bool,
) -> None:
    (tmp_path / "local").mkdir()
    original = {}
    staged = {}
    for i, relative in enumerate(STAGED_PATHS):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        original[relative] = f"original-{i}".encode()
        staged[relative] = f"staged-{i}".encode()
        target.write_bytes(original[relative])

    def validate() -> None:
        assert all((tmp_path / path).read_bytes() == staged[path] for path in STAGED_PATHS)
        if fail_validation:
            raise ValueError("post-promotion check failed")

    if fail_validation:
        with pytest.raises(RuntimeError, match="Promotion rolled back"):
            _replace_staged_batch(tmp_path, staged, validate)
    else:
        backup = _replace_staged_batch(tmp_path, staged, validate)
        assert backup.is_dir()

    expected = original if fail_validation else staged
    assert all((tmp_path / path).read_bytes() == expected[path] for path in STAGED_PATHS)
    backups = list((tmp_path / "local").glob("hacking-device-citation-backup-*"))
    assert len(backups) == 1
    assert all((backups[0] / path).read_bytes() == original[path] for path in STAGED_PATHS)


def test_promotion_rolls_back_when_second_artifact_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools import stage_hacking_device_chart_citations as migration

    (tmp_path / "local").mkdir()
    original = {}
    proposed = {}
    for index, relative in enumerate(STAGED_PATHS):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        original[relative] = f"old-{index}".encode()
        proposed[relative] = f"new-{index}".encode()
        target.write_bytes(original[relative])

    replace = migration.os.replace
    calls = 0

    def fail_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second-artifact failure")
        replace(source, destination)

    monkeypatch.setattr(migration.os, "replace", fail_second_replace)
    with pytest.raises(RuntimeError, match="Promotion rolled back"):
        migration._replace_staged_batch(tmp_path, proposed, lambda: None)
    assert all((tmp_path / path).read_bytes() == original[path] for path in STAGED_PATHS)
    backups = list((tmp_path / "local").glob("hacking-device-citation-backup-*"))
    assert len(backups) == 1
    assert all((backups[0] / path).read_bytes() == original[path] for path in STAGED_PATHS)
