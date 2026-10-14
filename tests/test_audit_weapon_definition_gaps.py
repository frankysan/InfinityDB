from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.database.repository import Database
from tools.audit_weapon_definition_gaps import (
    WeaponGapTriageError,
    load_shared_reviews,
    markdown_report,
    reconcile,
)


def _reports() -> tuple[dict, dict, dict[int, str]]:
    weapon_items = [
        {
            "id": 1, "name": "MULTI Rifle", "slug": "multi-rifle",
            "useCount": 15, "gapCodes": ["missing_rule_definition"],
            "familyRuleIds": [], "exactSourceRuleIds": [],
        },
        {
            "id": 2, "name": "SymbioBomb", "slug": "symbiobomb",
            "useCount": 1, "gapCodes": ["missing_rule_definition"],
            "familyRuleIds": [], "exactSourceRuleIds": [],
        },
        {
            "id": 3, "name": "Cybermine", "slug": "cybermine",
            "useCount": 22, "gapCodes": ["ambiguous_family_mapping"],
            "familyRuleIds": ["weapon:cybermine", "weapon:mines"],
            "exactSourceRuleIds": [],
        },
        {
            "id": 4, "name": "Flash Pulse", "slug": "flash-pulse",
            "useCount": 100, "gapCodes": ["stale_citation_source"],
            "familyRuleIds": ["weapon:flash-pulse"], "exactSourceRuleIds": [],
        },
    ]
    rows = [
        {"name": "MULTI Rifle", "mode": "AP Mode", "page": 182, "differences": []},
        {"name": "MULTI Rifle", "mode": "DA Mode", "page": 182, "differences": []},
        {"name": "Cybermine", "mode": "", "page": 180, "differences": []},
        {"name": "Flash Pulse", "mode": "", "page": 179, "differences": []},
    ]
    coverage = {
        "format": "InfinityDB rules enrichment coverage audit",
        "formatVersion": 3,
        "database": {"sha256": "a" * 64},
        "rulesDatabase": {"sha256": "b" * 64},
        "domains": {"weapons": {"gapCount": len(weapon_items), "items": weapon_items}},
    }
    chart = {
        "format": "InfinityDB N5 Weapon Chart profile evidence",
        "formatVersion": 3,
        "armyDatabaseSha256": "a" * 64,
        "corePdfSha256": "c" * 64,
        "comparison": {
            "chartRowsLocated": len(rows),
            "unambiguousRowsCompared": len(rows),
            "deferredRows": 0,
            "compared": rows,
        },
    }
    return coverage, chart, {
        1: "Rifles", 2: "Uncategorized", 3: "Mines", 4: "Uncategorized"
    }


def test_triage_keeps_missing_rules_separate_from_chart_profiles() -> None:
    coverage, chart, categories = _reports()
    report = reconcile(coverage, chart, categories, "a" * 64)
    assert report["summary"] == {
        "unresolvedWeapons": 4,
        "dispositions": {
            "ambiguous-rule-mapping": 1,
            "definition-review": 1,
            "outside-chart-review": 1,
            "stale-rule-citation": 1,
        },
        "matchedChartIdentity": 3,
        "noChartIdentity": 1,
        "reviewBatches": 4,
    }
    indexed = {row["name"]: row for row in report["items"]}
    assert indexed["MULTI Rifle"]["chart"] == {
        "status": "identity-present",
        "printedRows": 2,
        "pages": [182],
        "modes": ["AP Mode", "DA Mode"],
        "profileCandidates": 0,
    }
    assert indexed["SymbioBomb"]["chart"]["status"] == "identity-not-in-chart"
    assert indexed["Cybermine"]["familyRules"] == ["weapon:cybermine", "weapon:mines"]
    assert "not missing-fact or browser-defect verdicts" in markdown_report(report)
    assert "does not infer Weapon rules" in markdown_report(report)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("enrichment-version", "enrichment coverage"),
        ("chart-version", "Weapon Chart profile"),
        ("army-hash", "different Army database"),
        ("chart-hash", "different Army database"),
        ("pdf-hash", "PDF SHA-256"),
        ("deferred", "deferred rows"),
        ("missing-catalog", "absent from Army catalog"),
        ("unknown-gap", "Unclassified gap codes"),
        ("duplicate-id", "Duplicate or invalid"),
    ],
)
def test_triage_fails_closed_on_inconsistent_evidence(
    change: str, message: str
) -> None:
    coverage, chart, categories = _reports()
    if change == "enrichment-version":
        coverage["formatVersion"] = 1
    elif change == "chart-version":
        chart["formatVersion"] = 2
    elif change == "army-hash":
        coverage["database"]["sha256"] = "0" * 64
    elif change == "chart-hash":
        chart["armyDatabaseSha256"] = "0" * 64
    elif change == "pdf-hash":
        chart["corePdfSha256"] = "not-a-hash"
    elif change == "deferred":
        chart["comparison"]["deferredRows"] = 1
    elif change == "missing-catalog":
        del categories[4]
    elif change == "unknown-gap":
        coverage["domains"]["weapons"]["items"][0]["gapCodes"] = ["unknown"]
    elif change == "duplicate-id":
        coverage["domains"]["weapons"]["items"][1]["id"] = 1
    with pytest.raises(WeaponGapTriageError, match=message):
        reconcile(coverage, chart, categories, "a" * 64)


def test_reusable_ammunition_coverage_reclassifies_review_not_completion() -> None:
    enrichment, chart, categories = _reports()
    chart["comparison"]["compared"].append({
        "name": "SymbioBomb", "mode": "", "page": 179, "differences": [],
    })
    chart["comparison"]["chartRowsLocated"] += 1
    chart["comparison"]["unambiguousRowsCompared"] += 1
    report = reconcile(
        enrichment, chart, categories, "a" * 64,
        shared_effect_coverage={
            1: {"total": 2, "linked": 2},
            2: {"total": 1, "linked": 0},
        },
    )
    assert report["formatVersion"] == 3
    assert report["summary"]["unresolvedWeapons"] == 4
    assert report["summary"]["sharedEffectCandidates"] == 1
    assert report["summary"]["missingEffectLinkCandidates"] == 1
    assert report["summary"]["modeReviewCandidates"] == 1
    rows = {row["id"]: row for row in report["items"]}
    assert rows[1]["disposition"] == "shared-effects-review"
    assert rows[1]["sharedEffectCoverage"] == {"total": 2, "linked": 2}
    assert rows[1]["requiresModeReview"] is True
    assert rows[2]["disposition"] == "missing-effect-links-review"
    assert rows[2]["requiresModeReview"] is False
    assert "review still pending" in markdown_report(report)
    assert "Canonical Ammunition effects are linked" in next(
        b["evidenceRequirement"] for b in report["batches"]
        if b["disposition"] == "shared-effects-review"
    )

    with pytest.raises(WeaponGapTriageError, match="Missing Weapon profile coverage"):
        reconcile(
            enrichment, chart, categories, "a" * 64,
            shared_effect_coverage={1: {"total": 2, "linked": 2}},
        )


def test_source_review_acceptance_requires_explicit_matching_chart_and_links() -> None:
    enrichment, chart, categories = _reports()
    accepted = {1: {"sourceId": "n5-core-v5.3-pdf", "chartPage": 182,
                    "reason": "Shared components suffice"}}
    coverage = {1: {"total": 2, "linked": 2}}
    report = reconcile(enrichment, chart, categories, "a" * 64,
                       shared_effect_coverage=coverage, reviewed_shared=accepted)
    items = {r["id"]: r for r in report["items"]}
    assert items[1]["disposition"] == "reviewed-shared-effects"
    assert items[1]["sharedReview"] == accepted[1]
    assert report["summary"]["reviewedSharedEffects"] == 1
    assert report["summary"]["remainingSourceReviews"] == 3
    assert report["summary"]["reviewBatches"] == 3
    assert all(1 not in batch["weaponIds"] for batch in report["batches"])
    assert "Explicitly reviewed without a standalone Weapon definition" in (
        markdown_report(report)
    )

    with pytest.raises(WeaponGapTriageError, match="source conditions changed"):
        reconcile(
            enrichment, chart, categories, "a" * 64,
            shared_effect_coverage=coverage,
            reviewed_shared={1: {**accepted[1], "chartPage": 999}},
        )
    with pytest.raises(WeaponGapTriageError, match="source conditions changed"):
        reconcile(
            enrichment, chart, categories, "a" * 64,
            shared_effect_coverage={1: {"total": 2, "linked": 1}},
            reviewed_shared=accepted,
        )


def test_checked_in_weapon_shared_reviews_are_profile_pinned(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    db = Database(root / "data/generated/infinity.db")
    original = json.loads(
        (root / "data/curated/weapon-shared-effect-reviews.json").read_text(
            encoding="utf8",
        )
    )
    assert len(original["reviews"]) == 21
    catalog = {r["name"]: r for r in db.list_catalog_items("weapons")}
    items = [
        {"id": catalog[r["name"]]["id"], "name": r["name"],
         "slug": r["slug"], "gapCodes": ["missing_rule_definition"]}
        for r in original["reviews"]
    ]
    enrichment = {"domains": {"weapons": {"items": items}}}
    policy = tmp_path / "reviewed.json"
    policy.write_text(json.dumps(original), encoding="utf8")
    approved = load_shared_reviews(db, enrichment, policy)
    assert len(approved) == 21
    assert {r["chartPage"] for r in approved.values()} == {179, 183, 184, 185, 186, 187, 188}
    assert {
        r["name"] for r in original["reviews"] if r["chartPage"] == 184
    } == {
        "Boarding Shotgun", "Light Shotgun", "Vulkan Shotgun",
        "Heavy Shotgun", "T2 Boarding Shotgun",
    }
    assert {
        r["name"] for r in original["reviews"] if r["chartPage"] == 185
    } == {"Submachine Gun", "AP Submachine Gun"}
    assert {
        r["name"] for r in original["reviews"]
        if r["chartPage"] in (186, 187, 188)
    } == {
        "E/Marat", "Mk12", "Zapper", "Contender", "Crazykoala", "Madtraps",
    }
    assert {
        r["name"] for r in original["reviews"] if r["chartPage"] == 179
    } == {"Heavy Machine Gun", "AP Heavy Machine Gun"}
    assert {r["reason"] for r in approved.values()} == {
        r["reason"] for r in original["reviews"]
    }
    first_hash = original["reviews"][0]["profileSha256"]
    original["reviews"][0]["profileSha256"] = "0" * 64
    policy.write_text(json.dumps(original), encoding="utf8")
    with pytest.raises(WeaponGapTriageError, match="profile changed"):
        load_shared_reviews(db, enrichment, policy)

    # New shared-only Shotgun approvals must reopen if their Army profile drifts.
    original["reviews"][0]["profileSha256"] = first_hash
    vulkan = next(r for r in original["reviews"] if r["name"] == "Vulkan Shotgun")
    vulkan["profileSha256"] = "0" * 64
    policy.write_text(json.dumps(original), encoding="utf8")
    with pytest.raises(WeaponGapTriageError, match="profile changed"):
        load_shared_reviews(db, enrichment, policy)

    vulkan["profileSha256"] = next(
        row["profileSha256"] for row in json.loads(
            (root / "data/curated/weapon-shared-effect-reviews.json").read_text(
                encoding="utf8",
            )
        )["reviews"] if row["name"] == "Vulkan Shotgun"
    )
    smg = next(r for r in original["reviews"] if r["name"] == "AP Submachine Gun")
    smg["profileSha256"] = "0" * 64
    policy.write_text(json.dumps(original), encoding="utf8")
    with pytest.raises(WeaponGapTriageError, match="profile changed"):
        load_shared_reviews(db, enrichment, policy)


def test_hmg_shared_only_reviews_are_profile_pinned(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    db = Database(root / "data/generated/infinity.db")
    policy = json.loads(
        (root / "data/curated/weapon-shared-effect-reviews.json").read_text(
            encoding="utf8",
        )
    )
    reviewed = [
        item for item in policy["reviews"] if item["chartPage"] == 179
    ]
    assert {item["name"] for item in reviewed} == {
        "Heavy Machine Gun", "AP Heavy Machine Gun",
    }
    catalog = {item["name"]: item for item in db.list_catalog_items("weapons")}
    pending = {
        "domains": {"weapons": {"items": [
            {"id": catalog[item["name"]]["id"], "name": item["name"],
             "slug": item["slug"], "gapCodes": ["missing_rule_definition"]}
            for item in reviewed
        ]}}
    }
    subset = {**policy, "reviews": reviewed}
    target = tmp_path / "hmg-reviews.json"
    target.write_text(json.dumps(subset), encoding="utf8")
    assert len(load_shared_reviews(db, pending, target)) == 2

    subset["reviews"][1]["profileSha256"] = "0" * 64
    target.write_text(json.dumps(subset), encoding="utf8")
    with pytest.raises(WeaponGapTriageError, match="profile changed"):
        load_shared_reviews(db, pending, target)


def test_reviewed_historical_comparison_remains_visible_but_not_pending() -> None:
    coverage, chart, categories = _reports()
    flash = coverage["domains"]["weapons"]["items"][-1]
    flash["gapClassifications"] = [{
        "code": "stale_citation_source",
        "classification": "intentional-omission",
        "source": "override",
        "reason": "N5.2 is historical comparison evidence; current PDFs are authoritative.",
    }]
    report = reconcile(coverage, chart, categories, "a" * 64)
    assert report["summary"]["dispositions"]["reviewed-historical-citation"] == 1
    assert "stale-rule-citation" not in report["summary"]["dispositions"]
    reviewed = [
        batch for batch in report["batches"]
        if batch["disposition"] == "reviewed-historical-citation"
    ]
    assert len(reviewed) == 1
    assert reviewed[0]["weaponNames"] == ["Flash Pulse"]
    assert "separate unresolved publication conflict" in reviewed[0]["evidenceRequirement"]


def test_triage_batches_are_deterministic_and_bounded() -> None:
    coverage, chart, categories = _reports()
    template = deepcopy(coverage["domains"]["weapons"]["items"][0])
    for weapon_id in range(5, 15):
        entry = deepcopy(template)
        entry["id"] = weapon_id
        entry["name"] = f"MULTI Rifle ({weapon_id})"
        entry["useCount"] = weapon_id
        coverage["domains"]["weapons"]["items"].append(entry)
        categories[weapon_id] = "Rifles"
        chart["comparison"]["compared"].append({
            "name": entry["name"], "mode": "", "page": 183, "differences": [],
        })
    coverage["domains"]["weapons"]["gapCount"] += 10
    chart["comparison"]["chartRowsLocated"] += 10
    chart["comparison"]["unambiguousRowsCompared"] += 10
    first = reconcile(coverage, chart, categories, "a" * 64)
    second = reconcile(coverage, chart, categories, "a" * 64)
    assert first == second
    assert all(len(batch["weaponIds"]) <= 8 for batch in first["batches"])
    definition_batches = [
        batch for batch in first["batches"]
        if batch["sourceCategory"] == "Rifles"
        and batch["disposition"] == "definition-review"
    ]
    assert [len(batch["weaponIds"]) for batch in definition_batches] == [8, 3]
