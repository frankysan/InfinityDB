"""Source comparison pilot tests: conservative classifications and evidence."""

from copy import deepcopy

from infinity_db.army_history_pilot import (
    catalog_index,
    collect_references,
    compare_catalog_contexts,
    compare_faction,
    faction_filter_ids,
    pilot,
)
from infinity_db.army_history_source import read_history
from tests.test_army_history_source import fixture, write_archive


def faction():
    return {
        "version": "a",
        "units": [{
            "id": 1, "slug": "one", "name": "One", "factions": [101],
            "profileGroups": [{
                "id": 1, "profiles": [{"id": 1, "name": "One", "move": [10, 15], "bs": 12}],
                "options": [{
                    "id": 1, "name": "One", "points": 15,
                    "weapons": [{"id": 4, "q": 2, "order": 1}, {"id": 5, "order": 2}],
                }],
            }],
        }],
    }


def test_compare_preserves_typed_fields_and_review_boundaries():
    before = faction()
    after = deepcopy(before)
    after["version"] = "b"
    unit = after["units"][0]
    unit["name"] = "Renamed"
    unit["factions"] = [101, 102]
    group = unit["profileGroups"][0]
    profile = group["profiles"][0]
    profile["bs"] = 13
    profile["move"] = [15, 10]
    profile["notes"] = None
    option = group["options"][0]
    option["points"] = 16
    option["weapons"] = [{"id": 5, "order": 1}, {"id": 4, "order": 2, "q": 2}]
    changes = {c["path"][-1]: c for c in compare_faction(before, after)}
    assert changes["version"]["category"] == "sourceRevisionField"
    assert changes["name"]["category"] == "identityLabelReview"
    assert changes["factions"]["category"] == "availabilityOrIdentityReview"
    assert changes["bs"]["category"] == "gameplayFieldCandidate"
    assert changes["bs"]["ancestorOrRecordLabelChanged"]
    assert changes["move"]["after"]["value"] == [15, 10]
    assert changes["points"]["before"]["value"] == 15
    assert changes["notes"]["before"] == {"present": False}
    assert changes["notes"]["after"] == {"present": True, "value": None}
    assert changes["weapons"]["category"] == "referenceDisplayOrderOnly"


def test_reference_quantities_duplicates_and_anonymous_objects():
    before = faction()
    after = deepcopy(before)
    weapons = after["units"][0]["profileGroups"][0]["options"][0]["weapons"]
    weapons[0]["q"] = 3
    assert compare_faction(before, after)[0]["category"] == "referenceContentReview"
    weapons.append(deepcopy(weapons[0]))
    assert compare_faction(before, after)[0]["category"] == "referenceContentReview"
    weapons.append({"order": 3, "extra": [1]})
    changes = compare_faction(before, after)
    assert changes[0]["category"] == "referenceShapeReview"
    samples = []
    ids, issues = collect_references(after, samples)
    assert ids == {"weapons": {4, 5}}
    assert issues == {"loadout.weapons.anonymous": 1}
    assert samples[0]["value"] == {"order": 3, "extra": [1]}
    assert samples[0]["path"] == ["units", 0, "profileGroups", 0, "options", 0, "weapons", 3]


def test_appearance_and_disappearance_are_not_canonical_events():
    before = faction()
    after = deepcopy(before)
    after["units"][0]["id"] = 2
    changes = compare_faction(before, after)
    assert [c["category"] for c in changes] == [
        "observedKeyDisappearance", "observedKeyAppearance",
    ]
    assert changes[0]["before"]["value"]["id"] == 1
    assert changes[1]["after"]["value"]["id"] == 2


def test_duplicate_child_keys_fail_closed():
    before = faction()
    after = deepcopy(before)
    after["units"].append(deepcopy(after["units"][0]))
    assert compare_faction(before, after)[0]["category"] == "childShapeReview"


def test_catalog_modes_and_context_ambiguity():
    old = catalog_index({"weapons": [{"id": 4, "mode": "A"}, {"id": 4, "mode": "B"}]})
    reordered = catalog_index({"weapons": [{"id": 4, "mode": "B"}, {"id": 4, "mode": "A"}]})
    changed = catalog_index({"weapons": [{"id": 4, "mode": "C"}]})
    missing = catalog_index({})
    refs = {"weapons": {4}}
    for left, right, expected in (
        ([old], [reordered], "unchangedCatalogRecord"),
        ([old], [changed], "catalogRecordDifference"),
        ([old, changed], [reordered], "ambiguousContext"),
        ([old], [missing], "missingCatalogId"),
        ([], [old], "noContext"),
    ):
        _, counts = compare_catalog_contexts(refs, refs, left, right)
        assert counts == {expected: 1}


def test_peripheral_and_local_catalog_review():
    before = faction()
    after = deepcopy(before)
    for data, identity in ((before, 1), (after, 2)):
        data["units"][0]["profileGroups"][0]["profiles"][0]["peripheral"] = [{"id": identity}]
    assert compare_faction(before, after)[0]["category"] == "peripheralReferenceReview"
    filters = {"filters": {"weapons": [{"id": 4}, {"id": 5}], "equip": [{"id": 8}]}}
    assert faction_filter_ids(filters) == {"weapons": {4, 5}, "equips": {8}}
    assert faction_filter_ids({}) == {}
    before["filters"] = {"peripheral": [{"id": 1, "name": "Crabbot"}]}
    after["filters"] = {"peripheral": [{"id": 2, "name": "Crabbot"}]}
    changes = compare_faction(before, after)
    assert any(c["category"] == "peripheralDefinitionEquivalentRekey" for c in changes)
    after["filters"]["peripheral"].append({"id": 3, "name": "Crabbot"})
    changes = compare_faction(before, after)
    assert any(c["category"] == "peripheralReferenceReview" for c in changes)
    assert not any(c["category"] == "peripheralDefinitionEquivalentRekey" for c in changes)


def test_pilot_evidence_and_same_day_boundary(tmp_path):
    for distinct in (True, False):
        index, members, _ = fixture(distinct_days=distinct)
        archive = tmp_path / f"history-{distinct}.zip"
        source = read_history(archive, write_archive(archive, index, members))
        report = pilot(source)
        assert report["archiveSha256"] == source.sha256
        assert report["comparisonCount"] == int(distinct)
        if distinct:
            comparison = report["comparisons"][0]
            assert comparison["earlier"]["encodedRevisionDate"] == "2026-11-25"
            assert comparison["later"]["encodedRevisionDate"] == "2026-11-26"
            assert comparison["earlier"]["observationIndices"]
            assert comparison["earlier"]["metadataSha256"]
            assert report["changeCounts"]["observedKeyAppearance"] == 1
        else:
            assert not report["comparisons"]
