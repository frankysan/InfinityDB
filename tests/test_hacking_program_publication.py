"""Whole-publication parity checks for Army-backed Hacking Programs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

from infinity_db.curated import load_curated_directory
from infinity_db.database.repository import Database
from infinity_db.domain_slugs import assign_domain_slugs
from infinity_db.hacking_program_catalog import hacking_program_declaration_categories
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools.verify_hacking_programs_browser import WIDTHS, source_programs

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"


def _get(app: Any, path: str) -> tuple[str, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def respond(status: str, _headers: list, _exc_info: object = None) -> None:
        statuses.append(status)

    response = app(environ, respond)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1, path
    return statuses[0], body


def test_all_published_hacking_programs_match_army_and_curated_rules() -> None:
    """Check Army profile facts, rule identities, and normal HTTP publication."""

    with sqlite3.connect(ARMY_DB) as connection:
        army_rows = list(connection.execute(
            "SELECT position, name, attack_mod, opponent_mod, ps, burst, special, "
            "source_extra_id FROM application_hacking_programs ORDER BY position"
        ))
    source_rows = Database(ARMY_DB).list_hacking_programs()
    assert len(source_rows) == len(army_rows) == 12
    for row, source in zip(army_rows, source_rows, strict=True):
        assert tuple(source[field] for field in (
            "position", "name", "attack_mod", "opponent_mod", "ps",
            "burst", "special", "source_extra_id"
        )) == row

    slugs = assign_domain_slugs(
        ((int(row["position"]), row["name"]) for row in source_rows),
        domain="hacking-programs",
    )
    expected_by_slug = {slugs[int(row["position"])]: row for row in source_rows}
    assert len(expected_by_slug) == len(source_rows)
    assert source_programs(ROOT) == expected_by_slug
    assert WIDTHS == (1440, 390, 320)

    curated = {
        record["id"].removeprefix("hacking-program:"): record
        for _, document in load_curated_directory(ROOT / "data/curated")
        if document["collection"]["status"] == "current"
        for record in document["records"]
        if record["kind"] == "hacking-program"
    }
    assert curated
    assert set(curated) == set(expected_by_slug), (
        "Unmatched Army Programs or curated Hacking Program semantics"
    )
    with sqlite3.connect(RULES_DB) as connection:
        rules_rows = {
            identity.removeprefix("hacking-program:"): (name, summary, json.loads(facts or "{}"))
            for identity, name, summary, facts in connection.execute(
                "SELECT r.id, r.name, r.summary, r.facts_json FROM records AS r "
                "JOIN collections AS c ON c.id = r.collection_id "
                "WHERE c.status = 'current' AND r.kind = 'hacking-program'"
            )
        }
    assert set(rules_rows) == set(curated)
    for slug, record in curated.items():
        assert rules_rows[slug] == (
            record["name"], record["summary"], record.get("facts", {})
        ), slug

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    status, body = _get(app, "/api/hacking-programs")
    assert status == "200 OK"
    listed = json.loads(body)["items"]
    assert len(listed) == len(expected_by_slug)
    assert {item["slug"] for item in listed} == set(expected_by_slug)
    assert len({item["position"] for item in listed}) == len(listed)
    status, body = _get(app, "/hacking-programs")
    assert status == "200 OK"
    assert b'data-catalog="hacking-programs"' in body
    assert b"/static/catalog-list.js" in body

    for item in listed:
        slug = item["slug"]
        source = expected_by_slug[slug]
        record = curated[slug]
        assert record["name"] == source["name"], slug
        assert item["id"] == slug
        for field in (
            "position", "name", "attack_mod", "opponent_mod", "ps",
            "burst", "special", "source_extra_id", "targets",
            "skill_types", "devices",
        ):
            assert item[field] == source[field], (slug, field)
        assert item["declaration_categories"] == hacking_program_declaration_categories(
            source["skill_types"]
        ), slug
        assert item["description"] == record["summary"], slug

        status, body = _get(app, f"/api/hacking-programs/{slug}")
        assert status == "200 OK", slug
        detail = json.loads(body)
        for field in (
            "position", "name", "attack_mod", "opponent_mod", "ps",
            "burst", "special", "source_extra_id", "targets",
            "skill_types", "devices", "declaration_categories", "description",
        ):
            assert detail[field] == item[field], (slug, field)
        assert len(detail["rules"]) == 1, slug
        rule = detail["rules"][0]
        assert (rule["id"], rule["summary"], rule.get("facts", {})) == (
            record["id"], record["summary"], record.get("facts", {})
        ), slug
        assert rule["citations"], slug
        assert {citation["source_id"] for citation in rule["citations"]} >= {
            citation["sourceId"] for citation in record["citations"]
        }, slug

        status, body = _get(app, f"/hacking-programs/{slug}")
        assert status == "200 OK", slug
        assert b"/static/hacking-program-detail.js" in body
        assert b'id="item-content"' in body
        assert b'id="item-status"' in body

    javascript = (ROOT / "src/infinity_db/web/static/hacking-program-detail.js").read_text(
        encoding="utf-8"
    )
    assert (
        "rulesReferenceArticle(rule, { leadingContent, headerContent, beforeRelations })"
        in javascript
    )
    assert "programProfileContent(program)" in javascript
    assert "hacking-program-target-scope-note" in javascript
    assert "if (!program.targets?.length)" in javascript
    assert "Consult its rules below" in javascript
    assert {slug for slug, row in expected_by_slug.items() if not row["targets"]} == {
        "controlled-jump", "cybermask", "spotlight", "white-noise", "zero-pain"
    }
    assert "baselineDevicesGroup(program)" in javascript
    assert "content.hidden = false;" in javascript


def test_generated_core_orders_aros_matrix_matches_pinned_source_and_routes() -> None:
    """The browser matrix projects domain metadata, not a second literal chart."""
    from infinity_db.declaration_matrix import core_declaration_matrix

    database = Database(ARMY_DB)
    rules = RulesDatabase(RULES_DB)
    projected = core_declaration_matrix(database, rules)
    assert projected["scope"] == "n5-core-current-unscoped"
    assert projected["legalityEvaluation"] is False
    assert projected["source"] == {"id": "n5-core-v5.3-pdf", "page": 191}

    source = json.loads(
        (ROOT / "config/validation/orders-aro-object-adjacent-source-review.json")
        .read_text(encoding="utf-8")
    )
    section_ids = {
        "basic": "basic-short-skill",
        "long": "long-skill",
        "short": "short-skill",
        "aro": "aro",
    }
    by_section = {
        section["id"]: {item["record_id"]: item for item in section["items"]}
        for section in projected["sections"]
    }
    assert len(by_section) == 4
    expected: dict[str, set[str]] = {key: set() for key in section_ids.values()}
    for source_row in source["rows"]:
        category = section_ids[source_row["section"]]
        expected[category].add(source_row["recordId"])
        item = by_section[category][source_row["recordId"]]
        assert item["name"].removesuffix("!") == source_row["name"].removesuffix("!")
        assert item["source_type"].upper() == source_row["sourceType"]
        assert item["href"].startswith(("/skills/", "/equipment/", "/hacking-programs/"))
    assert {key: set(items) for key, items in by_section.items()} == expected, {
        key: {"additional": sorted(set(items) - expected[key]),
              "missing": sorted(expected[key] - set(items))}
        for key, items in by_section.items()
    }
    for action in ("equipment:deactivator", "equipment:gizmokit", "equipment:medikit"):
        assert action in by_section["short-skill"]
        assert all(
            action not in items for section, items in by_section.items()
            if section != "short-skill"
        )
        # The Equipment Short Skill type is now authored in the current
        # curated definition and carried by rules.db, not a runtime ID list.
        record = rules.composed_record(action)
        assert record is not None
        assert record["facts"]["typeIds"] == ["short-skill"]
        assert [item["id"] for item in record["skill_types"]] == ["short-skill"]
        assert any(
            cite["source_id"] == "n5-core-v5.3-pdf" and cite["page"] == 191
            for cite in record["citations"]
        )

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    status, html = _get(app, "/orders-aros")
    assert status == "200 OK"
    assert b"/static/orders-aros.js" in html
    assert b'aria-current="page"' in html
    status, body = _get(app, "/api/orders-aros")
    assert status == "200 OK"
    assert json.loads(body) == projected
    status, javascript = _get(app, "/static/orders-aros.js")
    assert status == "200 OK"
    assert b"textContent" in javascript
    assert b"getOrdersAros" in javascript
    invalid = app.api.handle("/api/orders-aros", "unexpected=1")
    assert invalid is not None and invalid.status.value == 400
    assert b"Unknown query parameter" in invalid.body
    assert app.api.handle("/api/orders-aros", "cache_bust=1") is not None

    # Neither scenario actions nor source-replacement variants enter the
    # unscoped core projection just because they have a declaration type.
    assert all(
        item["record_id"] not in {"skill:bs-11", "skill:bs-12", "skill:cc-21"}
        for section in projected["sections"] for item in section["items"]
    )
    for section in projected["sections"]:
        assert len({row["record_id"] for row in section["items"]}) == len(section["items"])
