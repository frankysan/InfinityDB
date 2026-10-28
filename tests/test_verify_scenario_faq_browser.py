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
        assert "published 2026-09-01" in faq.locator(
            ".faq-publication-source"
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
