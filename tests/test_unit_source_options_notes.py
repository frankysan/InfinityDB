"""Pinned source-to-Unit-API parity for Unit notes and composite options.

These tests inspect the tracked application database (not the ignored raw
archive). They do not replace the final Chromium acceptance or source audit.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(DATABASE, rules_database_path=RULES)


def _unit(app: Any, slug: str) -> dict[str, Any]:
    environment: dict[str, Any] = {}
    setup_testing_defaults(environment)
    environment.update(PATH_INFO=f"/api/units/{slug}", REQUEST_METHOD="GET")
    statuses: list[int] = []

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None,
    ) -> None:
        statuses.append(int(status.split()[0]))

    response = app(environment, start_response)
    try:
        body = b"".join(response)
    finally:
        closer = getattr(response, "close", None)
        if closer is not None:
            closer()
    assert statuses == [200], (slug, statuses)
    return json.loads(body)


def test_every_published_source_unit_note_is_visible_with_provenance(app: Any) -> None:
    with sqlite3.connect(f"{DATABASE.resolve().as_uri()}?mode=ro", uri=True) as db:
        source_notes = db.execute(
            "SELECT lu.slug, lu.representative_unit_id, n.source_unit_id, n.note "
            "FROM logical_unit_notes AS n "
            "JOIN logical_units AS lu ON lu.id = n.logical_unit_id "
            "ORDER BY lu.slug, n.source_unit_id"
        ).fetchall()

    assert len(source_notes) == 30  # Pinned publication, not generated fixture data.
    assert len({slug for slug, *_ in source_notes}) == 28
    by_slug: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for slug, representative, source_unit_id, note in source_notes:
        by_slug[str(slug)].append((int(representative), int(source_unit_id), str(note)))

    for slug, expected in by_slug.items():
        unit = _unit(app, slug)
        actual = {int(note["source_unit_id"]): note for note in unit["source_notes"]}
        assert len(actual) == len(expected), slug
        assert set(actual) == {source_id for _, source_id, _ in expected}, slug
        for representative, source_id, note in expected:
            published = actual[source_id]
            assert published["note"] == note, (slug, source_id)
            assert published["is_representative"] is (source_id == representative)
            assert published["source_name"].strip(), (slug, source_id)
            assert source_id in unit["source_ids"], (slug, source_id)
            assert all(
                isinstance(army["id"], int) and army["name"]
                for army in published["armies"]
            ), (slug, source_id)


def test_every_composite_option_preserves_source_cost_orders_and_includes(app: Any) -> None:
    with sqlite3.connect(f"{DATABASE.resolve().as_uri()}?mode=ro", uri=True) as db:
        source_options = db.execute(
            "SELECT lu.slug, u.unit_id, u.option_id, u.name, u.points, "
            "u.swc, u.minis FROM unit_options AS u "
            "JOIN logical_unit_sources AS src ON src.source_unit_id = u.unit_id "
            "JOIN logical_units AS lu ON lu.id = src.logical_unit_id "
            "ORDER BY lu.slug, u.unit_id, u.option_id"
        ).fetchall()
        source_orders = db.execute(
            "SELECT unit_id, option_id, order_type, list_count, total_count "
            "FROM unit_option_orders ORDER BY unit_id, option_id, position"
        ).fetchall()
        source_includes = db.execute(
            "SELECT unit_id, option_id, target_army_id, target_loadout_payload_id, quantity "
            "FROM unit_option_include_targets "
            "ORDER BY unit_id, option_id, target_army_id, position"
        ).fetchall()

    assert len(source_options) == 18
    assert len({slug for slug, *_ in source_options}) == 7
    orders: dict[tuple[int, int], list[tuple[str, Any, Any]]] = defaultdict(list)
    for source_id, option_id, order_type, list_count, total_count in source_orders:
        orders[(source_id, option_id)].append((order_type, list_count, total_count))
    includes: dict[tuple[int, int], set[tuple[int, int, int]]] = defaultdict(set)
    for source_id, option_id, army_id, target, quantity in source_includes:
        includes[(source_id, option_id)].add((army_id, target, quantity))

    by_slug: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for row in source_options:
        by_slug[str(row[0])].append(tuple(row[1:]))

    for slug, expected in by_slug.items():
        unit = _unit(app, slug)
        published = defaultdict(list)
        for army in unit["armies"]:
            for option in army.get("composite_options", []):
                published[(option["source_unit_id"], option["option_id"])].append(
                    (int(army["id"]), option)
                )
        assert set(published) == {(row[0], row[1]) for row in expected}, slug
        for source_id, option_id, name, points, swc, minis in expected:
            key = (source_id, option_id)
            assert published[key], (slug, key)
            for army_id, option in published[key]:
                assert (option["name"], option["points"], option["swc"], option["minis"]) == (
                    name, points, swc, minis
                ), (slug, key)
                assert [
                    (item["type"], item["list"], item["total"])
                    for item in option["orders"]
                ] == orders[key], (slug, key)
                actual_includes = {
                    (
                        int(item["army_id"]), int(item["loadout_payload_id"]),
                        int(item["quantity"]),
                    )
                    for item in option["includes"]
                }
                expected_includes = {
                    item for item in includes[key] if item[0] == army_id
                }
                assert actual_includes == expected_includes, (slug, key, army_id)
                assert len(option["order_presentations"]) == len(orders[key])
