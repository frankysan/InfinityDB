"""Accepted Game Sequence and Order Pool source, Rules, and API regressions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES = ROOT / "data/generated/rules_n5.db"
ARMY = ROOT / "data/generated/army.db"
IDENTITIES = frozenset({"rule:game-sequence", "rule:order-pool"})
CITATIONS = {
    "rule:game-sequence": {
        ("n5-core-v5.3-pdf", 16), ("n5-core-v5.3-pdf", 17),
    },
    "rule:order-pool": {
        ("n5-core-v5.3-pdf", 11), ("n5-core-v5.3-pdf", 12),
        ("n5-core-v5.3-pdf", 16), ("n5-core-v5.3-pdf", 17),
        ("n5-core-v5.3-es-pdf", 17),
    },
}
SOURCE_PINS = (
    ("data/pdf/rules/n5-rules-v5.3-en.pdf",
     "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"),
    ("data/pdf/rules/n5-rules-v5.3-es.pdf",
     "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f"),
)


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
    records = load_curated_document(CORE)["records"]
    assert all(sum(row["id"] == identity for row in records) == 1
               for identity in IDENTITIES)
    return {record["id"]: record for record in records}


@pytest.mark.parametrize("relative,digest", SOURCE_PINS)
def test_turn_sequence_reviewed_source_pins(
    relative: str, digest: str,
    pinned_pdf_sources: Callable[[Mapping[str, str]], dict[str, Path]],
) -> None:
    source = pinned_pdf_sources({relative: digest})[relative]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_game_sequence_has_five_phases_and_source_ordered_tactical_checks() -> None:
    record = _records()["rule:game-sequence"]
    assert record["name"] == "Game Sequence"
    assert record["facts"]["category"] == "basic-rule"
    assert record["composition"] == {"role": "definition"}
    assert record["scope"] == {"game": "N5", "seasons": ["current"]}
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
    assert record["composition"] == {"role": "definition"}
    assert record["scope"] == {"game": "N5", "seasons": ["current"]}
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


def test_accepted_references_match_rules_database_and_normal_web_api() -> None:
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
