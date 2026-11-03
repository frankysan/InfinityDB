"""Normal-mode Chromium acceptance for the optional N4-origin Reinforcements annex.

This verifies published navigation and disclosures, not N5-native annex authority,
army-list legality, or adoption of the N4 procedures as N5-native.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import pytest

from infinity_db.web import create_app
from tools.browser_test_metrics import launch_timed_chromium
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-reinforcements-browser.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    api = pytest.importorskip("playwright.sync_api")
    with api.sync_playwright() as driver:
        try:
            chrome = launch_timed_chromium(driver, "reinforcements-optional")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield chrome
        finally:
            chrome.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
def test_optional_annex_disclosures_and_links_stay_outside_core_matrix(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    responses: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("response", lambda response: responses.append(
        f"{response.status} {response.url}",
    ) if response.status >= 400 else None)
    try:
        response = page.goto(f"{ORIGIN}/rules/reinforcements-extra", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        rule = page.locator("#rule-rule-reinforcements-extra")
        rule.wait_for(state="visible", timeout=20000)
        assert page.locator("#item-name").inner_text().startswith("Reinforcements Extra")
        assert "N4-origin" in rule.inner_text()
        assert "not been verified" in rule.inner_text()
        assert rule.locator(".rules-source-citations a").count() == 4
        assert "N4" in rule.locator(".detail-source").all_inner_texts()[-1]

        # The annex offers direct navigation to the current Section pools and
        # their parent Armies using the published /api/armies relationships.
        armies = page.evaluate("async () => (await fetch('/api/armies')).json()")
        eligible = {
            army["id"]: army
            for army in armies["items"]
            if army.get("playable") is not False and not army.get("legacy")
        }
        reinforcement_sections = sorted(
            (army for army in eligible.values() if army["role"] == "reinforcement"),
            key=lambda army: army["name"],
        )
        assert reinforcement_sections
        navigation = page.locator("#reinforcement-section-navigation")
        navigation.wait_for(state="visible", timeout=20000)
        assert "do not validate a combined Army List" in navigation.inner_text()
        rows = navigation.locator("li")
        assert rows.count() == len(reinforcement_sections)
        for section, row in zip(reinforcement_sections, rows.all(), strict=True):
            section_slug = section.get("public_slug") or section.get("slug") or str(section["id"])
            assert row.locator("a").first.get_attribute("href") == f"/armies#army-{section_slug}"
            parent_links = row.locator('a[href^="/armies#army-"]')
            parents = [
                eligible[parent["id"]]
                for parent in section.get("parent_armies", [])
                if parent["id"] in eligible
            ]
            assert parent_links.count() == 1 + len(parents)
            assert [link.text_content() for link in parent_links.all()][1:] == [
                parent["name"] for parent in parents
            ]
            units_link = row.get_by_role("link", name="Browse section units")
            assert units_link.get_attribute("href").startswith("/units?s=v1.u.")
        if width == 1440:
            destination = rows.first.locator("a").first.get_attribute("href")
            rows.first.locator("a").first.click()
            page.wait_for_url(f"{ORIGIN}{destination}")
            page.locator(f'[id="{destination.split("#", 1)[1]}"]').wait_for(state="visible")
            page.goto(f"{ORIGIN}/rules/reinforcements-extra", wait_until="domcontentloaded")
            rule.wait_for(state="visible", timeout=20000)
            navigation.wait_for(state="visible", timeout=20000)
            section = reinforcement_sections[0]
            expected_slug = section.get("public_slug") or section.get("slug") or str(section["id"])
            navigation.locator("li").first.get_by_role(
                "link", name="Browse section units",
            ).click()
            page.wait_for_url("**/units?s=*")
            page.locator("#army-filter").wait_for(state="visible")
            page.wait_for_function(
                "() => document.querySelector('#army-filter')?.disabled === false"
            )
            assert page.locator("#army-filter").input_value() == expected_slug
            assert page.evaluate(
                "async () => (await import('/static/share-state.js'))"
                ".readShareState('units').params.get('reinforcement')"
            ) == "1"
            page.goto(f"{ORIGIN}/rules/reinforcements-extra", wait_until="domcontentloaded")
            rule.wait_for(state="visible", timeout=20000)

        commlink = rule.locator('a[href="/skills/commlink"]').first
        assert commlink.is_visible()
        commlink.click()
        page.wait_for_url(f"{ORIGIN}/skills/commlink")
        skill = page.locator("#rule-skill-commlink")
        skill.wait_for(state="visible", timeout=20000)
        assert page.locator("#skill-name").inner_text().startswith("Commlink")
        assert "N4-origin" in skill.inner_text()
        assert "maximum Trooper count" in skill.inner_text()
        assert skill.locator(".rules-source-citations a").count() >= 1

        request = skill.locator('a[href="/skills/request-reinforcements"]').first
        assert request.is_visible()
        request.click()
        page.wait_for_url(f"{ORIGIN}/skills/request-reinforcements")
        request_rule = page.locator("#rule-skill-request-reinforcements")
        request_rule.wait_for(state="visible", timeout=20000)
        assert page.locator("#skill-name").inner_text().startswith("Request Reinforcements")
        assert "N4-origin" in request_rule.inner_text()
        assert "Tactical Phase step" in request_rule.inner_text()
        assert "not an ordinary Order declaration" in request_rule.inner_text()

        annex_link = request_rule.locator('a[href="/rules/reinforcements-extra"]').first
        assert annex_link.is_visible()
        annex_link.focus()
        page.keyboard.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/reinforcements-extra")
        rule.wait_for(state="visible", timeout=20000)

        page.goto(f"{ORIGIN}/orders-aros", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector('#matrix-count')?.textContent === '57 declarations'",
            timeout=20000,
        )
        matrix = page.locator("#matrix-sections")
        assert matrix.locator("tbody tr").count() == 57
        assert not matrix.locator('tr[data-record-id="skill:commlink"]').count()
        assert not matrix.locator('tr[data-record-id="skill:request-reinforcements"]').count()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        ), width
        assert not errors, errors
        assert not responses, responses
    finally:
        page.close()


def _published_unit(app: Any, slug: str, *, query: str = "") -> dict[str, Any]:
    url = f"{ORIGIN}/api/units/{quote(slug, safe='')}"
    if query:
        url += f"?{query}"
    status, _headers, body = wsgi_response(app, url)
    assert status == 200, (slug, query, status, body[:200])
    return json.loads(body)


@pytest.fixture(scope="module")
def shared_section_unit(app: Any) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Pick one pinned logical Unit with actual profiles in both list contexts."""
    with sqlite3.connect(ROOT / "data/generated/infinity.db") as database:
        rows = database.execute(
            "SELECT lu.slug FROM logical_units AS lu "
            "JOIN logical_unit_sources AS lus ON lus.logical_unit_id = lu.id "
            "JOIN army_units AS au ON au.unit_id = lus.source_unit_id "
            "JOIN army_lists AS al ON al.id = au.army_id "
            "JOIN profile_payload_occurrences AS ppo "
            "ON ppo.unit_id = au.unit_id AND ppo.army_id = au.army_id "
            "WHERE lu.slug IS NOT NULL GROUP BY lu.id, lu.slug "
            "HAVING COUNT(DISTINCT CASE WHEN al.kind = 'reinforcement' "
            "THEN al.id END) > 0 "
            "AND COUNT(DISTINCT CASE WHEN al.kind != 'reinforcement' "
            "THEN al.id END) > 0 ORDER BY lu.slug"
        )
        slugs = [str(row[0]) for row in rows]
    assert slugs, "No pinned logical Unit with ordinary and Reinforcement source profiles"
    for slug in slugs:
        unit = _published_unit(app, slug)
        ordinary = [
            army for army in unit["armies"]
            if army["role"] != "reinforcement" and army["profiles"]
            and "reinforcement" not in army["availability_flags"]
        ]
        sections = [
            army for army in unit["armies"]
            if army["role"] == "reinforcement" and army["profiles"]
            and "reinforcement" in army["availability_flags"]
        ]
        for section in sections:
            parents = {parent["id"] for parent in section["parent_armies"]}
            for main in ordinary:
                if main["id"] in parents:
                    return slug, main, section
    raise AssertionError(
        f"No source-backed Unit has both an ordinary parent and its Reinforcement "
        f"Section's own profile occurrences among {len(slugs)} shared candidates"
    )


def test_real_shared_unit_keeps_profiles_in_their_source_sections(
    app: Any, shared_section_unit: tuple[str, dict[str, Any], dict[str, Any]],
) -> None:
    """Source variants remain separate after logical identity reconciliation."""
    slug, main, section = shared_section_unit
    main_slug = main["public_slug"]
    section_slug = section["public_slug"]
    assert main["id"] != section["id"]
    assert main["role"] != "reinforcement"
    assert section["role"] == "reinforcement"
    assert any(parent["id"] == main["id"] for parent in section["parent_armies"])

    with sqlite3.connect(ROOT / "data/generated/infinity.db") as database:
        source_ids = [
            row[0] for row in database.execute(
                "SELECT lus.source_unit_id FROM logical_unit_sources AS lus "
                "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
                "WHERE lu.slug = ? ORDER BY lus.source_unit_id", (slug,),
            )
        ]
        assert source_ids
        placeholders = ", ".join("?" for _ in source_ids)
        source_names: dict[int, set[str]] = {}
        for army_id, name in database.execute(
            "SELECT aas.application_army_id, pp.name "
            "FROM profile_payload_occurrences AS ppo "
            "JOIN application_army_sources AS aas "
            "ON aas.source_army_id = ppo.army_id "
            "JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id "
            f"WHERE ppo.unit_id IN ({placeholders})",
            source_ids,
        ):
            source_names.setdefault(army_id, set()).add(name)

    for army in (main, section):
        actual = {profile["name"] for profile in army["profiles"]}
        assert actual == source_names[army["id"]], (slug, army["name"], actual)

    ordinary_view = _published_unit(
        app, slug, query=urlencode({"reinforcement": 0, "army_id": main_slug}),
    )
    ordinary_armies = {army["id"]: army for army in ordinary_view["armies"]}
    assert ordinary_armies[main["id"]]["presentation_visible"]
    assert ordinary_armies[main["id"]]["presentation_requested"]
    assert not ordinary_armies[section["id"]]["presentation_visible"]
    assert not ordinary_armies[section["id"]]["presentation_requested"]
    assert not any(
        profile["reinforcement_only"] for profile in ordinary_view["general_profiles"]
    )

    section_view = _published_unit(
        app, slug, query=urlencode({"reinforcement": 0, "army_id": section_slug}),
    )
    selected = {army["id"]: army for army in section_view["armies"]}
    assert selected[section["id"]]["presentation_requested"]
    assert selected[section["id"]]["presentation_visible"]
    assert "reinforcement" in selected[section["id"]]["availability_flags"]
    assert {profile["name"] for profile in selected[section["id"]]["profiles"]} == (
        source_names[section["id"]]
    )
    assert selected[main["id"]]["presentation_visible"]
    expected_general = {
        profile["profile_identity"]
        for army in section_view["armies"] if army["presentation_visible"]
        for profile in army["profiles"]
    }
    assert {profile["profile_identity"] for profile in section_view["general_profiles"]} == (
        expected_general
    )


@pytest.mark.parametrize("width", [1440, 390])
def test_real_shared_unit_opens_only_the_explicit_army_context(
    app: Any, browser: Any,
    shared_section_unit: tuple[str, dict[str, Any], dict[str, Any]], width: int,
) -> None:
    """The browser's expanded profile must follow Army selection, not Unit identity."""
    slug, main, section = shared_section_unit
    page = browser.new_page(viewport={"width": width, "height": 850})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for target in (main, section):
            chosen = target["public_slug"]
            page.goto(f"{ORIGIN}/units/{slug}", wait_until="domcontentloaded")
            url = page.evaluate(
                """async ({slug, army}) => (await import('/static/share-state.js'))
                    .shareStateHref('/units/' + encodeURIComponent(slug), 'unit',
                    {army_id: army})""",
                {"slug": slug, "army": chosen},
            )
            page.goto(f"{ORIGIN}{url}", wait_until="domcontentloaded")
            page.locator("#unit-content").wait_for(state="visible", timeout=20000)
            expanded = page.locator("details.army-profile[open]")
            assert expanded.count() == 1, (slug, chosen, width)
            assert target["name"] in expanded.locator("summary").inner_text()
            profile_names = {profile["name"] for profile in target["profiles"]}
            rendered_names = set(
                expanded.locator(".profile-name-with-division").all_text_contents()
            )
            assert profile_names <= rendered_names, (
                slug, chosen, width, profile_names - rendered_names,
            )
        assert not errors, errors
    finally:
        page.close()


@pytest.fixture(scope="module")
def commlink_variant_units(app: Any) -> dict[int, tuple[str, dict[str, Any]]]:
    """Locate one source-backed Unit/loadout for each exact Army Commlink extra."""
    with sqlite3.connect(ROOT / "data/generated/infinity.db") as database:
        candidates = database.execute(
            "SELECT DISTINCT lu.slug, e.extra_id "
            "FROM loadout_payload_skill_extras AS e "
            "JOIN loadout_payload_skills AS s "
            "ON s.loadout_payload_id = e.loadout_payload_id "
            "AND s.position = e.occurrence_position "
            "JOIN loadout_payloads AS lp ON lp.id = s.loadout_payload_id "
            "JOIN logical_units AS lu ON lu.id = lp.logical_unit_id "
            "WHERE s.item_id = 260 AND e.extra_id IN (298, 299) "
            "AND lu.slug IS NOT NULL ORDER BY e.extra_id, lu.slug"
        ).fetchall()
    found: dict[int, tuple[str, dict[str, Any]]] = {}
    for slug, extra_id in candidates:
        if extra_id in found:
            continue
        unit = _published_unit(app, slug)
        for army in unit["armies"]:
            if not army.get("profiles") or not army.get("loadouts"):
                continue
            if any(
                skill.get("id") == 260
                and [(extra["id"], extra["name"]) for extra in skill.get("extras", [])]
                == [(extra_id, "+1" if extra_id == 298 else "+2")]
                for loadout in army["loadouts"]
                for skill in loadout.get("skills", [])
            ):
                found[extra_id] = (slug, army)
                break
        if len(found) == 2:
            break
    assert set(found) == {298, 299}, (
        "Both reviewed Commlink (+X) Army signatures need Unit detail consumers",
        found,
    )
    return found


@pytest.mark.parametrize(
    ("extra_id", "width"), [(298, 1440), (299, 390)],
)
def test_published_commlink_extra_is_linked_from_exact_source_army_loadout(
    app: Any, browser: Any,
    commlink_variant_units: dict[int, tuple[str, dict[str, Any]]],
    extra_id: int, width: int,
) -> None:
    """Commlink (+X) stays on its actual Army loadout and leads to scoped rules."""
    slug, army = commlink_variant_units[extra_id]
    page = browser.new_page(viewport={"width": width, "height": 850})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    expected = "Commlink (+1)" if extra_id == 298 else "Commlink (+2)"
    try:
        page.goto(f"{ORIGIN}/units/{slug}", wait_until="domcontentloaded")
        href = page.evaluate(
            """async ({slug, army}) => (await import('/static/share-state.js'))
                .shareStateHref('/units/' + encodeURIComponent(slug), 'unit',
                {army_id: army})""",
            {"slug": slug, "army": army["public_slug"]},
        )
        page.goto(f"{ORIGIN}{href}", wait_until="domcontentloaded")
        page.locator("#unit-content").wait_for(state="visible", timeout=20000)
        selected = page.locator("details.army-profile[open]")
        assert selected.count() == 1, (slug, army["name"], width)
        link = selected.locator('a[href="/skills/commlink"]').filter(has_text=expected)
        assert link.count() > 0, (slug, army["name"], expected, width)
        link.first.click()
        page.wait_for_url(f"{ORIGIN}/skills/commlink")
        rule = page.locator("#rule-skill-commlink")
        rule.wait_for(state="visible", timeout=20000)
        assert "N4-origin" in rule.inner_text()
        assert "maximum Trooper count" in rule.inner_text()
        assert not errors, errors
    finally:
        page.close()
