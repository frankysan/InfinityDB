"""ITS 17 Critical Intervention historical source pins and isolated SQLite."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    build_its_database,
    inspect_its_database,
    select_its_scenario,
)

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
SIZES = [150, 200, 250, 300, 350, 400]


def records() -> tuple[dict, dict]:
    history = load_curated_document(SEASON, shared_scenario_library=SHARED)
    modern = load_curated_document(ITS18)
    return (
        next(r for r in history["records"] if r["id"] == "scenario:critical-intervention"),
        next(r for r in modern["records"] if r["id"] == "scenario:critical-intervention"),
    )


def test_its17_critical_intervention_has_own_bilingual_publication() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert len(library["definitions"]) == 16
    definition = library["definitions"][13]
    assert definition["id"] == "scenario:critical-intervention"
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = season["scenarioCollection"]["members"][13]
    assert member["scenarioId"] == "scenario:critical-intervention"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(c["sourceId"], c["page"]) for c in binding["citations"]] == [
        *((EN, page) for page in range(45, 51)),
        *((ES, page) for page in range(63, 70)),
    ]


def test_its17_critical_intervention_scores_skills_and_geometry() -> None:
    old, current = records()
    history, now = old["facts"], current["facts"]
    assert old["scope"]["seasons"] == ["its-17"]
    assert old["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert history["playRequirements"] == {
        "classifiedObjectives": 1, "tacticalObjectives": 0, "hvts": 1,
    }
    assert history["mission"]["objectives"] == now["mission"]["objectives"]
    assert history["mission"]["endConditions"] == now["mission"]["endConditions"]
    assert history["mission"]["gameSizes"] == now["mission"]["gameSizes"]
    assert history["configurations"] == now["configurations"]
    objectives = history["mission"]["objectives"]
    assert [o["id"] for o in objectives] == [
        "attacker-unlock-console", "attacker-extract-pack",
        "attacker-extractor-not-killed", "attacker-extractor-home",
        "attacker-dominate-room", "attacker-kill-threshold",
        "defender-prevent-unlock", "defender-prevent-extract",
        "defender-kill-extractor", "defender-dominate-room",
        "defender-kill-threshold", "classified-objective",
    ]
    assert [o["maximumPoints"] for o in objectives] == [
        1, 2, 1, 2, 2, 1, 1, 3, 2, 3, 2, 1,
    ]
    attacker_threshold = objectives[5]["awards"]
    defender_threshold = objectives[10]["awards"]
    assert [a["objectivePoints"] for a in attacker_threshold] == [1] * 6
    assert [a["objectivePoints"] for a in defender_threshold] == [2] * 6
    assert [a["armyPoints"] for a in attacker_threshold] == [
        [n] for n in SIZES
    ]
    assert [a["armyPoints"] for a in defender_threshold] == [
        [n] for n in SIZES
    ]
    for award, threshold in zip(
        attacker_threshold, (40, 50, 65, 75, 85, 100), strict=True,
    ):
        assert f"at least {threshold} enemy Army Points" in (
            award["condition"]["text"]
        )
    for award, threshold in zip(
        defender_threshold, (75, 100, 125, 150, 175, 200), strict=True,
    ):
        assert f"at least {threshold} enemy Army Points" in (
            award["condition"]["text"]
        )
    for conf, width, height, depth in zip(
        history["configurations"], (24, 32, 48), (32, 48, 48),
        (8, 12, 12), strict=True,
    ):
        g = conf["geometry"]
        items = {i["id"]: i for i in g["elements"]}
        assert (g["table"]["width"], g["table"]["height"]) == (width, height)
        assert items["server-room"]["x2"] - items["server-room"]["x1"] == 8
        assert items["server-room"]["y2"] - items["server-room"]["y1"] == 8
        assert items["attacker-exclusion-zone"]["y1"] == height / 2 - 4
        assert items["attacker-exclusion-zone"]["y2"] == height / 2 + 4
        assert items["deployment-a"]["y2"] == depth
        assert items["deployment-b"]["y1"] == height - depth
        assert items["data-console"]["x"] == width / 2
        assert items["data-console"]["y"] == height / 2
        assert items["inhibitor-antenna"]["y"] > height / 2
    rules = {r["id"]: r for r in history["mission"]["rules"]}
    current_rules = {r["id"]: r for r in now["mission"]["rules"]}
    for skill_id in ("extract-data-pack", "use-inhibitor-antenna"):
        old_skill = rules[skill_id]
        new_skill = current_rules[skill_id]
        assert old_skill["skillTypeIds"] == ["short-skill"]
        for field in ("requirements", "effects", "restrictions"):
            assert old_skill["skillFacts"][field] == new_skill["skillFacts"][field]
        assert {EN, ES} == {c["sourceId"] for c in old["citations"]}


def test_its17_critical_intervention_preserves_historical_differences() -> None:
    old, modern = records()
    old_rules = {r["id"]: r for r in old["facts"]["mission"]["rules"]}
    current = {r["id"]: r for r in modern["facts"]["mission"]["rules"]}
    assert "matching diameter" in old_rules["data-console"]["paragraphs"][0]
    assert "40 mm" in current["data-console"]["paragraphs"][0]
    assert "matching-diameter" in old_rules["inhibitor-antenna"]["paragraphs"][0]
    assert "40 mm" in current["inhibitor-antenna"]["paragraphs"][0]
    assert "enemy Models" in old_rules["defense-system"]["paragraphs"][1]
    assert "Attacker's active Models" in current["defense-system"]["paragraphs"][1]
    assert "Both originals" in old_rules["defense-system"]["paragraphs"][2]
    assert "STR 1" in old_rules["defense-system"]["paragraphs"][2]
    assert "STR 1" in current["defense-system"]["paragraphs"][3]
    assert "ES p. 66" in old_rules["server-room"]["paragraphs"][1]
    assert "ES p. 69" in old_rules["intelcom-support-control"]["paragraphs"][2]
    issues = {i["id"]: i for i in old["facts"]["mission"]["sourceIssues"]}
    assert set(issues) == {
        "its17-critical-intervention-defender-maximum",
        "its17-critical-intervention-room-dimension-en-es",
        "its17-critical-intervention-gate-access-es",
        "its17-critical-intervention-shasvastii-en-es",
        "its17-critical-intervention-intelcom-points-en-es",
        "its17-critical-intervention-exclusion-distance-en-es",
    }
    assert all(i["armyPoints"] == SIZES for i in issues.values())
    assert all(i["status"] == "needs-verification" for i in issues.values())
    assert all("ITS 17 V0.2" in i["description"] for i in issues.values())
    assert not set(issues).intersection({
        i["id"] for i in modern["facts"]["mission"]["sourceIssues"]
    })


def test_its17_critical_intervention_sqlite_stays_isolated(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON, target, shared_library=SHARED)
    assert len(report["scenarios"]) == 16
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2",
        scenario_id="scenario:critical-intervention",
    )
    assert selected is not None
    history, _ = records()
    assert selected["record"] == history
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:critical-intervention",
    ) is None
