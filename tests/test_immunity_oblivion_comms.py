"""Exact N5.3 Oblivion Comms exception for BTS and State Immunity.

The pinned rule excludes ordinary Immunity from Comms Attacks, but
Immunity (State: Isolated) can stop that State. Do not infer any
Saving Roll count from a Hacking Program's Burst.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pymupdf

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
RULES = ROOT / "data/generated/rules.db"
ARMY = ROOT / "data/generated/infinity.db"
EXPECTED = {
    "when": {
        "programId": "hacking-program:oblivion",
        "attackClass": "comms",
        "stateId": "state:isolated",
    },
    "sourceProfile": {
        "ammunitionId": "ammunition:ap",
        "savingAttribute": "BTS",
        "nonLethalTrait": "trait:non-lethal",
        "failedSaveState": "state:isolated",
        "burst": 2,
    },
    "immunityBts": {
        "applies": False,
        "apModifierIgnored": False,
        "isolatedStatePrevented": False,
    },
    "immunityStateIsolated": {
        "applies": True,
        "isolatedStatePrevented": True,
        "savingRollCancelled": False,
    },
    "evidence": "derived-from-pinned-general-rules",
}


def test_pinned_comms_exclusion_oblivion_and_saving_attribute() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as source:
        pages = {}
        for number in (57, 58, 95):
            raw = source[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split())
    assert all(fragment in pages[57] for fragment in (
        "saving roll", "bts", "burst (b)",
    ))
    assert all(fragment in pages[58] for fragment in (
        "oblivion", "ap ammo", "non-lethal", "state: isolated",
        "hacking programs chart",
    ))
    assert all(fragment in pages[95] for fragment in (
        "immunity (state)", "comms", "exception of immunity (state)",
    ))
    records = load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]
    skill = next(item for item in records if item["id"] == "skill:immunity")
    assert skill["facts"]["immunityInteraction"]["reviewedCommsCases"] == [EXPECTED]
    program_records = load_curated_document(
        ROOT / "data/curated/rules/n5-hacking-programs-v5.3.json"
    )["records"]
    program = next(item for item in program_records if item["id"] == "hacking-program:oblivion")
    assert "comms-attack" in program["labelIds"]
    assert "Non-Lethal" in program["summary"]
    assert "AP Comms Attack" in program["summary"]
    assert any("isolated" in text.casefold() for text in program["facts"]["effects"])


def test_reviewed_oblivion_exception_is_published_without_mutating_program() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedCommsCases"] == [
        EXPECTED
    ]
    app = create_app(ARMY, rules_database_path=RULES)

    def get(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        content = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        return json.loads(content)

    assert get("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedCommsCases"] == [EXPECTED]
    response = get("/api/hacking-programs/oblivion")
    assert str(response["burst"]) == "2"
    assert str(response["ps"]) == "4"
    oblivion = response["rules"][0]
    assert oblivion["id"] == "hacking-program:oblivion"
    assert "AP Comms Attack" in oblivion["summary"]
    assert "Non-Lethal" in oblivion["summary"]
    assert oblivion["facts"]["effects"]
    assert "immunityInteraction" not in oblivion["facts"]
