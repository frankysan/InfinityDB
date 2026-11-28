"""Private Army history SQLite import preserves the research evidence boundary."""

import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.army_history_source import HistoricalArmySource, digest
from tools.research import build_army_history_database as history


def fixture():
    earlier = {"encodedRevisionDate": "2025-01-01", "sha256": "a",
               "observationIndices": [0], "metadataSha256": []}
    later = {"encodedRevisionDate": "2025-02-01", "sha256": "b",
             "observationIndices": [1], "metadataSha256": []}
    other_earlier = {**earlier, "observationIndices": [2]}
    other_later = {**later, "observationIndices": [3]}
    other_alternative = {**later, "sha256": "c", "observationIndices": [4]}
    groups = {
        ("n5", army, endpoint["encodedRevisionDate"], endpoint["sha256"]):
        tuple(endpoint["observationIndices"])
        for army, endpoints in ((101, [earlier, later]),
                                (102, [other_earlier, other_later, other_alternative]))
        for endpoint in endpoints
    }
    observations = sorted([
        (i, {"edition": edition, "factionId": army, "sha256": sha,
             "encodedRevisionDate": date})
        for (edition, army, date, sha), indices in groups.items()
        for i in indices
    ])
    source = HistoricalArmySource(
        Path("test.zip"), "pin",
        {"observations": [row for _, row in observations], "coverage": "incomplete",
         "sourceScope": {}, "evidence": {}},
        {}, groups, (), {}, {},
    )
    path = ["units", 42, "profileGroups", 1, "profiles", 2, "bs"]
    ev = {"comparisonIndex": 0, "changeIndex": 0, "factionId": 101,
          "earlier": earlier, "later": later}
    comparison = {"factionId": 101, "earlier": earlier, "later": later,
                  "changes": [{"path": path, "category": "gameplayFieldCandidate",
                               "before": {"present": True, "value": 11},
                               "after": {"present": True, "value": 12}}]}
    row = {"path": path, "candidateId": "candidate", "evidence": [ev],
           "earlierObservedDate": "2025-01-01", "laterObservedDate": "2025-02-01"}
    catalog_evidence = {k: v for k, v in ev.items() if k != "changeIndex"}
    catalog_evidence["usages"] = [{"path": path}, {"path": ["units", 43, "weapons"]}]
    reports = {
        "characterization": {},
        "identityReview": {},
        "pilot": {"comparisons": [comparison], "skipped": [
            {"factionId": 102, "earlier": [other_earlier],
             "later": [other_later, other_alternative]},
        ]},
        "consolidation": {
            "candidates": [row],
            "identityInventory": {"eligibleUnitIds": [42, 43], "candidates": [
                {"unitId": i, "candidateKey": f"n5:{i}", "status": "consistentObservedIdAndSlug"}
                for i in (42, 43)
            ]},
        },
        "membership": {"nestedCandidateGroups": [], "structuralOccurrences": [],
                       "declaredMembershipClaims": [], "armyFieldOccurrences": [], "review": []},
        "loadouts": {"matches": [], "unpaired": [], "modificationReviewGroups": []},
        "catalogs": {"transitionGroups": [
            {"definitionTransitionId": "definition", "evidence": [catalog_evidence]},
        ], "review": []},
    }
    return source, reports


def test_private_database_preserves_evidence_and_separate_definition_stream():
    source, reports = fixture()
    with closing(sqlite3.connect(":memory:")) as db:
        counts = history.populate(db, source, reports)
        assert counts["rawChanges"] == counts["compositionCandidate"] == 1
        assert counts["comparisons"] == counts["coverageGaps"] == 1
        assert counts["sourceObservations"] == 5
        assert counts["recordUnitLinks"] == 3
        assert counts["recordEvidenceLinks"] == 2
        rows = db.execute("SELECT stream, unit_id FROM history_record_unit ORDER BY 1,2")
        assert rows.fetchall() == [
            ("catalogTransition", 42), ("catalogTransition", 43), ("compositionCandidate", 42),
        ]
        rows = db.execute("SELECT stream, change_index FROM history_record_evidence ORDER BY 1")
        assert rows.fetchall() == [
            ("catalogTransition", None), ("compositionCandidate", 0),
        ]
        raw = db.execute(
            "SELECT body FROM history_record WHERE stream='compositionCandidate'"
        ).fetchone()
        assert json.loads(raw[0]) == reports["consolidation"]["candidates"][0]
        assert db.execute(
            "SELECT body FROM metadata WHERE key='publicationStatus'"
        ).fetchone() == ('"privateResearchOnly"',)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("problem", ["missingGap", "invalidChange", "wrongEndpoint"])
def test_invalid_evidence_is_rejected(problem):
    source, reports = fixture()
    reports = deepcopy(reports)
    if problem == "missingGap":
        reports["pilot"]["skipped"] = []
    elif problem == "invalidChange":
        reports["consolidation"]["candidates"][0]["evidence"][0]["changeIndex"] = 99
    else:
        reports["consolidation"]["candidates"][0]["evidence"][0]["factionId"] = 999
    with closing(sqlite3.connect(":memory:")) as db, pytest.raises(ValueError):
        history.populate(db, source, reports)


def test_report_pin_rejects_modified_bytes(tmp_path, monkeypatch):
    source, _ = fixture()
    directory = tmp_path / "reports"
    directory.mkdir()
    report = directory / "characterization.json"
    original = history.encode({"formatVersion": 1, "archiveSha256": source.sha256}).encode()
    report.write_bytes(original)
    monkeypatch.setattr(history, "REPORTS", {
        "characterization": (report.name, 1, digest(original)),
    })
    assert history.selected_reports(tmp_path, source)["characterization"]["formatVersion"] == 1
    report.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="SHA-256 differs"):
        history.selected_reports(tmp_path, source)


@pytest.mark.parametrize(("status", "direct", "current", "expected"), [
    ("consistentObservedIdAndSlug", {3}, True, "matched"),
    ("reviewedSpellingAlias", {3}, True, "matched"),
    ("reviewedSeparateArmyIdentity", {3}, True, "matched"),
    ("review", {3}, True, "historicalIdentityReview"),
    ("consistentObservedIdAndSlug", set(), True, "noDirectEvidence"),
    ("consistentObservedIdAndSlug", set(), False, "historicalOnly"),
    ("consistentObservedIdAndSlug", {3}, False, "missingCurrentSource"),
])
def test_preview_requires_direct_identity_evidence(status, direct, current, expected):
    from tools.research.project_army_history import resolve_identity

    historical = {
        "unitId": 42, "status": status,
        "slugEvidence": [{"slug": "test", "occurrences": [
            {"observationIndices": [3], "canonical": 101, "idArmy": 42},
        ]}],
    }
    row = {"sourceSlug": "test", "canonicalFactionId": 101, "idArmy": 42,
           "logicalUnitId": 7}
    result = resolve_identity(historical, row if current else None, direct)
    assert result["status"] == expected
    assert result["logicalUnitId"] == (7 if expected == "matched" else None)
    if expected == "matched":
        for field, changed in (("sourceSlug", "other"), ("canonicalFactionId", 102),
                               ("idArmy", 43)):
            conflict = resolve_identity(historical, {**row, field: changed}, direct)
            assert conflict["status"] == "currentSourceConflict"
            assert conflict["logicalUnitId"] is None


def test_preview_groups_only_identical_target_window_and_scope():
    from tools.research.project_army_history import composition_groups

    def candidate(field, comparison, army=101, end="2025-02-01"):
        return {
            "ref": {"stream": "compositionCandidate", "position": comparison},
            "historicalLabels": [[{"id": 42, "name": "Historical name"}]],
            "body": {
                "candidateId": f"{field}-{comparison}-{end}",
                "path": ["units", 42, "profileGroups", 1, "profiles", 2, field],
                "earlierObservedDate": "2025-01-01", "laterObservedDate": end,
                "before": {"present": True, "value": 11},
                "after": {"present": True, "value": 12},
                "evidence": [{"factionId": army, "comparisonIndex": comparison}],
            },
        }

    rows = [candidate("bs", 0), candidate("cc", 0), candidate("ph", 1),
            candidate("wip", 0, end="2025-03-01")]
    result = composition_groups(rows)
    assert len(result) == 3
    assert sum(len(group["changes"]) for group in result) == 4
    combined = next(group for group in result if len(group["changes"]) == 2)
    assert [c["field"] for c in combined["changes"]] == ["bs", "cc"]
    assert combined["historicalLabels"][0][0]["name"] == "Historical name"
    assert combined["comparisonIndices"] == [0]
    assert combined["status"] == "observedCandidate"


def history_reference(identity, *, name="Weapon", metadata: str | None = "a", quantity=1):
    return {
        "filter": {"id": identity, "name": name},
        "metadataFingerprints": [metadata] if metadata else None,
        "occurrence": {"quantity": quantity},
    }


def test_render_reference_multisets_preserve_duplicates_and_distinct_ids():
    from tools.research.render_army_history import reference_changes

    first = history_reference(1)
    other = history_reference(2)
    changes = reference_changes([first, first], [first, other])
    assert changes == [
        {"kind": "removed", "before": [first], "after": []},
        {"kind": "added", "before": [], "after": [other]},
    ]


def test_render_reference_definition_changes_not_occurrence_changes():
    from tools.research.render_army_history import reference_changes

    first = history_reference(1)
    changed = history_reference(1, metadata="b")
    assert reference_changes([first], [changed]) == [
        {"kind": "definitionChanged", "before": [first], "after": [changed]},
    ]
    modified = history_reference(1, quantity=2)
    assert reference_changes([first], [modified])[0]["kind"] == "changed"
    assert reference_changes([first, modified], [modified, first]) == []


def test_history_render_preserves_source_values_and_escapes_names():
    from tools.research.render_army_history import render_change, value_text

    row = history_reference(1, name="<script>alert(1)</script>", metadata=None)
    change = {
        "field": "skills", "before": {"present": True, "value": []},
        "after": {"present": True, "value": [row]},
        "evidenceRecord": {"stream": "compositionCandidate", "position": 0,
                           "sourceUnitId": 42},
    }
    html, counts = render_change(change)
    assert counts == {"skills:added": 1}
    assert "Added occurrence" in html and "filter-only evidence" in html
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert value_text("ava", {"present": False}) == "Not present in source"
    assert value_text("ava", {"present": True, "value": None}) == "Null (source value)"
    assert value_text("move", {"present": True, "value": [4, 4]}) == "4-4"


def test_render_army_observations_distinguish_list_presence_from_availability():
    from tools.research.render_army_history import render_army

    row = {
        "kind": "unitListMembership", "direction": "appeared", "armyId": 101,
        "earlierObservedDate": "2025-01-01", "laterObservedDate": "2025-02-01",
        "sourcePath": ["units", 42],
        "evidenceRecord": {"stream": "structuralOccurrence", "position": 0,
                           "sourceUnitId": 42},
    }
    html = render_army(row, {101: "Army A"})
    assert "Appeared in source list" in html
    assert "current label" in html
    assert "Observed between 2025-01-01 and 2025-02-01" in html
    assert "Added to Army" not in html


def semantic_group(profile_skills, options):
    return {
        "units": [{"id": 42, "name": "Test Unit", "profileGroups": [{
            "id": 1, "profiles": [{"id": 1, "name": "Test Profile",
                                  "skills": profile_skills}],
            "options": options,
        }]}],
        "filters": {"skills": [{"id": 1, "name": "Mimetism"},
                               {"id": 2, "name": "Engineer"}]},
    }


def semantic_option(identity, skills=None, points=20):
    return {"id": identity, "name": "Test", "skills": skills or [],
            "points": points, "swc": 0}


def semantic_summary_with_coverage(old, new, field, paths, rekeys=None):
    from tools.research.summarize_army_history import summarize_group

    return summarize_group(old, new, 42, 1, field, [{}], [{}], set(paths), rekeys)


def semantic_summary(old, new, field, paths, rekeys=None):
    return semantic_summary_with_coverage(old, new, field, paths, rekeys)[:2]


def test_effective_history_suppresses_relocation_and_counts_real_gain():
    skill = {"id": 1}
    old = semantic_group([], [semantic_option(1, [skill]), semantic_option(2)])
    new = semantic_group([skill], [semantic_option(1), semantic_option(2)])
    paths = [
        ("units", 42, "profileGroups", 1, "profiles", 1, "skills"),
        ("units", 42, "profileGroups", 1, "options", 1, "skills"),
    ]
    result, status = semantic_summary(old, new, "skills", paths)
    assert status == "comparable"
    assert result is not None and len(result) == 1
    assert result[0]["summary"] == "Gained Mimetism"
    assert [row["optionId"] for row in result[0]["loadouts"]] == [2]
    assert result[0]["allGroupLoadouts"] is False
    unchanged = semantic_group([skill], [semantic_option(1)])
    previous = semantic_group([], [semantic_option(1, [skill])])
    assert semantic_summary(previous, unchanged, "skills", paths) == ([], "comparable")
    partial, status, coverage = semantic_summary_with_coverage(
        old, new, "skills", paths[:1],
    )
    assert status == "partial"
    assert partial == result
    assert coverage["reviewPairs"] == [
        {"beforeOptionId": 1, "afterOptionId": 1, "reason": "unacceptedReferenceChange"},
    ]


def test_effective_history_consolidates_cost_delta():
    old = semantic_group([], [semantic_option(1, points=20), semantic_option(2, points=30)])
    new = semantic_group([], [semantic_option(1, points=18), semantic_option(2, points=28)])
    paths = [("units", 42, "profileGroups", 1, "options", i, "points") for i in (1, 2)]
    result, status = semantic_summary(old, new, "points", paths)
    assert status == "comparable"
    assert result is not None and len(result) == 1
    assert result[0]["summary"] == "-2 Points"
    assert result[0]["allGroupLoadouts"]
    assert [(r["before"], r["after"]) for r in result[0]["loadouts"]] == [(20, 18), (30, 28)]
    partial, status, coverage = semantic_summary_with_coverage(
        old, new, "points", paths[:1],
    )
    assert status == "partial"
    assert partial is not None and partial[0]["allGroupLoadouts"] is False
    assert coverage["reviewPairs"] == [
        {"beforeOptionId": 2, "afterOptionId": 2, "reason": "unacceptedCostChange"},
    ]


def test_effective_history_accepts_only_complete_reconciled_rekeys():
    skill = {"id": 1}
    old = semantic_group([], [semantic_option(1, [skill])])
    new = semantic_group([], [semantic_option(2, [skill], points=18)])
    assert semantic_summary(old, new, "points", []) == (None, "changedLoadoutKeys")
    result, status = semantic_summary(old, new, "points", [], {1: 2})
    assert status == "comparable"
    assert result is not None and result[0]["summary"] == "-2 Points"
    assert result[0]["loadouts"][0]["laterOptionId"] == 2
    conflict = semantic_group([], [semantic_option(2, [{"id": 2}])])
    assert semantic_summary(old, conflict, "points", [], {1: 2}) == (
        None, "rekeyCompositionConflict",
    )


def test_effective_history_rejects_overlapping_layers_and_peripherals():
    skill = {"id": 1}
    old = semantic_group([skill], [semantic_option(1, [skill])])
    new = semantic_group([skill], [semantic_option(1)])
    assert semantic_summary(old, new, "skills", []) == (None, "overlappingOwners")
    new["units"][0]["profileGroups"][0]["options"][0]["peripheral"] = [{"id": 1}]
    assert semantic_summary(old, new, "skills", []) == (None, "includesOrPeripheral")


def test_effective_reference_comparison_ignores_definition_only_and_default_quantity():
    from tools.research.summarize_army_history import effective_delta, reference_summary

    old = {"filter": {"id": 1, "name": "Mimetism"}, "occurrence": {},
           "metadataFingerprints": ["a"]}
    new = {"filter": {"id": 1, "name": "Mimetism renamed"}, "occurrence": {"q": 1},
           "metadataFingerprints": ["b"]}
    assert effective_delta([old], [new]) == {"lost": [], "gained": []}
    changed = {**old, "occurrence": {"extra": [{"id": 2, "name": "-3"}]}}
    assert reference_summary(effective_delta([old], [changed])) == (
        "Changed Mimetism → Mimetism (-3)"
    )

def test_effective_history_partial_continuity_with_added_and_removed_loadouts():
    skill = {"id": 1}
    old = semantic_group([], [semantic_option(1, [skill]), semantic_option(2),
                              semantic_option(3)])
    new = semantic_group([skill], [semantic_option(1), semantic_option(2),
                                   semantic_option(4)])
    paths = [
        ("units", 42, "profileGroups", 1, "profiles", 1, "skills"),
        ("units", 42, "profileGroups", 1, "options", 1, "skills"),
    ]
    result, status, coverage = semantic_summary_with_coverage(
        old, new, "skills", paths,
    )
    assert status == "partial"
    assert result is not None and len(result) == 1
    assert result[0]["summary"] == "Gained Mimetism"
    assert [row["optionId"] for row in result[0]["loadouts"]] == [2]
    assert result[0]["allGroupLoadouts"] is False
    assert coverage["unpairedBefore"] == [3]
    assert coverage["unpairedAfter"] == [4]
    assert coverage["comparedPairs"] == [
        {"beforeOptionId": 1, "afterOptionId": 1, "changed": False},
        {"beforeOptionId": 2, "afterOptionId": 2, "changed": True},
    ]


def test_effective_history_disabled_sibling_does_not_block_survivor():
    disabled = {**semantic_option(2), "disabled": True}
    old = semantic_group([], [semantic_option(1), disabled])
    new = semantic_group([], [semantic_option(1, points=18), disabled])
    paths = [("units", 42, "profileGroups", 1, "options", 1, "points")]
    result, status, coverage = semantic_summary_with_coverage(
        old, new, "points", paths,
    )
    assert status == "partial"
    assert result is not None and result[0]["summary"] == "-2 Points"
    assert result[0]["allGroupLoadouts"] is False
    assert coverage["reviewPairs"] == [
        {"beforeOptionId": 2, "afterOptionId": 2, "reason": "disabledLoadout"},
    ]


def test_effective_history_partial_no_change_does_not_claim_complete_comparison():
    old = semantic_group([], [semantic_option(1), semantic_option(2)])
    new = semantic_group([], [semantic_option(1), semantic_option(3)])
    result, status, coverage = semantic_summary_with_coverage(
        old, new, "points", [],
    )
    assert result == [] and status == "partial"
    assert coverage["unpairedBefore"] == [2] and coverage["unpairedAfter"] == [3]


def test_effective_history_partial_rekey_preserves_unpaired_keys():
    skill = {"id": 1}
    old = semantic_group([], [semantic_option(1, [skill]), semantic_option(3)])
    new = semantic_group([], [semantic_option(2, [skill], points=18), semantic_option(4)])
    result, status, coverage = semantic_summary_with_coverage(
        old, new, "points", [], {1: 2},
    )
    assert status == "partial"
    assert result is not None and result[0]["loadouts"][0]["laterOptionId"] == 2
    assert result[0]["allGroupLoadouts"] is False
    assert coverage["unpairedBefore"] == [3] and coverage["unpairedAfter"] == [4]


def lifecycle_event(option, direction="appeared", possible=None):
    present, absent = {"present": True, "value": option}, {"present": False}
    return {
        "path": ["units", 42, "profileGroups", 1, "options", option["id"]],
        "direction": direction, "possibleReplacementIds": possible or [],
        "before": absent if direction == "appeared" else present,
        "after": present if direction == "appeared" else absent,
    }


@pytest.mark.parametrize("direction", ["appeared", "disappeared"])
def test_lifecycle_one_sided_effective_loadout(direction):
    from tools.research.summarize_army_history import lifecycle_payload

    option = semantic_option(2, [{"id": 2}], points=23)
    one = semantic_group([{"id": 1}], [semantic_option(1)])
    two = semantic_group([{"id": 1}], [semantic_option(1), option])
    old, new = (one, two) if direction == "appeared" else (two, one)
    result, status = lifecycle_payload(
        old, new, lifecycle_event(option, direction), "noOppositeKey", [{}], [{}],
    )
    assert status == "oneSided"
    assert result is not None
    assert result["kind"] == ("loadoutAdded" if direction == "appeared" else "loadoutRemoved")
    assert result["points"] == 23
    assert {r["filter"]["name"] for r in result["effectiveReferences"]["skills"]} == {
        "Mimetism", "Engineer",
    }
    assert result["status"] == "observedCandidate"
    assert "Engineer" in result["summary"]


def test_lifecycle_does_not_infer_replacement_or_add_remove_from_two_sided_keys():
    from tools.research.summarize_army_history import lifecycle_payload

    option = semantic_option(2, [{"id": 2}])
    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [option])
    for reason in ("modificationReview", "ambiguousModification", "noUniqueCompositionMatch"):
        assert lifecycle_payload(old, new, lifecycle_event(option), reason, [{}], [{}]) == (
            None, reason,
        )
    assert lifecycle_payload(
        old, new, lifecycle_event(option, possible=[1]), "noOppositeKey", [{}], [{}],
    ) == (None, "possibleReplacement")
    assert lifecycle_payload(
        old, new, lifecycle_event(option), "noOppositeKey", [{}], [{}],
    ) == (None, "opposingKeyChanges")


@pytest.mark.parametrize(("extra", "expected"), [
    ({"disabled": True}, "disabledLoadout"),
    ({"includes": [7]}, "includesOrPeripheral"),
    ({"peripheral": [{"id": 1}]}, "includesOrPeripheral"),
    ({"skills": [{"id": 999}]}, "missingFactionDefinition"),
    ({"points": None}, "invalidCost"),
])
def test_lifecycle_retains_unsupported_options_as_review(extra, expected):
    from tools.research.summarize_army_history import lifecycle_payload

    option = {**semantic_option(2), **extra}
    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [semantic_option(1), option])
    assert lifecycle_payload(
        old, new, lifecycle_event(option), "noOppositeKey", [{}], [{}],
    ) == (None, expected)


def test_lifecycle_supports_first_or_last_loadout_without_inventing_continuity():
    from tools.research.summarize_army_history import lifecycle_payload

    option = semantic_option(1)
    empty = semantic_group([], [])
    populated = semantic_group([], [option])
    result, status = lifecycle_payload(
        empty, populated, lifecycle_event(option), "noOppositeKey", [{}], [{}],
    )
    assert result is not None and status == "oneSided"
    assert result["kind"] == "loadoutAdded"


@pytest.mark.parametrize(("raw", "expected"), [
    (0, "0"), (2, "2"), (100, "Total"), ("T", "Total"), ("total", "Total"),
    (None, None), (-1, None), (True, None), ("unknown", None),
])
def test_history_ava_display(raw, expected):
    from tools.research.summarize_army_history import ava_display

    assert ava_display({"present": True, "value": raw}) == expected
    assert ava_display({"present": False}) is None


def test_availability_retains_profile_scope_and_total():
    from tools.research.summarize_army_history import availability_payload

    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [semantic_option(1)])
    old["units"][0]["profileGroups"][0]["profiles"][0]["ava"] = 2
    new["units"][0]["profileGroups"][0]["profiles"][0]["ava"] = 100
    row = {
        "kind": "ava", "path": ["units", 42, "profileGroups", 1, "profiles", 1, "ava"],
        "before": {"present": True, "value": 2},
        "after": {"present": True, "value": 100},
    }
    payload, status = availability_payload(old, new, row)
    assert status == "observedFieldChange"
    assert payload is not None and payload["summary"] == "AVA: 2 → Total"
    assert payload["sourcePath"] == row["path"]
    assert payload["historicalLabels"][-1]["name"] == "Test Profile"


def test_availability_list_presence_does_not_claim_playable_availability():
    from tools.research.summarize_army_history import availability_payload

    new = semantic_group([], [semantic_option(1)])
    old = {"units": []}
    row = {
        "kind": "unitListMembership", "path": ["units", 42],
        "direction": "appeared", "possibleReplacementIds": [],
        "before": {"present": False},
        "after": {"present": True, "value": new["units"][0]},
        "sourceRole": "mercenaryVariant", "declaredInThisArmy": False,
    }
    payload, status = availability_payload(old, new, row)
    assert status == "observedListPresence"
    assert payload is not None and payload["summary"] == "Appeared in Army list"
    assert payload["declaredInThisArmy"] is False
    row["possibleReplacementIds"] = [99]
    assert availability_payload(old, new, row) == (None, "possibleReplacement")


def test_availability_disabled_state_not_inferred_from_missing_value():
    from tools.research.summarize_army_history import availability_payload

    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [semantic_option(1)])
    old["units"][0]["profileGroups"][0]["options"][0]["disabled"] = False
    new["units"][0]["profileGroups"][0]["options"][0]["disabled"] = True
    row = {
        "kind": "disabled", "path": ["units", 42, "profileGroups", 1, "options", 1, "disabled"],
        "before": {"present": True, "value": False},
        "after": {"present": True, "value": True},
    }
    payload, status = availability_payload(old, new, row)
    assert status == "observedFieldChange"
    assert payload is not None and payload["summary"] == "Disabled in Army source"
    del old["units"][0]["profileGroups"][0]["options"][0]["disabled"]
    row["before"] = {"present": False}
    assert availability_payload(old, new, row) == (None, "unresolvedDisabledState")


def test_mult_profile_relocation_preserves_individual_profile_scope():
    old = semantic_group([], [semantic_option(1, [{"id": 1}]), semantic_option(2)])
    new = semantic_group([{"id": 1}], [semantic_option(1), semantic_option(2)])
    for data in (old, new):
        data["units"][0]["profileGroups"][0]["profiles"].append(
            {"id": 2, "name": "Second Profile", "skills": []},
        )
    paths = [
        ("units", 42, "profileGroups", 1, "profiles", 1, "skills"),
        ("units", 42, "profileGroups", 1, "options", 1, "skills"),
    ]
    result, status, coverage = semantic_summary_with_coverage(
        old, new, "skills", paths,
    )
    assert status == "comparable"
    assert result is not None and len(result) == 2
    gained = next(r for r in result if r["gained"])
    lost = next(r for r in result if r["lost"])
    assert gained["profiles"] == [
        {"profileId": 1, "name": "Test Profile", "allProfileLoadouts": False},
    ]
    assert lost["profiles"] == [
        {"profileId": 2, "name": "Second Profile", "allProfileLoadouts": False},
    ]
    assert [r["optionId"] for r in gained["loadouts"]] == [2]
    assert [r["optionId"] for r in lost["loadouts"]] == [1]
    assert not any(r["allGroupLoadouts"] for r in result)
    assert len(coverage["profileComparisons"]) == 2


def test_multi_profile_cost_is_not_duplicated():
    old = semantic_group([], [semantic_option(1, points=20)])
    new = semantic_group([], [semantic_option(1, points=18)])
    for data in (old, new):
        data["units"][0]["profileGroups"][0]["profiles"].append(
            {"id": 2, "name": "Second Profile", "skills": []},
        )
    result, status = semantic_summary(
        old, new, "points", [("units", 42, "profileGroups", 1, "options", 1, "points")],
    )
    assert status == "comparable"
    assert result is not None and len(result) == 1
    assert result[0]["allGroupLoadouts"]
    assert len(result[0]["loadouts"]) == 1
    assert "profiles" not in result[0]


def test_stable_peripheral_rekey_allows_direct_owner_comparison():
    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([{"id": 1}], [semantic_option(1)])
    for data, identity in ((old, 7), (new, 9)):
        data["filters"]["peripheral"] = [{"id": identity, "name": "Attached Model"}]
        data["units"][0]["profileGroups"][0]["options"][0]["peripheral"] = [{"id": identity}]
    paths = [("units", 42, "profileGroups", 1, "profiles", 1, "skills")]
    result, status, coverage = semantic_summary_with_coverage(
        old, new, "skills", paths,
    )
    assert status == "comparable"
    assert result is not None and result[0]["summary"] == "Gained Mimetism"
    assert result[0]["loadouts"][0]["relationshipScope"] == "directOwners"
    assert coverage["comparedPairs"][0]["relationshipScope"] == "directOwners"
    new["filters"]["peripheral"][0]["name"] = "Different Model"
    assert semantic_summary(old, new, "skills", paths) == (None, "includesOrPeripheral")


def test_stable_include_edges_allow_direct_owner_changes_but_not_inheritance():
    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([{"id": 1}], [semantic_option(1)])
    for data in (old, new):
        groups = data["units"][0]["profileGroups"]
        groups[0]["options"][0]["includes"] = [{"group": 2, "option": 7}]
        groups.append({
            "id": 2, "name": "Included", "profiles": [
                {"id": 2, "name": "Included Profile", "skills": [{"id": 2}]},
            ], "options": [semantic_option(7)],
        })
    paths = [("units", 42, "profileGroups", 1, "profiles", 1, "skills")]
    result, status, coverage = semantic_summary_with_coverage(
        old, new, "skills", paths,
    )
    assert status == "comparable"
    assert result is not None and result[0]["summary"] == "Gained Mimetism"
    assert result[0]["loadouts"][0]["relationshipFields"] == ["includes"]
    assert coverage["comparedPairs"][0]["relationshipScope"] == "directOwners"
    assert not result[0]["lost"]
    new["units"][0]["profileGroups"][0]["options"][0]["includes"][0]["q"] = 2
    assert semantic_summary(old, new, "skills", paths) == (None, "includesOrPeripheral")
    new["units"][0]["profileGroups"][0]["options"][0]["includes"][0]["q"] = 1
    new["units"][0]["profileGroups"][1]["options"] = []
    assert semantic_summary(old, new, "skills", paths) == (None, "includesOrPeripheral")


def relationship_change(old, new, field):
    a = old["units"][0]["profileGroups"][0]["options"][0]
    b = new["units"][0]["profileGroups"][0]["options"][0]
    return {
        "path": ["units", 42, "profileGroups", 1, "options", 1, field],
        "ancestorOrRecordLabelChanged": False,
        "before": {"present": True, "value": a[field]} if field in a else {"present": False},
        "after": {"present": True, "value": b[field]} if field in b else {"present": False},
    }


def test_relationship_history_peripheral_quantity_and_rekey():
    from tools.research.summarize_army_history import relationship_payload

    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [semantic_option(1)])
    for data, identity in ((old, 7), (new, 9)):
        data["filters"]["peripheral"] = [{"id": identity, "name": "Attached Model"}]
        data["units"][0]["profileGroups"][0]["options"][0]["peripheral"] = [
            {"id": identity, "order": identity},
        ]
    assert relationship_payload(old, new, relationship_change(old, new, "peripheral")) == (
        None, "unchangedRelationship",
    )
    new["units"][0]["profileGroups"][0]["options"][0]["peripheral"][0]["q"] = 2
    result, status = relationship_payload(old, new, relationship_change(old, new, "peripheral"))
    assert status == "changedRelationship"
    assert result is not None
    assert result["summary"] == "Changed Peripheral attachment: Attached Model → 2 × Attached Model"
    new["filters"]["peripheral"][0]["name"] = "Different Model"
    assert relationship_payload(old, new, relationship_change(old, new, "peripheral")) == (
        None, "possibleAttachmentReplacement",
    )


def test_relationship_history_include_addition_and_unresolved_target():
    from tools.research.summarize_army_history import relationship_payload

    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [semantic_option(1)])
    for data in (old, new):
        data["units"][0]["profileGroups"].append({
            "id": 2, "name": "Included", "profiles": [
                {"id": 2, "name": "Included Profile", "skills": [{"id": 2}]},
            ], "options": [semantic_option(7)],
        })
    new["units"][0]["profileGroups"][0]["options"][0]["includes"] = [{"group": 2, "option": 7}]
    result, status = relationship_payload(old, new, relationship_change(old, new, "includes"))
    assert status == "changedRelationship"
    assert result is not None and result["summary"] == "Added Include: Included Profile (Test)"
    assert result["relationshipScope"] == "directOwner"
    assert result["lost"] == []
    new["units"][0]["profileGroups"][1]["options"] = []
    assert relationship_payload(old, new, relationship_change(old, new, "includes")) == (
        None, "unresolvedAttachmentTarget",
    )


def test_relationship_history_rejects_unresolved_definitions_and_ambiguous_owners():
    from tools.research.summarize_army_history import relationship_payload

    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [semantic_option(1)])
    new["filters"]["peripheral"] = [
        {"id": 7, "name": "Attached Model"}, {"id": 9, "name": "Attached Model"},
    ]
    new["units"][0]["profileGroups"][0]["options"][0]["peripheral"] = [{"id": 7}]
    change = relationship_change(old, new, "peripheral")
    assert relationship_payload(old, new, change) == (None, "unresolvedAttachmentTarget")
    change["ancestorOrRecordLabelChanged"] = True
    assert relationship_payload(old, new, change) == (None, "changedLabels")


def test_normalized_rekey_preserves_quantity_equivalence_and_cost_change():
    from tools.research.summarize_army_history import normalized_rekeys

    old = semantic_group([], [semantic_option(1, [{"id": 1}], points=20)])
    new = semantic_group([], [semantic_option(2, [{"id": 1, "q": 1}], points=18)])
    assert normalized_rekeys(old, new, 42, 1, [{}], [{}]) == {1: 2}
    result, status = semantic_summary(old, new, "points", [], {1: 2})
    assert status == "comparable"
    assert result is not None and result[0]["summary"] == "-2 Points"
    new["units"][0]["profileGroups"][0]["options"][0]["skills"][0]["q"] = 2
    assert normalized_rekeys(old, new, 42, 1, [{}], [{}]) == {}


def test_normalized_rekey_rejects_surviving_duplicate():
    from tools.research.summarize_army_history import normalized_rekeys

    old = semantic_group([], [semantic_option(1, [{"id": 1}]),
                              semantic_option(3, [{"id": 1}])])
    new = semantic_group([], [semantic_option(2, [{"id": 1}]),
                              semantic_option(3, [{"id": 1}])])
    assert normalized_rekeys(old, new, 42, 1, [{}], [{}]) == {}


def test_normalized_rekey_requires_resolved_include_and_peripheral_targets():
    from tools.research.summarize_army_history import normalized_rekeys

    old = semantic_group([], [semantic_option(1, [{"id": 1}])])
    new = semantic_group([], [semantic_option(2, [{"id": 1}])])
    for data, identity in ((old, 7), (new, 9)):
        groups = data["units"][0]["profileGroups"]
        groups[0]["options"][0]["includes"] = [{"group": 2, "option": 5}]
        groups[0]["options"][0]["peripheral"] = [{"id": identity}]
        groups.append({
            "id": 2, "name": "Included", "profiles": [{"id": 2, "name": "Included"}],
            "options": [semantic_option(5)],
        })
        data["filters"]["peripheral"] = [{"id": identity, "name": "Attached Model"}]
    assert normalized_rekeys(old, new, 42, 1, [{}], [{}]) == {1: 2}
    new["units"][0]["profileGroups"][1]["options"] = []
    assert normalized_rekeys(old, new, 42, 1, [{}], [{}]) == {}


def test_attachment_target_rekey_is_not_an_attachment_change():
    from tools.research.summarize_army_history import relationship_payload

    old = semantic_group([], [semantic_option(1)])
    new = semantic_group([], [semantic_option(1)])
    for data, identity in ((old, 7), (new, 9)):
        groups = data["units"][0]["profileGroups"]
        groups[0]["options"][0]["includes"] = [{"group": 2, "option": identity}]
        groups.append({
            "id": 2, "name": "Included", "profiles": [{"id": 2, "name": "Included"}],
            "options": [semantic_option(identity)],
        })
    change = relationship_change(old, new, "includes")
    assert relationship_payload(old, new, change) == (None, "possibleAttachmentReplacement")
    assert relationship_payload(old, new, change, {(2, 9): 7}) == (
        None, "unchangedRelationship",
    )
