from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit_rules_interactions import (
    DEFAULT_CATALOG_SCOPE_PATH,
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

    assert report["summary"]["recordCount"] == 120
    assert report["summary"]["authoredOutgoingRelationCount"] == 97
    assert report["summary"]["futureInteractionCount"] == 20
    assert report["summary"]["releases"]["0.7.0"] == {
        "total": 120,
        "complete": 80,
        "pending": 40,
        "reviewed": 64,
        "inherited": 16,
        "percentComplete": 66.7,
    }
    assert report["summary"]["primaryCatalog"] == {
        "targetRelease": "0.7.0",
        "total": 161,
        "complete": 57,
        "pending": 104,
        "percentComplete": 35.4,
        "catalogs": {
            "skills": {
                "total": 100,
                "complete": 35,
                "pending": 65,
                "defined": 39,
                "missingRuleDefinition": 61,
                "percentComplete": 35.0,
            },
            "equipment": {
                "total": 28,
                "complete": 13,
                "pending": 15,
                "defined": 14,
                "missingRuleDefinition": 14,
                "percentComplete": 46.4,
            },
            "traits": {
                "total": 33,
                "complete": 9,
                "pending": 24,
                "defined": 28,
                "missingRuleDefinition": 5,
                "percentComplete": 27.3,
            },
        },
    }
    assert report["summary"]["supporting"]["total"] == 39
    assert report["summary"]["supporting"]["complete"] == 23
    assert report["summary"]["supporting"]["pending"] == 16

    primary = {item["id"]: item for item in report["primaryCatalogItems"]}
    equipment_items = [
        item for item in report["primaryCatalogItems"] if item["catalog"] == "equipment"
    ]
    assert len(equipment_items) == 28
    assert primary["equipment:360o-visor"]["status"] == "reviewed"
    assert primary["equipment:360o-visor"]["recordDefined"] is True
    assert primary["equipment:baggage"]["status"] == "reviewed"
    assert primary["equipment:biometric-visor"]["status"] == "reviewed"
    assert primary["equipment:deployable-repeater"]["status"] == "reviewed"
    assert primary["equipment:fastpanda"]["status"] == "reviewed"
    assert primary["equipment:repeater"]["status"] == "reviewed"
    assert primary["skill:aerial"]["recordDefined"] is False
    assert primary["trait:cc-attack-3"]["recordDefined"] is False

    items = {item["id"]: item for item in report["items"]}
    assert "declaration-category:skill:74:automatic" not in items
    assert items["skill:super-jump"]["status"] == "reviewed"
    for record_id in {
        "skill:alert",
        "skill:bs-attack",
        "skill:cautious-movement",
        "skill:cc-attack",
        "skill:climb",
        "skill:idle",
        "skill:intuitive-attack",
        "skill:jump",
        "skill:move",
        "skill:place-deployable",
        "skill:request-speedball",
        "skill:suppressive-fire",
    }:
        assert items[record_id]["status"] == "reviewed"
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
    future_keys = {
        (candidate["sourceRecordId"], candidate["targetRecordId"], candidate["relationType"])
        for candidate in report["futureInteractions"]
    }
    assert ("skill:request-speedball", "skill:combat-jump", "uses-effects-of") in future_keys
    assert ("skill:suppressive-fire", "state:suppressive-fire", "enters-state") in future_keys
    assert ("skill:jump", "state:prone", "cancels-state") in future_keys
    assert ("skill:stealth", "skill:idle", None) in future_keys
    assert ("skill:stealth", "skill:move", None) in future_keys

    expected = render_markdown(report)
    assert "Skill **35/100**; Equipment **13/28**; Trait **9/33**" in expected
    assert "**360º Visor** (`equipment:360o-visor`)" in expected
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
    assert "0.7.0 primary catalog: 57/161 complete" in output
    assert "104 pending" in output
    assert "16 supporting identities pending" in output


def test_rules_interaction_catalog_scope_tracks_public_catalogs() -> None:
    document = json.loads(DEFAULT_CATALOG_SCOPE_PATH.read_text(encoding="utf-8"))
    assert document["targetRelease"] == "0.7.0"
    assert {key: len(value) for key, value in document["catalogs"].items()} == {
        "skills": 100,
        "equipment": 28,
        "traits": 33,
    }


def test_rules_interaction_checklist_check_passes() -> None:
    assert main(["--check-output", str(DEFAULT_CHECKLIST_PATH)]) == 0
