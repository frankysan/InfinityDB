"""Chromium acceptance for the floating, session-collapsible accuracy notice."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-footer-browser.test"


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


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 640), (320, 540)])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_accuracy_notice_floats_and_remembers_session_toggle(
    app: Any, chrome: Any, width: int, height: int, theme: str,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": height}, has_touch=True)
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/", wait_until="domcontentloaded")
        page.evaluate(
            "(theme) => document.documentElement.setAttribute('data-theme', theme)",
            theme,
        )
        details = page.locator("main .page-footer-notice")
        summary = details.locator("summary")
        assert details.count() == 1
        assert details.evaluate("(node) => node.open")
        assert details.locator(".page-footer-notice-title").is_visible()
        assert details.locator("p").is_visible()
        assert details.locator("a").get_attribute("href") == "/about"
        disclosure = details.locator("p").inner_text()
        assert "not affiliated with Corvus Belli S.L." in disclosure
        assert "may contain errors" in disclosure
        assert summary.get_attribute("aria-label") == (
            "Toggle InfinityDB accuracy and independence notice"
        )
        assert details.evaluate(
            "(node) => getComputedStyle(node).position === 'fixed'"
        )
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        bounds = details.bounding_box()
        assert bounds is not None
        assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width + 1
        assert 0 <= height - (bounds["y"] + bounds["height"]) <= 36
        assert bounds["height"] <= height * 0.65
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), (width, theme)

        summary.focus()
        assert summary.evaluate("(node) => node === document.activeElement")
        summary.press("Enter")
        assert not details.evaluate("(node) => node.open")
        assert not details.locator("p").is_visible()
        assert not details.locator(".page-footer-notice-title").is_visible()
        assert details.locator(".page-footer-notice-icon").is_visible()
        closed = details.bounding_box()
        assert closed is not None
        assert 43 <= closed["width"] <= 45 and 43 <= closed["height"] <= 45
        page.wait_for_function(
            "() => sessionStorage.getItem('infinitydb-accuracy-notice-collapsed') === 'true'"
        )

        # Soft navigation replaces main; the icon and its state must survive.
        page.evaluate("() => window.infinityNavigate('/about')")
        page.locator("main .page-footer-notice").wait_for(state="visible")
        assert not details.evaluate("(node) => node.open")
        summary.press("Space")
        assert details.evaluate("(node) => node.open")
        page.wait_for_function(
            "() => sessionStorage.getItem('infinitydb-accuracy-notice-collapsed') === 'false'"
        )
        page.reload(wait_until="domcontentloaded")
        assert details.evaluate("(node) => node.open")
        assert details.locator("p").is_visible()
        page.locator(".page-footer-notice-body a[href='/about']").click()
        page.wait_for_url(f"{ORIGIN}/about")
        assert details.evaluate("(node) => node.open")
        assert not errors, errors
    finally:
        page.close()
