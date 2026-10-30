"""Audit core-scenario physical objectives against deployed-object publication.

This read-only source-domain boundary intentionally does not construct
Weapon/Equipment object profiles, delivery paths or Unit ownership.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_document
from infinity_db.scenario_components import ScenarioComponents
from infinity_db.scenario_definition import parse_scenario_definition_record
from infinity_db.scenario_geometry import MarkerElement
from infinity_db.scenario_mission import ElementStatusComparison, ElementStatusCount

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
PUBLICATION = ROOT / "data/generated/deployed-objects.json"
SOURCE = "n5-core-v5.3-pdf"

# Printed English N5.3 pp. 149-155; these are scenario-placed elements,
# not entries in the Army Weapon/Equipment deployable profiles table.
EXPECTED = {
    "scenario:annihilation": (None, 0, None, (), (), (149, 150)),
    "scenario:domination": (
        "console", 4, "rule:scenario:consoles",
        ("skill:hack-consoles",), ("hacked",), (151, 152),
    ),
    "scenario:supplies": (
        "supply-box", 3, "rule:scenario:supply-boxes",
        ("skill:pick-up-supply-boxes",), ("controlled",), (153, 154),
    ),
    "scenario:firefight": (None, 0, None, (), (), (155, 156)),
}
OBJECT_NAMES = {"console", "supply box"}


def audit_scenario_object_boundary(
    curated: dict[str, Any], publication: dict[str, Any],
) -> dict[str, Any]:
    """Pin source, map instances, objective status and domain separation."""
    records = {r["id"]: r for r in curated["records"]}
    if len(records) != len(curated["records"]):
        raise ValueError("Duplicate maintained record ID")
    if {r["id"] for r in curated["records"] if r["kind"] == "scenario"} != set(EXPECTED):
        raise ValueError("Core scenario inventory drift")
    objects = publication.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("Missing reviewed deployed-object publication")
    if any(
        isinstance(obj.get("name"), str)
        and obj["name"].strip().casefold() in OBJECT_NAMES
        for obj in objects
    ):
        raise ValueError("Scenario objective unexpectedly published as Weapon/Equipment")
    if len({obj["id"] for obj in objects}) != len(objects):
        raise ValueError("Duplicate reviewed deployed-object identity")
    composer = ScenarioComponents(curated)
    scenarios: list[dict[str, Any]] = []
    for scenario_id, (
        marker_type, count, rule_id, skills, statuses, expected_pages,
    ) in EXPECTED.items():
        source_record = records[scenario_id]
        if (
            source_record.get("composition", {}).get("role") != "definition"
            or source_record.get("kind") != "scenario"
        ):
            raise ValueError(f"Missing scenario definition: {scenario_id}")
        cited_pages = {
            citation["page"] for citation in source_record["citations"]
            if citation["sourceId"] == SOURCE
        }
        if cited_pages != set(expected_pages):
            raise ValueError(f"Scenario PDF provenance drift: {scenario_id}")
        scenario = parse_scenario_definition_record(composer.compose(source_record))
        if scenario.mission is None:
            raise ValueError(f"Missing scenario mission: {scenario_id}")
        if tuple(scenario.mission.skill_ids) != skills:
            raise ValueError(f"Unexpected scenario objective skills: {scenario_id}")
        if rule_id is not None:
            rule = records.get(rule_id)
            if (
                rule is None
                or rule.get("scope", {}).get("scenarios") != [scenario_id]
                or not any(
                    cite["sourceId"] == SOURCE and cite.get("page") == expected_pages[0]
                    for cite in rule.get("citations", [])
                )
                or rule_id not in {
                    mission_rule.definition_id for mission_rule in scenario.mission.rules
                }
            ):
                raise ValueError(f"Scenario objective rule provenance drift: {scenario_id}")
            for skill_id in skills:
                skill = records.get(skill_id)
                if (
                    skill is None
                    or skill.get("scope", {}).get("scenarios") != [scenario_id]
                    or not any(
                        cite["sourceId"] == SOURCE and cite.get("page") == expected_pages[0]
                        for cite in skill.get("citations", [])
                    )
                ):
                    raise ValueError(f"Scenario interaction provenance drift: {skill_id}")
        scoring = tuple(sorted({
            condition.status
            for objective in scenario.mission.objectives
            for award in objective.awards
            for condition in (award.condition,)
            if isinstance(condition, (ElementStatusCount, ElementStatusComparison))
        }))
        if scoring != statuses:
            raise ValueError(f"Scenario objective scoring mismatch: {scenario_id}")
        configurations = []
        first_ids: tuple[str, ...] | None = None
        for configuration in scenario.configurations:
            markers = [
                element for element in configuration.geometry.elements
                if isinstance(element, MarkerElement)
            ]
            if len(markers) != count or {
                m.marker_type for m in markers
            } != ({marker_type} if marker_type else set()):
                raise ValueError(
                    f"Scenario physical element count/type drift: {scenario_id}"
                )
            marker_ids = tuple(sorted(marker.id for marker in markers))
            if first_ids is not None and marker_ids != first_ids:
                raise ValueError(
                    f"Scenario objective identity changes by game size: {scenario_id}"
                )
            first_ids = marker_ids
            configurations.append({
                "id": configuration.id,
                "armyPoints": list(configuration.army_points),
                "markerIds": list(marker_ids),
            })
        if marker_type and count != len(first_ids or ()):
            raise ValueError(f"Missing physical scenario elements: {scenario_id}")
        status_conditions = [
            condition
            for objective in scenario.mission.objectives
            for award in objective.awards
            for condition in (award.condition,)
            if isinstance(condition, (ElementStatusCount, ElementStatusComparison))
        ]
        for condition in status_conditions:
            if tuple(sorted(condition.element_ids)) != (first_ids or ()):
                raise ValueError(
                    f"Scenario objective status references do not match "
                    f"physical markers: {scenario_id}"
                )
        scenarios.append({
            "scenarioId": scenario_id,
            "sourcePages": list(expected_pages),
            "objectDomain": "scenario-object" if marker_type else "none",
            "markerType": marker_type,
            "physicalObjectCount": count,
            "ruleId": rule_id,
            "interactionSkills": list(skills),
            "scoringStatuses": list(statuses),
            "configurations": configurations,
        })
    return {
        "scope": "core-scenario-objects-not-weapon-equipment-deployables",
        "coreScenarioCount": len(scenarios),
        "scenarioObjectTypes": sorted(OBJECT_NAMES),
        "reviewedDeployedObjectCount": len(objects),
        "scenarios": scenarios,
    }


def audit_source_files(curated_path: Path, publication_path: Path) -> dict[str, Any]:
    source_bytes = curated_path.read_bytes()
    publication_bytes = publication_path.read_bytes()
    return {
        **audit_scenario_object_boundary(
            load_curated_document(curated_path),
            json.loads(publication_bytes),
        ),
        "curatedSourceSha256": hashlib.sha256(source_bytes).hexdigest(),
        "deployedPublicationSha256": hashlib.sha256(publication_bytes).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curated", type=Path, default=CURATED)
    parser.add_argument("--publication", type=Path, default=PUBLICATION)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_source_files(args.curated, args.publication)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Core scenarios: {report['coreScenarioCount']}")
        for row in report["scenarios"]:
            print(
                f"  {row['scenarioId']}: {row['physicalObjectCount']} "
                f"{row['markerType'] or 'no scenario markers'}"
            )
        print(
            "Unchanged reviewed Weapon/Equipment objects: "
            f"{report['reviewedDeployedObjectCount']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
