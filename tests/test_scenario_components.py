from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.scenario_components import ScenarioComponents
from infinity_db.scenario_definition import (
    parse_scenario_definition_record,
)

CORE = Path("data/curated/rules/n5-core-v5.3.json")


@pytest.fixture
def document() -> dict:
    return load_curated_document(CORE)


def scenario(document: dict, identifier: str) -> dict:
    return next(r for r in document["records"] if r["id"] == "scenario:" + identifier)


def test_shared_sources_replace_repeated_authoring_and_keep_overrides_explicit(
    document: dict,
) -> None:
    rules = [r for r in document["records"] if r["kind"] == "rule"]
    assert len([r for r in rules if r["id"] == "rule:scenario:killing"]) == 1
    assert len([r for r in rules if r["id"] == "rule:specialist-troops:standard"]) == 1
    baseline = next(r for r in rules if r["id"] == "rule:specialist-troops:standard")
    assert len(baseline["facts"]["specialists"]["anyOfSkills"]) == 7
    assert all(
        isinstance(x, str) and x.startswith("skill:")
        for x in baseline["facts"]["specialists"]["anyOfSkills"]
    )
    for name in ("domination", "supplies", "firefight"):
        inclusion = scenario(document, name)["facts"]["mission"]["rules"][-1]
        assert inclusion["ref"] == baseline["id"]
        assert inclusion["addSkills"] == inclusion["removeSkills"] == []
    assert scenario(document, "domination")["facts"]["mission"]["setup"]["gameSizeOverrides"] == [
        {"armyPoints": 350, "swc": 6}
    ]
    before = deepcopy(document)
    composed = ScenarioComponents(document)
    dom = parse_scenario_definition_record(composed.compose(scenario(document, "domination")))
    sup = parse_scenario_definition_record(composed.compose(scenario(document, "supplies")))
    assert dom.mission and sup.mission
    assert dom.mission.game_sizes[4].swc == 6 and sup.mission.game_sizes[4].swc == 7
    assert document == before


def test_specialist_inclusions_resolve_differences_without_changing_baseline(
    document: dict,
) -> None:
    inclusion = scenario(document, "domination")["facts"]["mission"]["rules"][-1]
    inclusion["addSkills"] = ["skill:combat-jump"]
    inclusion["removeSkills"] = ["skill:engineer"]
    registry = ScenarioComponents(document)
    changed = parse_scenario_definition_record(registry.compose(scenario(document, "domination")))
    normal = parse_scenario_definition_record(registry.compose(scenario(document, "supplies")))
    assert changed.mission and normal.mission
    assert "skill:combat-jump" in changed.mission.rules[-1].specialist_skill_ids
    assert "skill:engineer" not in changed.mission.rules[-1].specialist_skill_ids
    assert "skill:engineer" in normal.mission.rules[-1].specialist_skill_ids
    assert "skill:combat-jump" not in normal.mission.rules[-1].specialist_skill_ids
    assert "Other qualifying Skills still apply" in " ".join(changed.mission.rules[-1].paragraphs)


@pytest.mark.parametrize(
    "operation,value",
    [
        ("addSkills", "skill:doctor"),
        ("addSkills", "skill:missing"),
        ("removeSkills", "skill:combat-jump"),
        ("removeSkills", "skill:missing"),
    ],
)
def test_invalid_specialist_differences_fail(document: dict, operation: str, value: str) -> None:
    inclusion = scenario(document, "domination")["facts"]["mission"]["rules"][-1]
    inclusion[operation] = [value]
    with pytest.raises(ValueError):
        ScenarioComponents(document).compose(scenario(document, "domination"))


def test_named_definitions_are_not_deduplicated_by_display_name(document: dict) -> None:
    original = next(r for r in document["records"] if r["id"] == "rule:scenario:consoles")
    alternate = deepcopy(original)
    alternate["id"] = "rule:scenario:consoles-alternate"
    alternate["facts"]["effects"] = ["A different Console procedure."]
    alternate["facts"]["definesSkills"] = []
    document["records"].append(alternate)
    raw = scenario(document, "domination")
    raw["facts"]["mission"]["rules"].append({"id": "alternate", "ref": alternate["id"]})
    resolved = parse_scenario_definition_record(ScenarioComponents(document).compose(raw))
    assert resolved.mission
    first = next(r for r in resolved.mission.rules if r.id == "consoles")
    second = resolved.mission.rules[-1]
    assert first.name == second.name and first.definition_id != second.definition_id
    assert first.paragraphs != second.paragraphs


def test_component_cycles_unknown_references_and_wrong_kinds_fail(document: dict) -> None:
    standard = next(
        d
        for d in document["scenarioComponents"]["definitions"]
        if d["id"] == "setup:standard-opposed"
    )
    standard["payload"] = {"ref": standard["id"]}
    with pytest.raises(ValueError, match="Cyclic"):
        ScenarioComponents(document)
    standard["payload"] = {"ref": "setup:unknown"}
    with pytest.raises(ValueError, match="Unknown"):
        ScenarioComponents(document)
    standard["payload"] = {"ref": "end-condition:round-limit"}
    with pytest.raises(ValueError):
        ScenarioComponents(document)


def test_scope_is_explicit_and_skill_definitions_are_separate(
    document: dict, tmp_path: Path
) -> None:
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(Path("data/curated")), output, finalize=False)
    database = RulesDatabase(output)
    database.validate()
    assert database.composed_record("skill:hack-consoles") is None
    assert database.composed_record("rule:specialist-troops:standard") is None
    assert database.composed_record("skill:hack-consoles", scenario_id="supplies") is None
    view = database.scenario_reference("domination")
    assert view and len(view["skills"]) == 1
    skill = view["skills"][0]
    assert skill["kind"] == "skill" and skill["id"] == "skill:hack-consoles"
    assert skill["skill_types"][0]["id"] == "short-skill"
    assert skill["labels"][0]["id"] == "attack"
    assert skill["facts"]["requirements"] and skill["facts"]["effects"]
    assert skill["applicable_scenarios"] == [{"id": "scenario:domination", "name": "Domination"}]
    assert all(r["id"] != skill["id"] for r in view["rules"])
    assert all(not r["scope"].get("scenarios") for r in database.composed_records_by_kind("rule"))
    assert database.scenario_reference("missing") is None
    firefight = database.scenario_reference("firefight")
    assert firefight is not None and firefight["skills"] == []
    record = view["scenario"]
    sources = record["facts"]["componentSources"]
    assert {s["id"] for s in sources} >= {
        "setup:standard-opposed",
        "setup:minimum-vp",
        "end-condition:round-limit",
    }
    assert all(s["citations"] for s in sources)


def test_scope_mismatch_does_not_fall_back_to_another_definition(document: dict) -> None:
    raw = scenario(document, "supplies")
    raw["facts"]["mission"]["rules"].append({"id": "wrong", "ref": "rule:scenario:consoles"})
    with pytest.raises(ValueError, match="not applicable"):
        ScenarioComponents(document).compose(raw)


def test_unused_invalid_component_payload_is_rejected(document: dict) -> None:
    entry = deepcopy(document["scenarioComponents"]["definitions"][-1])
    entry["id"] = "end-condition:unused-invalid"
    entry["kind"] = "end-condition"
    entry["payload"] = {
        "id": "bad",
        "checkAt": "immediate",
        "finishAt": "immediate",
        "condition": {"kind": "unsupported"},
    }
    document["scenarioComponents"]["definitions"].append(entry)
    with pytest.raises(ValueError, match="Unsupported ending"):
        ScenarioComponents(document)


def test_scoped_skills_and_specialist_arrays_use_the_existing_detail_renderer(
    tmp_path: Path,
) -> None:
    import importlib.util
    import json
    import shutil
    import subprocess
    import sys

    from infinity_db.database import Database
    from infinity_db.maintained_text_references import enrich_maintained_text_references

    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(Path("data/curated")), output, finalize=False)
    rules = RulesDatabase(output)
    army = Database(Path("data/generated/infinity.db"))
    dom = rules.scenario_reference("domination")
    sup = rules.scenario_reference("supplies")
    assert dom and sup
    specialist = dom["rules"][-1]
    payload = {"skills": dom["skills"] + sup["skills"], "specialist": specialist}
    payload = enrich_maintained_text_references(army, rules, payload, scenario_id="domination")
    document = tmp_path / "render.json"
    document.write_text(json.dumps(payload), encoding="utf-8")
    node = shutil.which("node")
    if node:
        command = [node]
    else:
        assert importlib.util.find_spec("nodejs_wheel"), "Node.js dev dependency is required"
        command = [sys.executable, "-m", "nodejs_wheel"]
    result = subprocess.run(
        [
            *command,
            "tests/scenario_renderer_harness.cjs",
            "src/infinity_db/web/static/rules-reference.js",
            str(document),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = json.loads(result.stdout)
    assert "Hack Consoles" in rendered["skills"][0]
    assert "Short Skills" in rendered["skills"][0] and "Attack" in rendered["skills"][0]
    assert "Requirements" in rendered["skills"][0] and "Effects" in rendered["skills"][0]
    assert "Domination" in rendered["skills"][0]
    assert "Pick Up Supply Boxes" in rendered["skills"][1] and "Supplies" in rendered["skills"][1]
    assert "Restrictions" in rendered["skills"][1]
    assert "Domination" not in rendered["embeddedSkills"][0]
    assert "Supplies" not in rendered["embeddedSkills"][1]
    assert "Qualifying Skills" in rendered["specialist"]
    assert rendered["specialist"].index("Qualifying Skills") < rendered["specialist"].index(
        "Restrictions"
    )
    assert "Domination" not in rendered["embeddedSpecialist"]
    assert "Supplies" not in rendered["embeddedSpecialist"]
    assert "Firefight" not in rendered["embeddedSpecialist"]
    assert "Doctor" in rendered["specialist"] and "Chain of Command" in rendered["specialist"]
    assert "Non Specialist" in rendered["specialist"]
    assert "[[" not in rendered["specialist"] and "[[" not in "".join(rendered["skills"])
