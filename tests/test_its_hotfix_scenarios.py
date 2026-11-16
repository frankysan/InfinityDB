"""Exact-source acceptance for the separately published ITS 18 September hotfix.

The historical September 1 selection remains independent of the hotfix.
"""
from pathlib import Path

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    build_its_database,
    inspect_its_database,
    select_its_policies,
    select_its_scenario,
)

ROOT = Path(__file__).resolve().parents[1]
HOTFIX = ROOT / "data/curated/its/n5-its-season-18-2026.09.11.json"
HISTORICAL = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"


def test_hotfix_is_independent_and_retains_historical_source() -> None:
    old = load_curated_document(HISTORICAL)
    current = load_curated_document(HOTFIX)

    assert old["scenarioCollection"]["revision"] == "2026.09.01"
    assert [entry["scenarioId"] for entry in old["scenarioCollection"]["members"]] == [
        "scenario:battleground",
    ]
    assert old["sources"][0]["sha256"] == (
        "9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf"
    )
    assert current["collection"]["id"] == "its-season-18-2026.09.11"
    assert current["scenarioCollection"]["revision"] == "2026.09.11"
    assert [entry["scenarioId"] for entry in current["scenarioCollection"]["members"]] == [
        "scenario:crossing-lines", "scenario:double-bind", "scenario:the-dig",
        "scenario:annihilation", "scenario:battleground", "scenario:cutthroat",
        "scenario:superiority", "scenario:uplink-center", "scenario:hardlock",
        "scenario:b-pong", "scenario:akial-interference", "scenario:evacuation",
        "scenario:neutralization",
    ]
    assert {s["id"]: s["sha256"] for s in current["sources"]} == {
        "its-season-18-en-pdf": (
            "d1700f7f7ebb6c6bd8c2fbfad927c9eee864d170108941032a37f7673c82597f"
        ),
        "its-season-18-es-pdf": (
            "df7398f8bc99927dc30c86cf5625cb08f8f38db9f3bbba685223c9c4981fa94d"
        ),
    }


def test_hotfix_annihilation_exact_score_bands_and_geometry(tmp_path: Path) -> None:
    output = tmp_path / "hotfix.db"
    report = build_its_database(HOTFIX, output)
    assert report["inputIdentity"]["seasonRevision"] == "2026.09.11"
    assert [item["id"] for item in report["scenarios"]] == [
        "scenario:crossing-lines", "scenario:double-bind", "scenario:the-dig",
        "scenario:annihilation", "scenario:battleground", "scenario:cutthroat",
        "scenario:superiority", "scenario:uplink-center", "scenario:hardlock",
        "scenario:b-pong", "scenario:akial-interference", "scenario:evacuation",
        "scenario:neutralization",
    ]
    assert inspect_its_database(output, source=HOTFIX)["sha256"] == report["sha256"]
    assert select_its_scenario(
        output, season_id="its-18", revision="2026.09.01",
        scenario_id="scenario:battleground",
    ) is None

    selected = select_its_scenario(
        output, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:annihilation",
    )
    assert selected is not None
    record = selected["record"]
    mission = record["facts"]["mission"]
    assert [item["armyPoints"] for item in mission["gameSizes"]] == [
        150, 200, 250, 300, 350, 400,
    ]
    assert {item["id"]: item["maximumPoints"] for item in mission["objectives"]} == {
        "destroy-forces": 4, "preserve-forces": 4, "eliminate-lieutenant": 2,
    }
    for objective in mission["objectives"][:2]:
        three_op = next(
            item for item in objective["awards"]
            if item["armyPoints"] == [350] and item["objectivePoints"] == 3
        )
        four_op = next(
            item for item in objective["awards"]
            if item["armyPoints"] == [350] and item["objectivePoints"] == 4
        )
        assert three_op["condition"]["minimum"] == 176
        assert three_op["condition"]["maximum"] == 274
        assert four_op["condition"]["minimum"] == 276
        assert four_op["condition"]["maximum"] is None
    assert {item["id"] for item in mission["sourceIssues"]} == {
        "350-point-destroy-forces-gap",
        "350-point-preserve-forces-gap",
        "400-point-preserve-forces-bilingual-threshold",
    }
    assert len(record["facts"]["configurations"]) == 3
    for conf in record["facts"]["configurations"]:
        geometry = conf["geometry"]
        assert geometry["title"] == "Annihilation"
        assert {element["id"] for element in geometry["elements"]} == {
            "deployment-a", "deployment-b", "table-center-line",
            "deployment-a-label", "deployment-b-label",
        }
        assert {annotation["target"] for annotation in geometry["annotations"]} == {
            "deployment-a", "deployment-b",
        }
    assert [(c["sourceId"], c["page"]) for c in record["citations"]] == [
        ("its-season-18-en-pdf", 125), ("its-season-18-en-pdf", 126),
        ("its-season-18-en-pdf", 127), ("its-season-18-en-pdf", 128),
        ("its-season-18-es-pdf", 132),
    ]


def test_hotfix_battleground_and_event_policies_are_rebased_to_hotfix_pages(
    tmp_path: Path,
) -> None:
    output = tmp_path / "hotfix.db"
    build_its_database(HOTFIX, output)
    battleground = select_its_scenario(
        output, season_id="its-18", revision="2026.09.11",
        scenario_id="scenario:battleground",
    )
    assert battleground is not None
    assert [c["page"] for c in battleground["record"]["citations"]] == [129, 130, 131]
    for context, page in (
        ("official-tournament", 27), ("reinforcements-extra", 28),
        ("team-ops-extra", 29),
    ):
        policies = select_its_policies(
            output, season_id="its-18", revision="2026.09.11", context=context,
        )
        assert len(policies) == 1
        assert policies[0]["citations"][0]["page"] == page
        assert select_its_policies(
            output, season_id="its-18", revision="2026.09.01", context=context,
        ) == []
