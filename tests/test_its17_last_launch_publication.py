"""Source-reviewed ITS 17 Last Launch and isolated historical publication."""
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
    historical = load_curated_document(SEASON, shared_scenario_library=SHARED)
    current = load_curated_document(ITS18)
    return (
        next(r for r in historical["records"] if r["id"] == "scenario:last-launch"),
        next(r for r in current["records"] if r["id"] == "scenario:last-launch"),
    )


def test_its17_last_launch_has_bilingual_pinned_source_membership() -> None:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert season["sharedScenarioLibrary"] == {
        "id": "its17-scenarios",
        "sha256": hashlib.sha256(SHARED.read_bytes()).hexdigest(),
    }
    assert len(library["definitions"]) == 16
    definition = library["definitions"][9]
    assert definition["id"] == "scenario:last-launch"
    assert definition["version"] == "its17-v0.2"
    assert definition["origin"] == {
        "sourceCollectionId": "its-season-17-v0.2",
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert definition["components"] == []
    member = season["scenarioCollection"]["members"][9]
    assert member["scenarioId"] == "scenario:last-launch"
    binding = member["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["review"]["status"] == "reviewed"
    assert binding["componentCitations"] == {}
    assert binding["overrides"] == []
    assert [(c["sourceId"], c["page"]) for c in binding["citations"]] == [
        *((EN, page) for page in (63, 64, 65, 66, 67)),
        *((ES, page) for page in (75, 76, 77, 78, 79, 80)),
    ]


def test_its17_last_launch_scoring_geometry_and_skills_are_source_verified() -> None:
    historical, modern = records()
    assert historical["scope"]["seasons"] == ["its-17"]
    assert historical["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    assert {c["sourceId"] for c in historical["citations"]} == {EN, ES}
    old = historical["facts"]
    current = modern["facts"]
    assert old["playRequirements"] == current["playRequirements"]
    assert old["mission"]["objectives"] == current["mission"]["objectives"]
    assert old["mission"]["gameSizes"] == current["mission"]["gameSizes"]
    assert old["mission"]["endConditions"] == current["mission"]["endConditions"]
    assert old["configurations"] == current["configurations"]
    assert {o["id"]: o["maximumPoints"] for o in old["mission"]["objectives"]} == {
        "extract-more-army-points": 2,
        "extract-more-specialists": 2,
        "kill-specialists-comparison": 2,
        "dominate-launching-tower": 1,
        "classified-objectives": 3,
    }
    assert [
        award["objectivePoints"]
        for award in old["mission"]["objectives"][2]["awards"]
    ] == [2, 1]
    for configuration, offset in zip(old["configurations"], (4, 8, 8), strict=True):
        geometry = configuration["geometry"]
        elements = {row["id"]: row for row in geometry["elements"]}
        tower = elements["launching-tower"]
        assert tower["x2"] - tower["x1"] == 8
        assert tower["y2"] - tower["y1"] == 8
        assert elements["id-scanner-left"]["x"] == offset
        assert elements["id-scanner-right"]["x"] == geometry["table"]["width"] - offset
        assert elements["id-checker"]["x"] == geometry["table"]["width"] / 2
        assert elements["id-checker"]["y"] == geometry["table"]["height"] / 2
        assert elements["deployment-a"]["y2"] == (8 if offset == 4 else 12)
    rules = {r["id"]: r for r in old["mission"]["rules"]}
    modern_rules = {r["id"]: r for r in current["mission"]["rules"]}
    for key in ("download-id", "swap-id", "extract-identified-trooper"):
        assert rules[key]["skillTypeIds"] == ["short-skill"]
        assert rules[key]["skillFacts"]["requirements"] == (
            modern_rules[key]["skillFacts"]["requirements"]
        )
        assert rules[key]["skillFacts"]["effects"] == (
            modern_rules[key]["skillFacts"]["effects"]
        )
        assert rules[key]["skillFacts"]["restrictions"] == (
            modern_rules[key]["skillFacts"]["restrictions"]
        )


def test_its17_last_launch_keeps_historical_diameters_and_bilingual_issues() -> None:
    historical, modern = records()
    old = {r["id"]: r for r in historical["facts"]["mission"]["rules"]}
    now = {r["id"]: r for r in modern["facts"]["mission"]["rules"]}
    for name in ("id-scanners", "id-checker"):
        assert "matching diameter" in old[name]["paragraphs"][0] or (
            "matching-diameter" in old[name]["paragraphs"][0]
        )
        assert "40 mm" in now[name]["paragraphs"][0]
        assert "does not independently specify" in old[name]["paragraphs"][0]
    assert "ES p. 77" in old["launching-tower-gates"]["paragraphs"][0]
    assert "ES p. 78" in old["dominate-launching-tower"]["paragraphs"][1]
    extract = old["extract-identified-trooper"]
    assert "ES p. 79" in extract["skillFacts"]["sourceNotes"][0]
    assert "Peripheral" in extract["paragraphs"][1]
    issues = {
        issue["id"]: issue
        for issue in historical["facts"]["mission"]["sourceIssues"]
    }
    assert set(issues) == {
        "its17-last-launch-tower-dimensions-en-es",
        "its17-last-launch-gate-access-en-es",
        "its17-last-launch-shasvastii-states-en-es",
        "its17-last-launch-peripheral-points-en-es",
    }
    assert all(issue["status"] == "needs-verification" for issue in issues.values())
    assert all(issue["armyPoints"] == SIZES for issue in issues.values())
    assert all("ITS 17 V0.2" in issue["description"] for issue in issues.values())
    assert not set(issues).intersection({
        row["id"] for row in modern["facts"]["mission"]["sourceIssues"]
    })


def test_its17_last_launch_sqlite_is_isolated(tmp_path: Path) -> None:
    target = tmp_path / "its_17.db"
    report = build_its_database(SEASON, target, shared_library=SHARED)
    assert len(report["scenarios"]) == 16
    assert report["inputIdentity"]["seasonId"] == "its-17"
    assert inspect_its_database(
        target, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    selected = select_its_scenario(
        target, season_id="its-17", revision="0.2",
        scenario_id="scenario:last-launch",
    )
    assert selected is not None
    historical, _ = records()
    assert selected["record"] == historical
    assert [s["id"] for s in selected["publication"]["sources"]] == [EN, ES]
    assert select_its_scenario(
        target, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:last-launch",
    ) is None
