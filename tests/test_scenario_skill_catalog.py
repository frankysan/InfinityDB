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
ITS17 = ROOT / "data/curated/its/n5-its-season-17.json"
ITS17_SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    location = tmp_path_factory.mktemp("scenario-skills") / "its_18.db"
    build_its_database(SOURCE, location)
    return create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db",
        season_databases={"its-18": location},
    )


@pytest.fixture(scope="module")
def its17_app(tmp_path_factory):
    location = tmp_path_factory.mktemp("scenario-skills-its17") / "its_17.db"
    build_its_database(ITS17, location, shared_library=ITS17_SHARED)
    return create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db",
        season_databases={"its-17": location},
    )


def _get(app, path):
    status, _, content = wsgi_response(app, "https://scenario-skills.example" + path)
    return status, json.loads(content)


def test_season_rules_use_exact_selected_publication():
    selected_app = create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db",
        season_databases={
            "its-17": GENERATED / "its_17.db",
            "its-18": GENERATED / "its_18.db",
        },
    )
    for season, revision, expected in (
        ("its-18", "2026.09.11", {
            "skill:civevac", "skill:casevac", "state:casevac",
            "skill:team-ops", "skill:request-tacball", "rule:team-ops-extra",
        }),
        ("its-17", "0.2", {
            "skill:civevac", "skill:casevac", "state:casevac",
            "rule:treasure-hunters", "rule:spec-ops-extra",
        }),
    ):
        status, item = _get(
            selected_app, f"/api/scenarios/evacuation?collection={season}&army_points=300",
        )
        assert status == 200, item
        cards = {record["id"]: record for record in item["season_rules"]}
        common = {
            "rule:civilians", "rule:designated-target", "rule:classified-objectives",
            "rule:high-value-target", "rule:tournament-army-lists", "rule:long-service",
            "rule:tournament-format", "rule:tournament-scoring", "rule:tournament-pairings",
            "rule:escalation-tournament", "rule:free-game", "rule:soldiers-of-fortune",
            "rule:direct-action", "rule:reinforcements-extra", "rule:resilience-operations",
        }
        assert set(cards) == expected | common
        assert cards["rule:tournament-army-lists"]["facts"]["applicability"]["context"] == (
            "official-tournament"
        )
        civilian = cards["rule:civilians"]
        assert bool(civilian["facts"].get("sourceNotes")) == (season == "its-18")
        assert any(
            token.get("public_reference", {}).get("href") == "#rule-skill-civevac"
            for row in civilian["fact_tokens"]["restrictions"] for token in row
            if token["type"] == "reference"
        )
        assert all(record["facts"]["applicability"]["revision"] == revision
                   for record in cards.values())
        assert all(citation["source_id"].startswith(f"its-season-{season[4:]}-")
                   for record in cards.values() for citation in record["citations"])
        assert cards["skill:civevac"]["skill_types"][0]["id"] == (
            "basic-short-skill" if season == "its-18" else "short-movement-skill"
        )
        state = cards["state:casevac"]
        assert state["facts"]["applicability"]["context"] == "season"
        assert any(token.get("public_reference", {}).get("href") == "#rule-skill-casevac"
                   for token in state["summary_tokens"] if token["type"] == "reference")
        assert "rule:tactical-support" not in cards
        assert "season_rules" not in _get(
            selected_app, "/api/scenarios/annihilation?army_points=300",
        )[1]


@pytest.mark.parametrize("season", ["its-17", "its-18"])
def test_mission_event_context(app, its17_app, season):
    common = {
        "evacuation", "hardlock", "uplink-center", "battleground", "annihilation",
        "cutthroat", "superiority", "provisioning", "area-of-interest", "last-launch",
        "b-pong", "crossing-lines", "corporate-appropriation", "critical-intervention",
        "outbreak", "akial-interference",
    }
    excluded = {"battleground", "superiority", "crossing-lines", "critical-intervention"}
    historical = season == "its-17"
    selected_app = its17_app if historical else app
    slugs = common if historical else common | {
        "double-bind", "the-dig", "data-harvest", "neutralization",
    }
    counts = {
        "b-pong": 2, "evacuation": 2, "last-launch": 2,
        "critical-intervention": 1, "hardlock": 1, "provisioning": 1,
    }
    for slug in sorted(slugs):
        status, mission = _get(
            selected_app, f"/api/scenarios/{slug}?collection={season}&army_points=300",
        )
        assert status == 200, slug
        if historical:
            en = "not-suitable" if slug in excluded else "suitable"
            es = "not-suitable" if slug in {
                "area-of-interest", "corporate-appropriation",
            } else en
        else:
            en = "not-declared" if slug in excluded | {
                "double-bind", "data-harvest", "provisioning",
            } else "suitable"
            es = "suitable" if slug == "provisioning" else en
        expected: dict[str, object] = {"reinforcements": {"en": en, "es": es}}
        count = counts.get(slug, 0) if historical else 0
        if historical:
            expected["tacticalSupportOptions"] = count
        assert mission["setup"]["event_context"] == expected, slug
        if not count:
            assert "tactical_support" not in mission, slug
            continue
        support = mission["tactical_support"]
        assert support["name"] == "Tactical Support"
        assert len(support["options"]) == 12
        assert len(support["sourceNotes"]) == 2
        assert {(c["source_id"], c["page"]) for c in support["citations"]} == {
            ("its-season-17-v0.2-en-pdf", page) for page in (27, 28, 29)
        } | {
            ("its-season-17-v0.2-es-pdf", page) for page in (28, 29, 30)
        }
        cancel = next(o for o in support["options"] if o["name"] == "Cancel enemy support")
        assert "EN:" in cancel["timing"] and "ES:" in cancel["timing"]


@pytest.mark.parametrize("season", ["its-17", "its-18"])
def test_season_specific_marker_dimensions(app, its17_app, season):
    selected_app = its17_app if season == "its-17" else app
    page = 13 if season == "its-17" else 18
    source = "its-season-17-v0.2-en-pdf" if season == "its-17" else "its-season-18-en-pdf"
    for slug, marker_type, count in (
        ("b-pong", "tracking-beacon", 1),
        ("evacuation", "civilian", 4),
        ("critical-intervention", "defensive-turret", 2),
    ):
        for points in (150, 200, 250, 300, 350, 400):
            status, mission = _get(
                selected_app, f"/api/scenarios/{slug}?collection={season}&army_points={points}",
            )
            assert status == 200
            marker = next(
                m for m in mission["placement"]["marker_dimensions"]
                if m["marker_type"] == marker_type
            )
            assert marker["count"] == count
            if slug == "b-pong" and season == "its-18":
                assert marker["diameter_mm"] is None
                assert marker["size_status"] == "source-conflict"
                assert marker["citation"] is None
            else:
                assert marker["diameter_mm"] == 25
                assert marker["citation"]["page"] == page
                assert marker["citation"]["source_id"] == source
                if slug == "evacuation":
                    assert marker["size_status"] == "token-or-civilian-model"
                elif slug == "critical-intervention":
                    assert marker["size_status"] == "token-or-model"
                else:
                    assert "size_status" not in marker


def _scoped_actions(catalog, season):
    return sorted({
        slug
        for item in catalog["items"]
        for slug in [item["slug"], *item.get("aliases", [])]
        if slug.startswith(f"{season}-")
        and item["category"] == "Scenario-specific Skills"
    })


def test_scenario_skills_listed_with_context_and_source(app):
    status, payload = _get(app, "/api/skills")
    assert status == 200
    items = [item for item in payload["items"]
             if item["category"] == "Scenario-specific Skills"]
    assert len(items) == 26
    assert {"scenario-hack-consoles", "scenario-pick-up-supply-boxes"} <= {
        item["slug"] for item in items
    }
    assert {item["slug"] for item in items if item["name"] == "Activate Console"} == {
        "scenario-activate-console",
    }
    assert all(item["categories"][0]["id"] == "short-skill" for item in items
               if item.get("scenario"))
    assert all(not item["name"].endswith((" (Short Skill)", " (Long Skill)"))
               for item in items)
    assert next(item["name"] for item in items
                if item["slug"] == "scenario-download-id") == "Download ID"

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


def test_its17_source_labels_are_visible_on_skill_cards(its17_app):
    status, catalog = _get(its17_app, "/api/skills")
    assert status == 200
    actions = _scoped_actions(catalog, "its-17")
    assert len(actions) == 22
    for slug in actions:
        status, detail = _get(its17_app, f"/api/skills/{slug}")
        assert status == 200
        assert [label["name"] for label in detail["rules"][0]["labels"]] == [
            "Attack", "Scenario",
        ]

    status, scenario = _get(
        its17_app, "/api/scenarios/hardlock?collection=its-17&army_points=300",
    )
    assert status == 200
    beacon = next(rule for rule in scenario["special_rules"] if rule["id"] == "pick-up-beacon")
    assert [label["name"] for label in beacon["skill"]["labels"]] == [
        "Attack", "Scenario",
    ]
    for slug, expected in (("civevac", ["Optional", "Scenario"]),
                           ("casevac", ["Optional"])):
        status, skill = _get(its17_app, f"/api/skills/{slug}")
        assert status == 200
        assert [label["name"] for label in skill["rules"][0]["labels"]] == expected


def test_its18_source_labels_are_visible_on_every_skill_card(app):
    status, catalog = _get(app, "/api/skills")
    assert status == 200
    actions = _scoped_actions(catalog, "its-18")
    assert len(actions) == 31
    for slug in actions:
        status, detail = _get(app, f"/api/skills/{slug}")
        assert status == 200
        labels = detail["rules"][0]["labels"]
        assert [label["name"] for label in labels] == ["Attack", "Scenario"]
        assert labels[0]["id"] == "attack"
        assert labels[0]["description"]
        assert "id" not in labels[1]  # Not a Core N5 Label route.

    status, hardlock = _get(app, "/api/scenarios/hardlock?collection=its-18&army_points=300")
    assert status == 200
    beacon = next(rule for rule in hardlock["special_rules"] if rule["id"] == "pick-up-beacon")
    assert [label["name"] for label in beacon["skill"]["labels"]] == ["Attack", "Scenario"]

    # Core Scenario Skills preserve their own authored N5 Labels.
    status, core = _get(app, "/api/skills/hack-consoles")
    assert status == 200
    assert [label["name"] for label in core["rules"][0]["labels"]] == ["Attack"]


@pytest.mark.parametrize(("slug", "expected"), [
    ("civevac", ["Optional", "Scenario"]),
    ("casevac", ["Optional"]),
    ("team-ops", ["Obligatory"]),
    ("request-tacball", ["Attack", "Optional"]),
])
def test_its18_season_skills_display_printed_labels(app, slug, expected):
    status, detail = _get(app, f"/api/skills/{slug}")
    assert status == 200
    labels = detail["rules"][0]["labels"]
    assert [label["name"] for label in labels] == expected
    assert all(label.get("id") for label in labels if label["name"] != "Scenario")


@pytest.mark.parametrize(("source_labels", "error"), [
    (["Attack", "Attack"], "sourceLabels"),
    (["Attack", ""], "sourceLabels"),
    (["Attack", 42], "sourceLabels"),
])
def test_scenario_skill_source_labels_fail_closed(source_labels, error):
    record = next(
        row for row in load_curated_document(SOURCE)["records"]
        if row["id"] == "scenario:hardlock"
    )
    action = next(
        rule for rule in record["facts"]["mission"]["rules"]
        if rule["id"] == "pick-up-beacon"
    )
    action["sourceLabels"] = source_labels
    with pytest.raises(ValueError, match=error):
        parse_scenario_definition_record(record)


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
        if result["href"] == "/skills/scenario-download-id"
    } == {"Download ID"}


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
        "its-18-double-bind-activate-antenna-destroyed": (75, 76),
        "its-18-the-dig-analyze-hyperthermal-tech": (80, 80),
        "its-18-the-dig-neutralize-hyperthermal-tech": (80, 80),
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
        "its-18-neutralization-extract-hyperthermal-tech": (106, 107),
        "its-18-provisioning-extract-supply-boxes": (112, 112),
        "its-18-provisioning-pickup-supply-boxes": (112, 112),
        "its-18-area-of-interest-activate-communication-antenna": (122, 123),
        "its-18-data-harvest-extract-data-harvester": (68, 68),
        "its-18-data-harvest-pickup-data-harvester": (69, 69),
        "its-18-data-harvest-neutralize-data-harvester": (70, 70),
        "its-18-last-launch-download-id": (116, 117),
        "its-18-last-launch-swap-id": (117, 118),
        "its-18-last-launch-extract-identified-trooper": (119, 120),
        "its-18-corporate-appropriation-pick-up-prototype": (55, 55),
        "its-18-corporate-appropriation-use-panoply": (57, 56),
        "its-18-outbreak-stabilize-infected": (85, 85),
        "its-18-outbreak-scan-infected": (86, 86),
        "its-18-critical-intervention-extract-data-pack": (101, 102),
        "its-18-critical-intervention-use-inhibitor-antenna": (102, 103),
    }
    status, catalog = _get(app, "/api/skills")
    assert status == 200
    assert set(_scoped_actions(catalog, "its-18")) == set(expected)
    for slug, (english_page, spanish_page) in expected.items():
        status, detail = _get(app, f"/api/skills/{slug}")
        assert status == 200, slug
        assert [(c["source_id"], c["page"]) for c in detail["rules"][0]["citations"]] == [
            ("its-season-18-en-pdf", english_page),
            ("its-season-18-es-pdf", spanish_page),
        ], slug


@pytest.mark.parametrize(("season", "scenario", "action", "query"), [
    ("its-18", "double-bind", "activate-antenna-destroyed", "activate antenna"),
    ("its-18", "the-dig", "neutralize-hyperthermal-tech", "neutralize hyperthermal tech"),
    ("its-18", "neutralization", "extract-hyperthermal-tech", "extract hyperthermal tech"),
    ("its-18", "corporate-appropriation", "use-panoply", "use panoplies"),
    ("its-18", "provisioning", "pickup-supply-boxes", "pick up supply boxes"),
    ("its-17", "provisioning", "pickup-supply-boxes", "pick up supply boxes"),
])
def test_restored_actions_have_cards_and_search_routes(
    app, its17_app, season, scenario, action, query,
):
    selected_app = app if season == "its-18" else its17_app
    slug = f"{season}-{scenario}-{action}"
    status, detail = _get(selected_app, f"/api/skills/{slug}")
    assert status == 200
    rule = detail["rules"][0]
    assert rule["facts"]["requirements"]
    assert rule["facts"]["effects"]
    assert [label["name"] for label in rule["labels"]] == ["Attack", "Scenario"]
    assert rule["skill_types"][0]["id"] == "short-skill"
    status, mission = _get(
        selected_app, f"/api/scenarios/{scenario}?collection={season}&army_points=300",
    )
    assert status == 200
    card = next(rule for rule in mission["special_rules"] if rule["id"] == action)
    assert card["skill"]["id"] == f"skill:{slug}"
    status, results = _get(selected_app, "/api/search?q=" + query.replace(" ", "%20"))
    assert status == 200
    route = detail.get("canonical_slug", slug)
    assert f"/skills/{route}" in {result["href"] for result in results["items"]}


def test_destroyed_antenna_and_supply_pickup_variants_are_distinct(app, its17_app):
    prefix = "/api/skills/its-18-double-bind-activate-antenna"
    _, normal = _get(app, prefix)
    _, destroyed = _get(app, prefix + "-destroyed")
    intact = normal["rules"][0]["facts"]
    wreck = destroyed["rules"][0]["facts"]
    assert "Specialist Troops" in " ".join(intact["requirements"])
    assert "WIP-3" not in " ".join(intact["effects"])
    assert "Hacker" in " ".join(wreck["requirements"])
    assert "entirely inside" in " ".join(wreck["requirements"])
    assert "WIP-3" in " ".join(wreck["effects"])

    _, current = _get(app, "/api/skills/its-18-provisioning-pickup-supply-boxes")
    _, historic = _get(its17_app, "/api/skills/its-17-provisioning-pickup-supply-boxes")
    modern = current["rules"][0]
    old = historic["rules"][0]
    assert "any Safe Area" in " ".join(modern["facts"]["sourceNotes"])
    assert "enemy's Safe Area" in " ".join(old["facts"]["requirements"])
    assert [(c["source_id"], c["page"]) for c in old["citations"]] == [
        ("its-season-17-v0.2-en-pdf", 74),
        ("its-season-17-v0.2-es-pdf", 72),
    ]


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
    with pytest.raises(ValueError, match="sourceLabels|skillFacts"):
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


def test_scenario_skill_lookup_preserves_detached_catalog_and_aliases(app):
    catalog = ScenarioCatalog(app.rules_database, app.publication_registry)
    for slug in ("scenario-activate-console", "its-18-hardlock-activate-console"):
        expected = catalog.get_scenario_skill(slug)
        assert expected is not None
        selected = catalog.get_scenario_skill(slug)
        assert selected == expected
        assert selected is not None
        selected["rules"].clear()
        assert catalog.get_scenario_skill(slug) == expected
    items = catalog.scenario_skill_items()
    items[0]["rules"].clear()
    assert catalog.scenario_skill_items()[0]["rules"]


def test_scenario_skills_search_uses_canonical_route(app):
    status, payload = _get(app, "/api/search?q=activate%20console")
    assert status == 200
    relevant = [entry for entry in payload["items"] if entry["name"] == "Activate Console"]
    assert [item["href"] for item in relevant] == ["/skills/scenario-activate-console"]
    status, detail = _get(app, "/api/skills/scenario-activate-console")
    assert status == 200
    assert {scenario["slug"] for scenario in detail["scenarios"]} == {"hardlock", "b-pong"}
    assert len(detail["context_variants"]) == 2
    for variant in detail["context_variants"]:
        for rule in variant["rules"]:
            status, exact = _get(app, "/api/skills/" + rule["id"].removeprefix("skill:"))
            assert status == 200
            assert exact["canonical_slug"] == detail["slug"]
            assert exact["rules"][0]["facts"] == rule["facts"]
            assert exact["rules"][0]["citations"] == rule["citations"]
