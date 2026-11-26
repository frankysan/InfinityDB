"""Composition continuity requires unique endpoint-specific sibling evidence."""

from copy import deepcopy

from infinity_db.army_history_consolidation import identity_inventory
from infinity_db.army_history_loadouts import composition, match_siblings, reconcile
from infinity_db.army_history_membership import membership
from infinity_db.army_history_pilot import catalog_index
from tests.test_army_history_consolidation import SyntheticSource, pair, report
from tests.test_army_history_pilot import faction


def options(data):
    return data["units"][0]["profileGroups"][0]["options"]


def fixture():
    old = faction()
    old["filters"] = {
        "weapons": [{"id": i, "name": str(i)} for i in (4, 5, 6, 7)],
    }
    new = deepcopy(old)
    options(new)[0]["id"] = 2
    metadata = {"weapons": [{"id": i, "name": str(i)} for i in (4, 5, 6, 7)]}
    return old, new, metadata


def match(old, new, metadata):
    left, right = ({r["id"]: r for r in options(data)} for data in (old, new))
    context = [catalog_index(metadata)]
    return match_siblings(
        left, right,
        {i: composition(r, old, context) for i, r in left.items()},
        {i: composition(r, new, context) for i, r in right.items()},
    )


def test_cost_name_and_display_changes_preserve_composition():
    old, new, meta = fixture()
    row = options(new)[0]
    row.update(points=17, name="Renamed")
    row["weapons"].reverse()
    row["weapons"][0].update(order=1, extra=None)
    row["weapons"][1]["order"] = 2
    matches, reasons = match(old, new, meta)
    assert not reasons
    assert matches[0]["kind"] == "sameComposition"
    assert matches[0]["changedNonCompositionFields"] == ["name", "points"]


def test_surviving_duplicate_and_unresolved_sibling_prevent_match():
    old, new, meta = fixture()
    for data in (old, new):
        options(data).append(dict(options(data)[0], id=9))
    matches, reasons = match(old, new, meta)
    assert not matches and len(reasons) == 2
    options(old)[1]["weapons"] = [{"id": 99}]
    options(new)[1]["weapons"] = [{"id": 99}]
    matches, reasons = match(old, new, meta)
    assert not matches and len(reasons) == 2


def test_distinctive_shared_reference_suggests_modification_only():
    old, new, meta = fixture()
    options(new)[0]["weapons"][1]["id"] = 6
    matches, reasons = match(old, new, meta)
    assert matches[0]["kind"] == "modificationReview"
    assert matches[0]["changedCompositionFields"] == ["weapons"]
    assert set(reasons.values()) == {"modificationReview"}
    # A generic shared weapon cannot distinguish the alternatives.
    for data in (old, new):
        options(data).append(dict(options(data)[0], id=9, weapons=[{"id": 4, "q": 2}]))
    matches, reasons = match(old, new, meta)
    assert not matches and len(reasons) == 2


def test_includes_and_quantities_not_silently_erased():
    old, new, meta = fixture()
    row = options(new)[0]
    options(old)[0]["includes"] = []
    row["includes"] = [{"group": 1, "option": 3}]
    matches, reasons = match(old, new, meta)
    assert not matches and reasons[("after", 2)] == "unresolvedIncludes"
    row["includes"] = []
    row["weapons"][0]["q"] = 3
    matches, reasons = match(old, new, meta)
    assert matches[0]["kind"] == "modificationReview"
    assert reasons


def test_one_sided_appearance_is_not_a_replacement():
    old, new, meta = fixture()
    options(new).append(deepcopy(options(old)[0]))
    matches, reasons = match(old, new, meta)
    assert not matches
    assert reasons == {("after", 2): "noOppositeKey"}


def test_modification_review_groups_retain_separate_windows():
    old, new, meta = fixture()
    options(new)[0]["weapons"][1]["id"] = 6
    source = SyntheticSource(pair(101, old, new) + pair(102, old, new, end="2025-02-02"))
    source.documents["meta"] = meta
    source.metadata_contexts = {i: ("meta",) for i in range(4)}
    evidence = membership(source, report(source), identity_inventory(source))
    result = reconcile(source, evidence)
    assert result["counts"]["modificationReview"] == 2
    assert result["counts"]["modificationReviewGroups"] == 1
    assert len(result["unpaired"]) == 4
    group = result["modificationReviewGroups"][0]
    assert {e["after"]["later"]["encodedRevisionDate"] for e in group["evidence"]} == {
        "2025-02-01", "2025-02-02",
    }


def test_reconcile_preserves_both_source_occurrences():
    old, new, meta = fixture()
    options(new)[0]["points"] = 17
    source = SyntheticSource(pair(101, old, new))
    source.documents["meta"] = meta
    source.metadata_contexts = {i: ("meta",) for i in range(2)}
    evidence = membership(source, report(source), identity_inventory(source))
    result = reconcile(source, evidence)
    assert result["loadoutOccurrences"] == 2
    assert result["counts"]["sameComposition"] == 1
    assert result["counts"]["previousReviewResolved"] == 2
    assert not result["unpaired"]
    match_row = result["matches"][0]
    assert match_row["before"]["before"]["value"]["id"] == 1
    assert match_row["after"]["after"]["value"]["id"] == 2
    assert match_row["rawChangedFields"] == ["id", "points"]
