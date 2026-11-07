"""V1S-033A source, identity and matched-publication regressions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults
from zipfile import ZipFile

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools import promote_movement_reference
from tools.promote_movement_reference import CITATIONS, verify_candidate

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5.3-en.pdf"


def _records() -> dict[str, Any]:
    document = load_curated_document(ROOT / "data/curated/rules/n5-core-v5.3.json")
    return {r["id"]: r for r in document["records"]}


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


def test_movement_source_pages_and_archived_move_requirements() -> None:
    if not PDF.is_file():
        pytest.skip("Pinned English N5.3 PDF unavailable")
    pymupdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    excerpts = {
        27: ("before determining where the Trooper", "outer edge and underside",
             "the exact route"),
        28: ("At least half the Trooper", "at least half as wide as their base",
             "equal to or larger than their base", "second value", "stairs and ladders"),
        29: ("no minimum", "360", "ends automatically", "except for Jump and Berserk",
             "they perform an Idle instead", "even if they enter a Null or Immobilized"),
        30: ("on both sides", "combined height is higher", "between each of those levels"),
    }
    with pymupdf.open(PDF) as pdf:
        for page, phrases in excerpts.items():
            text = " ".join(pdf[page - 1].get_text().split()).casefold()
            for phrase in phrases:
                assert phrase.casefold() in text, (page, phrase)
    archive = ROOT / "data/wiki/WIKI-en 20260926-200832.zip"
    if archive.is_file():
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == (
            "c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987"
        )
        with ZipFile(archive) as wiki:
            move = wiki.read("Move").decode()
            assert 'wgRevisionId":3530' in move
            assert "at least half as wide" in move
            assert "equal to or larger than their base" in move


def test_move_and_shared_rules_preserve_conditional_boundaries() -> None:
    records = _records()
    move = records["skill:move"]
    assert move["labelIds"] == ["movement", "no-lof", "no-roll"]
    assert move["facts"]["typeIds"] == ["basic-short-skill"]
    assert len(move["facts"]["requirements"]) == 3
    requirements = " ".join(move["facts"]["requirements"])
    for phrase in ("when declaring", "at least half", "except while vaulting",
                   "half as wide", "entire base"):
        assert phrase in requirements
    assert "first" in move["facts"]["effects"][0]
    assert "second Basic Short Skill" in move["facts"]["effects"][1]
    assert "after the first" in move["facts"]["restrictions"][0]
    general = records["rule:general-movement"]
    text = " ".join(general["facts"][k][i] for k in ("effects", "restrictions")
                    for i in range(len(general["facts"][k])))
    for phrase in ("360-degree", "both sides", "intermediate supporting surface",
                   "cannot finish", "wider than", "except [[skill:jump|Jump]]",
                   "either the start or end", "no movement", "[[skill:idle|Idle]]",
                   "successful enemy Attacks", "contact stopping condition",
                   "does not determine pathfinding"):
        assert phrase in text, phrase
    for identity, pages in CITATIONS.items():
        record = records[identity]
        assert {c["page"] for c in record["citations"]
                if c["sourceId"] == "n5-core-v5.3-pdf"} == pages
        assert not record.get("relations")  # No unconditional State/Skill grants.


def test_published_movement_source_api_search_and_routes() -> None:
    app = create_app(ROOT / "data/generated/infinity.db", rules_database_path=RULES)
    db = RulesDatabase(RULES)
    records = _records()
    for identity in CITATIONS:
        record = records[identity]
        published = db.composed_record(identity)
        assert published is not None
        for key in ("summary", "facts"):
            assert published[key] == record[key]
        assert {c["page"] for c in published["citations"]
                if c["source_id"] == "n5-core-v5.3-pdf"} == CITATIONS[identity]
        domain = "skills" if identity == "skill:move" else "rules"
        slug = identity.partition(":")[2]
        for route in (f"/{domain}", f"/{domain}/{slug}", f"/api/{domain}/{slug}"):
            status, body = _get(app, route)
            assert status == "200 OK", route
            if route.startswith("/api/"):
                assert json.loads(body)["rules"][0]["id"] == identity
        status, body = _get(app, "/api/search", "q=" + record["name"].replace(" ", "+"))
        assert status == "200 OK"
        assert any(item.get("href") == f"/{domain}/{slug}"
                   for item in json.loads(body)["items"])


def test_guarded_movement_rebuild_matches_current_release() -> None:
    if not PDF.is_file() or not (ROOT / "local").is_dir():
        pytest.skip("Pinned source and local staging unavailable")
    result = verify_candidate()
    assert result["alreadyPublished"]
    assert result["deterministic"] and result["matchedPublication"]
    assert result["logicallyEquivalentWithPublished"]
    assert result["candidateRecords"] >= 489
    assert result["publishedRulesSha256"] == hashlib.sha256(RULES.read_bytes()).hexdigest()


def test_movement_guard_refuses_repeat_and_mismatch_without_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not PDF.is_file() or not (ROOT / "local").is_dir():
        pytest.skip("Pinned source and local staging unavailable")
    objects = ROOT / "data/generated/deployed-objects.json"
    original = (RULES.read_bytes(), objects.read_bytes())
    with pytest.raises(ValueError, match="repeated movement promotion"):
        verify_candidate(promote=True)
    monkeypatch.setattr(promote_movement_reference, "load_deployed_object_publication",
                        lambda *_args: None)
    with pytest.raises(ValueError, match="publication does not match"):
        verify_candidate()
    assert (RULES.read_bytes(), objects.read_bytes()) == original
