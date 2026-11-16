"""One season may publish old and hotfix revisions without redirecting either."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.its_season_database import build_its_database
from infinity_db.publication_registry import PublicationReference, PublicationRegistry
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
HOTFIX_SOURCE = ROOT / "data/curated/its/n5-its-season-18-2026.09.11.json"
ORIGIN = "https://revision-test.example"


@pytest.fixture
def two_revisions(tmp_path: Path):
    hotfix = tmp_path / "its_18_2026.09.11.db"
    build_its_database(HOTFIX_SOURCE, hotfix)
    revisions = {
        "its-18": RELEASE / "its_18.db",
        "its-18@2026.09.11": hotfix,
    }
    rules = RulesDatabase(RELEASE / "rules_n5.db")
    return PublicationRegistry(rules, revisions), create_app(
        RELEASE / "army.db", RELEASE / "rules_n5.db", season_databases=revisions,
    )


def _json(app, path: str) -> tuple[int, dict, dict]:
    status, headers, data = wsgi_response(app, ORIGIN + path)
    return status, dict(headers), json.loads(data)


def test_both_its_revisions_registered_and_no_cross_version_fallback(two_revisions) -> None:
    registry, app = two_revisions
    assert set(registry.season_manifest()) == {"its-18", "its-18@2026.09.11"}
    assert registry.has_season("its-18", "2026.09.01")
    assert registry.has_season("its-18", "2026.09.11")
    assert not registry.has_season("its-18", "2026.09.12")
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:the-dig", "2026.09.01",
    )) is None

    summaries = {}
    for revision, expected_ids in (
        ("2026.09.01", ["battleground"]),
        ("2026.09.11", [
            "crossing-lines", "double-bind", "the-dig", "annihilation", "battleground",
        ]),
    ):
        status, _, payload = _json(
            app, f"/api/scenarios?collection=its-18&revision={revision}",
        )
        assert status == 200
        summaries[revision] = payload["items"]
        assert [entry["id"] for entry in payload["items"]] == expected_ids
        assert all(item["publication"]["revision"] == revision for item in payload["items"])

    assert len(summaries["2026.09.01"]) == 1
    status, _, payload = _json(app, "/api/scenarios")
    assert status == 200
    collections = {
        (item["id"], item["revision"]): item
        for item in payload["collections"]
    }
    assert collections[("its-18", "2026.09.11")]["scenario_count"] == 5
    assert collections[("its-18", "2026.09.01")]["scenario_count"] == 1
    assert _json(app, "/api/scenarios?collection=its-18&revision=2026.09.12")[2]["items"] == []


def test_battleground_and_policies_bind_correct_edition_sources(two_revisions) -> None:
    registry, app = two_revisions
    for revision, pages in (("2026.09.01", [121, 122, 123]), ("2026.09.11", [129, 130, 131])):
        uri = (
            f"/api/scenarios/battleground?army_points=300"
            f"&collection=its-18&revision={revision}"
        )
        status, headers, item = _json(app, uri)
        assert status == 200
        assert item["publication"]["revision"] == revision
        assert [citation["page"] for citation in item["citations"]] == pages
        assert item["publication"]["sources"][0]["version"] == revision
        status, _, policy = _json(
            app, "/api/season-policies?season_id=its-18"
            f"&season_revision={revision}&context=official-tournament",
        )
        assert status == 200
        assert len(policy["items"]) == 1
        assert policy["items"][0]["citations"][0]["sourceVersion"] == revision
        assert wsgi_response(app, ORIGIN + uri.replace(
            "/api/scenarios/battleground?", "/api/scenarios/battleground/map.svg?",
        ))[0] == 200

    status, _, the_dig = _json(
        app, "/api/scenarios/the-dig?army_points=150"
        "&collection=its-18&revision=2026.09.11",
    )
    assert status == 200
    assert the_dig["placement"]["geometry"]["table"]["width"] == 24
    assert (
        the_dig["placement"]["marker_dimensions"][0]["citation"]["source_version"]
        == "2026.09.11"
    )
    status, _, double_bind = _json(
        app, "/api/scenarios/double-bind?army_points=300"
        "&collection=its-18&revision=2026.09.11",
    )
    assert status == 200
    assert len(double_bind["objective_selection"]["sets"]) == 3
    assert double_bind["objective_selection"]["sets"][0]["id"] == "encryption"
    assert all(o["awards"] for o in double_bind["objectives"])

    assert registry.source_citation(
        season_id="its-18", source_id="its-season-18-en-pdf",
        revision="2026.09.11", page=17,
    )["source_version"] == "2026.09.11"


def test_mislabeled_revision_and_duplicate_registration_fail_closed(tmp_path: Path) -> None:
    hotfix = tmp_path / "hotfix.db"
    build_its_database(HOTFIX_SOURCE, hotfix)
    rules = RulesDatabase(RELEASE / "rules_n5.db")
    with pytest.raises(ValueError, match="registration does not match"):
        PublicationRegistry(rules, {"its-18@2026.09.01": hotfix})
    with pytest.raises(ValueError, match="Duplicate registered ITS season/revision"):
        PublicationRegistry(rules, {
            "its-18": hotfix,
            "its-18@2026.09.11": hotfix,
        })
