"""Chromium acceptance for Weapon and Equipment profiles and source conflicts."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from typing import Any
from urllib.request import urlopen
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
        "127.0.0.1", 0, app,
        server_class=_ThreadedServer, handler_class=_QuietHandler,
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


CASES = (
    ("d-charges", "weapon:d-charges", {"CC Mode", "Demolition Mode"}, {70, 186}),
    ("disco-baller", "weapon:disco-baller", {None, "Disco Ball"}, {71, 186}),
)


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize(("slug", "rule_id", "modes", "pages"), CASES)
def test_pinned_weapon_modes_rules_links_and_citations(
    origin: str, chrome: Any, width: int, slug: str, rule_id: str,
    modes: set[str | None], pages: set[int],
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        response = page.request.get(f"{origin}/api/weapons/{slug}")
        assert response.status == 200
        item = response.json()
        profiles = item["profiles"]
        assert len(profiles) == 2
        assert {profile["mode"] for profile in profiles} == modes
        rule = next(rule for rule in item["rules"] if rule["id"] == rule_id)
        assert pages <= {
            citation["page"] for citation in rule["citations"]
            if citation["source_id"] == "n5-core-v5.3-pdf"
        }
        variants = item["weapon_variants"]
        expected_profile_titles = [
            profile.get("mode") or profile.get("name") or variant["name"]
            for variant in variants for profile in variant["profiles"]
        ]
        assert len(expected_profile_titles) == 2

        route = f"{origin}/weapons/{slug}#rule-{rule_id.replace(':', '-')}"
        page.goto(route, wait_until="domcontentloaded")
        page.locator("#item-content").wait_for(state="visible", timeout=60000)
        cards = page.locator(".weapon-variant .weapon-profile")
        assert cards.count() == 2, (slug, width)
        assert [card.locator("h4").first.text_content() for card in cards.all()] == (
            expected_profile_titles
        )
        for card, profile in zip(cards.all(), (
            profile for variant in variants for profile in variant["profiles"]
        ), strict=True):
            stat = card.locator(".weapon-statline tbody tr").first
            assert stat.locator('td[data-label="B"]').text_content() == str(profile["burst"])
            assert stat.locator('td[data-label="PS"]').text_content() == str(profile["damage"])
            assert card.locator("h4").first.is_visible()
            if profile.get("profile"):
                assert profile["profile"] in card.inner_text()

        article = page.locator(f'[id="rule-{rule_id.replace(":", "-")}"]')
        article.wait_for(state="visible", timeout=10000)
        assert article.count() == 1
        visible_text = article.inner_text()
        assert all(f"p. {number}" in visible_text for number in pages)
        assert "[[" not in visible_text  # Maintained semantic links must render as UI.
        for relation in rule.get("display_relations", []):
            if not relation.get("presentation"):
                continue
            reference = relation["record"].get("public_reference") or {}
            href = reference.get("href")
            if not href and reference.get("catalog") and reference.get("id"):
                href = f"/{reference['catalog']}/{reference['id']}"
            if href:
                assert article.locator(".rules-relations a").evaluate_all(
                    "(links, href) => links.some(link => link.getAttribute('href') === href)",
                    href,
                ), (slug, width, relation["record"]["id"], href)
        assert not errors, (slug, width, errors)
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), (slug, width)
    finally:
        page.close()

@pytest.fixture(scope="module")
def published_weapons(origin: str) -> list[dict[str, Any]]:
    """Read every published Weapon detail once for storage/API/browser checks."""
    def get(path: str) -> dict[str, Any]:
        with urlopen(f"{origin}{path}", timeout=15) as response:
            assert response.status == 200, path
            return json.load(response)

    items = get("/api/weapons")["items"]
    assert len(items) >= 50, "Pinned Weapon catalog unexpectedly sparse"
    details = [get(f"/api/weapons/{item['slug']}") for item in items]
    assert [detail["slug"] for detail in details] == [item["slug"] for item in items]
    return details


@pytest.fixture(scope="module")
def multi_profile_weapons(published_weapons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details = []
    for detail in published_weapons:
        profiles = [
            profile for variant in detail.get("weapon_variants", [])
            for profile in variant.get("profiles", [])
        ]
        assert len(profiles) == len(detail["profiles"]), detail["slug"]
        if len(profiles) > 1:
            details.append(detail)
    assert len(details) >= 2, "Pinned catalog unexpectedly lacks multi-profile Weapons"
    return details


def _saving_display(profile: dict[str, Any]) -> str:
    saving = profile.get("saving")
    if saving is None or str(saving).strip() in ("", "-", "--"):
        return "--"
    return " × ".join(
        str(value) for value in (saving, profile.get("saving_num"))
        if value is not None and value != ""
    )


def _stat_display(value: Any) -> str:
    return "—" if value is None or value == "" else str(value)


def _ammunition_display(profile: dict[str, Any]) -> str:
    if profile.get("ammunition") == 0:
        return "--"
    if isinstance(profile.get("ammunition_parts"), list):
        return "".join(part["text"] for part in profile["ammunition_parts"])
    return _stat_display(profile.get("ammunition"))


def test_all_published_multi_profile_weapon_statlines_render_on_mobile(
    origin: str, chrome: Any, multi_profile_weapons: list[dict[str, Any]],
) -> None:
    """All published multi-profile source rows must reach their own rendered card."""
    page = chrome.new_page(viewport={"width": 390, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for weapon in multi_profile_weapons:
            slug = weapon["slug"]
            expected = [
                [
                    profile.get("mode") or profile.get("name") or variant["name"],
                    _ammunition_display(profile),
                    _stat_display(profile.get("burst")),
                    _stat_display(profile.get("damage")),
                    _saving_display(profile),
                    profile.get("profile") or "",
                ]
                for variant in weapon["weapon_variants"]
                for profile in variant["profiles"]
            ]
            page.goto(f"{origin}/weapons/{slug}", wait_until="domcontentloaded")
            page.locator("#item-content").wait_for(state="visible", timeout=15000)
            actual = page.locator(".weapon-variant .weapon-profile").evaluate_all(
                """(cards) => cards.map((card) => {
                  const cell = (label) => card.querySelector(
                    '.weapon-statline tbody td[data-label="' + label + '"]'
                  )?.textContent ?? '';
                  const profileRow = [...card.querySelectorAll('.weapon-data-row')].find(
                    row => row.querySelector('.weapon-data-heading')?.textContent === 'Profile'
                  );
                  return [
                    card.querySelector('h4')?.textContent ?? '',
                    cell('Ammunition'), cell('B'), cell('PS'), cell('Saving'),
                    profileRow?.querySelector('.weapon-data-value')?.textContent ?? ''
                  ];
                })"""
            )
            assert actual == expected, (slug, actual, expected)
            source_profiles = [
                profile for variant in weapon["weapon_variants"]
                for profile in variant["profiles"]
            ]
            for card, profile in zip(
                page.locator(".weapon-variant .weapon-profile").all(),
                source_profiles,
                strict=True,
            ):
                expected_modifiers = _expected_range_modifiers(profile)
                assert card.locator(".weapon-ranges tbody td").all_text_contents() == (
                    expected_modifiers if any(expected_modifiers) else []
                ), (slug, profile["mode"], expected_modifiers)
                parts = profile.get("ammunition_parts")
                if not isinstance(parts, list):
                    continue
                expected_links = []
                for part in parts:
                    reference = part.get("public_reference") or {}
                    href = reference.get("href")
                    if not href and reference.get("catalog") and reference.get("id"):
                        href = f"/{reference['catalog']}/{reference['id']}"
                    if href:
                        expected_links.append((part["text"], href))
                links = card.locator('.weapon-statline td[data-label="Ammunition"] a')
                actual_links = [
                    (link.text_content(), link.get_attribute("href"))
                    for link in links.all()
                ]
                assert actual_links == expected_links, (slug, profile["mode"])
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), slug
        assert not errors, errors
    finally:
        page.close()

def test_published_weapon_profiles_preserve_source_metadata(
    published_weapons: list[dict[str, Any]],
) -> None:
    """Full published source-row parity; curated rules remain a separate layer."""
    root = Path(__file__).resolve().parents[1]
    source_rows: dict[tuple[int, str | None], list[dict[str, Any]]] = defaultdict(list)
    with sqlite3.connect(
        f"{(root / 'data/generated/infinity.db').resolve().as_uri()}?mode=ro",
        uri=True,
    ) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, name, mode, type, ammunition, burst, damage, "
            "saving, savingNum, profile, properties, distance "
            "FROM metadata_weapons"
        ).fetchall()
    for row in rows:
        source_rows[(row["id"], row["mode"])].append(dict(row))

    checked = 0
    profileless = []
    for weapon in published_weapons:
        flat = [
            profile for variant in weapon["weapon_variants"]
            for profile in variant["profiles"]
        ]
        assert flat == weapon["profiles"], weapon["slug"]
        if not flat:
            profileless.append(weapon["slug"])
            continue
        for profile in flat:
            key = (profile["id"], profile["mode"])
            candidates = source_rows.get(key, [])
            assert candidates, (weapon["slug"], key)
            comparable = {
                "id": profile["id"],
                "name": profile["name"],
                "mode": profile["mode"],
                "type": profile["type"],
                "ammunition": profile["ammunition_source_id"],
                "burst": profile["burst"],
                "damage": profile["damage"],
                "saving": profile["saving"],
                "savingNum": profile["saving_num"],
                "profile": profile["profile"],
            }
            matching = [
                row for row in candidates
                if all(row[column] == value for column, value in comparable.items())
            ]
            assert matching, (weapon["slug"], key, comparable, candidates)
            source = matching[0]
            for source_column, api_key, default in (
                ("properties", "traits", []),
                ("distance", "ranges", {}),
            ):
                raw = source[source_column]
                decoded = json.loads(raw) if isinstance(raw, str) else (
                    default if raw is None else raw
                )
                assert decoded == profile[api_key], (
                    weapon["slug"], key, api_key, decoded, profile[api_key]
                )
            checked += 1
    assert checked >= 100, checked
    # SymbioBomb has a reviewed rules card but no standalone chart statline.
    assert "symbiobomb" in profileless



def _expected_range_modifiers(profile: dict[str, Any]) -> list[str]:
    ranges = sorted(
        (
            band for band in (profile.get("ranges") or {}).values()
            if isinstance(band, dict) and band.get("max") is not None
        ),
        key=lambda band: float(band["max"]),
    )
    modifiers = []
    for maximum in (20, 40, 60, 80, 100, 120, 240):
        matching = next(
            (band for band in ranges if float(band["max"]) >= maximum),
            None,
        )
        modifiers.append(
            "" if matching is None and not ranges
            else "--" if matching is None
            else str(matching["mod"]) if matching.get("mod") is not None
            else ""
        )
    return modifiers


@pytest.mark.parametrize("shard", [0, 1, 2])
def test_all_published_single_profile_weapon_cards_at_mobile_width(
    origin: str, chrome: Any, published_weapons: list[dict[str, Any]], shard: int,
) -> None:
    """Shard the full published single-profile browser audit for bounded check runs."""
    singles = [weapon for weapon in published_weapons if len(weapon["profiles"]) == 1]
    assert len(singles) >= 20, len(singles)
    selected = singles[shard::3]
    assert selected
    page = chrome.new_page(viewport={"width": 390, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for weapon in selected:
            slug = weapon["slug"]
            (variant,) = weapon["weapon_variants"]
            (profile,) = variant["profiles"]
            page.goto(f"{origin}/weapons/{slug}", wait_until="domcontentloaded")
            page.locator("#item-content").wait_for(state="visible", timeout=15000)
            cards = page.locator(".weapon-variant .weapon-profile")
            assert cards.count() == 1, slug
            card = cards.first
            observed = card.evaluate(
                """(card) => {
                  const cell = label => card.querySelector(
                    '.weapon-statline tbody td[data-label="' + label + '"]'
                  )?.textContent ?? '';
                  const profileRow = [...card.querySelectorAll('.weapon-data-row')].find(
                    row => row.querySelector('.weapon-data-heading')?.textContent === 'Profile'
                  );
                  return [
                    card.querySelector('h4')?.textContent ?? '',
                    cell('Ammunition'), cell('B'), cell('PS'), cell('Saving'),
                    profileRow?.querySelector('.weapon-data-value')?.textContent ?? ''
                  ];
                }"""
            )
            expected = [
                profile.get("mode") or profile.get("name") or variant["name"],
                _ammunition_display(profile),
                _stat_display(profile.get("burst")),
                _stat_display(profile.get("damage")),
                _saving_display(profile),
                profile.get("profile") or "",
            ]
            assert observed == expected, (slug, observed, expected)

            source_modifiers = _expected_range_modifiers(profile)
            rendered_range = card.locator(".weapon-ranges tbody td").all_text_contents()
            assert rendered_range == (
                source_modifiers if any(source_modifiers) else []
            ), (slug, rendered_range, source_modifiers)

            parts = profile.get("ammunition_parts")
            if isinstance(parts, list):
                expected_links = []
                for part in parts:
                    reference = part.get("public_reference") or {}
                    href = reference.get("href")
                    if not href and reference.get("catalog") and reference.get("id"):
                        href = f"/{reference['catalog']}/{reference['id']}"
                    if href:
                        expected_links.append((part["text"], href))
                actual_links = [
                    (link.text_content(), link.get_attribute("href"))
                    for link in card.locator(
                        '.weapon-statline td[data-label="Ammunition"] a'
                    ).all()
                ]
                assert actual_links == expected_links, (slug, actual_links, expected_links)
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), slug
        assert not errors, errors
    finally:
        page.close()


def test_profileless_symbiobomb_still_exposes_reviewed_rules(
    origin: str, chrome: Any, published_weapons: list[dict[str, Any]],
) -> None:
    weapon = next(weapon for weapon in published_weapons if weapon["slug"] == "symbiobomb")
    assert weapon["profiles"] == []
    assert any(rule["id"] == "weapon:symbiobomb" for rule in weapon["rules"])
    page = chrome.new_page(viewport={"width": 390, "height": 900})
    try:
        page.goto(f"{origin}/weapons/symbiobomb", wait_until="domcontentloaded")
        page.locator("#item-content").wait_for(state="visible", timeout=15000)
        assert page.locator(".weapon-variant .weapon-profile").count() == 0
        article = page.locator('[id="rule-weapon-symbiobomb"]')
        article.wait_for(state="visible")
        assert "SymbioBomb" in article.inner_text()
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_kobra_conflicting_sources_stay_visible_on_cc_mode_only(
    origin: str, chrome: Any, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    try:
        page.goto(f"{origin}/weapons/kobra-pistol", wait_until="domcontentloaded")
        page.locator("#item-content").wait_for(state="visible", timeout=15000)
        bs = page.locator(".weapon-profile").filter(
            has=page.get_by_role("heading", name="BS Mode", exact=True)
        )
        cc = page.locator(".weapon-profile").filter(
            has=page.get_by_role("heading", name="CC Mode", exact=True)
        )
        assert bs.count() == cc.count() == 1
        assert bs.locator('[id="rule-weapon-kobra-pistol-cc"]').count() == 0
        assert bs.locator('td[data-label="Ammunition"]').inner_text() == "Shock"
        assert cc.locator('td[data-label="Saving"]').inner_text() == "ARM × 2"
        card = cc.locator('[id="rule-weapon-kobra-pistol-cc"]')
        card.wait_for(state="visible")
        notes = card.locator(".rules-source-note").all_inner_texts()
        assert len(notes) == 2
        assert "Saving Rolls" in notes[0]
        assert "publication conflict unresolved" in notes[1]
        assert "Anti-materiel" in notes[1]
        assert "p. 182" in card.inner_text()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), width
    finally:
        page.close()

def test_katyusha_pdf_unsigned_mod_keeps_reviewed_plus_three_in_browser(
    origin: str, chrome: Any,
) -> None:
    root = Path(__file__).resolve().parents[1]
    review = json.loads(
        (root / "config/validation/weapon-range-source-review.json")
        .read_text(encoding="utf-8")
    )
    (candidate,) = review["candidates"]
    assert candidate["name"] == "Katyusha MRL"
    assert candidate["pdfUnsignedLabel"] == "3"
    assert candidate["resolvedRangeMod"] == "+3"
    assert candidate["classification"] == "confirmed-pdf-sign-omission"
    page = chrome.new_page(viewport={"width": 390, "height": 900})
    try:
        page.goto(f"{origin}/weapons/katyusha-mrl", wait_until="domcontentloaded")
        page.locator("#item-content").wait_for(state="visible", timeout=15000)
        actual = page.locator(
            ".weapon-profile .weapon-ranges tbody td"
        ).all_inner_texts()
        assert actual == ["-3", "+3", "+3", "0", "0", "-6", "--"]
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
    finally:
        page.close()


@pytest.mark.parametrize("slug", (
    "ap-mine", "e-m-mine", "monofilament-mine",
    "para-mine", "shock-mine", "viral-mine",
))
def test_mine_object_silhouette_sources_remain_disclosed(
    origin: str, chrome: Any, slug: str,
) -> None:
    page = chrome.new_page(viewport={"width": 390, "height": 900})
    try:
        page.goto(f"{origin}/weapons/{slug}", wait_until="domcontentloaded")
        rule = page.locator('[id="rule-weapon-mines"]')
        rule.wait_for(state="visible", timeout=15000)
        note = rule.locator(".rules-source-note").first
        assert note.is_visible()
        content = note.inner_text()
        assert "S0" in content and "S1" in content
        assert "No official correction or source precedence has been confirmed" in content
    finally:
        page.close()

# The auxiliary Weapon Chart object names are not necessarily the item carried by
# a Trooper (notably Disco Ball/Disco Baller). Keep their source identity and
# deployed object's mode separate. The tuple pins Army's S, not source precedence.
AUXILIARY_OBJECTS = (
    ("AP Mine", None, 1, 181),
    ("Cybermine", None, 0, 181),
    ("Drop Bears", "Deployable Mode", 0, 181),
    ("E/M Mine", None, 1, 181),
    ("Monofilament Mine", None, 1, 181),
    ("PARA Mine", None, 1, 181),
    ("Shock Mine", None, 1, 181),
    ("Viral Mine", None, 1, 181),
    ("WildParrot", None, 1, 181),
    ("Crazykoala", None, 1, 186),
    ("Dazer", None, 0, 186),
    ("Deployable Repeater", None, 1, 186),
    ("Disco Baller", "Disco Ball", 1, 186),
    ("FastPanda", None, 1, 186),
)


@pytest.mark.parametrize("width", [1440, 390])
def test_all_chart_auxiliary_objects_have_catalog_profile_in_normal_browser(
    origin: str, chrome: Any, published_weapons: list[dict[str, Any]], width: int,
) -> None:
    """The 14 pinned chart objects are reachable without picking a carrier Unit.

    This validates Army profile preservation, not precedence when official
    publications conflict (six Mines and Dazer).
    """
    import re

    assert len(AUXILIARY_OBJECTS) == 14
    by_name = {weapon["name"].casefold(): weapon for weapon in published_weapons}
    page = chrome.new_page(viewport={"width": width, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for name, mode, army_s, pdf_page in AUXILIARY_OBJECTS:
            if name in {"Dazer", "Deployable Repeater", "FastPanda"}:
                # These object identities are Equipment, not Weapon carriers.
                assert name.casefold() not in by_name
                slug = name.casefold().replace(" ", "-")
                response = page.request.get(f"{origin}/api/equipment/{slug}")
                assert response.status == 200
                equipment = response.json()
                assert any(rule["id"] == f"equipment:{slug}" for rule in equipment["rules"])
                page.goto(f"{origin}/equipment/{slug}", wait_until="domcontentloaded")
                rule_card = page.locator(f'[id="rule-equipment-{slug}"]')
                rule_card.wait_for(state="visible", timeout=15000)
                content = rule_card.inner_text()
                if name == "Dazer":
                    note = rule_card.locator(".rules-source-note").first
                    assert "S0" in note.inner_text() and "S1" in note.inner_text()
                    assert "ARM 0, BTS 0 and STR 1" in content
                elif name == "Deployable Repeater":
                    assert "ARM 0, BTS 0, STR 1 and S 1" in content
                else:
                    assert "ARM 0, BTS 0, STR 1, S 1" in content
                matching = [
                    profile for profile in equipment.get("profiles", [])
                    if profile.get("mode") == mode
                ]
                assert len(matching) == 1, (name, mode)
                (profile,) = matching
                source_text = profile["profile"]
                assert source_text
                attributes = {
                    key: int(value)
                    for key, value in re.findall(
                        r"\b(ARM|BTS|STR|S)\s*=\s*(\d+)\b", source_text
                    )
                }
                assert attributes == {"ARM": 0, "BTS": 0, "STR": 1, "S": army_s}
                cards = page.locator(".weapon-variant .weapon-profile").filter(
                    has=page.get_by_role(
                        "heading", name=mode or profile["name"], exact=True
                    )
                )
                assert cards.count() == 1, (name, mode)
                assert source_text in cards.first.inner_text()
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
                ), (name, width)
                continue
            weapon = by_name[name.casefold()]
            source_profiles = [
                p for variant in weapon["weapon_variants"]
                for p in variant["profiles"]
                if p["mode"] == mode
            ]
            assert len(source_profiles) == 1, (name, mode, pdf_page)
            (profile,) = source_profiles
            source_text = profile["profile"]
            assert isinstance(source_text, str) and source_text, (name, mode)
            attributes = {
                key: int(value)
                for key, value in re.findall(r"\b(ARM|BTS|STR|S)\s*=\s*(\d+)\b", source_text)
            }
            assert attributes == {"ARM": 0, "BTS": 0, "STR": 1, "S": army_s}, name

            page.goto(
                f"{origin}/weapons/{weapon['slug']}",
                wait_until="domcontentloaded",
            )
            page.locator("#item-content").wait_for(state="visible", timeout=15000)
            cards = page.locator(".weapon-variant .weapon-profile")
            candidates = cards.filter(
                has=page.get_by_role(
                    "heading", name=mode or profile["name"], exact=True,
                )
            )
            assert candidates.count() == 1, (name, mode)
            card = candidates.first
            profile_rows = card.locator(".weapon-data-row").filter(
                has=page.get_by_role("heading", name="Profile", exact=True)
            )
            assert profile_rows.count() == 1, (name, mode)
            assert source_text in profile_rows.first.inner_text(), (name, source_text)
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), (name, width)
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_armed_turret_curated_object_profile_keeps_source_conflict_visible(
    origin: str, chrome: Any, width: int,
) -> None:
    """Armed Turret has a curated Trooper profile, not a Weapon Chart object row."""
    page = chrome.new_page(viewport={"width": width, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        response = page.request.get(f"{origin}/api/weapons/armed-turret")
        assert response.status == 200
        weapon = response.json()
        profile = weapon["special_profile"]
        assert dict(profile["stats"])["S"] == "2"
        assert dict(profile["stats"])["ARM"] == "2"
        assert dict(profile["stats"])["BTS"] == "3"
        assert dict(profile["stats"])["STR"] == "1"

        page.goto(f"{origin}/weapons/armed-turret", wait_until="domcontentloaded")
        card = page.locator(".special-weapon-profile")
        card.wait_for(state="visible", timeout=15000)
        observed = card.evaluate(
            """(element) => [...element.querySelectorAll('thead th')].map(
              (th, index) => [
                th.textContent,
                element.querySelectorAll('tbody td')[index]?.textContent
              ]
            )"""
        )
        assert observed == profile["stats"]
        assert "360º Visor" in card.inner_text()
        assert "Total Reaction" in card.inner_text()
        assert profile["cc_weapon"] in card.inner_text()

        rule = page.locator('[id="rule-weapon-armed-turret"]')
        rule.wait_for(state="visible", timeout=15000)
        notes = rule.locator(".rules-source-note").all_inner_texts()
        assert len(notes) >= 2
        assert "S1" in notes[0] and "S2" in notes[0]
        assert "Unresolved Silhouette conflict" in notes[0]
        assert "one Saving Roll" in notes[1]
        assert not errors, errors
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), width
    finally:
        page.close()





