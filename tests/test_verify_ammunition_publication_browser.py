"""Browser parity between reviewed Ammunition source identities and Weapon details.

Use the published API as the source of truth. The visualized components and
shared rules are links/descriptions only: never compute Immunity, Saving Roll
counts, Critical results, or Weapon profile effects from them.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-ammunition-parity.test"
SAMPLES = (
    ("e-m-cc-weapon", 5, ("normal", "em"), "BTS/2", "2"),
    ("feuerbach", 10, ("ap", "da"), "ARM/2", "2"),
    ("missile-launcher", 13, ("ap", "exp"), "ARM/2", "3"),
    ("uragan-mrl", 30, ("ap", "shock"), "ARM/2", "1"),
    ("ap-t2-cc-weapon", 40, ("ap", "t2"), "ARM/2", "1"),
)


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


def _display_summary(summary: str) -> str:
    """The browser renders maintained [[target|label]] references as labels."""
    return re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", summary).strip()


def _api(app: Any, path: str) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def respond(status: str, _headers: list, _exc: object = None) -> None:
        statuses.append(status)

    data = b"".join(app(environ, respond))
    assert statuses == ["200 OK"]
    return json.loads(data)


def _profile(payload: dict[str, Any], source_id: int) -> dict[str, Any]:
    profiles = payload.get("profiles", []) + [
        p for variant in payload.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    matches = [
        p for p in profiles if p.get("ammunition_source_id") == source_id
    ]
    assert matches
    return matches[0]


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
@pytest.mark.parametrize(
    "slug,source_id,components,saving,rolls",
    SAMPLES,
)
def test_reviewed_components_and_shared_rules_render_from_published_api(
    app: Any, browser: Any, slug: str, source_id: int,
    components: tuple[str, str], saving: str, rolls: str,
    width: int, height: int,
) -> None:
    api_profile = _profile(_api(app, f"/api/weapons/{slug}"), source_id)
    assert api_profile["saving"] == saving
    assert str(api_profile["saving_num"]) == rolls
    expected_links = [f"/ammunition/{key}" for key in components]
    assert api_profile["ammunition_composition"]["kind"] == "combined"
    assert [
        part["public_reference"]["id"]
        for part in api_profile["ammunition_composition"]["components"]
    ] == list(components)
    assert [effect["record_id"] for effect in api_profile["ammunition_effects"]] == [
        f"ammunition:{key}" for key in components
    ]
    assert all(effect["citations"] for effect in api_profile["ammunition_effects"])

    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/weapons/{slug}", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector("
            "'.weapon-profile .weapon-statline tbody tr') !== null",
            timeout=20000,
        )
        cards = page.locator(".weapon-profile").filter(
            has=page.locator(".weapon-statline td[data-label='Ammunition']")
            .filter(has_text=api_profile["ammunition"])
        )
        if api_profile.get("mode"):
            cards = cards.filter(
                has=page.locator("h4").filter(has_text=api_profile["mode"])
            )
        assert cards.count() == 1, (slug, source_id, api_profile.get("mode"))
        card = cards.first
        ammo_cell = card.locator(".weapon-statline td[data-label='Ammunition']")
        assert ammo_cell.inner_text().replace(" ", "") == api_profile[
            "ammunition"
        ].replace(" ", "")
        assert ammo_cell.locator("a").evaluate_all(
            "(links) => links.map((link) => link.getAttribute('href'))"
        ) == expected_links
        assert card.locator(".weapon-statline td[data-label='Saving']").inner_text() == (
            f"{saving} × {rolls}"
        )
        details = card.locator(".weapon-ammunition-effects")
        assert details.count() == 1
        assert details.locator("summary").inner_text() == "Ammunition effects (shared rules)"
        details.evaluate("(element) => element.open = true")
        effects = details.locator(".weapon-ammunition-effect")
        assert effects.count() == len(components)
        for index, effect in enumerate(api_profile["ammunition_effects"]):
            item = effects.nth(index)
            assert item.locator("h5 a").get_attribute("href") == expected_links[index]
            assert item.locator("p.detail-copy").inner_text().strip() == (
                _display_summary(effect["summary"])
            )
            assert item.locator(".detail-source").inner_text().strip()
            assert item.locator(".detail-source a").count() == len(effect["citations"])
            assert item.locator("h5").inner_text().strip() == effect["name"]
        assert "Shared components only" in details.inner_text()
        assert "Follow the printed Weapon profile" in details.inner_text()
        assert "immunity" not in card.get_attribute("class").lower()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
def test_plasma_saving_attribute_pair_is_not_displayed_as_combined_ammunition(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    payload = _api(app, "/api/weapons/plasma-rifle")
    profiles = payload["profiles"] + [
        p for variant in payload.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    assert profiles
    assert all("ammunition_composition" not in p for p in profiles)
    assert all(p["ammunition"] == "N" for p in profiles)
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    try:
        page.goto(f"{ORIGIN}/weapons/plasma-rifle", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector("
            "'.weapon-profile .weapon-statline tbody tr') !== null",
            timeout=20000,
        )
        cells = page.locator(".weapon-profile .weapon-statline td[data-label='Ammunition']")
        assert cells.count() > 0
        for i in range(cells.count()):
            assert cells.nth(i).inner_text().strip() == "N"
            assert cells.nth(i).locator('a[href="/ammunition/normal"]').count() == 1
        saving_cells = page.locator(
            ".weapon-profile .weapon-statline td[data-label='Saving']"
        )
        assert saving_cells.count() > 0
        assert saving_cells.first.inner_text().startswith("ARM and BTS")
        assert not page.locator('.weapon-profile .weapon-statline a[href="/ammunition/ap"]').count()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
    finally:
        page.close()
