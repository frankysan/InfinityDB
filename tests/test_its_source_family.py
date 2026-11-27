"""ITS source-family projection: current-only publication and historical evidence."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import build_its_database, select_its_scenario
from infinity_db.its_source_family import project_its_source_family

SOURCE = Path(__file__).resolve().parents[1] / "data/curated/its/n5-its-season-18.json"
CURRENT = "2026.09.11"
OLDER = "2026.09.01"


def test_historical_facts_are_preserved_exactly_without_separate_authored_file() -> None:
    family = load_curated_document(SOURCE)
    current = project_its_source_family(family)
    historical = project_its_source_family(family, revision=OLDER)
    assert current["scenarioCollection"]["revision"] == CURRENT
    assert sum(record["kind"] == "scenario" for record in current["records"]) == 20
    assert sum(record["kind"] == "skill" for record in current["records"]) == 4
    assert current["collection"]["id"] == "its-season-18-2026.09.11"
    assert sum(record["kind"] == "rule" for record in current["records"]) == 5
    assert not any(record["kind"] == "rule" for record in historical["records"])
    assert [entry["id"] for entry in historical["records"] if entry["kind"] == "scenario"] == [
        "scenario:battleground"
    ]
    assert {entry["id"] for entry in historical["records"] if entry["kind"] == "skill"} == {
        "skill:civevac", "skill:casevac", "skill:team-ops", "skill:request-tacball",
    }
    assert historical["scenarioCollection"]["revision"] == OLDER
    assert historical["sources"][0]["version"] == OLDER
    assert [item["page"] for item in historical["records"][0]["citations"]] == [121, 122, 123]
    assert [item["page"] for item in current["records"][4]["citations"]] == [129, 130, 131]
    assert all(
        skill["facts"]["applicability"]["revision"] == OLDER
        for skill in historical["records"] if skill["kind"] == "skill"
    )
    assert all(
        policy["applicability"]["revision"] == OLDER
        for policy in historical["seasonPolicies"]
    )
    assert all(
        policy["applicability"]["revision"] == CURRENT
        for policy in current["seasonPolicies"]
    )
    # The deleted source's exact byte identity is preserved, without claiming
    # that a newly serialized projection must reproduce its original whitespace.
    assert family["sourceFamily"]["historicalRevisions"][0]["originalDocumentSha256"] == (
        "f002d279f711c5ac27e87cc3e91686beb85ec4e42aa7a740e2cebab1c4b2bbab"
    )


def test_current_publication_does_not_expose_historical_revision(tmp_path: Path) -> None:
    database = tmp_path / "current.db"
    published = build_its_database(SOURCE, database)
    assert published["inputIdentity"]["seasonRevision"] == CURRENT
    assert len(published["scenarios"]) == 20
    assert select_its_scenario(
        database, season_id="its-18", revision=OLDER, scenario_id="scenario:battleground",
    ) is None
    selected = select_its_scenario(
        database, season_id="its-18", revision=CURRENT, scenario_id="scenario:battleground",
    )
    assert selected and [citation["page"] for citation in selected["record"]["citations"]] == [
        129, 130, 131,
    ]


@pytest.mark.parametrize("bad", ["revision", "tag", "override", "membership"])
def test_invalid_source_family_fails_closed(bad: str) -> None:
    document = deepcopy(load_curated_document(SOURCE))
    family = document["sourceFamily"]
    if bad == "revision":
        family["currentRevision"] = OLDER
    elif bad == "tag":
        family["factRevisions"]["records"]["scenario:battleground"] = ["wrong"]
    elif bad == "override":
        family["historicalOverrides"][0]["fields"]["invented"] = "unsafe"
    elif bad == "membership":
        family["historicalRevisions"][0]["scenarioCollection"]["members"] = []
    with pytest.raises(ValueError):
        project_its_source_family(document)
