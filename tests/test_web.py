from __future__ import annotations

import json
import re
import shutil
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_army_data.merge import make_source, merge_sources
from infinity_army_data.normalize import normalize_master
from infinity_db.database import export_database
from infinity_db.web import create_app


def request(
    app: Callable,
    path: str,
    *,
    query: str = "",
    method: str = "GET",
    request_headers: Mapping[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(path)
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(
        PATH_INFO=parsed.path,
        QUERY_STRING=query or parsed.query,
        REQUEST_METHOD=method,
    )
    if request_headers:
        environ.update(
            {
                f"HTTP_{name.upper().replace('-', '_')}": value
                for name, value in request_headers.items()
            }
        )
    response: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]], exc_info=None) -> None:
        response["status"] = int(status.split()[0])
        response["headers"] = {name.lower(): value for name, value in headers}

    result: Iterator[bytes] = app(environ, start_response)
    try:
        body = b"".join(result)
    finally:
        if hasattr(result, "close"):
            result.close()
    return response["status"], response["headers"], body


@pytest.fixture
def app(tmp_path: Path) -> Callable:
    shared = {
        "id": 1,
        "name": "Alpha Ranger",
        "isc": "Explorer Prototype",
        "slug": "ranger-prototype",
        "canonical": 999,
        "factions": [101],
        "profileGroups": [
            {
                "id": 1,
                "category": 1,
                "profiles": [
                    {
                        "id": 1,
                        "name": "Ranger Profile",
                        "type": 1,
                        "skills": [{"id": 11, "extra": [41]}],
                        "equip": [{"id": 21, "q": 2, "extra": [42]}],
                        "weapons": [{"id": 31, "extra": [43]}],
                    }
                ],
                "options": [
                    {
                        "id": 1,
                        "name": "Rifle loadout",
                        "points": 20,
                        "swc": "0",
                        "skills": [{"id": 11, "extra": [41]}],
                        "equip": [{"id": 21, "extra": [42]}],
                        "weapons": [{"id": 31, "q": 2, "extra": [43]}],
                        "orders": [{"type": "regular", "list": 1, "total": 1}],
                    }
                ],
            }
        ],
    }
    # Declared factions and canonical ownership deliberately differ from actual occurrences.
    blue_only = {
        "id": 3,
        "name": "100%_Guard",
        "canonical": 1,
        "factions": [201],
    }
    red_only = {"id": 2, "name": "Beta Scout", "canonical": 1, "factions": [201]}
    specops_only = {
        "id": 4,
        "name": "Alpha Spec-Ops",
        "slug": "alpha-spec-ops",
        "canonical": 101,
        "factions": [101],
    }
    teamops_only = {
        "id": 5,
        "name": "Alpha Team Ops",
        "slug": "alpha-team-ops",
        "canonical": 101,
        "factions": [101],
    }
    reinforcement_only = {
        "id": 6,
        "name": "Alpha Reinforcement",
        "canonical": 101,
        "factions": [101],
    }
    documents = [
        ("101-zulu_company.json", [shared, blue_only, specops_only, teamops_only], True),
        ("201-alpha_company.json", [shared, red_only], True),
        ("198-zulu_reinforcements.json", [reinforcement_only], False),
    ]
    sources = []
    for filename, units, is_army in documents:
        document = {
            "version": "test",
            "units": units,
            "filters": {
                "category": [{"id": 1, "name": "Light Infantry"}],
                "type": [{"id": 1, "name": "Line Trooper"}],
                "skills": [{"id": 11, "name": "Stealth"}],
                "equip": [{"id": 21, "name": "Medikit"}],
                "weapons": [{"id": 31, "name": "Combi Rifle"}],
                "extras": [
                    {"id": 41, "name": "+3"},
                    {"id": 42, "name": "Mimetism"},
                    {"id": 43, "name": "AP"},
                ],
            },
        }
        if is_army:
            document["reinforcements"] = None
        if filename.startswith("101-"):
            # This unresolved reference becomes a placeholder, not a browsable unit.
            document["relations"] = [{"units": [{"unit": 9099}]}]
        raw = json.dumps(document)
        source = make_source(filename, raw.encode())
        assert source is not None
        sources.append(source)
    normalized = normalize_master(merge_sources(sources))
    normalized["armyMetadata"] = {
        "sourceFile": "metadata.json",
        "sourceSha256": "test-metadata",
        "data": {"factions": []},
    }
    normalized["tables"]["metadata_equipment"] = [
        {"id": 21, "name": "Medikit", "wiki": "https://infinitythewiki.com/Medikit"}
    ]
    normalized["_meta"]["snapshotDownloadedOn"] = "2026-09-10"
    database_path = tmp_path / "infinity.db"
    export_database(normalized, database_path)
    return create_app(database_path)


def test_armies_list_contains_actual_armies_and_counts(app: Callable) -> None:
    status, headers, body = request(app, "/api/armies")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    armies = {item["id"]: item for item in json.loads(body)["items"]}
    assert set(armies) == {101, 198, 201}
    assert [army["id"] for army in json.loads(body)["items"]] == [101, 198, 201]
    assert armies[101]["slug"] == "zulu_company"
    assert armies[101]["name"]
    assert armies[101]["kind"] == "army"
    assert {army["unit_count"] for army in armies.values()} == {1, 2, 4}


def test_army_filter_uses_actual_occurrences(app: Callable) -> None:
    for army_id, expected in [(101, {1, 3}), (201, {1, 2})]:
        status, _, body = request(
            app, "/api/units", query=urlencode({"army_id": army_id, "mercs": 1})
        )
        assert status == 200
        payload = json.loads(body)
        assert payload["total"] == 2
        assert {item["id"] for item in payload["items"]} == expected
        shared = next(item for item in payload["items"] if item["id"] == 1)
        assert set(shared["army_ids"]) == {101, 201}
        assert {army["id"] for army in shared["armies"]} == {101, 201}


def test_global_pagination_counts_unique_units(app: Callable) -> None:
    status, _, body = request(app, "/api/units")
    assert status == 200
    all_units = json.loads(body)
    assert all_units["total"] == 2
    assert all_units["limit"] == 50
    assert all_units["offset"] == 0
    expected_ids = [item["id"] for item in all_units["items"]]
    assert len(set(expected_ids)) == 2

    paged_ids = []
    for offset in range(3):
        status, _, body = request(app, "/api/units", query=f"limit=1&offset={offset}")
        assert status == 200
        page = json.loads(body)
        assert (page["total"], page["limit"], page["offset"]) == (2, 1, offset)
        paged_ids.extend(item["id"] for item in page["items"])
    assert paged_ids == expected_ids

    status, _, body = request(app, "/api/units", query="order=desc")
    assert status == 200
    assert [item["id"] for item in json.loads(body)["items"]] == list(reversed(expected_ids))


def test_optional_unit_modes_are_excluded_until_selected(app: Callable) -> None:
    status, _, body = request(app, "/api/units", query="army_id=101")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1}

    status, _, body = request(app, "/api/units", query="army_id=101&mercs=1")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1, 3}

    status, _, body = request(app, "/api/units", query="army_id=101&specops=1")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1, 4}

    status, _, body = request(app, "/api/units", query="army_id=101&teamops=1")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1, 5}

    status, _, body = request(app, "/api/units", query="army_id=101&mercs=1&specops=1&teamops=1")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1, 3, 4, 5}

    status, _, body = request(app, "/api/units", query="army_id=201")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1, 2}

    status, _, body = request(app, "/api/units", query="army_id=198")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == set()

    status, _, body = request(app, "/api/units", query="army_id=198&reinforcement=1")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {6}


def test_unit_details_are_available_by_id(app: Callable) -> None:
    status, _, body = request(app, "/api/units/1")
    assert status == 200
    unit = json.loads(body)
    assert unit["name"] == "Alpha Ranger"
    assert {army["id"] for army in unit["armies"]} == {101, 201}
    for army in unit["armies"]:
        assert army["profiles"][0]["type"] == "Line Trooper"
        assert army["profiles"][0]["classification"] == "Light Infantry"
        assert army["profiles"][0]["skills"] == [
            {
                "id": 11,
                "name": "Stealth",
                "quantity": None,
                "extras": [{"id": 41, "name": "+3"}],
            }
        ]
        assert army["profiles"][0]["equipment"] == [
            {
                "id": 21,
                "name": "Medikit",
                "quantity": 2,
                "extras": [{"id": 42, "name": "Mimetism"}],
            }
        ]
        assert army["profiles"][0]["weapons"] == [
            {
                "id": 31,
                "name": "Combi Rifle",
                "quantity": None,
                "extras": [{"id": 43, "name": "AP"}],
            }
        ]
        assert army["loadouts"][0]["orders"] == [{"type": "regular", "list": 1, "total": 1}]
        assert army["loadouts"][0]["skills"] == [
            {
                "id": 11,
                "name": "Stealth",
                "quantity": None,
                "extras": [{"id": 41, "name": "+3"}],
            }
        ]
        assert army["loadouts"][0]["equipment"] == [
            {
                "id": 21,
                "name": "Medikit",
                "quantity": None,
                "extras": [{"id": 42, "name": "Mimetism"}],
            }
        ]
        assert army["loadouts"][0]["weapons"] == [
            {
                "id": 31,
                "name": "Combi Rifle",
                "quantity": 2,
                "extras": [{"id": 43, "name": "AP"}],
            }
        ]
    status, headers, body = request(app, "/units/1")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"unit.js" in body
    assert b'aria-label="Project navigation"' in body
    assert b"Skip to unit details" in body
    status, _, body = request(app, "/api/units/9099")
    assert status == 404
    assert json.loads(body)["error"] == "Unit not found"


@pytest.mark.parametrize(
    ("unit_id", "expected_flags"),
    [
        (3, ["mercs"]),
        (4, ["specops"]),
        (5, ["teamops"]),
        (6, ["reinforcement"]),
    ],
)
def test_unit_details_include_occurrence_availability_categories(
    app: Callable,
    unit_id: int,
    expected_flags: list[str],
) -> None:
    status, _, body = request(app, f"/api/units/{unit_id}")
    assert status == 200
    unit = json.loads(body)
    assert unit["armies"][0]["availability_flags"] == expected_flags


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        ({"search": "ALPHA"}, {1}),
        ({"search": "explorer"}, {1}),
        ({"search": "profile"}, {1}),
        ({"search": "rifle loadout"}, {1}),
        ({"search": "%", "mercs": 1}, {3}),
        ({"search": "_", "mercs": 1}, {3}),
        ({"search": "' OR 1=1 --"}, set()),
        ({"search": "beta", "army_id": 101}, set()),
        ({"search": "beta", "army_id": 201}, {2}),
        ({"army_id": 999}, set()),
    ],
)
def test_unit_search_and_empty_results(
    app: Callable, query: dict[str, Any], expected_ids: set[int]
) -> None:
    status, _, body = request(app, "/api/units", query=urlencode(query))
    assert status == 200
    payload = json.loads(body)
    assert payload["total"] == len(expected_ids)
    assert {item["id"] for item in payload["items"]} == expected_ids


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=201",
        "limit=all",
        "offset=-1",
        "offset=1.5",
        "offset=9223372036854775808",
        "army_id=abc",
        "army_id=9223372036854775808",
        urlencode({"search": "x" * 201}),
    ],
)
def test_invalid_query_returns_json_error(app: Callable, query: str) -> None:
    status, headers, body = request(app, "/api/units", query=query)
    assert status == 400
    assert headers["content-type"].startswith("application/json")
    assert json.loads(body)["error"]


def test_largest_supported_offset_returns_empty_page(app: Callable) -> None:
    status, _, body = request(app, "/api/units", query="offset=9223372036854775807")
    assert status == 200
    assert json.loads(body)["items"] == []


def test_homepage_and_referenced_static_assets_are_served(app: Callable) -> None:
    status, headers, body = request(app, "/")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Your Infinity reference," in body
    assert b"in one place." in body
    assert b'aria-label="Project navigation"' in body
    assert b'href="/units"' in body
    assert b"Army snapshot downloaded" in body
    assert b"September 10, 2026" in body
    assert b'data-app-version="0.4.1"' in body
    assert b'data-snapshot-revision="' in body
    assert b"/static/version-check.js?v=0.4.1" in body
    assets = re.findall(r'(?:src|href)=["\'](/static/[^"\']+)', body.decode())
    assert assets
    for asset in assets:
        assert asset.endswith("?v=0.4.1")
        status, headers, body = request(app, asset)
        assert status == 200
        assert body
        assert int(headers["content-length"]) == len(body)
        head_status, head_headers, head_body = request(app, asset, method="HEAD")
        assert head_status == status
        assert head_headers == headers
        assert head_body == b""

    status, headers, body = request(app, "/units")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Unit explorer" in body
    assert b'href="/units" aria-current="page"' in body
    assert body.index(b'id="pagination-top"') < body.index(b'id="results"')
    assert body.index(b'id="results"') < body.index(b'id="pagination-bottom"')

    status, _, script = request(app, "/static/app.js")
    assert status == 200
    assert b'className = "page-results-summary"' in script


def test_browser_version_check_uses_an_uncached_server_version(app: Callable) -> None:
    status, headers, body = request(app, "/api/version")

    assert status == 200
    assert headers["cache-control"] == "no-store"
    version = json.loads(body)
    assert version["version"] == "0.4.1"
    assert len(version["snapshot_revision"]) == 64
    assert int(version["snapshot_revision"], 16) >= 0

    status, _, script = request(app, "/static/version-check.js")
    assert status == 200
    assert b'fetch("/api/version", { cache: "no-store" })' in script
    assert b"snapshot_revision: snapshotRevision" in script
    assert b"currentSnapshotRevision" in script
    assert b'freshUrl.searchParams.set("app-version", version || currentVersion)' in script
    assert b'freshUrl.searchParams.set("snapshot-revision", snapshotRevision)' in script
    assert b"window.location.replace(freshUrl)" in script


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/units",
        "/units/1",
        "/skills",
        "/skills/1",
        "/equipment",
        "/equipment/1",
        "/weapons",
        "/weapons/1",
        "/skill-extras",
        "/about",
    ],
)
def test_every_page_uses_the_shared_page_shell(app: Callable, path: str) -> None:
    status, _, body = request(app, path)

    assert status == 200
    assert b'<header class="topbar page-header">' in body
    assert b'aria-label="Breadcrumb"' in body
    assert b'<footer class="page-footer">' in body
    assert b"Version 0.4.1+dev" in body


def test_landing_hero_keeps_its_logo_with_the_heading_on_mobile(app: Callable) -> None:
    status, _, body = request(app, "/")

    assert status == 200
    assert b'<div class="landing-hero-heading">' in body
    assert body.index(b"landing-hero-heading") < body.index(b'class="landing-logo"')
    assert body.index(b'class="landing-logo"') < body.index(b"landing-hero-content")

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert b".landing-logo { grid-column: 2; grid-row: 1; align-self: start;" in styles
    assert b"width: min(30vw, 135px); height: auto;" in styles
    assert b".landing-hero-content { grid-column: 1 / -1; }" in styles


def test_mobile_unit_list_prioritizes_the_unit_name_column(
    app: Callable,
) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    assert b"thead th:last-child { width: 156px; }" in styles
    assert b".army-tags { --symbols-per-row: 4; }" in styles
    assert b".army-tags-compact { --symbols-per-row: 6; gap: 3px; }" in styles
    assert b".army-tags-compact .army-symbol { width: 17px; height: 17px; }" in styles

    status, _, unit_list = request(app, "/static/unit-list.js")
    assert status == 200
    assert b"if (armies.length > 12)" in unit_list


def test_intermediate_widths_reserve_space_for_movement_values(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    assert b"@media (min-width: 601px) and (max-width: 700px)" in styles
    assert b"--movement-column-width: 60px;" in styles
    assert (
        b'html[data-distance-unit="in"] .attribute-statline { --movement-column-width: 52px; }'
        in styles
    )
    assert (
        b"grid-template-columns: var(--movement-column-width) repeat(8, minmax(0, 1fr));" in styles
    )
    assert b".attribute-statline > div { padding-inline: 4px; }" in styles
    assert b"grid-template-columns: 60px repeat(4, minmax(0, 1fr));" in styles
    assert (
        b'html[data-distance-unit="in"] .attribute-statline-with-availability '
        b"{ grid-template-columns: 52px repeat(4, minmax(0, 1fr)); }" in styles
    )


def test_developer_mode_controls_database_id_visibility_in_settings_menu(
    app: Callable,
) -> None:
    status, _, body = request(app, "/units")

    assert status == 200
    assert b'id="developer-mode-toggle"' in body
    assert b'id="remember-settings-toggle"' in body
    assert b'id="cookie-consent-dialog"' in body
    assert b"Allow cookies" in body
    assert b'<div class="menu settings-menu" data-menu>' in body
    assert b'aria-controls="settings-menu"' in body
    assert b'>Settings <span aria-hidden="true">' in body
    assert body.index(b"compact-navigation-menu") < body.index(b"settings-menu")
    assert b'<th scope="col" class="id-column">Unit ID</th>' in body

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert b'html:not([data-developer-mode="true"]) .id-column { display: none; }' in styles
    assert b".settings-menu { margin-top: 32px; }" in styles
    assert b".compact-menu-panel { position: static; display: flex;" in styles
    assert b".menu-label { display: none; }" in styles
    assert b".sidebar { position: relative; z-index: 4;" in styles
    assert b".cookie-consent-dialog" in styles
    assert b"background: var(--color-surface-default);" in styles

    status, _, preferences = request(app, "/static/preferences.js")
    assert status == 200
    assert b'const DEVELOPER_MODE_KEY = "infinity-db-developer-mode";' in preferences
    assert b'const REMEMBER_SETTINGS_KEY = "infinity-db-remember-settings";' in preferences
    assert b"function initializeDeveloperModeToggle()" in preferences
    assert b"function initializeRememberSettingsToggle()" in preferences
    assert b"dialog.showModal()" in preferences
    assert b'getElementById("distance-unit-toggle")?.checked ? "in" : "cm"' in preferences
    assert b'getElementById("developer-mode-toggle")?.checked' in preferences
    assert b"window.localStorage" not in preferences
    assert b'new CustomEvent("developermodechange"' in preferences


def test_compact_navigation_is_closed_when_a_page_is_restored(app: Callable) -> None:
    status, _, body = request(app, "/units")

    assert status == 200
    assert b'<script type="module" src="/static/navigation.js?v=0.4.1"></script>' in body
    assert b'<script type="module" src="/static/page-navigation.js?v=0.4.1"></script>' in body
    assert b'<p class="nav-label menu-label">Navigation</p>' in body
    assert b'aria-controls="compact-navigation-menu"' in body
    assert b'>Navigation <span aria-hidden="true">' in body

    status, _, navigation = request(app, "/static/navigation.js")
    assert status == 200
    assert b'document.querySelectorAll("[data-menu]")' in navigation
    assert b"themed-logo.js" not in navigation

    status, _, page_navigation = request(app, "/static/page-navigation.js")
    assert status == 200
    assert b"currentMain.replaceWith(nextMain)" in page_navigation
    assert b"window.infinityNavigate" in page_navigation
    assert b'"/static/navigation.js", "/static/page-navigation.js"' in page_navigation
    assert b'source.searchParams.set("_navigation", String(navigationNumber))' in page_navigation
    assert b"window.document.body.append(script)" in page_navigation
    assert b"const menus = [...document.querySelectorAll" in navigation
    assert b'button.addEventListener("click"' in navigation
    assert b'window.matchMedia("(max-width: 920px)")' in navigation
    assert b'document.addEventListener("touchstart", closeOnOutsideInteraction' in navigation
    assert b"menu.dataset.open = String(isOpen)" in navigation
    assert b'document.addEventListener("pointerdown"' in navigation
    assert b'window.addEventListener("pagehide", closeMenu)' in navigation

    status, headers, themed_logo = request(app, "/static/themed-logo.js")
    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert b"hydrateThemedLogos" in themed_logo

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert b'.menu[data-open="true"] > .compact-menu-panel { display: flex; }' in styles
    assert b'window.addEventListener("pageshow", closeMenu)' in navigation


def test_about_page_is_served_with_active_navigation(app: Callable) -> None:
    status, headers, body = request(app, "/about")

    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Know your options." in body
    assert b'Made by Johannes "Franky" Haglund' in body
    assert b"Version 0.4.1+dev" in body
    assert b"Support questions, suggestions, or" in body
    assert b"feedback can be submitted on the project's GitHub page." in body
    assert b"mailto:johannes@haglund.info" not in body
    assert b"https://github.com/frankysan/InfinityDB" in body
    assert b"LLM code disclosure" in body
    assert b"better companion for choosing, collecting, and playing your army" in body
    assert b'href="/about" aria-current="page"' in body
    assert b"about.js" in body


def test_army_symbol_is_served(app: Callable) -> None:
    status, headers, body = request(app, "/static/army-symbols.js")
    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert b"armySymbolPath" in body
    status, headers, body = request(app, "/static/armies/panoceania/101-panoceania.svg")
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body
    status, _, body = request(
        app, "/static/units/unassigned/224-yojimbo-motorized-sword-for-hire.svg"
    )
    assert status == 200
    assert b"<svg" in body
    status, _, body = request(app, "/static/units/panoceania/18-clipper-dronbot.svg")
    assert status == 200
    assert b"<svg" in body
    for path in [
        "/static/armies/combined-army/605-next-wave.svg",
        "/static/armies/na2/998-contracted-back-up.svg",
    ]:
        status, headers, body = request(app, path)
        assert status == 200
        assert headers["content-type"] == "image/svg+xml"
        assert b"<svg" in body
    status, _, _ = request(app, "/static/armies/panoceania/not-an-army.svg")
    assert status == 404


def test_assets_and_catalog_api_have_release_safe_cache_headers(app: Callable) -> None:
    status, headers, _ = request(app, "/static/styles.css?v=0.4.1")
    assert status == 200
    assert headers["cache-control"] == "public, max-age=31536000, immutable"

    status, headers, _ = request(app, "/static/unit-list.js")
    assert status == 200
    assert headers["cache-control"] == "public, max-age=300, stale-while-revalidate=600"


def test_catalog_api_etag_revalidates_the_current_snapshot(app: Callable) -> None:
    status, headers, body = request(app, "/api/armies")

    assert status == 200
    assert body
    etag = headers["etag"]
    assert etag.startswith('"0.4.1-')

    status, conditional_headers, conditional_body = request(
        app,
        "/api/armies",
        request_headers={"If-None-Match": f'"other", W/{etag}'},
    )

    assert status == 304
    assert conditional_body == b""
    assert conditional_headers["etag"] == etag
    assert conditional_headers["cache-control"] == headers["cache-control"]
    assert "content-length" not in conditional_headers

    status, query_headers, _ = request(app, "/api/units", query="limit=1")
    assert status == 200
    assert query_headers["etag"] != etag

    status, missing_headers, _ = request(app, "/api/units/9099")
    assert status == 404
    assert "etag" not in missing_headers


def test_rebuilt_snapshot_changes_the_catalog_api_etag(app: Callable, tmp_path: Path) -> None:
    status, headers, body = request(app, "/api/armies")
    assert status == 200

    rebuilt_database = tmp_path / "rebuilt.db"
    shutil.copyfile(app.database.path, rebuilt_database)
    with sqlite3.connect(rebuilt_database) as connection:
        connection.execute("UPDATE units SET name = ? WHERE id = ?", ("Updated Ranger", 1))
    rebuilt_app = create_app(rebuilt_database)

    rebuilt_status, rebuilt_headers, rebuilt_body = request(rebuilt_app, "/api/armies")
    assert rebuilt_status == 200
    assert rebuilt_body == body
    assert rebuilt_headers["etag"] != headers["etag"]


def test_versioned_modules_reference_their_matching_release_dependencies(app: Callable) -> None:
    status, headers, body = request(app, "/static/unit.js?v=0.4.1")

    assert status == 200
    assert headers["cache-control"] == "public, max-age=31536000, immutable"
    assert b'from "./api.js?v=0.4.1"' in body
    assert b'from "./preferences.js?v=0.4.1"' in body

    status, _, body = request(app, "/static/api.js?v=0.4.1")
    assert status == 200
    assert b'import("./preferences.js?v=0.4.1")' in body

    status, headers, _ = request(app, "/api/armies")
    assert status == 200
    assert headers["cache-control"] == "public, max-age=300, stale-while-revalidate=600"


def test_frontend_recognizes_98_and_99_as_reinforcement_armies(app: Callable) -> None:
    for asset in ["/static/unit-list.js", "/static/unit.js"]:
        status, _, body = request(app, asset)
        assert status == 200
        assert b"[98, 99]" in body


def test_unit_details_frontend_collapses_army_profile_tables(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'document.createElement("details")' in body
    assert b"function isStandardArmy(army)" in body
    assert b"section.open = expanded" in body
    assert b"function profileIdentity(profileName)" in body
    assert b'reconaissance: "recon"' in body
    assert b'"troops", "autonomous", "intervention", "unit"' in body


def test_unit_details_frontend_displays_high_ava_as_total(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function displayAvailability(value)" in body
    assert b'return Number(value) >= 100 ? "Total" : displayStatlineValue(value)' in body


def test_unit_details_frontend_places_attributes_in_a_separate_row(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert (
        b"function attributeStatline(stats, generalStats = null, includeAvailability = false)"
        in body
    )
    assert b'className: "data-label profile-attributes-label"' in body
    assert b'className: "data-label general-item-label"' in body
    assert b'"data-table--compact profile-details-table"' in body
    assert b'["Name", "Points", "SWC"]' in body
    assert b"attributeStatline(profile, generalStatsForProfile, true)" in body


def test_unit_details_frontend_pluralizes_general_profile_heading(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'displayedGeneralProfiles.length === 1 ? "General profile" : "General profiles"' in body
    assert b"generalProfileTableRows([profile])" in body


def test_unit_details_frontend_marks_army_profile_section_headings(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'profilesHeading.className = "army-profiles-heading"' in body


def test_unit_details_frontend_marks_surface_and_deepspace_profiles(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function profileNameWithDivisionBadge(profile)" in body
    assert b'for (const division of ["surface", "deepspace"])' in body
    assert b"badge division-badge division-badge-${division}" in body

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert b".division-badge-surface { background: #256d1b; }" in styles
    assert b".division-badge-deepspace { background: #d68623; }" in styles


def test_detail_views_reuse_shared_detail_style_primitives(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    for selector in [
        b".detail-group",
        b".detail-section-title",
        b".data-surface-header",
        b".data-label",
        b".badge",
    ]:
        assert selector in styles

    for path in ["/static/unit.js", "/static/skill.js", "/static/catalog-detail.js"]:
        status, _, body = request(app, path)
        assert status == 200
        assert b"detail-group" in body
        assert b"data-surface-header" in body


def test_surfaces_and_table_densities_use_shared_variants(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    for selector in [
        b".surface, .explorer",
        b".surface--subtle",
        b".surface--highlighted",
        b".data-table--compact",
    ]:
        assert selector in styles

    for path in ["/static/unit.js", "/static/skill.js", "/static/catalog-detail.js"]:
        status, _, body = request(app, path)
        assert status == 200
        assert b"data-table--compact" in body

    status, _, weapon_detail = request(app, "/static/catalog-detail.js")
    assert status == 200
    assert b'card.className = "explorer surface weapon-profile"' in weapon_detail
    assert b"const profileTitle = profile.mode || profile.name || variant.name;" in weapon_detail
    assert b'title.className = "data-surface-header";' in weapon_detail
    assert b"headingText" not in weapon_detail
    assert b"variantTitle" not in weapon_detail
    assert b'profileHeading.textContent = "Profile";' in weapon_detail
    assert b'traitsHeading.textContent = "Traits";' in weapon_detail
    assert b"if (traitNames.length)" in weapon_detail
    assert b".weapon-data-heading" in styles
    assert b'profileRow.className = "weapon-data-row"' in weapon_detail
    assert b'profileStats.className = "weapon-data-value"' in weapon_detail
    assert b".weapon-data-row { display: grid;" in styles
    assert b"border-left: 1px solid #e9ece3" in styles
    assert b"--surface-data-header: #fafbf8" in styles
    assert b"thead th { background: var(--surface-data-header);" in styles
    assert b".weapon-data-heading" in styles
    assert b".weapon-variants, .weapon-variant, .weapon-profile { width: 100%; }" in styles
    assert b".weapon-profile .weapon-ranges { display: table;" in styles
    assert b"width: 100%; table-layout: auto; }" in styles

    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'generalProfile.className = "explorer general-profile"' in body
    assert b".general-profile .profile-title" in styles
    assert b"background: var(--surface-highlight)" in styles

    status, _, body = request(app, "/about")
    assert status == 200
    assert b"surface surface--highlighted about-callout" in body
    assert b"surface surface--subtle about-disclosure" in body

    assert b".usage-section-group thead th:first-child," in styles
    assert b".usage-section-group thead th:last-child { width: auto; }" in styles


def test_unit_details_frontend_hides_empty_army_profile_item_rows(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert body.count(b"if (!items.length) continue;") == 2


def test_unit_details_frontend_promotes_sole_loadout_skills_to_general_profile(
    app: Callable,
) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function generalProfileSkills(profiles, loadouts)" in body
    assert b"if (loadouts.length !== 1) return skills;" in body


def test_unit_details_frontend_links_catalog_items_to_their_details(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function profileItems(items, catalog, fallbackLabel)" in body
    assert b"link.href = `/${catalog}/${encodeURIComponent(item.id)}`" in body


@pytest.mark.parametrize(
    "symbol",
    [
        "regular",
        "irregular",
        "peripheral",
        "impetuous",
        "tactical",
        "lieutenant",
        "hackable",
        "cube",
        "cube-2",
    ],
)
def test_order_symbols_are_served(app: Callable, symbol: str) -> None:
    status, headers, body = request(app, f"/static/orders/{symbol}.svg")
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body


def test_unit_details_frontend_renders_order_symbols_as_content(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function profileTitle(profile)" in body
    assert b"generalProfile.append(profileTitle(profile), table(" in body
    assert b"nameWithOrderSymbols(loadout.name, symbolTypes)" in body
    assert b"function generalProfileOrderType(profiles, loadouts)" in body
    assert b'hasSkill(loadouts, "regular")' in body
    assert b'.startsWith("peripheral")' in body
    assert b'hasSkill([loadout], "impetuous")' in body
    assert b'hasSkill([loadout], "tactical awareness")' in body
    assert b"function lieutenantOrderCount(items)" in body
    assert b"function generalLieutenantOrderCount(profiles, loadouts)" in body
    assert b'Array(lieutenantOrderCount([loadout])).fill("lieutenant")' in body
    assert b"function characteristicSymbolTypes(profiles)" in body
    assert b"symbol.title = symbolLabels[symbolType]" in body
    assert b'"profile-summary loadout-start"' in body


def test_distance_preference_script_is_served(app: Callable) -> None:
    status, headers, body = request(app, "/static/preferences.js")
    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert b"distanceunitchange" in body


def test_skill_extras_page_and_api_are_served(app: Callable) -> None:
    status, headers, body = request(app, "/skill-extras")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"skill-extras.js" in body

    status, headers, body = request(app, "/api/skill-extras")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    assert json.loads(body) == {"items": []}


@pytest.mark.parametrize("catalog", ["skills", "equipment", "weapons"])
def test_reference_catalog_pages_and_apis_are_served(app: Callable, catalog: str) -> None:
    status, headers, body = request(app, f"/{catalog}")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"catalog-list.js" in body
    assert f'href="/{catalog}" aria-current="page"'.encode() in body
    assert b'<th scope="col">Uses</th>' in body
    assert b"Reference</th>" not in body

    status, headers, body = request(app, f"/api/{catalog}")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    expected = {
        "skills": {"id": 11, "name": "Stealth", "wiki": None, "use_count": 1},
        "equipment": {
            "id": 21,
            "name": "Medikit",
            "wiki": "https://infinitythewiki.com/Medikit",
            "use_count": 1,
        },
        "weapons": {
            "id": 31,
            "name": "Combi Rifle",
            "type": None,
            "category": "Rifles",
            "ammunition": None,
            "properties": None,
            "use_count": 1,
        },
    }
    assert json.loads(body)["items"] == [expected[catalog]]


def test_skill_details_page_and_api_are_served(app: Callable) -> None:
    status, headers, body = request(app, "/skills/11")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"skill.js" in body
    assert b'href="/skills" aria-current="page"' in body
    status, headers, body = request(app, "/api/skills/11")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    skill = json.loads(body)
    assert skill == {
        "id": 11,
        "name": "Stealth",
        "wiki": None,
        "variants": [
            {
                "skill_id": 11,
                "skill_name": "Stealth",
                "extras": [{"id": 41, "name": "+3"}],
                "units": [
                    {
                        "id": 1,
                        "name": "Alpha Ranger",
                        "isc": "Explorer Prototype",
                        "slug": "ranger-prototype",
                        "main_army_id": None,
                        "main_army_name": None,
                        "source_ids": [1],
                        "army_ids": [101, 201],
                        "armies": [
                            {"id": 101, "name": "Zulu Company"},
                            {"id": 201, "name": "Alpha Company"},
                        ],
                    }
                ],
            }
        ],
    }

    status, _, body = request(app, "/api/units")
    assert status == 200
    unit = next(item for item in json.loads(body)["items"] if item["id"] == 1)
    assert skill["variants"][0]["units"] == [unit]

    status, _, body = request(app, "/api/skills/999")
    assert status == 404
    assert json.loads(body)["error"] == "Skill not found"


def test_infinity_wiki_link_labels_omit_query_strings(app: Callable) -> None:
    for asset in ("catalog-detail.js", "skill.js"):
        status, _, body = request(app, f"/static/{asset}")
        assert status == 200
        assert b'new URL(url).hostname.toLowerCase() === "infinitythewiki.com"' in body
        assert b'url.split("?", 1)[0]' in body


def test_visible_unit_ids_api_matches_default_unit_listing(app: Callable) -> None:
    status, _, body = request(app, "/api/visible-unit-ids")
    assert status == 200
    visible_ids = json.loads(body)["ids"]

    status, _, body = request(app, "/api/units?limit=200")
    assert status == 200
    assert visible_ids == [item["id"] for item in json.loads(body)["items"]]


@pytest.mark.parametrize(
    ("catalog", "item_id", "name"),
    [
        ("equipment", 21, "Medikit"),
        ("weapons", 31, "Combi Rifle"),
    ],
)
def test_equipment_and_weapon_details_are_served(
    app: Callable,
    catalog: str,
    item_id: int,
    name: str,
) -> None:
    status, headers, body = request(app, f"/{catalog}/{item_id}")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"catalog-detail.js" in body

    status, headers, body = request(app, f"/api/{catalog}/{item_id}")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    payload = json.loads(body)
    assert payload["name"] == name
    if catalog == "equipment":
        assert payload["wiki"] == "https://infinitythewiki.com/Medikit"
    assert payload["variants"][0]["units"][0]["id"] == 1


def test_equipment_details_frontend_renders_metadata_profiles(app: Callable) -> None:
    status, _, body = request(app, "/static/catalog-detail.js")

    assert status == 200
    assert b'catalog === "equipment" && item.profiles?.length' in body
    assert b"weaponVariants([{ id: item.id, name: item.name, profiles: item.profiles }])" in body
    assert b'"Equipment profile"' not in body
    assert b'link.target = "_blank"' in body
    assert b'link.rel = "noopener noreferrer"' in body


def test_skill_details_frontend_opens_wiki_links_in_a_new_tab(app: Callable) -> None:
    status, _, body = request(app, "/static/skill.js")

    assert status == 200
    assert b'link.target = "_blank"' in body
    assert b'link.rel = "noopener noreferrer"' in body


def test_unit_symbol_is_served(app: Callable) -> None:
    status, headers, body = request(app, "/static/unit-symbol-map.js")
    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert b"unitSymbolSlug" in body
    status, headers, body = request(app, "/static/units/panoceania/1-fusiliers.svg")
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body
    for path in [
        "/static/units/next-wave/1921-blur-spec-ops.svg",
        "/static/units/next-wave/1935-next-wave-team-ops.svg",
    ]:
        status, headers, body = request(app, path)
        assert status == 200
        assert headers["content-type"] == "image/svg+xml"
        assert b"<svg" in body
    status, _, _ = request(app, "/static/units/unassigned/not-a-unit.svg")
    assert status == 404
    status, headers, body = request(app, "/static/armies/jsa/1199-hayabusa.svg")
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body


@pytest.mark.parametrize("path", ["/", "/api/armies", "/api/units", "/missing"])
def test_head_matches_get_headers_without_response_body(app: Callable, path: str) -> None:
    get_status, get_headers, get_body = request(app, path)
    head_status, head_headers, head_body = request(app, path, method="HEAD")
    assert head_status == get_status
    assert head_headers == get_headers
    assert head_body == b""
    assert int(head_headers["content-length"]) == len(get_body)


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_unsupported_method_is_rejected(app: Callable, method: str) -> None:
    status, headers, body = request(app, "/api/units", method=method)
    assert status == 405
    assert {item.strip() for item in headers["allow"].split(",")} == {"GET", "HEAD"}
    assert json.loads(body)["error"]


@pytest.mark.parametrize("path", ["/missing", "/api/nope", "/static/../web.py"])
def test_unknown_and_parent_paths_are_not_served(app: Callable, path: str) -> None:
    status, _, _ = request(app, path)
    assert status == 404


def test_missing_database_fails_before_app_starts(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.db"
    with pytest.raises((OSError, ValueError)):
        create_app(database_path)
    assert not database_path.exists()
