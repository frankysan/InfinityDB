"""Chromium acceptance for the generated N5.3 Orders/AROs reference page."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-orders-aros-browser.test"
SECTION_COUNTS = {
    "basic-short-skill": 3,
    "short-skill": 23,
    "long-skill": 15,
    "aro": 16,
}


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


@pytest.mark.parametrize("width,height", [
    (1440, 900), (1024, 768), (390, 844), (320, 640),
])
def test_orders_aros_page_renders_and_filters_without_overflow(
    app: Any, chrome: Any, width: int, height: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        response = page.goto(f"{ORIGIN}/orders-aros", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        page.wait_for_function(
            "() => document.querySelector('#matrix-count')?.textContent === "
            "'57 declarations'",
            timeout=20000,
        )
        assert page.locator('a.nav-item[aria-current="page"]').get_attribute(
            "href"
        ) == "/orders-aros"
        assert page.locator("#matrix-sections[aria-busy=false]").count() == 1
        assert page.locator("#matrix-sections tbody tr").count() == 57
        assert page.locator("#matrix-state").inner_text() == ""
        assert "not whether it is legal" in page.locator("#main").inner_text()
        assert "N5.3 Core Rules, p. 191" in page.locator("#main").inner_text()

        for section, count in SECTION_COUNTS.items():
            node = page.locator(f"#orders-aros-{section}")
            assert node.is_visible(), section
            assert node.locator("xpath=../following-sibling::div//tbody/tr").count() == count

        # The source's "Equipment" type includes the Skill Activate Disco Ball.
        search = page.locator("#matrix-search")
        search.fill("Equipment")
        assert page.locator("#matrix-count").inner_text() == "4 declarations"
        assert set(page.locator("#matrix-sections tbody tr").evaluate_all(
            "(rows) => rows.map((row) => row.dataset.recordId)"
        )) == {
            "skill:activate-disco-ball",
            "equipment:deactivator",
            "equipment:gizmokit",
            "equipment:medikit",
        }
        search.fill("Controlled Jump")
        assert page.locator("#matrix-count").inner_text() == "2 declarations"
        assert page.locator("#matrix-sections a").count() == 2
        search.fill("impossible-query-zzzz")
        assert page.locator("#matrix-count").inner_text() == "0 declarations"
        assert page.locator("#matrix-state").inner_text() == "No matching actions."
        assert page.locator("#matrix-sections section").count() == 0
        search.fill("")
        assert page.locator("#matrix-count").inner_text() == "57 declarations"

        # Data tables may be scrollable, but the page itself must not overflow.
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), width
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,record_id,target", [
    (1440, "equipment:deactivator", "/equipment/deactivator"),
    (390, "hacking-program:controlled-jump", "/hacking-programs/controlled-jump"),
    (320, "skill:move", "/skills/move"),
])
def test_orders_aros_links_open_existing_reference_details(
    app: Any, chrome: Any, width: int, record_id: str, target: str,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 844})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/orders-aros", wait_until="domcontentloaded")
        page.locator(f'#matrix-sections tr[data-record-id="{record_id}"] a').first.wait_for(
            state="visible", timeout=20000,
        )
        link = page.locator(f'#matrix-sections tr[data-record-id="{record_id}"] a').first
        assert link.get_attribute("href") == target
        link.click()
        page.wait_for_url(f"{ORIGIN}{target}")
        if record_id == "skill:move":
            page.locator("#skill-content").wait_for(state="visible", timeout=15000)
            assert "Move" in page.locator("#skill-name").inner_text()
        else:
            page.locator("#item-name").wait_for(state="visible", timeout=15000)
        assert not errors, errors
    finally:
        page.close()
