"""N5.3 regression evidence: Deployable trigger declarations versus exempt movement.

The audit deliberately does not assert an unconditional Dodge->Deployable
relationship: Dodge *declarations* can trigger Mines, Dodge *movement* cannot.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.audit_weaponry_family_clauses import _normalized_text

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PINNED_PDF_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"


def _records() -> dict[str, dict]:
    path = ROOT / "data/curated/rules/n5-core-v5.3.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {record["id"]: record for record in raw["records"]}


def test_declared_dodge_can_trigger_mines_but_following_movement_cannot() -> None:
    records = _records()
    mines = records["weapon:mines"]
    summary = mines["summary"]
    assert "Declaring [[skill:dodge|Dodge]] as an [[trait:aro|ARO]] can trigger a Mine" in summary
    assert "usual Trigger Area and allied-safety conditions" in summary
    assert "The later [[skill:dodge|Dodge]] movement does **not** itself trigger" in summary
    assert "Movement resulting from a failed [[rule:guts-roll|Guts Roll]]" in summary
    assert "is likewise exempt" in summary
    assert "[[skill:stealth|Stealth]] does not disable Mine triggering" in summary
    assert {
        ("n5-core-v5.3-pdf", 38),
        ("n5-core-v5.3-pdf", 72),
        ("n5-core-v5.3-pdf", 79),
        ("n5-core-v5.3-pdf", 80),
        ("n5-core-v5.3-pdf", 112),
    } <= {(cite["sourceId"], cite.get("page")) for cite in mines["citations"]}
    assert not any(
        rel["type"] == "restricts-use-of" and rel["recordId"] == "skill:dodge"
        for rel in mines["relations"]
    ), "A context-free restriction edge would misrepresent the declaration/movement distinction"


def test_canonical_skill_rules_preserve_scope_and_different_trigger_targets() -> None:
    records = _records()
    dodge = records["skill:dodge"]["facts"]
    guts = records["rule:guts-roll"]["facts"]
    stealth = records["skill:stealth"]["facts"]
    mines = records["weapon:mines"]["summary"]
    boost = records["trait:boost"]["summary"]
    placement = records["skill:place-deployable"]["facts"]

    assert any(
        "Dodge movement occurs in the Effects step" in line
        and "does not generate reactions or trigger" in line
        for line in dodge["effects"]
    )
    assert any(
        "Movement after failing a Guts Roll" in line
        and "does not generate [[trait:aro|AROs]], trigger [[trait:deployable|Deployable]]" in line
        for line in guts["restrictions"]
    )
    assert any(
        "Stealth does not prevent [[trait:deployable|Deployable]]" in line
        for line in stealth["restrictions"]
    )
    assert "enemy Model or Marker declares or executes a Skill" in mines
    assert "without affecting any ally" in mines
    assert "enemy Model declares or performs an Order" in boost
    assert "does not trigger if an obstacle or too-small gap" in boost
    assert "does not trigger" in boost and "[[state:camouflaged|CAMO]]" in boost
    assert any(
        "becomes active only in subsequent Orders" in line
        for line in placement["effects"]
    )


@pytest.mark.parametrize(
    ("page", "source_excerpt"),
    (
        (38, "Does not generate AROs or activate Deployable Weapons or Equipment."),
        (69, "weapon is not triggered by Camouflage Markers (CAMO)"),
        (72, "A Mine never triggers if the Small Teardrop Template would affect an ally"),
        (72, "Dodge movement and movement from failed Guts Rolls does not generate AROs"),
        (79, "Does not generate AROs or trigger Deployable Weapons or Equipment."),
        (80, "If he declares an ARO, the Mine will detonate."),
        (82, "placed at the Conclusion of the Order"),
        (112, "Stealth is not effective against Troopers with the Combat Instinct"),
    ),
)
def test_pinned_pdf_explicit_trigger_exceptions_if_source_available(
    page: int, source_excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 source PDF unavailable in checkout")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as doc:
        page_text = _normalized_text(doc[page - 1].get_text())
    assert _normalized_text(source_excerpt) in page_text, (page, source_excerpt)


def test_boost_placement_exception_is_not_marker_trigger_permission() -> None:
    records = _records()
    boost = records["trait:boost"]
    mines = records["weapon:mines"]
    place = records["skill:place-deployable"]["facts"]
    intuitive = records["skill:intuitive-attack"]["facts"]

    summary = boost["summary"]
    assert "**Placing is not triggering:**" in summary
    assert "valid non-camouflaged enemy in that area permits placement" in summary
    assert "the Marker remains exempt from Boost" in summary
    assert "[[skill:intuitive-attack|Intuitive Attack]]" in summary
    assert "Boost alone does not grant that Skill" in summary
    assert "becomes active at its Conclusion" in summary
    assert "subsequent Orders or [[trait:aro|AROs]]" in summary
    assert "[[weapon:mines|Mines]] can trigger" in summary
    assert "Models **or Markers**" in summary
    assert "does not affect allies" in summary
    assert "enemy Model declares or performs an Order" in summary
    assert "enemy Model or Marker declares or executes a Skill" in mines["summary"]

    assert any(
        "enemy Camouflaged Marker inside its Trigger Area" in item
        for item in place["restrictions"]
    )
    assert any(
        "a valid non-camouflaged enemy" in item
        and "[[skill:intuitive-attack|Intuitive Attack]]" in item
        for item in place["restrictions"]
    )
    assert any(
        "active only in subsequent Orders" in item
        for item in place["effects"]
    )
    assert any(
        "[[trait:intuitive-attack|Intuitive Attack]] Trait" in item
        for item in intuitive["requirements"]
    )
    assert {49, 69, 72, 82} <= {
        item.get("page") for item in boost["citations"]
        if item["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert not any(
        item["recordId"] == "weapon:mines"
        for item in boost.get("relations", [])
    ), "The two triggering mechanics must not inherit one another"


def test_boost_and_mine_representations_stay_separate() -> None:
    records = _records()
    boost = records["trait:boost"]["summary"]
    mine = records["weapon:mines"]["summary"]
    drop_bears = records["weapon:drop-bears"]["summary"]
    wildparrot = records["weapon:wildparrot"]["summary"]

    assert "[[state:camouflaged|CAMO]]" in boost
    assert "[[state:impersonation-1|IMP-1]]" in boost
    assert "obstacle or too-small gap" in boost
    assert "Small Teardrop Template" in mine
    assert "without affecting any ally" in mine
    assert "cannot detonate during the Order" in drop_bears
    assert "a visible Mine Token" in drop_bears
    assert "they work like [[weapon:mines|E/M Mines]]" in wildparrot
    assert "WildParrots do not have that Trait" in wildparrot


@pytest.mark.parametrize(
    ("page", "source_excerpt"),
    (
        (49, "BS Weapon with the Intuitive Attack Trait"),
        (69, "when an enemy Model declares or performs an Order or ARO"),
        (69, "weapon is not triggered by Camouflage Markers (CAMO)"),
        (69, "there is also a non-Camouflaged Enemy inside its Zone of Control"),
        (69, "when the Order concludes, the CrazyKoala is considered to be in play"),
        (71, "A Drop Bear cannot detonate during the Order it is used in BS Mode"),
        (72, "enemy Model or Marker declares or executes a Skill or ARO"),
        (82, "A Deployable Weapon cannot be placed if there is an enemy Camouflage Marker"),
        (82, "there is a valid, non-camouflaged enemy inside the Trigger Area"),
        (82, "or an Intuitive Attack was made"),
        (82, "can be used in subsequent Orders/AROs"),
    ),
)
def test_boost_mine_source_conditions_if_pinned_pdf_is_available(
    page: int, source_excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 source PDF unavailable in checkout")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as document:
        printed = _normalized_text(document[page - 1].get_text())
    assert _normalized_text(source_excerpt) in printed, (page, source_excerpt)


def test_drop_bears_uses_and_rolls_differ_by_deployment_mode() -> None:
    records = _records()
    drop = records["weapon:drop-bears"]
    text = drop["summary"]
    assert "three shared [[trait:disposable-x|Disposable (3)]] uses" in text
    assert "**[[trait:deployable|Deployable]] Mode** needs no Roll" in text
    assert "a legal [[skill:intuitive-attack|Intuitive Attack]] uses an unmodified WIP Roll" in text
    assert "places no Token but expends one shared" in text
    assert "The BS Mode throw instead uses a [[trait:bs-weapon-ph|PH-based BS Attack]] Roll" in text
    assert "A failed throw also spends one use, without deploying a Token" in text
    assert "new Drop Bear cannot detonate during the same Order" in text
    assert "valid non-camouflaged enemy in the Trigger Area" in text

    intuitive = records["skill:intuitive-attack"]["facts"]
    placement = records["skill:place-deployable"]["facts"]
    disposable = records["trait:disposable-x"]["summary"]
    perimeter = records["trait:perimeter"]["facts"]
    assert any(
        "On a failed WIP Roll, do not place the weapon" in clause
        and "spend one use" in clause
        for clause in intuitive["effects"]
    )
    assert any(
        "without a Roll" in clause and "Conclusion of the Order" in clause
        for clause in placement["effects"]
    )
    assert "failed or invalid declaration" in disposable
    assert "Modes share charges" in disposable
    assert any(
        "replaces the usual Silhouette contact" in clause
        for clause in perimeter["requirements"]
    )
    assert any(
        "remains stationary" in clause and "Conclusion" in clause
        for clause in perimeter["effects"]
    )
    assert {49, 71, 82, 175, 181} <= {
        cite["page"] for cite in drop["citations"]
        if cite["sourceId"] == "n5-core-v5.3-pdf"
    }


@pytest.mark.parametrize(
    ("page", "source_excerpt"),
    (
        (49, "If the WIP Roll is failed, the Deployable Weapon is not placed"),
        (49, "one use must be considered spent"),
        (71, "A Drop Bear cannot detonate during the Order it is used in BS Mode"),
        (71, "Disposable (3) Trait is shared between all Modes"),
        (82, "with no Roll required"),
        (82, "can be used in subsequent Orders/AROs"),
        (175, "regardless of the success or failure of the Roll involved"),
        (175, "BS Weapon (PH). This weapon can make BS Attacks"),
    ),
)
def test_drop_bears_source_clauses_if_pinned_pdf_available(
    page: int, source_excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 core rules unavailable")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as document:
        page_text = _normalized_text(document[page - 1].get_text())
    assert _normalized_text(source_excerpt) in page_text, (page, source_excerpt)
