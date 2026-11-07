"""N5.3 detailed-rule candidate queue is evidence, not object publication."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tools.audit_deployed_object_detail_queue import (
    audit_detail_candidates,
    detail_candidates,
    main,
)


def test_detailed_mentions_are_separate_from_summary_and_review_decisions() -> None:
    source = {"records": [
        {
            "id": "weapon:new-device", "kind": "weapon",
            "composition": {"role": "definition"},
            "summary": "A specialized launcher.",
            "facts": {"effects": ["Places a Deployable model."],
                      "sourceNotes": ["Not an independent Token."]},
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 74}],
        },
        {
            "id": "equipment:reviewed", "kind": "equipment",
            "composition": {"role": "definition"},
            "summary": "Token equipment.",
            "facts": {"restrictions": ["Use only one Token."]},
        },
        {
            "id": "weapon:summary-only", "kind": "weapon",
            "composition": {"role": "definition"},
            "summary": "A Deployable.",
            "facts": {"effects": ["No extra object reference."]},
        },
        {
            "id": "skill:ignored", "kind": "skill",
            "composition": {"role": "definition"}, "summary": "",
            "facts": {"effects": ["A Deployable Scenery Element."]},
        },
    ]}
    entries = detail_candidates(source, reviewed_ids={"equipment:reviewed"})
    assert [entry["recordId"] for entry in entries] == [
        "equipment:reviewed", "weapon:new-device",
    ]
    assert entries[0]["reviewed"] and entries[0]["summaryMatches"]
    assert not entries[1]["reviewed"] and not entries[1]["summaryMatches"]
    assert set(entries[1]["details"]) == {"effects", "sourceNotes"}
    assert entries[1]["citations"] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 74}
    ]


def test_cli_reports_pinned_review_coverage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_deployed_object_detail_queue"])
    root = Path(__file__).resolve().parents[1]
    if not (root / "data/generated/infinity.db").is_file():
        pytest.skip("Pinned Army database unavailable")
    assert main() == 0
    output = capsys.readouterr().out
    assert "Detailed-rule candidates:" in output
    assert "Detail-only candidates:" in output
    assert "Unreviewed candidates: 0" in output


def test_pinned_detailed_keyword_inventory_has_explicit_review_boundaries() -> None:
    root = Path(__file__).resolve().parents[1]
    inputs = (
        root / "data/generated/infinity.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in inputs):
        pytest.skip("Pinned N5.3 review inputs missing")
    report = audit_detail_candidates(*inputs)
    assert report["scope"] == "detail-keyword-discovery-not-complete-source-inventory"
    assert len(report["sourceSha256"]) == 64
    assert report["unreviewed"] == [], [
        (item["recordId"], item["summary"][:85], item["details"], item["citations"])
        for item in report["unreviewed"]
    ]
