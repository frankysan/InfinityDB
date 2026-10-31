"""Preflight all three audit-only N5.3 citation migrations together."""

from __future__ import annotations

import copy
import hashlib
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
from tools.stage_deployed_object_citation_migration import (
    prepare_migrated_inputs,
    stage_citation_migration,
)


def _inputs() -> tuple[dict, dict[str, dict]]:
    return (
        json.loads(CURATED.read_text(encoding="utf-8")),
        {
            key: json.loads(path.read_text(encoding="utf-8"))
            for key, path in MANIFEST_PATHS.items()
        },
    )


def _pending_inputs() -> tuple[dict, dict[str, dict]]:
    """Reconstruct the reviewed pending state for negative tests after promotion."""
    curated, manifests = _inputs()
    current = build_citation_migration_plan(curated, manifests)
    for entry in current["migrated"]:
        record = next(
            item for item in curated["records"] if item["id"] == entry["recordId"]
        )
        record["citations"].remove(entry["proposedCitation"])
        review = next(
            item for item in manifests[entry["reviewManifest"]]["reviews"]
            if item["recordId"] == entry["recordId"]
        )
        review["citationStatus"] = "pdf-verified-manifest-only"
        review["pdfExcerpt"] = entry["pdfExcerpt"]
    assert build_citation_migration_plan(curated, manifests)["pendingCount"] == 14
    return curated, manifests


def test_pinned_citation_migration_preflight_preserves_provenance() -> None:
    report = audit_citations()
    assert report["scope"] == "citation-preflight-only-no-source-or-runtime-modification"
    assert report["source"] == "n5-core-v5.3-pdf"
    assert (report["pendingCount"], report["migratedCount"]) in ((14, 0), (0, 14))
    assert report["countsByManifest"] == {
        "non-catalog": 6, "expanded": 5, "source-domain": 3,
    }
    assert len(report["curatedSourceSha256"]) == 64
    assert set(report["reviewManifestSha256"]) == set(MANIFEST_PATHS)
    assert all(len(digest) == 64 for digest in report["reviewManifestSha256"].values())
    all_reviews = report["pending"] + report["migrated"]
    assert len({row["recordId"] for row in all_reviews}) == 14
    assert all(
        row["proposedCitation"]["sourceId"] == "n5-core-v5.3-pdf"
        and isinstance(row["proposedCitation"]["page"], int)
        and row["pdfExcerpt"]
        for row in all_reviews
    )
    assert {
        row["recordId"]: row["proposedCitation"]["page"]
        for row in all_reviews
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
        key in row for row in all_reviews
        for key in ("objectProfile", "delivery", "sourceProfile", "unitCarriers")
    )


def test_preflight_rejects_lost_review_and_stale_or_published_citation() -> None:
    curated, manifests = _pending_inputs()
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
    current = build_citation_migration_plan(*_inputs())
    assert f"Audit-only citations pending migration: {current['pendingCount']}" in output
    assert f"Verified maintained citations migrated: {current['migratedCount']}" in output
    assert "No curated sources, generated databases" in output
    assert CURATED.read_bytes() == original

    # A copy of the curated document is accepted as input; it is never edited.
    copied = tmp_path / "curated.json"
    copied.write_bytes(original)
    assert audit_citations(copied)["pendingCount"] == current["pendingCount"]
    assert copied.read_bytes() == original


def test_migration_staging_is_complete_and_does_not_touch_inputs(tmp_path: Path) -> None:
    original_curated = CURATED.read_bytes()
    original_manifests = {name: path.read_bytes() for name, path in MANIFEST_PATHS.items()}
    original_rules = (CURATED.parents[2] / "generated/rules.db").read_bytes()
    original_publication = (
        CURATED.parents[2] / "generated/deployed-objects.json"
    ).read_bytes()

    if audit_citations()["pendingCount"] == 0:
        pytest.skip("Migration already promoted; staging covered before promotion")
    output = tmp_path / "stage"
    report = stage_citation_migration(output)
    assert report["migratedCount"] == 14
    assert report["reviewedObjects"] == 17
    assert len(report["stagedPaths"]) == 6
    staged = json.loads(
        (output / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    manifests = {
        name: json.loads((output / "config/validation" / path.name).read_text(
            encoding="utf-8",
        ))
        for name, path in MANIFEST_PATHS.items()
    }
    after = build_citation_migration_plan(staged, manifests)
    assert after["pendingCount"] == 0
    assert after["migratedCount"] == 14
    assert len((output / "data/generated/rules.db").read_bytes()) > 0
    publication = json.loads(
        (output / "data/generated/deployed-objects.json").read_text(encoding="utf-8")
    )
    assert len(publication["objects"]) == 17
    assert publication["sourceSnapshot"]["rulesDatabaseSha256"] == (
        report["stagedSha256"]["rulesDatabase"]
    )
    assert (output / "migration-report.json").is_file()
    assert original_curated == CURATED.read_bytes()
    assert original_rules == (CURATED.parents[2] / "generated/rules.db").read_bytes()
    assert original_publication == (
        CURATED.parents[2] / "generated/deployed-objects.json"
    ).read_bytes()
    assert original_manifests == {
        name: path.read_bytes() for name, path in MANIFEST_PATHS.items()
    }
    with pytest.raises(FileExistsError):
        stage_citation_migration(output)


def test_migration_staging_rejects_partial_and_duplicate_inputs() -> None:
    curated, manifests = _pending_inputs()
    plan = build_citation_migration_plan(curated, manifests)
    migrated, manifest_changes = prepare_migrated_inputs(
        copy.deepcopy(curated), copy.deepcopy(manifests), plan,
    )
    with pytest.raises(ValueError, match="already cites"):
        prepare_migrated_inputs(migrated, manifest_changes, plan)
    # Neither a source-only citation nor a manifest-only update may be
    # mistaken for a complete coordinated migration.
    partial = copy.deepcopy(curated)
    next(record for record in partial["records"] if record["id"] == "skill:frenzy")[
        "citations"
    ].append({"sourceId": "n5-core-v5.3-pdf", "page": 93})
    with pytest.raises(ValueError, match="PDF-only provenance"):
        build_citation_migration_plan(partial, manifests)


def test_promoted_artifacts_match_staging_report_when_available() -> None:
    """Verify historical staging evidence without freezing later release bytes."""
    repo = CURATED.parents[3]
    stage = repo / "local/citation-migration-n53"
    report_path = stage / "migration-report.json"
    if not report_path.is_file():
        pytest.skip("Local migration staging report is unavailable")
    report = audit_citations()
    if report["migratedCount"] != 14:
        pytest.skip("Citation migration has not yet been promoted")

    staged = json.loads(report_path.read_text(encoding="utf-8"))
    assert staged["scope"] == "staged-artifacts-only-not-applied-or-committed"
    assert staged["migratedCount"] == 14
    assert staged["reviewedObjects"] == 17
    assert len(staged["stagedPaths"]) == 6

    # The ignored staging directory records the earlier citation migration.
    # Later source reviews and schema v9 must not invalidate that evidence.
    assert all((stage / relative).is_file() for relative in staged["stagedPaths"])
    for key, relative in (
        ("rulesDatabase", "data/generated/rules.db"),
        ("deployedObjects", "data/generated/deployed-objects.json"),
    ):
        digest = hashlib.sha256((stage / relative).read_bytes()).hexdigest()
        assert digest == staged["stagedSha256"][key]

    staged_publication = json.loads(
        (stage / "data/generated/deployed-objects.json").read_text(encoding="utf-8")
    )
    assert staged_publication["sourceSnapshot"]["rulesDatabaseSha256"] == (
        staged["stagedSha256"]["rulesDatabase"]
    )
    publication = json.loads(
        (repo / "data/generated/deployed-objects.json").read_text(encoding="utf-8")
    )
    assert len(publication["objects"]) == 17
    assert publication["sourceSnapshot"]["rulesDatabaseSha256"] == hashlib.sha256(
        (repo / "data/generated/rules.db").read_bytes()
    ).hexdigest()
    assert publication["objects"] == staged_publication["objects"]
    assert publication["unresolvedDeliveries"] == staged_publication["unresolvedDeliveries"]

