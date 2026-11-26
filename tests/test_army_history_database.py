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


def history_reference(identity, *, name="Weapon", metadata="a", quantity=1):
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
