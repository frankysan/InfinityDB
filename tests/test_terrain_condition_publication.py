"""V1S-033D optional Difficult Terrain and Saturation source/publication gates."""

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
from tools import promote_terrain_condition_reference
from tools.promote_terrain_condition_reference import CITATIONS, verify_candidate

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5.3-en.pdf"


def _records() -> dict[str, Any]:
    doc = load_curated_document(ROOT / "data/curated/rules/n5-core-v5.3.json")
    return {item["id"]: item for item in doc["records"]}


def _text(record: dict[str, Any]) -> str:
    return " ".join([record["summary"], *[
        text for key in ("requirements", "effects", "restrictions", "clarifications")
        for text in record["facts"].get(key, [])
    ]])


def _get(app: Any, path: str, query: str = "") -> tuple[str, bytes]:
    env: dict[str, Any] = {}
    setup_testing_defaults(env)
    env.update(PATH_INFO=path, QUERY_STRING=query, REQUEST_METHOD="GET")
    statuses: list[str] = []
    response = app(env, lambda status, _headers, _exc=None: statuses.append(status))
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    return statuses[0], body


def test_terrain_conditions_pin_complete_optional_pdf_clauses() -> None:
    if not PDF.is_file():
        pytest.skip("Pinned N5.3 PDF unavailable")
    pymupdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    with pymupdf.open(PDF) as pdf:
        for page, clauses in {
            143: ("these rules are optional", "must be agreed by players",
                  "each Special Terrain must have", "at least one other characteristic"),
            144: ("Difficult Terrain also affects Troopers", "for the rest of the Order",
                  "apply a MOD of -1", "to both values of their MOV Attribute",
                  "Any BS Attack from, into, or through", "after dividing the Burst",
                  "cannot be reduced below 1", "never stack with MODs"),
            145: ("SUGGESTIONS AND EXAMPLES", "ACCESS WIDTH"),
        }.items():
            text = " ".join(pdf[page - 1].get_text().split()).casefold()
            for clause in clauses:
                assert clause.casefold() in text, (page, clause)


def test_terrain_conditions_keep_distinct_timing_exemptions_and_owners() -> None:
    records = _records()
    difficult = records["rule:difficult-terrain"]
    saturation = records["rule:saturation"]
    assert difficult["aliases"] == ["Difficult Movement"]
    assert saturation["aliases"] == ["Saturation Zone"]
    for item in (difficult, saturation):
        assert item["kind"] == "rule"
        assert item["facts"]["category"] == "basic-rule"
        assert item["scope"] == {"game": "N5", "seasons": ["current"]}
        assert not item.get("relations")
    movement = _text(difficult)
    for phrase in ("immediately ends", "remainder of that Order", "declare a new Order",
                   "-1 inch", "both values", "value of the declared Skill",
                   "[[skill:terrain|Terrain Special Skill]]", "not a permanent adjustment"):
        assert phrase in movement, phrase
    burst = _text(saturation)
    for phrase in ("from, into or through", "Divide the attack's Burst", "after",
                   "assigned to each affected target", "below 1", "Nonstacking",
                   "not a change to a Weapon's printed Burst", "optional"):
        assert phrase in burst, phrase
    assert "Difficult Terrain" in _text(records["rule:special-terrain"])
    assert "Saturation" in _text(records["rule:special-terrain"])
    assert "matching Terrain areas" in _text(records["skill:terrain"])
    assert "terrain-type-applicability" in json.dumps(records["skill:terrain"]["variantSemantics"])
    assert records["rule:access-width"]["facts"]["category"] == "basic-rule"


def test_terrain_conditions_storage_api_search_and_citations() -> None:
    app = create_app(ROOT / "data/generated/infinity.db", rules_database_path=RULES)
    db = RulesDatabase(RULES)
    records = _records()
    for identity, pages in CITATIONS.items():
        source = records[identity]
        published = db.composed_record(identity)
        assert published is not None
        assert published["summary"] == source["summary"]
        assert published["facts"] == source["facts"]
        assert {cite["page"] for cite in published["citations"]
                if cite["source_id"] == "n5-core-v5.3-pdf"} == pages
        domain = "skills" if identity.startswith("skill:") else "rules"
        slug = identity.partition(":")[2]
        status, body = _get(app, f"/api/{domain}/{slug}")
        assert status == "200 OK" and json.loads(body)["rules"][0]["id"] == identity
        status, _ = _get(app, f"/{domain}/{slug}")
        assert status == "200 OK"
    for identity in ("rule:difficult-terrain", "rule:saturation"):
        name = records[identity]["name"]
        status, body = _get(app, "/api/search", "q=" + name.replace(" ", "+"))
        assert status == "200 OK"
        assert any(item.get("href") == "/rules/" + identity.partition(":")[2]
                   for item in json.loads(body)["items"])


def test_terrain_conditions_matched_pair_guard_and_repeated_promotion_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not PDF.is_file() or not (ROOT / "local").is_dir():
        pytest.skip("Pinned PDF or ignored recovery path unavailable")
    objects = ROOT / "data/generated/deployed-objects.json"
    original = RULES.read_bytes(), objects.read_bytes()
    report = verify_candidate()
    assert report["alreadyPublished"] and report["deterministic"]
    assert report["matchedPublication"] and report["logicallyEquivalentWithPublished"]
    assert report["candidateRecords"] >= 498
    with pytest.raises(ValueError, match="repeated terrain-condition promotion"):
        verify_candidate(promote=True)
    monkeypatch.setattr(promote_terrain_condition_reference,
                        "load_deployed_object_publication", lambda *_args: None)
    with pytest.raises(ValueError, match="publication does not match"):
        verify_candidate()
    assert (RULES.read_bytes(), objects.read_bytes()) == original
