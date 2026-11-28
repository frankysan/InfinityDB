"""Source-native official Army deep links and their Unit-detail integration."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from infinity_db.database import Database
from infinity_db.database.official_army_links import official_army_links

BASE = "https://infinityuniverse.com/army/infinity"
ROOT = Path(__file__).resolve().parents[1]


def test_source_routes_require_exact_memberships_and_safe_unique_slugs() -> None:
    factions = {
        1: {"name": "First Army", "slug": "official-first"},
        2: {"name": "Second Army", "slug": "official-second"},
        3: {"name": "Section", "slug": "section"},
        4: {"name": "Broken Army", "slug": "../unsafe"},
        5: {"name": "Missing Section", "slug": "missing-section"},
        6: {"name": "Duplicate A", "slug": "duplicate"},
        7: {"name": "Duplicate B", "slug": "duplicate"},
    }
    def resume(*rows: tuple[int, str]) -> str:
        return json.dumps([{"id": identifier, "slug": slug} for identifier, slug in rows])

    with closing(sqlite3.connect(":memory:")) as db:
        db.row_factory = sqlite3.Row
        db.executescript(
            "CREATE TABLE army_lists(id,kind,reinforcement_id,resume);"
            "CREATE TABLE army_units(army_id,unit_id);"
        )
        db.executemany("INSERT INTO army_lists VALUES(?,?,?,?)", [
            (1, "vanilla", 3, resume(
                (17, "first-name"), (99, "nonmember"), (18, "ambiguous"),
                (19, "ambiguous"), (20, "collision"), (21, "../bad"),
            )),
            (2, "sectorial", 3, resume((17, "second-name"))),
            (3, "reinforcement", None, resume((22, "section-unit"), (23, "collision"))),
            (4, "vanilla", None, resume((17, "first-name"))),
            (5, "vanilla", 999, resume((17, "first-name"))),
            (6, "vanilla", None, resume((17, "first-name"))),
            (7, "vanilla", None, resume((17, "first-name"))),
        ])
        db.executemany("INSERT INTO army_units VALUES(?,?)", [
            (1, 17), (1, 18), (1, 19), (1, 20), (1, 21), (1, 24),
            (2, 17), (3, 22), (3, 23), (4, 17), (5, 17), (6, 17), (7, 17),
        ])
        result = official_army_links(db, factions)

    assert result == {
        (1, 17): [{"army_name": "First Army", "unit_name": "first-name",
                   "href": BASE + "/official-first/first-name"}],
        (2, 17): [{"army_name": "Second Army", "unit_name": "second-name",
                   "href": BASE + "/official-second/second-name"}],
        (3, 22): [
            {"army_name": "First Army", "unit_name": "section-unit",
             "href": BASE + "/official-first/section-unit"},
            {"army_name": "Second Army", "unit_name": "section-unit",
             "href": BASE + "/official-second/section-unit"},
        ],
        (3, 23): [{"army_name": "Second Army", "unit_name": "collision",
                   "href": BASE + "/official-second/collision"}],
    }


def test_published_snapshot_exposes_exact_zeros_memberships() -> None:
    database = Database(ROOT / "data/generated/army.db")
    unit = database.get_unit(401)
    assert unit is not None
    links = {
        link["href"] for army in unit["armies"] for link in army["official_army_links"]
    }
    assert BASE + "/nomads/zeros" in links
    assert BASE + "/bakunin/zeros" in links


def test_published_snapshot_exposes_reinforcement_parent_route() -> None:
    database = Database(ROOT / "data/generated/army.db")
    unit = database.get_unit("prowlers")
    assert unit is not None
    links = {
        link["href"] for army in unit["armies"]
        if "reinforcement" in army["availability_flags"]
        for link in army["official_army_links"]
    }
    assert BASE + "/bakunin/reinf-prowlers" in links
    assert BASE + "/nomads/reinf-prowlers" in links


def test_unit_page_renders_contextual_official_links() -> None:
    from infinity_db.web import create_app
    from tools.browser_wsgi_transport import route_browser_page

    api = pytest.importorskip("playwright.sync_api")
    app = create_app(ROOT / "data/generated/army.db")
    with api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        try:
            for width in (1280, 390):
                page = browser.new_page(viewport={"width": width, "height": 900})
                route_browser_page(page, app, "http://infinitydb-browser.test")
                page.goto("http://infinitydb-browser.test/units/401?army_id=503")
                link = page.locator(
                    'details.army-profile[open] a[href="' + BASE + '/bakunin/zeros"]'
                )
                link.wait_for(state="visible", timeout=30000)
                assert link.get_attribute("target") == "_blank"
                assert link.get_attribute("rel") == "noopener noreferrer"
                assert page.locator('a[href="' + BASE + '/nomads/zeros"]').count() == 1
                assert link.evaluate(
                    """element => element.getBoundingClientRect().right <= innerWidth"""
                )
                page.close()
        finally:
            browser.close()
