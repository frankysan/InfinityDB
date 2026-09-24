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

    assert report["summary"]["recordCount"] == 170
    assert report["summary"]["authoredOutgoingRelationCount"] == 185
    assert report["summary"]["futureInteractionCount"] == 91
    assert report["summary"]["releases"]["0.7.0"] == {
        "total": 170,
        "complete": 170,
        "pending": 0,
        "reviewed": 160,
        "inherited": 10,
        "percentComplete": 100.0,
    }
    assert report["summary"]["primaryCatalog"] == {
        "targetRelease": "0.7.0",
        "total": 180,
        "complete": 146,
        "pending": 34,
        "percentComplete": 81.1,
        "catalogs": {
            "skills": {
                "total": 95,
                "complete": 61,
                "pending": 34,
                "defined": 61,
                "missingRuleDefinition": 34,
                "percentComplete": 64.2,
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
            "states": {
                "total": 24,
                "complete": 24,
                "pending": 0,
                "defined": 24,
                "missingRuleDefinition": 0,
                "percentComplete": 100.0,
            },
        },
    }
    assert report["summary"]["supporting"]["total"] == 24
    assert report["summary"]["supporting"]["complete"] == 24
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
    assert primary["skill:aerial"]["status"] == "reviewed"
    assert primary["skill:aerial"]["recordDefined"] is True
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
    for state_id in {
        "state:dead",
        "state:engaged",
        "state:holoecho",
        "state:holomask",
        "state:normal",
        "state:prone",
        "state:possessed",
        "state:retreat",
        "state:sepsitorized",
        "state:suppressive-fire",
    }:
        assert primary[state_id]["status"] == "reviewed"
        assert primary[state_id]["recordDefined"] is True

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
        "skill:combat-jump",
        "skill:decoy",
        "skill:impersonation",
        "skill:infiltration",
        "skill:minelayer",
        "skill:parachutist",
        "skill:sapper",
        "skill:strategic-deployment",
        "skill:berserk",
        "skill:guard",
        "skill:neurocinetics",
        "skill:total-reaction",
        "skill:triangulated-fire",
        "skill:aerial",
        "skill:climbing-plus",
        "skill:terrain",
        "skill:warhorse",
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
    assert set(items["skill:request-speedball"]["relations"]) == {
        ("uses-effects-of", "skill:combat-jump")
    }
    assert ("cancels-state", "state:impersonation-1") in set(
        items["equipment:biometric-visor"]["relations"]
    )

    future_keys = {
        (candidate["sourceRecordId"], candidate["targetRecordId"], candidate["relationType"])
        for candidate in report["futureInteractions"]
    }
    assert ("skill:request-speedball", "skill:combat-jump", "uses-effects-of") not in future_keys
    assert ("skill:suppressive-fire", "state:suppressive-fire", "enters-state") not in future_keys
    assert ("skill:jump", "state:prone", "cancels-state") not in future_keys
    assert ("skill:stealth", "skill:idle", None) in future_keys
    assert ("skill:stealth", "skill:move", None) in future_keys
    assert ("skill:limited-cover", "rule:partial-cover", None) in future_keys
    assert ("skill:combat-jump", "rule:partial-cover", None) in future_keys
    assert ("skill:parachutist", "rule:partial-cover", None) in future_keys
    assert ("skill:infiltration", "state:camouflaged", None) in future_keys
    assert ("skill:infiltration", "state:hidden-deployment", None) in future_keys
    assert ("state:foxhole", "skill:courage", "uses-effects-of") not in future_keys
    assert ("state:foxhole", "rule:partial-cover", None) in future_keys
    assert ("skill:minelayer", "trait:disposable-x", None) in future_keys
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
    assert ("equipment:holomask", "state:holomask", "enters-state") not in future_keys
    assert ("weapon:armed-turret", "skill:total-reaction", "uses-effects-of") not in future_keys
    assert (
        "equipment:tinbot-neurocinetics",
        "skill:neurocinetics",
        "uses-effects-of",
    ) not in future_keys
    assert ("skill:guard", "skill:aerial", "restricts-use-of") not in future_keys
    assert set(items["skill:aerial"]["relations"]) == {
        ("restricts-use-of", "skill:cautious-movement"),
        ("restricts-use-of", "skill:guard"),
        ("negates-effects-of", "trait:boost"),
    }
    assert ("skill:aerial", "state:prone", None) in future_keys
    assert ("skill:aerial", "state:engaged", None) in future_keys
    assert ("skill:climbing-plus", "rule:partial-cover", None) in future_keys
    assert (
        "skill:climbing-plus",
        "rule:guts-roll",
        "applies-effects-to",
    ) in future_keys
    assert ("skill:terrain", "rule:movement-label", "applies-effects-to") in future_keys
    assert ("skill:terrain", "rule:special-terrain", None) in future_keys
    assert ("skill:warhorse", "state:isolated", None) in future_keys
    assert (
        "skill:triangulated-fire",
        "rule:range-modifiers",
        "ignores-modifiers-from",
    ) in future_keys
    assert (
        "skill:triangulated-fire",
        "rule:partial-cover",
        "ignores-modifiers-from",
    ) in future_keys
    assert ("state:unconscious", "state:prone", "causes-state") not in future_keys
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
    assert ("skill:courage", "rule:guts-roll", "applies-effects-to") in future_keys
    assert ("skill:impetuous", "state:prone", "cancels-state") not in future_keys
    assert ("skill:impetuous", "state:prone", None) in future_keys

    expected = render_markdown(report)
    assert "Skill **61/95**; Equipment **28/28**; Trait **33/33**; State **24/24**" in expected
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
    assert "0.7.0 primary catalog: 146/180 complete" in output
    assert "34 pending" in output
    assert "0 supporting identities pending" in output


def test_rules_interaction_catalog_scope_tracks_public_catalogs() -> None:
    document = json.loads(DEFAULT_CATALOG_SCOPE_PATH.read_text(encoding="utf-8"))
    assert document["targetRelease"] == "0.7.0"
    assert {key: len(value) for key, value in document["catalogs"].items()} == {
        "skills": 95,
        "equipment": 28,
        "traits": 33,
        "states": 24,
    }


def test_rules_interaction_checklist_check_passes() -> None:
    assert main(["--check-output", str(DEFAULT_CHECKLIST_PATH)]) == 0
