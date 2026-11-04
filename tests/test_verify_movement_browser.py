"""Ordinary movement-reference navigation and responsive Chromium acceptance."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page
from tools.promote_movement_reference import ARMY, ROOT, RULES

ORIGIN = "http://infinitydb-movement.test"


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
def test_movement_catalog_skill_links_and_source_citations(chrome: Any, width: int) -> None:
    app = create_app(ROOT / ARMY, rules_database_path=ROOT / RULES)
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    failed: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: failed.append(request.url))
    page.on("response", lambda response: failed.append(
        f"{response.status} {response.url}"
    ) if response.status >= 400 else None)
    try:
        response = page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        general = page.locator('#catalog-list a[href="/rules/general-movement"]')
        general.wait_for(state="visible", timeout=30000)
        general.focus()
        general.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/general-movement", timeout=30000)
        card = page.locator("#rule-rule-general-movement")
        card.wait_for(state="visible", timeout=30000)
        text = card.inner_text()
        for phrase in ("360-degree", "both sides", "cannot finish", "Enemy contact",
                       "No falling", "Idle", "does not determine pathfinding"):
            assert phrase in text, (width, phrase)
        citations = card.locator(".rules-source-citations").inner_text()
        assert "p. 29" in citations and "p. 30" in citations
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        move = card.locator('a[href="/skills/move"]').first
        move.focus()
        move.press("Enter")
        page.wait_for_url(f"{ORIGIN}/skills/move", timeout=30000)
        card = page.locator("#rule-skill-move")
        card.wait_for(state="visible", timeout=30000)
        text = card.inner_text()
        for phrase in ("Requirements", "at least half", "half as wide", "entire base",
                       "second Basic Short Skill", "after the first"):
            assert phrase in text, (width, phrase)
        assert "p. 28" in card.locator(".rules-source-citations").inner_text()
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        measuring = card.locator('a[href="/rules/moving-and-measuring"]').first
        measuring.focus()
        measuring.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/moving-and-measuring", timeout=30000)
        card = page.locator("#rule-rule-moving-and-measuring")
        card.wait_for(state="visible", timeout=30000)
        text = card.inner_text()
        for phrase in ("Sequence", "outer edge and underside", "Stairs and ladders",
                       "along the travelled surface", "no extra movement"):
            assert phrase in text, (width, phrase)
        citations = card.locator(".rules-source-citations").inner_text()
        assert "p. 27" in citations and "p. 28" in citations
        assert card.locator('a[href="/skills/jump"]').count() > 0
        assert card.locator('a[href="/skills/climb"]').count() > 0
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors and not failed, (width, errors, failed)
    finally:
        page.close()
