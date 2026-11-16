"""V1S-032C2 normal Chrome acceptance of ARO and Deployment rules."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-aro-deployment.test"


@pytest.fixture(scope="module")
def app() -> Callable[..., Any]:
    return create_app(
        ROOT / "data/generated/army.db",
        rules_database_path=ROOT / "data/generated/rules_n5.db",
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
def test_aro_and_deployment_reference_normal_browser(
    app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    """Browse catalog, ARO, Order Expenditure and Deployment at three widths."""
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        response = page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        anchor = page.locator(
            '#catalog-list a[href="/rules/automatic-reaction-order"]'
        )
        anchor.wait_for(state="visible", timeout=30000)
        anchor.click()
        page.wait_for_url(
            f"{ORIGIN}/rules/automatic-reaction-order", timeout=30000,
        )
        card = page.locator("#rule-rule-automatic-reaction-order")
        card.wait_for(state="visible", timeout=30000)
        content = card.inner_text()
        for phrase in (
            "One reaction, not one per Skill",
            "one ARO against each Order",
            "Line of Fire", "Zone of Control", "Hacking Area",
            "Template Weapon", "Comms Attack", "Burst B1",
            "cannot split that Burst", "forfeit", "simultaneous",
            "one of the Troopers activated by the Order",
            "not a second ARO", "does not evaluate",
        ):
            assert phrase in content, (width, phrase)
        cites = card.locator(".rules-source-citations").inner_text()
        assert "p. 13" in cites and "p. 14" in cites
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), ("aro", width)
        related = card.locator(
            'a[href="/rules/order-expenditure-sequence"]'
        ).first
        related.wait_for(state="visible", timeout=10000)
        related.focus()
        related.press("Enter")
        page.wait_for_url(
            f"{ORIGIN}/rules/order-expenditure-sequence", timeout=30000,
        )

        response = page.goto(f"{ORIGIN}/rules", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        deploy = page.locator('#catalog-list a[href="/rules/deployment-phase"]')
        deploy.wait_for(state="visible", timeout=30000)
        deploy.focus()
        deploy.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/deployment-phase", timeout=30000)
        card = page.locator("#rule-rule-deployment-phase")
        card.wait_for(state="visible", timeout=30000)
        content = card.inner_text()
        for phrase in (
            "first player's main force", "second player's main force",
            "entire base totally inside", "cannot be deployed in contact",
            "any mission objective", "whole base", "Prone",
            "central line", "Exclusion Zone", "Forward Deployment",
            "Unless both players previously agree",
        ):
            assert phrase in content, (width, phrase)
        cites = card.locator(".rules-source-citations").inner_text()
        assert "p. 15" in cites and "p. 16" in cites
        assert card.locator('a[href="/rules/initiative-roll"]').count() > 0
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), ("deployment", width)
        assert not errors, (width, errors)
    finally:
        page.close()
