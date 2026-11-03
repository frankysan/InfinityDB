"""Normal-mode Chromium acceptance for the optional N4-origin Reinforcements annex.

This verifies published navigation and disclosures, not N5-native annex authority,
army-list legality, or the still-unpromoted typed Commlink (+X) v9 publication.
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
ORIGIN = "http://infinitydb-reinforcements-browser.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    api = pytest.importorskip("playwright.sync_api")
    with api.sync_playwright() as driver:
        try:
            chrome = launch_timed_chromium(driver, "reinforcements-optional")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield chrome
        finally:
            chrome.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
def test_optional_annex_disclosures_and_links_stay_outside_core_matrix(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    responses: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("response", lambda response: responses.append(
        f"{response.status} {response.url}",
    ) if response.status >= 400 else None)
    try:
        response = page.goto(f"{ORIGIN}/rules/reinforcements-extra", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        rule = page.locator("#rule-rule-reinforcements-extra")
        rule.wait_for(state="visible", timeout=20000)
        assert page.locator("#item-name").inner_text().startswith("Reinforcements Extra")
        assert "N4-origin" in rule.inner_text()
        assert "not been verified" in rule.inner_text()
        assert rule.locator(".rules-source-citations a").count() == 4
        assert "N4" in rule.locator(".detail-source").all_inner_texts()[-1]

        commlink = rule.locator('a[href="/skills/commlink"]').first
        assert commlink.is_visible()
        commlink.click()
        page.wait_for_url(f"{ORIGIN}/skills/commlink")
        skill = page.locator("#rule-skill-commlink")
        skill.wait_for(state="visible", timeout=20000)
        assert page.locator("#skill-name").inner_text().startswith("Commlink")
        assert "N4-origin" in skill.inner_text()
        assert "maximum Trooper count" in skill.inner_text()
        assert skill.locator(".rules-source-citations a").count() >= 1

        request = skill.locator('a[href="/skills/request-reinforcements"]').first
        assert request.is_visible()
        request.click()
        page.wait_for_url(f"{ORIGIN}/skills/request-reinforcements")
        request_rule = page.locator("#rule-skill-request-reinforcements")
        request_rule.wait_for(state="visible", timeout=20000)
        assert page.locator("#skill-name").inner_text().startswith("Request Reinforcements")
        assert "N4-origin" in request_rule.inner_text()
        assert "Tactical Phase step" in request_rule.inner_text()
        assert "not an ordinary Order declaration" in request_rule.inner_text()

        annex_link = request_rule.locator('a[href="/rules/reinforcements-extra"]').first
        assert annex_link.is_visible()
        annex_link.focus()
        page.keyboard.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/reinforcements-extra")
        rule.wait_for(state="visible", timeout=20000)

        page.goto(f"{ORIGIN}/orders-aros", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#matrix-count')?.textContent === '57 declarations'",
            timeout=20000,
        )
        matrix = page.locator("#matrix-sections")
        assert matrix.locator("tbody tr").count() == 57
        assert not matrix.locator('tr[data-record-id="skill:commlink"]').count()
        assert not matrix.locator('tr[data-record-id="skill:request-reinforcements"]').count()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), width
        assert not errors, errors
        assert not responses, responses
    finally:
        page.close()
