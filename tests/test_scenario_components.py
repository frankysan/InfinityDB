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


def test_annihilation_review_preserves_all_source_scoring_and_end_conditions(
    document: dict,
) -> None:
    """N5.3 pp. 149-150: scoring, Killing, setup and mission end conditions."""
    from infinity_db.scenario_mission import NumericRangeCondition, ProseCondition

    raw = scenario(document, "annihilation")
    mission = parse_scenario_definition_record(ScenarioComponents(document).compose(raw)).mission
    assert mission is not None
    assert [size.army_points for size in mission.game_sizes] == [150, 200, 250, 300, 350, 400]
    assert [size.swc for size in mission.game_sizes] == [3, 4, 5, 6, 7, 8]
    assert all(size.minimum_victory_points is None for size in mission.game_sizes)
    assert [objective.id for objective in mission.objectives] == [
        "destroy-forces", "preserve-forces", "eliminate-command",
    ]
    expected = {
        150: ((40, 75), (76, 125), (126, None)),
        200: ((50, 100), (101, 150), (151, None)),
        250: ((65, 125), (126, 200), (201, None)),
        300: ((75, 150), (151, 250), (251, None)),
        350: ((85, 175), (176, 270), (271, None)),
        400: ((100, 200), (201, 300), (301, None)),
    }
    for index, metric in enumerate(("enemy-army-points-killed", "surviving-victory-points")):
        objective = mission.objectives[index]
        assert (objective.timing, objective.aggregation, objective.maximum_points) == (
            "end-of-game", "exclusive", 4,
        )
        for size, bounds in expected.items():
            awards = [award for award in objective.awards if size in award.army_points]
            assert [award.objective_points for award in awards] == [1, 3, 4]
            for award, (low, high) in zip(awards, bounds, strict=True):
                condition = award.condition
                assert isinstance(condition, NumericRangeCondition)
                assert (condition.metric, condition.minimum, condition.maximum) == (
                    metric, low, high,
                )

    commander = mission.objectives[2]
    assert commander.maximum_points == 2
    assert commander.timing == "end-of-game"
    assert len(commander.awards) == 1
    assert commander.awards[0].army_points == tuple(expected)
    assert commander.awards[0].objective_points == 2
    assert isinstance(commander.awards[0].condition, ProseCondition)
    assert "[[skill:lieutenant]]" in commander.awards[0].condition.text

    assert len(mission.rules) == 1
    assert mission.rules[0].definition_id == "rule:scenario:killing"
    killing = " ".join(mission.rules[0].paragraphs)
    assert "entering [[state:dead]]" in killing
    assert "Null when the game ends" in killing
    assert "never deployed" in killing or "never" in killing.lower()
    assert [(end.id, end.check_at, end.finish_at) for end in mission.end_conditions] == [
        ("round-limit", "end-of-round", "end-of-round"),
        ("all-troopers-null", "tactical-phase", "end-of-player-turn"),
    ]
    assert mission.end_conditions[0].rounds == 3
    assert "all Troopers" in (mission.end_conditions[1].description or "")
    assert mission.source_issues[0].id == "350-point-survival-bands"
    assert mission.source_issues[0].status == "reviewed-resolution"
    assert "Spanish N5.3 Aniquilación" in mission.source_issues[0].description
    assert "explicitly prints contiguous" in mission.source_issues[0].description
    assert {c["page"] for c in raw["citations"]} == {149, 150}


def test_domination_review_preserves_scoring_and_specialist_boundaries(
    document: dict,
) -> None:
    """N5.3 pp. 151-152: Quadrants, Consoles, Specialists and termination."""
    from infinity_db.scenario_mission import DominatedRegionComparison, ElementStatusCount

    source = scenario(document, "domination")
    mission = parse_scenario_definition_record(
        ScenarioComponents(document).compose(source)
    ).mission
    assert mission is not None
    assert [size.army_points for size in mission.game_sizes] == [
        150, 200, 250, 300, 350, 400,
    ]
    assert [size.swc for size in mission.game_sizes] == [3, 4, 5, 6, 6, 8]
    assert [size.minimum_victory_points for size in mission.game_sizes] == [
        38, 50, 63, 75, 88, 100,
    ]
    assert {c["page"] for c in source["citations"]} == {151, 152}
    assert len(mission.source_issues) == 1
    issue = mission.source_issues[0]
    assert (issue.id, issue.army_points, issue.game_size_field, issue.status) == (
        "350-point-swc", (350,), "swc", "needs-verification",
    )
    assert "Wiki Domination revision 3264" in issue.description
    assert "Spanish N5.3 Domination chart" in issue.description
    assert "official language editions" in issue.description
    assert "intended authoritative value remains unverified" in issue.description

    quadrants, consoles = mission.objectives
    assert (quadrants.timing, quadrants.aggregation, quadrants.maximum_points) == (
        "end-of-round", "exclusive", 6,
    )
    assert quadrants.maximum_points_per_round == 2
    assert [award.objective_points for award in quadrants.awards] == [1, 2]
    equal, greater = (award.condition for award in quadrants.awards)
    assert isinstance(equal, DominatedRegionComparison)
    assert isinstance(greater, DominatedRegionComparison)
    assert equal.element_ids == greater.element_ids == (
        "quadrant-1", "quadrant-2", "quadrant-3", "quadrant-4",
    )
    assert (equal.comparison, equal.minimum) == ("equal", 1)
    assert (greater.comparison, greater.minimum) == ("greater", None)
    assert (consoles.timing, consoles.aggregation, consoles.maximum_points) == (
        "end-of-game", "cumulative", 4,
    )
    assert len(consoles.awards) == 1 and consoles.awards[0].objective_points == 1
    hacked = consoles.awards[0].condition
    assert isinstance(hacked, ElementStatusCount)
    assert hacked.element_ids == ("console-q1", "console-q2", "console-q3", "console-q4")
    assert hacked.status == "hacked"

    domination, console_rule, specialists = mission.rules
    assert [rule.definition_id for rule in mission.rules] == [
        "rule:scenario:dominate-quadrants",
        "rule:scenario:consoles",
        "rule:specialist-troops:standard",
    ]
    quadrant_text = " ".join(domination.paragraphs)
    for phrase in ("end of each Game Round", "more Victory Points",
                   "more than half of its base", "classified as Null",
                   "anything other than a Trooper", "Shasvastii-Embryo"):
        assert phrase in quadrant_text
    assert "[[skill:shasvastii]]" in quadrant_text
    assert "[[state:normal|Normal]]" in quadrant_text
    assert "center of each of the four" in " ".join(console_rule.paragraphs)
    assert console_rule.skill_ids == ("skill:hack-consoles",)
    assert mission.skill_ids == ("skill:hack-consoles",)
    assert set(specialists.specialist_skill_ids) == {
        "skill:doctor", "skill:engineer", "skill:forward-observer",
        "skill:hacker", "skill:paramedic", "skill:specialist-operative",
        "skill:chain-of-command",
    }
    specialist_text = " ".join(specialists.paragraphs)
    assert "[[skill:peripheral:plural]]" in specialist_text
    assert "Non Specialist variant" in specialist_text
    assert [(
        end.id, end.check_at, end.finish_at, end.uses_minimum_victory_points
    ) for end in mission.end_conditions] == [
        ("round-limit", "end-of-round", "end-of-round", False),
        ("minimum-victory-points", "tactical-phase", "end-of-player-turn", True),
    ]
    assert mission.end_conditions[0].rounds == 3
    assert "not classified as Null" in (mission.end_conditions[1].description or "")

    skill = next(record for record in document["records"]
                 if record["id"] == "skill:hack-consoles")
    assert skill["scope"]["scenarios"] == ["scenario:domination"]
    assert "Silhouette contact" in " ".join(skill["facts"]["requirements"])
    skill_effects = " ".join(skill["facts"]["effects"])
    for phrase in ("failed attempt may be repeated", "Only the most recent player",
                   "+3 MOD", "[[attribute:wip]]"):
        assert phrase in skill_effects


def test_firefight_review_scoring_and_mission_only_overlays(document: dict) -> None:
    """N5.3 pp. 155-156: comparative objectives and scenario-local exceptions."""
    from infinity_db.scenario_mission import MetricComparison

    source = scenario(document, "firefight")
    mission = parse_scenario_definition_record(
        ScenarioComponents(document).compose(source)
    ).mission
    assert mission is not None
    assert [size.army_points for size in mission.game_sizes] == [
        150, 200, 250, 300, 350, 400,
    ]
    assert [size.swc for size in mission.game_sizes] == [3, 4, 5, 6, 7, 8]
    assert all(size.minimum_victory_points is None for size in mission.game_sizes)
    assert [obj.id for obj in mission.objectives] == [
        "surviving-specialists", "killed-specialists",
        "killed-lieutenants", "killed-army-points",
    ]
    assert [obj.maximum_points for obj in mission.objectives] == [2, 1, 3, 4]
    assert [obj.awards[0].objective_points for obj in mission.objectives] == [
        2, 1, 3, 4,
    ]
    assert all(
        obj.timing == "end-of-game" and obj.aggregation == "exclusive"
        and len(obj.awards) == 1
        and obj.awards[0].army_points == (150, 200, 250, 300, 350, 400)
        for obj in mission.objectives
    )
    for objective, metric in zip(mission.objectives, (
        "surviving-specialist-troops",
        "enemy-specialist-troops-killed",
        "enemy-lieutenants-killed",
        "enemy-army-points-killed",
    ), strict=True):
        condition = objective.awards[0].condition
        assert isinstance(condition, MetricComparison)
        assert (condition.metric, condition.comparison) == (metric, "greater")
    assert "[[skill:lieutenant:plural]]" in mission.objectives[2].name
    assert not mission.source_issues

    killing, tactical_link, landing, specialists = mission.rules
    assert [rule.definition_id for rule in mission.rules] == [
        "rule:scenario:killing",
        "rule:scenario:reinforced-tactical-link",
        "rule:scenario:designated-landing-area",
        "rule:specialist-troops:standard",
    ]
    killing_text = " ".join(killing.paragraphs)
    for phrase in ("entering [[state:dead]]", "Null when the game ends",
                   "never deployed"):
        assert phrase in killing_text
    link_text = " ".join(tactical_link.paragraphs)
    for phrase in ("always Open Information", "Marker", "first Game Round",
                   "start of the Tactical Phase", "without spending an Order",
                   "on the table"):
        assert phrase in link_text
    assert "[[skill:lieutenant]]" in link_text
    landing_text = " ".join(landing.paragraphs)
    for phrase in ("whole game table", "[[skill:combat-jump]]",
                   "+3 MOD", "[[attribute:ph]]", "cumulative",
                   "Airborne Deployment (AD)", "enemy Deployment Zone"):
        assert phrase in landing_text
    assert set(specialists.specialist_skill_ids) == {
        "skill:doctor", "skill:engineer", "skill:forward-observer",
        "skill:hacker", "skill:paramedic", "skill:specialist-operative",
        "skill:chain-of-command",
    }
    specialist_text = " ".join(specialists.paragraphs)
    assert "[[skill:peripheral:plural]]" in specialist_text
    assert "Non Specialist variant" in specialist_text
    assert [(end.id, end.check_at, end.finish_at) for end in mission.end_conditions] == [
        ("round-limit", "end-of-round", "end-of-round"),
        ("all-troopers-null", "tactical-phase", "end-of-player-turn"),
    ]
    assert mission.end_conditions[0].rounds == 3
    assert not mission.end_conditions[1].uses_minimum_victory_points
    assert {citation["page"] for citation in source["citations"]} == {155, 156}

    for rule_id in (
        "rule:scenario:reinforced-tactical-link",
        "rule:scenario:designated-landing-area",
    ):
        definition = next(rec for rec in document["records"] if rec["id"] == rule_id)
        assert definition["scope"]["scenarios"] == ["scenario:firefight"]


def test_supplies_review_retains_scoped_pickup_control_and_ending(
    document: dict,
) -> None:
    """N5.3 pp. 153-154: compose Supply Box interactions without globalizing them."""
    from infinity_db.scenario_mission import ElementStatusComparison, ElementStatusCount

    record = scenario(document, "supplies")
    mission = parse_scenario_definition_record(
        ScenarioComponents(document).compose(record)
    ).mission
    assert mission is not None
    assert [size.army_points for size in mission.game_sizes] == [
        150, 200, 250, 300, 350, 400,
    ]
    assert [size.swc for size in mission.game_sizes] == [3, 4, 5, 6, 7, 8]
    assert [size.minimum_victory_points for size in mission.game_sizes] == [
        38, 50, 63, 75, 88, 100,
    ]
    assert not mission.source_issues
    assert {c["page"] for c in record["citations"]} == {153, 154}
    assert [obj.maximum_points for obj in mission.objectives] == [6, 2, 2]
    assert [obj.aggregation for obj in mission.objectives] == [
        "cumulative", "exclusive", "exclusive",
    ]
    assert all(obj.timing == "end-of-game" for obj in mission.objectives)
    boxes = ("supply-box-left", "supply-box-center", "supply-box-right")
    assert [obj.awards[0].condition for obj in mission.objectives] == [
        ElementStatusCount(boxes, "controlled"),
        ElementStatusComparison(boxes, "controlled", "greater"),
        ElementStatusComparison(boxes, "controlled", "all"),
    ]
    assert [obj.awards[0].objective_points for obj in mission.objectives] == [
        2, 2, 2,
    ]

    assert [rule.definition_id for rule in mission.rules] == [
        "rule:scenario:supply-boxes",
        "rule:scenario:carrying-supply-boxes",
        "rule:scenario:controlling-supply-boxes",
        "rule:specialist-troops:standard",
    ]
    placement, carrying, control, specialist = (
        " ".join(rule.paragraphs) for rule in mission.rules
    )
    assert "Deployment in Silhouette contact" in placement
    assert "at most one Supply Box" in carrying
    assert "Markers cannot carry" in carrying
    assert "carrier becomes classified as Null" in carrying
    assert "at game end" in control.lower()
    assert "Marker cannot control" in control
    assert "not be classified as Null" in control
    assert "any enemy Model" in control
    assert "[[skill:peripheral:plural]]" in specialist
    assert len(mission.rules[-1].specialist_skill_ids) == 7
    assert mission.skill_ids == ("skill:pick-up-supply-boxes",)
    pickup = next(r for r in document["records"] if r["id"] == mission.skill_ids[0])
    assert pickup["scope"]["scenarios"] == ["scenario:supplies"]
    assert pickup["facts"]["typeIds"] == ["short-skill"]
    assert pickup["labelIds"] == ["attack"]
    pickup_text = " ".join(
        pickup["facts"]["requirements"] + pickup["facts"]["effects"]
    )
    for phrase in (
        "not being carried by a Model",
        "any Model classified as Null",
        "an allied Model in [[state:normal|Normal]]",
        "without making a Roll",
    ):
        assert phrase in pickup_text

    assert [(
        ending.id, ending.check_at, ending.finish_at,
        ending.uses_minimum_victory_points,
    ) for ending in mission.end_conditions] == [
        ("round-limit", "end-of-round", "end-of-round", False),
        ("minimum-victory-points", "tactical-phase", "end-of-player-turn", True),
    ]
    assert mission.end_conditions[0].rounds == 3
    assert "not classified as Null" in (
        mission.end_conditions[1].description or ""
    )


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
