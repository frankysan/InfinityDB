"""Season-wide ITS Skills are published independently of scenario actions."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import build_its_database, inspect_its_database
from infinity_db.its_source_family import project_its_source_family
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/curated/its/n5-its-season-18.json"
GENERATED = ROOT / "data/generated"
IDS = {"civevac", "casevac", "team-ops", "request-tacball"}


@pytest.fixture(scope="module")
def published(tmp_path_factory: pytest.TempPathFactory):
    path = tmp_path_factory.mktemp("its-season-skills") / "its_18.db"
    report = build_its_database(SOURCE, path)
    app = create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db",
        season_databases={"its-18": path},
    )
    return path, report, app


def _get(app, path: str):
    status, _, content = wsgi_response(app, "https://its-skills.example" + path)
    return status, json.loads(content)


def test_four_season_skills_keep_types_and_optional_extra_scope(published) -> None:
    _, report, app = published
    assert {item["id"].removeprefix("skill:") for item in report["skills"]} == IDS
    status, payload = _get(app, "/api/skills")
    assert status == 200
    items = {item["slug"]: item for item in payload["items"] if item["slug"] in IDS}
    assert set(items) == IDS
    assert {slug: item["category"] for slug, item in items.items()} == {
        "civevac": "Common Skills",
        "casevac": "Common Skills",
        "team-ops": "Special Skills",
        "request-tacball": "Special Skills",
    }
    expected = {
        "civevac": ("basic-short-skill", "season", [22, 23]),
        "casevac": ("short-skill", "season", [25, 26]),
        "team-ops": ("automatic", "team-ops-extra", [29, 30]),
        "request-tacball": ("short-skill", "team-ops-extra", [30, 31]),
    }
    for slug, (kind, context, pages) in expected.items():
        assert "scenario" not in items[slug]
        assert items[slug]["categories"][0]["id"] == kind
        status, detail = _get(app, f"/api/skills/{slug}")
        assert status == 200
        assert detail["rules"][0]["scope"] == {"game": "N5", "seasons": ["its-18"]}
        assert detail["rules"][0]["facts"]["applicability"] == {
            "context": context, "revision": "2026.09.11",
        }
        assert [citation["page"] for citation in detail["rules"][0]["citations"]] == pages
        assert detail["rules"][0]["facts"]["requirements"]
        assert detail["rules"][0]["facts"]["effects"]
        assert detail["rules"][0]["facts"]["restrictions"]
        assert detail["rules"][0]["name"] == items[slug]["name"]
    for term, slug in (("civevac", "civevac"), ("casevac", "casevac"),
                       ("team-ops", "team-ops"), ("tacball", "request-tacball")):
        status, search = _get(app, f"/api/search?q={term}")
        assert status == 200
        assert any(item["href"] == f"/skills/{slug}" for item in search["items"])


def test_civevac_capacity_is_scenario_scoped_not_a_global_rewrite() -> None:
    """Outbreak's one-Infected exception must not replace general CivEvac."""
    document = project_its_source_family(load_curated_document(SOURCE))
    records = {record["id"]: record for record in document["records"]}
    general = records["skill:civevac"]
    assert general["facts"]["applicability"]["context"] == "season"
    assert any("at most two Civilians" in effect
               for effect in general["facts"]["effects"])

    outbreak_rules = records["scenario:outbreak"]["facts"]["mission"]["rules"]
    infected = next(rule for rule in outbreak_rules if rule["id"] == "infected-placement")
    assert any("at most one Infected" in text for text in infected["paragraphs"])

    evacuation_rules = records["scenario:evacuation"]["facts"]["mission"]["rules"]
    civilians = next(rule for rule in evacuation_rules if rule["id"] == "civilians")
    assert any("applicable CivEvac rules" in text for text in civilians["paragraphs"])
    assert all("at most one Infected" not in text
               for rule in evacuation_rules for text in rule["paragraphs"])


def test_historical_skill_page_pins_are_revision_specific() -> None:
    document = load_curated_document(SOURCE)
    current = project_its_source_family(document)
    archived = project_its_source_family(document, revision="2026.09.01")
    current_skills = {item["id"]: item for item in current["records"]
                      if item["kind"] == "skill"}
    archived_skills = {item["id"]: item for item in archived["records"]
                       if item["kind"] == "skill"}
    assert set(current_skills) == set(archived_skills) == {
        f"skill:{slug}" for slug in IDS
    }
    for identifier, skill in current_skills.items():
        previous = archived_skills[identifier]
        assert skill["facts"]["applicability"]["revision"] == "2026.09.11"
        assert previous["facts"]["applicability"]["revision"] == "2026.09.01"
        assert [cite["page"] - 1 for cite in skill["citations"]] == [
            cite["page"] for cite in previous["citations"]
        ]
        assert skill["facts"]["requirements"] == previous["facts"]["requirements"]
        assert skill["facts"]["effects"] == previous["facts"]["effects"]


@pytest.mark.parametrize(("mutation", "error"), [
    ("context", "applicability"),
    ("revision", "applicability"),
    ("scenario", "must not acquire scenario"),
    ("type", "referencing skillTypes"),
    ("category", "must be Common or Special"),
])
def test_bad_season_skill_fails_before_publication(
    tmp_path: Path, mutation: str, error: str,
) -> None:
    original = project_its_source_family(load_curated_document(SOURCE))
    record = next(item for item in original["records"] if item["id"] == "skill:civevac")
    if mutation == "context":
        record["facts"]["applicability"]["context"] = "unsupported"
    elif mutation == "revision":
        record["facts"]["applicability"]["revision"] = "2026.09.01"
    elif mutation == "scenario":
        record["scope"]["scenarios"] = ["scenario:evacuation"]
    elif mutation == "type":
        record["facts"]["typeIds"] = ["long-skill"]
    else:
        record["facts"]["category"] = "scenario-skill"
    source = tmp_path / "bad.json"
    source.write_text(json.dumps(original, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        build_its_database(source, tmp_path / "bad.db")


def test_skills_are_source_hashed_and_reject_sqlite_tampering(
    published, tmp_path: Path,
) -> None:
    output, report, _ = published
    copied = tmp_path / "tampered.db"
    copied.write_bytes(output.read_bytes())
    original = inspect_its_database(copied, source=SOURCE)
    assert original["skills"] == report["skills"]
    with sqlite3.connect(copied) as db:
        db.execute(
            "UPDATE records SET payload_json=? WHERE id='skill:civevac'",
            ('{"id":"skill:civevac"}',),
        )
    with pytest.raises(ValueError, match="record content"):
        inspect_its_database(copied)


def test_casevac_state_is_published_once_with_reciprocal_skill_links(published) -> None:
    _, report, app = published
    assert {row["id"] for row in report["states"]} == {"state:casevac"}
    status, states = _get(app, "/api/states")
    assert status == 200
    casevac, = [entry for entry in states["items"] if entry["slug"] == "casevac"]
    assert casevac["name"] == "Casevac State"
    assert casevac["season"] == {"collection": "its-18", "revision": "2026.09.11"}

    status, detail = _get(app, "/api/states/casevac")
    assert status == 200
    state = detail["rules"][0]
    assert state["id"] == "state:casevac"
    assert state["kind"] == "state"
    assert state["facts"]["applicability"] == {
        "context": "season", "revision": "2026.09.11",
    }
    assert [pin["page"] for pin in state["citations"]] == [25, 26]
    assert all(pin["source_version"] == "2026.09.11" for pin in state["citations"])
    assert any("Impetuous Phase" in effect for effect in state["facts"]["effects"])
    assert any("Template Weapons Into Close Combat" in effect
               for effect in state["facts"]["effects"])
    assert any("Short Skill" in effect and "voluntarily" in effect
               for effect in state["facts"]["effects"])

    skill_links = [
        token for group in state["fact_tokens"]["requirements"]
        for token in group if token["type"] == "reference"
    ]
    assert any(token["target"] == "skill:casevac"
               and token["public_reference"] in (
                   {"href": "/skills/casevac"}, {"catalog": "skills", "id": "casevac"}
               )
               for token in skill_links)

    status, skill = _get(app, "/api/skills/casevac")
    assert status == 200
    state_links = [
        token for group in skill["rules"][0]["fact_tokens"]["effects"]
        for token in group if token["type"] == "reference"
    ]
    assert any(token["target"] == "state:casevac"
               and token["public_reference"] in (
                   {"href": "/states/casevac"}, {"catalog": "states", "id": "casevac"}
               )
               for token in state_links)

    status, search = _get(app, "/api/search?q=casevac")
    assert status == 200
    assert {"/skills/casevac", "/states/casevac"} <= {
        entry["href"] for entry in search["items"]
    }


def test_casevac_state_has_historical_source_pages_but_only_current_route() -> None:
    document = load_curated_document(SOURCE)
    current = project_its_source_family(document)
    old = project_its_source_family(document, revision="2026.09.01")
    current_state, = [record for record in current["records"]
                      if record["id"] == "state:casevac"]
    historical, = [record for record in old["records"]
                   if record["id"] == "state:casevac"]
    assert [c["page"] for c in current_state["citations"]] == [25, 26]
    assert [c["page"] for c in historical["citations"]] == [24, 25]
    assert current_state["facts"]["applicability"]["revision"] == "2026.09.11"
    assert historical["facts"]["applicability"]["revision"] == "2026.09.01"
    assert current_state["facts"]["effects"] == historical["facts"]["effects"]


@pytest.mark.parametrize(("mutation", "message"), [
    ("context", "applicability"),
    ("revision", "applicability"),
    ("missing-effects", "complete typed State facts"),
    ("empty-effect", "effects"),
    ("wrong-category", "state category"),
    ("scenario", "core or scenario scope"),
])
def test_invalid_casevac_state_is_not_published(
    tmp_path: Path, mutation: str, message: str,
) -> None:
    source = project_its_source_family(load_curated_document(SOURCE))
    state = next(item for item in source["records"] if item["id"] == "state:casevac")
    if mutation == "context":
        state["facts"]["applicability"]["context"] = "team-ops-extra"
    elif mutation == "revision":
        state["facts"]["applicability"]["revision"] = "2026.09.01"
    elif mutation == "missing-effects":
        state["facts"].pop("effects")
    elif mutation == "empty-effect":
        state["facts"]["effects"][0] = ""
    elif mutation == "wrong-category":
        state["facts"]["category"] = "skill"
    else:
        state["scope"]["scenarios"] = ["scenario:evacuation"]
    file = tmp_path / "invalid-state.json"
    file.write_text(json.dumps(source, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        build_its_database(file, tmp_path / "invalid.db")


def test_state_sqlite_tampering_is_detected(published, tmp_path: Path) -> None:
    output, _, _ = published
    copied = tmp_path / "tampered-state.db"
    copied.write_bytes(output.read_bytes())
    with sqlite3.connect(copied) as connection:
        connection.execute(
            "UPDATE records SET payload_json=? WHERE id='state:casevac'",
            ('{"id":"state:casevac"}',),
        )
    with pytest.raises(ValueError, match="record content"):
        inspect_its_database(copied)
