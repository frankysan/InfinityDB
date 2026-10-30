"""Non-catalog N5.3 battlefield-game-element discovery remains audit-only."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from tools.audit_deployed_object_non_catalog_queue import (
    audit_non_catalog_candidates,
    candidate_mentions,
    main,
    validate_reviews,
)

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
REVIEWS = ROOT / "config/validation/deployed-object-non-catalog-reviews.json"


def test_non_catalog_queue_does_not_infer_objects_from_generic_token_language() -> None:
    curated = {"records": [
        {
            "id": "skill:review-me", "kind": "skill",
            "composition": {"role": "definition"}, "summary": "Call a supply Token.",
            "facts": {"effects": ["A Token arrives with a supply item."]},
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 84}],
        },
        {
            "id": "rule:other", "kind": "rule",
            "composition": {"role": "definition"}, "summary": "A background rule.",
            "facts": {"restrictions": ["Do not place Scenery Elements here."]},
        },
        {
            "id": "weapon:excluded", "kind": "weapon",
            "composition": {"role": "definition"}, "summary": "A Deployable.",
        },
        {
            "id": "scenario:excluded", "kind": "scenario",
            "composition": {"role": "definition"}, "summary": "A scenery Token.",
        },
    ]}
    matches = candidate_mentions(curated)
    assert [entry["recordId"] for entry in matches] == [
        "rule:other", "skill:review-me",
    ]
    assert not matches[0]["summaryMatches"]
    assert list(matches[0]["details"]) == ["restrictions"]
    assert matches[1]["summaryMatches"]
    assert matches[1]["citations"] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 84},
    ]


def test_non_catalog_reviews_fail_closed_on_evidence_and_classification() -> None:
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    manifest = json.loads(REVIEWS.read_text(encoding="utf-8"))
    candidates = candidate_mentions(curated)
    assert len(validate_reviews(manifest, curated, candidates)) == 48

    for key, bad_value, error in (
        ("classification", "fully-reviewed-four-stat-object", "classification"),
        ("summaryEvidence", "text that does not exist", "summary evidence"),
        ("factsEvidence", ["fabricated effect"], "detailed evidence"),
        ("sourcePages", [999], "PDF-only provenance"),
        ("objectProfile", {"ARM": 0}, "review scope"),
    ):
        changed = copy.deepcopy(manifest)
        changed["reviews"][-1][key] = bad_value
        with pytest.raises(ValueError, match=error):
            validate_reviews(changed, curated, candidates)

    repeated = copy.deepcopy(manifest)
    repeated["reviews"].append(copy.deepcopy(repeated["reviews"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_reviews(repeated, curated, candidates)

    missing = copy.deepcopy(manifest)
    missing["reviews"][0]["recordId"] = "skill:not-in-source"
    with pytest.raises(ValueError, match="No current"):
        validate_reviews(missing, curated, candidates)

    # Some cited Trait definitions have only summary text. A future detailed
    # clause must not silently inherit that summary-only review decision.
    detailed = copy.deepcopy(curated)
    boost = next(record for record in detailed["records"] if record["id"] == "trait:boost")
    boost["facts"] = {"effects": ["New Boost deployment behavior."]}
    with pytest.raises(ValueError, match="detailed evidence"):
        validate_reviews(manifest, detailed, candidate_mentions(detailed))

    # The six independently PDF-verified decisions have no maintained N5.3
    # citation yet. Their manually checked evidence is pinned separately,
    # and they must be migrated when the curated source gains the citation.
    for key, bad in (
        ("sourcePages", [999]),
        ("citationStatus", "maintained-source-cited"),
        ("pdfExcerpt", "a different quote"),
    ):
        changed = copy.deepcopy(manifest)
        changed["reviews"][-1][key] = bad
        with pytest.raises(ValueError, match="PDF-only provenance"):
            validate_reviews(changed, curated, candidates)

    changed_citation = copy.deepcopy(curated)
    transmutation = next(
        record for record in changed_citation["records"]
        if record["id"] == "skill:transmutation"
    )
    pdf_cites = [
        cite for cite in transmutation["citations"]
        if cite["sourceId"] == "n5-core-v5.3-pdf"
    ]
    if pdf_cites:
        pdf_cites[0]["page"] = 999
    else:
        transmutation["citations"].append({
            "sourceId": "n5-core-v5.3-pdf", "page": 117,
        })
    with pytest.raises(ValueError, match="PDF-only provenance"):
        validate_reviews(manifest, changed_citation, candidate_mentions(changed_citation))


def test_pinned_non_catalog_discovery_preserves_unreviewed_queue() -> None:
    report = audit_non_catalog_candidates(CURATED, REVIEWS)
    assert report["scope"] == "non-catalog-keyword-discovery-not-object-inventory"
    assert len(report["curatedSourceSha256"]) == 64
    assert report["reviewedCount"] == 48
    assert report["candidateCount"] == 49
    # Access Width now mentions scenery gate Tokens; it is a new audit
    # candidate, not automatically approved as a deployed object.
    assert [row["recordId"] for row in report["unreviewed"]] == [
        "rule:access-width",
    ]
    assert set(report["unreviewed"][0]["details"]) == {"effects", "restrictions"}
    assert not next(
        entry["reviewed"] for entry in report["candidates"]
        if entry["recordId"] == "rule:access-width"
    )
    assert len(report["reviewedPdfOnly"]) in (0, 6)
    selected = {
        row["recordId"]: row for row in report["candidates"]
    }
    for record_id in (
        "skill:minelayer", "skill:place-deployable", "skill:request-speedball",
        "skill:request-specball", "skill:remdriver",
        "skill:pick-up-supply-boxes", "rule:peripheral-type:ancillary",
        "rule:scenario:carrying-supply-boxes", "term:token",
        "term:state-token", "term:deployable-equipment",
        "term:deployable-weapon", "term:scenery-element",
        "trait:deployable", "trait:perimeter", "trait:boost",
        "skill:intuitive-attack", "skill:dodge", "skill:stealth",
        "skill:cautious-movement", "rule:guts-roll",
        "rule:peripheral-type:control", "rule:peripheral-type:cyberplug",
        "state:camouflaged", "state:holomask",
    ):
        assert selected[record_id]["reviewed"]
        assert selected[record_id]["citations"]
    assert {
        entry["recordId"] for entry in report["unreviewed"]
    }.isdisjoint({
        decision["recordId"] for decision in report["reviews"]
    })
    speedball = next(
        decision for decision in report["reviews"]
        if decision["recordId"] == "skill:request-speedball"
    )
    assert speedball["classification"] == "support-state-token-not-standard-deployable"
    assert speedball["sourcePages"] == [84]
    assert "State Tokens" in speedball["caveat"]
    reviewed = {decision["recordId"]: decision for decision in report["reviews"]}
    assert reviewed["skill:request-specball"]["classification"] == (
        "support-state-token-not-standard-deployable"
    )
    assert reviewed["rule:peripheral-type:ancillary"]["classification"] == (
        "deployed-peripheral-trooper-separate-domain"
    )
    assert reviewed["rule:scenario:carrying-supply-boxes"]["classification"] == (
        "scenario-object-outside-weapon-equipment"
    )
    assert reviewed["term:state-token"]["factsEvidence"] == []
    assert reviewed["trait:boost"]["factsEvidence"] == []
    assert reviewed["trait:perimeter"]["classification"] == (
        "placement-trait-not-object-identity"
    )
    assert reviewed["rule:peripheral-type:control"]["classification"] == (
        "peripheral-role-token-not-object"
    )
    assert reviewed["rule:peripheral-type:cyberplug"]["classification"] == (
        "peripheral-mode-token-not-object"
    )
    assert reviewed["skill:infiltration"]["classification"] == (
        "deployment-failure-removes-existing-deployables"
    )
    assert reviewed["rule:coordinated-orders"]["classification"] == (
        "role-token-and-delivery-choice-not-object"
    )
    assert reviewed["rule:hacking-area"]["classification"] == (
        "existing-repeater-interaction-not-object"
    )
    pdf_only_ids = {
        "skill:frenzy",
        "state:possessed",
        "rule:command-token-strategic-use",
        "skill:counterintelligence",
        "skill:inspiring-leadership",
        "skill:transmutation",
    }
    assert {entry["recordId"] for entry in report["reviewedPdfOnly"]} == (
        pdf_only_ids if report["reviewedPdfOnly"] else set()
    )
    assert {
        entry["recordId"] for entry in report["missingMaintainedN5Citation"]
    } == {entry["recordId"] for entry in report["reviewedPdfOnly"]}
    assert reviewed["skill:transmutation"]["classification"] == (
        "trooper-profile-representation-not-deployable"
    )
    assert reviewed["skill:frenzy"]["classification"] == (
        "indirect-deployable-wounds-not-eligible"
    )


def test_non_catalog_cli_reports_open_queue_without_publishing_objects(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_deployed_object_non_catalog_queue"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Candidate definitions:" in output
    assert "Candidate definitions: 49" in output
    assert "Reviewed classifications: 48" in output
    assert "Awaiting manual review: 1" in output
    assert "rule:access-width: effects, restrictions" in output
    count = 6 if any(
        review.get("citationStatus") == "pdf-verified-manifest-only"
        for review in json.loads(REVIEWS.read_text(encoding="utf-8"))["reviews"]
    ) else 0
    assert f"Reviewed with audit-only PDF citation: {count}" in output
    assert f"Definitions missing maintained N5.3 PDF citation: {count}" in output
