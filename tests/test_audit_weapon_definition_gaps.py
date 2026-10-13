from __future__ import annotations

from copy import deepcopy

import pytest

from tools.audit_weapon_definition_gaps import (
    WeaponGapTriageError,
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
