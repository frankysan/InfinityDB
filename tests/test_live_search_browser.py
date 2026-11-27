"""Live navigation suggestions preserve canonical search and page navigation."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import route_browser_page
from tools.testing.browser_test_metrics import launch_timed_chromium

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-live-search.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app_from_database_set(ROOT / "data/generated")


@pytest.fixture(scope="module")
def chrome(pooled_chromium_browser: Any) -> Iterator[Any]:
    if pooled_chromium_browser is not None:
        yield pooled_chromium_browser
        return
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            browser = launch_timed_chromium(driver, "live-search")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        try:
            yield browser
        finally:
            browser.close()


@pytest.mark.parametrize("width", (1440, 768, 390, 320))
def test_live_search_navigation(app: Any, chrome: Any, width: int) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        toggle = page.locator(".global-search-toggle")
        if toggle.is_visible():
            toggle.click()
        query = page.locator("#global-search-query")
        panel = page.locator("#global-search-panel")
        options = panel.get_by_role("option")
        query.fill("m")
        assert not panel.is_visible()
        query.fill("mim")
        panel.wait_for(state="visible")
        assert query.get_attribute("aria-expanded") == "true"
        assert 1 < options.count() <= 9
        assert page.url == f"{ORIGIN}/rules"
        assert page.evaluate(
            """() => {
                const r = document.querySelector('#global-search-panel').getBoundingClientRect();
                return r.left >= 0 && r.right <= innerWidth + 1
                    && document.documentElement.scrollWidth <= innerWidth + 1;
            }"""
        )
        query.press("ArrowDown")
        assert query.get_attribute("aria-activedescendant") == options.first.get_attribute("id")
        query.press("Escape")
        assert not panel.is_visible()
        assert query.get_attribute("aria-expanded") == "false"
        query.fill("Saturation")
        result = panel.locator('a[href="/rules/saturation"]')
        result.wait_for(state="visible")
        result.click()
        page.wait_for_url(f"{ORIGIN}/rules/saturation")
        page.wait_for_function("() => document.activeElement === document.querySelector('main#main')")
        assert not panel.is_visible()
        if toggle.is_visible():
            toggle.click()
        query.fill("Dragões")
        panel.wait_for(state="visible")
        assert panel.locator(".global-search-option-domain").count() > 0
        query.press("Enter")
        page.wait_for_url(lambda url: url.startswith(f"{ORIGIN}/search?s=v1.s."))
        assert page.locator("#search-query").input_value() == "Dragões"
        assert not errors
    finally:
        page.close()


def test_live_search_latest_input_and_keyboard(app: Any, chrome: Any) -> None:
    page = chrome.new_page(viewport={"width": 1440, "height": 900})
    route_browser_page(page, app, ORIGIN)
    try:
        page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        query = page.locator("#global-search-query")
        panel = page.locator("#global-search-panel")
        query.fill("mimetism")
        query.fill("Saturation")
        panel.locator('a[href="/rules/saturation"]').wait_for(state="visible")
        assert panel.locator('a[href="/skills/mimetism"]').count() == 0
        query.fill("")
        assert not panel.is_visible()
        query.fill("no-such-result-987654")
        panel.get_by_text("No matching suggestions").wait_for(state="visible")
        assert panel.get_by_role("option").count() == 1
        query.fill("Saturation")
        panel.locator('a[href="/rules/saturation"]').wait_for(state="visible")
        query.press("ArrowDown")
        query.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/saturation")
        assert not panel.is_visible()
    finally:
        page.close()
