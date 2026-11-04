"""V1S-032C1 source-scoped Game Sequence and Order Pool publication tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools.promote_turn_sequence_reference import (
    CITATIONS,
    EN,
    ES,
    IDENTITIES,
    verify_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES = ROOT / "data/generated/rules.db"
ARMY = ROOT / "data/generated/infinity.db"


def _get(app: Any, path: str, query: str = "") -> tuple[str, bytes]:
    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, QUERY_STRING=query, REQUEST_METHOD="GET")
    statuses: list[str] = []
    response = app(environ, lambda status, _headers, _exc=None: statuses.append(status))
    try:
        result = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    return statuses[0], result


def _records() -> dict[str, dict[str, Any]]:
    return {
        record["id"]: record for record in load_curated_document(CORE)["records"]
    }


def test_game_sequence_has_five_phases_and_source_ordered_tactical_checks() -> None:
    record = _records()["rule:game-sequence"]
    assert record["name"] == "Game Sequence"
    assert record["facts"]["category"] == "basic-rule"
    effects = record["facts"]["effects"]
    assert len(effects) == 5
    for index, phase in enumerate((
        "Tactical Phase", "Impetuous", "Orders Phase", "States", "End of the Turn",
    ), start=1):
        assert effects[index - 1].startswith(f"**{index}. "), phase
        assert phase in effects[index - 1]
    tactical = effects[0]
    positions = [
        tactical.index(key) for key in (
            "Executive Use", "Retreat!", "Loss of Lieutenant", "Order Count",
        )
    ]
    assert positions == sorted(positions)
    states = effects[3]
    for key in ("both players", "do not generate", "ARO", "Order Tokens"):
        assert key in states
    for phrase in ("cannot be saved for a later Turn", "not required to spend all Orders"):
        assert phrase in record["facts"]["restrictions"][0]
    assert {(c["sourceId"], c["page"]) for c in record["citations"]} == (
        CITATIONS[record["id"]]
    )


def test_order_pool_has_distinct_order_owners_and_source_discrepancy() -> None:
    record = _records()["rule:order-pool"]
    assert record["facts"]["category"] == "basic-rule"
    reqs = record["facts"]["requirements"]
    assert len(reqs) == 4
    assert all(word in reqs[0] for word in ("Regular", "Model or Marker", "Null"))
    assert "Irregular" in reqs[1] and "not part of the Regular Order Pool" in reqs[1]
    assert "SRC-031" in reqs[2] and "Teniente en estado no Nulo" in reqs[2]
    assert "not in a non-Null" in reqs[2]
    assert "not** been officially corrected" in reqs[2]
    assert "Tactical Awareness" in reqs[3]
    details = " ".join(record["facts"]["effects"])
    for key in (
        "separate", "same Trooper repeatedly", "Open Information",
        "Private Information", "lost", "Hidden Deployment",
    ):
        assert key.casefold() in details.casefold(), key
    assert "SRC-031" in record["facts"]["sourceNotes"][0]
    assert {(c["sourceId"], c["page"]) for c in record["citations"]} == (
        CITATIONS[record["id"]]
    )


def test_two_new_references_match_rules_database_and_normal_web_api() -> None:
    app = create_app(ARMY, rules_database_path=RULES)
    published = RulesDatabase(RULES)
    records = _records()
    for identity in sorted(IDENTITIES):
        record = records[identity]
        composed = published.composed_record(identity)
        assert composed is not None
        assert composed["summary"] == record["summary"]
        assert composed["facts"] == record["facts"]
        assert {(c["source_id"], c["page"]) for c in composed["citations"]} == (
            CITATIONS[identity]
        )
        slug = identity.partition(":")[2]
        for path in ("/rules", f"/rules/{slug}"):
            status, body = _get(app, path)
            assert status == "200 OK", path
            assert b"<html" in body.lower()
        status, body = _get(app, f"/api/rules/{slug}")
        assert status == "200 OK"
        assert json.loads(body)["rules"][0]["id"] == identity
        status, body = _get(app, "/api/search", f"q={slug.replace('-', '+')}")
        assert status == "200 OK"
        assert any(
            item.get("href") == f"/rules/{slug}"
            for item in json.loads(body)["items"]
        ), slug


def test_published_turn_sequence_release_pair_rebuilds_deterministically() -> None:
    if not EN.is_file() or not ES.is_file() or not (ROOT / "local").is_dir():
        pytest.skip("Pinned bilingual source and ignored local staging not available")
    report = verify_candidate()
    assert report["identities"] == sorted(IDENTITIES)
    assert report["alreadyPublished"] is True
    assert report["existingRecordsUnchanged"] == report["candidateRecords"] == 486
    assert report["deterministic"] and report["matchedPublication"]
    assert report["candidateRulesSha256"] == (
        "871a76f8fb69c4d4f9ba9120494635713cdc4970a79b448c191d83cff08a42ea"
    )
