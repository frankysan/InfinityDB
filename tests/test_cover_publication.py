"""V1S-033C Cover, native vertical movement and unchanged parameter contracts."""

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
CITATIONS = {
    "rule:cover": {41, 42},
    "skill:climb": {32, 33},
    "skill:jump": {34},
    "skill:climbing-plus": {88},
}


def _records() -> dict[str, Any]:
    doc = load_curated_document(ROOT / "data/curated/rules/n5-core-v5.3.json")
    records = doc["records"]
    assert all(sum(row["id"] == identity for row in records) == 1
               for identity in CITATIONS)
    return {r["id"]: r for r in records}


def _text(record: dict[str, Any]) -> str:
    return " ".join([record["summary"], *[
        text for key in ("requirements", "effects", "restrictions", "clarifications")
        for text in record.get("facts", {}).get(key, [])
    ]])


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


def test_cover_vertical_source_clauses_match_pinned_pdf_and_archive(
    pinned_n53_core_pdf: Path,
) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(pinned_n53_core_pdf.read_bytes()).hexdigest() == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    excerpts = {
        32: ("outer edge and underside", "only allows movement on vertical surfaces",
             "cannot declare any Skills other than Climb", "State Token beside",
             "cannot enter Prone State", "cannot be used in the Reactive Turn"),
        33: ("as soon as the whole of their base", "they will remain in the position",
             "their target is performing the Climb Skill"),
        34: ("tracing a parabola", "A jump ends", "during an Order in which they declared Jump",
             "automatically cancels Prone State", "no safe alternative landing spot"),
        41: ("that requires LoF", "apply a -3 MOD", "applies a +3 MOD",
             "in contact with a piece of scenery that partially obscures"),
        42: ("In both situations the Blue Trooper has Cover",),
        88: ("first Basic Short Skill", "once per Order", "while they are on a vertical surface"),
    }
    with pymupdf.open(pinned_n53_core_pdf) as pdf:
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
            for member, revision in {"Cover": 4094, "Climb": 4022, "Jump": 3869,
                                     "Climbing_Plus": 3993}.items():
                source = wiki.read(member).decode()
                assert re.search(r'"wgRevisionId":' + str(revision) + r'\b', source)
                if member == "Cover":
                    assert '"wgPageName":"Ballistic_Skills"' in source


def test_cover_conditions_and_skill_metadata_preserve_distinct_owners() -> None:
    records = _records()
    cover = records["rule:cover"]
    assert cover["kind"] == "rule" and cover["facts"]["category"] == "basic-rule"
    assert cover["aliases"] == ["Total Cover", "Partial Cover"]
    text = _text(cover)
    for phrase in ("completely block", "touches a [[term:scenery-element|Scenery Element]]",
                   "-3 to the attacker's", "+3 to the target's", "if a roll is necessary",
                   "contact alone is insufficient", "that require [[rule:line-of-fire|LoF]]",
                   "not a permanent increase", "different conditions"):
        assert phrase in text, phrase
    assert not cover.get("relations")
    parameters = {"inheritance": "family", "occurrenceParameters": [
        {"source": "army-extra", "kind": "distance", "positiveSign": "omit"}
    ]}
    for identity, source in (("skill:climb", 271), ("skill:jump", 263)):
        record = records[identity]
        assert record["armyLinks"] == [{"entity": "skill", "id": source}]
        assert record["variantSemantics"] == parameters
        assert record["facts"]["typeIds"] == ["long-skill"]
        assert record["labelIds"] == ["movement", "no-lof", "no-roll"]
        assert "not the underlying [[attribute:mov|MOV]] value" in _text(record)
    assert not records["skill:climb"].get("relations")
    assert records["skill:jump"]["relations"] == [
        {"type": "cancels-state", "recordId": "state:prone"}
    ]
    plus = records["skill:climbing-plus"]
    assert plus["facts"]["typeIds"] == ["automatic"]
    assert plus["labelIds"] == ["movement", "optional"]
    assert plus["variantSemantics"] == {"inheritance": "family"}
    assert plus["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:climb"},
        {"type": "applies-effects-to", "recordId": "skill:move"},
        {"type": "applies-effects-to", "recordId": "skill:dodge"},
    ]
    assert plus["citations"] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 88, "section": "Climbing Plus"},
        {"sourceId": "wiki-climbing-plus-oldid-3993", "heading": "Climbing Plus"},
    ]


def test_vertical_procedures_keep_landing_declaration_and_cover_conditions() -> None:
    rows = _records()
    climb = _text(rows["skill:climb"])
    for phrase in ("When declaring", "outer edge and underside", "whole base",
                   "Unused allowance", "remain holding", "not mandatory in every Order",
                   "Long Skill", "Reactive Turn", "[[rule:automatic-reaction-order|ARO]]",
                   "performing [[skill:climb|Climb]] or holding", "State Token",
                   "except for Unit Types", "horizontal upper surface"):
        assert phrase in climb, phrase
    jump = _text(rows["skill:jump"])
    for phrase in ("horizontal landing surface", "parabolic route", "outer edge and underside",
                   "touches the landing surface", "entire Order", "including after landing",
                   "automatically cancels", "no safe alternative", "[[skill:idle|Idle]]"):
        assert phrase in jump, phrase
    plus = _text(rows["skill:climbing-plus"])
    for phrase in ("first Basic Short Skill", "once per Order", "second [[attribute:mov|MOV]]",
                   "[[rule:cover|Partial Cover]] MODs while on a vertical surface",
                   "[[rule:general-movement|General Movement Rules]]"):
        assert phrase in plus, phrase
    assert "vault" not in climb.casefold() and "vault" not in jump.casefold()


def test_cover_skill_storage_api_search_and_dated_vaulting_faq() -> None:
    app = create_app(ROOT / "data/generated/army.db", rules_database_path=RULES)
    db = RulesDatabase(RULES)
    source = _records()
    for identity, pages in CITATIONS.items():
        curated = source[identity]
        assert curated["kind"] == identity.partition(":")[0]
        assert curated["scope"] == {"game": "N5", "seasons": ["current"]}
        assert curated["composition"] == {"role": "definition"}
        assert {c["page"] for c in curated["citations"]
                if c["sourceId"] == "n5-core-v5.3-pdf"} == pages
        published = db.composed_record(identity)
        assert published is not None
        assert published["summary"] == source[identity]["summary"]
        assert published["facts"] == source[identity]["facts"]
        assert {c["page"] for c in published["citations"]
                if c["source_id"] == "n5-core-v5.3-pdf"} == pages
        domain = "rules" if identity == "rule:cover" else "skills"
        slug = identity.partition(":")[2]
        status, body = _get(app, f"/api/{domain}/{slug}")
        assert status == "200 OK" and json.loads(body)["rules"][0]["id"] == identity
        status, _body = _get(app, f"/{domain}/{slug}")
        assert status == "200 OK"
        status, body = _get(app, "/api/search", "q=" + source[identity]["name"].replace(" ", "+"))
        assert status == "200 OK"
        assert any(item.get("href") == f"/{domain}/{slug}"
                   for item in json.loads(body)["items"])
    for topic in ("skill:climb", "skill:jump"):
        status, body = _get(app, "/api/faq-rulings",
                            f"topic_id={topic}&rules_revision=5.3&as_of=2026-09-01")
        assert status == "200 OK"
        vault = [r for r in json.loads(body)["items"]
                 if r["id"] == "faq-ruling:vault-during-climb-and-jump"]
        assert len(vault) == 1
        assert vault[0]["original_publication"]["version"] == "0.0"
        assert vault[0]["selected_source"]["version"] == "0.1"
