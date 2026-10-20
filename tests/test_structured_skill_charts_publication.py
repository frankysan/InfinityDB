"""Release-contract parity for Army Martial Arts, Booty, and MetaChemistry charts."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.database.repository import Database
from infinity_db.structured_chart_outcomes import (
    project_booty_rows,
    project_metachemistry_rows,
)
from infinity_db.web import create_app
from tools.verify_structured_skill_charts_browser import CHARTS, source_charts

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"


def _get(app: Any, path: str) -> tuple[str, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def start_response(status: str, _headers: list, _exc_info: object = None) -> None:
        statuses.append(status)

    response = app(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1, path
    return statuses[0], body


def _roll_positions(rows: list[dict[str, Any]], chart: str) -> list[int]:
    """Expand source roll ranges without inferring random result semantics."""
    result: list[int] = []
    for row in rows:
        notation = str(row["roll"])
        match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", notation)
        assert match is not None, (chart, notation)
        low = int(match.group(1))
        high = int(match.group(2) or low)
        assert 1 <= low <= high <= 20, (chart, notation)
        result.extend(range(low, high + 1))
    return result


def test_all_published_structured_skill_charts_preserve_army_rows_and_api() -> None:
    database = Database(ARMY_DB)
    expected = source_charts(database)
    assert set(expected) == {"martial-arts", "booty", "metachemistry"}
    assert set(expected) == set(CHARTS)

    with sqlite3.connect(ARMY_DB) as connection:
        for slug, chart in CHARTS.items():
            rows = expected[slug]["rows"]
            assert rows, slug
            source_columns = ", ".join(chart["columns"])
            stored = [
                dict(zip(chart["columns"], item, strict=True))
                for item in connection.execute(
                    f"SELECT {source_columns} FROM {chart['table']} ORDER BY {chart['order']}"
                )
            ]
            assert [
                {
                    key: value for key, value in row.items()
                    if key not in {"conditional_outcomes", "outcome_components"}
                }
                for row in rows
            ] == stored, slug
            if slug == "martial-arts":
                assert [str(row["level"]) for row in rows] == [
                    "1", "2", "3", "4", "5"
                ]
                assert [int(row["position"]) for row in rows] == list(range(1, 6))
            else:
                covered = _roll_positions(rows, slug)
                assert covered == list(range(1, 21)), (slug, covered)
                assert len({row["id"] for row in rows}) == len(rows), slug

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    status, body = _get(app, "/api/skills")
    assert status == "200 OK"
    published = json.loads(body)["items"]
    by_slug = {row["slug"]: row for row in published}
    assert set(CHARTS) <= set(by_slug)

    status, body = _get(app, "/skills")
    assert status == "200 OK"
    assert b'data-catalog="skills"' in body
    assert b"/static/catalog-list.js" in body

    for slug, chart in CHARTS.items():
        status, body = _get(app, f"/api/skills/{slug}")
        assert status == "200 OK", slug
        detail = json.loads(body)
        assert detail["slug"] == slug
        assert detail["name"] == by_slug[slug]["name"]
        structured = detail["structured_reference"]
        assert structured == expected[slug], slug
        assert structured["kind"] == chart["kind"], slug
        assert structured["title"] == chart["title"], slug

        status, body = _get(app, f"/skills/{slug}")
        assert status == "200 OK", slug
        assert b"/static/skill.js" in body
        assert b'id="skill-content"' in body

    javascript = (ROOT / "src/infinity_db/web/static/skill.js").read_text(
        encoding="utf-8"
    )
    assert "structuredReferenceSection(skill.structured_reference)" in javascript
    assert 'if (reference.kind === "martial-arts")' in javascript
    assert 'if (reference.kind === "random-chart")' in javascript
    assert "randomChartOutcome(row)" in javascript
    assert "row.conditional_outcomes" in javascript
    assert 'className = "chart-outcome-branches"' in javascript
    assert 'const hasPsMod = reference.rows.some(' in javascript
    assert '{ label: "Burst MOD", role: "metric" }' in javascript
    stylesheet = (ROOT / "src/infinity_db/web/static/components.css").read_text(
        encoding="utf-8"
    )
    assert ".chart-outcome-branches {\n  white-space: pre-line;" in stylesheet
    assert 'row.outcome_components' in javascript
    assert 'className = "chart-outcome-component"' in javascript
    assert ".chart-outcome-component {\n  display: inline-block;" in stylesheet


def test_army_chart_source_fields_preserve_n5_reference_distinctions() -> None:
    """Guard reviewed N5 chart distinctions without inventing new game effects."""

    database = Database(ARMY_DB)
    martial_arts = database.list_martial_arts_levels()
    # The N5 Martial Arts chart has Attack, Opponent, and Burst modifiers.
    # The source's extra PS MOD column is not a current rules benefit.
    assert all(row["ps_mod"] in (None, "", "-") for row in martial_arts), martial_arts

    booty = database.list_booty_results()
    conditional = {
        str(row["roll"]): str(row["result"])
        for row in booty
        if "TAG:" in str(row["result"])
    }
    # These four results have different effects for TAGs and other
    # Troop Types; flattening them would change the game outcome.
    assert set(conditional) == {"12", "16", "18", "20"}, conditional
    assert all("Other Troop Types:" in result for result in conditional.values())
    assert all(
        " / Other Troop Types: " in result for result in conditional.values()
    ), conditional

    projected = project_booty_rows(booty)
    assert all("conditional_outcomes" not in row for row in booty)
    assert {row["roll"] for row in projected if "conditional_outcomes" in row} == {
        "12", "16", "18", "20"
    }
    for row in projected:
        if "conditional_outcomes" not in row:
            continue
        branches = row["conditional_outcomes"]
        assert [branch["scope"] for branch in branches] == [
            "tag", "other-troop-types"
        ]
        assert [branch["label"] for branch in branches] == ["TAG", "Other Troop Types"]
        assert " / ".join(
            f"{branch['label']}: {branch['result']}" for branch in branches
        ) == row["result"]


def test_conditional_booty_parser_fails_closed_for_unreviewed_source_syntax() -> None:
    for malformed in (
        "TAG: Immunity (AP)",
        "Other Troop Types: +2 ARM",
        "TAG: / Other Troop Types: +2 ARM",
        "TAG: Immunity (AP) / Other Troop Types: ",
        "TAG: Immunity (AP) / Other Troop Types: +2 ARM / Unknown: X",
    ):
        with pytest.raises(ValueError):
            project_booty_rows([{"id": 12, "roll": "12", "result": malformed}])


def test_metachemistry_compound_source_outcomes_match_reviewed_n5_chart() -> None:
    expected = {
        "16": "+1 ARM + Immunity (ARM)",
        "17": "Dogged + Immunity (Enhanced)",
        "18": "MOV: 6-4 + Super-Jump",
        "19": "MOV: 8-4 + Climbing Plus",
        "20": "+3 PH + Regeneration",
    }
    rows = Database(ARMY_DB).list_metachemistry_results()
    assert {row["roll"]: row["result"] for row in rows if row["roll"] in expected} == expected


def test_metachemistry_compounds_are_typed_and_source_preserving() -> None:
    raw = Database(ARMY_DB).list_metachemistry_results()
    projected = project_metachemistry_rows(raw)
    assert all("outcome_components" not in row for row in raw)
    components = {
        row["roll"]: row["outcome_components"]
        for row in projected
        if "outcome_components" in row
    }
    assert set(components) == {"16", "17", "18", "19", "20"}
    assert {
        roll: [part["kind"] for part in parts]
        for roll, parts in components.items()
    } == {
        "16": ["attribute-modifier", "special-skill"],
        "17": ["special-skill", "special-skill"],
        "18": ["movement-value", "special-skill"],
        "19": ["movement-value", "special-skill"],
        "20": ["attribute-modifier", "special-skill"],
    }
    assert components["16"][0]["attribute"] == "ARM"
    assert components["16"][0]["modifier"] == 1
    assert components["16"][1]["name"] == "Immunity"
    assert components["16"][1]["parameter"] == "ARM"
    assert components["17"][1]["parameter"] == "Enhanced"
    assert components["18"][0]["value"] == "6-4"
    assert components["19"][0]["value"] == "8-4"
    assert components["20"][0]["attribute"] == "PH"
    assert components["20"][0]["modifier"] == 3
    for row in projected:
        parts = row.get("outcome_components")
        if parts is None:
            continue
        assert " + ".join(part["text"] for part in parts) == row["result"]


def test_metachemistry_compound_parser_rejects_unreviewed_formats() -> None:
    rows = Database(ARMY_DB).list_metachemistry_results()
    for malformed in (
        "MOV: 6-4 + Mystery",
        "MOV: 6-4",
        "MOV: 6-4 + Super-Jump + Regeneration",
        "MOV: 6-4 + ",
        "Dogged + Immunity",
    ):
        modified = [
            {**row, "result": malformed} if row["roll"] == "18" else row
            for row in rows
        ]
        with pytest.raises(ValueError):
            project_metachemistry_rows(modified)
    # Partial fixture charts are supported; the full publication test
    # separately requires the exact five source-owned compound rolls.
    partial = [row for row in rows if row["roll"] not in {"16", "17", "18", "19", "20"}]
    assert project_metachemistry_rows(partial) == partial
    with pytest.raises(ValueError, match="Duplicate MetaChemistry compound"):
        project_metachemistry_rows([*rows, next(row for row in rows if row["roll"] == "20")])


def test_roll_range_audit_detects_gaps_overlaps_and_invalid_notation() -> None:
    assert _roll_positions([
        {"roll": "1-3"}, {"roll": "4"}, {"roll": "5-20"},
    ], "test") == list(range(1, 21))
    for rows in (
        [{"roll": "1-3"}, {"roll": "3-20"}],
        [{"roll": "1-3"}, {"roll": "5-20"}],
    ):
        assert _roll_positions(rows, "test") != list(range(1, 21))
    for invalid in ("0", "21", "10-9", "1;20", "special"):
        with pytest.raises(AssertionError):
            _roll_positions([{"roll": invalid}], "test")
