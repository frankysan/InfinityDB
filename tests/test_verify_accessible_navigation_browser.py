"""Accessibility-facing Chromium contracts for soft navigation and the shared notice.

These assertions check browser focus/DOM semantics, not human screen-reader sign-off.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_test_metrics import launch_timed_chromium
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-accessible-navigation.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


@pytest.fixture(scope="module")
def chrome(pooled_chromium_browser: Any) -> Iterator[Any]:
    if pooled_chromium_browser is not None:
        yield pooled_chromium_browser
        return
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            browser = launch_timed_chromium(driver, "accessible-navigation")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield browser
        finally:
            browser.close()


def assert_soft_navigation_handoff(page: Any, pathname: str) -> None:
    # Soft navigation can retain the Units page’s shareable ?s= state.
    page.wait_for_function(
        "expected => window.location.pathname === expected", arg=pathname,
    )
    page.wait_for_function(
        """() => {
          const main = document.querySelector('main#main');
          const status = document.querySelector('#page-navigation-status');
          return document.activeElement === main
            && status?.textContent === `Loaded ${document.title}`;
        }"""
    )
    status = page.locator("#page-navigation-status")
    assert status.get_attribute("role") == "status"
    assert status.get_attribute("aria-live") == "polite"
    assert status.get_attribute("aria-atomic") == "true"
    assert page.locator("main#main").get_attribute("tabindex") == "-1"


@pytest.mark.parametrize("width", [1440, 390])
def test_soft_navigation_focuses_main_and_announces_route(
    app: Any, chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/", wait_until="domcontentloaded")
        assert page.locator("#page-navigation-status").inner_text() == ""

        # First activate an ordinary link inside the main content.
        page.locator("main a[href='/units']").first.press("Enter")
        assert_soft_navigation_handoff(page, "/units")
        page.wait_for_function(
            "() => document.querySelector('#skill-filter')?.disabled === false"
        )
        page.evaluate("() => window.scrollTo(0, 160)")
        previous_scroll = page.evaluate("() => window.scrollY")
        assert previous_scroll >= 60
        units_url = page.url

        # The persistent shell stays mounted; keyboard navigation must not leave
        # focus on its old link or on a detached main-content element.
        if width < 920:
            menu_button = page.locator(".navigation-menu .menu-button")
            menu_button.press("Enter")
            assert menu_button.get_attribute("aria-expanded") == "true"
        page.locator(".navigation-menu a[href='/about']").press("Enter")
        assert_soft_navigation_handoff(page, "/about")
        assert page.locator(".navigation-menu .menu-button").get_attribute(
            "aria-expanded"
        ) == "false"

        page.go_back(wait_until="domcontentloaded")
        assert page.url == units_url, f"back lost Units state: {page.url}"
        assert_soft_navigation_handoff(page, "/units")
        page.wait_for_function(
            "expected => Math.abs(window.scrollY - expected) <= 2",
            arg=previous_scroll,
        )
        assert not errors, errors
    finally:
        page.close()
