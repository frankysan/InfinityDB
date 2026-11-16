"""Current-source terrain/scenery boundaries and published reference parity."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
ARMY = ROOT / "data/generated/army.db"
RULES = ROOT / "data/generated/rules_n5.db"

# Previously reviewed from N5.3 pp.143–145. Examples and gate labels do not
# acquire independent Terrain Type or deployed-object identities.
TERRAIN_TYPES = ("Aquatic", "Desert", "Mountain", "Jungle", "Zero-G")
EXAMPLE_LABELS = (
    "Beach", "Open Sea", "Swamp", "Rocky Ground", "Sand Dunes",
    "Low Mountain or Steep Hills", "Artic Plains", "Mid-Mountain",
    "High Mountain", "Woods", "Jungle", "Dense Jungle",
    "Primeval Forest", "Zero-G", "Storm", "Engine Room",
    "Generator Room", "Energy Core Room",
)
GATE_MARKERS = ("Narrow Gate", "Wide Gate")


def _inputs() -> tuple[dict, dict]:
    rules = RulesDatabase(RULES)
    rules.validate()
    publication = rules.deployed_objects_payload(ARMY)
    assert publication is not None
    return load_curated_document(CURATED), publication


def test_terrain_and_scenery_remain_separate_from_deployed_objects() -> None:
    curated, publication = _inputs()
    records = {row["id"]: row for row in curated["records"]}
    assert len(records) == len(curated["records"])
    assert records["skill:terrain"]["kind"] == "skill"

    for record_id, name, page in (
        ("rule:special-terrain", "Special Terrain", 143),
        ("rule:access-width", "Access Width", 145),
    ):
        record = records[record_id]
        assert record["kind"] == "rule"
        assert record["name"] == name
        assert record["composition"] == {"role": "definition"}
        assert record["scope"] == {"game": "N5", "seasons": ["current"]}
        assert record["facts"]["category"] == "basic-rule"
        assert record["facts"]["effects"]
        assert record["facts"]["restrictions"]
        assert any(
            cite["sourceId"] == "n5-core-v5.3-pdf" and cite.get("page") == page
            for cite in record["citations"]
        )

    assert records["rule:access-width"]["aliases"] == list(GATE_MARKERS)
    assert not {"term:narrow-gate", "term:wide-gate"}.intersection(records)
    table = records["rule:special-terrain"]["facts"]["terrainExamples"]
    assert table["scope"] == "optional-source-suggestions-not-terrain-types"
    assert [row["name"] for row in table["rows"]] == list(EXAMPLE_LABELS)
    assert len(table["rows"]) == 18
    assert all(
        set(row) == {
            "name", "terrainType", "difficultTerrain", "visibility", "saturation",
        }
        for row in table["rows"]
    )
    assert len(TERRAIN_TYPES) == 5
    assert len(GATE_MARKERS) == 2

    objects = publication["objects"]
    assert len(objects) == 17
    assert len({obj["id"] for obj in objects}) == 17
    excluded = {name.casefold() for name in (*EXAMPLE_LABELS, *GATE_MARKERS)}
    assert all(obj["name"].strip().casefold() not in excluded for obj in objects)


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


def test_terrain_table_and_gate_aliases_reach_storage_api_search_and_glossary() -> None:
    root = CURATED.parents[3]
    db = RulesDatabase(root / "data/generated/rules_n5.db")
    app = create_app(root / "data/generated/army.db", rules_database_path=db.path)

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
