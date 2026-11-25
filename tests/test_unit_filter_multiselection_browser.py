"""Browser acceptance for the Unit Explorer categorical multi-select controls."""

from collections.abc import Iterator
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
def app() -> Any:
    root = Path(__file__).resolve().parents[1]
    return create_app(
        root / "data/generated/army.db",
        rules_database_path=root / "data/generated/rules_n5.db",
    )


@pytest.fixture(scope="module")
def origin(app: Any) -> Iterator[str]:
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
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
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


@pytest.mark.parametrize("width", [1280, 390])
def test_unit_multiselect_url_state_keyboard_and_removal(
    app: Any, origin: str, browser: Any, width: int
) -> None:
    page = browser.new_page(
        viewport={"width": width, "height": 900},
        has_touch=width == 390, is_mobile=width == 390,
    )
    route_browser_page(page, app, origin)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        page.goto(f"{origin}/units", wait_until="domcontentloaded")
        control = page.locator(".unit-multi-select").first
        control.locator(".unit-multi-option").first.wait_for(state="attached")
        assert page.locator(".unit-multi-select").count() == 6
        page.wait_for_function(
            "() => [...document.querySelectorAll('.unit-multi-count')].some("
            "(item) => Number(item.textContent.replaceAll(',', '')) > 0)"
        )
        assert page.locator(".unit-multi-count").first.text_content() != "…"
        assert page.locator(".advanced-filter-row > .field > select").evaluate_all(
            "(selects) => selects.map((select) => select.id)"
        ) == [
            "skill-filter",
            "equipment-filter",
            "weapon-filter",
            "troop-type-filter",
            "classification-filter",
            "characteristic-filter",
            "specialist-filter",
        ]
        assert page.locator("#skill-filter").is_hidden()

        if page.locator(".advanced-filters").get_attribute("open") is None:
            page.locator(".advanced-filters > summary").click()
        control.locator("summary").focus()
        control.locator("summary").press("Enter")
        assert control.get_attribute("open") is not None

        available = control.locator(".unit-multi-option:not([hidden]) input")
        first = available.nth(0)
        second = available.nth(1)
        row_height = first.evaluate(
            "(checkbox) => checkbox.closest('label').getBoundingClientRect().height"
        )
        assert 28 <= row_height <= 38, row_height
        if width == 390:
            first.tap()
        else:
            first.focus()
            first.press("Space")
        assert first.is_checked()
        second.check()
        assert "2 selected" in control.locator("summary").inner_text()
        assert page.locator(".unit-multi-chip").count() == 2

        selected = page.evaluate("""async () => {
            const { readShareState } = await import('/static/share-state.js');
            return readShareState('units').params.get('skill_id');
        }""")
        assert selected is not None and len(selected.split(",")) == 2

        page.locator(".unit-multi-chip").first.click()
        assert page.locator(".unit-multi-chip").count() == 1
        page.go_back(wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.unit-multi-chip').length === 2"
        )
        assert not errors, errors
        assert "2 selected" in page.locator(".unit-multi-select summary").first.inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    finally:
        page.close()

def test_unit_multiselect_legacy_invalid_and_empty_links(
    app: Any, origin: str, browser: Any,
) -> None:
    page = browser.new_page(viewport={"width": 1024, "height": 768})
    route_browser_page(page, app, origin)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        catalog = page.request.get(f"{origin}/api/skills").json()["items"]
        legacy_id = catalog[0]["id"]
        legacy_slug = catalog[0]["slug"]

        # Numeric and slug legacy query strings continue working after reload.
        for identifier in (str(legacy_id), legacy_slug):
            page.goto(f"{origin}/units?skill_id={identifier}", wait_until="domcontentloaded")
            page.locator(".unit-multi-chip").first.wait_for(state="attached")
            assert page.locator(".unit-multi-chip").count() == 1
            assert page.locator('.unit-multi-mode input[role="switch"]').first.is_checked()
            page.reload(wait_until="domcontentloaded")
            page.locator(".unit-multi-chip").first.wait_for(state="attached")
            assert page.locator(".unit-multi-chip").count() == 1

        # A malformed legacy selection is ignored rather than sent to the API.
        page.goto(f"{origin}/units?skill_id=aerial,,berserk", wait_until="domcontentloaded")
        page.locator(".unit-multi-option").first.wait_for(state="attached")
        assert page.locator(".unit-multi-chip").count() == 0

        # Syntactically valid but unknown slugs fail closed to empty results.
        page.goto(
            f"{origin}/units?skill_id=does-not-exist,also-missing",
            wait_until="domcontentloaded",
        )
        page.locator("#empty-state").wait_for(state="visible")
        assert page.locator(".unit-multi-chip").count() == 2
        counts = page.locator(".unit-multi-select").first.locator(".unit-multi-count")
        assert counts.count() > 0
        assert all(value == "0" for value in counts.all_text_contents())
        assert "0 matching Units" in page.locator(
            ".unit-multi-option input"
        ).first.get_attribute("aria-label")
        assert not errors, errors
    finally:
        page.close()

def test_contextual_counts_accessible_loading_and_failure(
    app: Any, origin: str, browser: Any,
) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 820}, has_touch=True, is_mobile=True)
    route_browser_page(page, app, origin)
    try:
        page.goto(f"{origin}/units", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => [...document.querySelectorAll('.unit-multi-count')].some("
            "(item) => Number(item.textContent.replaceAll(',', '')) > 0)"
        )
        page.locator(".advanced-filters > summary").click()
        control = page.locator(".unit-multi-select").first
        control.locator("summary").click()
        checkbox = control.locator(".unit-multi-option input").first
        assert "matching Unit" in checkbox.get_attribute("aria-label")
        assert control.locator(".unit-multi-choices").get_attribute("aria-busy") == "false"
        page.route("**/api/units?*", lambda route: route.abort())
        snapshot = checkbox.evaluate("""(input) => {
            const count = input.closest("label").querySelector(".unit-multi-count");
            const main = document.querySelector("#unit-count");
            const previous = { option: count.textContent, main: main.textContent };
            input.click();
            return {
                previous, option: count.textContent, main: main.textContent,
                label: input.getAttribute("aria-label"),
            };
        }""")
        assert "count loading" in snapshot["label"]
        assert snapshot["option"] == snapshot["previous"]["option"]
        assert snapshot["main"] == snapshot["previous"]["main"]
        page.locator("#error-state").wait_for(state="visible")
        assert "count unavailable" in checkbox.get_attribute("aria-label")
        assert control.locator(".unit-multi-choices").get_attribute("aria-busy") == "false"
    finally:
        page.close()


@pytest.mark.parametrize("width", [1280, 390])
def test_and_or_switch_preserves_share_state(
    app: Any, origin: str, browser: Any, width: int,
) -> None:
    page = browser.new_page(
        viewport={"width": width, "height": 850},
        has_touch=width == 390,
        is_mobile=width == 390,
    )
    route_browser_page(page, app, origin)
    try:
        page.goto(f"{origin}/units", wait_until="domcontentloaded")
        page.locator(".unit-multi-option").first.wait_for(state="attached")
        switches = page.locator('.unit-multi-mode input[role="switch"]')
        assert switches.count() == 6
        assert all(switch.is_enabled() for switch in switches.all())
        assert all(not switch.is_checked() for switch in switches.all())
        assert switches.first.locator("xpath=..").text_content().strip() == "ANDOR"
        page.locator(".advanced-filters > summary").click()
        control = page.locator(".unit-multi-select").first
        toggle = switches.first
        toggle.check()
        assert toggle.is_checked()
        toggle.uncheck()
        control.locator("summary").click()
        options = control.locator(".unit-multi-option:not([hidden]) input")
        options.nth(0).check()
        assert toggle.is_enabled()
        toggle.check()
        assert toggle.is_checked()
        options.nth(1).check()
        assert toggle.is_checked()
        assert page.evaluate("""async () => {
            const { readShareState } = await import('/static/share-state.js');
            return readShareState('units').params.get('and_filters');
        }""") == "equipment,weapon,troop_type,classification,characteristic"
        page.reload(wait_until="domcontentloaded")
        page.locator(".unit-multi-option").first.wait_for(state="attached")
        toggle = page.locator('.unit-multi-mode input[role="switch"]').first
        assert toggle.is_checked()
        page.go_back(wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.unit-multi-chip').length === 1"
        )
        assert toggle.is_checked()
        assert toggle.is_enabled()
        page.goto(f"{origin}/units", wait_until="domcontentloaded")
        page.locator(".unit-multi-option").first.wait_for(state="attached")
        toggle = page.locator('.unit-multi-mode input[role="switch"]').first
        assert not toggle.is_checked()
        assert toggle.is_enabled()
    finally:
        page.close()


def test_contextual_and_baseline_counts_control_menu_visibility(
    app: Any, origin: str, browser: Any,
) -> None:
    page = browser.new_page(viewport={"width": 1024, "height": 800})
    route_browser_page(page, app, origin)
    try:
        page.goto(f"{origin}/units", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => [...document.querySelectorAll('.unit-multi-count')].some("
            "(item) => Number(item.textContent.replaceAll(',', '')) > 0)"
        )
        controls = page.locator(".unit-multi-select")
        assert controls.count() == 6
        for index in range(6):
            counts = controls.nth(index).locator(".unit-multi-count")
            assert counts.count() > 0
            assert "…" not in counts.all_text_contents()

        # Hide options absent from the Settings-adjusted unfiltered population.
        assert controls.first.locator(".unit-multi-option[hidden]").count() > 0

        # Cube/2.0 are Characteristic identities, not Equipment menu options.
        equipment = controls.nth(1)
        assert equipment.locator('input[value="cube"]').is_hidden()
        assert equipment.locator('input[value="cube-2"]').is_hidden()
        characteristics = controls.nth(5)
        visible_characteristics = characteristics.locator(
            ".unit-multi-option:not([hidden])"
        ).all_text_contents()
        assert any("Cube" in name for name in visible_characteristics)
        assert any("Cube 2.0" in name for name in visible_characteristics)

        # A currently zero-use option stays selectable.
        page.goto(
            f"{origin}/units?search=impossible-unique-unit-name",
            wait_until="domcontentloaded",
        )
        page.locator("#empty-state").wait_for(state="visible")
        page.locator(".advanced-filters > summary").click()
        skill_control = page.locator(".unit-multi-select").first
        skill_control.locator("summary").click()
        first_visible = skill_control.locator(".unit-multi-option:not([hidden])").first
        assert "unit-multi-zero-use" in first_visible.get_attribute("class")
        first_visible.locator("input").check()
        assert page.locator(".unit-multi-chip").count() == 1
        assert "0 matching Units" in first_visible.locator("input").get_attribute(
            "aria-label"
        )
    finally:
        page.close()


def test_individual_filter_clear_resets_search_and_keeps_counts_clear(
    app: Any, origin: str, browser: Any,
) -> None:
    page = browser.new_page(viewport={"width": 1024, "height": 800})
    route_browser_page(page, app, origin)
    try:
        page.goto(f"{origin}/units", wait_until="domcontentloaded")
        control = page.locator(".unit-multi-select").first
        control.locator(".unit-multi-option").first.wait_for(state="attached")
        if page.locator(".advanced-filters").get_attribute("open") is None:
            page.locator(".advanced-filters > summary").click()
        control.locator("summary").click()
        search = control.locator('input[type="search"]')
        clear = control.locator(".unit-multi-clear")
        assert clear.is_disabled()

        search.fill("no-skill-has-this-name")
        assert clear.is_enabled()
        assert control.locator(".unit-multi-option:not([hidden])").count() == 0
        clear.click()
        assert search.input_value() == ""
        assert clear.is_disabled()
        assert control.locator(".unit-multi-option:not([hidden])").count() > 0

        choice = control.locator(".unit-multi-option:not([hidden]) input").first
        choice.check()
        assert page.locator(".unit-multi-chip").count() == 1
        search.fill("no-skill-has-this-name")
        clear.click()
        assert search.input_value() == ""
        assert page.locator(".unit-multi-chip").count() == 0
        assert control.locator(".unit-multi-option:not([hidden])").count() > 0

        # The reserved scrollbar gutter must leave room for visible usage counts.
        row = control.locator(".unit-multi-option:not([hidden])").first
        count_box = row.locator(".unit-multi-count").bounding_box()
        choices_box = control.locator(".unit-multi-choices").bounding_box()
        assert count_box is not None and choices_box is not None
        assert count_box["x"] + count_box["width"] < (
            choices_box["x"] + choices_box["width"] - 8
        )
    finally:
        page.close()


def test_specialist_menu_has_only_unique_current_choices(
    app: Any, origin: str, browser: Any,
) -> None:
    page = browser.new_page(viewport={"width": 1024, "height": 800})
    route_browser_page(page, app, origin)
    try:
        page.goto(f"{origin}/units", wait_until="domcontentloaded")
        assert "View matches optional-unit Settings in the Settings menu." in (
            page.locator("#optional-unit-context").inner_text()
        )
        options = page.locator("#specialist-filter option").evaluate_all(
            "(items) => items.map((item) => [item.value, item.textContent])"
        )
        assert options == [["", "Any"], ["standard", "Standard set"]]
        page.goto(f"{origin}/units?specialist=domination", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#specialist-filter').value === 'standard'"
        )
        assert page.locator("#specialist-filter").input_value() == "standard"
    finally:
        page.close()


@pytest.mark.parametrize("width", [1280, 390])
def test_matching_scope_prospective_count_share_state_and_history(
    app: Any, origin: str, browser: Any, width: int,
) -> None:
    page = browser.new_page(
        viewport={"width": width, "height": 900},
        has_touch=width == 390, is_mobile=width == 390,
    )
    route_browser_page(page, app, origin)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        page.goto(
            f"{origin}/units?skill_id=berserk&and_filters=skill&matching_scope=profile",
            wait_until="domcontentloaded",
        )
        page.wait_for_function(
            "() => document.querySelector('#unit-count')?.getAttribute('aria-busy') === 'false'"
        )
        selector = page.locator("#matching-scope-filter")
        assert selector.input_value() == "profile"
        control = page.locator(".unit-multi-select").first
        control.locator("summary").click()
        engineer = control.locator('input[value="engineer"]')
        engineer.wait_for(state="attached")
        prospective = engineer.locator("xpath=..").locator(".unit-multi-count").text_content()
        assert prospective is not None
        predicted = int(prospective.replace(",", ""))
        engineer.check()
        page.wait_for_function(
            "() => document.querySelector('#unit-count')?.getAttribute('aria-busy') === 'false'"
        )
        shown = page.locator("#unit-count").text_content()
        assert shown is not None
        assert int(shown.split(" / ")[0].replace(",", "")) == predicted

        selector.select_option("loadout")
        page.wait_for_function(
            "() => document.querySelector('#unit-count')?.getAttribute('aria-busy') === 'false'"
        )
        assert "different profiles" in page.locator("#matching-scope-description").inner_text()
        assert selector.input_value() == "loadout"
        page.go_back()
        page.wait_for_function(
            "() => document.querySelector('#matching-scope-filter')?.value === 'profile'"
        )
        assert selector.input_value() == "profile"

        page.goto(f"{origin}/units?skill_id=berserk", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#unit-count')?.getAttribute('aria-busy') === 'false'"
        )
        assert selector.input_value() == ""
        assert "previous matching behavior" in (
            page.locator("#matching-scope-description").inner_text()
        )
        selector.select_option("unit")
        assert selector.input_value() == "unit"
        assert not errors
    finally:
        page.close()

@pytest.mark.parametrize(
    ("filter_name", "slug", "control_index"),
    [
        ("skill_id", "bs-attack", 0),
        ("weapon_id", "adhesive-launcher-rifle", 2),
    ],
)


def test_selected_option_count_equals_matching_unit_count(
    app: Any, origin: str, browser: Any,
    filter_name: str, slug: str, control_index: int,
) -> None:
    page = browser.new_page(viewport={"width": 1024, "height": 800})
    route_browser_page(page, app, origin)
    try:
        page.goto(
            f"{origin}/units?{filter_name}={slug}&mercs=1&specops=1&teamops=1&reinforcement=0",
            wait_until="domcontentloaded",
        )
        page.wait_for_function(
            "() => document.querySelector('#unit-count')?.getAttribute('aria-busy') === 'false'"
        )
        displayed_total = page.locator("#unit-count").text_content()
        assert displayed_total is not None
        selected_option = page.locator(".unit-multi-select").nth(control_index).locator(
            f'input[value="{slug}"]'
        )
        selected_option.wait_for(state="attached")
        displayed_count = selected_option.locator(
            "xpath=.."
        ).locator(".unit-multi-count").text_content()
        assert displayed_count is not None
        assert int(displayed_count.replace(",", "")) == int(
            displayed_total.split(" / ")[0].replace(",", "")
        )
    finally:
        page.close()


@pytest.mark.parametrize("width", [1280, 390])
def test_bit_and_kiss_includes_one_linked_peripheral_per_loadout(
    app: Any, origin: str, browser: Any, width: int,
) -> None:
    page = browser.new_page(
        viewport={"width": width, "height": 900},
        is_mobile=width == 390, has_touch=width == 390,
    )
    route_browser_page(page, app, origin)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{origin}/units/bit-and-kiss", wait_until="domcontentloaded")
        page.locator("#unit-content").wait_for(state="visible")
        combined = page.locator(".army-profile").first
        if combined.get_attribute("open") is None:
            combined.locator("summary").click()
        bit_loadouts = combined.locator(".loadout-table").first
        assert bit_loadouts.get_by_text("Included peripherals", exact=True).count() == 2
        assert bit_loadouts.get_by_text("Attached peripherals", exact=True).count() == 0
        assert bit_loadouts.get_by_text("Includes", exact=True).count() == 0
        assert bit_loadouts.get_by_role("link", name="KISS! (Repeater)").count() == 1
        assert bit_loadouts.get_by_role("link", name="KISS!", exact=True).count() == 1
        # The distinct KISS Trooper profile and its own loadouts remain visible.
        assert combined.locator(".profile-details-table").count() == 2
        assert combined.locator(".loadout-table").count() == 2
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    finally:
        page.close()


@pytest.mark.parametrize("width", [1280, 390])
def test_extended_profiles_show_plain_text_capabilities(
    app: Any, origin: str, browser: Any, width: int,
) -> None:
    page = browser.new_page(
        viewport={"width": width, "height": 900},
        has_touch=width == 390, is_mobile=width == 390,
    )
    route_browser_page(page, app, origin)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    try:
        with page.expect_response(
            lambda response: "/api/units?" in response.url
            and "extended=1" in response.url and response.status == 200
        ) as response_info:
            page.goto(f"{origin}/units?search=fusiliers&extended=1", wait_until="domcontentloaded")
        expected = [
            general
            for unit in response_info.value.json()["items"]
            for general in unit["general_profiles"]
        ]
        profile = page.locator(".unit-extended-profile").first
        try:
            profile.wait_for(state="visible", timeout=10000)
        except Exception:
            pytest.fail(
                f"Extended results missing: {errors}; {page.locator('body').inner_text()[-2000:]}"
            )
        assert page.locator("#extended-results").is_checked()
        capabilities = profile.locator(".unit-extended-capability-section")
        assert capabilities.is_visible()
        assert "Weapons:" in capabilities.inner_text()
        assert "Shared by all variants of this profile" in capabilities.inner_text()
        assert "Combi Rifle" not in capabilities.inner_text()
        assert page.locator(".unit-extended-profile").count() == len(expected)
        assert [
            heading.text_content()
            for heading in page.locator(".unit-extended-profile-heading > strong").all()
        ] == [f"General profile — {general['display_name']}" for general in expected]
        assert page.locator(".unit-extended-loadout").count() == 0
        assert capabilities.locator("a").count() == 0
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    finally:
        page.close()


@pytest.mark.parametrize("scope", ["profile", "loadout"])
@pytest.mark.parametrize("width", [1024, 390])
def test_matching_context_disclosure_does_not_navigate(
    app: Any, origin: str, browser: Any, scope: str, width: int,
) -> None:
    page = browser.new_page(
        viewport={"width": width, "height": 800},
        is_mobile=width == 390, has_touch=width == 390,
    )
    route_browser_page(page, app, origin)
    try:
        page.goto(
            f"{origin}/units?skill_id=berserk&matching_scope={scope}",
            wait_until="domcontentloaded",
        )
        summary = page.locator(".unit-match-contexts summary").first
        summary.wait_for(state="visible")
        assert "Matched:" in summary.inner_text()
        url = page.url
        if width == 390:
            summary.tap()
        else:
            summary.click()
        assert page.url == url
        assert summary.locator("xpath=..").get_attribute("open") is not None
        items = page.locator(".unit-match-contexts li")
        assert items.count() > 0
        details = page.locator(".unit-match-context-details").first
        assert details.is_visible()
        assert any(
            category in details.inner_text()
            for category in ("pts", "SWC", "Weapons:", "Equipment:", "Skills:")
        )
        items.first.click()
        assert page.url == url
        summary.focus()
        summary.press("Enter")
        assert summary.locator("xpath=..").get_attribute("open") is None
        summary.press("Enter")
        assert summary.locator("xpath=..").get_attribute("open") is not None
        assert page.url == url
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    finally:
        page.close()
