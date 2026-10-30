"""Source and publication boundaries for core N5.3 scenario objectives."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from infinity_db.curated import load_curated_document
from tools.audit_core_scenario_objects import (
    CURATED,
    PUBLICATION,
    audit_scenario_object_boundary,
    audit_source_files,
    main,
)


def _inputs() -> tuple[dict, dict]:
    return (
        load_curated_document(CURATED),
        json.loads(PUBLICATION.read_text(encoding="utf-8")),
    )


def test_core_scenario_object_census_is_separate_from_deployables() -> None:
    report = audit_source_files(CURATED, PUBLICATION)
    assert report["scope"] == "core-scenario-objects-not-weapon-equipment-deployables"
    assert report["coreScenarioCount"] == 4
    assert report["reviewedDeployedObjectCount"] == 17
    assert len(report["curatedSourceSha256"]) == 64
    assert len(report["deployedPublicationSha256"]) == 64
    cases = {r["scenarioId"]: r for r in report["scenarios"]}
    assert set(cases) == {
        "scenario:annihilation", "scenario:domination",
        "scenario:supplies", "scenario:firefight",
    }
    assert {
        name: (row["markerType"], row["physicalObjectCount"])
        for name, row in cases.items()
    } == {
        "scenario:annihilation": (None, 0),
        "scenario:domination": ("console", 4),
        "scenario:supplies": ("supply-box", 3),
        "scenario:firefight": (None, 0),
    }
    for scenario in cases.values():
        assert len(scenario["configurations"]) == 3
        assert all(
            len(configuration["markerIds"]) == scenario["physicalObjectCount"]
            for configuration in scenario["configurations"]
        )
    assert cases["scenario:domination"]["interactionSkills"] == ["skill:hack-consoles"]
    assert cases["scenario:domination"]["scoringStatuses"] == ["hacked"]
    assert cases["scenario:supplies"]["interactionSkills"] == [
        "skill:pick-up-supply-boxes",
    ]
    assert cases["scenario:supplies"]["scoringStatuses"] == ["controlled"]
    assert cases["scenario:supplies"]["ruleId"] == "rule:scenario:supply-boxes"
    assert cases["scenario:domination"]["ruleId"] == "rule:scenario:consoles"


def test_scenario_object_audit_rejects_domain_promotion_and_source_drift() -> None:
    curated, publication = _inputs()
    assert audit_scenario_object_boundary(curated, publication)["coreScenarioCount"] == 4

    promoted = copy.deepcopy(publication)
    promoted["objects"].append({
        "id": "invented-console", "name": "Console",
    })
    with pytest.raises(ValueError, match="unexpectedly published"):
        audit_scenario_object_boundary(curated, promoted)

    duplicated = copy.deepcopy(publication)
    duplicated["objects"].append(copy.deepcopy(duplicated["objects"][0]))
    with pytest.raises(ValueError, match="Duplicate reviewed"):
        audit_scenario_object_boundary(curated, duplicated)

    tampered = copy.deepcopy(curated)
    rule = next(
        row for row in tampered["records"] if row["id"] == "rule:scenario:consoles"
    )
    rule["citations"][0]["page"] = 999
    with pytest.raises(ValueError, match="rule provenance"):
        audit_scenario_object_boundary(tampered, publication)

    tampered = copy.deepcopy(curated)
    scenario = next(
        row for row in tampered["records"] if row["id"] == "scenario:supplies"
    )
    scenario["citations"][0]["page"] = 999
    with pytest.raises(ValueError, match="PDF provenance"):
        audit_scenario_object_boundary(tampered, publication)

    tampered = copy.deepcopy(curated)
    skill = next(
        row for row in tampered["records"]
        if row["id"] == "skill:pick-up-supply-boxes"
    )
    skill["scope"]["scenarios"] = ["scenario:domination"]
    with pytest.raises(ValueError, match="not applicable|interaction provenance"):
        audit_scenario_object_boundary(tampered, publication)


def test_core_scenario_object_audit_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_core_scenario_objects"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Core scenarios: 4" in output
    assert "scenario:domination: 4 console" in output
    assert "scenario:supplies: 3 supply-box" in output
    assert "Unchanged reviewed Weapon/Equipment objects: 17" in output
