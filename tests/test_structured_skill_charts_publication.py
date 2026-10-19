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
from infinity_db.structured_chart_outcomes import project_booty_rows
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
                {key: value for key, value in row.items() if key != "conditional_outcomes"}
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
