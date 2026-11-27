"""Chromium acceptance for source-reviewed Weapon Chart footnote presentation."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page
from tools.testing.browser_test_metrics import launch_timed_chromium

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-browser.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/army.db",
        rules_database_path=ROOT / "data/generated/rules_n5.db",
    )


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            chromium = launch_timed_chromium(driver, "weapon-chart-footnotes")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        try:
            yield chromium
        finally:
            chromium.close()


def test_reviewed_weapon_footnotes_are_accessible_and_routable(
    app: Any, browser: Any,
) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    cases = (
        ("blitzen", "/ammunition/em", "N5.3 chart p. 178"),
        ("e-m-carbine", "/ammunition/em", "N5.3 chart p. 176"),
        ("e-m-cc-weapon", "/ammunition/em", "N5.3 chart p. 177"),
        ("smoke-grenades", "/ammunition/smoke", "N5.3 chart p. 178"),
        ("e-m-grenades", "/ammunition/em", "N5.3 chart p. 178"),
        ("eclipse-grenades", "/ammunition/eclipse", "N5.3 chart p. 178"),
        ("smoke-grenade-launcher", "/ammunition/smoke", "N5.3 chart p. 179"),
        ("e-m-grenade-launcher", "/ammunition/em", "N5.3 chart p. 179"),
        ("chest-mine", "#rule-weapon-chest-mine", "N5.3 chart p. 181"),
        ("para-mine", "#rule-weapon-mines", "N5.3 chart p. 181"),
        ("sepsitor-plus", "#rule-weapon-sepsitor-plus", "N5.3 chart p. 187"),
    )
    try:
        for slug, href, source in cases:
            page.goto(f"{ORIGIN}/weapons/{slug}", wait_until="domcontentloaded")
            link = page.locator(f'.weapon-source-footnotes a[href="{href}"]').first
            link.wait_for(state="visible", timeout=30000)
            section_text = link.evaluate(
                "(node) => node.closest('.weapon-source-footnotes')?.innerText || ''"
            )
            assert source in section_text
            if slug == "para-mine":
                assert "SRC-013" not in section_text
                assert "Army: [**]" in section_text
                assert "exact target not verified" not in section_text
            if slug == "sepsitor-plus":
                assert "SRC-014" not in section_text
            if slug in ("para-mine", "sepsitor-plus"):
                page.evaluate(
                    "() => document.documentElement.dataset.developerMode = 'true'"
                )
                developer_text = link.evaluate(
                    "(node) => node.closest('.weapon-source-footnotes')?.innerText || ''"
                )
                assert ("SRC-013" if slug == "para-mine" else "SRC-014") in developer_text
                if slug == "para-mine":
                    assert "exact target not verified" in developer_text
                page.evaluate(
                    "() => document.documentElement.dataset.developerMode = 'false'"
                )
            if slug == "chest-mine":
                cc = page.locator(".weapon-profile").filter(
                    has=page.locator("h4", has_text="CC Mode")
                )
                bs = page.locator(".weapon-profile").filter(
                    has=page.locator("h4", has_text="BS Mode")
                )
                assert cc.locator(".weapon-source-footnotes").count() == 1
                assert bs.locator(".weapon-source-footnotes a").count() == 0
                bs_note = bs.locator(".weapon-source-footnotes").inner_text()
                assert "Army and N5.3 chart p. 181: [*]" in bs_note
                assert "exact target not verified" not in bs_note
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 900})
                for scheme in ("light", "dark"):
                    page.evaluate(
                        "(scheme) => document.documentElement.dataset.theme = scheme",
                        scheme,
                    )
                    assert link.is_visible(), (slug, width, scheme)
                    assert page.evaluate(
                        "() => document.documentElement.scrollWidth <= innerWidth + 1"
                    ), (slug, width, scheme)
        page.goto(f"{ORIGIN}/weapons/para-mine", wait_until="domcontentloaded")
        link = page.locator(
            '.weapon-source-footnotes a[href="#rule-weapon-mines"]'
        )
        link.wait_for(state="visible", timeout=30000)
        link.focus()
        assert link.evaluate("(node) => document.activeElement === node")
        link.press("Enter")
        assert page.url.endswith("#rule-weapon-mines")
        assert page.locator("#rule-weapon-mines").count() == 1
        assert not errors, errors
    finally:
        context.close()


def test_reviewed_weapon_footnote_supports_touch(
    app: Any, browser: Any,
) -> None:
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
    )
    page = context.new_page()
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/weapons/blitzen", wait_until="domcontentloaded")
        link = page.locator(
            '.weapon-source-footnotes a[href="/ammunition/em"]'
        )
        link.wait_for(state="visible", timeout=30000)
        link.tap()
        page.wait_for_url(f"{ORIGIN}/ammunition/em", timeout=30000)
        assert not errors, errors
    finally:
        context.close()


def test_deactivator_equipment_footnote_links_to_canonical_rule(
    app: Any, browser: Any,
) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/equipment/deactivator", wait_until="domcontentloaded")
        link = page.locator(
            '.weapon-source-footnotes a[href="#rule-equipment-deactivator"]'
        )
        link.wait_for(state="visible", timeout=30000)
        note = page.locator(".weapon-source-footnotes").inner_text()
        assert "Army and N5.3 chart p. 186" in note
        assert "[***] Skills and Equipment" in note
        assert page.locator("#rule-equipment-deactivator").count() == 1
        assert page.locator('.weapon-source-footnotes a[href*="weapon-"]').count() == 0
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 900})
            for scheme in ("light", "dark"):
                page.evaluate(
                    "(scheme) => document.documentElement.dataset.theme = scheme",
                    scheme,
                )
                assert link.is_visible(), (width, scheme)
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth <= innerWidth + 1"
                ), (width, scheme)
        link.focus()
        assert link.evaluate("(node) => document.activeElement === node")
        link.press("Enter")
        assert page.url.endswith("#rule-equipment-deactivator")
        assert not errors, errors
    finally:
        context.close()

    touch_context = browser.new_context(
        viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
    )
    touch_page = touch_context.new_page()
    route_browser_page(touch_page, app, ORIGIN)
    try:
        touch_page.goto(
            f"{ORIGIN}/equipment/deactivator", wait_until="domcontentloaded"
        )
        touch_link = touch_page.locator(
            '.weapon-source-footnotes a[href="#rule-equipment-deactivator"]'
        )
        touch_link.wait_for(state="visible", timeout=30000)
        touch_link.tap()
        assert touch_page.url.endswith("#rule-equipment-deactivator")
    finally:
        touch_context.close()

def test_additional_reviewed_chart_footnotes_render_exact_mode_and_catalog_targets(
    app: Any, browser: Any,
) -> None:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    cases = (
        ("weapons", "trench-hammer", "#rule-weapon-mixed-weapons", 2),
        ("weapons", "drop-bears", "#rule-weapon-drop-bears", 2),
        ("weapons", "d-charges", "#rule-weapon-d-charges", 2),
        ("weapons", "eclipse-grenade-launcher", "/ammunition/eclipse", 1),
        ("weapons", "zapper", "/ammunition/em", 1),
        ("equipment", "fastpanda", "#rule-equipment-fastpanda", 1),
        ("equipment", "gizmokit", "#rule-equipment-gizmokit", 1),
        ("equipment", "medikit", "#rule-equipment-medikit", 1),
    )
    try:
        for catalog, slug, href, count in cases:
            page.goto(f"{ORIGIN}/{catalog}/{slug}", wait_until="domcontentloaded")
            links = page.locator(f'.weapon-source-footnotes a[href="{href}"]')
            links.first.wait_for(state="visible", timeout=30000)
            assert links.count() == count, slug
            assert page.locator(".weapon-source-footnotes").count() == count, slug
            if href.startswith("#"):
                assert page.locator(href).count() == 1, slug
            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                for scheme in ("light", "dark"):
                    page.evaluate(
                        "(scheme) => document.documentElement.dataset.theme = scheme",
                        scheme,
                    )
                    assert links.first.is_visible(), (slug, width, scheme)
                    assert page.evaluate(
                        "() => document.documentElement.scrollWidth <= innerWidth + 1"
                    ), (slug, width, scheme)
        assert not errors, errors
    finally:
        context.close()
