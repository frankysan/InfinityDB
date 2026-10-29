"""Pin the source-defined Spec-Ops/Team-Ops choice chart inventory.

These are immutable Army source options, not a player's selected upgrades.
The current application database preserves them with per-source-unit provenance
and ordinary Unit detail APIs publish them as read-only source choices.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
ARMY = ROOT / "data/generated/infinity.db"
SOURCE = ROOT / "data/raw/JSON 20260929-114335.zip"
RULES = ROOT / "data/generated/rules.db"
SPEC_OPS_IDS = {1908, *range(1912, 1926)}
TEAM_OPS_IDS = {1909, *range(1926, 1940)}


def _unit_api(app: Any, slug: str) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=f"/api/units/{slug}", REQUEST_METHOD="GET")
    statuses: list[str] = []
    response = app(
        environ, lambda status, headers, exc_info=None: statuses.append(status)
    )
    try:
        body = b"".join(response)
    finally:
        closer = getattr(response, "close", None)
        if closer is not None:
            closer()
    assert statuses == ["200 OK"]
    return json.loads(body)


def test_spec_ops_charts_are_source_attributed_and_not_flattened() -> None:
    assert len(SPEC_OPS_IDS) == len(TEAM_OPS_IDS) == 15

    with sqlite3.connect(ARMY) as connection:
        rows = connection.execute(
            "SELECT u.id, u.spectables, s.spectables "
            "FROM units AS u "
            "JOIN logical_unit_spectables AS s ON s.source_unit_id = u.id "
            "WHERE u.id BETWEEN 1908 AND 1939 ORDER BY u.id"
        ).fetchall()

    assert {row[0] for row in rows} == SPEC_OPS_IDS | TEAM_OPS_IDS
    saw_compound_option = False
    for source_id, raw_source, raw_projection in rows:
        assert json.loads(raw_source) == json.loads(raw_projection)
        charts = json.loads(raw_projection)
        assert set(charts) == {"table", "specball"}
        assert len(charts["table"]["items"]) == (
            8 if source_id in SPEC_OPS_IDS else 10
        )
        assert len(charts["specball"]["items"]) == 4
        for chart in charts.values():
            for item in chart["items"]:
                attrs = item["attrs"]
                assert isinstance(attrs, list) and attrs
                assert all(attr["type"] in {"stat", "weapon", "equip", "skill"} for attr in attrs)
                saw_compound_option |= len(attrs) > 1
    assert saw_compound_option


def test_every_source_chart_option_reaches_public_unit_api_in_order() -> None:
    app = create_app(ARMY, rules_database_path=RULES)
    with sqlite3.connect(ARMY) as connection:
        rows = connection.execute(
            "SELECT lu.slug, s.source_unit_id, s.spectables "
            "FROM logical_unit_spectables AS s "
            "JOIN logical_units AS lu ON lu.id = s.logical_unit_id "
            "ORDER BY lu.slug, s.source_unit_id"
        ).fetchall()
    assert len(rows) == 30
    cached: dict[str, dict[str, Any]] = {}
    for slug, source_id, original in rows:
        if slug not in cached:
            cached[slug] = _unit_api(app, slug)
        unit = cached[slug]
        chart = next(
            item for item in unit["source_charts"]
            if item["source_unit_id"] == source_id
        )
        assert chart["source_versions"]
        for kind, raw_chart in json.loads(original).items():
            actual = chart["charts"][kind]["items"]
            assert len(actual) == len(raw_chart["items"])
            for original_item, published_item in zip(
                raw_chart["items"], actual, strict=True
            ):
                assert [
                    {
                        key: value for key, value in attribute.items()
                        if key not in ("name", "href", "extras")
                    }
                    for attribute in published_item["attributes"]
                ] == original_item["attrs"]


def test_source_choices_are_exposed_on_unit_api_without_player_selections() -> None:
    app = create_app(ARMY, rules_database_path=RULES)
    for slug, source_id, table_size in (
        ("indigo-spec-ops", 1912, 8),
        ("indigo-team-ops", 1926, 10),
    ):
        unit = _unit_api(app, slug)
        charts = [item for item in unit["source_charts"]
                  if item["source_unit_id"] == source_id]
        assert len(charts) == 1
        entry = charts[0]
        assert entry["source_name"]
        assert entry["source_versions"] and entry["source_versions"][0]["version"]
        assert len(entry["charts"]["table"]["items"]) == table_size
        assert len(entry["charts"]["specball"]["items"]) == 4
        all_attributes = [
            attr for chart in entry["charts"].values()
            for choice in chart["items"] for attr in choice["attributes"]
        ]
        assert any(attr["name"] and attr["href"] for attr in all_attributes)
        assert any(attr["type"] == "stat" and attr.get("q") is not None
                   for attr in all_attributes)
        assert any(len(choice["attributes"]) > 1
                   for choice in entry["charts"]["table"]["items"])
        assert not any("selected" in chart for chart in entry["charts"].values())

    ordinary = _unit_api(app, "pathfinder-dronbot")
    assert ordinary["source_charts"] == []


@pytest.mark.skipif(not SOURCE.exists(), reason="Pinned Army ZIP unavailable")
@pytest.mark.parametrize(
    ("source_member", "spec_slug", "spec_id", "team_slug", "team_id"),
    (
        ("101-panoceania.json", "indigo-spec-ops", 1912, "indigo-team-ops", 1926),
        (
            "103-military-orders.json",
            "confessor-spec-ops", 1913, "confessor-team-ops", 1927,
        ),
        ("201-yu-jing.json", "gu-feng-spec-ops", 1914, "yu-jing-team-ops", 1928),
    ),
)
def test_army_02_to_04_source_pairs_are_published_with_own_chart_context(
    source_member: str,
    spec_slug: str,
    spec_id: int,
    team_slug: str,
    team_id: int,
) -> None:
    """Current-source pair identities and exact option context, not a historical diff."""
    with zipfile.ZipFile(SOURCE) as archive:
        member = json.loads(archive.read(source_member))
    source_units = {unit["id"]: unit for unit in member["units"]}
    app = create_app(ARMY, rules_database_path=RULES)
    for slug, source_id, choices in (
        (spec_slug, spec_id, 8),
        (team_slug, team_id, 10),
    ):
        source_unit = source_units[source_id]
        assert source_unit["slug"] == slug
        assert len(source_unit["spectables"]["table"]["items"]) == choices
        assert len(source_unit["spectables"]["specball"]["items"]) == 4
        published = _unit_api(app, slug)
        assert source_id in published["source_ids"]
        source_chart = next(
            chart for chart in published["source_charts"]
            if chart["source_unit_id"] == source_id
        )
        assert source_chart["source_name"] == source_unit["name"]
        assert {"version": member["version"], "source_file": source_member} in (
            source_chart["source_versions"]
        )
        for chart_kind, source_table in source_unit["spectables"].items():
            actual = source_chart["charts"][chart_kind]["items"]
            assert len(actual) == len(source_table["items"])
            for source_choice, public_choice in zip(
                source_table["items"], actual, strict=True,
            ):
                assert [
                    {
                        key: value for key, value in attr.items()
                        if key not in ("name", "href", "extras")
                    }
                    for attr in public_choice["attributes"]
                ] == source_choice["attrs"]
        assert "selected" not in source_chart


@pytest.mark.skipif(not SOURCE.exists(), reason="Pinned Army ZIP unavailable")
def test_pinned_army_spec_ops_charts_match_materialized_source_payloads() -> None:
    """Cross-check the exact September 29 snapshot without altering source data."""
    by_source_id: dict[int, set[str]] = {}
    with zipfile.ZipFile(SOURCE) as archive:
        for name in archive.namelist():
            if name == "metadata.json" or not name.endswith(".json"):
                continue
            document = json.loads(archive.read(name))
            for unit in document["units"]:
                if "spectables" not in unit:
                    continue
                by_source_id.setdefault(unit["id"], set()).add(
                    json.dumps(unit["spectables"], sort_keys=True)
                )

    assert set(by_source_id) == SPEC_OPS_IDS | TEAM_OPS_IDS
    assert all(len(payloads) == 1 for payloads in by_source_id.values())
    with sqlite3.connect(ARMY) as connection:
        current = {
            source_id: json.dumps(json.loads(raw), sort_keys=True)
            for source_id, raw in connection.execute(
                "SELECT id, spectables FROM units "
                "WHERE spectables IS NOT NULL AND spectables != ''"
            )
        }
    assert current == {
        source_id: next(iter(payloads))
        for source_id, payloads in by_source_id.items()
    }
