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
    assert all(not item["name"].endswith((" (Short Skill)", " (Long Skill)"))
               for item in items)
    assert next(item["name"] for item in items
                if item["slug"] == "its-18-last-launch-download-id") == "Download ID"

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
    assert action["skill"]["name"] == "Activate Console"
    assert action["skill"]["summary"] == ""
    assert action["skill"]["facts"]["requirements"] == [
        "A Specialist Troop must be in Silhouette contact with a Console.",
    ]
    assert action["skill"]["facts"]["effects"]
    assert action["skill"]["citations"]


def test_suffix_is_absent_from_skill_detail_scenario_and_search(app):
    skill_slug = "its-18-last-launch-download-id"
    status, detail = _get(app, f"/api/skills/{skill_slug}")
    assert status == 200
    assert detail["name"] == "Download ID"
    assert detail["rules"][0]["name"] == "Download ID"
    assert detail["rules"][0]["skill_types"][0]["name"] == "Short Skill"

    status, scenario = _get(
        app, "/api/scenarios/last-launch?collection=its-18&army_points=300",
    )
    assert status == 200
    action = next(
        rule for rule in scenario["special_rules"] if rule["id"] == "download-id"
    )
    assert action["skill"]["name"] == "Download ID"
    assert action["skill"]["id"] == f"skill:{skill_slug}"

    status, results = _get(app, "/api/search?q=download%20id")
    assert status == 200
    assert {
        result["name"] for result in results["items"]
        if result["href"] == f"/skills/{skill_slug}"
    } == {"Download ID (Last Launch)"}


def test_reviewed_action_pins_and_distinct_source_ambiguities(app):
    status, pinned = _get(app, "/api/skills/its-18-data-harvest-extract-data-harvester")
    assert status == 200
    assert {citation["page"] for citation in pinned["rules"][0]["citations"]} == {68}
    assert any("Silhouette contact" in note
               for note in pinned["rules"][0]["facts"]["sourceNotes"])

    status, hardlock = _get(app, "/api/skills/its-18-hardlock-activate-console")
    assert status == 200
    assert [(c["source_id"], c["page"]) for c in hardlock["rules"][0]["citations"]] == [
        ("its-season-18-en-pdf", 52), ("its-season-18-es-pdf", 129),
    ]

    status, b_pong = _get(app, "/api/skills/its-18-b-pong-activate-console")
    assert status == 200
    assert b_pong["rules"][0]["facts"]["restrictions"]
    assert b_pong["rules"][0]["facts"]["clarifications"]


def test_all_its18_scenario_actions_have_exact_bilingual_source_pages(app):
    # Independently reviewed against the pinned EN/ES 2026.09.11 originals.
    # Keep this expectation distinct from the curated source and build output.
    expected = {
        "its-18-crossing-lines-activate-antenna": (65, 65),
        "its-18-double-bind-activate-antenna": (75, 75),
        "its-18-the-dig-analyze-hyperthermal-tech": (80, 80),
        "its-18-superiority-hack-consoles": (137, 142),
        "its-18-uplink-center-activate-communication-antenna": (140, 145),
        "its-18-hardlock-pick-up-beacon": (50, 128),
        "its-18-hardlock-activate-console": (52, 129),
        "its-18-b-pong-relocate-tracking-beacon": (60, 59),
        "its-18-b-pong-activate-console": (61, 61),
        "its-18-akial-interference-emit-akial-interference": (95, 95),
        "its-18-akial-interference-filter-signal": (96, 96),
        "its-18-evacuation-activate-extraction-console": (90, 90),
        "its-18-neutralization-pick-up-hyperthermal-tech": (107, 107),
        "its-18-provisioning-extract-supply-boxes": (112, 112),
        "its-18-area-of-interest-activate-communication-antenna": (122, 123),
        "its-18-data-harvest-extract-data-harvester": (68, 68),
        "its-18-data-harvest-pickup-data-harvester": (69, 69),
        "its-18-data-harvest-neutralize-data-harvester": (70, 70),
        "its-18-last-launch-download-id": (116, 117),
        "its-18-last-launch-swap-id": (117, 118),
        "its-18-last-launch-extract-identified-trooper": (119, 120),
        "its-18-corporate-appropriation-pick-up-prototype": (55, 55),
        "its-18-outbreak-stabilize-infected": (85, 85),
        "its-18-outbreak-scan-infected": (86, 86),
        "its-18-critical-intervention-extract-data-pack": (101, 102),
        "its-18-critical-intervention-use-inhibitor-antenna": (102, 103),
    }
    status, catalog = _get(app, "/api/skills")
    assert status == 200
    published = {
        item["slug"] for item in catalog["items"]
        if item.get("scenario") and item["slug"].startswith("its-18-")
    }
    assert published == set(expected)
    for slug, (english_page, spanish_page) in expected.items():
        status, detail = _get(app, f"/api/skills/{slug}")
        assert status == 200, slug
        assert [(c["source_id"], c["page"]) for c in detail["rules"][0]["citations"]] == [
            ("its-season-18-en-pdf", english_page),
            ("its-season-18-es-pdf", spanish_page),
        ], slug


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
