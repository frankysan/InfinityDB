"""Chromium acceptance for the compact, fully reachable shared sidebar."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-navigation-browser.test"

DESTINATIONS = [
    "/armies", "/units", "/skills", "/orders-aros", "/equipment", "/weapons",
    "/ammunition", "/traits", "/labels", "/states", "/hacking-programs",
    "/fireteams", "/rules", "/scenarios", "/glossary", "/changes", "/about",
]


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


@pytest.mark.parametrize("width", [1440, 390])
def test_specialist_filter_combines_persists_and_resets(
    app: Any, chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/units", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#skill-filter')?.disabled === false",
            timeout=30000,
        )
        advanced = page.locator(".advanced-filters")
        if not advanced.evaluate("(node) => node.open"):
            advanced.locator("summary").click()
        specialist = page.locator("#specialist-filter")
        assert specialist.locator("option").all_text_contents() == [
            "Any", "Standard (InfinityDB)", "Domination", "Supplies", "Firefight",
        ]
        assert page.locator('a[href="/rules/specialist-troops-standard"]').is_visible()
        specialist.select_option("standard")
        assert "s=v1.u." in page.url
        page.wait_for_function(
            "() => document.querySelector('#unit-count')?.textContent?.includes(' / ')",
            timeout=12000,
        )
        standard = int(page.locator("#unit-count").inner_text().split(" / ")[0]
                       .replace(",", ""))
        assert standard > 0

        skills = page.locator("#skill-filter")
        doctor = skills.locator("option").filter(has_text="Doctor").first
        assert doctor.count() == 1
        doctor_id = doctor.get_attribute("value")
        skills.select_option(doctor_id)
        page.wait_for_function(
            "() => document.querySelector('#unit-count')?.textContent?.includes(' / ')",
            timeout=12000,
        )
        combined = int(page.locator("#unit-count").inner_text().split(" / ")[0]
                       .replace(",", ""))
        assert combined <= standard
        specialist.select_option("supplies")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#skill-filter')?.disabled === false",
            timeout=30000,
        )
        assert specialist.input_value() == "supplies"
        assert skills.input_value() == doctor_id
        page.locator("#clear-filters").click()
        page.wait_for_function(
            "() => document.querySelector('#specialist-filter')?.value === '' "
            "&& document.querySelector('#skill-filter')?.value === ''"
        )
        assert not errors, errors
    finally:
        page.close()

@pytest.mark.parametrize("width,height", [(1440, 900), (1024, 768)])
def test_desktop_sidebar_compacts_without_hiding_destinations(
    app: Any, chrome: Any, width: int, height: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/units", wait_until="domcontentloaded")
        nav = page.locator("#compact-navigation-menu")
        nav.wait_for(state="visible")
        links = nav.locator("a.nav-item")
        assert links.count() == len(DESTINATIONS)
        assert [link.get_attribute("href") for link in links.all()] == DESTINATIONS
        assert nav.bounding_box()["height"] < 680, width
        assert 32 <= links.first.bounding_box()["height"] <= 44
        assert page.locator(".nav-item[aria-current='page']").get_attribute("href") == "/units"

        sidebar = page.locator("aside.sidebar")
        assert sidebar.evaluate("(el) => el.scrollWidth <= el.clientWidth + 1")
        last = links.last
        last.focus()
        assert last.evaluate("(el) => document.activeElement === el")
        assert last.is_visible()
        assert last.evaluate(
            "(el) => { const parent = el.closest('.sidebar');"
            " const a = el.getBoundingClientRect();"
            " const b = parent.getBoundingClientRect();"
            " return a.top >= b.top && a.bottom <= b.bottom + 1; }"
        )
        settings = page.locator(".settings-menu")
        button = settings.locator("button.menu-button")
        button.focus()
        button.press("Enter")
        assert button.get_attribute("aria-expanded") == "true"
        assert settings.locator("#theme-selector").is_visible()
        button.press("Escape")
        assert button.get_attribute("aria-expanded") == "false"
        assert button.evaluate("(el) => document.activeElement === el")
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [(390, 640), (320, 640)])
def test_compact_navigation_uses_scrollable_keyboard_and_touch_menu(
    app: Any, chrome: Any, width: int, height: int,
) -> None:
    page = chrome.new_page(
        viewport={"width": width, "height": height}, has_touch=True,
    )
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/units", wait_until="domcontentloaded")
        menu = page.locator(".navigation-menu")
        panel = menu.locator("#compact-navigation-menu")
        button = menu.locator("button.menu-button")
        links = panel.locator("a.nav-item")
        page.wait_for_function(
            "() => document.querySelector('.navigation-menu')?.dataset.open === 'false'"
        )
        assert not panel.is_visible()
        button.tap()
        assert button.get_attribute("aria-expanded") == "true"
        assert panel.is_visible()
        assert [link.get_attribute("href") for link in links.all()] == DESTINATIONS
        assert panel.bounding_box()["height"] <= height - 90
        assert panel.evaluate("(el) => el.scrollHeight > el.clientHeight")
        last = links.last
        last.focus()
        assert last.evaluate("(el) => document.activeElement === el")
        assert panel.evaluate("(el) => el.scrollTop > 0")
        button.press("Escape")
        assert not panel.is_visible()
        assert button.get_attribute("aria-expanded") == "false"
        assert button.evaluate("(el) => document.activeElement === el")
        button.press("Enter")
        assert panel.is_visible()
        last.press("Enter")
        page.wait_for_url(f"{ORIGIN}/about")
        assert not page.locator("#compact-navigation-menu").is_visible()
        assert not errors, errors
    finally:
        page.close()
