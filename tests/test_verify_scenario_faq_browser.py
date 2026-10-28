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
