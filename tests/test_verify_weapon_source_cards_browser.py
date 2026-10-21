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
