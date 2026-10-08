from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.report_reference_baseline import (
    ReferenceBaselineError,
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
    assert _source_location(tmp_path, None) == "url-backed/no-local-artifact"
    assert "not a completeness verdict" in render_markdown(report)


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
    assert json.loads(first)["formatVersion"] == 1
    assert "## Outstanding 1.0 evidence" in markdown_output.read_text(encoding="utf-8")
