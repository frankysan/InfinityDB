"""Validate catalog summary and deduplicated detail usage parity."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.catalog_projection import CATALOGS, CatalogProjection
from infinity_db.database.repository import Database
from infinity_db.database_set import SEASON_DATABASE_SOURCES
from infinity_db.maintained_text_references import (
    _enrich_rule_record,
    _Resolver,
    collect_reference_targets,
)
from infinity_db.reference_page_storage import collect_reference_pages
from infinity_db.rules_database import RulesDatabase
from infinity_db.specialist_filter import SPECIALIST_CONTEXTS, candidate_unit_ids
from infinity_db.web.app import create_app, create_app_from_database_set
from tools.browser_wsgi_transport import wsgi_response

RELEASE = Path("data/generated")
SEASONS = {
    season: RELEASE / filename for season, (filename, _) in SEASON_DATABASE_SOURCES.items()
}


def test_every_published_catalog_detail_and_summary_matches_composer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app_from_database_set(RELEASE)
    projection = app.database.catalog_projection
    assert projection is not None
    with monkeypatch.context() as context:
        context.setattr(CatalogProjection, "select", lambda path: None)
        legacy = create_app(
            RELEASE / "army.db", RELEASE / "rules_n5.db", season_databases=SEASONS,
        )
    assert legacy.database.catalog_projection is None
    # Check before API consumers can attach slugs to cached raw records.
    total = 0
    for catalog in CATALOGS:
        summaries = legacy.database.list_catalog_items(catalog)
        assert app.database.list_catalog_items(catalog) == summaries
        assert app.database.list_catalog_filter_items(
            catalog
        ) == legacy.database.list_catalog_filter_items(catalog)
        for summary in summaries:
            item_id = summary["id"]
            slug = legacy.database.application_slug(catalog, item_id)
            if catalog == "skills":
                expected = legacy.database.get_skill(item_id)
                assert app.database.get_skill(item_id) == expected
                if slug:
                    assert app.database.get_skill(slug) == expected
            else:
                expected = legacy.database.get_catalog_item(catalog, item_id)
                assert app.database.get_catalog_item(catalog, item_id) == expected
                if slug:
                    assert app.database.get_catalog_item(catalog, slug) == expected
            total += 1
    assert total > 200
    for filter_only in (False, True):
        assert app.skill_catalog.list_skills(filter_only=filter_only) == (
            legacy.skill_catalog.list_skills(filter_only=filter_only)
        )
        assert app.equipment_catalog.list_equipment(filter_only=filter_only) == (
            legacy.equipment_catalog.list_equipment(filter_only=filter_only)
        )
    assert app.api._unit_filter_catalogs() == legacy.api._unit_filter_catalogs()
    # End-to-end parity covers the unchanged curated and reference enrichment,
    # including rules-only and presentation-encoded entries.
    for route in (
        "/api/skills", "/api/equipment", "/api/weapons",
        "/api/skills/mimetism", "/api/skills/scenario-activate-console",
        "/api/equipment/cube", "/api/equipment/firewall",
        "/api/weapons/combi-rifle",
        "/api/glossary", "/api/unit-profile-help", "/api/orders-aros",
        "/api/rules/specialist-troops-standard", "/api/traits/zone-of-control-zc",
        "/api/states/isolated", "/api/states/casevac", "/api/hacking-programs/oblivion",
        "/api/ammunition/para", "/api/scenarios/domination?army_points=350",
        "/api/scenarios/hardlock?collection=its-17&army_points=300",
        "/api/scenarios/hardlock?collection=its-18&army_points=300",
    ):
        status, _, body = wsgi_response(app, "http://localhost" + route)
        expected_status, _, expected_body = wsgi_response(legacy, "http://localhost" + route)
        assert status == expected_status == 200, route
        assert json.loads(body) == json.loads(expected_body), route
    assert app.database.get_skill("no-such-skill-xyz") is None
    assert app.database.get_catalog_item("weapons", "no-such-weapon-xyz") is None


@pytest.mark.parametrize("mutation", [
    "DELETE FROM catalog_summaries",
    "DELETE FROM catalog_usage_units",
    "UPDATE catalog_details SET body='null'",
    "DROP TABLE catalog_details",
])
def test_catalog_projection_damage_fails_closed(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(RELEASE / "rules_n5.db", path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match="catalog projection"):
        RulesDatabase(path).validate()


def test_partial_scope_retains_canonical_catalogs() -> None:
    app = create_app(
        RELEASE / "army.db", RELEASE / "rules_n5.db",
        season_databases={"its-18": SEASONS["its-18"]},
    )
    assert app.database.catalog_projection is None
    assert app.database.list_catalog_items("skills") == Database(
        RELEASE / "army.db"
    ).list_catalog_items("skills")


def test_specialist_projection_parity_and_api_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app_from_database_set(RELEASE)
    assert app.rules_database is not None
    projection = app.database.catalog_projection
    assert projection is not None
    canonical = Database(RELEASE / "army.db")
    for context in sorted(SPECIALIST_CONTEXTS):
        assert projection.specialist_candidates(context) == candidate_unit_ids(
            canonical, app.rules_database, context,
        )
    for context in sorted(SPECIALIST_CONTEXTS):
        url = ("http://localhost/api/units?matching_scope=loadout&counts=prospective"
               f"&specialist={context}&skill_id=berserk&limit=5")
        status, _, body = wsgi_response(app, url)
        with monkeypatch.context() as patch:
            patch.setattr(CatalogProjection, "specialist_candidates", lambda self, context: None)
            expected_status, _, expected_body = wsgi_response(app, url)
        assert status == expected_status == 200
        assert json.loads(body) == json.loads(expected_body)
    def fail(*args, **kwargs):
        raise AssertionError("Canonical Specialist composer should not run")
    monkeypatch.setattr("infinity_db.web.api_handler.candidate_unit_ids", fail)
    assert wsgi_response(app, "http://localhost/api/units?specialist=standard")[0] == 200


@pytest.mark.parametrize("mutation", [
    "DELETE FROM specialist_candidates WHERE context='standard'",
    "UPDATE specialist_candidates SET body='[]'",
    "DROP TABLE specialist_candidates",
])
def test_specialist_projection_damage_fails_closed(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(RELEASE / "rules_n5.db", path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match="Specialist candidate projection"):
        RulesDatabase(path).validate()


def test_reference_target_projection_matches_all_composed_records() -> None:
    app = create_app_from_database_set(RELEASE)
    rules = app.rules_database
    projection = app.database.catalog_projection
    assert rules is not None and projection is not None
    targets = projection.reference_targets
    assert targets is not None
    canonical = Database(RELEASE / "army.db")
    assert targets == collect_reference_targets(canonical, rules)
    with rules._connect() as db:
        rows = [(context, json.loads(body)) for context, body in db.execute(
            "SELECT scenario_id,body FROM composed_rule_records ORDER BY record_id,scenario_id"
        )]
    for context, record in rows:
        scenario_id = record["id"] if record["kind"] == "scenario" else context or None
        options = {
            "scenario_id": scenario_id,
            "local_rule_ids": frozenset({record["id"]}),
        }
        expected, actual = deepcopy(record), deepcopy(record)
        _enrich_rule_record(expected, _Resolver(canonical, rules, **options))
        resolver = _Resolver(app.database, rules, **options)
        assert resolver.reference_targets is targets
        _enrich_rule_record(actual, resolver)
        assert actual == expected, (record["id"], context)


def test_reference_target_routes_fallback_and_mutation_isolation(monkeypatch) -> None:
    app = create_app_from_database_set(RELEASE)
    rules = app.rules_database
    assert rules is not None
    canonical = Database(RELEASE / "army.db")
    additional = {
        "skill:synthetic-season-skill": {
            "id": "skill:synthetic-season-skill", "kind": "skill",
            "name": "Synthetic Season Skill", "summary": "Use [[skill:dodge]].",
            "facts": {"category": "common-skill"},
        },
    }
    options = {
        "local_rule_ids": frozenset({"skill:dodge"}),
        "additional_records": additional,
    }
    expected = _Resolver(canonical, rules, **options)
    actual = _Resolver(app.database, rules, **options)
    text = (
        "[[skill:synthetic-season-skill]] and [[skill:dodge:plural]] "
        "with [[skill:jump|Jumping]] over [[distance:2:inch]]."
    )
    value = expected.tokens(text)
    assert actual.tokens(text) == value
    assert value[0]["preview_tokens"][1]["public_reference"] == {"href": "#rule-skill-dodge"}
    assert value[2]["public_reference"] == {"href": "#rule-skill-dodge"}
    changed = actual.tokens(text)
    changed[2]["public_reference"]["href"] = "bad"
    changed[0]["preview_tokens"][0]["text"] = "bad"
    assert actual.tokens(text) == value

    def fail(*args, **kwargs):
        raise AssertionError("Published Rules target should not load a complete record")

    monkeypatch.setattr(rules, "composed_record", fail)
    assert _Resolver(app.database, rules).tokens("[[skill:dodge]]")
    monkeypatch.undo()
    with pytest.raises(ValueError, match="is not current"):
        actual.tokens("[[skill:no-such-record]]")


@pytest.mark.parametrize("mutation", [
    "DELETE FROM maintained_reference_targets",
    "UPDATE maintained_reference_targets SET body='{}'",
    "DROP TABLE maintained_reference_targets",
])
def test_reference_target_projection_damage_fails_closed(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(RELEASE / "rules_n5.db", path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match="maintained reference targets"):
        RulesDatabase(path).validate()



def test_reference_pages_match_canonical_composition() -> None:
    app = create_app_from_database_set(RELEASE)
    rules = app.rules_database
    projection = app.database.catalog_projection
    assert rules is not None and projection is not None
    canonical = Database(RELEASE / "army.db")
    pages = collect_reference_pages(canonical, rules)
    for key, expected in pages.items():
        assert projection.reference_page(key) == expected
    assert app.api.glossary_catalog.entries() == pages["glossary"]
    for key in pages:
        if not key.startswith("orders-aros:"):
            continue
        slug = key.partition(":")[2]
        status, _, body = wsgi_response(
            app, f"http://localhost/api/orders-aros?scenario={slug}"
        )
        assert status == 200
        assert json.loads(body) == {**pages["orders-aros"], "scenario": pages[key]}
    assert json.loads(wsgi_response(
        app, "http://localhost/api/orders-aros"
    )[2]) == pages["orders-aros"]
    assert wsgi_response(app, "http://localhost/api/orders-aros?scenario=hardlock")[0] == 400


@pytest.mark.parametrize("mutation", [
    "DELETE FROM reference_pages WHERE page='glossary'",
    "UPDATE reference_pages SET body='{}'",
    "DROP TABLE reference_pages",
])
def test_reference_page_projection_damage_fails_closed(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(RELEASE / "rules_n5.db", path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match="reference page projection"):
        RulesDatabase(path).validate()
