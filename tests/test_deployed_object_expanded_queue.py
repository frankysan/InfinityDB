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
    assert report["reviewedCount"] == 25
    assert report["unreviewed"] == []
    assert len(report["reviewedPdfOnly"]) in (0, 5)
    assert len(report["missingMaintainedN5Citation"]) == len(report["reviewedPdfOnly"])
    reviewed = {row["recordId"]: row for row in report["reviews"]}
    assert set(reviewed) == {
        "term:marker",
        "rule:scenario:consoles",
        "rule:scenario:supply-boxes",
        "rule:scenario:controlling-supply-boxes",
        "skill:hack-consoles",
        "skill:activate-disco-ball",
        "skill:decoy",
        "state:holoecho",
        "state:hidden-deployment",
        "state:impersonation-1",
        "state:impersonation-2",
        "skill:discover",
        "skill:surprise-attack",
        "skill:sensor",
        "trait:indiscriminate",
        "skill:look-out",
        "skill:chain-of-command",
        "skill:morpho-scan",
        "rule:scenario:killing",
        "rule:scenario:reinforced-tactical-link",
        "state:decoy",
        "trait:concealed",
        "skill:mnemonica",
        "skill:tactical-awareness",
        "skill:explode",
    }
    assert reviewed["rule:scenario:consoles"]["sourcePages"] == [151]
    assert reviewed["rule:scenario:supply-boxes"]["sourcePages"] == [153]
    assert reviewed["skill:activate-disco-ball"]["classification"] == (
        "reviewed-object-interaction-not-identity"
    )
    pdf_only_ids = {
        "state:decoy",
        "trait:concealed",
        "skill:mnemonica",
        "skill:tactical-awareness",
        "skill:explode",
    }
    assert {
        row["recordId"] for row in report["missingMaintainedN5Citation"]
    } == (pdf_only_ids if report["reviewedPdfOnly"] else set())
    assert {row["recordId"] for row in report["reviewedPdfOnly"]} == {
        row["recordId"] for row in report["missingMaintainedN5Citation"]
    }
    assert reviewed["state:decoy"]["classification"] == (
        "static-trooper-replicas-not-device"
    )
    assert "Line of Fire" in reviewed["state:decoy"]["caveat"]
    assert reviewed["trait:concealed"]["classification"] == (
        "existing-weapon-equipment-representation"
    )
    assert reviewed["state:holoecho"]["classification"] == (
        "interactive-trooper-replicas-not-device"
    )
    assert "trigger Mines or CrazyKoalas" in reviewed["state:holoecho"]["caveat"]
    assert reviewed["state:impersonation-1"]["classification"] == (
        "trooper-disguise-marker-not-device"
    )
    assert reviewed["state:impersonation-2"]["classification"] == (
        "trooper-disguise-marker-not-device"
    )
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
    assert len(validate_reviews(manifest, curated, candidates)) == 25

    for field, bad_value, reason in (
        ("classification", "new-four-stat-object", "classification"),
        ("summaryEvidence", "invented sentence", "summary evidence"),
        ("factsEvidence", ["invented detail"], "detail evidence"),
        ("sourcePages", [999], "citation"),
        ("objectProfile", {"ARM": 0}, "audit-only"),
    ):
        altered = copy.deepcopy(manifest)
        cited = next(
            review for review in altered["reviews"]
            if review["recordId"] == "skill:sensor"
        )
        cited[field] = bad_value
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

    # Manually verified PDF pages are audit-only until tracked rules sources
    # and their generated artifacts are rebuilt together.
    for field, wrong in (
        ("sourcePages", [999]),
        ("citationStatus", "maintained-source-cited"),
        ("pdfExcerpt", "unsupported quote"),
    ):
        changed = copy.deepcopy(manifest)
        changed["reviews"][-1][field] = wrong
        with pytest.raises(ValueError, match="PDF-only provenance"):
            validate_reviews(changed, curated, candidates)

    changed_cite = copy.deepcopy(curated)
    explode = next(
        item for item in changed_cite["records"] if item["id"] == "skill:explode"
    )
    cited = [
        cite for cite in explode["citations"]
        if cite["sourceId"] == "n5-core-v5.3-pdf"
    ]
    if cited:
        cited[0]["page"] = 999
    else:
        explode["citations"].append({"sourceId": "n5-core-v5.3-pdf", "page": 92})
    with pytest.raises(ValueError, match="PDF-only provenance"):
        validate_reviews(manifest, changed_cite, expanded_mentions(changed_cite))


def test_extended_cli_reports_open_queue(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_deployed_object_expanded_queue"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Additional candidate definitions: 25" in output
    assert "Reviewed distinctions: 25" in output
    assert "Open additional candidates: 0" in output
    count = 5 if any(
        review.get("citationStatus") == "pdf-verified-manifest-only"
        for review in json.loads(REVIEWS.read_text(encoding="utf-8"))["reviews"]
    ) else 0
    assert f"Reviewed with audit-only PDF evidence: {count}" in output
    assert f"Definitions missing maintained N5.3 PDF citations: {count}" in output
