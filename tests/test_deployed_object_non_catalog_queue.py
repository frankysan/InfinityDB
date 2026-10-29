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
    assert len(validate_reviews(manifest, curated, candidates)) == 3

    for key, bad_value, error in (
        ("classification", "fully-reviewed-four-stat-object", "classification"),
        ("summaryEvidence", "text that does not exist", "summary evidence"),
        ("factsEvidence", ["fabricated effect"], "detailed evidence"),
        ("sourcePages", [999], "citation"),
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


def test_pinned_non_catalog_discovery_preserves_unreviewed_queue() -> None:
    report = audit_non_catalog_candidates(CURATED, REVIEWS)
    assert report["scope"] == "non-catalog-keyword-discovery-not-object-inventory"
    assert len(report["curatedSourceSha256"]) == 64
    assert report["reviewedCount"] == 3
    assert report["candidateCount"] >= report["reviewedCount"]
    selected = {
        row["recordId"]: row for row in report["candidates"]
    }
    for record_id in (
        "skill:minelayer", "skill:place-deployable", "skill:request-speedball",
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


def test_non_catalog_cli_reports_open_queue_without_publishing_objects(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_deployed_object_non_catalog_queue"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Candidate definitions:" in output
    assert "Reviewed classifications: 3" in output
    assert "Awaiting manual review:" in output
