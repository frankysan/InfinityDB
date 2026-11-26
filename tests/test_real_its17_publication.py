"""Real ITS 17/18 runtime selection, identity isolation, and presentation readiness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.database_set import COMPLETE_RUNTIME_FILES, validate_database_set
from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data/generated"


@pytest.fixture(scope="module")
def published_app():
    return create_app_from_database_set(GENERATED)


def get(app, url: str):
    status, headers, body = wsgi_response(app, "https://seasons.test" + url)
    return status, dict(headers), body


def get_json(app, url: str) -> dict:
    status, _, body = get(app, url)
    assert status == 200, (status, url, body[:500])
    return json.loads(body)


def test_both_seasons_are_required_and_registered(published_app) -> None:
    report = validate_database_set(GENERATED, require_complete=True)
    assert report["layout"] == "v17-four-file"
    assert set(report["sha256"]) == COMPLETE_RUNTIME_FILES == {
        "army.db", "rules_n5.db", "its_17.db", "its_18.db",
    }
    assert {key: value["revision"] for key, value in report["seasons"].items()} == {
        "its-17": "0.2",
        "its-18": "2026.09.11",
    }
    assert report["seasons"]["its-17"]["sharedScenarioLibrary"]["id"] == "its17-scenarios"


def test_both_season_catalogs_and_revisions_fail_closed(published_app) -> None:
    app = published_app
    core = get_json(app, "/api/scenarios")
    assert len(core["items"]) == 4
    assert {
        (x["id"], x["scenario_count"]) for x in core["collections"]
    } >= {("its-17", 16), ("its-18", 20)}
    for season, revision, count in (("its-17", "0.2", 16), ("its-18", "2026.09.11", 20)):
        result = get_json(app, f"/api/scenarios?collection={season}")
        assert len(result["items"]) == count
        assert all(item["publication"]["revision"] == revision for item in result["items"])
        assert get_json(app, f"/api/scenarios?collection={season}&revision=legacy")["items"] == []
        stale = f"/api/scenarios/evacuation?army_points=300&collection={season}&revision=legacy"
        assert get(app, stale)[0] == 404


def test_same_named_scenarios_render_independently(published_app) -> None:
    app = published_app
    details = {}
    for season, revision in (("its-17", "0.2"), ("its-18", "2026.09.11")):
        url = f"/api/scenarios/outbreak?collection={season}&army_points=300"
        item = get_json(app, url)
        assert item["publication"]["collection_id"] == season
        assert item["publication"]["revision"] == revision
        details[season] = item
        status, headers, svg = get(
            app, f"/api/scenarios/outbreak/map.svg?collection={season}&army_points=300",
        )
        assert status == 200 and "image/svg+xml" in headers["Content-Type"]
        assert b"<svg" in svg
    assert details["its-17"]["objectives"] != details["its-18"]["objectives"]
    assert get(app, "/api/scenarios/outbreak?army_points=300")[0] == 404


def test_historical_casevac_routes_are_distinct(published_app) -> None:
    app = published_app
    skills = {row["slug"]: row for row in get_json(app, "/api/skills")["items"]}
    assert "casevac" in skills and "its-17-casevac" not in skills
    assert {use["collection"] for use in skills["casevac"]["seasons"]} == {"its-17", "its-18"}
    for slug, season, declaration in (
        ("its-18-casevac", "its-18", "short-skill"),
        ("its-17-casevac", "its-17", "short-movement-skill"),
    ):
        detail = get_json(app, f"/api/skills/{slug}")
        assert detail["rules"][0]["scope"]["seasons"] == [season]
        assert detail["categories"][0]["id"] == declaration
    states = {row["slug"]: row for row in get_json(app, "/api/states")["items"]}
    for slug, season in (("casevac", "its-18"), ("its-17-casevac", "its-17")):
        assert states[slug]["season"]["collection"] == season
        detail = get_json(app, f"/api/states/{slug}")
        assert detail["rules"][0]["scope"]["seasons"] == [season]


def test_real_scenario_skill_identities_cover_all_scoped_actions(published_app) -> None:
    app = published_app
    skills = [
        item for item in get_json(app, "/api/skills")["items"]
        if item["category"] == "Scenario-specific Skills"
    ]
    assert len(skills) == 26
    routes = [slug for item in skills for slug in item.get("aliases", [item["slug"]])]
    assert len(routes) == len(set(routes)) == 55
    assert sum(slug.startswith("its-17-") for slug in routes) == 22
    assert sum(slug.startswith("its-18-") for slug in routes) == 31
    canonical = get_json(app, "/api/skills/scenario-activate-antenna")
    assert len(canonical["aliases"]) == 8
    assert len(canonical["scenarios"]) == 7
    assert all(
        "WIP-3" not in clause
        for clause in canonical["rules"][0]["facts"].get("effects", [])
    )
    for item in skills:
        for slug in item.get("aliases", []):
            exact = get_json(app, f"/api/skills/{slug}")
            assert exact["canonical_slug"] == item["slug"]
            assert exact["scenario"]["collection"] in {
                context["collection"] for context in item["scenarios"]
            }
            assert exact["rules"][0]["citations"]


@pytest.mark.parametrize("width", [1280, 390])
def test_consolidated_scenario_skill_browser(published_app, width) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        page = browser.new_page(viewport={"width": width, "height": 900})
        origin = "http://scenario-skills.test"
        route_browser_page(page, published_app, origin)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(origin + "/skills/scenario-activate-console", wait_until="domcontentloaded")
            contexts = page.locator(".scenario-skill-contexts")
            contexts.wait_for(state="visible")
            assert contexts.locator("a").count() == 4
            assert "ITS 17" in contexts.inner_text() and "ITS 18" in contexts.inner_text()
            variants = page.locator(".scenario-skill-variants")
            assert variants.is_visible()
            assert "Hardlock" in variants.inner_text() and "B-Pong" in variants.inner_text()
            assert "Common mechanics" in page.locator("#skill-content").inner_text()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            page.goto(
                origin + "/skills/its-18-hardlock-activate-console",
                wait_until="domcontentloaded",
            )
            page.locator('a[href="/skills/scenario-activate-console"]').wait_for(state="visible")
            assert page.locator(".scenario-skill-variants").count() == 0
            assert not errors, errors
        finally:
            browser.close()


def test_marker_source_follows_selected_season(published_app) -> None:
    for season, expected_source, expected_page in (
        ("its-17", "its-season-17-v0.2-en-pdf", 13),
        ("its-18", "its-season-18-en-pdf", 18),
    ):
        item = get_json(
            published_app, f"/api/scenarios/uplink-center?collection={season}&army_points=300",
        )
        markers = item["placement"]["marker_dimensions"]
        source = next(x["citation"] for x in markers if x["citation"] is not None)
        assert source["source_id"] == expected_source
        assert source["page"] == expected_page
