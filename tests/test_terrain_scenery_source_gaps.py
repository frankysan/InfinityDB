"""Source-backed terrain/scenery discovery beyond deployable chart and scenarios."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools.audit_terrain_scenery_source_gaps import (
    ARMY,
    CURATED,
    EXAMPLE_LABELS,
    GATE_MARKERS,
    RULES,
    SOURCE,
    TERRAIN_TYPES,
    audit_source_files,
    audit_terrain_scenery_boundary,
    main,
    verify_example_values,
    verify_pinned_pdf,
)


def _inputs() -> tuple[dict, dict]:
    publication = RulesDatabase(RULES).deployed_objects_payload(ARMY)
    assert publication is not None
    return (
        load_curated_document(CURATED),
        publication,
    )


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
        "specialTerrainRule": "maintained",
        "accessWidthRule": "maintained",
        "accessWidthTokens": "owner-aliases",
        "exampleTable": "maintained-source-suggestions",
    }
    assert report["publishedDeployedObjectCount"] == 17
    assert len(report["curatedSha256"]) == 64
    assert len(report["armyDatabaseSha256"]) == 64
    assert len(report["rulesDatabaseSha256"]) == 64
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

    for omitted in ({"rule:access-width"}, {"rule:special-terrain", "rule:access-width"}):
        missing = copy.deepcopy(curated)
        missing["records"] = [
            row for row in missing["records"] if row["id"] not in omitted
        ]
        with pytest.raises(ValueError, match="Partial"):
            audit_terrain_scenery_boundary(missing, publication)

    incorrect_source = copy.deepcopy(curated)
    next(
        row for row in incorrect_source["records"] if row["id"] == "rule:access-width"
    )["citations"][0]["page"] = 143
    with pytest.raises(ValueError, match="Unreviewed terrain/access source definition"):
        audit_terrain_scenery_boundary(incorrect_source, publication)


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


def test_suggested_terrain_values_preserve_optional_and_unresolved_source_cells() -> None:
    curated, publication = _inputs()
    records = {row["id"]: row for row in curated["records"]}
    table = records["rule:special-terrain"]["facts"]["terrainExamples"]
    assert table["scope"] == "optional-source-suggestions-not-terrain-types"
    assert [row["name"] for row in table["rows"]] == list(EXAMPLE_LABELS)
    rows = {row["name"]: row for row in table["rows"]}
    assert rows["Rocky Ground"]["difficultTerrain"] == "Optional"
    assert rows["Low Mountain or Steep Hills"]["difficultTerrain"] == "--"
    assert rows["Storm"]["visibility"] == "Increases Visibility Conditions by one level"
    assert rows["Storm"]["saturation"] == "--"
    assert rows["Energy Core Room"] == {
        "name": "Energy Core Room", "terrainType": "Optional Zero-G",
        "difficultTerrain": "Yes if Zero-G", "visibility": "Low Visibility + White Noise",
        "saturation": "--",
    }
    assert records["rule:access-width"]["aliases"] == list(GATE_MARKERS)
    assert not {"term:narrow-gate", "term:wide-gate"}.intersection(records)
    assert len(publication["objects"]) == 17
    assert not set(EXAMPLE_LABELS + GATE_MARKERS).intersection(
        obj["name"] for obj in publication["objects"]
    )


@pytest.mark.parametrize("case", (
    "scope", "owner", "missing-row", "duplicate-name", "missing-column",
    "extra-column", "boolean", "null", "blank",
))
def test_suggested_terrain_schema_rejects_lossy_or_ambiguous_values(
    tmp_path: Path, case: str,
) -> None:
    curated, _publication = _inputs()
    records = {row["id"]: row for row in curated["records"]}
    table = records["rule:special-terrain"]["facts"]["terrainExamples"]
    first = table["rows"][0]
    if case == "scope":
        table["scope"] = "mandatory-scenario-terrain"
    elif case == "owner":
        records["rule:access-width"]["facts"]["terrainExamples"] = table
    elif case == "missing-row":
        table["rows"].pop()
    elif case == "duplicate-name":
        table["rows"][1]["name"] = " beach "
    elif case == "missing-column":
        first.pop("saturation")
    elif case == "extra-column":
        first["deviceId"] = "invented"
    else:
        first["difficultTerrain"] = {"boolean": False, "null": None, "blank": " "}[case]
    path = tmp_path / "invalid-terrain.json"
    path.write_text(json.dumps(curated), encoding="utf-8")
    with pytest.raises(ValueError, match="terrainExamples"):
        load_curated_document(path)


@pytest.mark.parametrize("name,field,replacement", (
    ("Rocky Ground", "difficultTerrain", "Yes"),
    ("Low Mountain or Steep Hills", "difficultTerrain", "No"),
    ("Storm", "visibility", "Zero Visibility"),
    ("Engine Room", "difficultTerrain", "Yes"),
    ("Energy Core Room", "visibility", "White Noise"),
))
def test_pinned_terrain_source_comparison_detects_changed_cell_meaning(
    name: str, field: str, replacement: str,
) -> None:
    pytest.importorskip("pymupdf")
    if not SOURCE.is_file():
        pytest.skip("Pinned local English N5.3 PDF unavailable")
    curated, _publication = _inputs()
    table = next(row for row in curated["records"] if row["id"] == "rule:special-terrain")
    rows = table["facts"]["terrainExamples"]["rows"]
    assert verify_pinned_pdf(SOURCE) == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    verify_example_values(SOURCE, rows)
    next(row for row in rows if row["name"] == name)[field] = replacement
    with pytest.raises(ValueError, match="differ from the pinned source table"):
        verify_example_values(SOURCE, rows)


def test_terrain_table_and_gate_aliases_reach_storage_api_search_and_glossary() -> None:
    root = CURATED.parents[3]
    db = RulesDatabase(root / "data/generated/rules.db")
    app = create_app(root / "data/generated/infinity.db", rules_database_path=db.path)

    def get(path: str, query: str = "") -> dict:
        env = {}
        setup_testing_defaults(env)
        env.update(PATH_INFO=path, QUERY_STRING=query, REQUEST_METHOD="GET")
        statuses = []
        result = app(env, lambda status, _headers, _exc=None: statuses.append(status))
        try:
            body = b"".join(result)
        finally:
            close = getattr(result, "close", None)
            if close:
                close()
        assert statuses == ["200 OK"]
        return json.loads(body)

    curated, _publication = _inputs()
    source = next(row for row in curated["records"] if row["id"] == "rule:special-terrain")
    stored = db.composed_record(source["id"])
    assert stored is not None and stored["facts"] == source["facts"]
    published = get("/api/rules/special-terrain")["rules"][0]
    assert published["facts"] == source["facts"]
    assert {cite["page"] for cite in published["citations"]
            if cite["source_id"] == "n5-core-v5.3-pdf"} == {143, 145}
    glossary = get("/api/glossary")["items"]
    access = next(row for row in glossary if row["id"] == "rule:access-width")
    assert access["aliases"] == list(GATE_MARKERS)
    assert access["href"] == "/rules/access-width"
    for label in GATE_MARKERS:
        results = get("/api/search", urlencode({"q": label}))["items"]
        assert any(row["href"] == "/rules/access-width" for row in results)
