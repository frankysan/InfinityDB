"""Flash Pulse / Immunity (BTS): pin the official N5.3 printed Example 4.

The English PDF p. 96, not only an old Wiki revision, establishes the
exception for Non-Lethal and State: Stunned. The p. 186 Weapon Chart and
Army profile establish one BTS roll despite the Spanish Wiki conflict.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pymupdf

from infinity_db.curated import load_curated_document
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
EXPECTED = {
    "when": {
        "weaponId": "weapon:flash-pulse",
        "immunity": "BTS",
        "savingAttribute": "BTS",
        "attackClass": "non-comms",
    },
    "ammunitionTreatedAs": "ammunition:normal",
    "survivingTraits": ["trait:non-lethal", "trait:state"],
    "stateEffect": {
        "stateId": "state:stunned",
        "condition": "failed-saving-roll",
    },
    "evidence": "explicit-n5.3-pdf-p96-example-4",
}


def test_flash_pulse_example_is_printed_in_pinned_english_n53() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as source:
        pages: dict[int, str] = {}
        for number in (95, 96, 186):
            raw = source[number - 1].get_text("text")
            assert isinstance(raw, str)
            pages[number] = " ".join(raw.casefold().split()).replace("non- lethal", "non-lethal")
    for phrase in (
        "example 4",
        "immunity (bts)",
        "flash pulse",
        "normal ammunition",
        "non-lethal trait",
        "state: stunned trait",
        "fails their saving roll",
    ):
        assert phrase in pages[96]
    assert all(phrase in pages[95] for phrase in (
        "immunity", "non-lethal and state:", "comms attacks",
    ))
    assert all(phrase in pages[186] for phrase in (
        "flash pulse", "stun", "bts", "non-lethal", "state: stunned",
    ))
    records = {row["id"]: row for row in load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]}
    assert records["skill:immunity"]["facts"]["immunityInteraction"][
        "reviewedWeaponCases"
    ][0] == EXPECTED
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 96} in records[
        "skill:immunity"
    ]["citations"]
    assert any(
        citation["sourceId"] == "n5-core-v5.3-pdf"
        and citation["page"] == 96
        and citation.get("section") == "Immunity Example 4"
        for citation in records["weapon:flash-pulse"]["citations"]
    )


def test_all_four_printed_n53_immunity_examples_have_distinct_pdf_evidence() -> None:
    records = {record["id"]: record for record in load_curated_document(
        ROOT / "data/curated/rules/n5-core-v5.3.json"
    )["records"]}
    facts = records["skill:immunity"]["facts"]["immunityInteraction"]
    printed = {
        ("weapon:missile-launcher", 1),
        ("weapon:monofilament-cc-weapon", 2),
        ("weapon:plasma-rifle", 3),
        ("weapon:flash-pulse", 4),
    }
    actual = set()
    for case in facts["reviewedWeaponCases"] + facts["reviewedSavingRollCases"]:
        label = case["evidence"]
        for number in range(1, 5):
            if label == f"explicit-n5.3-pdf-p96-example-{number}":
                actual.add((case["when"]["weaponId"], number))
    assert actual == printed
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 96} in (
        records["skill:immunity"]["citations"]
    )


def test_flash_pulse_source_profile_does_not_inherit_spanish_wiki_discrepancy() -> None:
    weapon = Database(ARMY).get_catalog_item("weapons", "flash-pulse")
    assert weapon is not None
    profiles = weapon.get("profiles", []) + [
        p for v in weapon.get("weapon_variants", [])
        for p in v.get("profiles", [])
    ]
    assert profiles
    for profile in profiles:
        assert profile["ammunition"].casefold() == "stun"
        assert profile["saving"] == "BTS"
        assert profile["saving_num"] == "1"
        assert "non-lethal" in [trait.casefold() for trait in profile["traits"]]
        assert "State: Stunned" in profile["traits"]


def test_flash_pulse_pdf_evidence_is_published_without_profile_mutation() -> None:
    rules = RulesDatabase(RULES)
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"][0] == EXPECTED

    app = create_app(ARMY, rules_database_path=RULES)

    def fetch(path: str) -> dict:
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc: object = None) -> None:
            statuses.append(status)

        body = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        return json.loads(body)

    assert fetch("/api/skills/immunity")["rules"][0]["facts"][
        "immunityInteraction"
    ]["reviewedWeaponCases"][0] == EXPECTED
    weapon = fetch("/api/weapons/flash-pulse")
    profiles = weapon.get("profiles", []) + [
        p for v in weapon.get("weapon_variants", [])
        for p in v.get("profiles", [])
    ]
    assert profiles
    assert all(
        p["saving"] == "BTS" and p["saving_num"] == "1"
        and "immunity_result" not in p
        and "immunityInteraction" not in p
        for p in profiles
    )
