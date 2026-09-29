from __future__ import annotations

import copy
import importlib
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_army_data.merge import make_source, merge_sources
from infinity_army_data.normalize import normalize_master
from infinity_db import __display_version__, __version__
from infinity_db.army_overview import army_overview_out_of_catalog
from infinity_db.curated import load_curated_directory
from infinity_db.database import export_database
from infinity_db.database.publication import (
    PUBLISHED_CONTENT_SHA256_KEY,
    published_content_sha256,
)
from infinity_db.rules_database import export_rules_database
from infinity_db.symbol_catalog import SymbolCatalog
from infinity_db.web import create_app
from infinity_db.web.app import STATIC_ASSET_REVISION, STATIC_ASSET_VERSION


def _refresh_published_content_checksum(path: Path) -> None:
    """Refresh build-integrity metadata after intentional fixture mutation."""

    with sqlite3.connect(path) as connection:
        checksum = published_content_sha256(connection)
        connection.execute(
            "UPDATE __infinity_metadata SET value = ? WHERE key = ?",
            (json.dumps(checksum), PUBLISHED_CONTENT_SHA256_KEY),
        )


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
        close = getattr(result, "close", None)
        if close is not None:
            close()
    return response["status"], response["headers"], body


def _normalized_css_selector(selector: str) -> str:
    selector = re.sub(r"\s+", " ", selector.strip())
    return re.sub(r"\s*([>,+~])\s*", r"\1", selector)


def assert_css_rule(
    styles: bytes,
    selector: str,
    declarations: Mapping[str, str],
) -> None:
    target = _normalized_css_selector(selector)
    candidates: list[dict[str, str]] = []
    for match in re.finditer(rb"([^{}]+)\{([^{}]*)\}", styles):
        candidate_selector = _normalized_css_selector(match.group(1).decode())
        if candidate_selector != target:
            continue
        parsed: dict[str, str] = {}
        for declaration in match.group(2).decode().split(";"):
            if ":" not in declaration:
                continue
            name, value = declaration.split(":", 1)
            parsed[name.strip()] = re.sub(r"\s+", " ", value.strip())
        candidates.append(parsed)

    expected = {name: re.sub(r"\s+", " ", value.strip()) for name, value in declarations.items()}
    if any(
        all(candidate.get(name) == value for name, value in expected.items())
        for candidate in candidates
    ):
        return

    raise AssertionError(
        f"CSS rule {selector!r} did not contain expected declarations {expected!r}; "
        f"matching rules: {candidates!r}"
    )


@pytest.fixture(scope="module")
def app_database_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
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
                        "ava": 2,
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
    # Declared factions and source-origin context deliberately differ from actual occurrences.
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
    normalized["_meta"]["sourceDataChangedOn"] = "2026-09-03"
    normalized["_meta"]["snapshotDownloadedOn"] = "2026-09-10"
    database_path = tmp_path_factory.mktemp("web-app") / "infinity.db"
    export_database(normalized, database_path)
    return database_path


@pytest.fixture
def app(tmp_path: Path, app_database_template: Path) -> Callable:
    database_path = tmp_path / "infinity.db"
    shutil.copy2(app_database_template, database_path)
    return create_app(database_path)


def test_internal_metrics_use_bounded_normalized_route_labels(app: Callable) -> None:
    status, _, _ = request(
        app,
        "/api/units/ranger-prototype",
        query="search=private-search-term&visitor=private-id",
    )
    assert status == 200
    status, _, _ = request(
        app,
        "/api/units/not-a-unit",
        query="search=another-private-term",
    )
    assert status == 404

    status, headers, body = request(app, "/internal/metrics")
    assert status == 200
    assert headers["content-type"].startswith("text/plain; version=0.0.4")
    assert headers["cache-control"] == "no-store"
    assert b'infinitydb_http_requests_total{route="/api/units/:id",status_class="2xx"} 1' in body
    assert b'infinitydb_http_requests_total{route="/api/units/:id",status_class="4xx"} 1' in body
    assert b'infinitydb_http_request_duration_seconds_bucket{route="/api/units/:id"' in body
    assert b'infinitydb_http_response_size_bytes_bucket{route="/api/units/:id"' in body
    assert b"ranger-prototype" not in body
    assert b"not-a-unit" not in body
    assert b"private-search-term" not in body
    assert b"private-id" not in body
    assert b"another-private-term" not in body


def test_internal_health_and_metrics_do_not_instrument_themselves(app: Callable) -> None:
    status, _, before = request(app, "/internal/metrics")
    assert status == 200

    status, headers, body = request(app, "/internal/health")
    assert status == 200
    assert headers["cache-control"] == "no-store"
    assert body == b"ok\n"

    status, headers, body = request(app, "/internal/metrics", method="POST")
    assert status == 405
    assert headers["allow"] == "GET, HEAD"
    assert body == b"method not allowed\n"

    status, _, after = request(app, "/internal/metrics")
    assert status == 200
    assert after == before


def test_armies_list_contains_actual_armies_and_counts(app: Callable) -> None:
    status, headers, body = request(app, "/api/armies")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    armies = {item["id"]: item for item in json.loads(body)["items"]}
    assert set(armies) == {101, 198, 201, 906, 907}
    assert [army["id"] for army in json.loads(body)["items"]] == [101, 198, 201, 906, 907]
    assert armies[101]["slug"] == "zulu_company"
    assert armies[101]["public_slug"] == "zulu-company"
    assert armies[101]["name"]
    assert armies[101]["kind"] == "army"
    assert armies[101]["overview_description"]
    assert armies[101]["overview_group"] == {"id": 101, "name": "Zulu Company"}
    assert armies[198]["kind"] == "reinforcement"
    assert armies[198]["overview_description"]
    assert armies[198]["overview_group"]
    assert {armies[army_id]["unit_count"] for army_id in (101, 198, 201)} == {1, 2, 4}
    assert armies[906]["name"] == "Spiral Corps"
    assert armies[906]["legacy"] is True
    assert armies[906]["playable"] is False
    assert armies[906]["overview_group"] == {"id": 901, "name": "Non-Aligned Armies"}
    assert armies[907]["name"] == "Foreign Company"
    assert armies[907]["legacy"] is True
    assert armies[907]["playable"] is False



def test_army_overview_page_uses_canonical_armies_and_unit_links(app: Callable) -> None:
    status, headers, body = request(app, "/armies")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Army lists" in body
    assert b'/static/armies.js?v=' in body
    assert b'href="/armies" aria-current="page"' in body

    status, _, script = request(app, "/static/armies.js")
    assert status == 200
    assert b'from "./api.js"' in script
    assert b'from "./unit-symbols.js"' in script
    assert b"getArmies" in script
    assert b"army.overview_description" in script
    assert b"staticSymbolPath(army.symbol_path)" in script
    assert b"new URLSearchParams({ army_id: armyValue(army) })" in script
    assert b"army.overview_group" in script
    assert b"Out of catalog" in script
    assert b"Not playable in N5" in script
    assert b"groupIdentity" not in script
    assert b"infinity:beforenavigation" in script

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(styles, ".army-overview", {"width": "min(1040px, 100%)"})
    assert_css_rule(
        styles,
        ".army-overview-grid",
        {"display": "grid", "grid-template-columns": "repeat(auto-fit, minmax(280px, 1fr))"},
    )
    assert_css_rule(
        styles,
        ".status-badge--warning",
        {
            "background": "var(--color-status-warning-surface)",
            "color": "var(--color-status-warning-text)",
        },
    )


def test_reinforcement_catalog_status_uses_main_overview_group_only() -> None:
    armies = {
        101: {"id": 101, "name": "Main", "role": "main", "discontinued": False},
        102: {
            "id": 102,
            "name": "Sectorial",
            "role": "sectorial",
            "group_id": 101,
            "discontinued": True,
        },
        198: {
            "id": 198,
            "name": "Reinforcements",
            "role": "reinforcement",
            "discontinued": False,
            "parent_armies": [{"id": 102}, {"id": 101}],
        },
    }

    assert army_overview_out_of_catalog(armies[198], armies_by_id=armies) is False
    armies[101]["discontinued"] = True
    assert army_overview_out_of_catalog(armies[198], armies_by_id=armies) is True


def test_fireteam_chart_page_and_api_use_application_projection(
    tmp_path: Path, app_database_template: Path
) -> None:
    database_path = tmp_path / "infinity.db"
    shutil.copy2(app_database_template, database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE application_fireteam_charts SET description = ? "
            "WHERE application_army_id = 101",
            ("Current chart note",),
        )
        connection.execute(
            "INSERT INTO application_fireteam_chart_limits "
            "(application_army_id, fireteam_type, position, raw_limit) "
            "VALUES (101, 'CORE', 1, 1)"
        )
        connection.execute(
            "INSERT INTO application_fireteams "
            "(application_army_id, fireteam_id, position, name, observation, source_army_id, "
            "source_fireteam_id, is_wildcard) "
            "VALUES (101, 1, 1, 'Ranger Team', 'No Wildcards', 101, 1, 0)"
        )
        connection.execute(
            "INSERT INTO application_fireteam_types "
            "(application_army_id, fireteam_id, position, fireteam_type) "
            "VALUES (101, 1, 1, 'CORE')"
        )
        connection.execute(
            "INSERT INTO application_fireteam_members "
            "(application_army_id, fireteam_id, member_id, position, source_army_id, "
            "source_fireteam_id, source_member_id, slug, name, comment, min_count, max_count, "
            "required, source_unit_id, logical_unit_id, resolution, fto_marker) "
            "VALUES (101, 1, 1, 1, 101, 1, 1, 'ranger-prototype', 'Alpha Ranger', "
            "'Line Trooper', 1, 2, 1, 1, 1, 'army', NULL)"
        )
    _refresh_published_content_checksum(database_path)
    fireteam_app = create_app(database_path)

    status, _, body = request(fireteam_app, "/fireteams")
    assert status == 200
    assert b"Fireteams" in body
    assert b"/static/fireteams.js?v=" in body
    assert b'href="/fireteams" aria-current="page"' in body

    status, _, body = request(fireteam_app, "/api/fireteams")
    assert status == 200
    fireteam_index = json.loads(body)
    assert fireteam_index["reference"] is None
    armies = fireteam_index["items"]
    assert [(item["id"], item["public_slug"], item["fireteam_count"]) for item in armies] == [
        (101, "zulu-company", 1)
    ]

    status, _, body = request(fireteam_app, "/api/fireteams", query="army_id=zulu-company")
    assert status == 200
    chart = json.loads(body)
    assert "reference" not in chart
    assert chart["army"]["public_slug"] == "zulu-company"
    assert chart["description"] == "Current chart note"
    assert chart["limits"] == [{"type": "CORE", "position": 1, "max_count": 1}]
    assert chart["teams"][0]["name"] == "Ranger Team"
    assert chart["teams"][0]["types"] == ["CORE"]
    member = chart["teams"][0]["members"][0]
    assert member["unit"]["slug"] == "ranger-prototype"
    assert member["required"] is True

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(database_path, rules_database_path=rules_path)
    status, _, body = request(rules_app, "/api/fireteams")
    assert status == 200
    reference = json.loads(body)["reference"]
    assert reference["general"]["facts"]["category"] == "fireteam-general"
    assert reference["general"]["facts"]["memberLimits"] == {"min": 2, "max": 5}
    assert [item["type"] for item in reference["general"]["facts"]["types"]] == [
        "DUO",
        "HARIS",
        "CORE",
    ]
    assert {
        term["term"]: term["provenance"] for term in reference["general"]["facts"]["terminology"]
    } == {
        "Linkable": "historical-official",
        "Pure Fireteam": "community-historical",
    }
    levels = reference["levels"]["facts"]
    assert levels["cumulative"] is True
    assert [level["level"] for level in levels["levels"]] == [1, 2, 3, 4, 5]
    assert levels["levels"][1]["bonuses"] == ["BS Attack (+1 SD)"]
    assert levels["levels"][4]["bonuses"] == ["Sixth Sense"]
    assert any(
        citation.get("source_url") and "Fireteam_Bonuses" in citation["source_url"]
        for citation in reference["levels"]["citations"]
    )

    status, _, body = request(rules_app, "/api/fireteams", query="army_id=zulu-company")
    assert status == 200
    assert "reference" not in json.loads(body)

    status, _, script = request(fireteam_app, "/static/fireteams.js")
    assert status == 200
    assert b"getFireteamArmies" in script
    assert b"getFireteamChart" in script
    assert b"Counts as:" in script
    assert b"Authoritative" in script
    assert b'army.role === "reinforcement"' in script
    assert b'army.role === "sectorial" || army.role === "non_aligned"' in script
    assert b"value === 256" in script
    assert b"`${limit.type}: unlimited`" in script
    assert b'element.classList.add("developer-only")' in script
    assert b'["FTO Profiles", true, "table-column--descriptor"]' in script
    assert b'["Notes", true, "table-column--descriptor"]' in script
    assert b'fto.className = "developer-only table-column--descriptor";' in script
    assert b'note.className = "developer-only table-column--descriptor";' in script
    assert b'table.className = "data-table--reference";' in script
    assert b'name.className = "table-column--primary";' in script
    assert (
        b'requirements.className = "table-column--descriptor fireteam-member-requirements";'
        in script
    )
    assert b"fireteamsIncludeWildcards" in script
    assert b"const wildcardTeams = teams.filter((team) => team.is_wildcard);" in script
    assert b"if (wildcardTeams.length !== 1) return teams;" in script
    assert b".filter((team) => !team.is_wildcard)" in script
    assert b"wildcard_members: wildcardMembers" in script
    assert b'if (wildcard) name.append(badge("Wildcard"));' in script
    assert b"appendMemberRow(member, { wildcard: true })" in script
    assert b'window.addEventListener("fireteamswildcardschange"' in script
    assert b"detail-badges fireteam-card-types" in script
    assert b"function renderReference(reference)" in script
    assert 'new Option("Select an Army…", "")'.encode() in script
    assert b"function renderOverview()" in script
    assert b"currentReference = payload.reference || null;" in script
    assert b"renderReference(chart.reference)" not in script
    assert b"for (const level of levelFacts.levels || [])" in script
    assert b"Historical official term" in script
    assert b"Community / historical shorthand" in script

    status, _, page = request(fireteam_app, "/fireteams")
    assert status == 200
    assert b'id="fireteam-landing"' in page
    assert b'id="fireteam-reference"' in page
    assert b'id="fireteam-reference-content"' in page

    status, _, styles = request(fireteam_app, "/static/styles.css")
    assert status == 200
    assert_css_rule(styles, ".fireteam-card", {"width": "min(640px, 100%)"})
    assert_css_rule(
        styles,
        ".fireteam-chart-summary",
        {
            "grid-template-columns": "minmax(0, 1fr)",
            "width": "min(640px, 100%)",
            "min-width": "0",
        },
    )
    assert_css_rule(
        styles,
        ".fireteam-landing,\n.fireteam-content,\n.fireteam-list",
        {"grid-template-columns": "minmax(0, 1fr)", "min-width": "0"},
    )
    assert_css_rule(styles, ".fireteam-reference", {"min-width": "0"})
    assert_css_rule(styles, "#fireteam-reference-content", {"min-width": "0"})
    assert b".fireteam-card-types {\n    width: 100%;\n    min-width: 0;" in styles
    assert (
        b".fireteam-card-titlebar {\n    flex-direction: column;\n"
        b"    align-items: stretch;"
        in styles
    )
    assert (
        b"""  .fireteam-reference-table table {
    --table-heading-padding: 9px 8px;
    --table-cell-padding: 10px 8px;
    --table-heading-size: var(--font-size-xs);
    --table-cell-size: var(--font-size-sm);
    width: 100%;
    min-width: 0;
  }"""
        in styles
    )
    assert_css_rule(
        styles,
        ".fireteam-reference-table table",
        {"min-width": "560px", "table-layout": "fixed"},
    )
    assert_css_rule(
        styles,
        ".fireteam-reference-table",
        {"width": "min(720px, 100%)"},
    )
    assert_css_rule(
        styles,
        ".fireteam-reference-table .table-column--metric",
        {"width": "64px", "text-align": "center"},
    )
    assert_css_rule(
        styles,
        ".fireteam-reference-table .table-column--descriptor",
        {"width": "calc((100% - 64px) / 2)"},
    )
    assert b'html[data-developer-mode="true"] .fireteam-card {' not in styles
    assert_css_rule(styles, ".fireteam-member-table", {"border": "0"})
    assert_css_rule(styles, ".fireteam-member-table table", {"min-width": "520px"})
    assert (
        b"""  html:not([data-developer-mode="true"]) .fireteam-member-table table {
    width: 100%;
    min-width: 0;
    table-layout: fixed;
  }"""
        in styles
    )
    assert (
        b"""  .fireteam-member-table table {
    --table-heading-padding: 9px 10px;
    --table-cell-padding: 12px 10px;
    --table-heading-size: var(--font-size-xs);
    --table-cell-size: var(--font-size-base);
  }"""
        in styles
    )
    assert (
        b"""  .fireteam-member-table th,
  .fireteam-member-table td {
    min-width: 0;
    white-space: normal;
  }"""
        in styles
    )
    assert (
        b"""  html:not([data-developer-mode="true"]) .fireteam-member-table .table-column--primary {
    width: 54%;
    min-width: 0;
  }"""
        in styles
    )
    assert_css_rule(
        styles,
        'html[data-developer-mode="true"] .fireteam-member-table table',
        {"min-width": "760px"},
    )
    assert_css_rule(
        styles,
        ".fireteam-member-table .table-column--primary .skill-category-badge",
        {"margin-left": "8px", "vertical-align": "middle"},
    )
    assert b".fireteam-member-table th:first-child" not in styles
    assert b".fireteam-member-table th:nth-child" not in styles
    assert b".fireteam-reference-table th:first-child" not in styles
    assert b".fireteam-reference-table th:nth-child" not in styles


def test_army_api_exposes_source_derived_roles_and_grouping(tmp_path: Path) -> None:
    unit = {"id": 1, "name": "Shared Unit", "canonical": 101, "factions": [101]}
    documents = [
        ("101-main.json", True, 198),
        ("102-sectorial.json", True, None),
        ("901-non-aligned.json", True, None),
        ("902-independent.json", True, None),
        ("198-main-reinforcements.json", False, None),
    ]
    sources = []
    for filename, ordinary, reinforcement_id in documents:
        document = {"version": "test", "units": [unit]}
        if ordinary:
            document["reinforcements"] = reinforcement_id
        source = make_source(filename, json.dumps(document).encode())
        assert source is not None
        sources.append(source)

    normalized = normalize_master(merge_sources(sources))
    normalized["armyMetadata"] = {
        "sourceFile": "metadata.json",
        "sourceSha256": "test-metadata",
        "data": {
            "factions": [
                {"id": 101, "name": "Main Army", "discontinued": True},
                {"id": 102, "name": "Sectorial", "discontinued": False},
                {"id": 198, "name": "Reinforcements", "discontinued": False},
                {"id": 901, "name": "Non-Aligned Armies", "discontinued": False},
                {"id": 902, "name": "Independent Army", "discontinued": False},
            ]
        },
    }
    normalized["tables"]["metadata_factions"] = [
        {"id": 101, "parent": 101, "name": "Main Army", "slug": "main-army"},
        {"id": 102, "parent": 101, "name": "Sectorial", "slug": "sectorial"},
        {"id": 198, "parent": 101, "name": "Reinforcements", "slug": "reinforcements"},
        {
            "id": 901,
            "parent": 900,
            "name": "Non-Aligned Armies",
            "slug": "non-aligned-armies",
        },
        {"id": 902, "parent": 901, "name": "Independent Army", "slug": "independent-army"},
    ]
    database_path = tmp_path / "roles.db"
    export_database(normalized, database_path)
    role_app = create_app(database_path)

    status, _, body = request(role_app, "/api/armies")
    assert status == 200
    armies = {item["id"]: item for item in json.loads(body)["items"]}
    assert armies[101]["role"] == "main"
    assert armies[102]["role"] == "sectorial"
    assert armies[102]["group_id"] == 101
    assert armies[198]["role"] == "reinforcement"
    assert armies[198]["parent_army_ids"] == [101]
    assert armies[198]["parent_armies"] == [
        {"id": 101, "name": "Main Army", "slug": "main", "public_slug": "main"}
    ]
    assert armies[101]["discontinued"] is True
    assert armies[101]["out_of_catalog"] is True
    assert armies[102]["discontinued"] is False
    assert armies[102]["out_of_catalog"] is False
    assert armies[198]["discontinued"] is False
    assert armies[198]["out_of_catalog"] is True
    assert armies[101]["reinforcement_sections"] == [
        {
            "id": 198,
            "name": "Reinforcements",
            "slug": "main-reinforcements",
            "public_slug": "main-reinforcements",
        }
    ]
    assert armies[902]["role"] == "non_aligned"
    assert armies[902]["group_id"] == 901
    assert armies[901]["role"] == "grouping"
    assert armies[901]["playable"] is False

    status, _, body = request(role_app, "/api/units")
    assert status == 200
    unit_payload = json.loads(body)["items"][0]
    assert unit_payload["main_army_id"] == 101
    assert unit_payload["main_army_slug"] == "main"
    assert unit_payload["display_army_id"] == 101
    assert unit_payload["display_army_slug"] == "main"
    assert unit_payload["main_faction"]["public_slug"] == "main"
    assert unit_payload["display_faction"]["public_slug"] == "main"
    assert {army["id"]: army["public_slug"] for army in unit_payload["armies"]} == {
        101: "main",
        102: "sectorial",
        901: "non-aligned",
        902: "independent",
    }

    status, _, body = request(role_app, "/api/units/1")
    assert status == 200
    detail = json.loads(body)
    detail_armies = {army["id"]: army for army in detail["armies"]}
    assert detail_armies[198]["role"] == "reinforcement"
    assert detail_armies[198]["parent_armies"] == [
        {"id": 101, "name": "Main Army", "slug": "main", "public_slug": "main"}
    ]
    assert detail_armies[101]["reinforcement_sections"] == [
        {
            "id": 198,
            "name": "Reinforcements",
            "slug": "main-reinforcements",
            "public_slug": "main-reinforcements",
        }
    ]

    for army_ref in ("901", "non-aligned"):
        status, _, body = request(role_app, "/api/units", query=f"army_id={army_ref}")
        assert status == 400
        assert "grouping-only identity" in json.loads(body)["error"]


def test_army_filter_uses_actual_occurrences(app: Callable) -> None:
    for army_ref, expected in [
        (101, {1, 3}),
        ("zulu-company", {1, 3}),
        (201, {1, 2}),
        ("alpha-company", {1, 2}),
    ]:
        status, _, body = request(
            app, "/api/units", query=urlencode({"army_id": army_ref, "mercs": 1})
        )
        assert status == 200
        payload = json.loads(body)
        assert payload["total"] == 2
        assert {item["id"] for item in payload["items"]} == expected
        shared = next(item for item in payload["items"] if item["id"] == 1)
        assert set(shared["army_ids"]) == {101, 201}
        assert {army["id"] for army in shared["armies"]} == {101, 201}


def test_declared_faction_membership_is_distinct_and_navigable(
    tmp_path: Path, app_database_template: Path
) -> None:
    database_path = tmp_path / "declared-membership.db"
    shutil.copy2(app_database_template, database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO unit_factions (unit_id, faction_id, position) VALUES (?, ?, ?)",
            (3, 907, 2),
        )
    _refresh_published_content_checksum(database_path)
    membership_app = create_app(database_path)

    status, _, body = request(membership_app, "/api/units/3")
    assert status == 200
    unit = json.loads(body)
    memberships = {item["source_faction_id"]: item for item in unit["declared_factions"]}
    assert memberships[201] == {
        "source_faction_id": 201,
        "source_unit_ids": [3],
        "application_army_id": 201,
        "name": "Alpha Company",
        "has_army_list": True,
        "available": False,
    }
    assert memberships[907] == {
        "source_faction_id": 907,
        "source_unit_ids": [3],
        "application_army_id": None,
        "name": "Faction 907",
        "has_army_list": False,
        "available": False,
    }

    status, _, body = request(membership_app, "/api/units", query="declared_faction_id=201&mercs=1")
    assert status == 200
    payload = json.loads(body)
    assert {item["id"] for item in payload["items"]} == {2, 3}
    assert payload["declared_faction"] == {
        "source_faction_id": 201,
        "application_army_id": 201,
        "name": "Alpha Company",
        "has_army_list": True,
    }

    status, _, body = request(membership_app, "/api/units", query="declared_faction_id=907&mercs=1")
    assert status == 200
    payload = json.loads(body)
    assert [item["id"] for item in payload["items"]] == [3]
    assert payload["declared_faction"] == {
        "source_faction_id": 907,
        "application_army_id": None,
        "name": "Faction 907",
        "has_army_list": False,
    }


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


def test_unit_details_api_exposes_include_relationships(
    tmp_path: Path, app_database_template: Path
) -> None:
    database_path = tmp_path / "infinity.db"
    shutil.copy2(app_database_template, database_path)

    with sqlite3.connect(database_path) as connection:
        payload_id = connection.execute(
            "SELECT loadout_payload_id FROM loadout_payload_occurrences "
            "WHERE army_id = 101 AND unit_id = 1 AND group_id = 1 AND option_id = 1"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO profile_occurrence_includes "
            "(army_id, unit_id, group_id, profile_id, position, "
            "target_loadout_payload_id, quantity, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (101, 1, 1, 1, 1, payload_id, 2, None),
        )
        connection.execute(
            "INSERT INTO loadout_occurrence_includes "
            "(army_id, unit_id, group_id, option_id, position, "
            "target_loadout_payload_id, quantity, raw) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (101, 1, 1, 1, 1, payload_id, 1, None),
        )
        connection.execute(
            "INSERT INTO unit_options "
            "(unit_id, option_id, position, name, points, swc, minis, disabled) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, 7, 1, "Ranger pair", 50, "1.5", 2, False),
        )
        connection.execute(
            "INSERT INTO unit_option_orders "
            "(unit_id, option_id, position, order_type, list_count, total_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (1, 7, 1, "REGULAR", 2, 2),
        )
        connection.execute(
            "INSERT INTO unit_option_include_targets "
            "(unit_id, option_id, position, target_army_id, "
            "target_loadout_payload_id, quantity, raw) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 7, 1, 101, payload_id, 1, None),
        )
    _refresh_published_content_checksum(database_path)

    include_app = create_app(database_path)
    status, _, body = request(include_app, "/api/units/ranger-prototype")

    assert status == 200
    unit = json.loads(body)
    army = next(item for item in unit["armies"] if item["id"] == 101)
    assert army["profiles"][0]["includes"] == [
        {
            "loadout_payload_id": payload_id,
            "name": "Rifle loadout",
            "quantity": 2,
            "army_id": 101,
        }
    ]
    assert army["loadouts"][0]["includes"] == [
        {
            "loadout_payload_id": payload_id,
            "name": "Rifle loadout",
            "quantity": 1,
            "army_id": 101,
        }
    ]
    assert army["loadouts"][0]["loadout_payload_ids"] == [payload_id]
    assert army["unit_option_includes"] == [
        {
            "option_id": 7,
            "name": "Ranger pair",
            "source_unit_id": 1,
            "includes": [
                {
                    "loadout_payload_id": payload_id,
                    "name": "Rifle loadout",
                    "quantity": 1,
                    "army_id": 101,
                }
            ],
        }
    ]
    assert army["composite_options"] == [
        {
            "option_id": 7,
            "name": "Ranger pair",
            "source_unit_id": 1,
            "points": 50,
            "swc": "1.5",
            "minis": 2,
            "disabled": False,
            "compatible": None,
            "habilities": None,
            "orders": [{"type": "REGULAR", "list": 2, "total": 2}],
            "includes": [
                {
                    "loadout_payload_id": payload_id,
                    "name": "Rifle loadout",
                    "quantity": 1,
                    "army_id": 101,
                }
            ],
        }
    ]


def test_unit_rule_filters_match_profiles_and_loadouts(app: Callable) -> None:
    for parameter in (
        "skill_id=11",
        "equipment_id=21",
        "weapon_id=31",
        "skill_id=stealth",
        "equipment_id=medikit",
        "weapon_id=combi-rifle",
    ):
        status, _, body = request(app, "/api/units", query=parameter)
        assert status == 200
        assert {item["id"] for item in json.loads(body)["items"]} == {1}

    status, _, body = request(app, "/api/units", query="skill_id=stealth&weapon_id=combi-rifle")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1}

    status, _, body = request(app, "/api/units", query="skill_id=999")
    assert status == 200
    assert json.loads(body)["items"] == []


def test_unit_profile_help_is_rules_backed_and_optional(
    app: Callable, tmp_path: Path,
) -> None:
    status, _, body = request(app, "/api/unit-profile-help")
    assert status == 200
    assert json.loads(body) == {"items": [], "attributes": []}

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_database_path=rules_path)

    status, _, body = request(rules_app, "/api/unit-profile-help")
    assert status == 200
    payload = json.loads(body)
    items = payload["items"]
    assert {item["id"] for item in payload["attributes"]} == {
        "attribute:mov",
        "attribute:cc",
        "attribute:bs",
        "attribute:ph",
        "attribute:wip",
        "attribute:arm",
        "attribute:bts",
        "attribute:vita",
        "attribute:str",
        "attribute:ava",
        "attribute:s",
        "attribute:swc",
        "attribute:c",
    }
    assert [item["key"] for item in items] == [
        "unit-profile",
        "attributes",
        "training-orders",
        "troop-type",
        "classification",
        "isc",
        "hackable",
        "peripheral",
        "equipment-weapons",
        "profile-options",
    ]
    assert items[6]["name"] == "Hackable"


def test_unit_categorical_filters_are_exposed_and_filter_units(app: Callable) -> None:
    status, _, body = request(app, "/api/unit-filters")
    assert status == 200
    assert json.loads(body) == {
        "troop_types": [
            {"id": 1, "slug": "line-trooper", "name": "Line Trooper"}
        ],
        "classifications": [
            {"id": 1, "slug": "light-infantry", "name": "Light Infantry"}
        ],
        "characteristics": [],
        "numeric": {
            "ava": {
                "exact_values": ["2"],
                "range": {"min": 2, "max": 2, "step": 1},
            },
            "points": {
                "exact_values": ["20"],
                "range": {"min": 20, "max": 20, "step": 1},
            },
            "swc": {
                "exact_values": ["0"],
                "range": {"min": 0.0, "max": 0.0, "step": 0.5},
            },
        },
    }

    for query in (
        "troop_type=1",
        "troop_type=line-trooper",
        "classification=1",
        "classification=light-infantry",
        "troop_type=line-trooper&classification=light-infantry",
    ):
        status, _, body = request(app, "/api/units", query=query)
        assert status == 200
        assert {item["id"] for item in json.loads(body)["items"]} == {1}

    status, _, body = request(app, "/api/units", query="characteristic=hackable")
    assert status == 200
    assert json.loads(body)["items"] == []


def test_unit_numeric_filters_support_exact_values_and_ranges(app: Callable) -> None:
    matching_queries = (
        "ava=2",
        "ava_min=1&ava_max=2",
        "points=20",
        "points_min=19&points_max=20",
        "swc=0",
        "swc_min=0&swc_max=0",
    )
    for query in matching_queries:
        status, _, body = request(app, "/api/units", query=query)
        assert status == 200
        assert {item["id"] for item in json.loads(body)["items"]} == {1}

    for query in ("ava=total", "ava_min=3", "points_max=19", "swc_min=0.5"):
        status, _, body = request(app, "/api/units", query=query)
        assert status == 200
        assert json.loads(body)["items"] == []



def test_unit_extended_results_are_opt_in_and_include_profile_context(app: Callable) -> None:
    status, _, body = request(app, "/api/units")
    assert status == 200
    normal = next(item for item in json.loads(body)["items"] if item["id"] == 1)
    assert "profiles" not in normal

    status, _, body = request(app, "/api/units", query="extended=1")
    assert status == 200
    item = next(item for item in json.loads(body)["items"] if item["id"] == 1)
    profile = item["profiles"][0]
    assert profile["name"] == "Ranger Profile"
    assert profile["type"] == "Line Trooper"
    assert profile["classification"] == "Light Infantry"
    assert {entry["army_id"] for entry in profile["availability"]} == {101, 201}
    assert {entry["ava"] for entry in profile["availability"]} == {2}

    status, _, body = request(app, "/api/units", query="extended=yes")
    assert status == 400
    assert json.loads(body)["error"] == "extended must be 0 or 1"

def test_optional_unit_modes_are_excluded_until_selected(app: Callable) -> None:
    status, _, body = request(app, "/api/units", query="army_id=101")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1}

    status, _, body = request(app, "/api/units", query="army_id=101&mercs=1")
    assert status == 200
    assert {item["id"] for item in json.loads(body)["items"]} == {1, 3}

    status, _, body = request(app, "/api/units", query="army_id=101&specops=1")
    assert status == 200
    payload = json.loads(body)
    assert {item["id"] for item in payload["items"]} == {1, 4}
    assert payload["availability"] == {
        "shown": 2,
        "available": 4,
        "filtered": 2,
        "categories": {
            "standard": {"shown": 1, "filtered": 0},
            "mercs": {"shown": 0, "filtered": 1},
            "specops": {"shown": 1, "filtered": 0},
            "teamops": {"shown": 0, "filtered": 1},
            "reinforcement": {"shown": 0, "filtered": 0},
        },
    }

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
    assert unit["slug"] == "ranger-prototype"
    assert unit["public_slug"] == "ranger-prototype"
    assert {army["id"] for army in unit["armies"]} == {101, 201}
    assert {army["id"]: army["public_slug"] for army in unit["armies"]} == {
        101: "zulu-company",
        201: "alpha-company",
    }
    for army in unit["armies"]:
        assert army["profiles"][0]["type"] == "Line Trooper"
        assert army["profiles"][0]["classification"] == "Light Infantry"
        assert army["profiles"][0]["profile_identity"] == "profile ranger"
        assert army["profiles"][0]["display_name"] == army["profiles"][0]["name"]
        assert army["profiles"][0]["skills"] == [
            {
                "id": 11,
                "name": "Stealth",
                "slug": "stealth",
                "quantity": None,
                "extras": [{"id": 41, "name": "+3"}],
            }
        ]
        assert army["profiles"][0]["equipment"] == [
            {
                "id": 21,
                "name": "Medikit",
                "slug": "medikit",
                "quantity": 2,
                "extras": [{"id": 42, "name": "Mimetism"}],
            }
        ]
        assert army["profiles"][0]["weapons"] == [
            {
                "id": 31,
                "name": "Combi Rifle",
                "slug": "combi-rifle",
                "quantity": None,
                "extras": [{"id": 43, "name": "AP"}],
            }
        ]
        assert army["loadouts"][0]["orders"] == [{"type": "regular", "list": 1, "total": 1}]
        assert army["loadouts"][0]["skills"] == [
            {
                "id": 11,
                "name": "Stealth",
                "slug": "stealth",
                "quantity": None,
                "extras": [{"id": 41, "name": "+3"}],
            }
        ]
        assert army["loadouts"][0]["equipment"] == [
            {
                "id": 21,
                "name": "Medikit",
                "slug": "medikit",
                "quantity": None,
                "extras": [{"id": 42, "name": "Mimetism"}],
            }
        ]
        assert army["loadouts"][0]["weapons"] == [
            {
                "id": 31,
                "name": "Combi Rifle",
                "slug": "combi-rifle",
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

    status, headers, slug_page = request(app, "/units/ranger-prototype")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"unit.js" in slug_page

    status, headers, slug_body = request(app, "/api/units/ranger-prototype")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    assert json.loads(slug_body) == unit

    status, _, body = request(app, "/api/units/not-a-unit")
    assert status == 404
    assert json.loads(body)["error"] == "Unit not found"

    status, _, body = request(app, "/api/units/9099")
    assert status == 404
    assert json.loads(body)["error"] == "Unit not found"


def test_unit_details_expose_source_attributed_notes(app: Callable) -> None:
    database_path = app.database.path
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE units SET notes = ? WHERE id = ?",
            ("Only this source variant has this restriction.", 1),
        )
        connection.execute(
            "INSERT INTO logical_unit_notes (logical_unit_id, source_unit_id, note) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(logical_unit_id, source_unit_id) DO UPDATE SET note = excluded.note",
            (1, 1, "Only this source variant has this restriction."),
        )
    _refresh_published_content_checksum(database_path)
    notes_app = create_app(database_path)

    status, _, body = request(notes_app, "/api/units/ranger-prototype")

    assert status == 200
    unit = json.loads(body)
    source_note = next(
        item for item in unit["source_notes"] if item["source_unit_id"] == 1
    )
    assert source_note["source_name"] == "Alpha Ranger"
    assert source_note["note"] == "Only this source variant has this restriction."
    assert source_note["is_representative"] is True
    assert {army["id"] for army in source_note["armies"]} == {101, 201}
    assert all("public_slug" in army for army in source_note["armies"])


def test_unit_details_expose_bidirectional_peripheral_controller_links(
    tmp_path: Path, app_database_template: Path
) -> None:
    database_path = tmp_path / "infinity.db"
    shutil.copy2(app_database_template, database_path)
    peripheral_app = create_app(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO application_peripheral_unit_sources "
            "(source_unit_id, logical_unit_id, type_id, source_id, source_name) "
            "VALUES (?, ?, ?, ?, ?)",
            (2, 2, "rule:peripheral-type:cyberplug", "test-source", "Beta Scout"),
        )
        connection.execute(
            "INSERT INTO application_peripheral_controller_access "
            "(id, source_id, controller_kind, army_id, unit_id, group_id, parent_id, "
            "source_name, type_id, relationship) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "peripheral-controller-access:test",
                "test-source",
                "loadout",
                101,
                1,
                1,
                1,
                "Alpha Ranger",
                "rule:peripheral-type:cyberplug",
                "access-pool",
            ),
        )
        connection.execute(
            "INSERT INTO application_peripheral_controller_targets "
            "(access_id, target_logical_unit_id) VALUES (?, ?)",
            ("peripheral-controller-access:test", 2),
        )

    status, _, body = request(peripheral_app, "/api/units/ranger-prototype")
    assert status == 200
    controller = json.loads(body)
    army = next(item for item in controller["armies"] if item["id"] == 101)
    assert army["loadouts"][0]["peripheral_access"] == [
        {
            "id": "peripheral-controller-access:test",
            "type_id": "rule:peripheral-type:cyberplug",
            "relationship": "access-pool",
            "targets": [{"id": 2, "slug": "beta-scout", "name": "Beta Scout"}],
        }
    ]

    status, _, body = request(peripheral_app, "/api/units/2")
    assert status == 200
    target = json.loads(body)
    assert target["peripheral_type_ids"] == ["rule:peripheral-type:cyberplug"]
    assert target["peripheral_controllers"] == [
        {
            "id": "peripheral-controller-access:test",
            "type_id": "rule:peripheral-type:cyberplug",
            "relationship": "access-pool",
            "controller_kind": "loadout",
            "controller_option_name": "Rifle loadout",
            "army": {"id": 101, "name": "Zulu Company"},
            "controller": {
                "id": 1,
                "slug": "ranger-prototype",
                "name": "Alpha Ranger",
            },
        }
    ]


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
        ({"army_id": "missing-army"}, set()),
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
        "army_id=ABC",
        "army_id=9223372036854775808",
        "ava=-1",
        "ava=100",
        "ava=1&ava_min=1",
        "ava_min=3&ava_max=2",
        "points=10&points_max=10",
        "points_min=1.5",
        "swc=free",
        "swc_min=-1",
        "swc_min=2&swc_max=1",
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
    assert b'href="/armies"' in body
    assert b'href="/units"' in body
    assert b'href="/ammunition"' in body
    assert b'href="/traits"' in body
    assert b'href="/labels"' in body
    assert b'href="/states"' in body
    assert b'href="/hacking-programs"' in body
    assert b"Army data last changed" in body
    assert b"September 3, 2026" in body
    assert b'class="snapshot-date developer-only">Snapshot downloaded' in body
    assert b"September 10, 2026" in body
    assert f'data-app-version="{__version__}"'.encode() in body
    assert f'data-static-version="{STATIC_ASSET_VERSION}"'.encode() in body
    assert f'data-static-revision="{STATIC_ASSET_REVISION}"'.encode() in body
    assert b'data-snapshot-revision="' in body
    assert f"/static/version-check.js?v={STATIC_ASSET_VERSION}".encode() in body
    assets = re.findall(r'(?:src|href)=["\'](/static/[^"\']+)', body.decode())
    assert assets
    for asset in assets:
        assert asset.endswith(f"?v={STATIC_ASSET_VERSION}")
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
    assert b'id="unit-count-details"' in body
    assert b'id="unit-count-shown-breakdown"' in body
    assert b'id="unit-count-filtered-breakdown"' in body
    assert b"Optional availability categories may overlap" in body
    for filter_id in (
        b'troop-type-filter',
        b'classification-filter',
        b'characteristic-filter',
    ):
        assert filter_id in body
    for exact_filter in (b'ava-filter', b'points-filter', b'swc-filter'):
        assert b'<select id="' + exact_filter + b'" disabled>' in body
    assert body.count(b'<option value="">Any</option>') >= 3
    assert b'id="extended-results" type="checkbox"' in body
    assert b'</details><label class="extended-results-control">' in body
    for range_filter in (b'ava', b'points', b'swc'):
        assert b'data-range-filter="' + range_filter + b'"' in body
        assert b'id="' + range_filter + b'-min-filter" class="range-input range-input-min"' in body
        assert b'id="' + range_filter + b'-max-filter" class="range-input range-input-max"' in body
        assert b'id="' + range_filter + b'-range-reset" class="numeric-range-reset"' in body
        assert b'aria-label="Reset ' in body

    status, _, script = request(app, "/static/app.js")
    assert status == 200
    assert b'className = "page-results-summary"' in script
    assert b"renderAvailabilitySummary(data)" in script
    assert b"summary.shown" in script
    assert b"summary.available" in script
    assert b'populateNumericFilter("ava", unitFilters.numeric?.ava)' in script
    assert b'updateNumericRangeFromInput(control, input)' in script
    assert b'control.container.classList.toggle("is-active", isActive)' in script
    assert b'control.reset.disabled = !isActive' in script
    assert b'resetNumericRangeAndApply(control)' in script
    assert b'avaMin: avaExact ? ""' in script
    assert b'pointsMin: pointsExact ? ""' in script
    assert b'swcMin: swcExact ? ""' in script
    assert b'renderUnitRows(elements.list, data.items, { extended: state.extended })' in script
    assert b'advancedFilters?.addEventListener("toggle"' not in script
    assert b'extendedPreferenceTouched' not in script
    assert b'params.get("extended") === "1"' in script

    status, _, unit_list_script = request(app, "/static/unit-list.js")
    assert status == 200
    assert b'unit-extended-profile-subordinate' in unit_list_script
    assert b'unit-profile-availability-value' in unit_list_script
    assert b'if (!extended && displayArmySymbol)' in unit_list_script
    assert b'nameCell.colSpan = 2' in unit_list_script
    assert b'row.append(nameCell, idCell)' in unit_list_script
    assert b'unit-profile-characteristic-symbol' in unit_list_script
    assert b'unit-profile-characteristic-fallback' in unit_list_script
    assert b'developerOnlyCharacteristic(characteristic)' in unit_list_script
    assert b'unit-profile-troop-type-long' in unit_list_script
    assert b'unit-profile-troop-type-short' in unit_list_script

    status, _, unit_presentation_script = request(app, "/static/unit-presentation.js")
    assert status == 200
    for characteristic in (b"no cube", b"non hackable", b"not impetuous"):
        assert characteristic in unit_presentation_script

    status, _, app_script = request(app, "/static/app.js")
    assert status == 200
    assert b'(item) => troopTypeLabel(item.name)' in app_script

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(
        styles,
        ".double-range-slider",
        {
            "z-index": "1",
            "isolation": "isolate",
            "height": "var(--control-height)",
            "overflow": "visible",
            "border": "1px solid var(--color-control-border)",
            "border-radius": "var(--radius-sm)",
            "background": "var(--color-surface-default)",
        },
    )
    assert_css_rule(
        styles,
        ".range-slider-track",
        {
            "top": "50%",
            "right": "10px",
            "left": "10px",
            "transform": "translateY(-50%)",
        },
    )
    assert_css_rule(
        styles,
        ".range-input",
        {"top": "50%", "transform": "translateY(-50%)"},
    )
    assert_css_rule(
        styles,
        ".range-value-bubble",
        {"z-index": "6", "opacity": "0", "visibility": "hidden"},
    )
    assert_css_rule(styles, ".range-value-max", {"top": "30px"})
    assert (
        b".double-range-slider.is-active .range-value-bubble,"
        b"\n.double-range-slider:hover .range-value-bubble,"
        b"\n.double-range-slider:focus-within .range-value-bubble {"
    ) in styles
    assert_css_rule(
        styles,
        ".range-slider-selected",
        {"background": "var(--color-range-selection-muted)"},
    )
    assert_css_rule(
        styles,
        ".double-range-slider.is-active .range-slider-selected",
        {"background": "var(--color-action-primary)"},
    )
    assert_css_rule(
        styles,
        ".extended-results-control input",
        {"width": "16px", "height": "16px", "min-height": "0"},
    )


def test_browser_version_check_uses_an_uncached_server_version(app: Callable) -> None:
    status, headers, body = request(app, "/api/version")

    assert status == 200
    assert headers["cache-control"] == "no-store"
    version = json.loads(body)
    assert version["version"] == __version__
    assert version["static_revision"] == STATIC_ASSET_REVISION
    assert len(version["snapshot_revision"]) == 64
    assert int(version["snapshot_revision"], 16) >= 0

    status, _, script = request(app, "/static/version-check.js")
    assert status == 200
    assert b'from "./api.js"' in script
    assert b"getVersion()" in script
    assert b"snapshot_revision: snapshotRevision" in script
    assert b"static_revision: staticRevision" in script
    assert b"currentStaticRevision" in script
    assert b"currentSnapshotRevision" in script
    assert b'freshUrl.searchParams.set("app-version", version || currentVersion)' in script
    assert b'freshUrl.searchParams.set("static-revision", staticRevision)' in script
    assert b'freshUrl.searchParams.set("snapshot-revision", snapshotRevision)' in script
    assert b"window.location.replace(freshUrl)" in script


def test_browser_json_transport_is_centralized_in_api_module(app: Callable) -> None:
    for asset, helper in (
        ("catalog-list.js", b"getCatalogItems(page, pageController.signal)"),
        ("catalog-detail.js", b"getCatalogItem(catalog, itemId, pageController.signal)"),
        (
            "hacking-program-detail.js",
            b'getCatalogItem("hacking-programs", itemId, pageController.signal)',
        ),
        ("skill.js", b'getCatalogItem("skills", skillId, pageController.signal)'),
        ("skill-extras.js", b"getSkillExtras(pageController.signal)"),
        ("glossary.js", b"getGlossary(controller.signal)"),
        ("version-check.js", b"getVersion()"),
    ):
        status, _, body = request(app, f"/static/{asset}")
        assert status == 200
        assert b'from "./api.js"' in body
        assert helper in body
        assert b"fetch(" not in body


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/armies",
        "/units",
        "/units/1",
        "/skills",
        "/skills/1",
        "/equipment",
        "/equipment/1",
        "/weapons",
        "/weapons/1",
        "/ammunition",
        "/ammunition/example",
        "/traits",
        "/traits/example",
        "/labels",
        "/labels/example",
        "/states",
        "/states/example",
        "/hacking-programs",
        "/hacking-programs/example",
        "/fireteams",
        "/glossary",
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
    assert f"Version {__display_version__}".encode() in body


@pytest.mark.parametrize(
    "path",
    [
        "/skills",
        "/skills/example",
        "/equipment",
        "/equipment/example",
        "/weapons",
        "/weapons/example",
        "/traits",
        "/traits/example",
        "/labels",
        "/labels/example",
        "/states",
        "/states/example",
        "/hacking-programs",
        "/hacking-programs/example",
        "/glossary",
    ],
)
def test_rules_reference_pages_share_the_same_shell_classification(
    app: Callable, path: str
) -> None:
    status, _, body = request(app, path)

    assert status == 200
    assert (
        b'<span class="catalog-tag"><span aria-hidden="true"></span> Rules reference</span>' in body
    )


@pytest.mark.parametrize(
    ("path", "active_href"),
    [
        ("/armies", "/armies"),
        ("/units", "/units"),
        ("/units/example", "/units"),
        ("/skills", "/skills"),
        ("/skills/example", "/skills"),
        ("/equipment", "/equipment"),
        ("/equipment/example", "/equipment"),
        ("/weapons", "/weapons"),
        ("/weapons/example", "/weapons"),
        ("/ammunition", "/ammunition"),
        ("/ammunition/example", "/ammunition"),
        ("/traits", "/traits"),
        ("/traits/example", "/traits"),
        ("/labels", "/labels"),
        ("/labels/example", "/labels"),
        ("/states", "/states"),
        ("/states/example", "/states"),
        ("/hacking-programs", "/hacking-programs"),
        ("/hacking-programs/example", "/hacking-programs"),
        ("/fireteams", "/fireteams"),
        ("/glossary", "/glossary"),
        ("/about", "/about"),
    ],
)
def test_browser_routes_keep_their_parent_navigation_active(
    app: Callable, path: str, active_href: str
) -> None:
    status, _, body = request(app, path)

    assert status == 200
    assert f'href="{active_href}" aria-current="page"'.encode() in body


def test_every_browser_page_has_a_meta_description(app: Callable) -> None:
    for path in (
        "/",
        "/armies",
        "/units",
        "/units/example",
        "/skills",
        "/skills/example",
        "/equipment",
        "/equipment/example",
        "/weapons",
        "/weapons/example",
        "/traits",
        "/traits/example",
        "/labels",
        "/labels/example",
        "/states",
        "/states/example",
        "/hacking-programs",
        "/hacking-programs/example",
        "/fireteams",
        "/glossary",
        "/skill-extras",
        "/about",
    ):
        status, _, body = request(app, path)
        assert status == 200
        assert b'<meta name="description"' in body


def test_landing_page_states_independence_and_asset_permission(app: Callable) -> None:
    status, _, body = request(app, "/")

    assert status == 200
    assert b"Open-source Infinity community reference" in body
    assert b"non-commercial open-source community project" in body
    assert b"not affiliated with Corvus Belli S.L." in body
    assert b"explicitly granted InfinityDB permission" in body
    assert b"permission to use and redistribute" in body
    assert b"Infinity graphical" in body
    assert b"assets used by the project" in body


def test_landing_database_links_match_primary_navigation_order(app: Callable) -> None:
    status, _, body = request(app, "/")

    assert status == 200
    navigation_links = re.findall(rb'<a class="nav-item" href="([^"]+)"', body)
    landing_links = re.findall(rb'<a class="landing-link" href="([^"]+)"', body)
    assert navigation_links[:-1] == landing_links
    assert navigation_links[-1] == b"/about"


def test_landing_page_links_to_fireteams(app: Callable) -> None:
    status, _, body = request(app, "/")

    assert status == 200
    assert b'<a class="landing-link" href="/fireteams">' in body
    assert b"<strong>Fireteams</strong>" in body


def test_landing_hero_keeps_its_logo_with_the_heading_on_mobile(app: Callable) -> None:
    status, _, body = request(app, "/")

    assert status == 200
    assert b'<div class="landing-hero-heading">' in body
    assert body.index(b"landing-hero-heading") < body.index(b'class="landing-logo"')
    assert body.index(b'class="landing-logo"') < body.index(b"landing-hero-content")

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(
        styles,
        ".landing-logo",
        {
            "grid-column": "2",
            "grid-row": "1",
            "align-self": "start",
            "width": "min(30vw, 135px)",
            "height": "auto",
        },
    )
    assert_css_rule(styles, ".landing-hero-content", {"grid-column": "1 / -1"})


def test_listing_tables_use_semantic_column_layout(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    assert_css_rule(
        styles,
        ".table-viewport",
        {
            "width": "100%",
            "min-width": "0",
            "max-width": "100%",
            "overflow-x": "auto",
        },
    )
    assert_css_rule(styles, ".data-table--listing", {"width": "100%"})
    assert_css_rule(
        styles,
        ".data-table--listing .table-column--primary",
        {"width": "100%"},
    )
    assert_css_rule(
        styles,
        (
            ".data-table--listing .table-column--descriptor, "
            ".data-table--listing .table-column--metric, "
            ".data-table--listing .table-column--technical"
        ),
        {"width": "1%"},
    )
    assert_css_rule(
        styles,
        ".table-column--metric, .table-column--technical",
        {"white-space": "nowrap"},
    )
    assert_css_rule(
        styles,
        ".table-column--metric",
        {"text-align": "right", "font-variant-numeric": "tabular-nums"},
    )
    assert_css_rule(styles, ".table-column--technical", {"text-align": "right"})
    assert_css_rule(
        styles,
        "tbody .table-column--technical",
        {
            "color": "var(--color-text-technical)",
            "font-family": "var(--font-family-mono)",
            "font-size": "var(--font-size-xs)",
        },
    )
    assert_css_rule(
        styles,
        ".data-table--interactive tbody tr:hover",
        {"background": "var(--color-surface-interactive-hover)"},
    )
    assert b"\ntbody tr:hover {" not in styles
    assert b"  .id-column {\n    display: none;\n  }" not in styles

    status, _, units = request(app, "/units")
    assert status == 200
    assert b'class="data-table--listing data-table--interactive"' in units
    assert b'class="table-column--primary" scope="col">Unit</th>' in units
    assert b'class="table-column--descriptor" scope="col">Available in</th>' in units
    assert b'class="id-column table-column--technical" scope="col">Unit ID</th>' in units

    assert_css_rule(styles, ".army-tags", {"--symbols-per-row": "4"})
    assert_css_rule(
        styles,
        ".army-tags-compact",
        {"--symbols-per-row": "6", "gap": "3px"},
    )
    assert_css_rule(
        styles,
        ".army-tags-compact .army-symbol",
        {"width": "17px", "height": "17px"},
    )

    status, _, unit_list = request(app, "/static/unit-list.js")
    assert status == 200
    assert b"if (armies.length > 12)" in unit_list


def test_generated_tables_own_accessible_semantics_and_normal_wrapping(app: Callable) -> None:
    status, _, unit_js = request(app, "/static/unit.js")
    assert status == 200
    assert b'caption.className = "sr-only";' in unit_js
    assert b'th.scope = "col";' in unit_js
    assert b'"Loadouts",' in unit_js
    assert b'"Composite options",' in unit_js
    assert b'"Profiles",' in unit_js
    assert b'`${profile.name || "Unit"} general profile`' in unit_js

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(styles, ".unit-name", {"overflow-wrap": "break-word"})
    assert_css_rule(styles, ".army-tag", {"white-space": "nowrap"})
    assert_css_rule(
        styles,
        ".unit-detail .profile-summary>*",
        {"overflow-wrap": "break-word"},
    )
    assert_css_rule(
        styles,
        ".weapon-profile tbody td",
        {"overflow-wrap": "break-word"},
    )


def test_secondary_tables_use_shared_semantic_layout(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    assert_css_rule(
        styles,
        ".data-table--reference, .data-table--profile",
        {"width": "100%"},
    )
    assert_css_rule(
        styles,
        ".data-table--profile .table-column--descriptor",
        {"width": "100%"},
    )
    assert_css_rule(
        styles,
        ".data-table--profile .table-column--metric",
        {"width": "1%", "text-align": "center"},
    )

    status, _, skill = request(app, "/static/skill.js")
    assert status == 200
    assert b'data-table--compact data-table--reference' in skill
    assert b'data-table--compact data-table--listing data-table--interactive' in skill
    assert b'{ label: "Program", role: "primary" }' in skill
    assert b'{ label: "Attack MOD", role: "metric" }' in skill
    assert b'{ label: "Target", role: "descriptor" }' in skill

    status, _, catalog_detail = request(app, "/static/catalog-detail.js")
    assert status == 200
    assert b"function tableViewport(table, className = \"\")" in catalog_detail
    assert b'data-table--compact data-table--profile weapon-statline' in catalog_detail
    assert b'data-table--compact data-table--listing data-table--interactive' in catalog_detail
    assert b'cell.className = "table-column--metric";' in catalog_detail

    status, _, hacking = request(app, "/static/hacking-program-detail.js")
    assert status == 200
    assert b'table.className = "data-table--compact data-table--profile";' in hacking
    assert b'"Targets", program.targets?.length' in hacking
    assert b'"descriptor"' in hacking
    assert b'"metric"' in hacking

    status, _, modifiers = request(app, "/skill-extras")
    assert status == 200
    assert b'class="data-table--reference skill-modifier-table"' in modifiers
    assert b'class="table-column--primary" scope="col">Skill</th>' in modifiers
    assert b"skill-modifier-units" in modifiers

    assert b".fireteam-member-table th:first-child" not in styles
    assert b".fireteam-member-table th:nth-child" not in styles
    assert b".fireteam-reference-table th:first-child" not in styles
    assert b".fireteam-reference-table th:nth-child" not in styles


def test_intermediate_widths_reserve_space_for_movement_values(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    assert b"@media (min-width: 601px) and (max-width: 700px)" in styles
    assert_css_rule(
        styles,
        ".attribute-statline",
        {
            "--movement-column-width": "68px",
            "grid-template-columns": ("var(--movement-column-width) repeat(8, minmax(0, 1fr))"),
        },
    )
    assert_css_rule(
        styles,
        'html[data-distance-unit="in"] .attribute-statline',
        {"--movement-column-width": "56px"},
    )
    assert_css_rule(styles, ".attribute-statline > div", {"padding-inline": "4px"})
    assert_css_rule(
        styles,
        ".attribute-statline, .attribute-statline-with-availability",
        {"grid-template-columns": "68px repeat(4, minmax(0, 1fr))"},
    )
    assert_css_rule(
        styles,
        (
            'html[data-distance-unit="in"] .attribute-statline, '
            'html[data-distance-unit="in"] .attribute-statline-with-availability'
        ),
        {"grid-template-columns": "56px repeat(4, minmax(0, 1fr))"},
    )


def test_very_narrow_detail_layout_wraps_titles_and_stacks_general_profiles(
    app: Callable,
) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    assert b"@media (max-width: 400px)" in styles
    assert_css_rule(styles, "h1", {"overflow-wrap": "break-word"})
    assert_css_rule(
        styles,
        ".unit-detail .general-profile .statline, .unit-detail .general-profile .statline tbody",
        {"display": "block", "width": "100%"},
    )
    assert_css_rule(
        styles,
        ".unit-detail .general-profile .statline tr",
        {"display": "grid", "grid-template-columns": "minmax(0, 1fr)"},
    )
    assert_css_rule(
        styles,
        ".unit-detail .general-profile .general-item-label, "
        ".unit-detail .general-profile .profile-attributes-label",
        {"padding": "10px 16px 4px"},
    )
    assert_css_rule(
        styles,
        ".unit-detail .general-profile .general-item-list, "
        ".unit-detail .general-profile .profile-attributes",
        {"padding": "4px 16px 12px"},
    )


def test_developer_mode_controls_database_id_visibility_in_settings_menu(
    app: Callable,
) -> None:
    status, _, body = request(app, "/units")

    assert status == 200
    assert b'id="developer-mode-toggle"' in body
    assert b'id="remember-settings-toggle"' in body
    assert (
        b'id="fireteams-include-wildcards-toggle" class="setting-switch" '
        b'type="checkbox" checked'
        in body
    )
    assert b'id="cookie-consent-dialog"' in body
    assert b"Allow cookies" in body
    assert b"Remember settings with browser cookies" in body
    assert b"Fireteam Wildcard" in body
    assert b"InfinityDB / Player reference" in body
    assert b'<div class="menu settings-menu" data-menu>' in body
    assert b'aria-controls="settings-menu"' in body
    assert body.count(b'class="setting-switch') == 9
    assert b'class="setting-row setting-row--choice"' in body
    assert b'class="setting-row developer-only"' in body
    assert b'class="settings-group"' in body
    assert b'>Settings <span aria-hidden="true">' in body
    assert body.index(b"compact-navigation-menu") < body.index(b"settings-menu")
    assert b'<th class="id-column table-column--technical" scope="col">Unit ID</th>' in body

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(
        styles,
        (
            'html:not([data-developer-mode="true"]) .developer-only, '
            'html:not([data-developer-mode="true"]) .id-column'
        ),
        {"display": "none"},
    )
    assert_css_rule(styles, ".settings-menu", {"margin-top": "32px"})
    assert_css_rule(
        styles,
        ".setting-row",
        {"display": "flex", "justify-content": "space-between"},
    )
    assert_css_rule(
        styles,
        ".setting-switch",
        {"appearance": "none", "width": "var(--setting-switch-width)"},
    )
    assert_css_rule(
        styles,
        ".setting-switch--choice",
        {"--setting-switch-width": "29px", "--setting-switch-height": "16px"},
    )
    assert b".developer-toggle" not in styles
    assert b".optional-unit-toggle" not in styles
    assert b".remember-settings-toggle" not in styles
    assert b".distance-toggle" not in styles
    assert_css_rule(
        styles,
        ".compact-menu-panel",
        {"position": "static", "display": "flex"},
    )
    assert_css_rule(
        styles,
        ".settings-menu>.compact-menu-panel",
        {"display": "none"},
    )
    assert_css_rule(
        styles,
        '.settings-menu[data-open="true"]>.compact-menu-panel',
        {"display": "flex"},
    )
    assert_css_rule(styles, ".menu-label", {"display": "none"})
    assert_css_rule(
        styles,
        ".sidebar",
        {"position": "sticky", "z-index": "4", "inset": "auto", "top": "0"},
    )
    assert b".cookie-consent-dialog" in styles
    assert b"background: var(--color-surface-default);" in styles

    status, _, preferences = request(app, "/static/preferences.js")
    assert status == 200
    assert b'const DEVELOPER_MODE_KEY = "infinity-db-developer-mode";' in preferences
    assert b'const REMEMBER_SETTINGS_KEY = "infinity-db-remember-settings";' in preferences
    assert (
        b'const FIRETEAMS_INCLUDE_WILDCARDS_KEY = "infinity-db-fireteams-include-wildcards";'
        in preferences
    )
    assert b"function initializeFireteamsIncludeWildcardsToggle()" in preferences
    assert b"function fireteamsIncludeWildcards()" in preferences
    assert b'new CustomEvent("fireteamswildcardschange"' in preferences
    assert b"function initializeDeveloperModeToggle()" in preferences
    assert b"function initializeRememberSettingsToggle()" in preferences
    assert b"dialog.showModal()" in preferences
    assert b'getElementById("distance-unit-toggle")?.checked ? "in" : "cm"' in preferences
    assert b'getElementById("developer-mode-toggle")?.checked' in preferences
    assert b"window.localStorage" not in preferences
    assert b"window.sessionStorage.getItem(name)" in preferences
    assert b"window.sessionStorage.setItem(name, value)" in preferences
    assert b"if (!isRememberingSettings()) return session;" in preferences
    assert b"const persistent = cookieValue(name);" in preferences
    assert b"if (persistent === undefined) return session;" in preferences
    assert b"setSessionValue(name, persistent);" in preferences
    assert b'new CustomEvent("developermodechange"' in preferences
    assert b'const unit = savedUnit === "cm" ? "cm" : "in";' in preferences
    assert preferences.count(b"defaultChecked: true") == 4
    assert (
        b'id="distance-unit-toggle" class="setting-switch setting-switch--choice" '
        b'type="checkbox" checked'
        in body
    )
    for optional_id in (
        b"mercs-filter",
        b"specops-filter",
        b"teamops-filter",
        b"reinforcement-filter",
    ):
        assert (
            b'id="' + optional_id + b'" class="setting-switch" type="checkbox" checked'
            in body
        )

    status, _, navigation = request(app, "/static/navigation.js")
    assert status == 200
    assert b'menu.classList.contains("settings-menu")' in navigation


def test_browser_pages_require_external_same_origin_scripts(app: Callable) -> None:
    paths = (
        "/",
        "/units",
        "/units/ranger-prototype",
        "/skill-extras",
        "/skills",
        "/skills/11",
        "/equipment",
        "/equipment/21",
        "/weapons",
        "/weapons/31",
        "/ammunition",
        "/ammunition/shock",
        "/traits",
        "/traits/suppressive-fire",
        "/labels",
        "/labels/hackable",
        "/states",
        "/states/unconscious",
        "/hacking-programs",
        "/hacking-programs/carbonite",
        "/fireteams",
        "/glossary",
        "/about",
    )
    expected_csp = (
        "default-src 'self'; script-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )

    for path in paths:
        status, headers, body = request(app, path)
        assert status == 200
        assert headers["content-security-policy"] == expected_csp
        assert re.search(rb"\son[a-z]+\s*=", body, flags=re.IGNORECASE) is None

        scripts = list(
            re.finditer(
                rb"<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>",
                body,
                flags=re.IGNORECASE | re.DOTALL,
            )
        )
        assert scripts
        for script in scripts:
            assert re.search(rb"\bsrc\s*=", script.group("attrs"), flags=re.IGNORECASE)
            assert not script.group("body").strip()


def test_compact_navigation_is_closed_when_a_page_is_restored(app: Callable) -> None:
    status, _, body = request(app, "/units")

    assert status == 200
    assert (
        f'<script type="module" '
        f'src="/static/navigation.js?v={STATIC_ASSET_VERSION}"></script>'.encode()
        in body
    )
    assert (
        f'<script type="module" '
        f'src="/static/page-navigation.js?v={STATIC_ASSET_VERSION}"></script>'.encode()
        in body
    )
    assert b'<p class="nav-label menu-label">Navigation</p>' in body
    assert b'aria-controls="compact-navigation-menu"' in body
    assert b'>Navigation <span aria-hidden="true">' in body
    assert b'data-global-search' in body
    assert b'class="global-search-toggle"' in body
    assert b'aria-controls="global-search-query"' in body

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
    assert b'window.matchMedia("(max-width: 700px)")' in navigation
    assert b'setGlobalSearchOpen(!isOpen, { focus: !isOpen })' in navigation
    assert b'globalSearchToggle.setAttribute("aria-expanded", String(open))' in navigation
    assert (
        b'globalSearchToggle.setAttribute("aria-label", open ? "Close search" : "Open search")'
        in navigation
    )
    assert b'navigationShell.dataset.searchOpen = String(open)' in navigation
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
    assert_css_rule(
        styles,
        '.menu[data-open="true"] > .compact-menu-panel',
        {"display": "flex"},
    )
    assert_css_rule(styles, ".sidebar", {"position": "sticky", "inset": "auto", "top": "0"})
    assert_css_rule(
        styles,
        '.global-search[data-open="true"] .global-search-input',
        {"display": "block"},
    )
    assert (
        b"@media (max-width: 400px) {\n  .brand>span {\n    display: none;\n  }\n}"
        in styles
    )
    assert b'window.addEventListener("pageshow", closeMenu)' in navigation
    assert b'window.addEventListener("pageshow", closeGlobalSearch)' in navigation


def test_soft_navigation_preserves_shell_state_and_disposes_page_handlers(
    app: Callable,
) -> None:
    status, _, page_navigation = request(app, "/static/page-navigation.js")
    assert status == 200
    assert b"pathname.startsWith(`${linkPath}/`)" in page_navigation
    assert b'link.setAttribute("aria-current", "page")' in page_navigation
    assert b'link.removeAttribute("aria-current")' in page_navigation
    assert b'link.toggleAttribute("aria-current", isCurrent)' not in page_navigation
    assert b"syncDescription(nextDocument)" in page_navigation
    assert b"document.querySelector('meta[name=\"description\"]')" in page_navigation

    for asset in (
        "catalog-list.js",
        "catalog-detail.js",
        "skill.js",
        "skill-extras.js",
        "unit.js",
        "fireteams.js",
        "hacking-program-detail.js",
    ):
        status, _, script = request(app, f"/static/{asset}")
        assert status == 200
        assert b"infinity:beforenavigation" in script
        assert b"pageController.abort()" in script

    for asset in ("catalog-detail.js", "skill.js", "skill-extras.js", "unit.js", "fireteams.js"):
        status, _, script = request(app, f"/static/{asset}")
        assert status == 200
        assert b"signal: pageController.signal" in script


def test_about_page_is_served_with_active_navigation(app: Callable) -> None:
    status, headers, body = request(app, "/about")

    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Know your options." in body
    assert b'Made by Johannes "Franky" Haglund' in body
    assert f"Version {__display_version__}".encode() in body
    assert b"developed in the open" in body
    assert b"https://github.com/frankysan/InfinityDB" in body
    assert b"LLM code disclosure" in body
    assert b"Version 0.8 connects more of the game" in body
    assert b"Version 0.9 closes the remaining application-presentation gaps" in body
    assert b"0.10 is the consistency, presentation, and release-hardening pass" in body
    assert b"1.0 completes the current rules/reference coverage" in body
    assert b"not affiliated with Corvus Belli S.L." in body
    assert b"explicitly permitted InfinityDB to use and redistribute" in body
    assert b'href="/about" aria-current="page"' in body
    assert b"about.js" in body


def test_web_route_handlers_keep_presentation_and_api_ownership_separate(app: Callable) -> None:
    page = app.presentation.handle("/units", "")
    assert page is not None
    assert page.content_type == "text/html; charset=utf-8"
    assert app.presentation.handle("/api/version", "") is None

    api = app.api.handle("/api/version", "")
    assert api is not None
    assert api.content_type == "application/json; charset=utf-8"
    assert app.api.handle("/units", "") is None


def test_dynamic_symbol_routes_serve_project_owned_svg_fixtures(
    app: Callable,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    web_presentation = importlib.import_module("infinity_db.web.presentation")
    package_root = tmp_path / "package"
    fixture_paths = (
        "static/armies/test/101-test.svg",
        "static/characteristics/cube.svg",
        "static/orders/regular.svg",
        "static/units/test/1-test.svg",
    )
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'
    for relative in fixture_paths:
        path = package_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(svg)

    monkeypatch.setattr(web_presentation, "files", lambda _: package_root)

    for url in (
        "/static/armies/test/101-test.svg",
        "/static/characteristics/cube.svg",
        "/static/orders/regular.svg",
        "/static/units/test/1-test.svg",
    ):
        status, headers, body = request(app, url)
        assert status == 200
        assert headers["content-type"] == "image/svg+xml"
        assert body == svg

    for url in ("/static/orders/cube.svg", "/static/characteristics/regular.svg"):
        status, _, _ = request(app, url)
        assert status == 404


@pytest.mark.full_assets
def test_army_symbol_is_served(app: Callable) -> None:
    catalog = SymbolCatalog()
    for army_id in [101, 605, 998, 1199]:
        published = catalog.army_path(army_id)
        assert published is not None
        status, headers, body = request(app, f"/static/{published}")
        assert status == 200
        assert headers["content-type"] == "image/svg+xml"
        assert b"<svg" in body
    status, _, _ = request(app, "/static/armies/panoceania/not-an-army.svg")
    assert status == 404
    status, _, _ = request(app, "/static/army-symbols.js")
    assert status == 404


def test_browser_fonts_are_served_from_the_canonical_publication(app: Callable) -> None:
    fonts = (
        "/static/fonts/Audiowide/Audiowide-Regular.woff2",
        "/static/fonts/Oxanium/Oxanium-Variable.woff2",
        "/static/fonts/IBM_Plex_Sans/IBMPlexSans-Variable.woff2",
        "/static/fonts/IBM_Plex_Sans/IBMPlexSans-Italic-Variable.woff2",
        "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Regular.woff2",
        "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Medium.woff2",
        "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-SemiBold.woff2",
        "/static/fonts/IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Bold.woff2",
        "/static/fonts/IBM_Plex_Mono/IBMPlexMono-Regular.woff2",
    )
    for path in fonts:
        status, headers, body = request(app, path)
        assert status == 200
        assert headers["content-type"] == "font/woff2"
        assert body.startswith(b"wOF2")

    status, _, _ = request(app, "/static/fonts/Audiowide/OFL.txt")
    assert status == 404
    status, _, _ = request(app, "/static/fonts/Audiowide/not-a-font.woff2")
    assert status == 404


def test_assets_and_catalog_api_have_release_safe_cache_headers(app: Callable) -> None:
    status, headers, _ = request(app, f"/static/styles.css?v={STATIC_ASSET_VERSION}")
    assert status == 200
    assert headers["cache-control"] == "public, max-age=31536000, immutable"

    status, headers, _ = request(app, f"/static/styles.css?v={__version__}")
    assert status == 200
    assert headers["cache-control"] == "public, max-age=300, stale-while-revalidate=600"

    status, headers, _ = request(app, "/static/unit-list.js")
    assert status == 200
    assert headers["cache-control"] == "public, max-age=300, stale-while-revalidate=600"


def test_catalog_api_etag_revalidates_the_current_snapshot(app: Callable) -> None:
    status, headers, body = request(app, "/api/armies")

    assert status == 200
    assert body
    etag = headers["etag"]
    assert etag.startswith(f'"{__version__}-')

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
        connection.execute(
            "UPDATE logical_units SET name = ? WHERE representative_unit_id = ?",
            ("Updated Ranger", 1),
        )
    _refresh_published_content_checksum(rebuilt_database)
    rebuilt_app = create_app(rebuilt_database)

    rebuilt_status, rebuilt_headers, rebuilt_body = request(rebuilt_app, "/api/armies")
    assert rebuilt_status == 200
    assert rebuilt_body == body
    assert rebuilt_headers["etag"] != headers["etag"]


def test_versioned_modules_reference_their_matching_release_dependencies(app: Callable) -> None:
    status, headers, body = request(app, f"/static/unit.js?v={STATIC_ASSET_VERSION}")

    assert status == 200
    assert headers["cache-control"] == "public, max-age=31536000, immutable"
    assert f'from "./api.js?v={STATIC_ASSET_VERSION}"'.encode() in body
    assert f'from "./preferences.js?v={STATIC_ASSET_VERSION}"'.encode() in body

    status, _, body = request(app, f"/static/api.js?v={STATIC_ASSET_VERSION}")
    assert status == 200
    assert f'import("./preferences.js?v={STATIC_ASSET_VERSION}")'.encode() in body
    assert b'cache: "no-store"' in body

    status, headers, _ = request(app, "/api/armies")
    assert status == 200
    assert headers["cache-control"] == "public, max-age=300, stale-while-revalidate=600"


def test_unit_explorer_domain_filters_prefer_public_slugs(app: Callable) -> None:
    status, _, body = request(app, "/static/app.js")

    assert status == 200
    assert b"return army.public_slug || String(army.id);" in body
    assert b"return item.slug || String(item.id);" in body
    assert b"armyId: domainFilterIdentifier(armyId)" in body
    assert b"skillId: domainFilterIdentifier(skillId)" in body
    assert b"equipmentId: domainFilterIdentifier(equipmentId)" in body
    assert b"weaponId: domainFilterIdentifier(weaponId)" in body
    assert b"troopType: domainFilterIdentifier(troopType)" in body
    assert b"classification: domainFilterIdentifier(classification)" in body
    assert b"characteristic: domainFilterIdentifier(characteristic)" in body
    assert b"normalizeArmyFilterState(playableArmies)" in body
    for call in (
        b'normalizeCatalogFilterState(skills.items, "skillId")',
        b'normalizeCatalogFilterState(equipment.items, "equipmentId")',
        b'normalizeCatalogFilterState(weapons.items, "weaponId")',
    ):
        assert call in body
    for call in (
        b'normalizeUnitFilterState(unitFilters.troop_types, "troopType")',
        b'normalizeUnitFilterState(unitFilters.classifications, "classification")',
        b'normalizeUnitFilterState(unitFilters.characteristics, "characteristic")',
    ):
        assert call in body
    assert b"candidate.source_ids?.some((sourceId) => String(sourceId) === current)" in body


def test_army_selector_uses_backend_role_and_playability(app: Callable) -> None:
    status, _, body = request(app, "/static/app.js")

    assert status == 200
    assert b"Math.floor(Number(army.id) / 100)" not in body
    assert b"army.playable !== false" in body
    assert b'army.role === "reinforcement"' in body
    assert b'army.role === "sectorial" || army.role === "non_aligned"' in body
    assert b'army.role === "non_aligned" && army.group_id' in body


def test_unit_list_renders_all_toggle_visible_armies(app: Callable) -> None:
    status, _, body = request(app, "/static/unit-list.js")

    assert status == 200
    assert b"return [...armies].sort" in body
    assert b"const factionSlugs" not in body
    assert b"function factionSlug(" not in body
    assert b"Math.floor(Number(armyId) / 100)" not in body
    assert b"const faction = unit.display_faction?.slug;" in body
    assert body.count(b"unit.public_slug || unit.id") == 2


def test_unit_details_frontend_uses_backend_reinforcement_flags(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")

    assert status == 200
    assert b"[98, 99]" not in body
    assert b"function isReinforcementArmy(" not in body
    assert b'reinforcement: (army.availability_flags || []).includes("reinforcement"),' in body


def test_unit_details_frontend_uses_backend_faction_metadata(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")

    assert status == 200
    assert b"const factionGroups" not in body
    assert b"const factionSlugs" not in body
    assert b"Math.floor(Number(armyId) / 100)" not in body
    assert b"const faction = army.faction;" in body
    assert b"const displayFaction = unit.display_faction?.slug;" in body
    assert b"const unitIdentifier = /^\\/units\\/([a-z0-9]+(?:-[a-z0-9]+)*)$/" in body


def test_unit_details_frontend_collapses_army_profile_tables(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'document.createElement("details")' in body
    assert b"function isStandardArmy(army)" in body
    assert b"section.open = expanded" in body
    assert b"const profileKey = profile.profile_identity;" in body
    assert b"profile.display_name || profile.name" in body
    assert b"(?:REINF|REFUERZOS)" not in body
    assert b"function baseProfileName(" not in body
    assert b"function profileIdentity(" not in body
    assert b"profileIdentityWordAliases" not in body
    assert b"profileIdentityIgnoredWords" not in body


def test_unit_details_frontend_places_unit_symbols_on_general_profiles(
    app: Callable,
) -> None:
    status, _, unit_js = request(app, "/static/unit.js")
    assert status == 200
    assert b"staticSymbolPath" in unit_js
    assert b"profile.symbol_paths || []" in unit_js
    assert b"general-profile-symbols" in unit_js
    assert b"profileTitle(profile, profileSymbols)" in unit_js
    assert b"unitProfileSymbolPath" not in unit_js

    status, _, symbol_js = request(app, "/static/unit-symbols.js")
    assert status == 200
    assert b"export function staticSymbolPath" in symbol_js
    assert b"unit-symbol-map.js" not in symbol_js
    assert b"unitProfileSymbolSlug" not in symbol_js

    status, _, list_js = request(app, "/static/unit-list.js")
    assert status == 200
    assert b"army-symbols.js" not in list_js
    assert b"unit.display_army_symbol_path" in list_js
    assert b"unit.symbol_path" in list_js
    assert b"army.symbol_path" in list_js

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert b".general-profile-symbols" in styles
    assert b".general-profile-unit-symbol" in styles
    assert_css_rule(
        styles,
        ".unit-symbol.general-profile-unit-symbol",
        {"width": "56px", "height": "56px"},
    )
    assert b"--profile-symbol-title-space" not in unit_js
    assert b"general-profile--with-symbols" not in unit_js
    assert b".unit-symbol-detail" not in styles


def test_unit_details_frontend_displays_high_ava_as_total(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function displayAvailability(value)" in body
    assert b'return Number(value) >= 100 ? "Total" : displayStatlineValue(value)' in body


def test_unit_details_frontend_places_attributes_in_a_separate_row(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function attributeStatline(" in body
    assert b"generalDifferenceLabels = null" in body
    assert b'className: "data-label profile-attributes-label"' in body
    assert b'className: "data-label general-item-label"' in body
    assert b'"data-table--compact profile-details-table"' in body
    assert b'["Name", "Points", "SWC"]' in body
    assert b"attributeStatline(profile, generalStatsForProfile, true)" in body


def test_unit_details_frontend_labels_vitality_as_vita_or_str(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'["VITA", (profile) => profile.vitality]' in body
    assert b'["W", (profile) => profile.vitality]' not in body
    assert b"profile.is_structure === true || Number(profile.is_structure) === 1" in body
    assert b'label === "VITA" && isStructureProfile(profile) ? "STR" : label' in body
    assert b'is_structure: mostCommon(profiles, "is_structure")' in body


def test_unit_details_frontend_pluralizes_general_profile_heading(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'displayedGeneralProfiles.length === 1 ? "General profile" : "General profiles"' in body
    assert b"generalProfileTableRows([profile])" in body


def test_unit_details_frontend_marks_general_stats_that_vary_by_army(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function generalStatDifferenceLabels(profile)" in body
    assert b"general-stat-difference-indicator" in body
    assert b"One or more Army profiles differ from this General profile stat" in body

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(
        styles,
        ".general-stat-difference-indicator",
        {"font-size": "var(--font-size-xs)", "margin-left": "2px"},
    )


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
    assert_css_rule(styles, ".division-badge-surface", {"background": "#256d1b"})
    assert_css_rule(styles, ".division-badge-deepspace", {"background": "#d68623"})


def test_detail_views_reuse_shared_detail_style_primitives(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    for selector in [
        b".detail-group",
        b".detail-heading",
        b".surface-titlebar",
        b".surface-titlebar--subtle",
        b".data-label",
        b".badge",
    ]:
        assert selector in styles

    for path in ["/static/unit.js", "/static/skill.js", "/static/catalog-detail.js"]:
        status, _, body = request(app, path)
        assert status == 200
        assert b"detail-group" in body
        assert b"surface-titlebar surface-titlebar--subtle" in body

    assert b".data-surface-header" not in styles
    assert b".detail-section-title" not in styles


def test_recurring_presentation_colors_use_semantic_tokens(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")
    assert status == 200

    css = styles.decode("utf-8")
    root = re.search(r":root\s*\{.*?\n\}", css, flags=re.DOTALL)
    assert root is not None

    component_css = css[: root.start()] + css[root.end() :]
    color_literals = re.findall(
        r"#[0-9a-fA-F]{3,8}\b|(?:rgb|rgba)\([^)]*\)",
        component_css,
    )
    counts = Counter(literal.lower() for literal in color_literals)
    repeated = {literal: count for literal, count in counts.items() if count > 1}
    assert repeated == {}

    for token in [
        "--color-surface-data-header",
        "--color-surface-interactive-hover",
        "--color-text-heading",
        "--color-text-tertiary",
        "--color-text-technical",
        "--color-border-subtle",
        "--color-control-border",
        "--color-link-hover",
    ]:
        assert f"{token}:".encode() in styles


def test_weapon_range_tables_always_include_canonical_bands(app: Callable) -> None:
    status, _, body = request(app, "/static/catalog-detail.js")

    assert status == 200
    assert b"const canonicalWeaponRangeBands = [20, 40, 60, 80, 100, 120, 240];" in body
    assert b"const rangeBands = canonicalWeaponRangeBands;" in body
    assert b".sort((left, right) => Number(left.max) - Number(right.max));" in body
    assert b".find((range) => Number(range.max) >= maximum);" in body
    assert b'if (!matchingRange) return "--";' in body
    assert b"String(modifier)" in body
    assert b"maximum / 2.5" in body
    assert b"weaponRangeBands" not in body


def test_catalog_detail_frontend_uses_backend_trait_references(
    app: Callable,
) -> None:
    status, _, body = request(app, "/static/catalog-detail.js")

    assert status == 200
    assert b"profile.trait_references" in body
    assert b"function weaponTraitLinks(traits)" in body
    assert b"const label = trait.label || trait.name ||" in body
    assert b"link.href = `/traits/${encodeURIComponent(trait.slug)}`;" in body
    assert b"function canonicalTraitName(" not in body
    assert b"function traitSlug(" not in body
    assert b"Continous Damage" not in body
    assert b"BioWeapon" not in body


def test_surfaces_and_table_densities_use_shared_variants(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(
        styles,
        ".surface",
        {"background": "var(--color-surface-default)"},
    )
    assert_css_rule(
        styles,
        ".content-frame",
        {"width": "fit-content", "max-width": "100%"},
    )
    assert_css_rule(styles, ".surface--clipped", {"overflow": "hidden"})
    assert_css_rule(
        styles,
        ".section-heading",
        {"column-gap": "var(--space-2)"},
    )
    assert_css_rule(
        styles,
        ".section-index",
        {"flex": "0 0 auto", "white-space": "nowrap"},
    )

    for path in ["/units", "/skills", "/fireteams"]:
        status, _, body = request(app, path)
        assert status == 200
        assert b'class="surface surface--clipped content-frame' in body

    assert_css_rule(
        styles,
        ".surface--subtle",
        {"background": "var(--color-surface-subtle)"},
    )
    assert_css_rule(
        styles,
        ".surface--highlighted",
        {"background": "var(--color-surface-highlight)"},
    )
    assert_css_rule(
        styles,
        ".surface--raised",
        {"box-shadow": "var(--shadow-card)"},
    )
    assert_css_rule(
        styles,
        ".data-table--compact",
        {
            "--table-cell-size": "var(--font-size-sm)",
            "--table-heading-size": "var(--font-size-xs)",
        },
    )

    for path in ["/static/unit.js", "/static/skill.js", "/static/catalog-detail.js"]:
        status, _, body = request(app, path)
        assert status == 200
        assert b"data-table--compact" in body

    status, _, weapon_detail = request(app, "/static/catalog-detail.js")
    assert status == 200
    assert (
        b'card.className = "surface surface--clipped content-frame weapon-profile"'
        in weapon_detail
    )
    assert b"const profileTitle = profile.mode || profile.name || variant.name;" in weapon_detail
    assert b'data-table--compact data-table--profile weapon-statline' in weapon_detail
    assert b'class=\\"table-column--descriptor\\" scope=\\"col\\">Ammunition</th>' in weapon_detail
    assert b'class=\\"table-column--metric\\" scope=\\"col\\">PS</th>' in weapon_detail
    assert b'["PS", profile.damage, "metric"]' in weapon_detail
    assert b"<th>DAM</th>" not in weapon_detail
    assert b'title.className = "surface-titlebar surface-titlebar--subtle";' in weapon_detail
    assert b"headingText" not in weapon_detail
    assert b"variantTitle" not in weapon_detail
    assert b'profileHeading.textContent = "Profile";' in weapon_detail
    assert b'traitsHeading.textContent = "Traits";' in weapon_detail
    assert b"if (traitReferences.length)" in weapon_detail
    assert b"function weaponTraitLinks(traits)" in weapon_detail
    assert b"function canonicalTraitName(" not in weapon_detail
    assert b"function traitSlug(" not in weapon_detail
    assert b"function traitUsageSectionGroup(item)" in weapon_detail
    assert (
        b"title.textContent = catalogName[0].toUpperCase() + catalogName.slice(1);" in weapon_detail
    )
    assert b'title.className = "trait-catalog-heading";' in weapon_detail
    assert b"link.href = `/traits/${encodeURIComponent(trait.slug)}`;" in weapon_detail
    assert b".weapon-data-heading" in styles
    assert b'profileRow.className = "weapon-data-row"' in weapon_detail
    assert b'profileStats.className = "weapon-data-value"' in weapon_detail
    assert_css_rule(styles, ".weapon-data-row", {"display": "grid"})
    assert_css_rule(
        styles,
        ".weapon-data-value",
        {"border-left": "1px solid var(--color-border-subtle)"},
    )
    assert b"--color-surface-data-header: #fafbf8" in styles
    assert_css_rule(
        styles,
        "thead th",
        {"background": "var(--color-surface-data-header)"},
    )
    assert_css_rule(
        styles,
        ".weapon-variants, .weapon-variant, .weapon-profile",
        {"width": "100%"},
    )
    assert_css_rule(
        styles,
        ".weapon-profile .weapon-ranges",
        {"display": "table", "width": "100%", "table-layout": "auto"},
    )

    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b'generalProfile.className = "surface content-frame general-profile"' in body
    assert_css_rule(
        styles,
        ".unit-detail .general-profile .profile-title",
        {"background": "var(--color-surface-highlight)"},
    )

    status, _, fireteams = request(app, "/fireteams")
    assert status == 200
    assert b"surface surface--subtle surface--raised fireteam-reference" in fireteams
    assert b"surface surface--subtle surface--raised fireteam-chart-summary" in fireteams

    status, _, fireteam_js = request(app, "/static/fireteams.js")
    assert status == 200
    assert (
        b'article.className = "surface surface--subtle surface--raised fireteam-card";'
        in fireteam_js
    )

    status, _, rules_js = request(app, "/static/rules-reference.js")
    assert status == 200
    assert b'article.className = "surface surface--subtle detail-section";' in rules_js

    status, _, body = request(app, "/about")
    assert status == 200
    assert b"surface surface--highlighted about-callout" in body
    assert b"surface about-principles" in body
    assert b"<h3>Connectivity</h3>" in body
    assert b"<h3>Connected data</h3>" not in body
    assert b"surface surface--subtle about-disclosure" in body

    assert_css_rule(
        styles,
        ".usage-section-group",
        {"width": "min(760px, 100%)"},
    )
    assert b".usage-section-group table.data-table--compact" not in styles


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
    assert b"const routeId = item.slug || item.id;" in body
    assert b"link.href = `/${catalog}/${encodeURIComponent(routeId)}`" in body


def test_unit_details_frontend_presents_include_relationships(app: Callable) -> None:
    status, _, unit_js = request(app, "/static/unit.js")

    assert status == 200
    assert b"function includeTargetLink(target, anchorScope)" in unit_js
    assert b'{ value: "Includes", header: true' in unit_js
    assert b"loadout.loadout_payload_ids || []" in unit_js
    assert b"anchoredPayloads.has(payloadId)" in unit_js
    assert b'[army.id, ...(army.availability_flags || [])].join("-")' in unit_js
    assert b"details.open = true" in unit_js
    assert b"function compositeOptionTable(options, anchorScope)" in unit_js
    assert b'"Composite option", "PTS", "SWC"' in unit_js
    assert b"function compositeOptionOrderSummary(orders)" in unit_js
    assert b'section.append(subheading("Composite options"));' in unit_js


def test_unit_frontend_presents_army_relationships_and_declared_membership_filter(
    app: Callable,
) -> None:
    status, _, unit_js = request(app, "/static/unit.js")
    assert status == 200
    assert b"function renderArmyRelationships(unit, armies)" in unit_js
    assert b'heading("Army relationships")' in unit_js
    assert b'section.className = "detail-group army-relationships developer-only";' in unit_js
    assert b"link.href = `/units?army_id=${encodeURIComponent(identifier)}`;" in unit_js
    assert (
        b"link.href = `/units?declared_faction_id="
        b"${encodeURIComponent(membership.source_faction_id)}`;" in unit_js
    )
    assert b"broader source-declared faction membership separately" in unit_js
    assert b"this faction identity has no current Army list" in unit_js

    status, _, app_js = request(app, "/static/app.js")
    assert status == 200
    assert b'declaredFactionId = params.get("declared_faction_id") || ""' in app_js
    assert b'url.searchParams.set("declared_faction_id", state.declaredFactionId)' in app_js
    assert b"renderDeclaredMembershipContext(data)" in app_js
    assert b"broader than concrete current Army-list availability" in app_js

    status, _, api_js = request(app, "/static/api.js")
    assert status == 200
    assert b'params.set("declared_faction_id", declaredFactionId)' in api_js

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(styles, ".army-relationships", {"width": "min(760px, 100%)"})


def test_unit_details_frontend_presents_source_attributed_notes(app: Callable) -> None:
    status, _, unit_js = request(app, "/static/unit.js")

    assert status == 200
    assert b"function renderSourceNotes(unit, armies)" in unit_js
    assert b'heading("Source notes")' in unit_js
    assert b"it is not a rule for every profile shown for this Unit" in unit_js
    assert b'intro.className = "army-relationship-intro developer-only";' in unit_js
    assert b"const appliesToAllShownArmies = shownArmyIds.size > 0" in unit_js
    assert b"if (sourceNote.armies.length && !appliesToAllShownArmies)" in unit_js
    assert b"item.append(armyExplorerLink(army));" in unit_js


def test_unit_details_frontend_presents_selection_relationships(app: Callable) -> None:
    status, _, unit_js = request(app, "/static/unit.js")

    assert status == 200
    assert b"function renderSelectionRelationships(unit, armies)" in unit_js
    assert b'heading("Selection relationships")' in unit_js
    assert b'section.className = "detail-group selection-relationships developer-only";' in unit_js
    assert b'if (relation.family === "same-logical-cross-context-exclusive")' in unit_js
    assert b'else if (relation.family === "cross-logical-shared-cardinality")' in unit_js
    assert b'else if (relation.family === "single-logical-cardinality")' in unit_js
    assert b"appendUnitLinks(item, members);" in unit_js
    assert b"profileGroupLink(army, member.group_id)" in unit_js
    assert b"profileGroupLink(army, target.group_id)" in unit_js
    assert b"dependencyOptionLinks(army, target)" in unit_js
    assert b"Source parameters:" in unit_js
    assert b"InfinityDB does not validate complete Army Lists" in unit_js
    assert b"profilesHeading.id = groupAnchor" in unit_js
    assert b"if (!groupAnchored) loadoutsHeading.id = groupAnchor" in unit_js

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(styles, ".selection-relationships", {"width": "min(760px, 100%)"})
    assert_css_rule(
        styles,
        ".selection-source-parameters",
        {
            "color": "var(--color-text-secondary)",
            "font-size": "var(--font-size-sm)",
        },
    )


def test_unit_details_frontend_presents_peripheral_relationships(app: Callable) -> None:
    status, _, unit_js = request(app, "/static/unit.js")
    assert status == 200
    assert b"function appendPeripheralRows(rows, item, colSpan = null)" in unit_js
    assert b'profileHelpLabel("Peripherals", "peripheral")' in unit_js
    assert b'profileHelpLabel("Controller access", "peripheral")' in unit_js
    assert b"group.append(unitLink(target));" in unit_js
    assert b"function renderPeripheralRelationships(unit)" in unit_js
    assert b"const controllers = unit.peripheral_controllers || [];" in unit_js
    assert b"item.append(unitLink(access.controller));" in unit_js
    assert b"no fixed ownership is implied" in unit_js

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(styles, ".peripheral-relationships", {"width": "min(760px, 100%)"})
    assert_css_rule(styles, ".connected-unit-surface", {"padding": "14px 16px"})


@pytest.mark.full_assets
@pytest.mark.parametrize(
    "symbol",
    ["regular", "irregular", "impetuous", "tactical", "lieutenant"],
)
def test_order_symbols_are_served(app: Callable, symbol: str) -> None:
    status, headers, body = request(app, f"/static/orders/{symbol}.svg")
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body


@pytest.mark.full_assets
@pytest.mark.parametrize("symbol", ["peripheral", "hackable", "cube", "cube-2"])
def test_characteristic_symbols_are_served(app: Callable, symbol: str) -> None:
    status, headers, body = request(app, f"/static/characteristics/{symbol}.svg")
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body


def test_unit_details_frontend_renders_order_symbols_as_content(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"function profileTitle(profile, profileSymbols = null)" in body
    assert b"generalProfile.append(profileTitle(profile, profileSymbols), table(" in body
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
    assert b"characteristic.equipment_reference?.slug" in body
    assert b"href: `/equipment/${encodeURIComponent(slug)}`" in body
    assert b"symbol.src = `/static/${symbolCategories[symbolType]}/${symbolType}.svg`" in body
    assert b"symbol.title = symbolLabels[symbolType]" in body
    assert b'"profile-summary loadout-start"' in body


def test_distance_preference_script_is_served(app: Callable) -> None:
    status, headers, body = request(app, "/static/preferences.js")
    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert b"distanceunitchange" in body


def test_developer_cache_toggle_is_served(app: Callable) -> None:
    status, _, body = request(app, "/static/preferences.js")
    assert status == 200
    assert b"function initializeDisableCacheToggle()" in body
    assert b"function cacheBustedUrl(path)" in body
    assert b'document.documentElement.dataset.disableCache = "false";' in body

    status, _, body = request(app, "/units")
    assert status == 200
    assert b'id="disable-cache-toggle"' in body
    assert b"setting-row developer-only" in body


def test_skill_distance_display_uses_api_parameter_semantics(app: Callable) -> None:
    status, _, preferences = request(app, "/static/preferences.js")
    assert status == 200
    assert b"function formatSkillDistanceExtra(value, parameterSemantics = null)" in preferences
    assert b"parameterSemantics?.positive_sign" in preferences

    for asset in ("skill.js", "skill-extras.js", "unit.js"):
        status, _, body = request(app, f"/static/{asset}")
        assert status == 200
        assert b"parameter_semantics" in body
        assert b"Super-Jump" not in body
        assert b"Forward Deployment" not in body


def test_skill_extras_page_and_api_are_served(app: Callable) -> None:
    status, headers, body = request(app, "/skill-extras")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"skill-extras.js" in body

    status, _, script = request(app, "/static/skill-extras.js")
    assert status == 200
    assert b"unit.public_slug || unit.id" in script

    status, headers, body = request(app, "/api/skill-extras")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    assert json.loads(body) == {"items": []}


def test_traits_page_and_api_are_served(app: Callable) -> None:
    status, headers, body = request(app, "/traits")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"catalog-list.js" in body
    assert b'href="/traits" aria-current="page"' in body
    assert b"Traits catalog" in body

    status, headers, body = request(app, "/api/traits")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    assert json.loads(body) == {"items": []}

    status, headers, body = request(app, "/traits/suppressive-fire")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"catalog-detail.js" in body

    status, _, body = request(app, "/api/traits/suppressive-fire")
    assert status == 404
    assert json.loads(body)["error"] == "Trait not found"

    status, _, body = request(app, "/static/catalog-list.js")
    assert status == 200
    assert b'from "./api.js"' in body
    assert b"getCatalogItems(page, pageController.signal)" in body
    assert b"fetch(" not in body
    assert (
        b'["skills", "equipment", "weapons", "traits", "states", "hacking-programs"]'
        b".includes(page)" in body
    )
    assert b"const routeId = item.slug || item.id;" in body
    assert b"link.href = `/${page}/${encodeURIComponent(routeId)}`;" in body


def test_ammunition_and_label_pages_and_rules_backed_apis_are_served(
    app: Callable, tmp_path: Path
) -> None:
    for path, heading, current_href in (
        ("/ammunition", b"Ammunition catalog", b"/ammunition"),
        ("/labels", b"Labels catalog", b"/labels"),
    ):
        status, headers, body = request(app, path)
        assert status == 200
        assert headers["content-type"].startswith("text/html")
        assert heading in body
        assert b'href="' + current_href + b'" aria-current="page"' in body
        assert b"reference-catalog.js" in body

    for path in ("/api/ammunition", "/api/labels"):
        status, _, body = request(app, path)
        assert status == 200
        assert json.loads(body) == {"items": []}

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_path)

    status, _, body = request(rules_app, "/api/ammunition")
    assert status == 200
    ammunition = {item["slug"]: item for item in json.loads(body)["items"]}
    assert len(ammunition) == 11
    assert ammunition["ap"]["name"] == "Armor Piercing (AP) Ammunition"
    assert ammunition["shock"]["name"] == "Shock Ammunition"

    status, headers, body = request(rules_app, "/ammunition/shock")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"reference-detail.js" in body

    status, _, body = request(rules_app, "/api/ammunition/shock")
    assert status == 200
    shock = json.loads(body)
    assert shock["slug"] == "shock"
    assert shock["rules"][0]["id"] == "ammunition:shock"
    assert shock["rules"][0]["citations"][0]["source_id"] == "wiki-en-20260918-130233"

    status, _, body = request(rules_app, "/api/labels")
    assert status == 200
    labels = {item["slug"]: item for item in json.loads(body)["items"]}
    assert len(labels) == 24
    assert labels["hackable"]["name"] == "Hackable"

    status, _, body = request(rules_app, "/api/labels/non-reloadable")
    assert status == 200
    label = json.loads(body)
    assert label["name"] == "Non-Reloadable"
    reference = next(
        token for token in label["description_tokens"] if token["type"] == "reference"
    )
    assert reference["target"] == "state:unloaded"
    assert reference["public_reference"] == {"catalog": "states", "id": "unloaded"}

    status, _, body = request(rules_app, "/api/search", query="q=Shock")
    assert status == 200
    assert {
        (item["domain"], item["name"], item["href"])
        for item in json.loads(body)["items"]
    } >= {("Ammunition type", "Shock Ammunition", "/ammunition/shock")}

    status, _, body = request(rules_app, "/api/search", query="q=Hackable")
    assert status == 200
    assert {
        (item["domain"], item["name"], item["href"])
        for item in json.loads(body)["items"]
    } >= {("Label", "Hackable", "/labels/hackable")}

    status, _, script = request(rules_app, "/static/reference-detail.js")
    assert status == 200
    assert b'from "./maintained-text.js"' in script
    assert b"appendMaintainedText(" in script

    status, _, renderer = request(rules_app, "/static/rules-reference.js")
    assert status == 200
    assert b'element.href = `/labels/${encodeURIComponent(label.id)}`' in renderer

def test_hacking_program_pages_and_empty_api_are_served(app: Callable) -> None:
    status, headers, body = request(app, "/hacking-programs")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Hacking Program catalog" in body
    assert b'href="/hacking-programs" aria-current="page"' in body
    assert b'>Uses</th>' not in body

    status, _, body = request(app, "/api/hacking-programs")
    assert status == 200
    assert json.loads(body) == {"items": []}

    status, headers, body = request(app, "/hacking-programs/carbonite")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"hacking-program-detail.js" in body

    status, _, script = request(app, "/static/hacking-program-detail.js")
    assert status == 200
    assert b'detail-group rules-reference hacking-program-profile' in script
    assert b'from "./rules-reference.js"' in script
    assert (
        b"rulesReferenceArticle(rule, { leadingContent, headerContent, beforeRelations })"
        in script
    )
    assert b'detail-card hacking-program-profile-card' not in script
    assert b'from "./skill-categories.js"' in script
    assert b"skillCategoryBadge(category)" in script
    assert b"baselineDevicesGroup(program)" in script
    assert (
        b"[\"Targets\", program.targets?.length ? program.targets.join(\", \") : null, "
        b"\"descriptor\"]" in script
    )
    assert b"headerContent" in script
    assert b"beforeRelations" in script
    assert b"rulesReferenceSection" not in script
    assert b'"Entire Order"' not in script

    status, _, body = request(app, "/api/hacking-programs/carbonite")
    assert status == 404
    assert json.loads(body)["error"] == "Hacking Program not found"


def test_states_page_and_rules_backed_api_are_served(app: Callable, tmp_path: Path) -> None:
    status, headers, body = request(app, "/states")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"States catalog" in body
    assert b'href="/states" aria-current="page"' in body
    assert b'>Uses</th>' not in body

    status, _, body = request(app, "/api/states")
    assert status == 200
    assert json.loads(body) == {"items": []}

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_path)

    status, _, body = request(rules_app, "/api/states")
    assert status == 200
    states = {item["id"]: item for item in json.loads(body)["items"]}
    assert len(states) == 24
    assert states["unconscious"]["name"] == "Unconscious State"
    assert states["targeted"]["name"] == "Targeted State"

    status, headers, body = request(rules_app, "/states/unconscious")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"catalog-detail.js" in body

    status, _, body = request(rules_app, "/api/states/unconscious")
    assert status == 200
    state = json.loads(body)
    assert state["slug"] == "unconscious"
    assert {
        relation["record"]["name"]
        for relation in state["rules"][0]["display_relations"]
        if relation["type"] == "cancels-state" and relation["direction"] == "inbound"
    } == {"Doctor", "Engineer", "GizmoKit", "MediKit", "Regeneration"}
    doctor = next(
        relation["record"]
        for relation in state["rules"][0]["display_relations"]
        if relation["record"]["name"] == "Doctor"
    )
    assert doctor["public_reference"] == {"catalog": "skills", "id": "doctor"}

    status, _, body = request(rules_app, "/api/states/not-a-state")
    assert status == 404
    assert json.loads(body)["error"] == "State not found"


def test_cube_profile_characteristic_resolves_to_canonical_equipment(
    tmp_path: Path, app_database_template: Path
) -> None:
    database_path = tmp_path / "cube.db"
    shutil.copy2(app_database_template, database_path)
    with sqlite3.connect(database_path) as connection:
        logical_unit_id = connection.execute(
            "SELECT id FROM logical_units WHERE slug = ?", ("ranger-prototype",)
        ).fetchone()[0]
        profile_payload_id = connection.execute(
            "SELECT id FROM profile_payloads WHERE logical_unit_id = ? ORDER BY id LIMIT 1",
            (logical_unit_id,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO characteristics (id, name, source_defined) VALUES (?, ?, ?)",
            (999, "Cube", 1),
        )
        position = connection.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM profile_payload_characteristics "
            "WHERE profile_payload_id = ?",
            (profile_payload_id,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO profile_payload_characteristics "
            "(profile_payload_id, position, characteristic_id) VALUES (?, ?, ?)",
            (profile_payload_id, position, 999),
        )
    _refresh_published_content_checksum(database_path)

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(database_path, rules_path)

    status, _, body = request(rules_app, "/api/equipment")
    assert status == 200
    equipment = {item["slug"]: item for item in json.loads(body)["items"]}
    assert equipment["cube"]["name"] == "Cube"
    assert equipment["cube"]["use_count"] == 1
    assert equipment["cube-2"]["name"] == "Cube 2.0"
    assert equipment["cube-2"]["use_count"] == 0

    status, _, body = request(rules_app, "/api/equipment/cube")
    assert status == 200
    cube = json.loads(body)
    assert cube["id"] == "cube"
    assert cube["slug"] == "cube"
    assert cube["rules"][0]["id"] == "equipment:cube"
    assert [unit["slug"] for unit in cube["variants"][0]["units"]] == ["ranger-prototype"]

    status, _, body = request(rules_app, "/api/units", query="equipment_id=cube")
    assert status == 200
    filtered = json.loads(body)
    assert filtered["total"] == 1
    assert [item["slug"] for item in filtered["items"]] == ["ranger-prototype"]

    status, _, body = request(rules_app, "/api/units/ranger-prototype")
    assert status == 200
    unit = json.loads(body)
    references = [
        characteristic["equipment_reference"]
        for army in unit["armies"]
        for profile in army["profiles"]
        for characteristic in profile["characteristics"]
        if characteristic["name"] == "Cube"
    ]
    assert references
    assert references[0] == {"id": "cube", "slug": "cube", "name": "Cube"}


@pytest.mark.parametrize("catalog", ["skills", "equipment", "weapons"])
def test_reference_catalog_pages_and_apis_are_served(app: Callable, catalog: str) -> None:
    status, headers, body = request(app, f"/{catalog}")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"catalog-list.js" in body
    assert f'href="/{catalog}" aria-current="page"'.encode() in body
    assert b'class="table-column--metric" scope="col">Uses</th>' in body
    if catalog == "skills":
        assert b'class="table-column--descriptor" scope="col">Type(s)</th>' in body
    else:
        assert b'>Type(s)</th>' not in body
    assert b"Reference</th>" not in body

    status, headers, body = request(app, f"/api/{catalog}")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    expected = {
        "skills": {
            "id": 11,
            "name": "Stealth",
            "wiki": None,
            "source_ids": [11],
            "use_count": 1,
            "slug": "stealth",
            "categories": [
                {"id": "unclassified", "name": "Unclassified", "source": None, "page": None}
            ],
            "category": "Special Skills",
        },
        "equipment": {
            "id": 21,
            "name": "Medikit",
            "wiki": "https://infinitythewiki.com/Medikit",
            "source_ids": [21],
            "use_count": 1,
            "slug": "medikit",
        },
        "weapons": {
            "id": 31,
            "name": "Combi Rifle",
            "slug": "combi-rifle",
            "type": None,
            "category": "Rifles",
            "ammunition": None,
            "properties": None,
            "source_ids": [31],
            "use_count": 1,
        },
    }
    assert json.loads(body)["items"] == [expected[catalog]]


def test_global_search_routes_to_domain_specific_surfaces(app: Callable) -> None:
    status, headers, body = request(app, "/search?q=alpha")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Every database domain" in body
    assert b'action="/search" role="search"' in body
    assert b"search.js" in body

    status, _, body = request(app, "/api/search", query="q=alpha")
    assert status == 200
    items = json.loads(body)["items"]
    assert {item["domain"] for item in items} >= {"Army", "Unit"}
    assert {item["href"] for item in items} >= {
        "/units?army_id=alpha-company",
        "/units/ranger-prototype",
    }

    status, _, body = request(app, "/api/search", query="q=combi")
    assert status == 200
    assert {
        "domain": "Weapon",
        "name": "Combi Rifle",
        "href": "/weapons/combi-rifle",
    } in json.loads(body)["items"]

    status, _, body = request(app, "/api/search", query="q=&unexpected=value")
    assert status == 400
    assert json.loads(body)["error"] == "Unknown query parameter: unexpected"

    status, _, body = request(app, "/api/search", query="q=alpha&q=beta")
    assert status == 400
    assert json.loads(body)["error"] == "Provide q exactly once"


def test_glossary_projects_canonical_rules_and_embedded_attributes(
    app: Callable, tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_database_path=rules_path)

    status, headers, body = request(rules_app, "/glossary")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Canonical terminology" in body
    assert b"glossary.js" in body
    assert b'href="/glossary" aria-current="page"' in body

    status, _, body = request(rules_app, "/api/glossary")
    assert status == 200
    items = json.loads(body)["items"]
    movement = next(item for item in items if item["id"] == "attribute:mov")
    assert movement == {
        "id": "attribute:mov",
        "kind": "attribute",
        "domain": "Attribute",
        "domain_slug": "attributes",
        "name": "Movement (MOV)",
        "description": (
            "Movement (MOV) is the distance a Trooper can move in an Order. It normally "
            "has separate first-move and second-move values; a dash means the Trooper "
            "is stationary."
        ),
        "aliases": [],
        "href": "/glossary#attribute-mov",
        "embedded": True,
        "description_tokens": [
            {
                "type": "text",
                "text": (
                    "Movement (MOV) is the distance a Trooper can move in an Order. It "
                    "normally has separate first-move and second-move values; a dash "
                    "means the Trooper is stationary."
                ),
            }
        ],
    }
    camouflage = next(item for item in items if item["id"] == "skill:camouflage")
    assert camouflage["href"] == "/skills/camouflage"
    assert camouflage["embedded"] is False
    assert any(
        token.get("target") == "state:camouflaged"
        and token.get("public_reference") == {
            "catalog": "states",
            "id": "camouflaged",
        }
        for token in camouflage["description_tokens"]
        if token.get("type") == "reference"
    )

    status, _, body = request(rules_app, "/api/search", query="q=movement")
    assert status == 200
    assert {
        "domain": "Attribute",
        "name": "Movement (MOV)",
        "href": "/glossary#attribute-mov",
    } in json.loads(body)["items"]


def test_catalog_api_exposes_all_accepted_numeric_source_ids(app: Callable) -> None:
    with sqlite3.connect(app.database.path) as connection:
        connection.execute(
            "INSERT INTO application_catalog_sources "
            "(catalog, application_item_id, source_item_id, source_name, has_metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            ("equipment", 21, 244, "Medikit: Legacy Variant", 0),
        )
        connection.commit()

    status, _, body = request(app, "/api/equipment")

    assert status == 200
    item = json.loads(body)["items"][0]
    assert item["id"] == 21
    assert item["slug"] == "medikit"
    assert item["source_ids"] == [21, 244]


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
        "slug": "stealth",
        "categories": [
            {"id": "unclassified", "name": "Unclassified", "source": None, "page": None}
        ],
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
                        "public_slug": "ranger-prototype",
                        "main_army_id": None,
                        "main_army_name": None,
                        "main_faction": None,
                        "display_army_id": None,
                        "display_army_name": None,
                        "display_faction": None,
                        "source_ids": [1],
                        "army_ids": [101, 201],
                        "armies": [
                            {
                                "id": 101,
                                "name": "Zulu Company",
                                "public_slug": "zulu-company",
                                "symbol_path": "armies/panoceania/101-panoceania.svg",
                            },
                            {
                                "id": 201,
                                "name": "Alpha Company",
                                "public_slug": "alpha-company",
                                "symbol_path": "armies/yu-jing/201-yu-jing.svg",
                            },
                        ],
                    }
                ],
            }
        ],
    }

    status, headers, slug_page = request(app, "/skills/stealth")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"skill.js" in slug_page

    status, headers, slug_body = request(app, "/api/skills/stealth")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    assert json.loads(slug_body) == skill

    status, _, body = request(app, "/api/skills/not-a-skill")
    assert status == 404
    assert json.loads(body)["error"] == "Skill not found"

    status, _, body = request(app, "/api/units")
    assert status == 200
    unit = next(item for item in json.loads(body)["items"] if item["id"] == 1)
    assert skill["variants"][0]["units"] == [unit]

    status, _, body = request(app, "/api/skills/999")
    assert status == 404
    assert json.loads(body)["error"] == "Skill not found"


def test_unit_api_adds_training_to_order_occurrences_only_when_rules_exist(
    app: Callable, tmp_path: Path
) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_path)

    status, _, body = request(rules_app, "/api/units/1")
    assert status == 200
    payload = json.loads(body)
    orders = [
        order
        for army in payload["armies"]
        for loadout in army["loadouts"]
        for order in loadout["orders"]
    ]
    assert orders
    assert all(order["training_reference"]["id"] == "training:regular" for order in orders)
    assert all(order["training_reference"]["citations"][0]["page"] == 11 for order in orders)
    assert not any(
        "training_reference" in profile
        for army in payload["armies"]
        for profile in army["profiles"]
    )

    status, _, body = request(app, "/api/units/1")
    assert status == 200
    assert all(
        "training_reference" not in order
        for army in json.loads(body)["armies"]
        for loadout in army["loadouts"]
        for order in loadout["orders"]
    )


def test_unit_profile_help_links_are_rendered_from_rules_data(app: Callable) -> None:
    status, _, unit_js = request(app, "/static/unit.js")
    assert status == 200
    assert b"getUnitProfileHelp" in unit_js
    assert b'"Profile notation"' in unit_js
    assert b'profileHelpLabel("Type", "troop-type")' in unit_js
    assert b'profileHelpLabel("Classification", "classification")' in unit_js
    assert b'profileHelpLabel("Peripherals", "peripheral")' in unit_js
    assert b'"training-orders"' in unit_js

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(
        styles,
        ".profile-help-grid",
        {"display": "grid", "grid-template-columns": "repeat(2, minmax(0, 1fr))"},
    )
    assert_css_rule(
        styles,
        ".profile-help-link",
        {"text-decoration-style": "dotted"},
    )


def test_unit_page_hides_textual_training_rows(app: Callable) -> None:
    status, _, body = request(app, "/static/unit.js")
    assert status == 200
    assert b"training_reference" not in body
    assert b"Training rules" not in body


def test_trait_apis_compose_army_usage_with_curated_rules(app: Callable, tmp_path: Path) -> None:
    with sqlite3.connect(app.database.path) as connection:
        connection.execute(
            "INSERT INTO metadata_weapons (position, id, type, name, properties) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, 31, "BS", "Combi Rifle", json.dumps(["Continous Damage", "Disposable (2)"])),
        )
        connection.commit()
    _refresh_published_content_checksum(app.database.path)

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_path)

    status, _, body = request(rules_app, "/api/traits")
    assert status == 200
    traits = {item["id"]: item for item in json.loads(body)["items"]}
    assert traits["continuous-damage"]["slug"] == "continuous-damage"
    assert traits["continuous-damage"]["name"] == "Continuous Damage"
    assert traits["disposable-x"]["slug"] == "disposable-x"
    assert traits["disposable-x"]["name"] == "Disposable (X)"

    status, _, body = request(rules_app, "/api/weapons/31")
    assert status == 200
    profile = json.loads(body)["profiles"][0]
    assert profile["traits"] == ["Continous Damage", "Disposable (2)"]
    assert profile["trait_references"] == [
        {
            "label": "Continous Damage",
            "name": "Continuous Damage",
            "slug": "continuous-damage",
        },
        {
            "label": "Disposable (2)",
            "name": "Disposable (X)",
            "slug": "disposable-x",
        },
    ]

    status, _, body = request(rules_app, "/api/traits/continuous-damage")
    assert status == 200
    payload = json.loads(body)
    assert payload["slug"] == "continuous-damage"
    assert payload["description"].startswith("After a failed Saving Roll")
    assert payload["variants"][0]["item_id"] == 31
    assert payload["variants"][0]["item_slug"] == "combi-rifle"
    assert payload["rules"][0]["citations"][0]["source_version"] == "N5.3 / oldid 4110"


def test_skill_api_adds_curated_rules_from_separate_database(app: Callable, tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    current = next(
        document
        for _, document in documents
        if document["collection"]["id"] == "n5-core-v5.3"
    )
    hacking_programs = next(
        item
        for item in documents
        if item[1]["collection"]["id"] == "n5-hacking-programs-v5.3"
    )
    document = copy.deepcopy(current)
    source_skill = next(record for record in document["records"] if record["kind"] == "skill")
    skill_record = copy.deepcopy(source_skill)
    skill_record["id"] = "skill:test-stealth-fixture"
    skill_record["name"] = "Test Stealth Fixture"
    skill_record["armyLinks"] = [{"entity": "skill", "id": 11}]
    skill_record["relations"] = []
    document["records"].append(skill_record)
    declaration = next(
        record
        for record in document["records"]
        if record["id"] == "declaration-category:automatic:p87"
    )
    declaration["armyLinks"].append({"entity": "skill", "id": 11})
    rules_path = tmp_path / "rules.db"
    export_rules_database(
        [(root / "curated.json", document), hacking_programs], rules_path
    )
    rules_app = create_app(app.database.path, rules_path)

    status, _, body = request(rules_app, "/api/skills/11")

    assert status == 200
    payload = json.loads(body)
    assert payload["categories"] == [
        {
            "id": "automatic",
            "name": "Automatic",
            "source": "N5 Core Rules v5.3",
            "page": 87,
        }
    ]
    assert payload["rules"][0]["id"] == "skill:test-stealth-fixture"
    assert payload["rules"][0]["collection"]["id"] == "n5-core-v5.3"
    assert payload["rules"][0]["scope"] == {"game": "N5", "seasons": ["current"]}
    assert payload["rules"][0]["labels"][0]["name"] == "Optional"
    assert payload["rules"][0]["citations"][0]["page"] == 87

    status, _, body = request(rules_app, "/api/skills")
    assert status == 200
    stealth = next(item for item in json.loads(body)["items"] if item["id"] == 11)
    assert stealth["categories"] == [
        {
            "id": "automatic",
            "name": "Automatic",
            "source": "N5 Core Rules v5.3",
            "page": 87,
        }
    ]

    status, _, body = request(rules_app, "/api/skills/alert")
    assert status == 200
    alert = json.loads(body)
    assert alert["id"] == "alert"
    assert alert["category"] == "Common Skills"
    assert alert["categories"] == [
        {
            "id": "automatic",
            "name": "Automatic",
            "source": "Infinity Wiki snapshot (English) v20260918-130233",
            "page": None,
        }
    ]
    assert alert["variants"] == []
    assert [rule["id"] for rule in alert["rules"]] == ["skill:alert"]

    status, _, body = request(rules_app, "/api/skills/reload")
    assert status == 200
    reload = json.loads(body)
    assert [category["name"] for category in reload["categories"]] == [
        "Short Skill",
        "ARO",
    ]
    assert [skill_type["category_name"] for skill_type in reload["rules"][0]["skill_types"]] == [
        "Short Skill",
        "ARO",
    ]


def test_equipment_api_adds_curated_declaration_category(app: Callable, tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_path)

    status, _, body = request(rules_app, "/api/equipment/medikit")

    assert status == 200
    payload = json.loads(body)
    assert payload["categories"] == [
        {"name": "Short Skill", "source": "N5 Core Rules v5.3", "page": 124}
    ]
    assert payload["rules"][0]["declaration_categories"] == payload["categories"]

    status, _, body = request(rules_app, "/static/catalog-detail.js")
    assert status == 200
    assert b"const categories = (item.categories || [])" in body
    assert "if (categories) meta.append(` · ${categories}`);".encode() in body

    status, _, body = request(rules_app, "/static/rules-reference.js")
    assert status == 200
    assert b"rule.declaration_categories || []" in body
    assert b'className = "surface-titlebar surface-titlebar--ruled rules-card-titlebar"' in body


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

    status, _, body = request(app, "/api/visible-unit-ids?cache_bust=development")
    assert status == 200
    assert json.loads(body)["ids"] == visible_ids


@pytest.mark.parametrize(
    ("catalog", "item_id", "slug", "name"),
    [
        ("equipment", 21, "medikit", "Medikit"),
        ("weapons", 31, "combi-rifle", "Combi Rifle"),
    ],
)
def test_equipment_and_weapon_details_are_served(
    app: Callable,
    catalog: str,
    item_id: int,
    slug: str | None,
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
    assert payload["slug"] == slug
    assert payload["variants"][0]["units"][0]["id"] == 1

    if slug is not None:
        status, headers, body = request(app, f"/{catalog}/{slug}")
        assert status == 200
        assert headers["content-type"].startswith("text/html")
        assert b"catalog-detail.js" in body

        status, headers, slug_body = request(app, f"/api/{catalog}/{slug}")
        assert status == 200
        assert headers["content-type"].startswith("application/json")
        assert json.loads(slug_body) == payload


def test_equipment_details_frontend_renders_metadata_profiles(app: Callable) -> None:
    status, _, body = request(app, "/static/catalog-detail.js")

    assert status == 200
    assert b'catalog === "equipment" && item.profiles?.length' in body
    assert b"weaponVariants([{ id: item.id, name: item.name, profiles: item.profiles }])" in body
    assert b'"Equipment profile"' not in body
    assert b'link.target = "_blank"' in body
    assert b'link.rel = "noopener noreferrer"' in body


def test_catalog_detail_frontend_renders_typed_source_variant_labels(
    app: Callable,
) -> None:
    status, _, body = request(app, "/static/catalog-detail.js")

    assert status == 200
    assert b"function sourceVariantLabel(variant)" in body
    assert b'if (semantics.kind === "named") return semantics.label;' in body
    assert b'variant.rules?.length ? "Variant rules" : null' in body
    assert b'count.textContent = summaryParts.join(" \xc2\xb7 ");' in body


def test_skill_detail_frontend_flags_exact_variant_rules_before_expansion(
    app: Callable,
) -> None:
    status, _, body = request(app, "/static/skill.js")

    assert status == 200
    assert b'variant.rules?.length ? "Variant rules" : null' in body
    assert b'count.textContent = summaryParts.join(" \xc2\xb7 ");' in body


def test_skill_detail_frontend_renders_structured_reference_tables(
    app: Callable,
) -> None:
    status, _, body = request(app, "/static/skill.js")

    assert status == 200
    assert b"function structuredReferenceSection(reference)" in body
    assert b'"hacking-programs"' in body
    assert b'"martial-arts"' in body
    assert b'"random-chart"' in body
    assert b'"Hacking Programs"' not in body
    assert b"hackingDeviceLinks(row.devices)" in body


def test_catalog_usage_summaries_wrap_variant_context_on_narrow_layouts(
    app: Callable,
) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    assert_css_rule(
        styles,
        ".usage-section-group .army-profile-title",
        {"flex-wrap": "wrap"},
    )
    assert_css_rule(
        styles,
        ".usage-section-group .army-profile-title>h2",
        {"flex": "1 1 220px", "min-width": "0"},
    )
    assert_css_rule(
        styles,
        ".usage-section-group .army-profile-title>.section-index",
        {"margin-left": "auto", "text-align": "right"},
    )


def test_unit_explorer_intro_disables_desktop_break_at_tablet_widths(app: Callable) -> None:
    status, _, styles = request(app, "/static/styles.css")

    assert status == 200
    tablet_media = styles.index(b"@media (max-width: 920px)")
    mobile_media = styles.index(b"@media (max-width: 600px)")
    desktop_break = styles.index(b".desktop-break {", tablet_media, mobile_media)
    assert desktop_break > tablet_media
    assert b"display: none" in styles[desktop_break:mobile_media]


def test_skill_details_frontend_opens_wiki_links_in_a_new_tab(app: Callable) -> None:
    status, _, body = request(app, "/static/skill.js")

    assert status == 200
    assert b'link.target = "_blank"' in body
    assert b'link.rel = "noopener noreferrer"' in body


def test_maintained_text_tokens_resolve_links_distances_and_tooltips(
    app: Callable, tmp_path: Path
) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_path)

    status, _, body = request(rules_app, "/api/skills/super-jump")
    assert status == 200
    rule = json.loads(body)["rules"][0]
    reference = next(
        token for token in rule["summary_tokens"] if token["type"] == "reference"
    )
    assert reference == {
        "type": "reference",
        "target": "skill:jump",
        "label": "Jump",
        "public_reference": {"catalog": "skills", "id": "jump"},
        "preview_tokens": [
            {
                "type": "text",
                "text": "A Long Common Skill used to clear obstacles and move through the air.",
            }
        ],
    }
    distances = [
        token
        for token in rule["fact_tokens"]["effects"][1]
        if token["type"] == "distance"
    ]
    assert distances == [
        {"type": "distance", "centimeters": 10, "positive_sign": False},
        {"type": "distance", "centimeters": 5, "positive_sign": False},
    ]

    status, _, renderer = request(rules_app, "/static/maintained-text.js")
    assert status == 200
    assert b'from "./preferences.js"' in renderer
    assert b'node.className = "maintained-distance"' in renderer
    assert b'wrapper.className = "maintained-reference-wrap"' in renderer
    assert b'tooltip.role = "tooltip"' in renderer
    assert b'{ interactive: false }' in renderer
    assert b'link.setAttribute("aria-describedby", tooltip.id)' in renderer
    assert b'event.pointerType !== "touch"' in renderer
    assert b'follow: activeTouchReference === link' in renderer
    assert b'if (!pendingTouchReference.follow) openTouchPreview(link)' in renderer
    assert b'event.preventDefault()' in renderer
    assert b'openTouchPreview(link)' in renderer
    assert b'const viewportGutter = 12' in renderer
    assert b'wrapper.dataset.tooltipPlacement = "below"' in renderer
    assert b'--maintained-tooltip-shift-x' in renderer
    assert (
        b'link.addEventListener("pointerenter", () => positionReferenceTooltip(link))'
        in renderer
    )
    assert b'link.addEventListener("focus", () => positionReferenceTooltip(link))' in renderer
    assert b'document.addEventListener("click", (event) =>' in renderer
    assert b'document.addEventListener("infinity:beforenavigation", closeTouchPreview)' in renderer
    assert b'window.addEventListener("resize", () =>' in renderer
    assert b'window.addEventListener("scroll", () =>' in renderer
    assert b'window.addEventListener("distanceunitchange", refreshDistances)' in renderer

    status, _, styles = request(rules_app, "/static/styles.css")
    assert status == 200
    assert b".maintained-reference-tooltip" in styles
    assert b".maintained-reference-wrap:focus-within .maintained-reference-tooltip" in styles
    assert b'.maintained-reference-wrap[data-touch-open="true"]' in styles
    assert b'.maintained-reference-wrap[data-tooltip-placement="below"]' in styles
    assert b'calc(100vw - 24px)' in styles
    assert b'--maintained-tooltip-shift-x' in styles
    assert b"@media (hover: hover)" in styles


def test_detail_frontends_share_curated_rules_reference_renderer(app: Callable) -> None:
    for asset in ("skill.js", "catalog-detail.js"):
        status, _, body = request(app, f"/static/{asset}")
        assert status == 200
        assert b"rulesReferenceSection" in body
        assert b'from "./rules-reference.js"' in body

    status, _, body = request(app, "/static/rules-reference.js")
    assert status == 200
    assert b"Rules reference" in body
    assert b"rule.collection?.title" in body
    assert b"rule.supplements || []" in body
    assert b"Additional rules context" in body
    assert b'["requirements", "Requirements"]' in body
    assert b'["effects", "Effects"]' in body
    assert b'["restrictions", "Restrictions"]' in body
    assert body.index(b'["requirements", "Requirements"]') < body.index(b'["effects", "Effects"]')
    assert body.index(
        b"appendMaintainedText(summary, rule.summary_tokens, rule.summary)"
    ) < body.index(b"const applicability = applicabilityText(rule)")
    assert b"detail-fact-heading" in body
    assert b'heading.textContent = "Related rules"' in body
    assert b"const presentation = relation.presentation;" in body
    assert b"const reference = record.public_reference;" in body
    assert b"if (!reference?.catalog || !reference?.id) return null;" in body
    assert b"return `/${reference.catalog}/${encodeURIComponent(reference.id)}`;" in body
    assert b"presentation?.group_id" in body
    assert b"presentation?.group_label" in body
    assert b"presentation?.group_order" in body
    assert b"presentation?.relation_order" in body
    assert b"left.presentation.relation_order - right.presentation.relation_order" in body
    assert body.index(b"left.label.localeCompare(right.label)") < body.index(
        b"left.record.name.localeCompare(right.record.name"
    )
    assert b"groupHeading.textContent = relationGroup.label" in body
    assert b"relationLabels" not in body
    assert b"relationGroupOrder" not in body
    assert b"Creates & enables" not in body
    assert b'"reduces-modifiers-from"' not in body
    assert b"citation.source_url" in body
    assert b'link.target = "_blank"' in body
    assert b'link.rel = "noopener noreferrer"' in body


def test_072_detail_and_catalog_presentation_contract(app: Callable, tmp_path: Path) -> None:
    for path in (
        "/units/ranger-prototype",
        "/skills/11",
        "/equipment/21",
        "/weapons/31",
        "/traits/suppressive-fire",
    ):
        status, _, body = request(app, path)
        assert status == 200
        assert b"intro-copy developer-only" in body

    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_app = create_app(app.database.path, rules_path)
    status, _, body = request(rules_app, "/states/unconscious")
    assert status == 200
    assert b"intro-copy developer-only" in body

    status, _, unit_script = request(app, "/static/unit.js")
    assert status == 200
    assert b"troopTypeLabel(profile.type)" in unit_script
    assert b"formatMovement(profile.move_1, profile.move_2, distanceUnit())" in unit_script

    status, _, presentation_script = request(app, "/static/unit-presentation.js")
    assert status == 200
    for code, label in (
        (b"LI", b"Light Infantry"),
        (b"MI", b"Medium Infantry"),
        (b"HI", b"Heavy Infantry"),
        (b"REM", b"Remote"),
        (b"TAG", b"Tactical Armored Gear"),
        (b"WB", b"Warband"),
        (b"SK", b"Skirmisher"),
        (b"VH", b"Vehicle"),
    ):
        assert code in presentation_script
        assert label in presentation_script
    assert b'join("-")}\\"`' in presentation_script
    assert b'`${values.join("-")} cm`' in presentation_script

    status, _, styles = request(app, "/static/styles.css")
    assert status == 200
    assert_css_rule(
        styles,
        ".profile-symbol-link",
        {"display": "inline-flex", "align-items": "center", "line-height": "0"},
    )
    assert_css_rule(
        styles,
        ".data-table--listing .table-column--primary",
        {"width": "100%"},
    )
    assert b"--font-family-brand: \"Audiowide\"" in styles
    assert b"--font-family-display: \"Oxanium\"" in styles
    assert b"--font-family-body: \"IBM Plex Sans\"" in styles
    assert b"--font-family-compact: \"IBM Plex Sans Condensed\"" in styles
    assert b"--font-family-mono: \"IBM Plex Mono\"" in styles
    assert_css_rule(styles, ".brand", {"font-family": "var(--font-family-brand)"})
    assert_css_rule(
        styles,
        "h1,\nh2,\nh3,\nh4,\nh5,\nh6",
        {"font-family": "var(--font-family-display)"},
    )
    assert_css_rule(styles, "table", {"font-family": "var(--font-family-compact)"})
    assert b"font-family: var(--font-family-body)" in styles
    assert b"font-family: var(--font-family-mono)" in styles
    assert b"--font-size-root: 93.75%" in styles
    assert b"font-size: var(--font-size-root)" in styles
    assert b"--font-size-xs: 0.733333rem" in styles
    assert b"--font-size-base: 1rem" in styles
    assert b"--font-size-title: clamp(2.266667rem, 3.5vw, 3.4rem)" in styles
    assert_css_rule(styles, ".intro-copy", {"font-size": "var(--font-size-base)"})
    stylesheet = styles.decode("utf-8")
    token_values = re.findall(r"--font-size-(?!root)[\w-]+:\s*([^;]+);", stylesheet)
    assert token_values
    assert all("px" not in value for value in token_values)
    assert all("rem" in value for value in token_values)
    font_sizes = re.findall(r"(?m)^\s*font-size:\s*([^;]+);", stylesheet)
    assert font_sizes
    assert all(value.startswith("var(") for value in font_sizes)
    font_shorthands = re.findall(r"(?m)^\s*font:\s*([^;]+);", stylesheet)
    assert all(
        value == "inherit" or value.startswith("var(--font-size-") for value in font_shorthands
    )
    for undersized in (
        b"font-size: 8px",
        b"font-size: 9px",
        b"font-size: 10px",
        b"--table-heading-size: 8px",
        b"--table-heading-size: 9px",
    ):
        assert undersized not in styles
    assert_css_rule(
        styles,
        "table",
        {"--table-heading-size": "var(--font-size-xs)"},
    )
    assert_css_rule(
        styles,
        ".data-table--compact",
        {
            "--table-heading-size": "var(--font-size-xs)",
            "--table-cell-size": "var(--font-size-sm)",
        },
    )


def test_skill_category_presentation_uses_shared_semantic_colors(app: Callable) -> None:
    status, _, body = request(app, "/static/catalog-list.js")
    assert status == 200
    assert b'from "./skill-categories.js"' in body
    assert b'const catalogColumnCount = elements.table.querySelectorAll("thead th").length;' in body
    assert b"categoryCell.colSpan = catalogColumnCount;" in body
    assert b'types.className = "skill-category-cell table-column--descriptor"' in body
    assert b"types.append(skillCategoryBadge(category))" in body

    status, _, body = request(app, "/static/rules-reference.js")
    assert status == 200
    assert b'from "./skill-categories.js"' in body
    assert b"skillCategoryBadge(category" in body

    status, _, skill_script = request(app, "/static/skill.js")
    assert status == 200
    assert b'from "./skill-categories.js"' in skill_script
    assert b"declarationCategoryBadges(row.declaration_categories)" in skill_script
    assert b'"Entire Order"' not in skill_script

    status, _, body = request(app, "/static/skill-categories.js")
    assert status == 200
    for token in (b"automatic", b"deployment", b"basic-short", b"short", b"long", b"aro"):
        assert token in body

    status, _, body = request(app, "/static/styles.css")
    assert status == 200
    assert b".skill-category-badge--automatic" in body
    assert b"var(--color-skill-category-automatic)" in body
    assert b".skill-category-badge--deployment" in body
    assert b"var(--color-skill-category-deployment)" in body
    assert b".skill-category-badge--basic-short" in body
    assert b"var(--color-skill-category-basic-short)" in body
    assert b".skill-category-badge--short" in body
    assert b"var(--color-skill-category-short)" in body
    assert b".skill-category-badge--long" in body
    assert b"var(--color-skill-category-long)" in body
    assert b".skill-category-badge--aro" in body
    assert b"var(--color-skill-category-aro)" in body
    assert b".rules-reference" in body
    assert b".hacking-program-profile-table" in body
    assert b".detail-card" not in body
    assert b".hacking-program-profile-card" not in body
    assert b".hacking-program-context-row" not in body
    assert b"margin-bottom: var(--space-2);" in body


@pytest.mark.full_assets
def test_unit_symbol_is_served(app: Callable) -> None:
    catalog = SymbolCatalog()
    for slug in [
        "fusiliers",
        "clipper-dronbot",
        "yojimbo-motorized-sword-for-hire",
        "blur-spec-ops",
        "next-wave-team-ops",
    ]:
        published = catalog.unit_path(slug)
        assert published is not None
        status, headers, body = request(app, f"/static/{published}")
        assert status == 200
        assert headers["content-type"] == "image/svg+xml"
        assert b"<svg" in body
    status, _, _ = request(app, "/static/units/unassigned/not-a-unit.svg")
    assert status == 404
    status, _, _ = request(app, "/static/unit-symbol-map.js")
    assert status == 404


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


def test_weapon_api_adds_curated_special_profile_when_rules_database_is_available(
    tmp_path: Path,
) -> None:
    unit = {
        "id": 1,
        "name": "Turret Carrier",
        "canonical": 101,
        "factions": [101],
        "profileGroups": [
            {
                "id": 1,
                "profiles": [{"id": 1, "weapons": [{"id": 226}]}],
                "options": [],
            }
        ],
    }
    document = {
        "version": "test",
        "units": [unit],
        "filters": {
            "weapons": [
                {"id": source_id, "name": name}
                for source_id, name in (
                    (209, "Armed Turret (Combi R.)"),
                    (215, "Armed Turret (Marksman R.)"),
                    (219, "Armed Turret (AP Rifle)"),
                    (222, "Armed Turret (Rifle)"),
                    (226, "Armed Turret"),
                    (228, "Armed Turret (E/Mitter)"),
                )
            ]
        },
        "reinforcements": None,
    }
    source = make_source("101-main.json", json.dumps(document).encode())
    assert source is not None
    normalized = normalize_master(merge_sources([source]))
    normalized["armyMetadata"] = {
        "sourceFile": "metadata.json",
        "sourceSha256": "test-metadata",
        "data": {"factions": []},
    }
    normalized["tables"]["metadata_weapons"] = [
        {
            "position": 1,
            "id": 226,
            "name": "Armed Turret",
            "mode": "Combi Rifle",
            "burst": "3",
            "damage": "7",
        }
    ]

    database_path = tmp_path / "infinity.db"
    rules_path = tmp_path / "rules.db"
    export_database(normalized, database_path)
    documents = load_curated_directory(Path(__file__).parents[1] / "data" / "curated" / "rules")
    export_rules_database(documents, rules_path)
    rules_app = create_app(database_path, rules_database_path=rules_path)

    status, _, body = request(rules_app, "/api/weapons/226")

    assert status == 200
    payload = json.loads(body)
    assert payload["special_profile"]["stats"] == [
        ["MOV", "--"],
        ["CC", "5"],
        ["BS", "10"],
        ["PH", "--"],
        ["WIP", "--"],
        ["ARM", "2"],
        ["BTS", "3"],
        ["STR", "1"],
        ["S", "2"],
    ]
    assert payload["special_profile"]["equipment"] == ["360º Visor"]
    assert payload["special_profile"]["skills"] == ["Total Reaction"]
    assert payload["special_profile"]["cc_weapon"] == "PARA CC Weapon (-3)"
    assert [record["id"] for record in payload["rules"]] == ["weapon:armed-turret"]


def test_explicit_rules_database_path_is_required(app: Callable, tmp_path: Path) -> None:
    missing = tmp_path / "missing-rules.db"
    with pytest.raises(ValueError, match="Rules database does not exist"):
        create_app(app.database.path, missing)

    invalid = tmp_path / "invalid-rules.db"
    invalid.write_text("not a SQLite database", encoding="utf-8")
    with pytest.raises(sqlite3.DatabaseError):
        create_app(app.database.path, invalid)


def test_adjacent_rules_database_remains_optional_for_local_use(
    app: Callable, tmp_path: Path
) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    database_path = local_root / "infinity.db"
    shutil.copy2(app.database.path, database_path)
    (local_root / "rules.db").write_text("not a SQLite database", encoding="utf-8")

    local_app = create_app(database_path)

    assert local_app.rules_database is None


def test_wsgi_uses_explicit_rules_database_from_environment(
    app: Callable, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "wsgi-rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated" / "rules"), rules_path)
    monkeypatch.setenv("INFINITY_DB_DATABASE", str(app.database.path))
    monkeypatch.setenv("INFINITY_DB_RULES_DATABASE", str(rules_path))
    sys.modules.pop("infinity_db.web.wsgi", None)

    module = importlib.import_module("infinity_db.web.wsgi")

    assert module.app.rules_database is not None
    assert module.app.rules_database.path == rules_path


def test_wsgi_rejects_missing_explicit_rules_database(
    app: Callable, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("INFINITY_DB_DATABASE", str(app.database.path))
    monkeypatch.setenv("INFINITY_DB_RULES_DATABASE", str(tmp_path / "missing-rules.db"))
    sys.modules.pop("infinity_db.web.wsgi", None)

    with pytest.raises(ValueError, match="Rules database does not exist"):
        importlib.import_module("infinity_db.web.wsgi")
