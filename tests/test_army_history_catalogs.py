"""Catalog definition evidence must not invent mode or Unit identity continuity."""

from copy import deepcopy

from infinity_db.army_history_catalogs import (
    catalog_rows,
    classify,
    compare_definitions,
    consensus,
    persistent_references,
)
from tests.test_army_history_consolidation import SyntheticSource, pair, report
from tests.test_army_history_pilot import faction


def test_catalog_modes_and_context_consensus():
    a = {"weapons": [{"id": 4, "burst": 2}, {"id": 4, "burst": 3}]}
    b = {"weapons": list(reversed(a["weapons"]))}
    left, right = (catalog_rows(x, "weapons", local=False) for x in (a, b))
    assert left == right
    assert consensus([left, right], 4) == (left[4], "resolved")
    assert consensus([left, {}], 4) == (None, "ambiguousContext")
    assert consensus([{}, {}], 4) == (None, "missingCatalogId")
    assert consensus([], 4) == (None, "noContext")
    assert classify("weapons", "metadata", left[4], [{"id": 4}]) == (
        "recordMultiplicityReview"
    )


def test_classification_does_not_assign_weapon_modes_by_position():
    a = [{"id": 4, "burst": 2, "damage": 13}, {"id": 4, "burst": 3, "damage": 14}]
    b = [{"id": 4, "burst": 2, "damage": 14}, {"id": 4, "burst": 3, "damage": 13}]
    assert classify("weapons", "metadata", a, b) == "recordAssociationReview"
    assert classify("weapons", "metadata", a[:1], [{"id": 4, "burst": 2, "damage": 15}]) == (
        "weaponMechanicsCandidate"
    )
    assert classify("skills", "factionFilter", [{"wiki": "a"}], [{"wiki": "b"}]) == (
        "linkOrPresentationReview"
    )
    assert classify("peripheral", "factionFilter", [{"name": "A"}], [{"name": "B"}]) == (
        "definitionIdentityReview"
    )


def test_persistent_refs_require_stable_paths_and_typed_occurrences():
    old = faction()
    new = deepcopy(old)
    weapons = new["units"][0]["profileGroups"][0]["options"][0]["weapons"]
    weapons.reverse()
    weapons[1]["order"] = 2
    assert ("weapons", 4) in persistent_references(old, new)
    weapons[1]["q"] = 99
    assert ("weapons", 4) not in persistent_references(old, new)
    new["units"][0]["name"] = "Changed"
    assert not persistent_references(old, new)


def test_definition_changes_preserve_origin_scope_and_evidence():
    old = faction()
    option = old["units"][0]["profileGroups"][0]["options"][0]
    option["peripheral"] = [{"id": 2}]
    old["filters"] = {
        "weapons": [{"id": 4, "name": "Rifle"}, {"id": 5, "name": "Pistol"}],
        "peripheral": [{"id": 2, "name": "A"}],
    }
    new = deepcopy(old)
    new["filters"]["peripheral"][0]["name"] = "B"
    new["filters"]["weapons"][0]["mercs"] = True
    source = SyntheticSource(pair(101, old, new) + pair(102, old, new))
    source.documents["a"] = {"weapons": [{"id": 4, "damage": 13}, {"id": 5}]}
    source.documents["b"] = {"weapons": [{"id": 4, "damage": 14}, {"id": 5}]}
    source.metadata_contexts = {i: ("a" if i % 2 == 0 else "b",) for i in range(4)}
    result = compare_definitions(source, report(source))
    groups = result["transitionGroups"]
    assert len(groups) == 3
    meta = next(g for g in groups if g["origin"] == "metadata")
    assert meta["scopeArmyId"] is None
    assert meta["category"] == "weaponMechanicsCandidate"
    assert meta["changedFields"] == ["damage"]
    assert len(meta["evidence"]) == 2
    assert all(e["usages"][0]["reference"]["id"] == 4 for e in meta["evidence"])
    assert {g["scopeArmyId"] for g in groups if g["origin"] == "factionFilter"} == {101, 102}
    assert all(g["field"] == "peripheral" for g in groups if g["origin"] == "factionFilter")
    source.metadata_contexts[1] = ("a", "b")
    result = compare_definitions(source, report(source))
    meta = next(g for g in result["transitionGroups"] if g["origin"] == "metadata")
    assert len(meta["evidence"]) == 1
    assert any(e["status"] == "ambiguousContext" for e in result["review"])
