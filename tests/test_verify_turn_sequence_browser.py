"""V1S-032C1 normal Chrome checks for Game Sequence and Order Pool."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-turn-sequence.test"


@pytest.fixture(scope="module")
def release_app() -> Callable[..., Any]:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


@pytest.fixture(scope="module")
def chrome() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as driver:
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


@pytest.mark.parametrize("width", (1440, 390, 320))
def test_game_sequence_and_order_pool_browser_navigation(
    release_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    """Catalog, two public pages, source citations and cross-links."""
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, release_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        response = page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        entry = page.locator('#catalog-list a[href="/rules/game-sequence"]')
        entry.wait_for(state="visible", timeout=30000)
        entry.click()
        page.wait_for_url(f"{ORIGIN}/rules/game-sequence", timeout=30000)
        sequence = page.locator("#rule-rule-game-sequence")
        sequence.wait_for(state="visible", timeout=30000)
        body = sequence.inner_text()
        for phrase in (
            "two Player Turns", "1. Tactical Phase", "2. Impetuous Phase",
            "3. Orders Phase", "4. States Phase", "5. End of the Turn",
            "Executive Use", "Order Count", "both players",
            "do not generate AROs", "cannot be saved for a later Turn",
        ):
            assert phrase in body, (width, phrase)
        source = sequence.locator(".rules-source-citations").inner_text()
        assert "p. 16" in source and "p. 17" in source
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), ("sequence", width)

        link = sequence.locator('a[href="/rules/order-pool"]').first
        link.wait_for(state="visible", timeout=10000)
        link.focus()
        link.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/order-pool", timeout=30000)
        pool = page.locator("#rule-rule-order-pool")
        pool.wait_for(state="visible", timeout=30000)
        body = pool.inner_text()
        for phrase in (
            "Regular Order Pool", "Irregular Order contribution",
            "Special Lieutenant Order", "Tactical Order contribution",
            "same Trooper repeatedly", "Private Information",
            "Open Information", "SRC-031", "Teniente en estado no Nulo",
            "not been officially corrected",
        ):
            assert phrase in body, (width, phrase)
        source = pool.locator(".rules-source-citations").inner_text()
        for page_number in (11, 12, 16, 17):
            assert f"p. {page_number}" in source
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), ("pool", width)
        link = pool.locator('a[href="/rules/game-sequence"]').first
        link.wait_for(state="visible", timeout=10000)
        link.focus()
        link.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/game-sequence", timeout=30000)
        assert not errors, (width, errors)
    finally:
        page.close()
