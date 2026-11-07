"""Small cross-engine release pilot; separate from the full Chromium acceptance suite.

Set INFINITYDB_CROSS_BROWSER_ENGINE to chromium, firefox, webkit or msedge.
The ordinary source suite does not require Playwright or browser downloads.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from typing import Any
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db.web import create_app

ENGINE = os.environ.get("INFINITYDB_CROSS_BROWSER_ENGINE", "")
ENGINES = ("chromium", "firefox", "webkit", "msedge")
ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "local/cross-browser-compatibility"

if ENGINE and ENGINE not in ENGINES:
    raise ValueError(f"Unsupported cross-browser engine: {ENGINE!r}")

pytestmark = pytest.mark.skipif(
    not ENGINE, reason="Cross-browser pilot requires an explicitly selected engine"
)


class _ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def origin() -> Iterator[str]:
    """Serve the exact tracked release-pair inputs, not a fresh curated export."""
    app = create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
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
def browser() -> Iterator[Any]:
    """Missing Playwright or the selected browser is an error, never a silent skip."""
    try:
        sync_api = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        pytest.fail(f"Cross-browser pilot requires Playwright: {exc}", pytrace=False)
    with sync_api.sync_playwright() as driver:
        browser_type = driver.chromium if ENGINE == "msedge" else getattr(driver, ENGINE)
        options = {"channel": "msedge"} if ENGINE == "msedge" else {}
        instance = browser_type.launch(**options)
        print(
            f"Cross-browser pilot: engine={ENGINE}, "
            f"browser={instance.version}, platform={os.name}",
            flush=True,
        )
        try:
            yield instance
        finally:
            instance.close()


def _exercise(page: Any, origin: str, journey: str) -> None:
    if journey == "navigation":
        page.goto(f"{origin}/", wait_until="domcontentloaded")
        page.locator("main a[href='/units']").first.press("Enter")
        page.wait_for_url(f"{origin}/units")
        page.wait_for_function(
            "() => document.activeElement === document.querySelector('main#main')"
        )
        assert page.locator("#page-navigation-status").get_attribute("aria-live") == "polite"
        page.go_back(wait_until="domcontentloaded")
        page.wait_for_url(f"{origin}/")
    elif journey == "rule":
        page.goto(f"{origin}/skills/stealth", wait_until="domcontentloaded")
        card = page.locator("#rule-skill-stealth")
        card.wait_for(state="visible")
        assert card.locator(".rules-source-citations a").count() >= 1
    elif journey == "fragment":
        page.goto(
            f"{origin}/weapons/ap-mine#rule-weapon-mines",
            wait_until="domcontentloaded",
        )
        card = page.locator("#item-content article#rule-weapon-mines")
        card.wait_for(state="visible")
        assert card.count() == 1
        assert page.evaluate("location.hash") == "#rule-weapon-mines"
    elif journey == "unit":
        page.goto(f"{origin}/units/dragoes", wait_until="domcontentloaded")
        page.locator("#unit-content").wait_for(state="visible")
        page.locator(".general-profile").first.wait_for(state="attached")
    elif journey == "scenario":
        page.goto(
            f"{origin}/scenarios/domination?army_points=150",
            wait_until="domcontentloaded",
        )
        select = page.locator("#scenario-army-points")
        select.wait_for(state="visible")
        select.select_option("350")
        page.wait_for_function(
            """() => document.querySelector('#scenario-content')?.hidden === false
            && document.querySelector('.scenario-setup-card .scenario-facts dd')
               ?.textContent?.trim() === '350'
            && document.querySelector('svg.scenario-map') !== null"""
        )
        assert page.locator(".scenario-citations a").count() >= 1
        assert page.locator(".scenario-source-issue").count() == 1
    elif journey == "faq":
        page.goto(f"{origin}/scenarios/supplies", wait_until="domcontentloaded")
        page.locator(".faq-rulings .faq-ruling").first.wait_for(state="visible")
        assert page.locator(".faq-publication-source a").count() >= 1
    elif journey == "notice":
        page.goto(f"{origin}/", wait_until="domcontentloaded")
        details = page.locator("main .page-footer-notice")
        details.wait_for(state="visible")
        summary = details.locator("summary")
        assert details.evaluate("(node) => node.open")
        if page.viewport_size["width"] <= 390:
            summary.tap()
        else:
            summary.focus()
            summary.press("Enter")
        assert not details.evaluate("(node) => node.open")
        summary.focus()
        summary.press("Enter")
        assert details.evaluate("(node) => node.open")
    else:
        raise AssertionError(f"Unknown browser journey: {journey}")


@pytest.mark.parametrize("width", (1440, 390))
@pytest.mark.parametrize(
    "journey", ("navigation", "rule", "fragment", "unit", "scenario", "faq", "notice")
)
def test_critical_browser_journey(browser: Any, origin: str, width: int, journey: str) -> None:
    """Reuse one portable browser contract for all four CI engine/platform jobs."""
    context = browser.new_context(
        viewport={"width": width, "height": 844},
        has_touch=width <= 390,
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    errors: list[str] = []
    failed_requests: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(f"{request.url}: {request.failure}")
        if "/api/" in request.url and "ERR_ABORTED" not in str(request.failure)
        else None,
    )
    try:
        response = context.request.get(f"{origin}/api/version", timeout=15000)
        assert response.status == 200
        _exercise(page, origin, journey)
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), f"{ENGINE} {journey} {width}px: page-level overflow"
        assert not errors, errors
        assert not failed_requests, failed_requests
    except Exception:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        prefix = ARTIFACTS / f"{ENGINE}-{journey}-{width}"
        try:
            page.screenshot(path=str(prefix) + ".png", full_page=True, timeout=5000)
        except Exception:
            pass
        context.tracing.stop(path=str(prefix) + ".zip")
        raise
    else:
        context.tracing.stop()
    finally:
        context.close()
