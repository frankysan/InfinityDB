import json
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.state_catalog import StateCatalog
from infinity_db.web import create_app
from tools.verify_states_browser import source_states


def test_state_catalog_exposes_reviewed_states_and_reverse_relations(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = StateCatalog(RulesDatabase(rules_path))

    states = {item["id"]: item for item in catalog.list_states()}
    assert len(states) == 24
    assert {
        "dead",
        "engaged",
        "holoecho",
        "holomask",
        "normal",
        "prone",
        "possessed",
        "retreat",
        "sepsitorized",
        "suppressive-fire",
    } <= states.keys()
    assert "unconscious" in states
    assert "immobilized-a" in states
    assert "targeted" in states
    assert "unloaded" in states
    assert states["unconscious"]["name"] == "Unconscious State"

    unconscious = catalog.get_state("unconscious")
    assert unconscious is not None
    relations = {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in unconscious["rules"][0]["display_relations"]
    }
    assert ("cancels-state", "inbound", "Doctor") in relations
    assert ("cancels-state", "inbound", "Engineer") in relations

    targeted = catalog.get_state("targeted")
    assert targeted is not None
    assert ("cancels-state", "inbound", "Engineer") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in targeted["rules"][0]["display_relations"]
    }

    unloaded = catalog.get_state("unloaded")
    assert unloaded is not None
    assert ("causes-state", "inbound", "Disposable (X)") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in unloaded["rules"][0]["display_relations"]
    }

    suppressive_fire = catalog.get_state("suppressive-fire")
    assert suppressive_fire is not None
    suppressive_relations = {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in suppressive_fire["rules"][0]["display_relations"]
    }
    assert ("enters-state", "inbound", "skill:suppressive-fire") in suppressive_relations
    assert ("cancels-state", "inbound", "state:dead") in suppressive_relations
    assert ("cancels-state", "inbound", "state:retreat") in suppressive_relations


def test_isolated_state_fireteam_and_coordinated_order_navigation_source_boundary(
    tmp_path: Path,
) -> None:
    """Pin reviewed context without equating membership with generic rule use."""
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data/curated"), rules_path)
    database = RulesDatabase(rules_path)
    database.validate()

    isolated = StateCatalog(database).get_state("isolated")
    assert isolated is not None
    state = isolated["rules"][0]
    assert state["id"] == "state:isolated"
    assert any(
        "cannot be part of a Fireteam or take part in a Coordinated Order" in fact
        for fact in state["facts"]["restrictions"]
    )
    assert any(
        "becomes Irregular in following Active Turns" in fact
        for fact in state["facts"]["effects"]
    )
    assert {item["record_id"] for item in state["display_relations"]} >= {
        "skill:reset", "skill:engineer"
    }

    fireteam = database.composed_record("rule:fireteam-general")
    coordinated = database.composed_record("rule:coordinated-orders")
    assert fireteam is not None and coordinated is not None
    fireteam_rules = fireteam["facts"]["rules"]
    assert any(
        "[[state:isolated|Isolated]]" in fact and "**Whole Fireteam cancellation:**" in fact
        for fact in fireteam_rules
    )
    assert any(
        "[[state:isolated|Isolated]]" in fact and "**Individual departure:**" in fact
        for fact in fireteam_rules
    )
    assert any(
        "Members must observe Coherency" in fact for fact in fireteam_rules
    )
    assert any(
        "same Training (Regular or Irregular)" in fact
        for fact in coordinated["facts"]["requirements"]
    )
    assert any(
        "Members of a Fireteam" in fact
        for fact in coordinated["facts"]["restrictions"]
    )
    # A shared Order-generation Training is not proof that an Isolated
    # Trooper may participate; no live-session eligibility is inferred.
    assert state["kind"] == "state"
    assert all(
        relation["type"] != "causes-state"
        for relation in state.get("relations", ())
    )


def test_every_current_state_reaches_published_api_and_player_template() -> None:
    """Check every canonical State's source/storage/API identity and cited facts."""

    root = Path(__file__).parents[1]
    source = {
        record["id"]: (document["collection"]["id"], record)
        for _, document in load_curated_directory(root / "data/curated")
        if document["collection"]["status"] == "current"
        for record in document["records"]
        if record["kind"] == "state"
    }
    assert len(source) == 24
    assert source_states(root) == {
        record_id.removeprefix("state:"): record["name"]
        for record_id, (_, record) in source.items()
    }

    rules_path = root / "data/generated/rules.db"
    with sqlite3.connect(rules_path) as connection:
        stored = list(connection.execute(
            "SELECT r.collection_id, r.id, r.name, r.summary, r.facts_json "
            "FROM records AS r JOIN collections AS c ON c.id = r.collection_id "
            "WHERE c.status = 'current' AND r.kind = 'state'"
        ))
    assert {record_id for _, record_id, *_ in stored} == set(source)
    for collection_id, record_id, name, summary, facts in stored:
        expected_collection, record = source[record_id]
        assert (collection_id, name, summary, json.loads(facts or "{}")) == (
            expected_collection, record["name"], record["summary"], record.get("facts", {})
        ), record_id

    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_path)

    def get(path: str) -> tuple[str, bytes]:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []
        response = app(
            environ,
            lambda status, _headers, _exc_info=None: statuses.append(status),
        )
        try:
            body = b"".join(response)
        finally:
            close = getattr(response, "close", None)
            if close is not None:
                close()
        assert len(statuses) == 1, path
        return statuses[0], body

    status, body = get("/api/states")
    assert status == "200 OK"
    listed = json.loads(body)["items"]
    assert len(listed) == 24
    assert {f"state:{row['slug']}" for row in listed} == set(source)
    assert len({row["slug"] for row in listed}) == len(listed)

    status, body = get("/states")
    assert status == "200 OK"
    assert b'data-catalog="states"' in body
    assert b"/static/catalog-list.js" in body

    for record_id, (_, record) in sorted(source.items()):
        slug = record_id.removeprefix("state:")
        listed_item = next(row for row in listed if row["slug"] == slug)
        assert (listed_item["name"], listed_item["description"]) == (
            record["name"], record["summary"]
        ), record_id

        status, body = get(f"/api/states/{slug}")
        assert status == "200 OK", record_id
        detail = json.loads(body)
        assert (detail["slug"], detail["name"], detail["description"]) == (
            slug, record["name"], record["summary"]
        ), record_id
        assert len(detail["rules"]) == 1, record_id
        rule = detail["rules"][0]
        assert (rule["id"], rule["summary"]) == (
            record_id, record["summary"]
        ), record_id
        assert rule.get("facts", {}) == record.get("facts", {}), record_id
        assert rule["citations"], record_id
        assert {citation["source_id"] for citation in rule["citations"]} >= {
            citation["sourceId"] for citation in record["citations"]
        }, record_id

        status, body = get(f"/states/{slug}")
        assert status == "200 OK", record_id
        assert b'data-catalog="states"' in body
        assert b"/static/catalog-detail.js" in body
        assert b'id="item-content"' in body

    script = (root / "src/infinity_db/web/static/catalog-detail.js").read_text(
        encoding="utf-8"
    )
    assert "rulesReferenceSection(rules)" in script
    assert "content.hidden = false;" in script
    assert "if (catalog === \"states\") return null;" in script


def test_state_catalog_caches_composed_records_and_isolates_detail_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules = RulesDatabase(rules_path)
    original = rules.composed_records_by_kind
    calls = 0

    def composed_records_by_kind(kind: str) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        return original(kind)

    monkeypatch.setattr(rules, "composed_records_by_kind", composed_records_by_kind)
    catalog = StateCatalog(rules)

    catalog.list_states()
    first = catalog.get_state("unconscious")
    second = catalog.get_state("unconscious")

    assert calls == 1
    assert first is not None
    assert second is not None
    first["rules"][0]["name"] = "mutated"
    assert second["rules"][0]["name"] == "Unconscious State"
    third = catalog.get_state("unconscious")
    assert third is not None
    assert third["rules"][0]["name"] == "Unconscious State"


def test_state_catalog_without_rules_is_empty() -> None:
    catalog = StateCatalog(None)
    assert catalog.list_states() == []
    assert catalog.get_state("unconscious") is None
