"""V1S-032A N5.3 Command Module source and public-reference regressions."""

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
SOURCE = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
SOURCE_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"

# Pinned Command Module mode and restriction evidence, not an executable engine.
COMMAND_CLAUSES = {
    128: (
        "Each player has four Command Tokens per game.",
        "Command Tokens have three different gaming use modes",
        "Strategic Use.", "Executive Use.", "Operational Use.",
        "one on a Procedural option and one on a Logistical option",
        "Permanently move an Allied Trooper and all their Peripherals to a",
        "different Combat Group, keeping in mind the 10-member limit",
        "Cancel the Possessed State of an Allied Trooper",
        "Declare a Coordinated Order, spending a Regular Order",
        "Have an Allied Trooper automatically pass or fail a Guts Roll",
        "Transforms the Irregular Order provided by an Irregular Trooper",
        "into a single Regular Order",
        "Have one Trooper be unaffected by Retreat!",
        "Reroll a failed WIP Roll when trying to use the Special Skill Doctor",
        "Reroll a failed WIP Roll when trying to use the Special Skill Engineer",
        "Create a new Fireteam by placing a Fireteam Leader Token",
        "Players may expend as many Command Tokens during a single Active",
        "more than one Command Token for the same effect",
    ),
    129: (
        "Players cannot expend Command Tokens during their Reactive Turn.",
        "Without expending or declaring a new Order",
        "spend a new Command Token",
    ),
}


def test_n5_command_resource_and_all_three_modes_are_pinned_source_obligations() -> None:
    if not SOURCE.is_file():
        pytest.skip("Pinned N5.3 English source PDF unavailable")
    pymupdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    with pymupdf.open(SOURCE) as pdf:
        for page, clauses in COMMAND_CLAUSES.items():
            text = " ".join(pdf[page - 1].get_text().split()).casefold()
            for clause in clauses:
                assert clause.casefold() in text, (page, clause)


def test_existing_strategic_use_has_source_citations_and_is_not_full_overview() -> None:
    curated = {
        row["id"]: row
        for row in load_curated_document(CORE)["records"]
    }
    strategic = curated["rule:command-token-strategic-use"]
    assert strategic["name"] == "Command Token: Strategic Use"
    assert strategic["composition"]["role"] == "definition"
    assert strategic["facts"]["category"] == "command-token-use"
    assert "one Procedural option and one Logistical option" in (
        strategic["facts"]["restrictions"][0]
    )
    assert any(
        item["sourceId"] == "n5-core-v5.3-pdf" and item["page"] == 128
        for item in strategic["citations"]
    )
    published = RulesDatabase(RULES).composed_record(strategic["id"])
    assert published is not None
    assert published["name"] == strategic["name"]
    assert published["summary"] == strategic["summary"]
    assert published["facts"]["effects"] == strategic["facts"]["effects"]
    # The previous narrow Strategic record remains unchanged.


def _get(app: Any, path: str, query: str = "") -> tuple[str, bytes]:
    environ: dict[str, object] = {}
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


def test_general_command_token_uses_are_published_with_exact_scope() -> None:
    records = {
        row["id"]: row
        for row in load_curated_document(CORE)["records"]
    }
    general = records["rule:command-tokens"]
    assert general["name"] == "Command Tokens"
    assert general["composition"] == {"role": "definition"}
    assert general["scope"] == {"game": "N5", "seasons": ["current"]}
    assert general["facts"]["category"] == "command-token-use"
    assert [(c["sourceId"], c["page"]) for c in general["citations"]] == [
        ("n5-core-v5.3-pdf", 128), ("n5-core-v5.3-pdf", 129),
    ]
    content = " ".join(
        [general["summary"]]
        + [
            detail
            for key in ("requirements", "effects", "restrictions", "clarifications")
            for detail in general["facts"].get(key, [])
        ]
    )
    for fragment in (
        "four Command Tokens", "Strategic", "Executive", "Operational",
        "first Player Turn", "second Player Turn", "Tactical Phase",
        "Speedball Tokens", "more than ten", "ten-member limit",
        "Possessed State", "Coordinated Order", "Guts Roll",
        "Irregular Order", "Regular Order", "Fireteam Leader",
        "Doctor", "Remote Presence", "Reactive Turn",
    ):
        assert fragment.casefold() in content.casefold(), fragment
    published = RulesDatabase(RULES).composed_record(general["id"])
    assert published is not None
    assert published["summary"] == general["summary"]
    assert published["facts"] == general["facts"]
    assert {(c["source_id"], c["page"]) for c in published["citations"]} == {
        ("n5-core-v5.3-pdf", 128), ("n5-core-v5.3-pdf", 129),
    }

    app = create_app(ROOT / "data/generated/infinity.db", rules_database_path=RULES)
    for route in ("/rules", "/rules/command-tokens"):
        status, body = _get(app, route)
        assert status == "200 OK", route
        assert b"<html" in body.lower(), route
    status, body = _get(app, "/api/rules/command-tokens")
    assert status == "200 OK"
    assert json.loads(body)["rules"][0]["id"] == "rule:command-tokens"
    status, body = _get(app, "/api/search", "q=command+tokens")
    assert status == "200 OK"
    assert any(
        item.get("href") == "/rules/command-tokens"
        for item in json.loads(body)["items"]
    )
