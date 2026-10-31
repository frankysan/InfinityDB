"""Regenerate promoted terrain/scenery binaries without touching tracked files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.audit_terrain_scenery_source_gaps import CURATED, PUBLICATION
from tools.stage_promoted_terrain_artifacts import stage_promoted_terrain_artifacts


def test_promoted_terrain_rebuild_is_source_pinned_and_nonmutating(
    tmp_path: Path,
) -> None:
    source_before = CURATED.read_bytes()
    publication_before = PUBLICATION.read_bytes()
    rules = CURATED.parents[2] / "generated/rules.db"
    rules_before = rules.read_bytes()
    output = tmp_path / "regenerated"
    report = stage_promoted_terrain_artifacts(output)

    assert report["scope"] == "post-promotion-binary-rebuild-not-applied"
    assert report["reviewedRuleIds"] == [
        "rule:special-terrain", "rule:access-width",
    ]
    assert report["reviewedObjects"] == 17
    assert report["sourceSha256"] == hashlib.sha256(source_before).hexdigest()
    assert report["stagedPaths"] == [
        "data/generated/rules.db", "data/generated/deployed-objects.json",
    ]
    for name, relative in (
        ("rulesDatabase", "data/generated/rules.db"),
        ("deployedObjects", "data/generated/deployed-objects.json"),
    ):
        assert report["stagedSha256"][name] == hashlib.sha256(
            (output / relative).read_bytes()
        ).hexdigest()
    deployed = json.loads(
        (output / "data/generated/deployed-objects.json").read_text(encoding="utf-8")
    )
    assert len(deployed["objects"]) == 17
    assert deployed["sourceSnapshot"]["rulesDatabaseSha256"] == (
        report["stagedSha256"]["rulesDatabase"]
    )
    assert source_before == CURATED.read_bytes()
    assert publication_before == PUBLICATION.read_bytes()
    assert rules_before == rules.read_bytes()
    assert (output / "staging-report.json").is_file()
    with pytest.raises(FileExistsError):
        stage_promoted_terrain_artifacts(output)


def test_promoted_terrain_publication_matches_rules_database_and_stage() -> None:
    """Require matching published binaries and check exact local staging provenance."""
    root = CURATED.parents[3]
    rules = root / "data/generated/rules.db"
    payload = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    rule_hash = hashlib.sha256(rules.read_bytes()).hexdigest()
    assert payload["sourceSnapshot"]["rulesDatabaseSha256"] == rule_hash
    assert len(payload["objects"]) == 17

    stage = root / "local/terrain-scenery-refresh-n53"
    report_path = stage / "staging-report.json"
    if not report_path.is_file():
        return  # Ignored local staging output is not a CI prerequisite.
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["scope"] == "post-promotion-binary-rebuild-not-applied"
    assert report["reviewedRuleIds"] == [
        "rule:special-terrain", "rule:access-width",
    ]
    assert report["reviewedObjects"] == 17
    assert report["stagedPaths"] == [
        "data/generated/rules.db", "data/generated/deployed-objects.json",
    ]
    for key, relative in (
        ("rulesDatabase", "data/generated/rules.db"),
        ("deployedObjects", "data/generated/deployed-objects.json"),
    ):
        # Historical local staging may predate later source citations or
        # rules.db schema migrations. Check its preserved evidence rather
        # than demanding byte identity with the current release pair.
        staged = (stage / relative).read_bytes()
        assert hashlib.sha256(staged).hexdigest() == report["stagedSha256"][key]
    old_publication = json.loads(
        (stage / "data/generated/deployed-objects.json").read_text(encoding="utf-8")
    )
    assert old_publication["sourceSnapshot"]["rulesDatabaseSha256"] == (
        report["stagedSha256"]["rulesDatabase"]
    )
    assert payload["objects"] == old_publication["objects"]
    assert payload["unresolvedDeliveries"] == old_publication["unresolvedDeliveries"]


def test_promoted_rebuild_rejects_output_inside_source_directory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "missing.json"
    source.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="overlap"):
        stage_promoted_terrain_artifacts(tmp_path / "nested", curated_path=source)
