from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.report_reference_baseline import (
    ReferenceBaselineError,
    _artifact_evidence,
    _revision_oldid,
    _source_location,
    build_baseline,
    main,
    render_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"


def test_baseline_reports_pinned_publication_without_claiming_completeness() -> None:
    report = build_baseline(ARMY_DB, RULES_DB)

    assert report["status"] == "initial-evidence-only-not-a-completeness-verdict"
    assert report["armySnapshot"]["archiveVerification"] == "not-supplied"
    assert len(report["armySnapshot"]["archiveSha256"]) == 64
    assert len(report["rulesPublication"]["publishedDatabaseSha256"]) == 64
    assert report["scenarioMembershipCount"] == 4
    assert "rules:scenario" in {item["id"] for item in report["inventory"]}
    assert "army:profiles" in {item["id"] for item in report["inventory"]}
    assert all(item["scopeDecision"] == "pending" for item in report["inventory"])
    assert all(item["browserEntryPoint"] is None for item in report["inventory"])
    assert all(item["apiReadPath"] is None for item in report["inventory"])
    assert all(item["factCoverage"] == "not-reviewed-against-source"
               for item in report["inventory"])
    assert len(report["sourceInventory"]) >= len(report["sourceGroups"])
    # URL-backed Wiki revisions cannot be collapsed into one generic source.
    revisions = [source for source in report["sourceGroups"]
                 if source["verificationStatus"] == "revision-url-pinned"]
    assert len(revisions) > 1
    assert len({source["url"] for source in revisions}) == len(revisions)
    assert all(source["revisionOldid"] for source in revisions)
    assert sum(report["sourceVerificationCounts"].values()) == len(report["sourceGroups"])
    assert all(item["rowsWithCitations"] <= item["publishedRows"]
               for item in report["inventory"] if item["rowsWithCitations"] is not None)


def test_unavailable_sources_and_pinned_url_revisions_are_not_conflated(
    tmp_path: Path,
) -> None:
    report = build_baseline(ARMY_DB, RULES_DB, root=tmp_path)
    assert any(item["localStatus"] == "missing-local-artifact"
               for item in report["sourceGroups"])
    assert any(item["localStatus"] == "url-backed/no-local-artifact"
               for item in report["sourceGroups"])
    assert _source_location(tmp_path, "../outside.pdf") == "unsafe-declared-path"
    assert _source_location(tmp_path, r"..\outside.pdf") == "unsafe-declared-path"
    assert _source_location(tmp_path, r"C:\outside.pdf") == "unsafe-declared-path"
    assert _source_location(tmp_path, None) == "url-backed/no-local-artifact"
    assert "not a completeness verdict" in render_markdown(report)


def test_local_source_hash_evidence_and_unpinned_pdf(tmp_path: Path) -> None:
    path = tmp_path / "rules.pdf"
    path.write_bytes(b"pinned bytes")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()

    matched = _artifact_evidence(tmp_path, "rules.pdf", None, {checksum})
    assert matched["verificationStatus"] == "hash-matched"
    assert matched["artifactSha256"] == checksum
    assert matched["declaredHashMatches"] is True

    unpinned = _artifact_evidence(tmp_path, "rules.pdf", None, set())
    assert unpinned["verificationStatus"] == "local-file-no-hash-pin"
    assert unpinned["artifactSha256"] == checksum

    wrong = _artifact_evidence(tmp_path, "rules.pdf", None, {"0" * 64})
    assert wrong["verificationStatus"] == "hash-mismatch-needs-review"
    assert wrong["declaredHashMatches"] is False
    conflict = _artifact_evidence(tmp_path, "rules.pdf", None, {checksum, "0" * 64})
    assert conflict["verificationStatus"] == "conflicting-source-hashes"


def test_url_pin_is_not_offline_content_verification(tmp_path: Path) -> None:
    exact = "https://infinitythewiki.com/index.php?title=Reset&oldid=3056"
    assert _revision_oldid(exact) == "3056"
    assert _revision_oldid("https://infinitythewiki.com/wiki/Reset") is None
    assert _revision_oldid(exact + "&oldid=3057") is None
    pinned = _artifact_evidence(tmp_path, None, exact, set())
    assert pinned["verificationStatus"] == "revision-url-pinned"
    assert pinned["artifactSha256"] is None
    assert pinned["declaredHashMatches"] is None
    assert _artifact_evidence(tmp_path, None, "https://example.org", set())[
        "verificationStatus"] == "url-without-revision-pin"


def test_baseline_requires_published_databases_and_verified_supplied_army_zip(
    tmp_path: Path,
) -> None:
    with pytest.raises(ReferenceBaselineError, match="database is unavailable"):
        build_baseline(tmp_path / "missing.db", RULES_DB)
    archive = tmp_path / "unmatched.zip"
    archive.write_bytes(b"incorrect source bytes")
    with pytest.raises(ReferenceBaselineError, match="differs from published metadata"):
        build_baseline(ARMY_DB, RULES_DB, army_archive=archive)


def test_baseline_cli_writes_stable_local_reports(tmp_path: Path) -> None:
    json_output = tmp_path / "baseline.json"
    markdown_output = tmp_path / "baseline.md"
    args = [
        "--army-db", str(ARMY_DB), "--rules-db", str(RULES_DB),
        "--json-output", str(json_output),
        "--markdown-output", str(markdown_output),
    ]
    assert main(args) == 0
    first = json_output.read_bytes()
    assert main(args) == 0
    assert json_output.read_bytes() == first
    assert json.loads(first)["formatVersion"] == 2
    assert "## Outstanding 1.0 evidence" in markdown_output.read_text(encoding="utf-8")
