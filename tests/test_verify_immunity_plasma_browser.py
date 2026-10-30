"""Real Chromium acceptance for N5.3 Immunity/Plasma Example 3."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-immunity-plasma.test"


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
            chrome = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield chrome
        finally:
            chrome.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_printed_plasma_case_has_separate_normal_reference_without_overflow(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        rows = page.locator(".immunity-reviewed-cases li")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 7",
            timeout=20000,
        )
        plasma = rows.filter(has_text="Immunity (Enhanced) vs Plasma Rifle")
        assert plasma.count() == 1
        assert "1 ARM Saving Roll and 1 BTS Saving Roll" in plasma.inner_text()
        assert "not a general immunity calculation" in plasma.inner_text()
        assert "Explicit N5.3 p. 96, Example 3" in plasma.inner_text()
        assert plasma.locator('a[href="/weapons/plasma-rifle"]').count() == 1
        assert plasma.locator('a[href="/ammunition/normal"]').count() == 1
        assert not plasma.locator("text=Critical").count()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_n53_bts_immunity_em_cc_weapon_is_exact_and_source_scoped(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 7",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        reviewed = cases.filter(has_text="Immunity (BTS) vs N + E/M")
        assert reviewed.count() == 1
        assert "E/M CC Weapon" in reviewed.inner_text()
        assert "1 Saving Roll on a hit (2 on a Critical) using BTS" in reviewed.inner_text()
        assert "2 Saving Rolls on a hit (3 on a Critical)" in reviewed.inner_text()
        assert "Derived from reviewed general rules" in reviewed.inner_text()
        assert "Applies to the reviewed non-Comms attack only." in reviewed.inner_text()
        assert reviewed.locator('a[href="/weapons/e-m-cc-weapon"]').count() == 1
        assert reviewed.locator('a[href="/ammunition/normal"]').count() >= 1
        assert reviewed.locator('a[href="/ammunition/em"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()
