from __future__ import annotations

import importlib
import json
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from infinity_db.specialist_filter import (
    _non_specialist_chain_variant,
    _qualifying_skills,
    candidate_unit_ids,
)
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


def test_specialist_candidates_ignore_non_specialist_chain_but_keep_other_skills() -> None:
    class FakeRules:
        def composed_record(self, identifier: str) -> dict:
            assert identifier == "rule:specialist-troops:standard"
            return {"facts": {"specialists": {
                "anyOfSkills": ["skill:doctor", "skill:chain-of-command"],
            }}}

    class FakeDatabase:
        def get_skill(self, identifier: str) -> dict:
            items = {
                "doctor": [
                    {"skill_name": "Doctor", "extras": [],
                     "units": [{"id": 1}, {"id": 4}]},
                ],
                "chain-of-command": [
                    {"skill_name": "Chain of Command", "extras": [],
                     "units": [{"id": 2}]},
                    {"skill_name": "Chain of Command", "extras": [
                        {"name": "Non Specialist"},
                    ], "units": [{"id": 3}, {"id": 4}]},
                ],
            }
            return {"variants": items[identifier]}

    candidates = candidate_unit_ids(
        cast(Any, FakeDatabase()), cast(Any, FakeRules()), "standard",
    )
    assert candidates == frozenset({1, 2, 4})


def test_specialist_candidate_variant_exclusion_is_per_skill() -> None:
    assert _non_specialist_chain_variant({
        "skill_name": "Chain of Command (Non Specialist)", "extras": [],
    })
    assert _non_specialist_chain_variant({
        "skill_name": "Chain of Command", "extras": [{"name": "Non Specialist"}],
    })
    assert not _non_specialist_chain_variant({
        "skill_name": "Chain of Command", "extras": [{"name": "Other"}],
    })


@pytest.mark.parametrize("context", ["standard", "domination", "supplies", "firefight"])
def test_specialist_filter_uses_published_qualifiers_and_unit_intersection(
    scenario_app: Application, context: str,
) -> None:
    assert scenario_app.rules_database is not None
    source_skills = _qualifying_skills(scenario_app.rules_database, context)
    assert "skill:doctor" in source_skills
    assert "skill:chain-of-command" in source_skills
    candidates = candidate_unit_ids(
        scenario_app.database, scenario_app.rules_database, context,
    )
    assert candidates
    assert all(type(identifier) is int for identifier in candidates)
    status, _, body = request(
        scenario_app, "/api/units",
        query=f"specialist={context}&limit=50&offset=0",
    )
    assert status == 200
    payload = json.loads(body)
    expected = scenario_app.database.list_units(
        _logical_unit_ids=candidates, limit=50,
    )
    assert payload["total"] == expected["total"]
    assert [item["id"] for item in payload["items"]] == [
        item["id"] for item in expected["items"]
    ]
    status, _, body = request(
        scenario_app, "/api/units",
        query=f"specialist={context}&search=doctor&limit=50",
    )
    assert status == 200
    narrowed = json.loads(body)
    assert narrowed["total"] <= payload["total"]


@pytest.mark.parametrize("value", ["invalid", "annihilation", "standard,domination"])
def test_specialist_filter_rejects_unsupported_contexts(
    scenario_app: Application, value: str,
) -> None:
    status, _, body = request(
        scenario_app, "/api/units", query=f"specialist={value}",
    )
    assert status == 400
    assert "Specialist" in json.loads(body)["error"]


def test_scenario_list_api_exposes_current_publications_without_selecting_game_size(
    scenario_app: Application,
) -> None:
    status, headers, body = request(scenario_app, "/api/scenarios", query="cache_bust=1")

    assert status == 200
    assert headers["cache-control"] == "public, max-age=300, stale-while-revalidate=600"
    payload = json.loads(body)
    assert payload["collections"] == [
        {"id": "n5-core", "revision": "5.3", "title": "N5 Core Scenarios", "scenario_count": 4},
        {
            "id": "its-18", "revision": "2026.09.01",
            "title": "ITS Season 18: Overheat", "scenario_count": 1,
        },
    ]
    items = payload["items"]
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


def test_domination_review_scoring_specialists_and_console_skill_reach_api(
    scenario_app: Application,
) -> None:
    """N5.3 pp. 151-152: publish scoring and conditional Console ownership."""
    status, _, body = request(
        scenario_app, "/api/scenarios/domination", query="army_points=350"
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["selected_army_points"] == 350
    assert payload["setup"]["game_size"]["swc"] == 6
    assert payload["setup"]["game_size"]["minimumVictoryPoints"] == 88
    assert len(payload["objectives"]) == 2
    quadrants, consoles = payload["objectives"]
    assert (quadrants["timing"], quadrants["aggregation"]) == (
        "end-of-round", "exclusive",
    )
    assert (quadrants["maximumPoints"], quadrants["maximumPointsPerRound"]) == (6, 2)
    assert [
        (award["objectivePoints"], award["condition"]["comparison"])
        for award in quadrants["awards"]
    ] == [(1, "equal"), (2, "greater")]
    assert quadrants["awards"][0]["condition"]["minimum"] == 1
    assert (consoles["timing"], consoles["aggregation"], consoles["maximumPoints"]) == (
        "end-of-game", "cumulative", 4,
    )
    assert len(consoles["awards"]) == 1
    assert consoles["awards"][0]["condition"]["status"] == "hacked"
    assert len(consoles["awards"][0]["condition"]["elementIds"]) == 4
    assert [rule["definitionId"] for rule in payload["special_rules"]] == [
        "rule:scenario:dominate-quadrants",
        "rule:scenario:consoles",
        "rule:specialist-troops:standard",
    ]
    paragraphs = " ".join(payload["special_rules"][0]["paragraphs"])
    assert "Shasvastii-Embryo" in paragraphs
    assert "more than half" in paragraphs
    assert len(payload["skills"]) == 1
    skill = payload["skills"][0]
    assert skill["id"] == "skill:hack-consoles"
    assert "Silhouette contact" in " ".join(skill["facts"]["requirements"])
    skill_effects = " ".join(skill["facts"]["effects"])
    assert "Only the most recent player" in skill_effects
    assert "+3 MOD" in skill_effects
    assert "failed attempt may be repeated" in skill_effects
    assert payload["end_conditions"][0]["condition"]["rounds"] == 3
    assert payload["end_conditions"][1]["checkAt"] == "tactical-phase"
    assert payload["end_conditions"][1]["finishAt"] == "end-of-player-turn"
    assert len(payload["source_issues"]) == 1
    issue = payload["source_issues"][0]
    assert issue["status"] == "needs-verification"
    assert "Wiki Domination revision 3264" in issue["description"]
    assert "Spanish N5.3 Domination chart" in issue["description"]
    assert "official language editions" in issue["description"]


def test_firefight_review_scoring_and_overlays_reach_api(
    scenario_app: Application,
) -> None:
    """Firefight mission rules remain scoped, linked and correctly projected."""
    status, _, body = request(
        scenario_app, "/api/scenarios/firefight", query="army_points=350"
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["setup"]["game_size"]["swc"] == 7
    assert payload["selected_army_points"] == 350
    assert [
        (obj["id"], obj["maximumPoints"], obj["awards"][0]["condition"]["metric"])
        for obj in payload["objectives"]
    ] == [
        ("surviving-specialists", 2, "surviving-specialist-troops"),
        ("killed-specialists", 1, "enemy-specialist-troops-killed"),
        ("killed-lieutenants", 3, "enemy-lieutenants-killed"),
        ("killed-army-points", 4, "enemy-army-points-killed"),
    ]
    assert all(
        obj["timing"] == "end-of-game"
        and obj["aggregation"] == "exclusive"
        and obj["awards"][0]["condition"]["comparison"] == "greater"
        for obj in payload["objectives"]
    )
    assert [rule["definitionId"] for rule in payload["special_rules"]] == [
        "rule:scenario:killing",
        "rule:scenario:reinforced-tactical-link",
        "rule:scenario:designated-landing-area",
        "rule:specialist-troops:standard",
    ]
    tactical = " ".join(payload["special_rules"][1]["paragraphs"])
    landing = " ".join(payload["special_rules"][2]["paragraphs"])
    assert "always Open Information" in tactical
    assert "without spending an Order" in tactical
    assert "+3 MOD" in landing
    assert "cumulative" in landing
    assert "enemy Deployment Zone" in landing
    assert payload["end_conditions"][0]["condition"]["rounds"] == 3
    assert payload["end_conditions"][1]["checkAt"] == "tactical-phase"
    assert payload["end_conditions"][1]["finishAt"] == "end-of-player-turn"
    assert payload["source_issues"] == []


@pytest.mark.parametrize(
    ("army_points", "swc", "minimum_vp", "configuration_id"),
    [
        (150, 3, 38, "150-points"),
        (200, 4, 50, "200-250-points"),
        (250, 5, 63, "200-250-points"),
        (300, 6, 75, "300-400-points"),
        (350, 7, 88, "300-400-points"),
        (400, 8, 100, "300-400-points"),
    ],
)
def test_supplies_review_scoring_and_pickup_reach_api(
    scenario_app: Application,
    army_points: int,
    swc: int,
    minimum_vp: int,
    configuration_id: str,
) -> None:
    """N5.3 pp. 153-154: all six public mission configurations and effects."""
    status, _, body = request(
        scenario_app, "/api/scenarios/supplies", query=f"army_points={army_points}"
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["selected_army_points"] == army_points
    assert payload["setup"]["game_size"]["swc"] == swc
    assert payload["setup"]["game_size"]["minimumVictoryPoints"] == minimum_vp
    assert payload["placement"]["configuration_id"] == configuration_id
    assert [
        (obj["id"], obj["maximumPoints"], obj["aggregation"])
        for obj in payload["objectives"]
    ] == [
        ("controlled-boxes", 6, "cumulative"),
        ("more-boxes", 2, "exclusive"),
        ("all-boxes", 2, "exclusive"),
    ]
    conditions = [obj["awards"][0]["condition"] for obj in payload["objectives"]]
    assert all(obj["timing"] == "end-of-game" for obj in payload["objectives"])
    assert all(obj["awards"][0]["objectivePoints"] == 2 for obj in payload["objectives"])
    assert [condition["status"] for condition in conditions] == ["controlled"] * 3
    assert [condition["elementIds"] for condition in conditions] == [
        ["supply-box-left", "supply-box-center", "supply-box-right"],
    ] * 3
    assert (conditions[1]["comparison"], conditions[2]["comparison"]) == (
        "greater", "all",
    )
    assert [rule["definitionId"] for rule in payload["special_rules"]] == [
        "rule:scenario:supply-boxes",
        "rule:scenario:carrying-supply-boxes",
        "rule:scenario:controlling-supply-boxes",
        "rule:specialist-troops:standard",
    ]
    assert len(payload["skills"]) == 1
    pickup = payload["skills"][0]
    assert pickup["id"] == "skill:pick-up-supply-boxes"
    pickup_requirements = " ".join(pickup["facts"]["requirements"])
    assert "not being carried by a Model" in pickup_requirements
    assert "any Model classified as Null" in pickup_requirements
    assert "an allied Model in [[state:normal|Normal]]" in pickup_requirements
    assert "without making a Roll" in " ".join(pickup["facts"]["effects"])
    control = " ".join(payload["special_rules"][2]["paragraphs"])
    assert "A Marker cannot control" in control
    assert "not be classified as Null" in control
    assert "any enemy Model" in control
    assert payload["end_conditions"][0]["condition"]["rounds"] == 3
    assert payload["end_conditions"][1]["checkAt"] == "tactical-phase"
    assert payload["end_conditions"][1]["finishAt"] == "end-of-player-turn"
    assert payload["source_issues"] == []


@pytest.mark.parametrize(
    ("slug", "source_chart_page", "swc_at_350", "minimum_vp"),
    [
        ("annihilation", 150, 7, False),
        ("domination", 151, 6, True),
        ("supplies", 153, 7, True),
        ("firefight", 155, 7, False),
    ],
)
@pytest.mark.parametrize(
    ("points", "standard_swc", "minimum_victory_points",
     "width", "height", "depth", "configuration_id"),
    [
        (150, 3, 38, 24, 32, 8, "150-points"),
        (200, 4, 50, 32, 48, 12, "200-250-points"),
        (250, 5, 63, 32, 48, 12, "200-250-points"),
        (300, 6, 75, 48, 48, 12, "300-400-points"),
        (350, 7, 88, 48, 48, 12, "300-400-points"),
        (400, 8, 100, 48, 48, 12, "300-400-points"),
    ],
)
def test_core_scenario_source_chart_rows_reach_public_api_at_every_size(
    scenario_app: Application,
    slug: str,
    source_chart_page: int,
    swc_at_350: int,
    minimum_vp: bool,
    points: int,
    standard_swc: int,
    minimum_victory_points: int,
    width: int,
    height: int,
    depth: int,
    configuration_id: str,
) -> None:
    """The 24 N5.3 chart selections survive curated DB, API and map projection."""
    status, _, body = request(
        scenario_app, f"/api/scenarios/{slug}", query=f"army_points={points}"
    )
    assert status == 200
    item = json.loads(body)
    assert item["slug"] == slug
    assert item["selected_army_points"] == points
    assert item["publication"]["revision"] == "5.3"
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf"
        and citation["page"] == source_chart_page
        for citation in item["citations"]
    )
    size = item["setup"]["game_size"]
    assert size["armyPoints"] == points
    assert size["swc"] == (swc_at_350 if points == 350 else standard_swc)
    assert size["configurationId"] == configuration_id
    if minimum_vp:
        assert size["minimumVictoryPoints"] == minimum_victory_points
    else:
        assert "minimumVictoryPoints" not in size
    assert item["placement"]["configuration_id"] == configuration_id
    geometry = item["placement"]["geometry"]
    assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
    deployment = next(
        element for element in geometry["elements"]
        if element["id"] == "deployment-a"
    )
    assert deployment["y2"] == depth
    assert all(
        award["armyPoints"] == [points]
        for objective in item["objectives"]
        for award in objective["awards"]
    )
    if slug == "domination" and points == 350:
        assert {issue["id"] for issue in item["source_issues"]} == {
            "350-point-swc",
        }
    elif slug == "annihilation" and points == 350:
        assert {issue["id"] for issue in item["source_issues"]} == {
            "350-point-survival-bands",
        }
    else:
        assert not item["source_issues"]


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
    assert supplies["source_issues"] == []

    status, _, body = request(
        scenario_app,
        "/api/scenarios/annihilation",
        query="army_points=350",
    )
    assert status == 200
    annihilation = json.loads(body)
    issue = annihilation["source_issues"][0]
    assert issue["status"] == "reviewed-resolution"
    assert "85–175" in issue["description"] and "more than 270" in issue["description"]


def test_annihilation_350_point_review_reaches_public_api(scenario_app: Application) -> None:
    """N5.3 pp. 149-150: verified source interpretation remains visible to players."""
    status, _, body = request(
        scenario_app, "/api/scenarios/annihilation", query="army_points=350"
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["selected_army_points"] == 350
    assert payload["setup"]["game_size"]["swc"] == 7
    assert len(payload["objectives"]) == 3
    for index, metric in enumerate(("enemy-army-points-killed", "surviving-victory-points")):
        objective = payload["objectives"][index]
        assert objective["timing"] == "end-of-game"
        assert objective["aggregation"] == "exclusive"
        assert objective["maximumPoints"] == 4
        assert [
            (award["objectivePoints"], award["condition"]["minimum"],
             award["condition"]["maximum"])
            for award in objective["awards"]
        ] == [(1, 85, 175), (3, 176, 270), (4, 271, None)]
        assert all(award["condition"]["metric"] == metric for award in objective["awards"])
    lieutenant = payload["objectives"][2]["awards"][0]
    assert lieutenant["objectivePoints"] == 2
    assert lieutenant["condition"]["kind"] == "reviewed-prose"
    assert any(
        token["target"] == "skill:lieutenant"
        for token in lieutenant["condition"]["text_tokens"]
        if token["type"] == "reference"
    )
    assert payload["special_rules"][0]["definitionId"] == "rule:scenario:killing"
    assert any(
        "never deployed" in paragraph
        for paragraph in payload["special_rules"][0]["paragraphs"]
    )
    assert [
        (end["id"], end["checkAt"], end["finishAt"])
        for end in payload["end_conditions"]
    ] == [
        ("round-limit", "end-of-round", "end-of-round"),
        ("all-troopers-null", "tactical-phase", "end-of-player-turn"),
    ]
    assert len(payload["source_issues"]) == 1
    assert payload["source_issues"][0]["id"] == "350-point-survival-bands"
    assert payload["source_issues"][0]["status"] == "reviewed-resolution"


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
    def fail(
        *, collection: str | None = None, revision: str | None = None
    ) -> list[dict[str, Any]]:
        del collection, revision
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
    assert (
        b"export function getScenarios(signal, { collection = \"\", revision = \"\" } = {})"
        in script
    )
    assert b'getJson(`/api/scenarios${query ? `?${query}` : ""}`, signal)' in script
    assert b"export function getScenario(scenarioId, armyPoints, signal, " in script
    assert b'new URLSearchParams({ army_points: String(armyPoints) })' in script
    assert b'if (collection) params.set("collection", collection);' in script
    assert b'if (revision) params.set("revision", revision);' in script
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
    assert b'const DEFAULT_ARMY_POINTS = 300;' in script
    assert b'const { points: requested, source } = selectedArmyPointsFromUrl();' in script
    assert b'if (source !== "token") setSelectedArmyPoints(requested);' in script
    assert b'summary.supported_army_points.includes(DEFAULT_ARMY_POINTS)' in script
    assert b'setSelectedArmyPoints(DEFAULT_ARMY_POINTS);' in script
    assert b'rulesReferenceArticle(inclusion.rule, { includeApplicability: false })' in script
    assert b'rulesReferenceArticle(skill, { includeApplicability: false })' in script
    assert b'group.className = "scenario-rules rules-card-stack";' in script
    assert b'new URLSearchParams(window.location.search).get("army_points")' not in script
    assert b'/api/scenarios/${encodeURIComponent(item.slug)}/map.svg?' in script
    assert b'new DOMParser().parseFromString(markup, "image/svg+xml")' in script
    assert b'svg.querySelector("style")?.remove();' in script
    assert b'document.importNode(svg, true)' in script
    assert b'window.addEventListener("distanceunitchange", refreshScenarioDistances, {' in script
    assert b"signal: pageController.signal" in script
    assert b'[data-distance-inches]' in script
    assert b'[data-distance-size-inches]' in script
    assert b'url.searchParams.set("distance_unit", distanceUnit())' in script
    assert b'rulesCitationNode(citation)' in script
    assert b'issue.status === "reviewed-resolution"' in script
    assert b'badge.textContent = reviewed ? "reviewed" : "uncertain"' in script
    assert b'wrapper.classList.add("developer-only")' in script

    status, _, stylesheet = request(scenario_app, "/static/components.css")
    assert status == 200
    assert b".rules-card-stack>.detail-section {" in stylesheet
    assert b".rules-card-stack h3," in stylesheet
    assert b"padding: 16px;" in stylesheet


def test_scenario_browser_aborts_map_and_unit_listener_on_soft_navigation() -> None:
    node = shutil.which("node")
    if node is not None:
        command = [node]
    else:
        try:
            importlib.import_module("nodejs_wheel")
        except ImportError:
            pytest.skip("Node.js is unavailable for scenario browser lifecycle contract")
        command = [sys.executable, "-m", "nodejs_wheel"]
    root = Path(__file__).parents[1]
    completed = subprocess.run(
        [
            *command,
            str(root / "tests" / "scenario_lifecycle_harness.cjs"),
            str(root / "src" / "infinity_db" / "web" / "static" / "scenario.js"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "scenario navigation lifecycle: passed" in completed.stdout


def test_scenario_selection_ignores_stale_requests() -> None:
    node = shutil.which("node")
    if node is not None:
        command = [node]
    else:
        try:
            importlib.import_module("nodejs_wheel")
        except ImportError:
            pytest.skip("Node.js is unavailable for scenario selection regression")
        command = [sys.executable, "-m", "nodejs_wheel"]
    root = Path(__file__).parents[1]
    completed = subprocess.run(
        [
            *command,
            str(root / "tests" / "scenario_selection_harness.cjs"),
            str(root / "src" / "infinity_db" / "web" / "static" / "scenario.js"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "scenario selection race: passed" in completed.stdout


def test_scenario_grid_can_shrink_to_narrow_viewports(scenario_app: Application) -> None:
    status, _, stylesheet = request(scenario_app, "/static/page-overrides.css")
    assert status == 200
    # Both the catalog cards and objective cards must shrink below 280px
    # after page gutters/padding are subtracted on narrow mobile screens.
    assert (
        b"grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));"
        in stylesheet
    )
    assert stylesheet.count(
        b"grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));"
    ) == 2


@pytest.mark.parametrize(
    ("slug", "marker_type", "name", "count", "diameter"),
    [
        ("domination", "console", "Console A Marker", 4, 40),
        ("supplies", "supply-box", "Supply Box Marker", 3, 25),
        ("annihilation", None, None, 0, None),
        ("firefight", None, None, 0, None),
    ],
)
def test_core_scenario_marker_sizes_are_source_cited_and_independent_of_game_size(
    scenario_app: Application,
    slug: str,
    marker_type: str | None,
    name: str | None,
    count: int,
    diameter: int | None,
) -> None:
    for points in (150, 200, 250, 300, 350, 400):
        status, _, body = request(
            scenario_app, f"/api/scenarios/{slug}", query=f"army_points={points}"
        )
        assert status == 200
        placement = json.loads(body)["placement"]
        physical = placement["marker_dimensions"]
        assert physical == ([] if marker_type is None else [{
            "marker_type": marker_type,
            "name": name,
            "count": count,
            "diameter_mm": diameter,
            "citation": {
                "source_id": "its-season-18-en-pdf",
                "source_title": "ITS Season 18: Overheat (English)",
                "source_version": "2026.09.01",
                "source_url": "https://experience.corvusbelli.com/en/infinity/its-rules",
                "page": 17,
            },
        }])
        occurrences = [
            element for element in placement["geometry"]["elements"]
            if element["kind"] == "marker"
        ]
        assert len(occurrences) == count
        assert all(element["markerType"] == marker_type for element in occurrences)


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


@pytest.mark.parametrize(
    ("slug", "diameter", "count"),
    [("domination", 40, 4), ("supplies", 25, 3)],
)
def test_standalone_marker_svg_preserves_physical_footprint_in_both_units(
    scenario_app: Application, slug: str, diameter: int, count: int,
) -> None:
    for points in (150, 200, 250, 300, 350, 400):
        for unit in ("in", "cm"):
            status, _, body = request(
                scenario_app, f"/api/scenarios/{slug}/map.svg",
                query=f"army_points={points}&distance_unit={unit}",
            )
            assert status == 200
            assert body.count(f'data-diameter-mm="{diameter}"'.encode()) == count
            assert f'data-distance-unit="{unit}"'.encode() in body


def test_scenario_map_api_supports_cm_and_rejects_invalid_unit_requests(
    scenario_app: Application,
) -> None:
    endpoint = "/api/scenarios/supplies/map.svg"
    for unit, expected in (("in", "8″"), ("cm", "20 cm")):
        status, headers, body = request(
            scenario_app, endpoint, query=f"army_points=300&distance_unit={unit}"
        )
        assert status == 200
        assert headers["content-type"].startswith("image/svg+xml")
        assert f'data-distance-unit="{unit}"'.encode() in body
        assert expected.encode() in body
        assert b'data-diameter-mm="25"' in body
        assert b'data-unit="in"' in body
    for query in (
        "army_points=300&distance_unit=mm",
        "army_points=300&distance_unit=cm&distance_unit=in",
    ):
        status, _, body = request(scenario_app, endpoint, query=query)
        assert status == 400
        assert b"distance_unit" in body or b"duplicate" in body.lower()


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
    assert b'id="quadrant-1-size" class="area-size"' not in body
    assert b'id="console-q1-center-left"' in body
    assert b'id="console-q1-center-top"' in body
    assert b'data-reference="center"' in body
    assert b'data-distance-inches="12"' in body
    assert b'data-distance-inches="18"' in body

    status, _, body = request(
        scenario_app,
        "/api/scenarios/domination/map.svg",
        query="army_points=175",
    )
    assert status == 400
    assert json.loads(body)["error"].startswith("This scenario does not support 175 Army Points")


def test_scenario_api_accepts_explicit_collection_revision_without_implicit_its_fallback(
    scenario_app: Application,
) -> None:
    status, _, body = request(
        scenario_app,
        "/api/scenarios?collection=n5-core&revision=5.3",
    )
    assert status == 200
    assert [r["slug"] for r in json.loads(body)["items"]] == [
        "annihilation", "domination", "supplies", "firefight",
    ]
    status, _, body = request(
        scenario_app, "/api/scenarios",
        query="collection=its-18&revision=2026.09.01",
    )
    assert status == 200
    season_payload = json.loads(body)
    assert [item["slug"] for item in season_payload["items"]] == ["battleground"]
    assert [(row["id"], row["revision"]) for row in season_payload["collections"]] == [
        ("n5-core", "5.3"), ("its-18", "2026.09.01"),
    ]
    for query in (
        "collection=its-17&revision=2025.09.01",
        "collection=n5-core&revision=5.2",
    ):
        status, _, body = request(scenario_app, "/api/scenarios", query=query)
        assert status == 200
        assert json.loads(body)["items"] == []

    for path in (
        "/api/scenarios/annihilation",
        "/api/scenarios/annihilation/map.svg",
    ):
        status, _, _ = request(
            scenario_app, path,
            query="army_points=300&collection=its-18&revision=2026.09.01",
        )
        assert status == 404
        status, _, _ = request(
            scenario_app, path,
            query="army_points=300&collection=n5-core&revision=5.3",
        )
        assert status == 200


@pytest.mark.parametrize(
    "query",
    [
        "collection=its-18",
        "revision=2026.09.01",
        "collection=its-18&revision=",
        "collection=ITS+18&revision=2026.09.01",
        "collection=its-18&revision=%202026.09.01",
        "collection=its-18&revision=2026.09.01&revision=2026.09.01",
        "collection=its-18&revision=2026.09.01&unsupported=1",
    ],
)
def test_scenario_api_rejects_invalid_or_partial_publication_context(
    scenario_app: Application, query: str,
) -> None:
    for path, args in (
        ("/api/scenarios", ""),
        ("/api/scenarios/annihilation", "army_points=300&"),
        ("/api/scenarios/annihilation/map.svg", "army_points=300&"),
    ):
        status, _, payload = request(scenario_app, path, query=args + query)
        assert status == 400, (path, query, payload)
        assert "error" in json.loads(payload)


def test_scenario_detail_and_map_respect_exact_current_publication(
    scenario_app: Application,
) -> None:
    detail_status, _, body = request(
        scenario_app, "/api/scenarios/annihilation",
        query="army_points=300&collection=n5-core&revision=5.3",
    )
    assert detail_status == 200
    assert json.loads(body)["publication"]["collection_id"] == "n5-core"
    assert json.loads(body)["publication"]["revision"] == "5.3"
    svg_status, headers, body = request(
        scenario_app, "/api/scenarios/annihilation/map.svg",
        query="army_points=300&collection=n5-core&revision=5.3&distance_unit=in",
    )
    assert svg_status == 200
    assert headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in body


def test_synthetic_season_publication_is_selected_exactly_at_public_api(
    scenario_app: Application, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API contract fixture only: intentionally does not publish ITS gameplay facts."""
    from copy import deepcopy

    catalog = scenario_app.api.scenario_catalog
    records = catalog._records()
    record, publication = next(
        item for item in records if item[0]["id"] == "scenario:annihilation"
    )
    synthetic_publication = {
        **publication,
        "collection": "its-demo",
        "collection_title": "Synthetic source-version selection test",
        "revision": "2099.01.01",
    }
    # Deliberately bypass curated export in this API-only test; the official
    # This synthetic selector does not create another real ITS mission.
    monkeypatch.setattr(
        catalog, "_records_cache",
        [*records, (deepcopy(record), synthetic_publication)],
    )
    status, _, body = request(
        scenario_app, "/api/scenarios?collection=its-demo&revision=2099.01.01",
    )
    assert status == 200
    items = json.loads(body)["items"]
    assert [item["slug"] for item in items] == ["annihilation"]
    assert items[0]["publication"]["collection_id"] == "its-demo"
    assert items[0]["publication"]["revision"] == "2099.01.01"

    status, _, body = request(
        scenario_app, "/api/scenarios/annihilation",
        query="army_points=300&collection=its-demo&revision=2099.01.01",
    )
    assert status == 200
    assert json.loads(body)["publication"]["collection_id"] == "its-demo"
    status, _, _ = request(
        scenario_app, "/api/scenarios/annihilation/map.svg",
        query="army_points=300&collection=its-demo&revision=2099.01.01",
    )
    assert status == 200

    status, _, body = request(
        scenario_app, "/api/scenarios?collection=n5-core&revision=5.3",
    )
    assert status == 200
    assert len(json.loads(body)["items"]) == 4
    status, _, _ = request(
        scenario_app, "/api/scenarios/annihilation",
        query="army_points=300&collection=its-17&revision=2025.09.01",
    )
    assert status == 404


@pytest.mark.parametrize(
    ("points", "config", "dimensions"),
    [
        (150, "150-points", (24, 32)),
        (200, "200-250-points", (32, 48)),
        (250, "200-250-points", (32, 48)),
        (300, "300-400-points", (48, 48)),
        (350, "300-400-points", (48, 48)),
        (400, "300-400-points", (48, 48)),
    ],
)
def test_battleground_its18_exact_public_scenario_detail_and_map(
    scenario_app: Application,
    points: int,
    config: str,
    dimensions: tuple[int, int],
) -> None:
    query=f"army_points={points}&collection=its-18&revision=2026.09.01"
    status, _, body = request(scenario_app, "/api/scenarios/battleground", query=query)
    assert status == 200
    item=json.loads(body)
    assert item["publication"]["collection_id"] == "its-18"
    assert item["publication"]["revision"] == "2026.09.01"
    assert item["selected_army_points"] == points
    assert item["placement"]["configuration_id"] == config
    assert item["placement"]["geometry"]["table"]["width"] == dimensions[0]
    assert item["placement"]["geometry"]["table"]["height"] == dimensions[1]
    status, headers, body = request(
        scenario_app, "/api/scenarios/battleground/map.svg",
        query=query,
    )
    assert status == 200
    assert headers["content-type"].startswith("image/svg+xml")
    assert b'<rect id="sector-center"' in body
    assert b'<rect id="sector-near-a"' in body
    assert b'<rect id="sector-near-b"' in body
    assert b'<rect id="deployment-a"' in body
    assert b'<rect id="deployment-b"' in body


def test_battleground_its18_is_never_returned_from_core_or_another_season(
    scenario_app: Application,
) -> None:
    for query in (
        "",
        "collection=n5-core&revision=5.3",
        "collection=its-17&revision=2025.09.01",
        "collection=its-18&revision=2026.08.01",
    ):
        for path in (
            "/api/scenarios/battleground",
            "/api/scenarios/battleground/map.svg",
        ):
            status, _, _ = request(
                scenario_app, path, query=("army_points=300&" + query).rstrip("&"),
            )
            assert status == 404
    for query in ("", "collection=n5-core&revision=5.3"):
        status, _, body = request(scenario_app, "/api/scenarios", query=query)
        assert status == 200
        assert [item["slug"] for item in json.loads(body)["items"]] == [
            "annihilation", "domination", "supplies", "firefight",
        ]


@pytest.mark.parametrize(
    ("slug", "collection", "revision", "expected_rulings"),
    [
        ("annihilation", "n5-core", "5.3", ["faq-ruling:undeployed-ancillary-not-killed"]),
        ("domination", "n5-core", "5.3", []),
        ("supplies", "n5-core", "5.3", ["faq-ruling:scenario-element-carrier-marker-state"]),
        ("firefight", "n5-core", "5.3", []),
        ("battleground", "its-18", "2026.09.01", []),
    ],
)
def test_published_scenarios_keep_faq_applicability_separate_from_core_rules(
    scenario_app: Application,
    slug: str,
    collection: str,
    revision: str,
    expected_rulings: list[str],
) -> None:
    detail_query = f"army_points=300&collection={collection}&revision={revision}"
    status, _, body = request(
        scenario_app, f"/api/scenarios/{slug}", query=detail_query,
    )
    assert status == 200
    detail = json.loads(body)
    assert detail["publication"]["collection_id"] == collection
    assert detail["publication"]["revision"] == revision

    faq_query = (
        f"topic_id=scenario:{slug}&scenario_id=scenario:{slug}"
        "&rules_revision=5.3&as_of=2026-09-01"
    )
    if collection != "n5-core":
        faq_query += f"&season_id={collection}&season_revision={revision}"
    status, _, body = request(scenario_app, "/api/faq-rulings", query=faq_query)
    assert status == 200
    faq = json.loads(body)
    assert [entry["id"] for entry in faq["items"]] == expected_rulings

    # FAQ applicability must not rewrite source-scoped scenario definitions.
    assert "faq_rulings" not in detail
    for ruling in faq["items"]:
        assert ruling["matched_applicability"]
        assert any(
            f"scenario:{slug}" in match.get("scenarioIds", [])
            for match in ruling["matched_applicability"]
        )


def test_scenario_faq_requires_explicit_matching_context_and_client_supplies_it(
    scenario_app: Application,
) -> None:
    base = "topic_id=scenario:annihilation&rules_revision=5.3&as_of=2026-09-01"
    for extra in ("", "&scenario_id=scenario:domination"):
        status, _, body = request(
            scenario_app, "/api/faq-rulings", query=base + extra,
        )
        assert status == 200
        assert json.loads(body)["items"] == []

    status, _, javascript = request(scenario_app, "/static/scenario.js")
    assert status == 200
    assert b"fetchReviewedFaqRulings(`scenario:${slug}`" in javascript
    assert b"scenarioId: `scenario:${slug}`" in javascript
    assert b"seasonRevision: selectedPublication.collection" in javascript
