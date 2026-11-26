"""Validate catalog summary and deduplicated detail usage parity."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from infinity_db.catalog_projection import CATALOGS, CatalogProjection
from infinity_db.database.repository import Database
from infinity_db.database_set import SEASON_DATABASE_SOURCES
from infinity_db.rules_database import RulesDatabase
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
