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
