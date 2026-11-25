"""Chromium acceptance of the normal Army overview Reinforcement relationships."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from typing import Any
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page


class _ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def army_app() -> Any:
    root = Path(__file__).resolve().parents[1]
    return create_app(
        root / "data/generated/army.db",
        rules_database_path=root / "data/generated/rules_n5.db",
    )


@pytest.fixture(scope="module")
def origin(army_app: Any) -> Iterator[str]:
    server = make_server(
        "127.0.0.1", 0, army_app, server_class=_ThreadedServer, handler_class=_QuietHandler
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


@contextmanager
def _overview_page(army_app: Any, origin: str, chrome: Any, width: int) -> Iterator[Any]:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, army_app, origin)
    errors: list[str] = []
    failed_requests: list[str] = []
    http_errors: list[str] = []
    api_responses: list[int] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(f"{request.url}: {request.failure}"),
    )
    page.on(
        "response",
        lambda response: http_errors.append(f"{response.status} {response.url}")
        if response.status >= 400 else None,
    )
    page.on(
        "response",
        lambda response: api_responses.append(response.status)
        if "/api/armies" in response.url else None,
    )
    try:
        yield page
        assert not errors, errors
        assert not failed_requests, failed_requests
        assert not http_errors, http_errors
    except Exception as exc:
        exc.add_note(
            f"Army overview at {width}px: url={page.url!r}; "
            f"status={page.locator('#army-overview-error-message').all_text_contents()!r}; "
            f"loading={page.locator('#army-overview-loading').is_visible()}; "
            f"api statuses={api_responses!r}; page errors={errors!r}; "
            f"failed requests={failed_requests!r}; http errors={http_errors!r}"
        )
        raise
    finally:
        page.close()


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
    army_app: Any, origin: str, chrome: Any, width: int
) -> None:
    with _overview_page(army_app, origin, chrome, width) as page:
        response = page.request.get(f"{origin}/api/armies")
        assert response.status == 200
        items = response.json()["items"]
        visible = {army["id"]: army for army in items if _visible(army)}
        assert any(army.get("role") == "reinforcement" for army in visible.values())
        assert any(len(army.get("parent_armies") or []) > 1 for army in visible.values())

        response = page.goto(f"{origin}/armies", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
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
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), width

        link = page.locator(first_link[0]).first
        link.focus()
        assert link.evaluate("(element) => element === document.activeElement")
        target_id = first_link[1][1:]
        page.evaluate("""() => {
            window.overviewMain = document.querySelector('main#main');
            window.overviewNavigations = 0;
            document.addEventListener('infinity:beforenavigation', () => {
                window.overviewNavigations += 1;
            });
        }""")

        def fragment_navigation(action: Callable[[], Any], fragment: str) -> None:
            page.evaluate("""() => {
                window.overviewHashChange = new Promise(resolve => {
                    window.addEventListener('hashchange', () => resolve(true), { once: true });
                });
            }""")
            action()
            page.evaluate("() => window.overviewHashChange")
            assert page.evaluate("window.location.hash") == fragment
            assert page.evaluate("window.overviewNavigations") == 0
            assert page.evaluate("document.querySelector('main#main') === window.overviewMain")

        fragment_navigation(lambda: page.keyboard.press("Enter"), first_link[1])
        page.wait_for_function("(id) => document.activeElement?.id === id", arg=target_id)
        fragment_navigation(page.go_back, "")
        fragment_navigation(page.go_forward, first_link[1])
        page.wait_for_function("(id) => document.activeElement?.id === id", arg=target_id)
        page.locator(f'[id="{target_id}"]').wait_for(state="visible", timeout=5000)


@pytest.mark.parametrize("width", [1440, 320])
def test_army_links_and_filtered_availability_counts(
    army_app: Any, origin: str, chrome: Any, width: int,
) -> None:
    with _overview_page(army_app, origin, chrome, width) as page:
        page.add_init_script(
            "sessionStorage.setItem('infinity-db-reinforcement', 'false')"
        )
        armies = page.request.get(f"{origin}/api/armies").json()["items"]
        section = next(army for army in armies if army["role"] == "reinforcement")
        page.goto(f"{origin}/armies", wait_until="domcontentloaded")
        card = page.locator(f'[id="army-{_slug(section)}"]')
        with page.expect_response(
            lambda response: "/api/units?" in response.url and "counts=prospective" in response.url,
            timeout=60000,
        ) as result:
            card.get_by_role("link", name="Browse units").click()
        payload = result.value.json()
        assert payload["total"] > 0
        page.wait_for_function(
            "() => document.querySelector('#army-count')?.getAttribute('aria-busy') === 'false'"
        )
        params = page.evaluate(
            "async () => Object.fromEntries((await import('/static/share-state.js'))"
            ".readShareState('units').params)"
        )
        assert params["army_id"] == _slug(section)
        assert params["matching_scope"] == "profile"
        assert params["and_filters"] == (
            "skill,equipment,weapon,troop_type,classification,characteristic"
        )
        assert params["reinforcement"] == "1"
        assert page.locator("#army-filter").input_value() == _slug(section)
        counts = payload["army_usage_counts"]
        assert counts[str(section["id"])] == payload["total"]
        total_armies = sum(
            army.get("playable") is not False or (army["unit_count"] or 0) > 0
            for army in armies
        )
        assert page.locator("#army-count").inner_text() == f"{len(counts)} / {total_armies}"
        disclosure = page.locator("#army-count-details")
        breakdown = page.locator("#army-count-shown-breakdown")
        assert not breakdown.is_visible()
        disclosure.locator("summary").click()
        assert breakdown.is_visible()
        role_labels = {
            "main": "Main armies", "sectorial": "Sectorials",
            "non_aligned": "Non-Aligned Armies", "reinforcement": "Reinforcements",
        }
        expected = dict.fromkeys(role_labels.values(), 0)
        for army in armies:
            if str(army["id"]) in counts:
                label = role_labels.get(army["role"], "Other Army availability")
                expected[label] = expected.get(label, 0) + 1
        assert sum(expected.values()) == len(counts)
        assert dict(zip(
            breakdown.locator("dt").all_inner_texts(),
            map(int, breakdown.locator("dd").all_inner_texts()),
            strict=True,
        )) == expected
        assert page.evaluate("""() => {
            const card = document.querySelector('#army-count-details .unit-count-card');
            const rect = card.getBoundingClientRect();
            return rect.left >= 0 && rect.right <= innerWidth + 1;
        }"""), width
        disclosure.locator("summary").click()
        assert page.locator("#army-filter option:checked").inner_text().endswith(
            f"({payload['total']})"
        )
        with page.expect_response(
            lambda response: "/api/units?" in response.url and "counts=prospective" in response.url,
            timeout=60000,
        ) as empty_result:
            page.locator("#unit-search").fill("impossible-unique-unit-name")
        assert empty_result.value.json()["army_usage_counts"] == {}
        page.wait_for_function(
            "total => document.querySelector('#army-count')?.textContent === `0 / ${total}`",
            arg=total_armies,
        )
        assert breakdown.locator("dd").all_text_contents() == ["0"] * 4
        assert page.locator("#army-filter option:checked").inner_text().endswith("(0)")


@pytest.mark.parametrize("width", [1440, 390])
def test_overview_ignores_missing_nonplayable_and_legacy_targets(
    army_app: Any, origin: str, chrome: Any, width: int
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

    with _overview_page(army_app, origin, chrome, width) as page:
        page.route("**/api/armies*", lambda route: route.fulfill(
            status=200, content_type="application/json",
            json={"items": [first, second, reinforcement, excluded, legacy, empty]},
        ))
        response = page.goto(f"{origin}/armies", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        page.locator("#army-overview-groups").wait_for(state="visible", timeout=60000)
        for army_id, expected in (
            (1, ["#army-army-3"]), (2, ["#army-army-3"]),
            (3, ["#army-army-1", "#army-army-2"]),
            (5, []), (6, []),
        ):
            links = page.locator(f'[id="army-army-{army_id}"] .army-overview-relationships a')
            assert [link.get_attribute("href") for link in links.all()] == expected
        assert page.locator('[id="army-army-4"]').count() == 0
        assert page.locator(".army-overview-relationships a").count() == 4
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), width
