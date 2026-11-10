"""Scoped State/Fireteam reciprocal links on the freshly reviewed N5.3 source."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://fireteam-state-context.test"

STATES = {
    "disconnected": ("Ancillary", "Other [[skill:peripheral|Peripheral]] Controllers", 134),
    "retreat": ("team-level consequence", "Command Token exception", 134),
    "suppressive-fire": ("joins a [[rule:fireteam-general|Fireteam]]", "Guts Roll", 136),
}


@pytest.fixture(scope="module")
def state_fireteam_app(
    tmp_path_factory: pytest.TempPathFactory,
) -> Any:
    """Export changed curated content, never silently use an older tracked DB."""
    rules_path = tmp_path_factory.mktemp("contextual-state-fireteam") / "rules_n5.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated"), rules_path)
    return create_app(
        ROOT / "data/generated/army.db", rules_database_path=rules_path,
    )


def _json_response(app: Any, path: str) -> dict[str, Any]:
    status, _headers, content = wsgi_response(app, ORIGIN + path)
    assert status == 200, (path, status)
    value: dict[str, Any] = json.loads(content)
    return value


def test_state_fireteam_links_have_source_scope_and_no_inferred_relations() -> None:
    core = ROOT / "data/curated/rules/n5-core-v5.3.json"
    document = next(
        payload for _, payload in load_curated_directory(ROOT / "data/curated")
        if payload["collection"]["id"] == "n5-core-v5.3"
    )
    records = {record["id"]: record for record in document["records"]}
    for slug, (scope_phrase, qualifier, source_page) in STATES.items():
        rule = records[f"state:{slug}"]
        facts = " ".join(rule["facts"]["clarifications"])
        assert "[[rule:fireteam-general|" in facts, slug
        assert scope_phrase in facts and qualifier in facts, slug
        assert any(
            cite["sourceId"] == "n5-core-v5.3-pdf" and cite.get("page") == source_page
            for cite in rule["citations"]
        ), slug
        assert not any(
            edge.get("recordId") == "rule:fireteam-general"
            for edge in rule.get("relations", [])
        ), slug
    isolated = records["state:isolated"]
    assert {"type": "prevents-membership-in", "recordId": "rule:fireteam-general"} in (
        isolated["relations"]
    )
    assert core.exists()


def test_state_fireteam_links_resolve_as_api_tokens_in_both_directions(
    state_fireteam_app: Any,
) -> None:
    fireteams = _json_response(state_fireteam_app, "/api/fireteams")
    reference = fireteams["reference"]["general"]
    assert reference["id"] == "rule:fireteam-general"
    body = " ".join(reference["facts"]["rules"])
    for slug, (scope_phrase, qualifier, _page) in STATES.items():
        state = _json_response(state_fireteam_app, f"/api/states/{slug}")["rules"][0]
        assert state["id"] == f"state:{slug}"
        notes = " ".join(state["facts"]["clarifications"])
        assert scope_phrase in notes and qualifier in notes
        assert any(
            token.get("type") == "reference"
            and token.get("target") == "rule:fireteam-general"
            for tokens in state["fact_tokens"]["clarifications"]
            for token in tokens
        ), slug
        assert f"[[state:{slug}|" in body, slug


@pytest.mark.parametrize("width", [1440, 390, 320])
@pytest.mark.parametrize("slug", list(STATES))
def test_state_fireteam_links_navigate_in_real_browser(
    state_fireteam_app: Any, slug: str, width: int, chromium_test_slot: None,
) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            page = browser.new_page(viewport={"width": width, "height": 900})
            route_browser_page(page, state_fireteam_app, ORIGIN)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            try:
                response = page.goto(
                    f"{ORIGIN}/states/{slug}", wait_until="domcontentloaded"
                )
                assert response and response.status == 200
                forward = page.locator(
                    "#item-content a.maintained-reference[href='/fireteams']"
                ).first
                forward.wait_for(state="visible", timeout=15000)
                forward.click()
                page.wait_for_url(ORIGIN + "/fireteams", timeout=15000)
                reverse = page.locator(
                    f"a.maintained-reference[href='/states/{slug}']"
                ).first
                reverse.wait_for(state="visible", timeout=15000)
                reverse.click()
                page.wait_for_url(ORIGIN + f"/states/{slug}", timeout=15000)
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth <= innerWidth + 1"
                ), (slug, width)
                assert not errors, (slug, width, errors)
            finally:
                page.close()
        finally:
            browser.close()
