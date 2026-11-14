"""V1S-032B source-led Order Pool / phase / activation boundary review.

These checks pin evidence and existing publication ownership. They do not
equate a source-page citation with full whole-corpus browser acceptance.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES = ROOT / "data/generated/rules_n5.db"
SHA_EN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
SHA_ES = "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f"

# Directly printed material by exact page; source claims are independent of
# already published partial interpretations and future implementation.
PHASE_CLAUSES = {
    11: (
        "Regular Troopers add their Orders to the Order Pool",
        "An Irregular Trooper is not added",
        "status and expenditure of every Order is Open Information",
    ),
    12: (
        "Each Combat Group has its own Order Pool",
        "Only Regular Orders go into the Order Pool",
        "recalculate Order Pools at the beginning of each of their Active Turns",
        "Each Regular Trooper deployed on the battlefield",
        "not in any Null State",
        "The status and existence of Orders provided by these Troopers is Private Information",
        "no limit to the number of Regular Orders",
        "Players are not required to spend all the Regular Orders",
    ),
    13: (
        "Basic Short Skills: These skills are Move, Discover, and Idle",
        "An enemy Trooper activates within its Line of Fire",
        "An enemy Trooper activates within its Zone of Control",
        "Hacking Area",
        "It has a Special Skill, weapon, or piece of Equipment",
        "It is affected by a Template Weapon, or is the target of a Comms",
        "each eligible enemy Trooper gets one single ARO",
        "1 Basic Short Skill + 1 Basic Short Skill",
        "1 Basic Short Skill + 1 Short Skill",
        "1 Long Skill",
        "target of an ARO must always be one of the Troopers",
        "only the Reactive Player may declare AROs",
        "AROs always have Burst B1",
        "cannot split it amongst different targets",
    ),
    14: (
        "All AROs are also simultaneous",
        "Order Expenditure Sequence",
        "Activation: The Active Player declares which Trooper will activate",
        "ARO Declaration.",
        "Resolution: Check that the Skills and pieces of Equipment",
        "All details and choices related to the execution",
    ),
    15: (
        "their Requirements must be checked when the Skill is declared",
        "the action is cancelled and the Trooper instead performs an Idle",
        "the positive effect is always applied first",
    ),
    16: (
        "GAME ROUND",
        "The base of each Trooper must be totally inside the Deployment Zone",
        "Troopers cannot be deployed in contact with enemy and neutral",
        "When a Trooper deploys, its owner can choose to deploy it Prone",
        "Troopers cannot deploy in a location without enough space",
        "Players can measure the size of the Deployment Zones",
        "Each Player Turn is divided into these steps",
        "Start of the Turn: Tactical Phase",
        "Executive Use of Command Tokens",
        "Retreat! Check",
        "Loss of Lieutenant check",
        "Order count",
        "Impetuous Phase",
        "Orders Phase",
        "States Phase",
        "End of the Turn",
    ),
    17: (
        "Each Combat Group has its own independent Order Pool",
        "Troopers that have yet to be deployed on the table",
        "their player can keep their Orders secret",
        "without spending an Order",
        "unused Orders cannot be reserved for subsequent Turns",
        "These rolls do not generate AROs",
        "All Order Tokens still on the table are removed",
    ),
    128: (
        "Command Tokens have three different gaming use modes",
        "EXECUTIVE USE",
        "OPERATIONAL USE",
    ),
    129: (
        "Players cannot expend Command Tokens during their Reactive Turn",
        "Only Troopers with the same Training",
        "only declare a Coordinated Order during the Orders Phase",
    ),
    130: (
        "all participants must declare the same sequence of Skills",
        "HACKING PROGRAMS",
        "TARGETLESS OR DEPLOYABLE TRAITS",
    ),
}


def test_order_and_turn_phase_source_clauses_are_pinned(
    pinned_n53_core_pdf: Path,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(pinned_n53_core_pdf.read_bytes()).hexdigest() == SHA_EN
    with pdf.open(pinned_n53_core_pdf) as document:
        for number, clauses in PHASE_CLAUSES.items():
            text = " ".join(document[number - 1].get_text().split()).casefold()
            for clause in clauses:
                assert " ".join(clause.split()).casefold() in text, (number, clause)


def test_lieutenant_order_count_bilingual_double_negative_is_not_hidden(
    pinned_pdf_sources: Callable[[Mapping[str, str]], dict[str, Path]],
) -> None:
    sources = pinned_pdf_sources({
        "data/pdf/rules/n5-rules-v5.3-en.pdf": SHA_EN,
        "data/pdf/rules/n5-rules-v5.3-es.pdf": SHA_ES,
    })
    en = sources["data/pdf/rules/n5-rules-v5.3-en.pdf"]
    es = sources["data/pdf/rules/n5-rules-v5.3-es.pdf"]
    pdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(en.read_bytes()).hexdigest() == SHA_EN
    assert hashlib.sha256(es.read_bytes()).hexdigest() == SHA_ES
    with pdf.open(en) as document:
        en = " ".join(document[16].get_text().split())
    with pdf.open(es) as document:
        es = " ".join(document[16].get_text().split())
    assert "not in a non-Null State" in en
    assert "Teniente en estado no Nulo" in es
    register = (ROOT / "docs/official-source-clarifications.md").read_text(
        encoding="utf-8"
    )
    assert "SRC-031" in register and "Lieutenant Order" in register
    assert "not in a non-Null State" in register
    assert "Teniente en estado no Nulo" in register


def test_existing_order_phase_rule_owners_retain_scoped_publication() -> None:
    curated = {
        record["id"]: record
        for record in load_curated_document(CORE)["records"]
    }
    published = RulesDatabase(RULES)
    expected = {
        "rule:combat-group": (10,),
        "rule:regular-order": (11,),
        "rule:irregular-order": (11,),
        "rule:order-expenditure-sequence": (14, 15),
        "rule:deployment-phase": (15,),
        "rule:coordinated-orders": (129, 130, 131),
        "rule:command-tokens": (128, 129),
        "skill:impetuous": (97,),
    }
    for identity, pages in expected.items():
        record = curated[identity]
        actual = published.composed_record(identity)
        assert actual is not None, identity
        assert record["summary"] == actual["summary"], identity
        assert set(pages).issubset({
            item["page"] for item in record["citations"]
            if item["sourceId"] == "n5-core-v5.3-pdf" and "page" in item
        }), identity
        assert set(pages).issubset({
            item["page"] for item in actual["citations"]
            if item["source_id"] == "n5-core-v5.3-pdf" and item.get("page")
        }), identity
    assert "simultaneous" in curated["rule:order-expenditure-sequence"]["summary"]
    assert "Spearhead" in curated["rule:coordinated-orders"]["summary"]
    assert "Impetuous Phase" in curated["skill:impetuous"]["summary"]
    assert "Tactical Phase" in curated["rule:command-tokens"]["summary"]
    # An Orders/AROs matrix is not a universal legal-action evaluator; the
    # gap register owns the missing normal Game Sequence/Order Pool/ARO overview.
