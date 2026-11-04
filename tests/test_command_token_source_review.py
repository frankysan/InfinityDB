"""V1S-032 Command Module source gap evidence, not an acceptance verdict."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES = ROOT / "data/generated/rules.db"
SOURCE = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
SOURCE_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"

# Comprehensive check of the three mode headings, pool, permitted options
# and the Reactive Turn prohibition. These are proof of the source obligation,
# not a claim that the still-missing general reference has been published.
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
    # Source p.128 describes Executive and Operational uses beyond this
    # Strategic-only record. V1S-032 remains open pending normal publication.
