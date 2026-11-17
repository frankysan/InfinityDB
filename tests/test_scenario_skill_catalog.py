"""Scenario-specific Skills use the normal catalog, detail and search surfaces."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import build_its_database
from infinity_db.scenario_catalog import ScenarioCatalog
from infinity_db.scenario_definition import parse_scenario_definition_record
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
    assert len([item for item in items if item.get("scenario")]) == 28
    assert {"hack-consoles", "pick-up-supply-boxes"} <= {
        item["slug"] for item in items
    }
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
        assert detail["rules"][0]["summary"] == ""
        assert detail["rules"][0]["facts"]["requirements"]
        assert detail["rules"][0]["facts"]["effects"]
        assert detail["variants"] == []

    for slug, scenario, page in (
        ("hack-consoles", "domination", 151),
        ("pick-up-supply-boxes", "supplies", 153),
    ):
        status, detail = _get(app, f"/api/skills/{slug}")
        assert status == 200
        assert detail["scenario"]["slug"] == scenario
        assert detail["rules"][0]["facts"]["category"] == "scenario-skill"
        assert detail["rules"][0]["citations"][0]["page"] == page


def test_scenario_actions_use_standard_rule_card_model(app):
    status, payload = _get(
        app, "/api/scenarios/hardlock?collection=its-18&army_points=300",
    )
    assert status == 200
    action = next(item for item in payload["special_rules"]
                  if item["id"] == "activate-console")
    assert action["skill"]["id"] == "skill:its-18-hardlock-activate-console"
    assert action["skill"]["summary"] == ""
    assert action["skill"]["facts"]["requirements"] == [
        "A Specialist Troop must be in Silhouette contact with a Console.",
    ]
    assert action["skill"]["facts"]["effects"]
    assert action["skill"]["citations"]


def test_reviewed_action_pins_and_distinct_source_ambiguities(app):
    status, pinned = _get(app, "/api/skills/its-18-data-harvest-extract-data-harvester")
    assert status == 200
    assert {citation["page"] for citation in pinned["rules"][0]["citations"]} == {68}
    assert any("Silhouette contact" in note
               for note in pinned["rules"][0]["facts"]["sourceNotes"])

    status, mission_wide = _get(app, "/api/skills/its-18-hardlock-activate-console")
    assert status == 200
    assert all(citation["page"] is None
               for citation in mission_wide["rules"][0]["citations"])

    status, b_pong = _get(app, "/api/skills/its-18-b-pong-activate-console")
    assert status == 200
    assert b_pong["rules"][0]["facts"]["restrictions"]
    assert b_pong["rules"][0]["facts"]["clarifications"]


@pytest.mark.parametrize("mutation", ["no-requirements", "unexpected-fact", "orphan-facts"])
def test_scenario_skill_facts_validate_fail_closed(mutation):
    record = next(
        item for item in load_curated_document(SOURCE)["records"]
        if item["id"] == "scenario:hardlock"
    )
    skill = next(
        item for item in record["facts"]["mission"]["rules"]
        if item["id"] == "activate-console"
    )
    if mutation == "no-requirements":
        skill["skillFacts"]["requirements"] = []
    elif mutation == "unexpected-fact":
        skill["skillFacts"]["unknown"] = ["Invented field"]
    else:
        skill.pop("skillTypeIds")
    with pytest.raises(ValueError, match="skillFacts"):
        parse_scenario_definition_record(record)


def test_skill_action_page_must_belong_to_published_mission(app):
    catalog = ScenarioCatalog(app.rules_database, app.publication_registry)
    records = deepcopy(catalog._records())
    record = next(
        record for record, _publication in records
        if record["id"] == "scenario:data-harvest"
    )
    skill = next(
        item for item in record["facts"]["mission"]["rules"]
        if item["id"] == "extract-data-harvester"
    )
    skill["skillCitations"][0]["page"] = 999
    catalog._records_cache = records
    with pytest.raises(ValueError, match="outside its mission source"):
        catalog.scenario_skill_items()


def test_multiple_exact_action_pages_are_preserved(app):
    catalog = ScenarioCatalog(app.rules_database, app.publication_registry)
    records = deepcopy(catalog._records())
    record = next(
        record for record, _publication in records
        if record["id"] == "scenario:data-harvest"
    )
    skill = next(
        item for item in record["facts"]["mission"]["rules"]
        if item["id"] == "extract-data-harvester"
    )
    skill["skillCitations"].insert(
        1, {"sourceId": "its-season-18-en-pdf", "page": 69},
    )
    catalog._records_cache = records
    item = catalog.get_scenario_skill("its-18-data-harvest-extract-data-harvester")
    assert item is not None
    assert [(cite["source_id"], cite["page"]) for cite in item["rules"][0]["citations"]] == [
        ("its-season-18-en-pdf", 68),
        ("its-season-18-en-pdf", 69),
        ("its-season-18-es-pdf", 68),
    ]


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
