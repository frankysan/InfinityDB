"""Historical membership evidence must remain scoped to observed army lists."""

from copy import deepcopy

from infinity_db.army_history_consolidation import identity_inventory
from infinity_db.army_history_membership import child_collection, membership, source_role
from tests.test_army_history_consolidation import SyntheticSource, pair, report
from tests.test_army_history_pilot import faction


def analyze(rows):
    source = SyntheticSource(rows)
    return membership(source, report(source), identity_inventory(source))


def test_membership_and_declaration_are_distinct_with_corroboration():
    old = faction()
    old["units"][0].update(canonical=101, factions=[101])
    new = deepcopy(old)
    new["units"][0]["factions"] = [101, 102]
    absent = deepcopy(old)
    absent["units"] = []
    result = analyze(pair(101, old, new) + pair(102, absent, new))
    event = result["structuralOccurrences"][0]
    assert event["kind"] == "unitListMembership"
    assert event["direction"] == "appeared"
    assert event["evidence"]["factionId"] == 102
    assert event["declaredInThisArmy"] is True
    assert event["otherArmyEvidence"][0]["factionId"] == 101
    assert event["sourceRole"] == "standardSourceRecord"
    claim = result["declaredMembershipClaims"][0]
    assert claim["declaredFactionId"] == 102
    assert claim["direction"] == "added"
    assert claim["evidence"][0]["factionId"] == 101
    assert claim["listEvidence"][0]["factionId"] == 102


def test_unobserved_declarations_and_order_only_are_not_list_events():
    old = faction()
    old["units"][0]["factions"] = [101, 102]
    new = deepcopy(old)
    new["units"][0]["factions"] = [102, 101]
    result = analyze(pair(101, old, new))
    assert result["counts"]["declaredMembershipOrderOnly"] == 1
    assert not result["declaredMembershipClaims"]
    new["units"][0]["factions"].append(103)
    result = analyze(pair(101, old, new))
    assert not result["structuralOccurrences"]
    assert not result["declaredMembershipClaims"][0]["listEvidence"]


def test_nested_appearance_groups_across_armies():
    old = faction()
    new = deepcopy(old)
    options = new["units"][0]["profileGroups"][0]["options"]
    options.append(dict(options[0], id=2, name="Other"))
    result = analyze(pair(101, old, new) + pair(102, old, new, end="2025-02-02"))
    assert result["counts"]["loadout:appeared"] == 2
    assert result["counts"]["nestedGroupedOccurrences"] == 2
    assert result["counts"]["nestedCandidateGroups"] == 1
    assert result["nestedCandidateGroups"][0]["laterObservedDate"] == "2025-02-01"
    assert len(result["nestedCandidateGroups"][0]["evidence"]) == 2
    assert all(e["after"]["value"]["id"] == 2 for e in result["structuralOccurrences"])


def test_replacement_is_not_grouped_as_definite_addition():
    old = faction()
    new = deepcopy(old)
    new["units"][0]["profileGroups"][0]["options"][0]["id"] = 2
    result = analyze(pair(101, old, new))
    assert result["counts"]["possibleReplacement"] == 2
    assert result["counts"]["exactRecordReplacementOccurrence"] == 2
    assert {e["exactRecordReplacementId"] for e in result["structuralOccurrences"]} == {1, 2}
    assert result["counts"]["nestedNotGrouped"] == 2
    assert not result["nestedCandidateGroups"]
    assert {tuple(e["possibleReplacementIds"]) for e in result["structuralOccurrences"]} == {
        (1,), (2,),
    }


def test_ambiguous_or_changed_replacement_is_only_a_review_candidate():
    old = faction()
    new = deepcopy(old)
    options = new["units"][0]["profileGroups"][0]["options"]
    options[0]["id"] = 2
    options.append(dict(options[0], id=3))
    result = analyze(pair(101, old, new))
    assert result["counts"]["possibleReplacement"] == 3
    assert not result["counts"].get("exactRecordReplacementOccurrence")
    options.pop()
    options[0]["points"] = 18
    result = analyze(pair(101, old, new))
    assert result["counts"]["possibleReplacement"] == 2
    assert not result["counts"].get("exactRecordReplacementOccurrence")


def test_ava_and_disabled_remain_army_scoped():
    old = faction()
    group = old["units"][0]["profileGroups"][0]
    group["profiles"][0]["ava"] = 1
    group["options"][0]["disabled"] = False
    new = deepcopy(old)
    group = new["units"][0]["profileGroups"][0]
    group["profiles"][0]["ava"] = 2
    group["options"][0]["disabled"] = True
    result = analyze(pair(101, old, new))
    assert {e["kind"] for e in result["armyFieldOccurrences"]} == {"ava", "disabled"}
    assert all(e["evidence"]["factionId"] == 101 for e in result["armyFieldOccurrences"])


def test_role_uses_explicit_markers_and_missing_collection_is_unknown():
    assert source_role({"slug": "merc-one", "canonical": 1, "factions": []}) == (
        "mercenaryVariant"
    )
    assert source_role({"slug": "merc-one", "canonical": 1, "factions": [101]}) == "unknown"
    assert source_role({"slug": "one", "canonical": 1, "factions": [101]}) == (
        "standardSourceRecord"
    )
    data = faction()
    assert child_collection(data, ["units", 1, "options", 1]) is None
    data["units"][0]["options"] = []
    assert child_collection(data, ["units", 1, "options", 1]) == {}
