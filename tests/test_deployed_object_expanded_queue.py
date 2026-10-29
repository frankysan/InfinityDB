"""Expanded non-catalog battlefield-element discovery remains audit-only."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from tools.audit_deployed_object_expanded_queue import (
    audit_expanded_candidates,
    expanded_mentions,
    main,
    validate_reviews,
)

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
REVIEWS = ROOT / "config/validation/deployed-object-expanded-reviews.json"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"


def test_extended_scan_is_distinct_from_original_token_keyword_scan() -> None:
    curated = {"records": [
        {
            "id": "rule:console-example", "kind": "rule",
            "composition": {"role": "definition"}, "summary": "Place two Consoles.",
            "facts": {"effects": ["Use a Console Marker."]},
        },
        {
            "id": "skill:existing", "kind": "skill",
            "composition": {"role": "definition"}, "summary": "Place a Token by a Console.",
        },
        {
            "id": "equipment:not-in-scope", "kind": "equipment",
            "composition": {"role": "definition"}, "summary": "A Disco Ball.",
        },
        {
            "id": "rule:not-definition", "kind": "rule",
            "composition": {"role": "fragment"}, "summary": "A Decoy Marker.",
        },
    ]}
    matches = expanded_mentions(curated)
    assert [row["recordId"] for row in matches] == ["rule:console-example"]
    assert list(matches[0]["matched"]) == ["summary", "effects"]


def test_pinned_extended_queue_keeps_scenario_and_device_identities_separate() -> None:
    report = audit_expanded_candidates(CURATED, REVIEWS)
    assert report["scope"] == "expanded-lexical-discovery-not-object-completeness"
    assert len(report["curatedSourceSha256"]) == 64
    assert report["candidateCount"] == 25
    assert report["reviewedCount"] == 6
    assert len(report["unreviewed"]) == 19
    reviewed = {row["recordId"]: row for row in report["reviews"]}
    assert set(reviewed) == {
        "term:marker",
        "rule:scenario:consoles",
        "rule:scenario:supply-boxes",
        "rule:scenario:controlling-supply-boxes",
        "skill:hack-consoles",
        "skill:activate-disco-ball",
    }
    assert reviewed["rule:scenario:consoles"]["sourcePages"] == [151]
    assert reviewed["rule:scenario:supply-boxes"]["sourcePages"] == [153]
    assert reviewed["skill:activate-disco-ball"]["classification"] == (
        "reviewed-object-interaction-not-identity"
    )
    assert {"state:decoy", "state:holoecho", "state:hidden-deployment"} <= {
        row["recordId"] for row in report["unreviewed"]
    }
    assert all(row["recordId"] not in reviewed for row in report["unreviewed"])

    # The Disco Ball object/source-mode has its own earlier approved
    # delivery review. Reactivation never creates a second source identity.
    delivery = json.loads(DELIVERY.read_text(encoding="utf-8"))
    assert "weapon:disco-baller" in json.dumps(delivery)
    assert "Disco Ball" in json.dumps(delivery)


def test_extended_reviews_reject_unsupported_or_stale_evidence() -> None:
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    manifest = json.loads(REVIEWS.read_text(encoding="utf-8"))
    candidates = expanded_mentions(curated)
    assert len(validate_reviews(manifest, curated, candidates)) == 6

    for field, bad_value, reason in (
        ("classification", "new-four-stat-object", "classification"),
        ("summaryEvidence", "invented sentence", "summary evidence"),
        ("factsEvidence", ["invented detail"], "detail evidence"),
        ("sourcePages", [999], "citation"),
        ("objectProfile", {"ARM": 0}, "audit-only"),
    ):
        altered = copy.deepcopy(manifest)
        altered["reviews"][-1][field] = bad_value
        with pytest.raises(ValueError, match=reason):
            validate_reviews(altered, curated, candidates)

    repeated = copy.deepcopy(manifest)
    repeated["reviews"].append(copy.deepcopy(repeated["reviews"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_reviews(repeated, curated, candidates)

    # The term has only a summary. Adding a structured clause demands review.
    extended = copy.deepcopy(curated)
    term = next(r for r in extended["records"] if r["id"] == "term:marker")
    term["facts"] = {"effects": ["A new representation clause."]}
    with pytest.raises(ValueError, match="detail evidence"):
        validate_reviews(manifest, extended, expanded_mentions(extended))


def test_extended_cli_reports_open_queue(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_deployed_object_expanded_queue"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Additional candidate definitions: 25" in output
    assert "Reviewed distinctions: 6" in output
    assert "Open additional candidates: 19" in output
