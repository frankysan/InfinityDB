"""Unit comparison uses current Army profiles and exact group-local loadouts."""
from pathlib import Path

import pytest

from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-comparison.test"


def test_unit_comparison_browser() -> None:
    api = pytest.importorskip("playwright.sync_api")
    app = create_app_from_database_set(ROOT / "data/generated")
    with api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        try:
            for width in (1440, 390):
                page = browser.new_page(viewport={"width": width, "height": 900})
                route_browser_page(page, app, ORIGIN)
                errors: list[str] = []
                page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                page.goto(f"{ORIGIN}/units/401")
                link = page.locator("#unit-compare-link")
                link.wait_for(state="visible", timeout=30000)
                link.click()
                page.locator("#left-profile option").nth(1).wait_for(state="attached")
                assert page.locator("#left-profile").input_value()
                page.locator("#right-search").fill("Zeros")
                page.locator("#right-matches option").nth(1).wait_for(state="attached")
                assert "zero" in page.locator("#right-matches option").nth(1).inner_text().lower()
                assert page.locator("#right-profile").input_value() == ""
                page.locator("#right-search").fill("")
                assert page.locator("#right-matches").is_hidden()
                page.locator("#right-search").fill("not-a-real-unit-123456")
                page.get_by_text("No matching Units.", exact=True).wait_for()
                page.locator("#right-search").fill("Zeros")
                page.locator("#right-matches option").nth(1).wait_for(state="attached")
                page.locator("#right-matches").select_option(index=1)
                table = page.locator(".comparison-table")
                table.wait_for(state="visible", timeout=30000)
                assert page.locator("#right-profile").input_value()
                assert "Profile Skills" in table.inner_text()
                assert "Loadout Weapons" in table.inner_text()
                assert "VITA / STR" in table.inner_text()
                page.locator("#left-loadout").select_option(index=1)
                assert page.locator("#left-loadout").input_value()
                page.locator("#comparison-differences").check()
                saved = page.url
                assert "?s=v1.p." in saved
                page.goto(saved)
                table.wait_for(state="visible", timeout=30000)
                assert page.locator("#left-loadout").input_value()
                assert page.locator("#comparison-differences").is_checked()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.get_by_role("button", name="Clear Unit").nth(1).click()
                assert table.count() == 0
                assert not errors, errors
                page.close()
        finally:
            browser.close()
