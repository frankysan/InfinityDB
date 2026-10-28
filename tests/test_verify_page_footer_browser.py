"""Chromium acceptance for the shared independent-resource footer disclosure."""

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


@pytest.mark.parametrize("width", [1440, 390, 320])
def test_shared_footer_disclosure_keyboard_and_mobile(
    app: Any, chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for path in ("/", "/about", "/scenarios/supplies?army_points=300"):
            page.goto(f"{ORIGIN}{path}", wait_until="domcontentloaded")
            details = page.locator("footer.page-footer details.page-footer-notice")
            summary = details.locator("summary")
            assert details.count() == 1
            assert summary.count() == 1
            assert not details.evaluate("(element) => element.open")
            assert summary.inner_text() == (
                "Independent community reference — important notice"
            )
            assert details.locator("a").get_attribute("href") == "/about"
            assert not details.locator("p").is_visible()
            summary.focus()
            assert summary.evaluate(
                "(element) => element === document.activeElement"
            )
            summary.press("Enter")
            assert details.evaluate("(element) => element.open")
            assert details.locator("p").is_visible()
            disclosure = details.locator("p").inner_text()
            assert "not affiliated with Corvus Belli S.L." in disclosure
            assert "may contain errors" in disclosure
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= innerWidth + 1"
            ), (width, path)
            summary.press("Space")
            assert not details.evaluate("(element) => element.open")
            assert not details.locator("p").is_visible()
        assert not errors, errors
    finally:
        page.close()
