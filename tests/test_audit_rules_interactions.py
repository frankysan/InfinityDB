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

    assert report["summary"]["recordCount"] == 135
    assert report["summary"]["authoredOutgoingRelationCount"] == 120
    assert report["summary"]["futureInteractionCount"] == 64
    assert report["summary"]["releases"]["0.7.0"] == {
        "total": 135,
        "complete": 135,
        "pending": 0,
        "reviewed": 125,
        "inherited": 10,
        "percentComplete": 100.0,
    }
    assert report["summary"]["primaryCatalog"] == {
        "targetRelease": "0.7.0",
        "total": 156,
        "complete": 101,
        "pending": 55,
        "percentComplete": 64.7,
        "catalogs": {
            "skills": {
                "total": 95,
                "complete": 40,
                "pending": 55,
                "defined": 40,
                "missingRuleDefinition": 55,
                "percentComplete": 42.1,
            },
            "equipment": {
                "total": 28,
                "complete": 28,
                "pending": 0,
                "defined": 28,
                "missingRuleDefinition": 0,
                "percentComplete": 100.0,
            },
            "traits": {
                "total": 33,
                "complete": 33,
                "pending": 0,
                "defined": 33,
                "missingRuleDefinition": 0,
                "percentComplete": 100.0,
            },
        },
    }
    assert report["summary"]["supporting"]["total"] == 34
    assert report["summary"]["supporting"]["complete"] == 34
    assert report["summary"]["supporting"]["pending"] == 0

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
    assert primary["equipment:tinbot"]["status"] == "reviewed"
    assert primary["equipment:hacking-device-plus"]["status"] == "reviewed"
    assert primary["equipment:motorcycle"]["status"] == "reviewed"
    assert primary["skill:aerial"]["recordDefined"] is False
    assert primary["skill:non-hackable"]["status"] == "reviewed"
    assert primary["skill:non-hackable"]["recordDefined"] is True
    for non_skill_id in {
        "skill:bangbomb",
        "skill:bts-3",
        "skill:gizmokit",
        "skill:infinity-team-ops",
        "skill:medikit",
        "skill:regular",
    }:
        assert non_skill_id not in primary
    assert primary["trait:cc"]["status"] == "reviewed"
    assert primary["trait:non-reloadable"]["status"] == "reviewed"
    assert primary["trait:arm-0"]["status"] == "reviewed"
    assert primary["trait:aro"]["status"] == "reviewed"
    assert primary["trait:bts-0"]["status"] == "reviewed"
    assert primary["trait:burst-b"]["status"] == "reviewed"
    assert primary["trait:prior-deployment"]["status"] == "reviewed"
    assert "trait:cc-attack-3" not in primary
    assert "trait:comms-attack" not in primary
    assert "trait:no-lof" not in primary
    assert "trait:technical-weapon" not in primary
    assert "trait:throwing-weapon" not in primary

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
        "skill:forward-deployment",
        "skill:limited-cover",
        "skill:strategos",
        "skill:surprise-attack",
        "skill:move",
        "skill:place-deployable",
        "skill:request-speedball",
        "skill:suppressive-fire",
    }:
        assert items[record_id]["status"] == "reviewed"
    assert items["skill:super-jump"]["futureInteractions"][0]["targetRecordId"] == ("skill:jump")
    assert items["trait:perimeter"]["futureInteractions"][0]["targetRelease"] == ("post-0.7.0")
    for record_id in {
        "rule:peripheral-type:control",
        "rule:peripheral-type:cyberplug",
        "rule:peripheral-type:servant",
        "rule:peripheral-type:synchronized",
        "state:disconnected",
        "state:stunned",
        "state:unconscious",
        "state:unloaded",
        "training:irregular",
        "training:regular",
        "weapon:armed-turret",
    }:
        assert items[record_id]["status"] == "reviewed"
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
    assert ("skill:limited-cover", "rule:partial-cover", None) in future_keys
    assert (
        "skill:surprise-attack",
        "rule:face-to-face-roll",
        "imposes-modifiers-on",
    ) in future_keys
    assert ("rule:marker-form", "skill:surprise-attack", "enables-use-of") in future_keys
    assert ("trait:bioweapon", "ammunition:da", "uses-effects-of") in future_keys
    assert ("trait:bioweapon", "ammunition:shock", "uses-effects-of") in future_keys
    assert ("trait:bs-weapon-wip", "skill:bs-attack-shock", "restricts-use-of") in future_keys
    assert ("trait:continuous-damage", "state:dead", None) in future_keys
    assert ("trait:double-shot", "trait:disposable-x", None) in future_keys
    assert ("trait:indiscriminate", "state:camouflaged", None) in future_keys
    assert ("equipment:ai-motorcycle", "skill:transmutation", "uses-effects-of") in future_keys
    assert ("equipment:holomask", "state:holomask", "enters-state") in future_keys
    assert ("weapon:armed-turret", "skill:total-reaction", "uses-effects-of") in future_keys
    assert ("state:unconscious", "state:prone", "causes-state") in future_keys
    assert (
        "state:stunned",
        "rule:attack-declaration",
        "restricts-use-of",
    ) in future_keys
    assert ("state:stunned", "rule:roll", "modifies-rolls-for") in future_keys
    assert ("state:isolated", "state:disconnected", "causes-state") in future_keys
    assert ("rule:null-state", "state:disconnected", "causes-state") in future_keys
    assert ("equipment:symbiomate", "skill:immunity", "uses-effects-of") in future_keys
    assert (
        "equipment:hacking-device-plus",
        "hacking-program:white-noise",
        "enables-use-of",
    ) in future_keys

    expected = render_markdown(report)
    assert "Skill **40/95**; Equipment **28/28**; Trait **33/33**" in expected
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
    assert "0.7.0 primary catalog: 101/156 complete" in output
    assert "55 pending" in output
    assert "0 supporting identities pending" in output


def test_rules_interaction_catalog_scope_tracks_public_catalogs() -> None:
    document = json.loads(DEFAULT_CATALOG_SCOPE_PATH.read_text(encoding="utf-8"))
    assert document["targetRelease"] == "0.7.0"
    assert {key: len(value) for key, value in document["catalogs"].items()} == {
        "skills": 95,
        "equipment": 28,
        "traits": 33,
    }


def test_rules_interaction_checklist_check_passes() -> None:
    assert main(["--check-output", str(DEFAULT_CHECKLIST_PATH)]) == 0
