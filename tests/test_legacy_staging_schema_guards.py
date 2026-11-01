"""Exercise legacy pre-promotion staging against disposable current-schema inputs."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from infinity_db.rules_database import RulesDatabase
from tools.audit_deployed_object_citation_migrations import (
    MANIFEST_PATHS,
    build_citation_migration_plan,
)
from tools.audit_hacking_device_program_source_chart import PINNED
from tools.stage_deployed_object_citation_migration import stage_citation_migration
from tools.stage_hacking_device_chart_citations import (
    SOURCE_CITATION,
    stage_hacking_device_chart_citations,
)
from tools.stage_terrain_scenery_references import (
    EXPECTED_IDS,
    stage_terrain_references,
)

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES_DB = ROOT / "data/generated/rules.db"
PUBLICATION = ROOT / "data/generated/deployed-objects.json"


def _temporary_curated_rules(tmp_path: Path) -> Path:
    rules_dir = tmp_path / "source/rules"
    shutil.copytree(CURATED.parent, rules_dir)
    return rules_dir / CURATED.name


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8", newline="\n",
    )


def _pending_citation_sources(tmp_path: Path, curated_path: Path) -> dict[str, Path]:
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    manifests = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in MANIFEST_PATHS.items()
    }
    plan = build_citation_migration_plan(curated, manifests)
    assert (plan["pendingCount"], plan["migratedCount"]) == (0, 14)
    records = {row["id"]: row for row in curated["records"]}
    for entry in plan["migrated"]:
        records[entry["recordId"]]["citations"].remove(entry["proposedCitation"])
        review = next(
            row for row in manifests[entry["reviewManifest"]]["reviews"]
            if row["recordId"] == entry["recordId"]
        )
        review_fields = dict(review)
        review.clear()
        review.update({
            "recordId": review_fields.pop("recordId"),
            "citationStatus": "pdf-verified-manifest-only",
            "pdfExcerpt": entry["pdfExcerpt"],
            **review_fields,
        })
    assert build_citation_migration_plan(curated, manifests)["pendingCount"] == 14
    _write_json(curated_path, curated)
    paths = {}
    for name, source in MANIFEST_PATHS.items():
        target = tmp_path / "source/manifests" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(manifests[name], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        paths[name] = target
    return paths


def _pending_device_citations(curated_path: Path) -> None:
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    records = {row["id"]: row for row in curated["records"]}
    for record_id, _, _ in PINNED:
        records[record_id]["citations"].remove(SOURCE_CITATION)
    _write_json(curated_path, curated)


def _pending_terrain_records(curated_path: Path) -> None:
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    original = len(curated["records"])
    curated["records"] = [
        row for row in curated["records"] if row["id"] not in EXPECTED_IDS
    ]
    assert len(curated["records"]) == original - len(EXPECTED_IDS)
    _write_json(curated_path, curated)


@pytest.mark.parametrize("stage_kind", ("citations", "terrain", "hacking-device"))
def test_legacy_staging_preserves_v9_restrictions_and_checkout(
    tmp_path: Path, stage_kind: str,
) -> None:
    """Staging must preserve schema, Restrictions and paired publication on v9."""
    immutable = (CURATED, RULES_DB, PUBLICATION, *MANIFEST_PATHS.values())
    originals = {path: hashlib.sha256(path.read_bytes()).digest() for path in immutable}
    staged_source = _temporary_curated_rules(tmp_path)
    output = tmp_path / "staged"
    if stage_kind == "citations":
        manifests = _pending_citation_sources(tmp_path, staged_source)
        report = stage_citation_migration(
            output, curated_path=staged_source, manifest_paths=manifests,
        )
    elif stage_kind == "terrain":
        _pending_terrain_records(staged_source)
        report = stage_terrain_references(output, curated_path=staged_source)
    else:
        _pending_device_citations(staged_source)
        report = stage_hacking_device_chart_citations(
            output, curated_path=staged_source,
        )

    staged_rules = output / "data/generated/rules.db"
    staged_publication = output / "data/generated/deployed-objects.json"
    with sqlite3.connect(RULES_DB) as current, sqlite3.connect(staged_rules) as staged:
        assert current.execute("PRAGMA user_version").fetchone()[0] == 9
        assert staged.execute("PRAGMA user_version").fetchone()[0] == 9
    current_restrictions = RulesDatabase(RULES_DB).restrictions_payload()
    assert len(current_restrictions["items"]) == 14
    assert RulesDatabase(staged_rules).restrictions_payload() == current_restrictions

    published = json.loads(staged_publication.read_text(encoding="utf-8"))
    active_publication = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    assert published["objects"] == active_publication["objects"]
    assert len(published["objects"]) == report["reviewedObjects"] == 17
    staged_hash = hashlib.sha256(staged_rules.read_bytes()).hexdigest()
    assert published["sourceSnapshot"]["rulesDatabaseSha256"] == staged_hash
    assert report["stagedSha256"]["rulesDatabase"] == staged_hash
    assert hashlib.sha256(staged_publication.read_bytes()).hexdigest() == (
        report["stagedSha256"]["deployedObjects"]
    )
    assert all(hashlib.sha256(path.read_bytes()).digest() == digest
               for path, digest in originals.items())
