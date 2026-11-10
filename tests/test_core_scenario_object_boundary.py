"""Source and publication boundaries for core N5.3 scenario objectives."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.rules_database import RulesDatabase, export_rules_database
from tools.audit_core_scenario_objects import (
    ARMY,
    CURATED,
    RULES,
    audit_scenario_object_boundary,
    audit_source_files,
    main,
)
from tools.audit_terrain_scenery_source_gaps import audit_source_files as audit_terrain
from tools.audit_terrain_scenery_source_gaps import main as terrain_main


def _inputs() -> tuple[dict, dict]:
    publication = RulesDatabase(RULES).deployed_objects_payload(ARMY)
    assert publication is not None
    return (
        load_curated_document(CURATED),
        publication,
    )


def test_core_scenario_object_census_is_separate_from_deployables() -> None:
    report = audit_source_files()
    assert report["scope"] == "core-scenario-objects-not-weapon-equipment-deployables"
    assert report["coreScenarioCount"] == 4
    assert report["reviewedDeployedObjectCount"] == 17
    assert len(report["curatedSourceSha256"]) == 64
    assert report["armyDatabaseSha256"] == hashlib.sha256(ARMY.read_bytes()).hexdigest()
    assert report["rulesDatabaseSha256"] == hashlib.sha256(RULES.read_bytes()).hexdigest()
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


@pytest.mark.parametrize("audit,cli", (
    (audit_source_files, main), (audit_terrain, terrain_main),
), ids=("core-scenarios", "terrain-scenery"))
def test_boundary_audits_use_explicit_databases_without_json(
    audit: Callable[..., dict], cli: Callable[[], int], tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    army = tmp_path / "army" / "selected.sqlite"
    rules = tmp_path / "rules" / "selected.sqlite"
    army.parent.mkdir()
    rules.parent.mkdir()
    shutil.copyfile(ARMY, army)
    shutil.copyfile(RULES, rules)
    # These are neither inputs nor a recovery path, even when present.
    for directory in (army.parent, rules.parent):
        (directory / "deployed-objects.json").write_text("invalid JSON", encoding="utf-8")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    report = audit(army_database=army, rules_database=rules)
    assert report["armyDatabaseSha256"] == hashlib.sha256(before[army]).hexdigest()
    assert report["rulesDatabaseSha256"] == hashlib.sha256(before[rules]).hexdigest()
    monkeypatch.setattr(sys, "argv", [
        cli.__module__, "--army-database", str(army), "--rules-database", str(rules), "--json",
    ])
    assert cli() == 0
    assert json.loads(capsys.readouterr().out) == report
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("audit", (audit_source_files, audit_terrain),
                         ids=("core-scenarios", "terrain-scenery"))
@pytest.mark.parametrize("case,error,match", (
    ("missing-army", FileNotFoundError, None),
    ("missing-rules", ValueError, "Rules database does not exist"),
    ("legacy", ValueError, "requires embedded deployed objects"),
    ("mismatched-army", ValueError, "do not match the Army database"),
    ("missing-model", ValueError, "Incomplete normalized deployed-object schema"),
    ("corrupt-rules", sqlite3.DatabaseError, "not a database"),
))
def test_boundary_audits_reject_missing_or_mismatched_embedded_models(
    audit: Callable[..., dict], case: str, error: type[Exception], match: str | None,
    tmp_path: Path,
) -> None:
    army, rules = tmp_path / "army.db", tmp_path / "rules_n5.db"
    shutil.copyfile(ARMY, army)
    shutil.copyfile(RULES, rules)
    if case == "missing-army":
        army.unlink()
    elif case == "missing-rules":
        rules.unlink()
    elif case == "legacy":
        export_rules_database(load_curated_directory(CURATED.parent), rules)
    elif case == "missing-model":
        with sqlite3.connect(rules) as connection:
            connection.execute("DROP TABLE deployed_objects")
    elif case == "corrupt-rules":
        rules.write_bytes(b"not a SQLite database")
    else:
        with army.open("ab") as stream:
            stream.write(b"mismatched-generation")
    (tmp_path / "deployed-objects.json").write_text("{}", encoding="utf-8")
    before = {path: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(error, match=match):
        audit(army_database=army, rules_database=rules)
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == before
