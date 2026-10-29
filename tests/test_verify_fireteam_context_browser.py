"""Chromium acceptance for chart uncertainty, annotations and parent context."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.database import Database
from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-fireteam-context.test"
VIEWPORTS = ((1440, "light"), (390, "dark"), (320, "light"))


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


@pytest.fixture(scope="module")
def chrome() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield browser
        finally:
            browser.close()


def _chart(app: Any, army: str | int) -> dict[str, Any]:
    status, _, body = wsgi_response(app, f"{ORIGIN}/api/fireteams?army_id={army}")
    assert status == 200
    return json.loads(body)


@pytest.mark.parametrize("width,theme", VIEWPORTS)
@pytest.mark.parametrize("army_id", (302, 499, 502, 601, 604, 799, 899, 902, 999))
def test_pinned_uncertainty_and_original_annotations_are_visible(
    app: Any, chrome: Any, army_id: int, width: int, theme: str,
) -> None:
    chart = _chart(app, army_id)
    page = chrome.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    route_browser_page(page, app, ORIGIN)
    page.add_init_script(
        "sessionStorage.setItem('infinity-db-fireteams-include-wildcards', 'false')"
    )
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(
            f"{ORIGIN}/fireteams?army={chart['army']['public_slug']}",
            wait_until="domcontentloaded",
        )
        page.locator("#fireteam-content").wait_for(state="visible", timeout=30000)
        expected_issues = set()
        for team in chart["teams"]:
            card = page.locator(".fireteam-card").filter(
                has=page.get_by_role("heading", name=team["name"].strip(), exact=True),
            )
            assert card.count() == 1
            rows = card.locator("tbody tr")
            assert rows.count() == len(team["members"])
            for index, member in enumerate(team["members"]):
                row = rows.nth(index)
                annotations = row.locator(".fireteam-member-annotation")
                if member["comment"]:
                    assert annotations.text_content() == f"Chart note: {member['comment']}"
                    assert annotations.is_visible()
                else:
                    assert annotations.count() == 0
                issues = row.locator(".fireteam-member-verification")
                texts = [f"Needs verification: {issue['message']}"
                         for issue in member["reference_issues"]]
                assert issues.all_text_contents() == texts
                expected_issues.update(texts)
                assert all(item.is_visible() for item in issues.all())
                if member["reference_issues"]:
                    assert row.locator(".fireteam-member-fto-summary").count() == 0
                if member["unit"] is None:
                    assert row.locator("th a").count() == 0
        # Exercise the actual setting: injected Wildcards must retain their notices.
        toggle = page.locator("#fireteams-include-wildcards-toggle")
        if not toggle.is_visible():
            page.locator('button[aria-controls="settings-menu"]').click()
        toggle.check()
        assert set(page.locator(".fireteam-member-verification").all_text_contents()) == (
            expected_issues
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors, errors
    finally:
        page.close()


def _reinforcement_slugs() -> list[str]:
    database = Database(ROOT / "data/generated/infinity.db")
    return [army["slug"] for army in database.list_fireteam_armies()
            if army["role"] == "reinforcement"]


@pytest.mark.parametrize("width,theme", VIEWPORTS)
@pytest.mark.parametrize("army_slug", _reinforcement_slugs())
def test_reinforcement_parent_limits_links_and_keyboard_navigation(
    app: Any, chrome: Any, army_slug: str, width: int, theme: str,
) -> None:
    chart = _chart(app, army_slug)
    page = chrome.new_page(viewport={"width": width, "height": 900}, color_scheme=theme)
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/fireteams?army={army_slug}", wait_until="domcontentloaded")
        section = page.locator("#fireteam-parent-charts")
        section.wait_for(state="visible", timeout=30000)
        parents = section.locator("li")
        assert parents.count() == len(chart["parent_charts"])
        for index, parent in enumerate(chart["parent_charts"]):
            row = parents.nth(index)
            link = row.locator("a")
            if parent["selectable"]:
                assert link.text_content() == parent["army"]["name"]
                assert "/fireteams?s=" in link.get_attribute("href")
            else:
                assert link.count() == 0
                assert parent["army"]["name"] in row.inner_text()
            labels = []
            for limit in parent["limits"]:
                suffix = ("unavailable" if limit["limit_kind"] == "unavailable" else
                          "unlimited" if limit["limit_kind"] == "unlimited" else
                          f"max {limit['max_count']}")
                labels.append(f"{limit['type']}: {suffix}")
            assert row.locator(".skill-category-badge").all_text_contents() == labels
            assert all(item.is_visible() for item in row.locator(".skill-category-badge").all())
            if not labels:
                assert ("No Fireteam type limits are listed." if parent["source"] else
                        "Chart limits unavailable.") in row.inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        # Follow a real parent chart, then return without leaking parent context.
        first = next(parent for parent in chart["parent_charts"] if parent["selectable"])
        link = parents.locator("a").first
        link.focus()
        link.press("Enter")
        page.wait_for_function(
            "name => document.querySelector('#fireteam-chart-name')?.textContent === name",
            arg=first["army"]["name"], timeout=30000,
        )
        assert page.locator("#fireteam-parent-charts").is_hidden()
        page.go_back(wait_until="domcontentloaded")
        section.wait_for(state="visible", timeout=30000)
        assert section.locator("li").count() == len(chart["parent_charts"])
        assert not errors, errors
    finally:
        page.close()


def test_missing_parent_chart_does_not_invent_zero_limits_or_a_link(app: Any, chrome: Any) -> None:
    chart = _chart(app, "ank-program")
    chart["parent_charts"] = [{
        "army": {"id": 701, "name": "ALEPH", "public_slug": "aleph"},
        "source": None, "limits": [],
    }]
    page = chrome.new_page(viewport={"width": 320, "height": 900})
    route_browser_page(page, app, ORIGIN)
    page.route("**/api/fireteams?army_id=*", lambda route: route.fulfill(json=chart))
    try:
        page.goto(f"{ORIGIN}/fireteams?army=ank-program", wait_until="domcontentloaded")
        section = page.locator("#fireteam-parent-charts")
        section.wait_for(state="visible", timeout=30000)
        assert "Chart limits unavailable." in section.inner_text()
        assert section.locator("li a,.skill-category-badge").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    finally:
        page.close()
