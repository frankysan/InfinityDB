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


@pytest.mark.parametrize("width", (1440, 390, 320))
def test_geometry_reference_navigation_and_existing_silhouette_diagrams(
    chrome: Any, width: int,
) -> None:
    """Browse shared geometry owners without conflating the range Trait."""
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

    def catalog_card(slug: str, phrases: tuple[str, ...], pages: tuple[int, ...]) -> Any:
        response = page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        link = page.locator(f'#catalog-list a[href="/rules/{slug}"]')
        link.wait_for(state="visible", timeout=30000)
        link.focus()
        link.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/{slug}", timeout=30000)
        card = page.locator(f"#rule-rule-{slug}")
        card.wait_for(state="visible", timeout=30000)
        for phrase in phrases:
            assert phrase in card.inner_text(), (width, slug, phrase)
        citations = card.locator(".rules-source-citations").inner_text()
        for number in pages:
            assert f"p. {number}" in citations, (width, slug, number)
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        return card

    try:
        card = catalog_card("line-of-fire", (
            "180-degree", "3 by 3 mm", "360-degree", "Mutual visibility is conditional",
            "friendly or enemy", "Close combat", "Sixth Sense",
        ), (18, 19))
        silhouette = card.locator('a[href="/glossary#attribute-s"]').first
        silhouette.focus()
        silhouette.press("Enter")
        page.wait_for_url(f"{ORIGIN}/glossary#attribute-s", timeout=30000)
        entry = page.locator("#attribute-s")
        entry.wait_for(state="visible", timeout=30000)
        for phrase in ("cylindrical", "projecting beyond", "SX", "3 mm", "base width"):
            assert phrase in entry.inner_text(), (width, phrase)
        assert entry.locator('img[src*="/static/silhouettes/"]').count() == 8
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")

        card = catalog_card("zone-of-control", (
            "above its top", "below its bottom", "Weapon Trait", "starting and final positions",
        ), (20,))
        assert card.locator('a[href="/traits/zone-of-control-zc"]').count() > 0
        zones = card.locator('a[href="/rules/zones-and-contact"]').first
        zones.focus()
        zones.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/zones-and-contact", timeout=30000)
        card = page.locator("#rule-rule-zones-and-contact")
        card.wait_for(state="visible", timeout=30000)
        for phrase in ("always in contact with themselves", "Totally inside", "entire Silhouette"):
            assert phrase in card.inner_text(), (width, phrase)
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")

        catalog_card("coherency", (
            "Reference Trooper", "Controller or Spearhead", "before measuring",
            "Conclusion step", "multiple reserve Troopers", "unless the opponent requests",
        ), (21,))
        card = catalog_card("distances-and-measurements", (
            "closest points", "straight line", "complete route and endpoint", "before declarations",
        ), (21, 22))
        assert card.locator('a[href="/rules/moving-and-measuring"]').count() > 0
        card = catalog_card("replacing-game-elements", (
            "same position", "matching the centers", "matching their edges",
            "cannot be used to cancel Engaged", "mandatory and inevitable",
            "Equipment is removed", "ends only when", "ordinary cancellation methods",
            "grants no independent permission",
        ), (22,))
        assert card.locator('a[href="/states/immobilized-a"]').count() > 0
        assert card.locator('a[href="/states/engaged"]').count() > 0
        assert not errors and not failed, (width, errors, failed)
    finally:
        page.close()


@pytest.mark.parametrize("width", (1440, 390, 320))
def test_cover_and_vertical_skills_with_separate_dated_faq(chrome: Any, width: int) -> None:
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

    def visible_card(identity: str, phrases: tuple[str, ...], numbers: tuple[int, ...]) -> Any:
        card = page.locator("#rule-" + identity.replace(":", "-"))
        card.wait_for(state="visible", timeout=30000)
        for phrase in phrases:
            assert phrase in card.inner_text(), (width, identity, phrase)
        citations = card.locator(".rules-source-citations").inner_text()
        for number in numbers:
            assert f"p. {number}" in citations
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        return card

    def dated_vaulting_faq() -> None:
        faq = page.locator(".faq-rulings .faq-ruling").filter(
            has_text="Can a Trooper vault while Climbing or Jumping?"
        )
        faq.wait_for(state="visible", timeout=30000)
        assert faq.count() == 1
        text = faq.inner_text()
        assert "version 0.1" in text and "first documented v0.0" in text

    try:
        response = page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        link = page.locator('#catalog-list a[href="/rules/cover"]')
        link.wait_for(state="visible", timeout=30000)
        link.focus()
        link.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/cover", timeout=30000)
        card = visible_card("rule:cover", (
            "Total Cover", "Partial Cover", "-3 to the attacker's", "+3 to the target's",
            "if a roll is necessary", "contact alone is insufficient", "not a permanent increase",
        ), (41, 42))
        climb = card.locator('a[href="/skills/climb"]').first
        climb.focus()
        climb.press("Enter")
        page.wait_for_url(f"{ORIGIN}/skills/climb", timeout=30000)
        card = visible_card("skill:climb", (
            "When declaring", "outer edge and underside", "whole base", "Unused allowance",
            "not mandatory in every Order", "Reactive Turn", "State Token",
            "except for Unit Types", "horizontal upper surface",
        ), (32, 33))
        dated_vaulting_faq()
        cover = card.locator('a[href="/rules/cover"]').first
        cover.focus()
        cover.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/cover", timeout=30000)
        card = page.locator("#rule-rule-cover")
        card.wait_for(state="visible", timeout=30000)
        jump = card.locator('a[href="/skills/jump"]').first
        jump.focus()
        jump.press("Enter")
        page.wait_for_url(f"{ORIGIN}/skills/jump", timeout=30000)
        visible_card("skill:jump", (
            "horizontal landing surface", "parabolic route", "touches the landing surface",
            "entire Order", "including after landing", "automatically cancels",
            "no safe alternative", "Idle",
        ), (34,))
        dated_vaulting_faq()

        response = page.goto(f"{ORIGIN}/skills", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        link = page.locator('#catalog-list a[href="/skills/climbing-plus"]')
        link.wait_for(state="visible", timeout=30000)
        link.focus()
        link.press("Enter")
        page.wait_for_url(f"{ORIGIN}/skills/climbing-plus", timeout=30000)
        card = visible_card("skill:climbing-plus", (
            "first Basic Short Skill", "once per Order", "second MOV value",
            "Partial Cover MODs while on a vertical surface", "General Movement Rules",
        ), (88,))
        assert card.locator('a[href="/rules/cover"]').count() > 0
        assert card.locator('a[href="/rules/line-of-fire"]').count() > 0
        assert not errors and not failed, (width, errors, failed)
    finally:
        page.close()
