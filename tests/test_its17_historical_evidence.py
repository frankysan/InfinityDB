"""ITS 17 older-edition observations remain source-pinned and unprojected."""
from __future__ import annotations

import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    build_its_database,
    inspect_its_database,
    select_its_scenario,
)
from infinity_db.its_source_family import project_its_source_family
from tools.research.acquire_its_pdf import PINNED_REVISIONS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/curated/its/n5-its-season-17.json"
LIBRARY = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"


def _document() -> dict:
    return load_curated_document(SOURCE, shared_scenario_library=LIBRARY)


def _facts() -> dict:
    return {f["id"]: f for f in _document()["historicalEvidence"]["facts"]}


def test_its17_evidence_is_one_source_family_with_exact_pins() -> None:
    document = _document()
    evidence = document["historicalEvidence"]
    assert evidence["mode"] == "review-only-not-projected"
    assert len(evidence["sources"]) == 4
    assert len(evidence["facts"]) == 11
    assert sum(len(f["observations"]) for f in evidence["facts"]) == 44
    assert [s["revision"] + "-" + s["language"] for s in evidence["sources"]] == [
        "0.0-en", "0.0-es", "0.1-en", "0.1-es",
    ]
    for source in evidence["sources"]:
        edition = f"v{source['revision']}-{source['language']}"
        sha256, size, pages = PINNED_REVISIONS[edition]
        assert source["sha256"] == sha256
        assert source["pageCount"] == pages
        assert size > 0
        assert source["localPath"].endswith(f"its-rules-season-17-{edition}.pdf")
    assert {f["recordId"] for f in evidence["facts"]} <= {
        record["id"] for record in document["records"]
    }
    assert "historicalEvidence" not in project_its_source_family(document)


def test_historical_conflicts_and_new_constraints_remain_separate_by_edition() -> None:
    facts = _facts()

    def values(key: str) -> list[str]:
        return [o["value"] for o in facts[key]["observations"]]

    assert values("casevac-declaration-type") == [
        "short-skill", "habilidad-corta",
        "short-movement-skill", "habilidad-corta-basica",
    ]
    assert values("critical-intervention-reinforcements") == [
        "yes", "no", "no", "no",
    ]
    assert values("corporate-appropriation-panoply-scoring") == [
        "one-objective-point", "not-stated-in-main-objectives",
        "one-objective-point", "one-objective-point",
    ]
    for key in (
        "critical-intervention-inhibitor-unlock",
        "critical-intervention-turret-reaction",
        "area-of-interest-scenario-name",
        "area-of-interest-hacker-opposition",
        "crossing-lines-secure-objective-exclusions",
        "akial-interference-secure-objective-exclusions",
    ):
        before, before_es, after, after_es = values(key)
        assert before != after and before_es != after_es
    assert values("resilience-operations-first-reveal") == [
        "after-deployment-before-round-one",
        "after-deployment-before-round-one",
        "beginning-of-round-one",
        "after-deployment-before-round-one",
    ]
    assert values("outbreak-scenario-introduction") == [
        "not-listed-as-scenario",
    ] * 4


def test_history_does_not_create_older_scenario_routes_or_sqlite_rows(
    tmp_path: Path,
) -> None:
    document = _document()
    current = project_its_source_family(document)
    assert current == {
        key: value for key, value in document.items()
        if key != "historicalEvidence"
    }
    output = tmp_path / "historical-its17.db"
    report = build_its_database(SOURCE, output, shared_library=LIBRARY)
    assert report == inspect_its_database(
        output, source=SOURCE, shared_library=LIBRARY, require_current_builder=True,
    )
    assert report["inputIdentity"]["seasonRevision"] == "0.2"
    assert len(report["scenarios"]) == 16
    assert select_its_scenario(
        output, season_id="its-17", revision="0.1", scenario_id="scenario:hardlock",
    ) is None
    with sqlite3.connect(output) as db:
        assert db.execute("SELECT COUNT(*) FROM scenario_sets").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 2
        rows = db.execute("SELECT payload_json FROM records").fetchall()
        assert len(rows) == 20
        assert all("historicalEvidence" not in row[0] for row in rows)


@pytest.mark.parametrize(("mutation", "message"), [
    ("future-source", "source identity or pin"),
    ("wrong-hash", "source identity or pin"),
    ("wrong-path", "source identity or pin"),
    ("bad-source-page", "uniquely source-bound"),
    ("duplicate-observation", "uniquely source-bound"),
    ("unknown-source", "uniquely source-bound"),
    ("unknown-record", "invalid target"),
    ("duplicate-fact", "invalid target"),
    ("unsupported-mode", "explicitly review-only"),
    ("unreviewed-fact", "must be reviewed"),
    ("invalid-review-date", "ISO review date"),
    ("untyped-value", "uniquely source-bound"),
])
def test_historical_evidence_rejects_unreviewed_or_unbound_data(
    mutation: str, message: str,
) -> None:
    document = deepcopy(_document())
    evidence = document["historicalEvidence"]
    fact = evidence["facts"][0]
    if mutation == "future-source":
        evidence["sources"][0]["revision"] = "0.2"
    elif mutation == "wrong-hash":
        evidence["sources"][0]["sha256"] = "not a valid source digest"
    elif mutation == "wrong-path":
        evidence["sources"][0]["localPath"] = "data/pdf/its-18.pdf"
    elif mutation == "bad-source-page":
        fact["observations"][0]["page"] = 9999
    elif mutation == "duplicate-observation":
        fact["observations"].append(deepcopy(fact["observations"][0]))
    elif mutation == "unknown-source":
        fact["observations"][0]["sourceId"] = "its-season-18-en-pdf"
    elif mutation == "unknown-record":
        fact["recordId"] = "scenario:unreviewed"
    elif mutation == "duplicate-fact":
        evidence["facts"].append(deepcopy(fact))
    elif mutation == "unsupported-mode":
        evidence["mode"] = "publish-all-older-revisions"
    elif mutation == "unreviewed-fact":
        fact["review"]["status"] = "inferred"
    elif mutation == "invalid-review-date":
        fact["review"]["reviewedOn"] = "tomorrow"
    elif mutation == "untyped-value":
        fact["observations"][0]["value"] = True
    with pytest.raises(ValueError, match=message):
        project_its_source_family(document)
