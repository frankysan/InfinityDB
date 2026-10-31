"""Browser parity between reviewed Ammunition source identities and Weapon details.

Use the published API as the source of truth. The visualized components and
shared rules are links/descriptions only: never compute Immunity, Saving Roll
counts, Critical results, or Weapon profile effects from them.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.database.repository import Database
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-ammunition-parity.test"
SAMPLES = (
    ("e-m-cc-weapon", 5, ("normal", "em"), "BTS/2", "2"),
    ("feuerbach", 10, ("ap", "da"), "ARM/2", "2"),
    ("missile-launcher", 13, ("ap", "exp"), "ARM/2", "3"),
    ("uragan-mrl", 30, ("ap", "shock"), "ARM/2", "1"),
    ("ap-t2-cc-weapon", 40, ("ap", "t2"), "ARM/2", "1"),
)


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
            chrome = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield chrome
        finally:
            chrome.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
@pytest.mark.parametrize("slug", ["smoke", "eclipse"])
def test_visibility_opposition_rows_match_api_and_link_to_roll_rules(
    app: Any, browser: Any, width: int, height: int, slug: str,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    failed: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: failed.append(request.url))
    page.on("response", lambda response: failed.append(
        f"{response.status} {response.url}"
    ) if response.status >= 400 else None)
    try:
        response = page.goto(f"{ORIGIN}/ammunition/{slug}", wait_until="domcontentloaded")
        assert response.status == 200
        group = page.locator(".ammunition-mechanics")
        group.get_by_text("Opposing Attacks", exact=True).wait_for()
        payload = page.evaluate(
            "async () => (await fetch('/api' + location.pathname)).json()"
        )
        record = next(r for r in payload["rules"] if r["id"] == f"ammunition:{slug}")
        opposition = record["facts"]["visibilityZone"]["opposition"]
        assert opposition["attackRequirements"] == [
            "requires-roll", "requires-lof", "lof-crosses-zone",
        ]
        assert opposition["enemyDodge"] == "normal-roll"
        assert opposition["critical"] == "no-additional-effect"
        actual = group.inner_text()
        assert "enemy Attacks requiring a Roll and LoF crossing the zone" in actual
        assert "Dodge inside the Template is a Normal Roll" in actual
        assert "Win every applicable Face to Face Roll" in actual
        assert "pass the unopposed Normal Roll" in actual
        assert "No additional effect; apply the Face to Face rules" in actual
        assert "Saving Roll" not in actual and "ammunitionResolution" not in record["facts"]
        if slug == "smoke":
            assert opposition["visorAttack"] == "normal-roll"
            assert "Smoke does not oppose these Attacks" in actual
        else:
            assert opposition["visorAttack"] == "face-to-face-if-qualifying"
            assert "Qualifying rolled Attacks through Eclipse can be Face to Face" in actual
        links = group.locator('a[href="/rules/face-to-face-rolls"]')
        assert links.count() == 2
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= innerWidth + 1"
        )
        links.first.focus()
        page.keyboard.press("Enter")
        page.wait_for_url(f"{ORIGIN}/rules/face-to-face-rolls")
        page.get_by_role("heading", name="Face to Face Rolls", exact=True).first.wait_for()
        page.go_back()
        page.wait_for_url(f"{ORIGIN}/ammunition/{slug}")
        page.locator(".ammunition-mechanics").get_by_text("Opposing Attacks", exact=True).wait_for()
        assert not errors, errors
        assert not failed, failed
    finally:
        page.close()


def _display_summary(
    summary: str, tokens: list[dict[str, Any]] | None = None,
) -> str:
    """Use published resolved labels, including canonical plural forms."""
    if tokens is not None:
        assert all(token["type"] in {"text", "reference"} for token in tokens)
        return "".join(
            token["label"] if token["type"] == "reference" else token["text"]
            for token in tokens
        ).strip()
    return re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", summary).strip()


def _api(app: Any, path: str) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def respond(status: str, _headers: list, _exc: object = None) -> None:
        statuses.append(status)

    data = b"".join(app(environ, respond))
    assert statuses == ["200 OK"]
    return json.loads(data)


def _profile(payload: dict[str, Any], source_id: int) -> dict[str, Any]:
    profiles = payload.get("profiles", []) + [
        p for variant in payload.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    matches = [
        p for p in profiles if p.get("ammunition_source_id") == source_id
    ]
    assert matches
    return matches[0]


BASE_SOURCE_IDS = (2, 3, 6, 8, 9, 14, 18, 21, 22, 29, 37)


@pytest.fixture(scope="module")
def base_samples(app: Any) -> dict[int, tuple[str, dict[str, Any]]]:
    """Select one unambiguous real Weapon profile for every reviewed base ID."""
    database = Database(ROOT / "data/generated/infinity.db")
    mapping = load_ammunition_reference_map()
    assert all("components" not in mapping[source_id] for source_id in BASE_SOURCE_IDS)
    with sqlite3.connect(ROOT / "data/generated/infinity.db") as connection:
        candidates = {
            source_id: [
                row[0] for row in connection.execute(
                    "SELECT DISTINCT id FROM metadata_weapons "
                    "WHERE ammunition = ? AND (type IS NULL OR type != 'EQUIPMENT') "
                    "ORDER BY id",
                    (source_id,),
                )
            ] for source_id in BASE_SOURCE_IDS
        }
    selected: dict[int, tuple[str, dict[str, Any]]] = {}
    for source_id, weapon_ids in candidates.items():
        for weapon_id in weapon_ids:
            slug = database.application_slug("weapons", weapon_id)
            if not slug:
                continue
            payload = _api(app, f"/api/weapons/{slug}")
            profiles = payload.get("profiles", []) + [
                profile for variant in payload.get("weapon_variants", [])
                for profile in variant.get("profiles", [])
            ]
            matches = [
                profile for profile in profiles
                if profile.get("ammunition_source_id") == source_id
            ]
            if not matches:
                continue
            profile = matches[0]
            if profile.get("ammunition") != mapping[source_id]["name"]:
                continue
            selected[source_id] = (slug, profile)
            break
    assert set(selected) == set(BASE_SOURCE_IDS), (
        "No unambiguous published Weapon for base source IDs",
        sorted(set(BASE_SOURCE_IDS) - set(selected)),
    )
    return selected


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
@pytest.mark.parametrize("source_id", BASE_SOURCE_IDS)
def test_reviewed_base_ammunition_is_linked_without_rewriting_weapon_rolls(
    app: Any, browser: Any, base_samples: dict[int, tuple[str, dict[str, Any]]],
    source_id: int, width: int, height: int,
) -> None:
    slug, profile = base_samples[source_id]
    mapping = load_ammunition_reference_map()[source_id]
    identity = mapping["segments"][0]["ruleId"]
    name = identity.split(":", 1)[1]
    assert profile["ammunition_parts"][0]["public_reference"] == {
        "catalog": "ammunition", "id": name,
    }
    assert len(profile["ammunition_parts"]) == 1
    assert "ammunition_composition" not in profile
    effects = profile["ammunition_effects"]
    assert len(effects) == 1
    assert effects[0]["record_id"] == identity
    assert effects[0]["citations"]

    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/weapons/{slug}", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector("
            "'.weapon-profile .weapon-statline tbody tr') !== null",
            timeout=20000,
        )
        card = page.locator(".weapon-profile").filter(
            has=page.locator(".weapon-statline td[data-label='Ammunition']")
            .filter(has_text=profile["ammunition"])
        )
        if profile.get("mode"):
            card = card.filter(has=page.locator("h4").filter(
                has_text=profile["mode"]
            ))
        assert card.count() >= 1, (source_id, slug, profile.get("mode"))
        card = card.first
        ammo_cell = card.locator(".weapon-statline td[data-label='Ammunition']")
        assert ammo_cell.inner_text().strip() == profile["ammunition"]
        assert ammo_cell.locator("a").evaluate_all(
            "(links) => links.map((link) => link.getAttribute('href'))"
        ) == [f"/ammunition/{name}"]
        raw_saving = profile.get("saving")
        if raw_saving is None or str(raw_saving).strip() in ("", "-", "--"):
            displayed_saving = "--"
        else:
            displayed_saving = " × ".join(
                str(value) for value in (raw_saving, profile.get("saving_num"))
                if value is not None and str(value) != ""
            )
        assert card.locator(
            ".weapon-statline td[data-label='Saving']"
        ).inner_text() == displayed_saving
        detail = card.locator(".weapon-ammunition-effects")
        assert detail.count() == 1
        detail.evaluate("(element) => element.open = true")
        effect = detail.locator(".weapon-ammunition-effect")
        assert effect.count() == 1
        assert effect.locator("h5 a").get_attribute("href") == f"/ammunition/{name}"
        assert effect.locator("h5").inner_text().strip() == effects[0]["name"]
        summary_tokens = effects[0]["summary_tokens"]
        assert effect.locator("p.detail-copy").inner_text().strip() == (
            _display_summary(effects[0]["summary"], summary_tokens)
        )
        for token in summary_tokens:
            if token["type"] != "reference":
                continue
            reference = token["public_reference"]
            href = reference.get("href") or (
                f"/{reference['catalog']}/{reference['id']}"
            )
            assert effect.locator(
                f'p.detail-copy a[href="{href}"]'
            ).filter(has_text=token["label"]).count() >= 1
        assert effect.locator(".detail-source a").count() == len(
            effects[0]["citations"]
        )
        assert "Follow the printed Weapon profile" in detail.inner_text()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("source_id", BASE_SOURCE_IDS)
def test_every_base_weapon_link_has_cited_player_ammunition_detail(
    app: Any, browser: Any, source_id: int,
) -> None:
    """The linked canonical destination must itself render the reviewed rule."""
    mapping = load_ammunition_reference_map()[source_id]
    slug = mapping["segments"][0]["ruleId"].split(":", 1)[1]
    published = _api(app, f"/api/ammunition/{slug}")
    assert len(published["rules"]) == 1
    rule = published["rules"][0]
    assert rule["id"] == f"ammunition:{slug}"
    assert rule["citations"]

    page = browser.new_page(viewport={"width": 390, "height": 844})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/ammunition/{slug}", wait_until="domcontentloaded")
        article = page.locator(
            f"#item-content article#rule-ammunition-{slug}"
        )
        article.wait_for(state="visible", timeout=20000)
        assert page.locator("#item-name").inner_text().strip().removesuffix(".") == (
            published["name"]
        )
        assert article.locator("header h3").inner_text().strip() == rule["name"]
        assert article.locator(".rules-source-citations a").count() == len(
            rule["citations"]
        )
        assert "InfinityDB-maintained reference" in article.inner_text()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
@pytest.mark.parametrize(
    "slug,source_id,components,saving,rolls",
    SAMPLES,
)
def test_reviewed_components_and_shared_rules_render_from_published_api(
    app: Any, browser: Any, slug: str, source_id: int,
    components: tuple[str, str], saving: str, rolls: str,
    width: int, height: int,
) -> None:
    api_profile = _profile(_api(app, f"/api/weapons/{slug}"), source_id)
    assert api_profile["saving"] == saving
    assert str(api_profile["saving_num"]) == rolls
    expected_links = [f"/ammunition/{key}" for key in components]
    assert api_profile["ammunition_composition"]["kind"] == "combined"
    assert [
        part["public_reference"]["id"]
        for part in api_profile["ammunition_composition"]["components"]
    ] == list(components)
    assert [effect["record_id"] for effect in api_profile["ammunition_effects"]] == [
        f"ammunition:{key}" for key in components
    ]
    assert all(effect["citations"] for effect in api_profile["ammunition_effects"])

    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/weapons/{slug}", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector("
            "'.weapon-profile .weapon-statline tbody tr') !== null",
            timeout=20000,
        )
        cards = page.locator(".weapon-profile").filter(
            has=page.locator(".weapon-statline td[data-label='Ammunition']")
            .filter(has_text=api_profile["ammunition"])
        )
        if api_profile.get("mode"):
            cards = cards.filter(
                has=page.locator("h4").filter(has_text=api_profile["mode"])
            )
        assert cards.count() == 1, (slug, source_id, api_profile.get("mode"))
        card = cards.first
        ammo_cell = card.locator(".weapon-statline td[data-label='Ammunition']")
        assert ammo_cell.inner_text().replace(" ", "") == api_profile[
            "ammunition"
        ].replace(" ", "")
        assert ammo_cell.locator("a").evaluate_all(
            "(links) => links.map((link) => link.getAttribute('href'))"
        ) == expected_links
        assert card.locator(".weapon-statline td[data-label='Saving']").inner_text() == (
            f"{saving} × {rolls}"
        )
        details = card.locator(".weapon-ammunition-effects")
        assert details.count() == 1
        assert details.locator("summary").inner_text() == "Ammunition effects (shared rules)"
        details.evaluate("(element) => element.open = true")
        effects = details.locator(".weapon-ammunition-effect")
        assert effects.count() == len(components)
        for index, effect in enumerate(api_profile["ammunition_effects"]):
            item = effects.nth(index)
            assert item.locator("h5 a").get_attribute("href") == expected_links[index]
            assert item.locator("p.detail-copy").inner_text().strip() == (
                _display_summary(effect["summary"])
            )
            assert item.locator(".detail-source").inner_text().strip()
            assert item.locator(".detail-source a").count() == len(effect["citations"])
            assert item.locator("h5").inner_text().strip() == effect["name"]
        assert "Shared components only" in details.inner_text()
        assert "Follow the printed Weapon profile" in details.inner_text()
        assert "immunity" not in card.get_attribute("class").lower()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844), (320, 640)])
def test_plasma_saving_attribute_pair_is_not_displayed_as_combined_ammunition(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    payload = _api(app, "/api/weapons/plasma-rifle")
    profiles = payload["profiles"] + [
        p for variant in payload.get("weapon_variants", [])
        for p in variant.get("profiles", [])
    ]
    assert profiles
    assert all("ammunition_composition" not in p for p in profiles)
    assert all(p["ammunition"] == "N" for p in profiles)
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    try:
        page.goto(f"{ORIGIN}/weapons/plasma-rifle", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelector("
            "'.weapon-profile .weapon-statline tbody tr') !== null",
            timeout=20000,
        )
        cells = page.locator(".weapon-profile .weapon-statline td[data-label='Ammunition']")
        assert cells.count() > 0
        for i in range(cells.count()):
            assert cells.nth(i).inner_text().strip() == "N"
            assert cells.nth(i).locator('a[href="/ammunition/normal"]').count() == 1
        saving_cells = page.locator(
            ".weapon-profile .weapon-statline td[data-label='Saving']"
        )
        assert saving_cells.count() > 0
        assert saving_cells.first.inner_text().startswith("ARM and BTS")
        assert not page.locator('.weapon-profile .weapon-statline a[href="/ammunition/ap"]').count()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
    finally:
        page.close()
