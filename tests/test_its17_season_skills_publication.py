"""ITS 17 V0.2 season-wide Skills and Casevac State remain isolated from ITS 18."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import build_its_database, inspect_its_database
from infinity_db.its_source_family import project_its_source_family
from tests.its17_inventory_expectations import EXPECTED_ITS17_SCENARIO_IDS

ROOT = Path(__file__).resolve().parents[1]
SEASON17 = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
SEASON18 = ROOT / "data/curated/its/n5-its-season-18.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"


def historical_records() -> dict[str, dict]:
    document = load_curated_document(SEASON17, shared_scenario_library=SHARED)
    return {record["id"]: record for record in document["records"]}


def test_all_original_its17_scenarios_are_present_without_resilience_extra() -> None:
    document = json.loads(SEASON17.read_text(encoding="utf-8"))
    assert document["collection"]["status"] == "archived"
    assert document["scenarioCollection"]["revision"] == "0.2"
    members = document["scenarioCollection"]["members"]
    assert [member["scenarioId"] for member in members] == list(EXPECTED_ITS17_SCENARIO_IDS)
    assert all("resilience" not in member["scenarioId"] for member in members)
    assert {record["id"] for record in document["records"]} == {
        "skill:civevac", "skill:casevac", "state:casevac",
        "rule:resilience-operations",
    }
    assert "short-movement-skill" in {
        item["id"] for item in document["skillTypes"]
    }


def test_original_casevac_and_civevac_types_have_bilingual_citations() -> None:
    records = historical_records()
    assert len(records) == len(EXPECTED_ITS17_SCENARIO_IDS) + 4  # season Skills, State, Extra
    expected = {
        "skill:civevac": [(EN, 17), (EN, 18), (ES, 18), (ES, 19)],
        "skill:casevac": [(EN, 19), (EN, 20), (ES, 20), (ES, 21)],
    }
    for identifier, pins in expected.items():
        skill = records[identifier]
        assert skill["kind"] == "skill"
        assert skill["facts"]["category"] == "common-skill"
        assert skill["facts"]["typeIds"] == ["short-movement-skill"]
        assert skill["facts"]["applicability"] == {
            "context": "season", "revision": "0.2",
        }
        assert skill["scope"] == {"game": "N5", "seasons": ["its-17"]}
        assert skill["review"]["status"] == "reviewed"
        assert [(c["sourceId"], c["page"]) for c in skill["citations"]] == pins

    assert any("two Civilians" in effect for effect in
               records["skill:civevac"]["facts"]["effects"])
    assert any("[[state:casevac|Casevac State]]" in effect
               for effect in records["skill:casevac"]["facts"]["effects"])
    assert not any("Team-Ops" in record["name"] for record in records.values())


def test_historical_casevac_state_preserves_activation_and_cancelation() -> None:
    state = historical_records()["state:casevac"]
    assert state["kind"] == "state"
    assert state["scope"] == {"game": "N5", "seasons": ["its-17"]}
    assert state["facts"]["applicability"] == {
        "context": "season", "revision": "0.2",
    }
    assert [(c["sourceId"], c["page"]) for c in state["citations"]] == [
        (EN, 20), (EN, 21), (ES, 21), (ES, 22),
    ]
    requirements = state["facts"]["requirements"]
    effects = state["facts"]["effects"]
    restrictions = state["facts"]["restrictions"]
    assert any("[[skill:casevac|Casevac]]" in text for text in requirements)
    assert any("one Order or ARO" in text for text in effects)
    assert any("Template Weapons Into Close Combat" in text for text in effects)
    assert any("Short Movement Skill" in text for text in effects)
    assert any("Impetuous Phase" in text for text in effects)
    assert any("recovers from Immobilized" in text for text in effects)
    assert any("voluntarily" in text and "Short Skill" in text for text in effects)
    assert any("at most one" in text for text in restrictions)


def test_historical_skills_and_state_build_in_isolated_database(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON17, target, shared_library=SHARED)
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert [item["id"] for item in report["scenarios"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    assert {item["id"] for item in report["skills"]} == {
        "skill:civevac", "skill:casevac",
    }
    assert {item["id"] for item in report["states"]} == {"state:casevac"}
    assert inspect_its_database(
        target, source=SEASON17, shared_library=SHARED,
        require_current_builder=True,
    ) == report

    current = project_its_source_family(load_curated_document(SEASON18))
    new = {record["id"]: record for record in current["records"]}
    assert new["skill:casevac"]["facts"]["typeIds"] == ["short-skill"]
    assert new["skill:civevac"]["facts"]["typeIds"] == ["basic-short-skill"]
    assert all(new[identifier]["scope"]["seasons"] == ["its-18"] for identifier in (
        "skill:casevac", "skill:civevac", "state:casevac",
    ))


@pytest.mark.parametrize("identifier", [
    "skill:civevac", "skill:casevac", "state:casevac",
])
def test_historical_season_revision_mismatch_is_rejected(
    tmp_path: Path, identifier: str,
) -> None:
    document = json.loads(SEASON17.read_text(encoding="utf-8"))
    record = next(r for r in document["records"] if r["id"] == identifier)
    record["facts"]["applicability"]["revision"] = "2026.09.11"
    modified = tmp_path / "bad.json"
    modified.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="revision applicability|current-revision applicability"):
        build_its_database(modified, tmp_path / "bad.db", shared_library=SHARED)
