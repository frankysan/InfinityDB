"""Regression coverage for confirmed 0.10.1 player-reference corrections."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated" / "rules" / "n5-core-v5.3.json"


def _records() -> dict[str, dict]:
    document = json.loads(CURATED.read_text(encoding="utf-8"))
    return {record["id"]: record for record in document["records"]}


def test_impersonation_2_does_not_erase_ordinary_discover_modifiers() -> None:
    record = _records()["state:impersonation-2"]
    summary = record["summary"]
    explanation = " ".join(record["facts"]["clarifications"])
    assert "unmodified" not in summary.casefold()
    assert "ordinary [[skill:discover|Discover]] MODs still apply" in summary
    for concept in ("Range", "Cover", "Mimetism", "IMP-1", "Biometric Visor"):
        assert concept in explanation


def test_stealth_qualifies_deployables_and_mixed_activation() -> None:
    record = _records()["skill:stealth"]
    text = " ".join(
        [record["summary"], *record["facts"]["effects"], *record["facts"]["restrictions"]]
    )
    for concept in (
        "[[trait:deployable|Deployable]] Weapons and Equipment",
        "becomes [[skill:idle|Idle]]",
        "Marker form",
    ):
        assert concept in text
    # The original mechanics remain in Effects/Restrictions; published
    # examples explain the distinct automatic weapon, ARO and Marker cases.
    assert len(record["facts"]["clarifications"]) == 3
    mines, mixed, marker = record["facts"]["clarifications"]
    assert "**[[trait:deployable|Deployables]] still trigger:**" in mines
    assert "Mine" in mines
    assert "[[trait:zone-of-control-zc|Zone of Control]]" in mines
    assert "[[skill:sixth-sense|Sixth Sense]]" in mines
    assert "[[skill:combat-instinct|Combat Instinct]]" in mines
    assert "**Mixed-activation example:**" in mixed
    assert "[[skill:peripheral|Peripheral]]" in mixed
    assert "other activated Trooper independently generates" in mixed
    assert "reaction becomes [[skill:idle|Idle]]" in mixed
    assert "does grant a [[trait:aro|ARO]]" in mixed
    assert "**Stealth in Marker form:**" in marker
    assert "optional Automatic Skill" in marker
    assert "must announce" in marker
    citations = {(c["sourceId"], c.get("page")) for c in record["citations"]}
    assert citations >= {
        ("n5-core-v5.3-pdf", 112),
        ("n5-core-v5.3-es-pdf", 114),
        ("n5-faq-v0.1-en-pdf", 2),
        ("n5-faq-v0.1-es-pdf", 2),
    }
    assert record["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:cautious-movement"}
    ]


def test_deployable_cover_explains_saving_cap_and_eligibility() -> None:
    record = _records()["equipment:deployable-cover"]
    effects = " ".join(record["facts"]["effects"])
    restrictions = " ".join(record["facts"]["restrictions"])
    for concept in (
        "Silhouette contact",
        "partial-obscuration",
        "does not stack",
        "at 12 before",
        "before PS",
    ):
        assert concept in effects
    assert "N5 FAQ v0.1" in restrictions


def test_tinbot_names_shared_eligibility_and_non_stacking() -> None:
    text = _records()["equipment:tinbot"]["summary"]
    for concept in (
        "[[state:isolated|Isolated]]",
        "Null State",
        "Fireteam",
        "once per Order or reaction",
        "most advantageous",
        "State Token",
    ):
        assert concept in text
    assert "\n\n" in text


def test_tinbot_shared_options_and_inactive_owner_are_explained() -> None:
    records = _records()
    family = records["equipment:tinbot"]
    text = " ".join([family["summary"], *family["facts"]["clarifications"]])
    for phrase in (
        "Null State",
        "Fireteam",
        "do not block Movement or LoF",
        "cannot be selected as targets for any Skill",
        "[[state:dead|Dead State]]",
        "[[equipment:tinbot-firewall|TinBot: Firewall]]",
        "stronger -6 WIP MOD",
        "+3 [[equipment:firewall|Firewall]] Saving Roll",
        "enters [[state:isolated|Isolated]] or leaves the Fireteam",
    ):
        assert phrase in text
    source_pages = {
        citation["page"] for citation in family["citations"]
        if citation["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert source_pages == {127}
    for variant in (
        "firewall", "neurocinetics", "albedo", "discover", "ecm-guided", "repeater"
    ):
        record = records[f"equipment:tinbot-{variant}"]
        assert "[[equipment:tinbot]]" in record["summary"]
        assert {"type": "variant-of", "recordId": "equipment:tinbot"} in record["relations"]
    fireteam = records["rule:fireteam-general"]
    shared = " ".join(fireteam["facts"]["rules"])
    assert "**Shared [[equipment:tinbot|TinBot]]:**" in shared
    assert "[[equipment:tinbot|TinBot]]" in shared
    assert "Sharing stops if the owner leaves the Fireteam" in shared


def test_fireteam_type_counts_are_creation_only() -> None:
    record = _records()["rule:fireteam-general"]
    assert "formation requirements" in record["summary"]
    assert "Type does not change" in " ".join(record["facts"]["rules"])
    assert {"sourceId": "n5-faq-v0.1-en-pdf", "page": 3} in record["citations"]
    javascript = (
        ROOT / "src" / "infinity_db" / "web" / "static" / "fireteams.js"
    ).read_text(encoding="utf-8")
    assert "badge(`Formation ${fireteamTypeLabel(type)}`)" in javascript


def test_kobra_cc_attribute_link_is_not_weapon_trait() -> None:
    records = _records()
    summary = records["weapon:kobra-pistol"]["summary"]
    assert "Trooper’s [[attribute:cc|CC]] Attribute" in summary
    assert "Trooper’s [[trait:cc|CC]] Attribute" not in summary
    cc = records["weapon:kobra-pistol-cc"]
    note = cc["facts"]["sourceNotes"][0]
    assert "**[[trait:cc|CC]] Mode:**" in summary
    assert "Its [[trait:cc|CC]] Mode" in cc["summary"]
    assert "[[trait:cc|CC]]" in note
    assert "print one Saving Roll" in note
    assert "[[trait:anti-materiel|Anti-materiel]]" in (
        cc["facts"]["sourceNotes"][1]
    )
