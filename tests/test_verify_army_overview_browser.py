"""Chromium acceptance of the normal Army overview Reinforcement relationships."""

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
        "127.0.0.1", 0, app, server_class=_ThreadedServer, handler_class=_QuietHandler
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


def _slug(army: dict[str, Any]) -> str:
    return str(army.get("public_slug") or army.get("slug") or army["id"])


def _visible(army: dict[str, Any]) -> bool:
    return army.get("playable") is not False or bool(army.get("legacy"))


def _expected(
    army: dict[str, Any], by_id: dict[int, dict[str, Any]]
) -> list[tuple[str, str]]:
    if army.get("legacy") or army.get("playable") is False:
        return []
    references = (
        army.get("parent_armies")
        if army.get("role") == "reinforcement"
        else army.get("reinforcement_sections")
    ) or []
    targets = [
        by_id[ref["id"]]
        for ref in references
        if ref.get("id") in by_id
        and by_id[ref["id"]].get("playable") is not False
        and not by_id[ref["id"]].get("legacy")
    ]
    return [(f"#army-{_slug(target)}", target["name"]) for target in targets]


@pytest.mark.parametrize("width", [1440, 390])
def test_pinned_army_overview_api_links_and_keyboard_navigation(
    origin: str, chrome: Any, width: int
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        response = page.request.get(f"{origin}/api/armies")
        assert response.status == 200
        items = response.json()["items"]
        visible = {army["id"]: army for army in items if _visible(army)}
        assert any(army.get("role") == "reinforcement" for army in visible.values())
        assert any(len(army.get("parent_armies") or []) > 1 for army in visible.values())

        page.goto(f"{origin}/armies", wait_until="domcontentloaded")
        page.locator("#army-overview-groups").wait_for(state="visible", timeout=60000)
        assert page.locator(".army-overview-card").count() == len(visible)
        tested_links = 0
        first_link: tuple[str, str] | None = None
        for army in visible.values():
            card = page.locator(f'[id="army-{_slug(army)}"]')
            assert card.count() == 1, (width, army["name"])
            links = card.locator(".army-overview-relationships a")
            expected = _expected(army, visible)
            actual = [(link.get_attribute("href"), link.text_content()) for link in links.all()]
            assert actual == expected, (width, army["name"], actual, expected)
            tested_links += len(expected)
            if expected and first_link is None:
                selector = f'[id="army-{_slug(army)}"] .army-overview-relationships a'
                first_link = (selector, expected[0][0])
        assert tested_links > 0
        assert first_link is not None
        assert not errors, errors
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), width

        link = page.locator(first_link[0]).first
        link.focus()
        assert link.evaluate("(element) => element === document.activeElement")
        page.keyboard.press("Enter")
        target_id = first_link[1][1:]
        page.wait_for_function("(id) => document.activeElement?.id === id", arg=target_id)
        assert page.evaluate("window.location.hash") == first_link[1]
        page.locator(f'[id="{target_id}"]').wait_for(state="visible", timeout=5000)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_overview_ignores_missing_nonplayable_and_legacy_targets(
    origin: str, chrome: Any, width: int
) -> None:
    def army(army_id: int, name: str, role: str, *, playable: bool = True,
             legacy: bool = False) -> dict[str, Any]:
        return {
            "id": army_id, "name": name, "slug": f"army-{army_id}",
            "role": role, "playable": playable, "legacy": legacy,
            "unit_count": 0,
        }

    first = army(1, "First main", "main")
    second = army(2, "Second main", "main")
    reinforcement = army(3, "Shared section", "reinforcement")
    excluded = army(4, "Nonplayable", "main", playable=False)
    legacy = army(5, "Legacy", "main", playable=False, legacy=True)
    empty = army(6, "No links", "main")
    first["reinforcement_sections"] = [{"id": i} for i in (3, 4, 5, 999)]
    second["reinforcement_sections"] = [{"id": 3}]
    reinforcement["parent_armies"] = [{"id": i} for i in (1, 2, 4, 5, 999)]
    legacy["reinforcement_sections"] = [{"id": 3}]

    page = chrome.new_page(viewport={"width": width, "height": 900})
    errors: list[str] = []
    failed_requests: list[str] = []
    api_responses: list[int] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(f"{request.url}: {request.failure}"),
    )
    page.on(
        "response",
        lambda response: api_responses.append(response.status)
        if "/api/armies" in response.url else None,
    )
    page.route("**/api/armies*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        json={"items": [first, second, reinforcement, excluded, legacy, empty]},
    ))
    try:
        page.goto(f"{origin}/armies", wait_until="domcontentloaded")
        try:
            page.locator("#army-overview-groups").wait_for(
                state="visible", timeout=60000
            )
        except Exception as exc:
            message = page.locator("#army-overview-error-message").inner_text()
            raise AssertionError(
                f"Injected Army overview at {width}px never rendered; "
                f"status={message!r}; api statuses={api_responses!r}; "
                f"page errors={errors!r}; failed requests={failed_requests!r}"
            ) from exc
        for army_id, expected in (
            (1, ["#army-army-3"]), (2, ["#army-army-3"]),
            (3, ["#army-army-1", "#army-army-2"]),
            (5, []), (6, []),
        ):
            links = page.locator(f'[id="army-army-{army_id}"] .army-overview-relationships a')
            assert [link.get_attribute("href") for link in links.all()] == expected
        assert page.locator('[id="army-army-4"]').count() == 0
        assert page.locator(".army-overview-relationships a").count() == 4
        assert not errors, errors
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), width
    finally:
        page.close()
