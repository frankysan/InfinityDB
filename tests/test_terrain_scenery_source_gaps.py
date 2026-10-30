"""Source-backed terrain/scenery discovery beyond deployable chart and scenarios."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from infinity_db.curated import load_curated_document
from tools.audit_terrain_scenery_source_gaps import (
    CURATED,
    EXAMPLE_LABELS,
    GATE_MARKERS,
    PUBLICATION,
    SOURCE,
    TERRAIN_TYPES,
    audit_source_files,
    audit_terrain_scenery_boundary,
    main,
    verify_pinned_pdf,
)


def _inputs() -> tuple[dict, dict]:
    return load_curated_document(CURATED), json.loads(PUBLICATION.read_text(encoding="utf-8"))


def test_terrain_scenery_inventory_remains_outside_deployed_objects() -> None:
    report = audit_source_files()
    assert report["scope"] == "terrain-scene-context-not-army-deployed-object-inventory"
    assert report["sourcePages"] == [143, 144, 145]
    assert report["optionalGameTableRules"] is True
    assert report["terrainTypes"] == list(TERRAIN_TYPES)
    assert report["namedExampleCount"] == len(EXAMPLE_LABELS) == 18
    assert [row["printedName"] for row in report["terrainExamples"]] == list(EXAMPLE_LABELS)
    assert [row["printedName"] for row in report["sceneryGateTokens"]] == list(GATE_MARKERS)
    assert report["reviewStatus"] == {
        "terrainSkill": "maintained",
        "specialTerrainRule": "unmodelled",
        "accessWidthRule": "unmodelled",
        "accessWidthTokens": "unmodelled",
        "exampleTable": "unmodelled-not-18-missing-types",
    }
    assert report["publishedDeployedObjectCount"] == 17
    assert len(report["curatedSha256"]) == 64
    assert len(report["publishedObjectSha256"]) == 64
    assert report["verifiedPdfSha256"] is None


def test_pinned_english_pdf_terrain_and_scenery_source_inventory() -> None:
    pytest.importorskip("pymupdf")
    if not SOURCE.is_file():
        pytest.skip("Pinned local English N5.3 PDF unavailable")
    result = audit_source_files(pdf_path=SOURCE)
    assert len(result["verifiedPdfSha256"]) == 64
    assert result["verifiedPdfSha256"] == verify_pinned_pdf(SOURCE)


def test_terrain_scenery_audit_fails_closed_on_domain_promotion() -> None:
    curated, publication = _inputs()
    assert audit_terrain_scenery_boundary(curated, publication)["namedExampleCount"] == 18

    for added in ("Narrow Gate", "Wide Gate", "Engine Room"):
        mutated = copy.deepcopy(publication)
        mutated["objects"].append({"name": added, "id": "invented-" + added})
        with pytest.raises(ValueError, match="promoted"):
            audit_terrain_scenery_boundary(curated, mutated)

    missing_skill = copy.deepcopy(curated)
    missing_skill["records"] = [
        row for row in missing_skill["records"] if row["id"] != "skill:terrain"
    ]
    with pytest.raises(ValueError, match="Terrain Special Skill"):
        audit_terrain_scenery_boundary(missing_skill, publication)

    new_rule = copy.deepcopy(curated)
    new_rule["records"].append({
        "id": "rule:access-width", "kind": "rule", "name": "Access Width",
    })
    with pytest.raises(ValueError, match="needs re-review"):
        audit_terrain_scenery_boundary(new_rule, publication)


def test_terrain_scenery_source_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_terrain_scenery_source_gaps"])
    assert main() == 0
    result = capsys.readouterr().out
    assert "Current terrain Types: 5" in result
    assert "Suggested terrain examples: 18" in result
    assert "Scenery gate tokens: 2" in result
    assert "Unchanged deployed objects: 17" in result
