"""Cross-army candidate consolidation never asserts canonical history."""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.army_history_consolidation import (
    consolidate,
    identity_inventory,
    merge_compatible_intervals,
    target_signature,
)
from infinity_db.army_history_pilot import catalog_index, compare_faction
from infinity_db.army_history_references import resolve_references
from infinity_db.army_history_source import HistoricalArmySource
from tests.test_army_history_pilot import faction


class SyntheticSource(HistoricalArmySource):
    def __init__(self, rows):
        super().__init__(Path("synthetic.zip"), "pin", {}, {}, {}, (), {}, {})
        self.documents = {}
        for i, (army, day, data) in enumerate(rows):
            sha = str(i)
            self.documents[sha] = data
            self.groups[("n5", army, day, sha)] = (i,)

    def read_object(self, sha):
        return self.documents[sha]


def pair(army, old, new, start="2025-01-01", end="2025-02-01"):
    return [(army, start, old), (army, end, new)]


def report(source):
    by_army: dict[int, list[Any]] = {}
    for key, indices in sorted(source.groups.items()):
        _, army, day, sha = key
        by_army.setdefault(army, []).append({
            "encodedRevisionDate": day, "sha256": sha, "observationIndices": list(indices),
            "metadataSha256": sorted({
                ref for i in indices for ref in source.metadata_contexts.get(i, ())
                if ref is not None
            }),
        })
    comparisons = []
    for army, endpoints in by_army.items():
        if len(endpoints) != 2:
            continue
        a, b = endpoints
        comparisons.append({
            "factionId": army, "earlier": a, "later": b,
            "changes": compare_faction(
                source.read_object(a["sha256"]), source.read_object(b["sha256"]),
            ),
        })
    return {"archiveSha256": "pin", "formatVersion": 1, "edition": "n5",
            "comparisons": comparisons}


def states():
    old = faction()
    new = deepcopy(old)
    new["units"][0]["profileGroups"][0]["options"][0]["points"] = 16
    return old, new


def test_identical_change_consolidated_with_all_evidence():
    old, new = states()
    source = SyntheticSource(pair(101, old, new) + pair(102, old, new))
    result = consolidate(source, report(source), identity_inventory(source))
    assert result["candidateCount"] == 1
    assert result["retainedOccurrenceCount"] == 2
    assert result["multiArmyCandidateCount"] == 1
    event = result["candidates"][0]
    assert event["before"]["value"] == 15 and event["after"]["value"] == 16
    assert [e["factionId"] for e in event["evidence"]] == [101, 102]
    assert [e["comparisonIndex"] for e in event["evidence"]] == [0, 1]


def test_compatible_intervals_merge_but_variants_remain_separate():
    old, new = states()
    other_old, other_new = deepcopy(old), deepcopy(new)
    for data in (other_old, other_new):
        data["units"][0]["profileGroups"][0]["options"][0]["weapons"] = [{"id": 8}]
    source = SyntheticSource(
        pair(101, old, new) + pair(102, old, new, end="2025-02-02")
        + pair(103, other_old, other_new),
    )
    result = consolidate(source, report(source), identity_inventory(source))
    assert result["exactWindowCandidateCount"] == 3
    # A competing variant overlaps, so the additional merge is withheld.
    assert result["candidateCount"] == 3
    assert result["multiArmyCandidateCount"] == 0
    assert result["intervalConsolidation"] == {"competingTransition": 1}
    source = SyntheticSource(pair(101, old, new) + pair(102, old, new, end="2025-02-02"))
    result = consolidate(source, report(source), identity_inventory(source))
    assert result["candidateCount"] == 1
    event = result["candidates"][0]
    assert event["laterObservedDate"] == "2025-02-01"
    assert {e["later"]["encodedRevisionDate"] for e in event["evidence"]} == {
        "2025-02-01", "2025-02-02",
    }


def test_overlap_chains_and_repeated_armies_are_not_merged():
    def event(identity, army, start, end):
        return {
            "candidateId": identity, "edition": "n5",
            "path": ["units", 1, "options", 1, "points"],
            "before": {"value": 15}, "after": {"value": 16},
            "earlierObservedDate": start, "laterObservedDate": end,
            "earlierTargetFingerprint": "before", "laterTargetFingerprint": "after",
            "evidence": [{"factionId": army, "comparisonIndex": identity}],
        }

    a = event(1, 101, "2025-01-01", "2025-02-01")
    b = event(2, 102, "2025-01-20", "2025-03-01")
    c = event(3, 103, "2025-02-15", "2025-04-01")
    rows, counts = merge_compatible_intervals([a, b, c])
    assert len(rows) == 3
    assert counts == {"noCommonWindow": 1}
    b["evidence"][0]["factionId"] = 101
    rows, counts = merge_compatible_intervals([a, b])
    assert len(rows) == 2
    assert counts == {"repeatedArmy": 1}


def test_reviewed_identity_exceptions_are_narrow():
    def state(identity, slug, canonical, factions):
        data = faction()
        data["units"][0].update(
            id=identity, idArmy=identity, slug=slug, canonical=canonical, factions=factions,
        )
        return data

    ward = "reinf-wardrivers-mercenary-hackers"
    old = state(1852, "zaybak-aero-unit", 401, [401, 403])
    new = state(1852, "zeybek-aero-unit", 401, [401, 403])
    rows = [
        (399, "2025-01-01", state(1635, ward, 399, [399])),
        (998, "2025-01-01", state(1691, ward, 998, [998, 999])),
        *pair(401, old, new),
    ]
    inventory = identity_inventory(SyntheticSource(rows))
    assert inventory["eligibleUnitIds"] == [1635, 1691, 1852]
    assert [r["status"] for r in inventory["candidates"]] == [
        "reviewedSeparateArmyIdentity", "reviewedSeparateArmyIdentity", "reviewedSpellingAlias",
    ]
    new["units"][0]["canonical"] = 403
    assert identity_inventory(SyntheticSource(rows))["eligibleUnitIds"] == [1635, 1691]
    new["units"][0]["canonical"] = 401
    rows.append((403, "2025-01-01", new))
    assert identity_inventory(SyntheticSource(rows))["eligibleUnitIds"] == [1635, 1691]


def test_slug_collision_and_alias_are_quarantined():
    old, new = states()
    other = deepcopy(old)
    other["units"][0]["id"] = 2
    alias = deepcopy(old)
    alias["units"][0]["slug"] = "alias"
    source = SyntheticSource(pair(101, old, new) + [(102, "2025-01-01", other),
                                                    (103, "2025-01-01", alias)])
    inventory = identity_inventory(source)
    assert not inventory["eligibleUnitIds"]
    assert inventory["candidates"][0]["reasons"] == [
        "multipleSlugsForId", "slugSharedByMultipleIds",
    ]
    result = consolidate(source, report(source), inventory)
    assert result["candidateCount"] == 0
    assert result["excludedOccurrencesByReason"]["unitIdentityReview"] == 1


def test_peripheral_signature_requires_local_definition():
    old, _ = states()
    new = deepcopy(old)
    path = ["units", 1, "profileGroups", 1, "options", 1, "points"]
    for data, identity in ((old, 3), (new, 7)):
        data["filters"] = {"peripheral": [{"id": identity, "name": "Crabbot"}]}
        data["units"][0]["profileGroups"][0]["options"][0]["peripheral"] = [{"id": identity}]
    assert target_signature(old, path) == target_signature(new, path)
    new["filters"]["peripheral"][0]["name"] = "Different"
    assert target_signature(old, path) != target_signature(new, path)
    new["filters"]["peripheral"] = []
    assert target_signature(new, path) is None


def test_reference_resolver_preserves_modes_extras_and_multiplicity():
    data = {"filters": {
        "weapons": [{"id": 4, "name": "Rifle", "mercs": True}],
        "extras": [{"id": 1, "name": "+1"}],
    }}
    meta = catalog_index({"weapons": [
        {"id": 4, "mode": "A"}, {"id": 4, "mode": "B"},
    ]})
    rows = [{"id": 4, "q": 2, "extra": [1], "order": 1}, {"id": 4, "order": 2}]
    resolved, status = resolve_references(rows, "weapons", data, [meta])
    assert status == "withMetadata"
    assert resolved is not None and len(resolved) == 2
    assert all(len(row["metadataFingerprints"]) == 2 for row in resolved)
    assert any(row["occurrence"].get("extra") == [{"id": 1, "name": "+1"}]
               for row in resolved)
    reordered = [dict(rows[1], order=1), dict(rows[0], order=2)]
    assert resolve_references(reordered, "weapons", data, [meta])[0] == resolved
    assert resolve_references(rows[:1], "weapons", data, [meta])[0] != resolved
    assert resolve_references(rows, "weapons", data, [meta, {}])[1] == (
        "ambiguousMetadataDefinition"
    )
    assert resolve_references(rows, "weapons", data, [{}])[1] == "filterOnly"
    assert resolve_references(rows, "weapons", data, [])[1] == "missingMetadataContext"
    assert resolve_references([{}], "weapons", data, [meta])[1] == "referenceShape"
    assert resolve_references([{"id": 9}], "weapons", data, [meta])[1] == (
        "missingFactionDefinition"
    )
    assert resolve_references([{"id": 4, "extra": [9]}], "weapons", data, [meta])[1] == (
        "missingExtraDefinition"
    )
    data["filters"]["weapons"].append({"id": 4, "name": "Other"})
    assert resolve_references(rows, "weapons", data, [meta])[1] == "missingFactionDefinition"


def test_reference_change_consolidation_keeps_context_and_raw_evidence():
    old = faction()
    old["filters"] = {"weapons": [{"id": 4, "name": "Rifle"}, {"id": 5, "name": "Pistol"}]}
    new = deepcopy(old)
    new["units"][0]["profileGroups"][0]["options"][0]["weapons"][0]["q"] = 3
    source = SyntheticSource(pair(101, old, new) + pair(102, old, new))
    source.documents["meta"] = {"weapons": [{"id": 4, "name": "Rifle"}]}
    source.metadata_contexts = {i: ("meta",) for i in range(4)}
    result = consolidate(source, report(source), identity_inventory(source))
    assert result["candidateCount"] == 1
    assert result["includedOccurrencesByField"] == {"weapons": 2}
    assert result["referenceOutcomes"] == {"weapons:filterOnly": 2}
    candidate = result["candidates"][0]
    assert len(candidate["evidence"]) == 2
    assert all(e["earlier"]["metadataSha256"] == ["meta"] for e in candidate["evidence"])
    assert any(v["occurrence"].get("q") == 3 for v in candidate["after"]["value"])
    source.documents["other"] = {"weapons": [{"id": 4, "name": "Different"}]}
    source.metadata_contexts[3] = ("meta", "other")
    result = consolidate(source, report(source), identity_inventory(source))
    assert result["retainedOccurrenceCount"] == 1
    assert result["referenceOutcomes"]["weapons:ambiguousMetadataDefinition"] == 1


def test_coverage_and_values_fail_closed():
    old, new = states()
    source = SyntheticSource(pair(101, old, new))
    inventory = identity_inventory(source)
    data = report(source)
    data["comparisons"][0]["changes"][0]["after"]["value"] = 999
    with pytest.raises(ValueError, match="value differs"):
        consolidate(source, data, inventory)
    data["comparisons"] = []
    with pytest.raises(ValueError, match="coverage differs"):
        consolidate(source, data, inventory)
