"""Pinned V1S-033B geometry procedures and their public reference owners."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults
from zipfile import ZipFile

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data/generated/rules_n5.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5.3-en.pdf"
NEW_IDS = {
    "rule:line-of-fire", "rule:zone-of-control", "rule:zones-and-contact",
    "rule:coherency", "rule:distances-and-measurements",
    "rule:replacing-game-elements",
}
CITATIONS = {
    "rule:line-of-fire": {18, 19},
    "rule:zone-of-control": {20},
    "rule:zones-and-contact": {20, 21},
    "rule:coherency": {21},
    "rule:distances-and-measurements": {21, 22},
    "rule:replacing-game-elements": {22},
    "attribute:s": {9, 18},
    "rule:general-movement": {29, 30},
}


def _records() -> dict[str, Any]:
    document = load_curated_document(ROOT / "data/curated/rules/n5-core-v5.3.json")
    records = document["records"]
    assert all(sum(row["id"] == identity for row in records) == 1
               for identity in CITATIONS)
    return {r["id"]: r for r in records}


def _get(app: Any, path: str, query: str = "") -> tuple[str, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, QUERY_STRING=query, REQUEST_METHOD="GET")
    statuses: list[str] = []
    response = app(environ, lambda status, _headers, _exc=None: statuses.append(status))
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    return statuses[0], body


def _text(record: dict[str, Any]) -> str:
    return " ".join([record["summary"], *[
        text for key in ("requirements", "effects", "restrictions", "clarifications")
        for text in record.get("facts", {}).get(key, [])
    ]])


def test_geometry_source_clauses_match_pinned_pdf_and_wiki() -> None:
    if not PDF.is_file():
        pytest.skip("Pinned English N5.3 PDF unavailable")
    pymupdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    excerpts = {
        18: ("cylinder-shaped", "juts out", "minimum size of 3x3mm", "front 180"),
        19: ("front 180", "360", "Markers do not obstruct LoF",
             "not in Engaged State with them", "not affected by Visibility"),
        20: ("8 inches up from the top", "8 inches down from the bottom",
             "always in Silhouette contact with themselves", "entire Silhouette"),
        21: ("Reference Trooper", "last figure kept back as reserve",
             "before measuring movement", "after having performed any movement",
             "closest parts of their Silhouettes", "before taking any measurements"),
        22: ("same base size", "match the center", "match the edge",
             "cannot be used to cancel the Engaged State", "mandatory and inevitable",
             "conditions of the space", "Pieces of Equipment will be removed"),
    }
    with pymupdf.open(PDF) as pdf:
        for page, phrases in excerpts.items():
            source = " ".join(pdf[page - 1].get_text().split()).casefold()
            for phrase in phrases:
                assert phrase.casefold() in source, (page, phrase)
    archive = ROOT / "data/wiki/WIKI-en 20260926-200832.zip"
    if archive.is_file():
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == (
            "c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987"
        )
        with ZipFile(archive) as wiki:
            for member, revision in {
                "Line_of_Fire": 3510, "Zone_of_Control": 3765,
                "Zones,_Bases_and_Silhouettes": 3514, "Coherency": 3849,
                "Distances_and_Measurements": 3684, "Replacing_Game_Elements": 3518,
                "Silhouette": 3509,
            }.items():
                assert re.search(r'"wgRevisionId":' + str(revision) + r'\b',
                                 wiki.read(member).decode()), member


def test_lof_zones_and_silhouette_preserve_geometric_exceptions() -> None:
    records = _records()
    lof = records["rule:line-of-fire"]
    assert len(lof["facts"]["requirements"]) == 3
    text = _text(lof)
    for clause in ("180-degree", "3 by 3 mm", "friendly or enemy", "360-degree",
                   "Mutual visibility is conditional", "within the target's front",
                   "do not obstruct", "outside its own close combat",
                   "[[skill:sixth-sense|Sixth Sense]]"):
        assert clause in text, clause
    zoc = records["rule:zone-of-control"]
    assert zoc["summary"].count("[[distance:8:inch]]") == 3
    assert "above its top" in zoc["summary"] and "below its bottom" in zoc["summary"]
    assert "[[trait:zone-of-control-zc|Zone of Control (ZoC)]] Weapon Trait" in zoc["summary"]
    assert "starting and final positions" in _text(zoc)
    zones = _text(records["rule:zones-and-contact"])
    for clause in ("always in contact with themselves", "touches that area",
                   "entire [[attribute:s|Silhouette]]", "does not by itself"):
        assert clause in zones
    silhouette = records["attribute:s"]
    assert silhouette["facts"] == {"category": "unit-profile-attribute", "abbreviation": "S"}
    for clause in ("cylindrical", "projecting beyond", "SX", "3 mm", "retaining the base width"):
        assert clause in silhouette["summary"]
    for identity in NEW_IDS:
        record = records[identity]
        assert record["kind"] == "rule" and record["facts"]["category"] == "basic-rule"
        assert not record.get("relations")  # Conditional prose is not a State/Skill grant.
    assert records["trait:zone-of-control-zc"]["summary"] == (
        "Its range is the user's Zone of Control ([[distance:8:inch]])."
    )


def test_coherency_measurement_and_replacement_keep_scoped_conditions() -> None:
    records = _records()
    coherency = _text(records["rule:coherency"])
    for clause in ("Reference Trooper", "Controller or Spearhead", "before measuring",
                   "Conclusion step", "failed [[rule:guts-roll|Guts Roll]]",
                   "consequences immediately", "reserve", "multiple reserve Troopers",
                   "unless the opponent requests"):
        assert clause in coherency, clause
    distances = _text(records["rule:distances-and-measurements"])
    for clause in ("closest points", "straight line", "before measuring",
                   "complete route and endpoint", "consistent base reference point"):
        assert clause in distances, clause
    replacement = _text(records["rule:replacing-game-elements"])
    for clause in ("same position", "matching the centers", "matching their edges",
                   "cannot be used to cancel [[state:engaged|Engaged]]",
                   "Obligatory replacement is mandatory and inevitable",
                   "Equipment is removed", "ends only when", "ordinary cancellation",
                   "optional replacement", "[[skill:engineer|Engineer]]",
                   "[[skill:reset|Reset]]", "grants no independent permission"):
        assert clause in replacement, clause


def test_geometry_storage_api_search_and_separate_trait_owner() -> None:
    app = create_app(ROOT / "data/generated/army.db", rules_database_path=RULES)
    db = RulesDatabase(RULES)
    source = _records()
    for identity, pages in CITATIONS.items():
        record = source[identity]
        assert record["kind"] == identity.partition(":")[0]
        assert record["scope"] == {"game": "N5", "seasons": ["current"]}
        assert record["composition"] == {"role": "definition"}
        assert {c["page"] for c in record["citations"]
                if c["sourceId"] == "n5-core-v5.3-pdf"} == pages
        published = db.composed_record(identity)
        assert published is not None
        assert published["summary"] == record["summary"]
        assert published["facts"] == record["facts"]
        assert {c["page"] for c in published["citations"]
                if c["source_id"] == "n5-core-v5.3-pdf"} == pages
        if identity not in NEW_IDS:
            continue
        slug = identity.partition(":")[2]
        status, body = _get(app, f"/api/rules/{slug}")
        assert status == "200 OK" and json.loads(body)["rules"][0]["id"] == identity
        status, _body = _get(app, f"/rules/{slug}")
        assert status == "200 OK"
        status, body = _get(app, "/api/search", "q=" + record["name"].replace(" ", "+"))
        assert status == "200 OK"
        assert any(item.get("href") == f"/rules/{slug}"
                   for item in json.loads(body)["items"])
    status, body = _get(app, "/api/traits/zone-of-control-zc")
    assert status == "200 OK" and json.loads(body)["rules"][0]["id"] == "trait:zone-of-control-zc"
    status, body = _get(app, "/api/glossary")
    assert status == "200 OK"
    entries = {item["id"]: item for item in json.loads(body)["items"]}
    assert entries["attribute:s"]["description"] == source["attribute:s"]["summary"]
    assert entries["attribute:s"]["href"] == "/glossary#attribute-s"