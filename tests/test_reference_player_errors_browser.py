"""Player-facing error and live-region acceptance for shared reference pages."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-browser.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app_from_database_set(ROOT / "data/generated")


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


@pytest.mark.parametrize(
    ("path", "api_path", "selector", "subject", "live_role"),
    [
        ("/skills/immunity", "/api/skills/immunity", "#skill-status", "Skill", "status"),
        (
            "/rules/specialist-troops-standard",
            "/api/rules/specialist-troops-standard",
            "#item-status", "general rule", "status",
        ),
        (
            "/equipment/hacking-device",
            "/api/equipment/hacking-device",
            "#item-status", "item", "status",
        ),
        (
            "/hacking-programs/trinity",
            "/api/hacking-programs/trinity",
            "#item-status", "Hacking Program", "status",
        ),
        ("/glossary", "/api/glossary", "#glossary-error-message", "glossary", "alert"),
    ],
)
@pytest.mark.parametrize("http_status", [404, 503])
def test_reference_failures_hide_backend_errors_and_are_announced(
    app: Any, browser: Any, path: str, api_path: str, selector: str,
    subject: str, live_role: str, http_status: int,
) -> None:
    """Backend diagnostics must not leak into accessible player-facing copy."""

    def failing_app(environ: Any, start_response: Any) -> Any:
        if environ["PATH_INFO"] == api_path:
            start_response(
                "404 Not Found" if http_status == 404 else "503 Service Unavailable",
                [("Content-Type", "application/json")],
            )
            return [b'{"error": "SQLite internal schema compatibility failure"}']
        return app(environ, start_response)

    page = browser.new_page(viewport={"width": 390, "height": 844})
    route_browser_page(page, failing_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    message = (
        f"This {subject} was not found. Check the link or search for it."
        if http_status == 404
        else f"Could not load this {subject}. Please try again."
    )
    try:
        page.goto(f"{ORIGIN}{path}", wait_until="domcontentloaded")
        page.wait_for_function(
            "([selector, text]) => document.querySelector(selector)?.textContent?.includes(text)",
            arg=[selector, message],
            timeout=30000,
        )
        assert page.locator(selector).inner_text() == message
        live_region = "#glossary-error" if live_role == "alert" else selector
        assert page.locator(live_region).get_attribute("role") == live_role
        assert "SQLite" not in page.locator("main").inner_text()

        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 850})
            for theme in ("light", "dark"):
                page.evaluate(
                    "(value) => document.documentElement.dataset.theme = value",
                    theme,
                )
                assert page.locator(selector).is_visible()
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth <= innerWidth + 1"
                ), (path, http_status, width, theme)
        assert not errors, errors
    finally:
        page.close()
