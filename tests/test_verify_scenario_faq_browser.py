"""Normal Chromium scenario-page acceptance for scoped N5 FAQ clarifications."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-browser.test"
@pytest.fixture(scope="module")
def scenario_app(tmp_path_factory: pytest.TempPathFactory) -> Callable[..., Any]:
    """Use freshly exported curated rules; the checked-in rules DB may lag."""
    rules_path = tmp_path_factory.mktemp("scenario-faq-browser") / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated"), rules_path)
    return create_app(ROOT / "data/generated/infinity.db", rules_database_path=rules_path)


@pytest.fixture(scope="module")
def chrome() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield browser
        finally:
            browser.close()


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("response", ["empty", "error"])
def test_core_scenario_catalog_controlled_empty_and_error_states(
    scenario_app: Callable[..., Any], chrome: Any, width: int, response: str,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    if response == "empty":
        page.route(
            "**/api/scenarios*",
            lambda route: route.fulfill(
                status=200, content_type="application/json",
                body='{"items":[],"collections":[]}',
            ),
        )
    else:
        page.route(
            "**/api/scenarios*",
            lambda route: route.fulfill(
                status=503, content_type="application/json",
                body='{"error":"Controlled unavailable publication"}',
            ),
        )
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/scenarios", wait_until="domcontentloaded")
        expected = page.locator(
            "#scenario-empty" if response == "empty" else "#scenario-error"
        )
        expected.wait_for(state="visible", timeout=30000)
        assert page.locator("#scenario-grid").is_hidden()
        assert not page.locator("#scenario-loading").is_visible()
        heading = (
            "No scenarios available" if response == "empty"
            else "Scenarios could not be loaded"
        )
        assert heading in expected.inner_text()
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_domination_scoped_rule_link_keyboard_navigation_restores_selection(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(
            f"{ORIGIN}/scenarios/domination?army_points=350",
            wait_until="domcontentloaded",
        )
        reference = page.locator(
            '.scenario-rules a.maintained-reference[href="/skills/shasvastii"]'
        ).first
        reference.wait_for(state="visible", timeout=30000)
        reference.focus()
        assert reference.evaluate("(node) => document.activeElement === node")
        reference.press("Enter")
        page.wait_for_url(f"{ORIGIN}/skills/shasvastii", timeout=30000)
        page.locator("#rule-skill-shasvastii").wait_for(
            state="visible", timeout=30000,
        )
        page.go_back(wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.querySelector('#scenario-content')?.hidden === false
              && document.querySelector('.scenario-setup-card .scenario-facts dd')
                ?.textContent?.trim() === '350'""",
            timeout=30000,
        )
        assert page.locator("#scenario-army-points").input_value() == "350"
        assert page.locator("#scenario-source-issue-350-point-swc").is_visible()
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_domination_rapid_size_changes_leave_only_final_configuration(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    """Browser changes may overlap API and SVG requests; latest size wins."""
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(
            f"{ORIGIN}/scenarios/domination?army_points=150",
            wait_until="domcontentloaded",
        )
        page.wait_for_function(
            "() => document.querySelector('.scenario-setup-card .scenario-facts dd')"
            "?.textContent === '150'",
            timeout=30000,
        )
        page.evaluate(
            """() => {
              const selector = document.querySelector('#scenario-army-points');
              for (const points of ['200', '250', '300', '400', '350']) {
                selector.value = points;
                selector.dispatchEvent(new Event('change', { bubbles: true }));
              }
            }"""
        )
        page.wait_for_function(
            """() => document.querySelector('#scenario-content')?.hidden === false
              && document.querySelector('.scenario-setup-card .scenario-facts dd')
                ?.textContent?.trim() === '350'
              && document.querySelector('svg.scenario-map') !== null""",
            timeout=30000,
        )
        assert page.locator("#scenario-army-points").input_value() == "350"
        assert page.locator(".scenario-setup-card .scenario-fact").nth(
            1
        ).locator("dd").inner_text().splitlines()[0] == "6"
        assert page.locator("svg.scenario-map").get_attribute("viewBox") == (
            "0 0 48 48"
        )
        assert page.locator("#scenario-source-issue-350-point-swc").is_visible()
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('.scenario-setup-card .scenario-facts dd')"
            "?.textContent === '350'",
            timeout=30000,
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_core_scenario_detail_error_recovers_after_valid_size_choice(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    pattern = "**/api/scenarios/domination*"
    def unavailable(route: Any) -> None:
        route.fulfill(
            status=503, content_type="application/json",
            body='{"error":"Controlled missing scenario"}',
        )
    page.route(pattern, unavailable)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(
            f"{ORIGIN}/scenarios/domination?army_points=350",
            wait_until="domcontentloaded",
        )
        panel = page.locator("#scenario-error")
        panel.wait_for(state="visible", timeout=30000)
        assert "Scenario could not be loaded" in panel.inner_text()
        assert page.locator("#scenario-content").is_hidden()
        page.unroute(pattern, unavailable)
        page.locator("#scenario-army-points").select_option("300")
        page.wait_for_function(
            """() => document.querySelector('#scenario-content')?.hidden === false
              && document.querySelector('.scenario-setup-card .scenario-facts dd')
                ?.textContent?.trim() === '300'""",
            timeout=30000,
        )
        assert panel.is_hidden()
        page.locator("svg.scenario-map").wait_for(state="visible", timeout=30000)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390, 320])
def test_core_scenario_catalog_keyboard_soft_navigation_and_back(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    """Normal-mode scenario selection preserves the catalog and back stack."""
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/scenarios", wait_until="domcontentloaded")
        for slug in ("annihilation", "domination", "supplies", "firefight"):
            catalog = page.locator("#scenario-grid")
            catalog.wait_for(state="visible", timeout=30000)
            assert page.locator(".scenario-card").count() == 4
            link = page.locator(f'#scenario-grid a[href="/scenarios/{slug}"]')
            assert link.count() == 1
            link.focus()
            assert link.evaluate("(node) => document.activeElement === node")
            link.press("Enter")
            page.wait_for_url(f"{ORIGIN}/scenarios/{slug}*", timeout=30000)
            page.wait_for_function(
                """() => document.querySelector('#scenario-content')?.hidden === false
                  && document.querySelector('.scenario-setup-card .scenario-facts dd')
                    ?.textContent?.trim() === '300'""",
                timeout=30000,
            )
            assert page.locator("#scenario-army-points").input_value() == "300"
            assert page.locator(".scenario-objective").count() > 0
            page.go_back(wait_until="domcontentloaded")
            page.locator("#scenario-grid").wait_for(state="visible", timeout=30000)
            assert page.locator(".scenario-card").count() == 4
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= innerWidth + 1"
            ), (width, slug)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize(
    ("slug", "source_page", "swc_350", "objective_count", "rule_count", "has_minimum"),
    [
        ("annihilation", 150, 7, 3, 1, False),
        ("domination", 151, 6, 2, 4, True),
        ("supplies", 153, 7, 3, 5, True),
        ("firefight", 155, 7, 4, 4, False),
    ],
)
def test_all_24_core_scenario_setups_render_source_backed_browser_contract(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
    slug: str, source_page: int, swc_350: int, objective_count: int,
    rule_count: int, has_minimum: bool,
) -> None:
    """Direct loads and subsequent size changes reach the player-facing DOM.

    Source-chart values are pinned separately by test_scenario_catalog.py.
    These checks ensure they actually reach ordinary browser presentation.
    """
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    sizes = [
        (150, 3, 24, 32, 38), (200, 4, 32, 48, 50),
        (250, 5, 32, 48, 63), (300, 6, 48, 48, 75),
        (350, swc_350, 48, 48, 88), (400, 8, 48, 48, 100),
    ]
    try:
        page.goto(
            f"{ORIGIN}/scenarios/{slug}?army_points=150",
            wait_until="domcontentloaded",
        )
        select = page.locator("#scenario-army-points")
        select.wait_for(state="visible", timeout=60000)
        assert [item.get_attribute("value") for item in select.locator("option").all()] == [
            "", "150", "200", "250", "300", "350", "400",
        ]
        for points, swc, table_width, table_height, minimum in sizes:
            if points != 150:
                select.select_option(str(points))
            page.wait_for_function(
                """(points) =>
                  document.querySelector('#scenario-content')?.hidden === false
                  && document.querySelector('.scenario-setup-card .scenario-facts dd')
                    ?.textContent?.trim() === String(points)
                  && document.querySelector('svg.scenario-map') !== null""",
                arg=points,
                timeout=30000,
            )
            setup = page.locator(".scenario-setup-card .scenario-fact")
            assert setup.nth(0).locator("dd").inner_text() == str(points)
            assert setup.nth(1).locator("dd").inner_text().splitlines()[0] == str(swc)
            assert setup.nth(2).locator("dd").inner_text() == (
                f"{table_width}″ × {table_height}″"
            )
            assert (setup.count() == 4) == has_minimum
            if has_minimum:
                assert setup.nth(3).locator("dd").inner_text() == str(minimum)

            svg = page.locator("svg.scenario-map")
            assert svg.get_attribute("viewBox") == f"0 0 {table_width} {table_height}"
            assert svg.locator("rect.table").count() == 1
            assert page.locator(".scenario-objective").count() == objective_count
            assert page.locator(".scenario-rules .detail-section").count() == rule_count
            assert page.locator(".scenario-citations a").count() >= 1
            assert f"p. {source_page}" in page.locator(
                ".scenario-citations"
            ).inner_text()
            expected_issue = slug in ("annihilation", "domination") and points == 350
            assert (page.locator(".scenario-source-issue").count() == 1) == expected_issue
            assert not page.locator("#scenario-error").is_visible()
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= innerWidth + 1"
            ), (width, slug, points)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('.scenario-setup-card .scenario-facts dd')"
            "?.textContent?.trim() === '400'",
            timeout=30000,
        )
        assert select.input_value() == "400"
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_specialist_troops_search_leads_to_general_rule_and_scenarios(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(
            f"{ORIGIN}/search?q=Specialist%20Troops",
            wait_until="domcontentloaded",
        )
        search_link = page.locator(
            '#search-list a[href="/rules/specialist-troops-standard"]'
        )
        search_link.wait_for(state="visible", timeout=60000)
        assert search_link.count() == 1
        assert search_link.inner_text() == "Specialist Troops"
        assert "GENERAL RULE" in search_link.locator("..").inner_text()
        search_link.click()
        page.wait_for_url(f"{ORIGIN}/rules/specialist-troops-standard")
        card = page.locator("#rule-rule-specialist-troops-standard")
        card.wait_for(state="visible", timeout=60000)
        assert "each scenario determines" in card.inner_text()
        assert card.get_by_role("heading", name="Qualifying Skills").is_visible()
        assert card.locator(".detail-list li").count() >= 7
        assert "Non Specialist" in card.inner_text()
        assert "p. 152" in card.inner_text()
        links = page.locator('.reference-usage-list a[href^="/scenarios/"]')
        assert [link.get_attribute("href") for link in links.all()] == [
            "/scenarios/domination",
            "/scenarios/firefight",
            "/scenarios/supplies",
        ]
        page.locator('.reference-usage-list a[href="/scenarios/supplies"]').click()
        page.wait_for_url(f"{ORIGIN}/scenarios/supplies")
        scoped = page.locator("#rule-rule-specialist-troops-standard")
        scoped.wait_for(state="visible", timeout=60000)
        assert scoped.get_by_role("heading", name="Qualifying Skills").is_visible()
        assert "p. 154" in scoped.inner_text()
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_reference_provenance_labels_remain_distinct_across_themes(
    scenario_app: Callable[..., Any], chrome: Any, width: int, theme: str,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(
            f"{ORIGIN}/rules/specialist-troops-standard",
            wait_until="domcontentloaded",
        )
        card = page.locator("#rule-rule-specialist-troops-standard")
        card.wait_for(state="visible", timeout=60000)
        page.evaluate(
            "(value) => document.documentElement.setAttribute('data-theme', value)",
            theme,
        )
        assert "InfinityDB-maintained reference" in card.locator(
            ".rules-card-provenance"
        ).inner_text()
        sources = card.locator(".rules-source-citations")
        assert sources.count() == 1
        assert sources.locator(".rules-provenance-label").inner_text().strip() == "Sources:"
        assert "p. 152" in sources.inner_text()
        assert card.locator(".rules-provenance-caption").count() == 0

        page.goto(
            f"{ORIGIN}/scenarios/supplies?army_points=300",
            wait_until="domcontentloaded",
        )
        card = page.locator("#rule-rule-scenario-supply-boxes")
        card.wait_for(state="visible", timeout=60000)
        page.evaluate(
            "(value) => document.documentElement.setAttribute('data-theme', value)",
            theme,
        )
        assert card.locator(".rules-card-provenance").is_visible()
        assert "Sources:" in card.locator(".rules-source-citations").inner_text()
        faq = page.locator("#scenario-content .faq-dated-clarification")
        faq.wait_for(state="visible", timeout=60000)
        assert "source date anchor 2026-09-01" in faq.locator(
            ".faq-publication-source"
        ).inner_text()
        assert "not a verified PDF publication date" in page.locator(
            "#scenario-content .faq-rulings > .detail-source"
        ).inner_text()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), (width, theme)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_core_scenario_marker_sizes_are_visible_and_physically_fixed(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for slug, expected in (
            ("domination", "4 × Console A Marker — 40 mm diameter"),
            ("supplies", "3 × Supply Box Marker — 25 mm diameter"),
            ("annihilation", None),
            ("firefight", None),
        ):
            page.goto(
                f"{ORIGIN}/scenarios/{slug}?army_points=300",
                wait_until="domcontentloaded",
            )
            page.locator(".scenario-map-card").wait_for(state="visible", timeout=60000)
            marker = page.locator(".scenario-marker-dimensions")
            if expected is None:
                assert marker.count() == 0
                continue
            assert marker.count() == 1
            for unit in ("in", "cm"):
                page.evaluate(
                    """async (unit) => {
                      const preferences = await import("/static/preferences.js");
                      preferences.saveDistanceUnit(unit);
                      window.dispatchEvent(new Event("distanceunitchange"));
                    }""",
                    unit,
                )
                assert expected in marker.inner_text()
                assert "not scoring area or map scale" in marker.inner_text()
                citation = marker.locator(".detail-source a")
                assert citation.count() == 1
                assert "ITS Season 18" in citation.inner_text()
                assert "p. 17" in citation.inner_text()
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth <= innerWidth + 1"
                ), (width, slug, unit)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_domination_embedded_map_emphasizes_console_center_placement(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for points, horizontal, vertical in ((150, 6, 12), (200, 8, 18), (300, 12, 18)):
            page.goto(
                f"{ORIGIN}/scenarios/domination?army_points={points}",
                wait_until="domcontentloaded",
            )
            svg = page.locator("svg.scenario-map")
            svg.wait_for(state="visible", timeout=60000)
            guides = svg.locator("g.center-measurement")
            assert guides.count() == 8
            assert svg.locator('rect.scoring').count() == 4
            assert svg.locator('text.area-size[data-target^="quadrant-"]').count() == 0
            note = page.locator(".scenario-map-placement-note")
            assert note.is_visible()
            assert "each Console center" in note.inner_text()
            assert "scoring areas" in note.inner_text()
            assert "p. 152" in note.inner_text()
            for unit, scale, suffix in (("in", 1, "″"), ("cm", 2.5, " cm")):
                page.evaluate(
                    """(unit) => {
                      const toggle = document.querySelector("#distance-unit-toggle");
                      toggle.checked = unit === "in";
                      toggle.dispatchEvent(new Event("change", { bubbles: true }));
                    }""",
                    unit,
                )
                for edge, inches in (("left", horizontal), ("top", vertical)):
                    group = svg.locator(
                        f'#console-q1-center-{edge}'
                    )
                    assert group.get_attribute("data-reference") == "center"
                    label = group.locator("text.dimension-label")
                    assert label.get_attribute("data-distance-inches") == str(inches)
                    assert label.text_content() == f"{inches * scale:g}{suffix}"
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth <= innerWidth + 1"
                ), (width, points, unit)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_domination_350_swc_conflict_is_visible_at_its_value_and_scoped(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for slug, points in (
            ("domination", 300), ("domination", 350), ("domination", 400),
            ("annihilation", 350), ("firefight", 350), ("supplies", 350),
        ):
            page.goto(
                f"{ORIGIN}/scenarios/{slug}?army_points={points}",
                wait_until="domcontentloaded",
            )
            setup = page.locator(".scenario-setup-card")
            setup.wait_for(state="visible", timeout=60000)
            conflict = setup.locator(".scenario-fact--source-conflict")
            issue = page.locator("#scenario-source-issue-350-point-swc")
            if slug == "domination" and points == 350:
                assert conflict.count() == 1
                assert conflict.locator("dt").inner_text() == "SWC"
                assert conflict.locator("dd").inner_text().startswith("6")
                link = conflict.locator("a.scenario-swc-source-conflict")
                assert link.count() == 1
                assert "Official sources disagree" in link.inner_text()
                assert link.get_attribute("href") == "#scenario-source-issue-350-point-swc"
                assert issue.is_visible()
                detail = issue.inner_text()
                assert "needs verification" in detail.lower()
                assert "English Domination N5.3 chart (printed p. 151)" in detail
                assert "Spanish N5.3 Domination chart (printed p. 155)" in detail
                assert "7 SWC (CAP)" in detail
                assert "retains 6 SWC" in detail
                link.focus()
                assert link.evaluate("(node) => document.activeElement === node")
                link.press("Enter")
                assert page.evaluate("() => location.hash") == (
                    "#scenario-source-issue-350-point-swc"
                )
            else:
                assert conflict.count() == 0
                assert issue.count() == 0
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= innerWidth + 1"
            ), (width, slug, points)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_scenario_rule_cards_omit_only_redundant_subtitles(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/scenarios/supplies?army_points=300",
                  wait_until="domcontentloaded")
        placeholder = page.locator("#rule-rule-scenario-supply-boxes")
        placeholder.wait_for(state="visible", timeout=60000)
        assert placeholder.locator("h3").first.inner_text() == "Supply Boxes"
        assert placeholder.locator(".detail-copy").count() == 0
        assert placeholder.locator(".detail-fact-group").count() > 0
        assert placeholder.locator(".detail-source").count() > 0
        assert "Rules for Supply Boxes." not in placeholder.inner_text()
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_supplies_faq_is_visible_and_does_not_leak_to_other_scenarios(
    scenario_app: Callable[..., Any], chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for slug, expected in (
            ("supplies", "Can a Trooper carrying a scenario element"),
            ("annihilation", "Does an undeployed Peripheral"),
            ("domination", None),
            ("firefight", None),
        ):
            page.goto(
                f"{ORIGIN}/scenarios/{slug}?army_points=300",
                wait_until="domcontentloaded",
            )
            page.locator("#scenario-content").wait_for(state="visible", timeout=60000)
            rulings = page.locator("#scenario-content .faq-rulings .faq-ruling")
            if expected is None:
                assert rulings.count() == 0, (width, slug, rulings.all_inner_texts())
                assert page.locator("#scenario-content .faq-rulings").count() == 0
                continue
            assert rulings.count() == 1, (width, slug, rulings.all_inner_texts())
            assert expected in rulings.first.locator("h3").inner_text()
            assert "FAQ v0.1" in page.locator(
                "#scenario-content .faq-rulings .detail-source"
            ).first.inner_text()
            assert page.locator("#scenario-content .faq-rulings").is_visible()
            if slug == "supplies":
                assert "cannot enter Marker State" in rulings.first.inner_text()
                assert "FAQ clarification" in rulings.first.inner_text()
                assert rulings.first.locator(".detail-source a").count() >= 1
                assert page.locator(
                    "#scenario-content .developer-only .faq-ruling"
                ).count() == 0
            else:
                assert "cannot enter Marker State" not in rulings.first.inner_text()
        assert not errors, errors
    finally:
        page.close()


# Each reviewed FAQ has at least one specific normal-player entry point. Keep
# the route/topic selection separate from curated topicIds so a removed route,
# missing frontend FAQ fetch or a no-longer-published catalog record fails.
FAQ_BROWSER_ROUTES = {
    "skills": (
        ("/skills/aerial", "skill:aerial", ("aerial-boost-no-silhouette-contact",)),
        ("/skills/bs-attack", "skill:bs-attack", (
            "bs-attack-roll-label-mods", "skill-declaration-target-position",
        )),
        ("/skills/camouflage", "skill:camouflage", (
            "camouflage-one-use-infiltration-failure",
        )),
        ("/skills/minelayer", "skill:minelayer", ("deployment-private-zoc-coherency",)),
        ("/skills/discover", "skill:discover", ("discover-fireteam-sd-bonuses",)),
        ("/skills/peripheral", "skill:peripheral", (
            "peripheral-controller-unable-to-declare",
        )),
        ("/skills/place-deployable", "skill:place-deployable", (
            "place-deployable-space-occupied",
        )),
        ("/skills/protheion", "skill:protheion", ("protheion-excess-saving-rolls",)),
        ("/skills/sixth-sense", "skill:sixth-sense", (
            "sixth-sense-msv1-zero-visibility",
        )),
        ("/skills/stealth", "skill:stealth", ("stealth-aro-multiple-activations",)),
        ("/skills/surprise-attack", "skill:surprise-attack", (
            "surprise-attack-multiple-users",
        )),
        ("/skills/climb", "skill:climb", ("vault-during-climb-and-jump",)),
    ),
    "catalogs": (
        ("/states/camouflaged", "state:camouflaged", (
            "camouflaged-marker-total-cover", "marker-automatic-skill-declarations",
        )),
        ("/hacking-programs/controlled-jump", "hacking-program:controlled-jump", (
            "controlled-jump-speedball",
        )),
        ("/equipment/deployable-cover", "equipment:deployable-cover", (
            "deployable-cover-no-placement",
        )),
        ("/traits/direct-template", "trait:direct-template", (
            "direct-template-secondary-target-los",
        )),
        ("/traits/deployable", "trait:deployable", (
            "fired-deployable-vertical-surface",
        )),
        ("/equipment/hacking-device", "equipment:hacking-device", (
            "hacking-device-firewall-disabled",
        )),
        ("/states/disconnected", "state:disconnected", (
            "null-state-marker-and-cautious-movement",
        )),
        ("/states/prone", "state:prone", (
            "prone-at-end-of-move-distance", "prone-movement-label",
        )),
    ),
    "rules": (
        ("/rules/coordinated-orders", "rule:coordinated-orders", (
            "coordinated-order-special-dice",
        )),
        ("/rules/deployment-phase", "rule:deployment-phase", (
            "deployment-phase-reposition-after-measurement",
        )),
        ("/fireteams", "rule:fireteam-general", (
            "fireteam-required-member-lost", "fireteam-type-after-member-loss",
        )),
    ),
    "scenarios": (
        ("/scenarios/annihilation?army_points=300", "scenario:annihilation", (
            "undeployed-ancillary-not-killed",
        )),
        ("/scenarios/supplies?army_points=300", "scenario:supplies", (
            "scenario-element-carrier-marker-state",
        )),
    ),
}


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("group", tuple(FAQ_BROWSER_ROUTES))
def test_every_published_faq_has_a_normal_browser_entry_point(
    scenario_app: Callable[..., Any], chrome: Any, group: str, width: int,
) -> None:
    """Full 29-ruling source -> API -> ordinary browser reachability gate.

    Source/version and selected scenario applicability are independently tested
    in test_faq_ruling_references.py. This verifies live, visible browser cards.
    """
    faq = next(
        document for _, document in load_curated_directory(ROOT / "data/curated")
        if document["collection"]["id"] == "n5-faq-v0.1"
    )
    records = {row["id"].removeprefix("faq-ruling:"): row for row in faq["records"]}
    routes = FAQ_BROWSER_ROUTES
    all_rulings = [
        ruling_id
        for group_routes in routes.values()
        for _, _, ids in group_routes
        for ruling_id in ids
    ]
    assert len(all_rulings) == len(set(all_rulings)) == 29
    assert set(all_rulings) == set(records)

    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, scenario_app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for path, topic, identifiers in routes[group]:
            page.goto(f"{ORIGIN}{path}", wait_until="domcontentloaded")
            for identifier in identifiers:
                record = records[identifier]
                assert topic in record["facts"]["topicIds"], (path, identifier)
                heading = page.locator(".faq-rulings .faq-ruling h3").get_by_text(
                    record["facts"]["question"], exact=True,
                )
                heading.wait_for(state="visible", timeout=20000)
                assert heading.count() == 1, (path, identifier)
                card = heading.locator("xpath=..")
                assert record["facts"]["answer"] in card.inner_text()
                source = card.locator(".faq-publication-source")
                assert "FAQ clarification" in source.inner_text()
                assert f"p. {record['facts']['selectedCitation']['page']}" in source.inner_text()
                assert source.locator("a").count() >= 1
            assert not errors, (path, errors)
    finally:
        page.close()
