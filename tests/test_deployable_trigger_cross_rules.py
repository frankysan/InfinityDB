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



def test_mine_dispenser_inherits_only_drop_bears_bs_placement_semantics() -> None:
    records = _records()
    dispenser = records["weapon:mine-dispenser"]
    drop = records["weapon:drop-bears"]
    summary = dispenser["summary"]

    assert "uses the **BS Mode** placement rules" in summary
    assert "uses the user's BS Attribute, not [[trait:bs-weapon-ph|BS Weapon (PH)]]" in summary
    assert "**Failed shot and charges:**" in summary
    assert "places no Mine Token for that Roll" in summary
    assert "still consumes its declared [[trait:disposable-x|Disposable (2)]] use" in summary
    assert "consumes both uses when selected with both charges remaining" in summary
    assert "even if the Rolls fail" in summary
    assert "does not gain the [[trait:deployable|Deployable]] Mode" in summary
    assert "no-Roll [[skill:place-deployable|Place Deployable]] action" in summary
    assert "or [[skill:intuitive-attack|Intuitive Attack]]" in summary
    assert "It is not placed as a [[skill:camouflage|CAMO]] Marker" in summary
    assert "a valid non-camouflaged enemy is there too" in summary
    assert "cannot detonate during the Order in which it was fired" in summary
    assert "use that Mine's printed effects" in summary
    assert "uses" in drop["summary"] and "Deployable" in drop["summary"]
    assert {49, 71, 72, 82, 175, 181} <= {
        c["page"] for c in dispenser["citations"]
        if c["sourceId"] == "n5-core-v5.3-pdf"
    }
    edges = {(r["type"], r["recordId"]) for r in dispenser["relations"]}
    assert ("modifies-use-of", "weapon:drop-bears") in edges
    assert ("uses-effects-of", "weapon:mines") in edges
    assert ("uses-effects-of", "trait:double-shot") in edges
    assert ("uses-effects-of", "trait:disposable-x") in edges
    assert ("enables-use-of", "skill:speculative-attack") in edges
    assert ("enables-use-of", "skill:place-deployable") not in edges
    assert ("enables-use-of", "skill:intuitive-attack") not in edges
    assert ("uses-effects-of", "trait:bs-weapon-ph") not in edges


@pytest.mark.parametrize(
    ("page", "source_excerpt"),
    (
        (71, "In BS Weapon Mode, Drop Bears cannot be placed where there"),
        (71, "If you pass the Roll, the Drop Bear is successfully deployed"),
        (71, "A Drop Bear cannot detonate during the Order it is used in BS Mode"),
        (72, "same rules as Drop Bears in BS Mode"),
        (72, "The type of Mines in the Mine Dispenser are listed in brackets"),
        (175, "one is expended every time you declare"),
        (175, "regardless of the success or failure of the Roll involved"),
        (175, "if both uses remain unspent"),
        (49, "must employ a BS Weapon with the Intuitive Attack Trait"),
        (82, "Allows the user to place a single Token or Model"),
    ),
)
def test_mine_dispenser_mode_inheritance_matches_pinned_pdf(
    page: int, source_excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 source PDF unavailable")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as doc:
        text = _normalized_text(doc[page - 1].get_text())
    assert _normalized_text(source_excerpt) in text, (page, source_excerpt)



def test_pitcher_and_disco_delivery_lifecycle_keeps_objects_separate() -> None:
    records = _records()
    pitcher = records["weapon:pitcher"]
    disco = records["weapon:disco-baller"]
    activation = records["skill:activate-disco-ball"]
    repeater = records["equipment:deployable-repeater"]

    p = pitcher["summary"]
    assert "A failed BS Roll places no [[equipment:deployable-repeater|Repeater]] Token" in p
    assert "still spends one [[trait:disposable-x|Disposable (2)]] use" in p
    assert "a separate [[equipment:deployable-repeater|Deployable Repeater]]" in p
    assert "ARM 0, BTS 0, STR 1 and S 1" in p
    assert "not the [[skill:place-deployable|Place Deployable]] Skill" in p
    assert "at the Order's Conclusion" in p
    assert "never on a vertical surface" in p
    assert "If none remains, the Equipment is lost" in p
    assert "without requiring a Saving Roll" not in p
    assert "[[skill:place-deployable|Place Deployable]]" in repeater["summary"]
    assert {
        ("n5-faq-v0.1-en-pdf", 2), ("n5-faq-v0.1-en-pdf", 3),
        ("n5-core-v5.3-pdf", 73), ("n5-core-v5.3-pdf", 175),
        ("n5-core-v5.3-pdf", 186), ("n5-core-v5.3-pdf", 187),
    } <= {(c["sourceId"], c.get("page")) for c in pitcher["citations"]}

    d = disco["summary"]
    assert "A failed launcher BS Roll places no Disco Ball" in d
    assert "still expends its declared [[trait:disposable-x|Disposable]] use" in d
    assert "both are spent even if the Rolls fail" in d
    assert "The deployed Disco Ball has its own ARM, BTS, STR and S values" in d
    assert "not placed on a vertical surface" in d
    assert "if none exists, that deployment is lost" in d
    assert "A failed activation WIP Roll does not restore the Eclipse Template" in d
    assert "not another launcher charge" in d
    assert "when the Ball is destroyed" in d
    assert "The source gives the Disco Ball ARM 0, BTS 0, STR 1 and S 1" in d
    assert "WIP +3" in activation["summary"]
    assert "Disposable" not in activation["summary"]
    assert {
        ("n5-faq-v0.1-en-pdf", 2), ("n5-faq-v0.1-en-pdf", 3),
        ("n5-core-v5.3-pdf", 71), ("n5-core-v5.3-pdf", 175),
        ("n5-core-v5.3-pdf", 186),
    } <= {(c["sourceId"], c.get("page")) for c in disco["citations"]}

    assert not any(
        x["type"] == "enables-use-of"
        and x["recordId"] == "skill:place-deployable"
        for x in pitcher.get("relations", []) + disco.get("relations", [])
    )


@pytest.mark.parametrize(
    ("page", "excerpt"),
    (
        (2, "The Token must be fully supported by the surface"),
        (2, "it cannot be placed on a vertical surface"),
        (3, "if this is not possible, the Deployable will be lost"),
        (3, "This also applies to weapons that place a Deployable Weapon"),
        (3, "such as Disco Ballers, Pitchers, and Drop Bears (BS Mode)"),
    ),
)
def test_fired_deployable_faq_covers_both_launchers(
    page: int, excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    faq = ROOT / "data/pdf/faq/n5-faqs-v0-1-en.pdf"
    if not faq.exists():
        pytest.skip("Pinned N5 FAQ v0.1 unavailable")
    assert hashlib.sha256(faq.read_bytes()).hexdigest() == (
        "7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa"
    )
    with pdf.open(faq) as document:
        found = _normalized_text(document[page - 1].get_text())
    assert _normalized_text(excerpt) in found, (page, excerpt)


@pytest.mark.parametrize(
    ("page", "excerpt"),
    (
        (71, "If you pass the Roll, a Disco Ball is successfully"),
        (71, "At the start of the States Phase, the Disco Ball deactivates"),
        (71, "Only allied Disco Balls can be Activated this way"),
        (73, "A successful BS Roll allows players to place a Deployable Repeater"),
        (175, "one is expended every time you declare"),
        (175, "This Burst MOD can only be applied if both uses"),
        (186, "DEPLOYABLE"),
    ),
)
def test_delivery_lifecycle_is_printed_in_pinned_core(
    page: int, excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 source PDF unavailable")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as document:
        found = _normalized_text(document[page - 1].get_text())
    assert _normalized_text(excerpt) in found, (page, excerpt)



def test_deployed_repeater_fired_and_placed_paths_share_object_rules() -> None:
    """Delivery Skill differs; the battlefield token still uses Repeater rules."""
    records = _records()
    equipment = records["equipment:deployable-repeater"]
    text = equipment["summary"]
    pitcher = records["weapon:pitcher"]["summary"]
    hacking = records["rule:hacking-area"]
    repeater = records["equipment:repeater"]

    assert "[[skill:place-deployable|Place Deployable]] action" in text
    assert "[[weapon:pitcher|Pitcher]]" in text
    assert "[[skill:bs-attack|BS Attack]]" in text
    assert "without declaring [[skill:place-deployable|Place Deployable]]" in text
    assert "ARM 0, BTS 0, STR 1 and S 1" in text
    assert "[[state:unconscious|Unconscious State]]" in text
    assert "[[state:dead|Dead State]]" in text
    assert "destroyed Token no longer extends a Hacking Area" in text
    assert "[[rule:hacking-area|Hacking Areas]]" in text
    assert "[[equipment:firewall|Firewall]]" in text
    assert "The Token itself does not declare Hacking Programs" in text
    assert "not the [[skill:place-deployable|Place Deployable]] Skill" in pitcher
    assert "enemy [[equipment:repeater]] or [[equipment:deployable-repeater]]" in (
        hacking["summary"]
    )
    assert "When an enemy [[skill:hacker]] uses this" in " ".join(
        repeater["facts"]["effects"]
    )
    assert {55, 56, 73, 175, 186} <= {
        cite["page"] for cite in equipment["citations"]
        if cite["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert equipment["relations"] == [
        {"type": "uses-effects-of", "recordId": "equipment:repeater"}
    ]
    assert max(map(len, text.split("\n\n"))) <= 350


def test_disco_ball_states_phase_removes_template_not_ball() -> None:
    records = _records()
    disco = records["weapon:disco-baller"]["summary"]
    activation = records["skill:activate-disco-ball"]

    assert "At the start of the States Phase the Disco Ball deactivates" in disco
    assert "the deployed Ball remains until it is destroyed or the game ends" in disco
    assert "A failed activation WIP Roll does not restore the Eclipse Template" in disco
    assert "not another launcher charge" in disco
    assert "WIP +3" in activation["summary"]
    assert "Enemy Disco Balls cannot be activated" in activation["summary"]
    assert "Conclusion Step" in activation["summary"]
    assert "The Template is removed at the start of the next States Phase" in (
        activation["summary"]
    )
    assert any(
        "when the Ball is destroyed" in clause
        for clause in activation["facts"]["effects"]
    )
    assert "Disposable" not in activation["summary"]


@pytest.mark.parametrize(
    ("page", "excerpt"),
    (
        (55, "Zone of Control of Repeaters and Deployable Repeaters"),
        (55, "any ARO or Hacking Program using the Enemy Repeater"),
        (56, "There can be no reaction against a Repeater"),
        (56, "The Deployable Repeater is a piece of Equipment that contains a"),
        (56, "ARM"),
        (71, "At the start of the States Phase, the Disco Ball deactivates"),
        (71, "A deployed Disco Ball remains on the table until the end"),
        (71, "If the Disco Ball is destroyed remove the Circular Template"),
        (73, "A successful BS Roll allows players to place a Deployable Repeater"),
        (175, "Deployable item enters Unconscious State"),
        (186, "DEPLOYABLE"),
    ),
)
def test_deployed_repeater_and_disco_ball_lifecycle_has_pinned_sources(
    page: int, excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned English N5.3 source PDF unavailable")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as doc:
        normalized = _normalized_text(doc[page - 1].get_text())
    assert _normalized_text(excerpt) in normalized, (page, excerpt)



def test_fastpanda_and_wildparrot_remain_distinct_deployed_objects() -> None:
    records = _records()
    fast = records["equipment:fastpanda"]
    wild = records["weapon:wildparrot"]

    fast_summary = fast["summary"]
    assert "[[trait:disposable-x|Disposable (1)]]" in fast_summary
    assert "[[trait:indiscriminate|Indiscriminate]]" in fast_summary
    assert "[[trait:perimeter|Perimeter]]" in fast_summary
    assert "[[skill:place-deployable|Place Deployable]]" in fast_summary
    assert "A passable route wide enough for its S1 Silhouette" in fast_summary
    assert "Placement needs no Roll" in fast_summary
    assert "at the Order's Conclusion" in fast_summary
    assert "ARM 0, BTS 0, STR 1, S 1" in fast_summary
    assert "[[equipment:repeater|Repeater]]" in fast_summary
    assert "[[rule:hacking-area|Hacking Areas]]" in fast_summary
    assert "Hacking Area extension cease" in fast_summary
    assert "does not travel toward enemies or detonate" in fast_summary
    assert fast["relations"] == [
        {"type": "uses-effects-of", "recordId": "equipment:repeater"}
    ]
    assert {56, 82, 175, 186} <= {
        c.get("page") for c in fast["citations"]
        if c["sourceId"] == "n5-core-v5.3-pdf"
    }

    wild_summary = wild["summary"]
    assert "using [[skill:place-deployable]] or" in wild_summary
    assert "[[skill:intuitive-attack|Intuitive Attack]]" in wild_summary
    assert "A legal [[skill:intuitive-attack|Intuitive Attack]]" in wild_summary
    assert "failure places no Token" in wild_summary
    assert "[[trait:disposable-x|Disposable (1)]]" in wild_summary
    assert "Order's Conclusion" in wild_summary
    assert "cannot trigger during its own placement Order" in wild_summary
    assert "Its visible S1 Token or Model has ARM 0, BTS 0 and STR 1" in wild_summary
    assert "[[weapon:mines|E/M Mines]]" in wild_summary
    assert "WildParrots do not have that Trait" in wild_summary
    assert "Non-Lethal" in wild["facts"]["sourceNotes"][0]
    assert "absent from the current imported Army Trait list" in (
        wild["facts"]["sourceNotes"][0]
    )
    assert {49, 74, 82, 175} <= {
        c.get("page") for c in wild["citations"]
        if c["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert ("uses-effects-of", "equipment:repeater") not in {
        (r["type"], r["recordId"]) for r in wild["relations"]
    }
    assert ("modifies-use-of", "weapon:mines") in {
        (r["type"], r["recordId"]) for r in wild["relations"]
    }
    assert max(map(len, fast_summary.split("\n\n"))) <= 350
    assert max(map(len, wild_summary.split("\n\n"))) <= 350


@pytest.mark.parametrize(
    ("page", "excerpt"),
    (
        (49, "If the WIP Roll is failed, the Deployable Weapon is not placed"),
        (56, "Repeaters extend the Hacking Area of all Hackers"),
        (69, "Some examples of Perimeter Weapons are CrazyKoalas, MadTraps"),
        (74, "WildParrot Token or Model is placed instead of a Camouflage Marker"),
        (74, "Intuitive Attack, Disposable"),
        (74, "FASTPANDA"),
        (82, "The Weapon or piece of Equipment will be placed at the Conclusion"),
        (82, "The path cannot be blocked by an impassable obstacle"),
        (175, "one is expended every time you declare"),
        (186, "INDISCRIMINATE, PERIMETER"),
    ),
)
def test_fastpanda_wildparrot_mechanics_match_pinned_core(
    page: int, excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 source PDF unavailable in checkout")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as doc:
        found = _normalized_text(doc[page - 1].get_text())
    assert _normalized_text(excerpt) in found, (page, excerpt)



def test_dazer_support_equipment_placement_and_persistent_effects() -> None:
    records = _records()
    dazer = records["equipment:dazer"]
    summary = dazer["summary"]
    effects = dazer["facts"]["effects"]
    source_note = dazer["facts"]["sourceNotes"][0]
    assert "[[trait:deployable|Deployable]]" in summary
    assert "[[trait:disposable-x|Disposable (3)]]" in summary
    assert "[[skill:place-deployable|Place Deployable]]" in summary
    assert "in Silhouette contact without a Roll" in summary
    assert "Dazer lacks [[trait:perimeter|Perimeter]]" in summary
    assert "effect area, not the placement distance" in summary
    assert "at the Order's Conclusion" in summary
    assert "Difficult Terrain of infinite height" in summary
    assert "[[skill:terrain|Terrain]] (Total)" in summary
    assert "with the Movement Label" in summary
    assert "ARM 0, BTS 0 and STR 1" in summary
    assert "An eligible enemy [[equipment:deactivator|Deactivator]]" in summary
    assert "After removal, it no longer generates Difficult Terrain" in summary
    assert "until the end of the game or until destroyed" in " ".join(effects)
    assert "English N5.3 detailed profile (p. 121) specify S0" in source_note
    assert "English chart (p. 186) specifies S1" in source_note
    assert "No official correction" in source_note
    assert {82, 121, 175, 186} <= {
        cite["page"] for cite in dazer["citations"]
        if cite["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert not any(
        item["recordId"] == "trait:perimeter"
        for item in dazer.get("relations", [])
    )
    assert max(map(len, summary.split("\n\n"))) <= 350
    place = records["skill:place-deployable"]["facts"]["effects"]
    assert any(
        "without a Roll" in clause and "Conclusion" in clause
        for clause in place
    )
    deactivator = records["equipment:deactivator"]["facts"]
    assert any(
        "[[trait:deployable]]" in clause
        for clause in deactivator["requirements"]
    )


@pytest.mark.parametrize(
    ("page", "excerpt"),
    (
        (82, "place a single Token or Model on the game table"),
        (82, "with no Roll required"),
        (82, "Silhouette contact"),
        (82, "Once the Token has been placed on the table"),
        (121, "The Dazer is Deployable Equipment that creates a Terrain Zone"),
        (121, "Difficult Terrain area of infinite"),
        (121, "Troopers with the Terrain (Total) Special Skill"),
        (121, "A deployed Dazer remains on the table until the end"),
        (121, "A Deactivator can only target enemy Deployable Weapons"),
        (175, "Deployable item enters Unconscious State"),
        (186, "DAZER"),
    ),
)
def test_dazer_lifecycle_matches_pinned_english_core(
    page: int, excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as document:
        printed = _normalized_text(document[page - 1].get_text())
    assert _normalized_text(excerpt) in printed, (page, excerpt)



def test_deactivator_removal_and_persistent_effects_stay_distinct() -> None:
    records = _records()
    deactivator = records["equipment:deactivator"]
    summary = deactivator["summary"]

    assert "enemy deployed [[trait:deployable|Deployable]]" in summary
    assert "the user's LoF or [[trait:zone-of-control-zc|Zone of Control]]" in summary
    assert "never a [[state:camouflaged|Camouflage Marker]]" in summary
    assert "not [[skill:place-deployable|Place Deployable]]" in summary
    assert "WIP [[rule:face-to-face-rolls|Normal Roll]]" in summary
    assert "Range MODs only" in summary
    assert "not [[skill:mimetism|Mimetism]] or Cover" in summary
    assert "does **not** prevent" in summary
    assert "triggering during that same Order" in summary
    assert "[[equipment:dazer|Dazer]] ends its persistent area effect" in summary
    assert "[[equipment:fastpanda|FastPanda]]" in summary
    assert "[[equipment:deployable-repeater|Deployable Repeater]]" in summary
    assert "[[equipment:deployable-cover|Deployable Cover]]" in summary
    assert "removes its scenery-based Cover effect" in summary
    assert "[[skill:activate-disco-ball|Activate Disco Ball]]" in summary
    assert "reactivate an **allied** Ball" in summary
    assert "It does not remove the Ball" in summary
    assert "does not change Deactivator's enemy-only targeting rule" in summary
    assert {71, 56, 121, 122} <= {
        c["page"] for c in deactivator["citations"]
        if c["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert max(map(len, summary.split("\n\n"))) <= 350

    req = deactivator["facts"]["requirements"]
    eff = deactivator["facts"]["effects"]
    restrictions = deactivator["facts"]["restrictions"]
    assert any("enemy Weapon or piece of Equipment" in x for x in req)
    assert any("cannot be a Camouflage Marker" in x for x in req)
    assert any("removed from the game table" in x for x in eff)
    assert any("Range MODs only" in x for x in restrictions)
    assert any("triggering during the current Order" in x for x in restrictions)

    assert "no longer generates Difficult Terrain" in records["equipment:dazer"]["summary"]
    assert "Hacking Area extension cease" in records["equipment:fastpanda"]["summary"]
    assert "no longer extends a Hacking Area" in (
        records["equipment:deployable-repeater"]["summary"]
    )
    assert "Scenery Element" in records["equipment:deployable-cover"]["summary"]
    activate = records["skill:activate-disco-ball"]
    assert "allied" in activate["summary"]
    assert "Enemy Disco Balls cannot be activated" in activate["summary"]
    assert "WIP +3" in activate["summary"]
    assert "The Template is removed at the start of the next States Phase" in (
        activate["summary"]
    )


@pytest.mark.parametrize(
    ("page", "excerpt"),
    (
        (121, "LoF or ZoC"),
        (121, "only target enemy Deployable Weapons"),
        (121, "but never Camouflage Markers"),
        (121, "by passing a Normal WIP Roll"),
        (121, "Deployable Cover, Deployable"),
        (121, "triggering during the current Order"),
        (121, "MODs for Range"),
        (121, "removed from the game table"),
        (71, "Only allied Disco Balls can be Activated this way"),
        (71, "By making a successful WIP +3 Normal Roll"),
        (175, "Deployable. This weapon or piece of Equipment may be deployed"),
    ),
)
def test_deactivator_and_allied_activation_pinned_source_clauses(
    page: int, excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 English PDF unavailable")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as document:
        text = _normalized_text(document[page - 1].get_text())
    assert _normalized_text(excerpt) in text, (page, excerpt)



def test_deactivator_same_order_devices_keep_distinct_trigger_rules() -> None:
    records = _records()
    reference = records["equipment:deactivator"]
    text = reference["summary"]
    assert "does **not** prevent an eligible device from triggering" in text
    assert "**Template triggers:**" in text
    assert "A [[state:camouflaged|CAMO]] Marker is not a Deactivator target" in text
    assert "A revealed [[weapon:mines|Mine]] may still trigger this Order" in text
    assert "enemy Model/Marker without affecting an ally" in text
    assert "[[weapon:cybermine|Cybermines]] share this trigger condition" in text
    assert "[[skill:reset|Reset]], not [[skill:dodge|Dodge]]" in text
    assert "**Contact-seeking devices:** [[trait:boost|Boost]]" in text
    assert "Crazykoalas/MadTraps" in text
    assert "eligible enemy **Model**" in text
    assert "passable route to Silhouette contact" in text
    assert "Exempt Markers do not trigger it" in text
    assert "[[rule:face-to-face-rolls|Normal Dodge Roll]]" in text
    assert "**Automated turret reactions:**" in text
    assert "[[weapon:armed-turret|Armed Turret]]" in text
    assert "[[skill:bs-attack|BS Attack]] or [[skill:cc-attack|CC Attack]]" in text
    assert "active enemy **Model**, never a Marker" in text
    assert "within LoF or in Silhouette contact" in text
    assert "This is not [[weapon:mines|Mine]] or [[trait:boost|Boost]] detonation" in text
    assert max(map(len, text.split("\n\n"))) <= 350

    core_pages = {
        c["page"] for c in reference["citations"]
        if c["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert {69, 70, 72, 121} <= core_pages
    assert "enemy Model or Marker" in records["weapon:mines"]["summary"]
    assert "even if that ally is Unconscious" not in text
    assert "[[skill:reset]]" in records["weapon:cybermine"]["summary"]
    assert "Only a successful [[skill:dodge]]" in records["trait:boost"]["summary"]
    assert "against an active enemy **Model**, not a Marker" in (
        records["weapon:armed-turret"]["summary"]
    )
    assert reference["relations"] == [
        {"type": "ignores-modifiers-from", "recordId": "skill:mimetism"}
    ]


@pytest.mark.parametrize(
    ("page", "excerpt"),
    (
        (121, "Passing the WIP Roll does not prevent the enemy"),
        (121, "from triggering during the current Order"),
        (121, "but never Camouflage Markers"),
        (69, "triggered when an enemy Model declares or performs an Order"),
        (69, "The weapon will not trigger if the path"),
        (69, "not triggered by Camouflage Markers"),
        (69, "The only way to avoid this attack is a successful Normal"),
        (70, "an active Enemy Model"),
        (70, "but not a Marker"),
        (70, "within its LoF or in Silhouette contact"),
        (72, "enemy Model or Marker declares or executes a Skill or ARO"),
        (72, "A Mine never triggers if the Small Teardrop Template would affect an ally"),
        (72, "they can only be evaded with a Reset, rather than a Dodge"),
        (72, "Replace the Camouflage Marker"),
    ),
)
def test_deactivator_hostile_device_clauses_in_pinned_n53_pdf(
    page: int, excerpt: str,
) -> None:
    pdf = pytest.importorskip("pymupdf")
    if not SOURCE.exists():
        pytest.skip("Pinned N5.3 English PDF unavailable")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PINNED_PDF_SHA256
    with pdf.open(SOURCE) as document:
        page_text = _normalized_text(document[page - 1].get_text())
    assert _normalized_text(excerpt) in page_text, (page, excerpt)
