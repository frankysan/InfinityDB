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
    with pytest.raises(ValueError, match="Skill content"):
        inspect_its_database(copied)
