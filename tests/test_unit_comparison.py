"""Unit comparison uses current Army profiles and exact group-local loadouts."""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-comparison.test"


def test_comparison_omits_published_history(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app_from_database_set(ROOT / "data/generated")
    url = f"{ORIGIN}/api/units/minutemen"
    status, _, body = wsgi_response(app, url)
    assert status == 200
    expected = json.loads(body)
    assert "historical_contexts" in expected
    expected.pop("historical_contexts")
    for section in ("general_profiles", "armies"):
        for card in expected[section]:
            card.pop("history", None)

    def unexpected_history(_unit_id):
        pytest.fail("History lookup is not needed for comparison")

    with monkeypatch.context() as context:
        context.setattr(app.database, "unit_history", unexpected_history)
        status, _, omitted = wsgi_response(app, url + "?history=0")
        assert status == 200 and json.loads(omitted) == expected
        status, _, compact = wsgi_response(app, url + "?view=comparison")
        assert status == 200
        assert wsgi_response(app, url + "?view=comparison&history=0")[2] == compact
        unit = json.loads(compact)
        assert "general_profiles" not in unit
        assert "historical_contexts" not in unit
        assert len(compact) < len(omitted)
        assert unit["id"] == expected["id"]
        assert len(unit["armies"]) == len(expected["armies"])
        for army, original in zip(unit["armies"], expected["armies"], strict=True):
            assert army["id"] == original["id"]
            assert army["availability_flags"] == original["availability_flags"]
            assert "history" not in army
            assert len(army["profiles"]) == len(original["profiles"])
            assert len(army["loadouts"]) == len(original["loadouts"])
    assert wsgi_response(app, url)[2] == body
    assert wsgi_response(app, url + "?view=detail")[2] == body
    for query in ("view=", "view=other", "view=comparison&view=detail",
                  "view=comparison&history=1"):
        assert wsgi_response(app, url + "?" + query)[0] == 400


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
                detail_queries = []

                def record_detail(request, detail_queries=detail_queries):
                    url = urlsplit(request.url)
                    if url.path.startswith("/api/units/"):
                        detail_queries.append(parse_qs(url.query))

                page.on("request", record_detail)
                page.goto(f"{ORIGIN}/units/401")
                link = page.locator("#unit-compare-link")
                link.wait_for(state="visible", timeout=30000)
                assert detail_queries and "history" not in detail_queries[-1]
                assert "view" not in detail_queries[-1]
                detail_queries.clear()
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
                assert len(detail_queries) >= 4
                assert all(query.get("history") == ["0"] for query in detail_queries)
                assert all(query.get("view") == ["comparison"] for query in detail_queries)
                page.get_by_role("button", name="Clear Unit").nth(1).click()
                assert table.count() == 0
                assert not errors, errors
                page.close()
        finally:
            browser.close()


def test_compact_comparison_matches_full_browser() -> None:
    api = pytest.importorskip("playwright.sync_api")
    app = create_app_from_database_set(ROOT / "data/generated")

    def full_detail_app(environ, start_response):
        query = parse_qs(environ["QUERY_STRING"], keep_blank_values=True)
        if environ["PATH_INFO"].startswith("/api/units/") and query.get("view") == ["comparison"]:
            query.pop("view")
            environ = {**environ, "QUERY_STRING": urlencode(query, doseq=True)}
        return app(environ, start_response)

    def snapshot(page):
        return page.evaluate("""() => ({
            table: document.querySelector('.comparison-table').outerHTML,
            status: document.querySelector('#comparison-status').textContent,
            selectors: [...document.querySelectorAll('#comparison-selectors select')]
                .map(select => [select.value, [...select.options]
                    .map(option => [option.value, option.textContent, option.disabled])]),
            links: [...document.querySelectorAll('#comparison-selectors a')]
                .map(link => [link.textContent, link.getAttribute('href')]),
        })""")

    def distance(page, inches):
        page.evaluate("""inches => {
            const toggle = document.querySelector('#distance-unit-toggle');
            toggle.checked = inches;
            toggle.dispatchEvent(new Event('change', {bubbles: true}));
        }""", inches)

    with api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            route_browser_page(page, app, ORIGIN)
            page.goto(f"{ORIGIN}/unit-compare")
            target = page.evaluate("""async () => {
                const {shareStateHref} = await import('/static/share-state.js');
                return shareStateHref('/unit-compare', 'comparison', {left: '198', right: '300'});
            }""")
            page.goto(ORIGIN + target)
            table = page.locator(".comparison-table")
            table.wait_for(state="visible", timeout=30000)
            page.locator("#left-loadout").select_option(index=1)
            page.locator("#right-loadout").select_option(index=1)
            saved = page.url
            distance(page, False)
            metric = snapshot(page)
            distance(page, True)
            imperial = snapshot(page)
            assert metric["table"] != imperial["table"]
            page.unroute("**/*")
            route_browser_page(page, full_detail_app, ORIGIN)
            page.goto(saved)
            table.wait_for(state="visible", timeout=30000)
            distance(page, False)
            assert snapshot(page) == metric
            distance(page, True)
            assert snapshot(page) == imperial
        finally:
            page.close()
            browser.close()
