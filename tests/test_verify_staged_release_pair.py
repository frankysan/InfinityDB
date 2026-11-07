"""Read-only freshness gate for legacy staged rules/publication binaries."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools.stage_promoted_terrain_artifacts import stage_promoted_terrain_artifacts
from tools.verify_staged_release_pair import (
    CURATED,
    RELEASE_RULES,
    verify_staged_release_pair,
)


@pytest.fixture
def stage(tmp_path: Path) -> Path:
    output = tmp_path / "staged"
    stage_promoted_terrain_artifacts(output)
    return output


def test_current_staged_pair_passes_freshness_gate(stage: Path) -> None:
    accepted = verify_staged_release_pair(stage)
    assert accepted["schemaVersion"] == 9
    assert accepted["reviewedObjects"] == 17
    assert set(accepted["releaseBaselineSha256"]) == {
        "rulesDatabase", "deployedObjects",
    }


def test_rejects_stale_release_baseline(stage: Path, tmp_path: Path) -> None:
    changed = tmp_path / "different-rules.db"
    shutil.copyfile(RELEASE_RULES, changed)
    with changed.open("ab") as stream:
        stream.write(b"stale")
    with pytest.raises(ValueError, match="Release baseline changed"):
        verify_staged_release_pair(stage, active_rules=changed)


def test_rejects_mutated_staged_binary(stage: Path) -> None:
    published = stage / "data/generated/deployed-objects.json"
    with published.open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="Staged artifact digest changed"):
        verify_staged_release_pair(stage)


def test_rejects_legacy_report_without_baseline(stage: Path) -> None:
    path = stage / "staging-report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    del report["releaseBaselineSha256"]
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="lacks current-pair provenance"):
        verify_staged_release_pair(stage)


def test_rejects_curated_source_drift(stage: Path, tmp_path: Path) -> None:
    stale = tmp_path / "changed-source.json"
    stale.write_bytes(CURATED.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Curated source changed"):
        verify_staged_release_pair(stage, curated_path=stale)
