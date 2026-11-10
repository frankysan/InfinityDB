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


@pytest.mark.parametrize(
    ("path", "api_path", "selector", "subject", "detail"),
    [
        ("/armies", "/api/armies", "#army-overview-error-message", "Army overview", False),
        ("/skills", "/api/skills", "#catalog-error-message", "skills", False),
        ("/rules", "/api/rules", "#catalog-error-message", "general rules", False),
        ("/fireteams", "/api/fireteams", "#fireteam-error-message", "Fireteam armies", False),
        ("/scenarios", "/api/scenarios", "#scenario-error-message", "scenarios", False),
        (
            "/scenarios/annihilation", "/api/scenarios/annihilation",
            "#scenario-error-message", "scenario", False,
        ),
        ("/search?q=immunity", "/api/search", "#search-error-message", "search results", False),
        ("/skill-extras", "/api/skill-extras", "#modifier-error-message", "skill modifiers", False),
        ("/orders-aros", "/api/orders-aros", "#matrix-state", "Orders and AROs", False),
        ("/units", "/api/units", "#error-message", "units", False),
        ("/units/fusilier", "/api/units/fusilier", "#unit-status", "Unit", True),
    ],
)
@pytest.mark.parametrize("http_status", [404, 503])
def test_collection_failures_are_player_readable(
    app: Any, browser: Any, path: str, api_path: str, selector: str,
    subject: str, detail: bool, http_status: int,
) -> None:
    """Collection and Unit failures do not expose raw storage error payloads."""

    def failing_app(environ: Any, start_response: Any) -> Any:
        if environ["PATH_INFO"] == api_path:
            start_response(
                "404 Not Found" if http_status == 404 else "503 Service Unavailable",
                [("Content-Type", "application/json")],
            )
            return [b'{"error": "SQLite internal schema compatibility failure"}']
        return app(environ, start_response)

    if detail:
        message = (
            f"This {subject} was not found. Check the link or search for it."
            if http_status == 404
            else f"Could not load this {subject}. Please try again."
        )
    else:
        message = (
            f"The requested {subject} could not be found. Check the selection."
            if http_status == 404
            else f"Could not load {subject}. Please try again."
        )
    page = browser.new_page(viewport={"width": 390, "height": 844})
    route_browser_page(page, failing_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}{path}", wait_until="domcontentloaded")
        page.wait_for_function(
            "([selector, text]) => document.querySelector(selector)?.textContent?.includes(text)",
            arg=[selector, message],
            timeout=30000,
        )
        assert page.locator(selector).inner_text() == message
        if selector in {"#matrix-state", "#unit-status"}:
            assert page.locator(selector).get_attribute("role") == "status"
        else:
            assert page.locator(selector).locator("xpath=..").get_attribute("role") == "alert"
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


@pytest.mark.parametrize(
    ("path", "api_path", "expected"),
    [
        (
            "/scenarios?collection=its-18&revision=bad",
            "/api/scenarios",
            "This scenario collection or revision is not supported. "
            "Open Scenarios to choose another collection.",
        ),
        (
            "/scenarios/annihilation?army_points=300",
            "/api/scenarios/annihilation",
            "This scenario setup is unavailable for the selected publication "
            "and Army Points value. Check the selection.",
        ),
        (
            "/orders-aros?scenario=unsupported",
            "/api/orders-aros",
            "This scenario is not supported by the Orders and AROs reference. Choose another.",
        ),
    ],
)
def test_invalid_context_response_has_actionable_copy(
    app: Any, browser: Any, path: str, api_path: str, expected: str,
) -> None:
    """Only explicit context failures receive context-specific messages."""

    def failing_app(environ: Any, start_response: Any) -> Any:
        if environ["PATH_INFO"] == api_path:
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [b'{"error": "invalid internal source selection key"}']
        return app(environ, start_response)

    page = browser.new_page(viewport={"width": 390, "height": 844})
    route_browser_page(page, failing_app, ORIGIN)
    selector = "#matrix-state" if path.startswith("/orders-aros") else "#scenario-error-message"
    try:
        page.goto(f"{ORIGIN}{path}", wait_until="domcontentloaded")
        page.wait_for_function(
            "([selector, text]) => document.querySelector(selector)?.textContent?.includes(text)",
            arg=[selector, expected],
            timeout=30000,
        )
        assert page.locator(selector).inner_text() == expected
        assert "internal source selection key" not in page.locator("main").inner_text()
    finally:
        page.close()


def test_unavailable_fireteam_army_chart_keeps_selection_guidance(
    app: Any, browser: Any,
) -> None:
    """A bad Army selection has actionable copy, not a source-schema error."""

    def failing_app(environ: Any, start_response: Any) -> Any:
        if environ["PATH_INFO"] == "/api/fireteams" and "army_id=" in environ["QUERY_STRING"]:
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [b'{"error": "unknown internal Army source mapping"}']
        return app(environ, start_response)

    page = browser.new_page(viewport={"width": 390, "height": 844})
    route_browser_page(page, failing_app, ORIGIN)
    try:
        page.goto(f"{ORIGIN}/fireteams", wait_until="domcontentloaded")
        select = page.locator("#fireteam-army")
        page.wait_for_function(
            """() => [...document.querySelector('#fireteam-army').options]
              .some(option => option.value && !option.disabled)""",
            timeout=30000,
        )
        army = select.evaluate(
            "node => [...node.options].find(option => option.value && !option.disabled).value"
        )
        select.select_option(army)
        error = page.locator("#fireteam-error-message")
        error.wait_for(state="visible", timeout=30000)
        assert error.inner_text() == (
            "This Fireteam chart selection is not supported. Choose another Army."
        )
        assert error.locator("xpath=..").get_attribute("role") == "alert"
        assert "internal Army source mapping" not in page.locator("main").inner_text()
    finally:
        page.close()


def test_unsupported_scenario_game_size_remains_specific(
    app: Any, browser: Any,
) -> None:
    """An unsupported selection is not flattened into a transient network error."""
    page = browser.new_page()
    route_browser_page(page, app, ORIGIN)
    try:
        page.goto(f"{ORIGIN}/scenarios/annihilation?army_points=999", wait_until="domcontentloaded")
        page.locator("#scenario-error-message").wait_for(state="visible", timeout=30000)
        assert page.locator("#scenario-error-message").inner_text() == (
            "999 Army Points is not supported by this scenario."
        )
    finally:
        page.close()
