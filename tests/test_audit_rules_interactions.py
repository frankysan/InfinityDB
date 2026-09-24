from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit_rules_interactions import (
    DEFAULT_CHECKLIST_PATH,
    DEFAULT_POLICY_PATH,
    DEFAULT_RULES_DIRECTORY,
    RulesInteractionAuditError,
    audit_rules_interactions,
    main,
    render_markdown,
)


def test_checked_in_rules_interaction_review_is_complete_and_current() -> None:
    report = audit_rules_interactions(DEFAULT_RULES_DIRECTORY, DEFAULT_POLICY_PATH)

    assert report["summary"]["recordCount"] == 110
    assert report["summary"]["authoredOutgoingRelationCount"] == 87
    assert report["summary"]["futureInteractionCount"] == 4
    assert report["summary"]["releases"]["0.7.0"] == {
        "total": 110,
        "complete": 58,
        "pending": 52,
        "reviewed": 42,
        "inherited": 16,
        "percentComplete": 52.7,
    }

    items = {item["id"]: item for item in report["items"]}
    assert "declaration-category:skill:74:automatic" not in items
    assert items["skill:super-jump"]["status"] == "reviewed"
    assert items["skill:super-jump"]["futureInteractions"][0]["targetRecordId"] == (
        "skill:jump"
    )
    assert items["trait:perimeter"]["futureInteractions"][0]["targetRelease"] == (
        "post-0.7.0"
    )
    white_noise = [
        candidate
        for candidate in report["futureInteractions"]
        if candidate["sourceRecordId"] == "hacking-program:white-noise"
    ]
    assert {candidate["targetRecordId"] for candidate in white_noise} == {
        "skill:marksmanship",
        "equipment:multispectral-visor",
    }

    expected = render_markdown(report)
    actual = DEFAULT_CHECKLIST_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == expected


def test_rules_interaction_review_rejects_missing_entity(tmp_path: Path) -> None:
    document = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    document["records"] = document["records"][1:]
    policy = tmp_path / "reviews.json"
    policy.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RulesInteractionAuditError, match="coverage mismatch"):
        audit_rules_interactions(DEFAULT_RULES_DIRECTORY, policy)


def test_rules_interaction_release_gate_reports_pending_reviews(capsys) -> None:
    assert main(["--require-release", "0.7.0"]) == 1
    output = capsys.readouterr().out
    assert "0.7.0: 58/110 complete" in output
    assert "52 pending" in output


def test_rules_interaction_checklist_check_passes() -> None:
    assert main(["--check-output", str(DEFAULT_CHECKLIST_PATH)]) == 0
