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
