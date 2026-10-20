"""Permanent source-to-API/template checks for non-Skill Army source entries.

The separate local Chromium acceptance is historical evidence, not run by CI.
These checks use the tracked published Army and rules databases only.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"

# Original Army Skill IDs deliberately published in other player-facing buckets.
SOURCE_BUCKETS = {
    254: ("gizmokit", "equipment"),
    273: ("medikit", "equipment"),
    266: ("bangbomb", "equipment"),
    258: ("regular", "training"),
    282: ("infinity-team-ops", "source_markers"),
    280: ("bts-3", "attribute_overrides"),
}

REPRESENTATIVE_UNITS = (
    ("dragoes", 254, "/equipment/gizmokit"),
    ("minutemen", 273, "/equipment/medikit"),
    ("racerbots", 266, "/equipment/bangbomb"),
    ("miyamoto-mushashi", 258, None),
    ("raoul-spector-mercenary-operative", 258, None),
    ("tohaa-team-ops", 282, None),
    ("corregidor-alguaciles", 280, None),
)


@pytest.fixture(scope="module")
def application() -> Any:
    assert APPLICATION_DB.is_file()
    assert RULES_DB.is_file()
    return create_app(APPLICATION_DB, rules_database_path=RULES_DB)


def _get(app: Any, path: str) -> tuple[int, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[int] = []

    def start_response(status: str, headers: list[tuple[str, str]], exc_info: Any = None) -> None:
        statuses.append(int(status.split()[0]))

    response = app(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1
    return statuses[0], body


def _source_pairs() -> list[tuple[str, int]]:
    # Cross-check all directly used source identities, not just a shortlist
    # of representative Unit pages.
    with sqlite3.connect(f"{APPLICATION_DB.resolve().as_uri()}?mode=ro", uri=True) as connection:
        return [
            (str(slug), int(source_id))
            for slug, source_id in connection.execute(
                """
                SELECT DISTINCT logical.slug, source.id
                FROM logical_units AS logical
                JOIN (
                    SELECT p.logical_unit_id, s.item_id
                    FROM profile_payloads AS p
                    JOIN profile_payload_skills AS s ON s.profile_payload_id = p.id
                    UNION ALL
                    SELECT p.logical_unit_id, s.item_id
                    FROM loadout_payloads AS p
                    JOIN loadout_payload_skills AS s ON s.loadout_payload_id = p.id
                ) AS used ON used.logical_unit_id = logical.id
                JOIN skills AS source ON source.id = used.item_id
                WHERE source.id IN (254, 273, 266, 258, 282, 280)
                ORDER BY logical.slug, source.id
                """
            )
        ]


def _unit_items(unit: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for general in unit["general_profiles"]:
        for bucket, items in general["shared_items"].items():
            found.extend((bucket, item) for item in items)
    for army in unit["armies"]:
        for kind in ("profiles", "loadouts"):
            for context in army[kind]:
                for bucket, items in context.get("specific_items", {}).items():
                    found.extend((bucket, item) for item in items)
    return found


def test_every_published_non_skill_army_source_has_a_correct_bucket(application: Any) -> None:
    pairs = _source_pairs()
    assert len(pairs) == 72  # Pinned published snapshot, not browser pass count.
    assert {source_id for _, source_id in pairs} == set(SOURCE_BUCKETS)
    for slug, source_id in pairs:
        source_slug, expected_bucket = SOURCE_BUCKETS[source_id]
        status, body = _get(application, f"/api/units/{slug}")
        assert status == 200, (slug, status)
        items = _unit_items(json.loads(body))
        matches = [(bucket, item) for bucket, item in items if item.get("slug") == source_slug]
        assert matches, (slug, source_slug)
        assert {bucket for bucket, _ in matches} == {expected_bucket}, (slug, source_slug)
        assert not any(bucket == "skills" for bucket, _ in matches)


@pytest.mark.parametrize(("slug", "source_id", "destination"), REPRESENTATIVE_UNITS)
def test_non_skill_sources_have_normal_unit_bootstrap_and_detail_api(
    application: Any, slug: str, source_id: int, destination: str | None,
) -> None:
    # Unit pages are client-rendered: the initial HTML provides the
    # bootstrap, not the .general-profile DOM nodes (Chromium checks those).
    status, body = _get(application, f"/units/{slug}")
    assert status == 200, slug
    html = body.decode("utf-8")
    assert 'id="unit-content"' in html, slug
    assert "/static/unit.js" in html, slug

    status, payload = _get(application, f"/api/units/{slug}")
    assert status == 200, slug
    unit = json.loads(payload)
    assert unit["general_profiles"], slug
    source_slug, expected_bucket = SOURCE_BUCKETS[source_id]
    assert any(
        bucket == expected_bucket and item.get("slug") == source_slug
        for bucket, item in _unit_items(unit)
    ), (slug, source_slug)
    if destination:
        assert _get(application, destination)[0] == 200
