"""Staged source-backed Special Terrain and Access Width reference publication."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from tools.audit_terrain_scenery_source_gaps import (
    CURATED,
    PUBLICATION,
    SOURCE,
    audit_terrain_scenery_boundary,
)
from tools.stage_terrain_scenery_references import (
    ADDITIONS,
    insert_reference_records,
    stage_terrain_references,
    verify_additions,
)


def test_reference_proposals_preserve_game_table_scope() -> None:
    additions = json.loads(ADDITIONS.read_text(encoding="utf-8"))
    records = verify_additions(additions)
    assert [row["id"] for row in records] == [
        "rule:special-terrain", "rule:access-width",
    ]
    terrain, access = records
    assert "Aquatic" in " ".join(terrain["facts"]["effects"])
    assert "Difficult Terrain" in " ".join(terrain["facts"]["effects"])
    assert "Saturation" in " ".join(terrain["facts"]["effects"])
    assert "Visibility Conditions" in " ".join(terrain["facts"]["effects"])
    assert "Silhouette" in " ".join(access["facts"]["effects"])
    assert "Prone" in " ".join(access["facts"]["restrictions"])
    assert "Narrow Gate" in " ".join(access["facts"]["effects"])
    assert all(row["kind"] == "rule" and not row["relations"] for row in records)

    changed = copy.deepcopy(additions)
    changed["records"][1]["citations"][0]["page"] = 143
    with pytest.raises(ValueError, match="source definition shape"):
        verify_additions(changed)


def test_reference_staging_preserves_originals_and_rebuilds_publication(
    tmp_path: Path,
) -> None:
    current = load_curated_document(CURATED)
    if any(
        row["id"] == "rule:special-terrain" for row in current["records"]
    ):
        pytest.skip("Rule references already promoted; staging is pre-promotion only")
    source_before = CURATED.read_bytes()
    publication_before = PUBLICATION.read_bytes()
    rules = CURATED.parents[2] / "generated/rules.db"
    rules_before = rules.read_bytes()
    directory = tmp_path / "terrain-staged"
    result = stage_terrain_references(
        directory, pdf_path=SOURCE if SOURCE.exists() else None,
    )
    assert result["scope"] == "staged-only-no-checkout-modification"
    assert result["proposedIds"] == [
        "rule:special-terrain", "rule:access-width",
    ]
    assert result["reviewedObjects"] == 17
    assert len(result["stagedPaths"]) == 3
    for key, relative in (
        ("curated", "data/curated/rules/n5-core-v5.3.json"),
        ("rulesDatabase", "data/generated/rules.db"),
        ("deployedObjects", "data/generated/deployed-objects.json"),
    ):
        assert result["stagedSha256"][key] == hashlib.sha256(
            (directory / relative).read_bytes()
        ).hexdigest()
    staged = load_curated_document(directory / result["stagedPaths"][0])
    with sqlite3.connect(directory / "data/generated/rules.db") as connection:
        records = connection.execute(
            "SELECT id, kind FROM records WHERE id IN (?, ?) ORDER BY id",
            ("rule:access-width", "rule:special-terrain"),
        ).fetchall()
    assert records == [
        ("rule:access-width", "rule"),
        ("rule:special-terrain", "rule"),
    ]
    old_pub = json.loads(publication_before)
    report = audit_terrain_scenery_boundary(staged, old_pub)
    assert report["reviewStatus"]["specialTerrainRule"] == "maintained"
    assert report["reviewStatus"]["accessWidthRule"] == "maintained"
    new_pub = json.loads(
        (directory / "data/generated/deployed-objects.json").read_text(encoding="utf-8")
    )
    assert new_pub["sourceSnapshot"]["rulesDatabaseSha256"] == (
        result["stagedSha256"]["rulesDatabase"]
    )
    assert len(new_pub["objects"]) == 17
    assert source_before == CURATED.read_bytes()
    assert rules_before == rules.read_bytes()
    assert publication_before == PUBLICATION.read_bytes()
    assert (directory / "staging-report.json").is_file()
    with pytest.raises(FileExistsError):
        stage_terrain_references(directory)


def test_promoted_terrain_rules_match_tracked_database_when_available() -> None:
    source = load_curated_document(CURATED)
    names = {item["id"] for item in source["records"]}
    if not names.intersection({"rule:special-terrain", "rule:access-width"}):
        pytest.skip("Reference additions not yet promoted")
    assert {"rule:special-terrain", "rule:access-width"} <= names
    db_path = CURATED.parents[2] / "generated/rules.db"
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, kind FROM records WHERE id IN (?, ?) ORDER BY id",
            ("rule:access-width", "rule:special-terrain"),
        ).fetchall()
    assert rows == [
        ("rule:access-width", "rule"),
        ("rule:special-terrain", "rule"),
    ]
    published = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    assert published["sourceSnapshot"]["rulesDatabaseSha256"] == hashlib.sha256(
        db_path.read_bytes()
    ).hexdigest()
    audit = audit_terrain_scenery_boundary(source, published)
    assert audit["reviewStatus"]["specialTerrainRule"] == "maintained"
    assert audit["reviewStatus"]["accessWidthRule"] == "maintained"


def test_reference_insertion_rejects_duplicates_and_unrelated_changes() -> None:
    original = CURATED.read_text(encoding="utf-8")
    additions = verify_additions(json.loads(ADDITIONS.read_text(encoding="utf-8")))
    current = json.loads(original)
    if any(record["id"] == additions[0]["id"] for record in current["records"]):
        pytest.skip("Rules already promoted")
    changed = insert_reference_records(original, additions)
    doc = json.loads(changed)
    assert doc["records"][-2:] == additions
    assert doc["records"][:-2] == current["records"]
    assert doc["scenarioComponents"] == current["scenarioComponents"]
    with pytest.raises(ValueError, match="already exist"):
        insert_reference_records(changed, additions)
    with pytest.raises(ValueError, match="Partial"):
        audit_terrain_scenery_boundary(
            {**doc, "records": doc["records"][:-1]},
            json.loads(PUBLICATION.read_text(encoding="utf-8")),
        )
