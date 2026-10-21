"""Pinned Chromium acceptance for two reviewed N5.3 Weapon source cards."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from typing import Any
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db.web import create_app


class _ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def origin() -> Iterator[str]:
    root = Path(__file__).resolve().parents[1]
    app = create_app(
        root / "data/generated/infinity.db",
        rules_database_path=root / "data/generated/rules.db",
    )
    server = make_server(
        "127.0.0.1", 0, app,
        server_class=_ThreadedServer, handler_class=_QuietHandler,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def chrome() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        try:
            yield browser
        finally:
            browser.close()


CASES = (
    ("d-charges", "weapon:d-charges", {"CC Mode", "Demolition Mode"}, {70, 186}),
    ("disco-baller", "weapon:disco-baller", {None, "Disco Ball"}, {71, 186}),
)


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize(("slug", "rule_id", "modes", "pages"), CASES)
def test_pinned_weapon_modes_rules_links_and_citations(
    origin: str, chrome: Any, width: int, slug: str, rule_id: str,
    modes: set[str | None], pages: set[int],
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        response = page.request.get(f"{origin}/api/weapons/{slug}")
        assert response.status == 200
        item = response.json()
        profiles = item["profiles"]
        assert len(profiles) == 2
        assert {profile["mode"] for profile in profiles} == modes
        rule = next(rule for rule in item["rules"] if rule["id"] == rule_id)
        assert pages <= {
            citation["page"] for citation in rule["citations"]
            if citation["source_id"] == "n5-core-v5.3-pdf"
        }
        variants = item["weapon_variants"]
        expected_profile_titles = [
            profile.get("mode") or profile.get("name") or variant["name"]
            for variant in variants for profile in variant["profiles"]
        ]
        assert len(expected_profile_titles) == 2

        route = f"{origin}/weapons/{slug}#rule-{rule_id.replace(':', '-')}"
        page.goto(route, wait_until="domcontentloaded")
        page.locator("#item-content").wait_for(state="visible", timeout=60000)
        cards = page.locator(".weapon-variant .weapon-profile")
        assert cards.count() == 2, (slug, width)
        assert [card.locator("h4").first.text_content() for card in cards.all()] == (
            expected_profile_titles
        )
        for card, profile in zip(cards.all(), (
            profile for variant in variants for profile in variant["profiles"]
        ), strict=True):
            stat = card.locator(".weapon-statline tbody tr").first
            assert stat.locator('td[data-label="B"]').text_content() == str(profile["burst"])
            assert stat.locator('td[data-label="PS"]').text_content() == str(profile["damage"])
            assert card.locator("h4").first.is_visible()
            if profile.get("profile"):
                assert profile["profile"] in card.inner_text()

        article = page.locator(f'[id="rule-{rule_id.replace(":", "-")}"]')
        article.wait_for(state="visible", timeout=10000)
        assert article.count() == 1
        visible_text = article.inner_text()
        assert all(f"p. {number}" in visible_text for number in pages)
        assert "[[" not in visible_text  # Maintained semantic links must render as UI.
        for relation in rule.get("display_relations", []):
            if not relation.get("presentation"):
                continue
            reference = relation["record"].get("public_reference") or {}
            href = reference.get("href")
            if not href and reference.get("catalog") and reference.get("id"):
                href = f"/{reference['catalog']}/{reference['id']}"
            if href:
                assert article.locator(".rules-relations a").evaluate_all(
                    "(links, href) => links.some(link => link.getAttribute('href') === href)",
                    href,
                ), (slug, width, relation["record"]["id"], href)
        assert not errors, (slug, width, errors)
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), (slug, width)
    finally:
        page.close()

@pytest.fixture(scope="module")
def multi_profile_weapons(origin: str) -> list[dict[str, Any]]:
    """Discover all multi-profile Weapons from the published API."""
    import json
    from urllib.request import urlopen

    def get(path: str) -> dict[str, Any]:
        with urlopen(f"{origin}{path}", timeout=15) as response:
            assert response.status == 200, path
            return json.load(response)

    details = []
    for item in get("/api/weapons")["items"]:
        detail = get(f"/api/weapons/{item['slug']}")
        profiles = [
            profile for variant in detail.get("weapon_variants", [])
            for profile in variant.get("profiles", [])
        ]
        assert len(profiles) == len(detail["profiles"]), item["slug"]
        if len(profiles) > 1:
            details.append(detail)
    assert len(details) >= 2, "Pinned catalog unexpectedly lacks multi-profile Weapons"
    return details


def _saving_display(profile: dict[str, Any]) -> str:
    saving = profile.get("saving")
    if saving is None or str(saving).strip() in ("", "-", "--"):
        return "--"
    return " × ".join(
        str(value) for value in (saving, profile.get("saving_num"))
        if value is not None and value != ""
    )


def _stat_display(value: Any) -> str:
    return "—" if value is None or value == "" else str(value)


def _ammunition_display(profile: dict[str, Any]) -> str:
    if profile.get("ammunition") == 0:
        return "--"
    if isinstance(profile.get("ammunition_parts"), list):
        return "".join(part["text"] for part in profile["ammunition_parts"])
    return _stat_display(profile.get("ammunition"))


def test_all_published_multi_profile_weapon_statlines_render_on_mobile(
    origin: str, chrome: Any, multi_profile_weapons: list[dict[str, Any]],
) -> None:
    """All published multi-profile source rows must reach their own rendered card."""
    page = chrome.new_page(viewport={"width": 390, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for weapon in multi_profile_weapons:
            slug = weapon["slug"]
            expected = [
                [
                    profile.get("mode") or profile.get("name") or variant["name"],
                    _ammunition_display(profile),
                    _stat_display(profile.get("burst")),
                    _stat_display(profile.get("damage")),
                    _saving_display(profile),
                    profile.get("profile") or "",
                ]
                for variant in weapon["weapon_variants"]
                for profile in variant["profiles"]
            ]
            page.goto(f"{origin}/weapons/{slug}", wait_until="domcontentloaded")
            page.locator("#item-content").wait_for(state="visible", timeout=15000)
            actual = page.locator(".weapon-variant .weapon-profile").evaluate_all(
                """(cards) => cards.map((card) => {
                  const cell = (label) => card.querySelector(
                    '.weapon-statline tbody td[data-label="' + label + '"]'
                  )?.textContent ?? '';
                  const profileRow = [...card.querySelectorAll('.weapon-data-row')].find(
                    row => row.querySelector('.weapon-data-heading')?.textContent === 'Profile'
                  );
                  return [
                    card.querySelector('h4')?.textContent ?? '',
                    cell('Ammunition'), cell('B'), cell('PS'), cell('Saving'),
                    profileRow?.querySelector('.weapon-data-value')?.textContent ?? ''
                  ];
                })"""
            )
            assert actual == expected, (slug, actual, expected)
            source_profiles = [
                profile for variant in weapon["weapon_variants"]
                for profile in variant["profiles"]
            ]
            for card, profile in zip(
                page.locator(".weapon-variant .weapon-profile").all(),
                source_profiles,
                strict=True,
            ):
                parts = profile.get("ammunition_parts")
                if not isinstance(parts, list):
                    continue
                expected_links = []
                for part in parts:
                    reference = part.get("public_reference") or {}
                    href = reference.get("href")
                    if not href and reference.get("catalog") and reference.get("id"):
                        href = f"/{reference['catalog']}/{reference['id']}"
                    if href:
                        expected_links.append((part["text"], href))
                links = card.locator('.weapon-statline td[data-label="Ammunition"] a')
                actual_links = [
                    (link.text_content(), link.get_attribute("href"))
                    for link in links.all()
                ]
                assert actual_links == expected_links, (slug, profile["mode"])
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), slug
        assert not errors, errors
    finally:
        page.close()
