"""Source-reviewed ITS 17 V0.2 Resilience Operations is an Extra, not a scenario."""
from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    build_its_database,
    inspect_its_database,
    select_its_scenario,
)
from tests.its17_inventory_expectations import EXPECTED_ITS17_SCENARIO_IDS

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
TRACKED_CORE = ROOT / "data/generated/rules_n5.db"
TRACKED_ITS18 = ROOT / "data/generated/its_18.db"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
ID = "rule:resilience-operations"


def source_document() -> dict:
    return json.loads(SEASON.read_text(encoding="utf-8"))


def resilience_record() -> dict:
    return next(record for record in source_document()["records"] if record["id"] == ID)


def test_extra_is_bilingually_cited_and_not_a_seventeenth_scenario() -> None:
    document = source_document()
    extra = resilience_record()
    assert [m["scenarioId"] for m in document["scenarioCollection"]["members"]] == list(
        EXPECTED_ITS17_SCENARIO_IDS
    )
    assert all("resilience" not in member["scenarioId"]
               for member in document["scenarioCollection"]["members"])
    assert len(document["records"]) == 5
    assert extra["kind"] == "rule"
    assert extra["facts"]["category"] == "optional-extra"
    assert extra["composition"] == {"role": "definition"}
    assert extra["scope"] == {"game": "N5", "seasons": ["its-17"]}
    assert extra["facts"]["applicability"] == {
        "context": "resilience-operations-extra", "revision": "0.2",
    }
    assert [(c["sourceId"], c["page"]) for c in extra["citations"]] == [
        *((EN, p) for p in range(96, 105)),
        *((ES, p) for p in range(103, 112)),
        (EN, 13), (ES, 14),
    ]
    assert extra["review"]["status"] == "reviewed"
    loaded = load_curated_document(SEASON, shared_scenario_library=SHARED)
    assert next(record for record in loaded["records"] if record["id"] == ID) == extra


def test_tactical_objective_battle_condition_and_scoring_facts() -> None:
    facts = resilience_record()["facts"]
    objective = facts["tacticalObjectives"]
    assert objective == {
        "draw": 4, "discard": 1, "maxPointsPerCard": 3,
        "completionMinimum": 1, "moreCompletedBonus": 1,
        "commandTokenRedraw": 1, "revealPerRound": 1,
        "priorityTargetFirst": True, "privateUntilRevealed": True,
    }
    assert facts["battleConditions"] == {
        "draw": 2, "discard": 1, "appliesToBoth": True,
        "wholeGame": True, "duplicateResolution": "second-player-redraws",
        "stackMovementBonuses": False,
    }
    assert [item["armyPoints"] for item in facts["gameSizes"]] == [
        150, 200, 250, 300, 350, 400,
    ]
    assert [item["swc"] for item in facts["gameSizes"]] == [3, 4, 5, 6, 7, 8]
    assert [(item["tableWidthIn"], item["tableHeightIn"],
             item["deploymentDepthIn"]) for item in facts["gameSizes"]] == [
        (24, 32, 8), (32, 48, 12), (32, 48, 12),
        (48, 48, 12), (48, 48, 12), (48, 48, 12),
    ]
    assert "Classified Deck" in " ".join(facts["effects"])
    assert "end of a player's Turn" in " ".join(facts["effects"])
    assert "Refer to the Tactical Objective and Battle Condition cards" in " ".join(
        facts["restrictions"]
    )


def test_tactical_elements_and_glossary_preserve_key_details_and_source_disputes() -> None:
    facts = resilience_record()["facts"]
    elements = {element["id"]: element for element in facts["tacticalElements"]}
    assert list(elements) == [
        "beacons", "hvts", "beepers", "objectives", "f13-defensive-turrets",
    ]
    assert elements["beacons"]["quantity"] == "2 per player (4 total)"
    assert "25 mm" in " ".join(elements["beacons"]["rules"])
    assert "STR 3" in " ".join(elements["beacons"]["rules"])
    assert "4 per player" in elements["hvts"]["quantity"]
    assert "10-10" in " ".join(elements["hvts"]["rules"])
    assert "additional Beeper" in elements["beepers"]["quantity"]
    assert "Coordinated Order" in elements["beepers"]["placement"]
    assert "40 mm" in " ".join(elements["objectives"]["rules"])
    assert "Only when" in elements["f13-defensive-turrets"]["quantity"]
    assert "not Markers" in " ".join(elements["f13-defensive-turrets"]["rules"])

    glossary = {item["id"]: item["text"] for item in facts["glossary"]}
    assert set(glossary) == {
        "capture", "captured-elements", "control", "dominate", "killing", "subjugate",
    }
    assert "without a Roll" in glossary["capture"]
    assert "two with Baggage" in glossary["captured-elements"]
    assert "20 VP" in glossary["dominate"]
    assert "not being deployed" in glossary["killing"]
    notes = " ".join(facts["sourceNotes"])
    for mismatch in ("V0.0 EN p. 63", "V0.1 EN p. 63", "V0.2 ES p. 104",
                     "HVT MOV", "failed Beacon repair", "Baggage"):
        assert mismatch in notes


def test_optional_extra_is_stored_only_in_its17_sqlite(
    tmp_path: Path,
) -> None:
    output = tmp_path / "its_17.db"
    report = build_its_database(SEASON, output, shared_library=SHARED)
    assert [item["id"] for item in report["scenarios"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    assert [item["id"] for item in report["extras"]] == [ID]
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report
    with sqlite3.connect(output) as con:
        row = con.execute(
            "SELECT kind, payload_json FROM records WHERE id=?", (ID,)
        ).fetchone()
        assert row and row[0] == "rule"
        assert json.loads(row[1]) == resilience_record()
        assert con.execute(
            "SELECT COUNT(*) FROM scenario_memberships WHERE scenario_id=?", (ID,)
        ).fetchone()[0] == 0
    assert select_its_scenario(
        output, season_id="its-17", revision="0.2", scenario_id="scenario:resilience-operations",
    ) is None
    assert ID not in {record["id"] for record in load_curated_document(ITS18)["records"]}
    # The new historical Rule must never enter the serving databases.
    for serving in (TRACKED_CORE, TRACKED_ITS18):
        with sqlite3.connect(serving) as con:
            assert con.execute(
                "SELECT COUNT(*) FROM records WHERE id=?", (ID,)
            ).fetchone()[0] == 0


@pytest.mark.parametrize(("change", "message"), [
    ("wrong-season", "out-of-season"),
    ("wrong-revision", "pin its season revision"),
    ("invalid-category", "optional-extra Rule"),
    ("duplicate-element", "invalid tacticalElements entry"),
    ("zero-size", "invalid deployment geometry"),
    ("missing-glossary", "complete typed Extra facts"),
])
def test_extra_fails_closed_on_invalid_scoped_or_typed_facts(
    tmp_path: Path, change: str, message: str,
) -> None:
    document = source_document()
    extra = next(r for r in document["records"] if r["id"] == ID)
    facts = extra["facts"]
    if change == "wrong-season":
        extra["scope"]["seasons"] = ["its-18"]
    elif change == "wrong-revision":
        facts["applicability"]["revision"] = "0.1"
    elif change == "invalid-category":
        facts["category"] = "basic-rule"
    elif change == "duplicate-element":
        facts["tacticalElements"].append(deepcopy(facts["tacticalElements"][0]))
    elif change == "zero-size":
        facts["gameSizes"][0]["tableWidthIn"] = 0
    else:
        del facts["glossary"]
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        build_its_database(source, tmp_path / "invalid.db", shared_library=SHARED)


def test_extra_sqlite_payload_tampering_is_detected(tmp_path: Path) -> None:
    output = tmp_path / "its_17.db"
    build_its_database(SEASON, output, shared_library=SHARED)
    with sqlite3.connect(output) as con:
        con.execute(
            "UPDATE records SET payload_json=? WHERE id=?",
            ('{"id":"rule:resilience-operations","kind":"rule"}', ID),
        )
    with pytest.raises(ValueError, match="content does not match stored hash"):
        inspect_its_database(output)
