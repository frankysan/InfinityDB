"""Accepted core ARO and Deployment source, Rules and API regressions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES = ROOT / "data/generated/rules.db"
ARMY = ROOT / "data/generated/infinity.db"
PDF = Path("data/pdf/rules/n5-rules-v5.3-en.pdf")
SOURCE_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
NEW_ID = "rule:automatic-reaction-order"
CHANGED_ID = "rule:deployment-phase"
CITATIONS = {
    NEW_ID: {("n5-core-v5.3-pdf", 13), ("n5-core-v5.3-pdf", 14)},
    CHANGED_ID: {("n5-core-v5.3-pdf", 15), ("n5-core-v5.3-pdf", 16)},
}


def _get(app: Any, route: str, query: str = "") -> tuple[str, bytes]:
    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=route, QUERY_STRING=query, REQUEST_METHOD="GET")
    statuses: list[str] = []
    response = app(environ, lambda status, _headers, _exc=None: statuses.append(status))
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    return statuses[0], body


def _records() -> dict[str, dict[str, Any]]:
    records = load_curated_document(CORE)["records"]
    assert all(sum(row["id"] == identity for row in records) == 1
               for identity in CITATIONS)
    return {record["id"]: record for record in records}


def test_n5_3_core_aro_and_deployment_clauses_match_pinned_source() -> None:
    file = ROOT / PDF
    if not file.is_file():
        pytest.skip("Pinned English N5.3 PDF not available on this worker")
    pymupdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(file.read_bytes()).hexdigest() == SOURCE_SHA256
    clauses = {
        13: (
            "An enemy Trooper activates within its Line of Fire",
            "An enemy Trooper activates within its Zone of Control",
            "It has a Special Skill, weapon, or piece of Equipment",
            "It is affected by a Template Weapon, or is the target of a Comms",
            "each eligible enemy Trooper gets one single ARO",
            "target of an ARO must always be one of the Troopers",
            "Troopers may not react to AROs",
            "AROs always have Burst B1",
            "cannot split it amongst different targets",
        ),
        14: (
            "All AROs are also simultaneous",
            "ARO Check",
            "ARO Declaration",
            "they forfeit their right to declare an ARO",
        ),
        15: ("DEPLOYMENT PHASE", "Player One Deployment", "Player Two Last Trooper"),
        16: (
            "The base of each Trooper must be totally inside the Deployment Zone",
            "Troopers cannot be deployed in contact with enemy and neutral",
            "or in contact with any mission objective",
            "When a Trooper deploys, its owner can choose to deploy it Prone",
            "Troopers cannot deploy in a location without enough space",
            "Players can measure the size of the Deployment Zones",
        ),
    }
    with pymupdf.open(file) as pdf:
        for page, excerpts in clauses.items():
            source = " ".join(pdf[page - 1].get_text().split()).casefold()
            for excerpt in excerpts:
                assert " ".join(excerpt.split()).casefold() in source, (page, excerpt)


def test_aro_reference_enforces_all_four_eligibility_families_and_limits() -> None:
    aro = _records()[NEW_ID]
    assert aro["name"] == "Automatic Reaction Order"
    assert aro["kind"] == "rule" and aro["facts"]["category"] == "basic-rule"
    assert len(aro["facts"]["requirements"]) == 4
    requirements = " ".join(aro["facts"]["requirements"])
    for phrase in ("Line of Fire", "Zone of Control", "Hacking Area",
                   "without LoF or ZoC", "Template Weapon", "Comms Attack"):
        assert phrase in requirements
    facts = " ".join(
        aro["facts"][key][index]
        for key in ("effects", "restrictions")
        for index in range(len(aro["facts"][key]))
    )
    for term in ("single", "activated by the Order", "Burst B1",
                 "cannot split", "forfeit", "simultaneous", "second Check",
                 "not a second", "not automatically reactive"):
        assert term in facts, term
    assert "does not evaluate" in facts
    assert {(c["sourceId"], c["page"]) for c in aro["citations"]} == CITATIONS[NEW_ID]


def test_existing_deployment_reference_includes_page_16_without_losing_sequence() -> None:
    record = _records()[CHANGED_ID]
    assert record["name"] == "Deployment Phase"
    summary = record["summary"]
    assert "first player's main force" in summary
    assert "second player's main force" in summary
    assert "first player's reserved" in summary
    assert "second player's reserved" in summary
    source_facts = " ".join(
        record["facts"][key][index]
        for key in ("requirements", "effects", "restrictions")
        for index in range(len(record["facts"][key]))
    )
    for clause in (
        "entire base totally inside", "cannot be deployed in contact",
        "enemy or Neutral", "any mission objective", "whole base",
        "Prone", "central line", "Exclusion Zone", "Forward Deployment",
        "Unless both players previously agree",
    ):
        assert clause in source_facts, clause
    assert {(c["sourceId"], c["page"]) for c in record["citations"]} == (
        CITATIONS[CHANGED_ID]
    )


def test_public_aro_and_deployment_routes_preserve_source_prose() -> None:
    app = create_app(ARMY, rules_database_path=RULES)
    source = _records()
    rules = RulesDatabase(RULES)
    for identity in (NEW_ID, CHANGED_ID):
        record = source[identity]
        assert record["kind"] == "rule"
        assert record["composition"] == {"role": "definition"}
        assert record["scope"] == {"game": "N5", "seasons": ["current"]}
        assert record["facts"]["category"] == "basic-rule"
        assert {(c["sourceId"], c["page"]) for c in record["citations"]} == CITATIONS[identity]
        published = rules.composed_record(identity)
        assert published is not None
        assert published["summary"] == record["summary"]
        assert published["facts"] == record["facts"]
        assert {(c["source_id"], c["page"]) for c in published["citations"]} == (
            CITATIONS[identity]
        )
        slug = identity.partition(":")[2]
        for path in ("/rules", f"/rules/{slug}"):
            status, body = _get(app, path)
            assert status == "200 OK" and b"<html" in body.lower(), path
        status, body = _get(app, f"/api/rules/{slug}")
        assert status == "200 OK"
        assert json.loads(body)["rules"][0]["id"] == identity
        status, body = _get(app, "/api/search", f"q={slug.replace('-', '+')}")
        assert status == "200 OK"
        assert any(item.get("href") == f"/rules/{slug}"
                   for item in json.loads(body)["items"])
    status, body = _get(app, "/api/orders-aros")
    assert status == "200 OK"
    assert json.loads(body)["legalityEvaluation"] is False