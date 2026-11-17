"""Scenario-specific Skills use the normal catalog, detail and search surfaces."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.its_season_database import build_its_database
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data/generated"
SOURCE = ROOT / "data/curated/its/n5-its-season-18.json"


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    location = tmp_path_factory.mktemp("scenario-skills") / "its_18.db"
    build_its_database(SOURCE, location)
    return create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db",
        season_databases={"its-18": location},
    )


def _get(app, path):
    status, _, content = wsgi_response(app, "https://scenario-skills.example" + path)
    return status, json.loads(content)


def test_scenario_skills_listed_with_context_and_source(app):
    status, payload = _get(app, "/api/skills")
    assert status == 200
    items = [item for item in payload["items"]
             if item["category"] == "Scenario-specific Skills"]
    assert len([item for item in items if item.get("scenario")]) == 26
    assert {item["slug"] for item in items if item["name"] == "Activate Console"} == {
        "its-18-hardlock-activate-console", "its-18-b-pong-activate-console",
    }
    assert all(item["categories"][0]["id"] == "short-skill" for item in items
               if item.get("scenario"))

    for scenario in ("hardlock", "b-pong"):
        status, detail = _get(app, f"/api/skills/its-18-{scenario}-activate-console")
        assert status == 200
        assert detail["scenario"]["slug"] == scenario
        assert detail["rules"][0]["kind"] == "skill"
        assert detail["rules"][0]["skill_types"][0]["id"] == "short-skill"
        assert detail["rules"][0]["citations"]
        assert detail["variants"] == []


def test_scenario_actions_use_standard_rule_card_model(app):
    status, payload = _get(
        app, "/api/scenarios/hardlock?collection=its-18&army_points=300",
    )
    assert status == 200
    action = next(item for item in payload["special_rules"]
                  if item["id"] == "activate-console")
    assert action["skill"]["id"] == "skill:its-18-hardlock-activate-console"
    assert action["skill"]["summary"].startswith("Activate Console is an Attack")
    assert action["skill"]["citations"]


def test_scenario_skills_search_uses_distinct_routes(app):
    status, payload = _get(app, "/api/search?q=activate%20console")
    assert status == 200
    relevant = [entry for entry in payload["items"]
                if "Activate Console (" in entry["name"]]
    assert {item["name"] for item in relevant} >= {
        "Activate Console (Hardlock)", "Activate Console (B-Pong)",
    }
    assert {item["href"] for item in relevant} >= {
        "/skills/its-18-hardlock-activate-console",
        "/skills/its-18-b-pong-activate-console",
    }
