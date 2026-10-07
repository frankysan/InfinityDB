from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from infinity_db.web.app import Application, create_app


def request(
    app: Application,
    path: str,
    *,
    query: str = "",
) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(path)
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(
        PATH_INFO=parsed.path,
        QUERY_STRING=query or parsed.query,
        REQUEST_METHOD="GET",
    )
    response: dict[str, Any] = {}

    def start_response(
        status: str,
        headers: list[tuple[str, str]],
        exc_info: object | None = None,
    ) -> None:
        del exc_info
        response["status"] = int(status.split()[0])
        response["headers"] = {name.lower(): value for name, value in headers}

    result: Iterable[bytes] = app(environ, start_response)
    try:
        body = b"".join(result)
    finally:
        close = getattr(result, "close", None)
        if close is not None:
            close()
    return response["status"], response["headers"], body


@pytest.fixture(scope="module")
def scenario_app(tmp_path_factory: pytest.TempPathFactory) -> Application:
    root = Path(__file__).parents[1]
    rules_path = tmp_path_factory.mktemp("scenario-api") / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    return create_app(root / "data" / "generated" / "infinity.db", rules_path)


def test_scenario_list_api_exposes_current_publications_without_selecting_game_size(
    scenario_app: Application,
) -> None:
    status, headers, body = request(scenario_app, "/api/scenarios", query="cache_bust=1")

    assert status == 200
    assert headers["cache-control"] == "public, max-age=300, stale-while-revalidate=600"
    items = json.loads(body)["items"]
    assert [item["slug"] for item in items] == [
        "annihilation",
        "domination",
        "supplies",
        "firefight",
    ]
    assert all("selected_army_points" not in item for item in items)
    assert all(
        item["supported_army_points"] == [150, 200, 250, 300, 350, 400]
        for item in items
    )
    annihilation = items[0]
    lieutenant = next(
        token
        for token in annihilation["description_tokens"]
        if token["type"] == "reference"
    )
    assert lieutenant["type"] == "reference"
    assert lieutenant["target"] == "skill:lieutenant"
    assert lieutenant["label"] == "Lieutenant"
    assert lieutenant["public_reference"] == {"catalog": "skills", "id": "lieutenant"}
    assert lieutenant["preview_tokens"]


def test_scenario_detail_api_requires_and_projects_exact_army_points(
    scenario_app: Application,
) -> None:
    status, _, body = request(
        scenario_app,
        "/api/scenarios/domination",
        query="army_points=350&cache_bust=1",
    )

    assert status == 200
    item = json.loads(body)
    assert item["slug"] == "domination"
    assert item["selected_army_points"] == 350
    assert item["setup"]["game_size"]["armyPoints"] == 350
    assert item["setup"]["game_size"]["swc"] == 6
    assert item["placement"]["configuration_id"] == "300-400-points"
    assert {issue["id"] for issue in item["source_issues"]} == {"350-point-swc"}

    domination_rule = item["special_rules"][0]
    paragraph_reference = next(
        token
        for tokens in domination_rule["paragraph_tokens"]
        for token in tokens
        if token["type"] == "reference" and token["target"] == "skill:shasvastii"
    )
    assert paragraph_reference["public_reference"] == {
        "catalog": "skills",
        "id": "shasvastii",
    }
    normal_reference = next(
        token
        for tokens in domination_rule["paragraph_tokens"]
        for token in tokens
        if token["type"] == "reference" and token["target"] == "state:normal"
    )
    assert normal_reference["public_reference"] == {
        "catalog": "states",
        "id": "normal",
    }


def test_scenario_detail_api_projects_objective_and_source_issue_tokens(
    scenario_app: Application,
) -> None:
    status, _, body = request(
        scenario_app,
        "/api/scenarios/firefight",
        query="army_points=300",
    )
    assert status == 200
    firefight = json.loads(body)
    lieutenant_objective = next(
        objective
        for objective in firefight["objectives"]
        if objective["id"] == "killed-lieutenants"
    )
    lieutenant = next(
        token
        for token in lieutenant_objective["name_tokens"]
        if token["type"] == "reference"
    )
    assert lieutenant["target"] == "skill:lieutenant"
    assert lieutenant["label"] == "Lieutenants"
    assert lieutenant["public_reference"] == {"catalog": "skills", "id": "lieutenant"}

    status, _, body = request(
        scenario_app,
        "/api/scenarios/supplies",
        query="army_points=300",
    )
    assert status == 200
    supplies = json.loads(body)
    issue = supplies["source_issues"][0]
    distances = [
        token["centimeters"]
        for token in issue["description_tokens"]
        if token["type"] == "distance"
    ]
    assert distances == [20, 30, 20]


@pytest.mark.parametrize(
    ("path", "query", "status", "message"),
    [
        (
            "/api/scenarios",
            "army_points=300",
            400,
            "Unknown query parameter: army_points",
        ),
        (
            "/api/scenarios/annihilation",
            "",
            400,
            "Provide army_points exactly once",
        ),
        (
            "/api/scenarios/annihilation",
            "army_points=300&army_points=350",
            400,
            "Provide army_points only once",
        ),
        (
            "/api/scenarios/annihilation",
            "army_points=abc",
            400,
            "army_points must be an integer between 1 and 10000",
        ),
        (
            "/api/scenarios/annihilation",
            "army_points=175",
            400,
            "This scenario does not support 175 Army Points. "
            "Supported values: 150, 200, 250, 300, 350, 400.",
        ),
        (
            "/api/scenarios/missing",
            "army_points=300",
            404,
            "Scenario not found",
        ),
    ],
)
def test_scenario_api_rejects_invalid_or_unknown_requests(
    scenario_app: Application,
    path: str,
    query: str,
    status: int,
    message: str,
) -> None:
    response_status, _, body = request(scenario_app, path, query=query)

    assert response_status == status
    assert json.loads(body) == {"error": message}


def test_scenario_api_failures_use_player_language(
    scenario_app: Application,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> list[dict[str, Any]]:
        raise sqlite3.DatabaseError("private database failure detail")

    monkeypatch.setattr(scenario_app.api.scenario_catalog, "list_scenarios", fail)

    status, _, body = request(scenario_app, "/api/scenarios")

    assert status == 503
    payload = json.loads(body)
    assert payload == {
        "error": "Scenario information is unavailable. Please try again."
    }
    assert b"private database failure detail" not in body


def test_scenario_api_routes_use_bounded_metric_labels(
    scenario_app: Application,
) -> None:
    status, _, _ = request(
        scenario_app,
        "/api/scenarios/domination",
        query="army_points=300",
    )
    assert status == 200

    status, _, metrics = request(scenario_app, "/internal/metrics")
    assert status == 200
    assert (
        b'infinitydb_http_requests_total{route="/api/scenarios/:id",status_class="2xx"}'
        in metrics
    )
    assert b"domination" not in metrics

    status, _, _ = request(
        scenario_app,
        "/api/scenarios/domination/map.svg",
        query="army_points=300",
    )
    assert status == 200

    status, _, metrics = request(scenario_app, "/internal/metrics")
    assert status == 200
    assert (
        b'infinitydb_http_requests_total{route="/api/scenarios/:id/map.svg",status_class="2xx"}'
        in metrics
    )
    assert b"domination" not in metrics


def test_browser_api_module_owns_scenario_endpoint_shapes(
    scenario_app: Application,
) -> None:
    status, _, script = request(scenario_app, "/static/api.js")

    assert status == 200
    assert b"export function getScenarios(signal)" in script
    assert b'return getJson("/api/scenarios", signal);' in script
    assert b"export function getScenario(scenarioId, armyPoints, signal)" in script
    assert b'new URLSearchParams({ army_points: String(armyPoints) })' in script
    assert (
        b'getJson(`/api/scenarios/${encodeURIComponent(scenarioId)}?${params}`, signal)'
        in script
    )

def test_scenario_browser_routes_are_published_with_shared_navigation(
    scenario_app: Application,
) -> None:
    status, _, body = request(scenario_app, "/scenarios")
    assert status == 200
    assert b"Current scenarios" in body
    assert b'href="/scenarios" aria-current="page"' in body
    assert b'src="/static/scenarios.js?' in body

    status, _, body = request(scenario_app, "/scenarios/domination")
    assert status == 200
    assert b"Choose Army Points" in body
    assert b'href="/scenarios" aria-current="page"' in body
    assert b'src="/static/scenario.js?' in body

    status, _, script = request(scenario_app, "/static/scenario.js")
    assert status == 200
    assert b'from "./share-state.js"' in script
    assert b'readShareState("scenario")' in script
    assert b'writeShareState(' in script
    assert b'"scenario",' in script
    assert b'army_points: String(value)' in script
    assert b'const { points: requested, source } = selectedArmyPointsFromUrl();' in script
    assert b'if (source !== "token") setSelectedArmyPoints(requested);' in script
    assert b'new URLSearchParams(window.location.search).get("army_points")' not in script
    assert b'/api/scenarios/${encodeURIComponent(item.slug)}/map.svg?' in script
    assert b'rulesCitationNode(citation)' in script
    assert b'badge.textContent = "uncertain"' in script
    assert b'wrapper.classList.add("developer-only")' in script

    status, _, stylesheet = request(scenario_app, "/static/page-overrides.css")
    assert status == 200
    assert b".scenario-rules > .detail-section {" in stylesheet
    assert b"padding: 16px;" in stylesheet


@pytest.mark.parametrize(
    "slug",
    ["annihilation", "domination", "supplies", "firefight"],
)
def test_scenario_map_api_renders_every_supported_configuration(
    scenario_app: Application,
    slug: str,
) -> None:
    status, _, body = request(scenario_app, "/api/scenarios")
    assert status == 200
    summary = next(item for item in json.loads(body)["items"] if item["slug"] == slug)

    for army_points in summary["supported_army_points"]:
        status, headers, svg = request(
            scenario_app,
            f"/api/scenarios/{slug}/map.svg",
            query=f"army_points={army_points}",
        )
        assert status == 200
        assert headers["content-type"].startswith("image/svg+xml")
        assert b'<svg xmlns="http://www.w3.org/2000/svg"' in svg


def test_scenario_map_api_renders_selected_maintained_geometry(
    scenario_app: Application,
) -> None:
    status, headers, body = request(
        scenario_app,
        "/api/scenarios/domination/map.svg",
        query="army_points=300",
    )

    assert status == 200
    assert headers["content-type"].startswith("image/svg+xml")
    assert b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"' in body
    assert b'data-unit="in"' in body
    assert b'id="quadrant-1-size" class="area-size"' in body
    assert "24″ × 12″".encode() in body

    status, _, body = request(
        scenario_app,
        "/api/scenarios/domination/map.svg",
        query="army_points=175",
    )
    assert status == 400
    assert json.loads(body)["error"].startswith("This scenario does not support 175 Army Points")
