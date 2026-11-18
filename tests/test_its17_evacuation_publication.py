"""Real ITS 17 V0.2 Evacuation: isolated shared-library publication acceptance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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


def test_reviewed_its17_evacuation_source_and_definition_scope() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    assert source["collection"]["id"] == "its-season-17-v0.2"
    assert source["collection"]["status"] == "archived"
    assert source["scenarioCollection"]["revision"] == "0.2"
    assert [member["scenarioId"] for member in source["scenarioCollection"]["members"]] == [
        "scenario:evacuation",
        "scenario:hardlock",
        "scenario:uplink-center",
        "scenario:battleground",
        "scenario:annihilation",
        "scenario:cutthroat",
    ]
    assert source["records"] == []  # Facts are owned by the shared library.
    assert source["sharedScenarioLibrary"]["sha256"] == hashlib.sha256(
        SHARED.read_bytes(),
    ).hexdigest()
    assert {
        item["id"]: (item["sha256"], item["pageCount"])
        for item in source["sources"]
    } == {
        EN: (
            "73a184b80535f23499000bb81112d95168c12f970fa14a30050a95ec51cdfe71",
            105,
        ),
        ES: (
            "d202d7e3373852204b848fa8eee3bbc19000695cec0296c9882e7d0f3a030457",
            112,
        ),
    }
    binding = source["scenarioCollection"]["members"][0]["sharedDefinition"]
    assert binding["version"] == "its17-v0.2"
    assert binding["componentCitations"] == {}
    assert [(item["sourceId"], item["page"]) for item in binding["citations"]] == [
        *((EN, page) for page in (55, 56, 57, 58)),
        *((ES, page) for page in (50, 51, 52, 53)),
    ]
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert [entry["id"] for entry in library["definitions"]] == [
        "scenario:evacuation",
        "scenario:hardlock",
        "scenario:uplink-center",
        "scenario:battleground",
        "scenario:annihilation",
        "scenario:cutthroat",
    ]
    entry = library["definitions"][0]
    assert entry["origin"] == {
        "sourceCollectionId": source["collection"]["id"],
        "seasonId": "its-17",
        "revision": "0.2",
        "sourceIds": [EN, ES],
    }
    assert entry["record"]["facts"]["definitionVersion"] == 1
    assert entry["components"] == []
    # The current published ITS 18 document is still standalone, not
    # implicitly retargeted through this new historical authoring input.
    current = load_curated_document(ITS18)
    assert "sharedScenarioLibrary" not in current
    assert current["scenarioCollection"]["id"] == "its-18"


def test_real_its17_evacuation_build_is_standalone_and_source_local(
    tmp_path: Path,
) -> None:
    historic = load_curated_document(SEASON, shared_scenario_library=SHARED)
    assert historic["scenarioCollection"]["members"] == [
        {"scenarioId": "scenario:evacuation"},
        {"scenarioId": "scenario:hardlock"},
        {"scenarioId": "scenario:uplink-center"},
        {"scenarioId": "scenario:battleground"},
        {"scenarioId": "scenario:annihilation"},
        {"scenarioId": "scenario:cutthroat"},
    ]
    record = historic["records"][0]
    assert record["scope"]["seasons"] == ["its-17"]
    assert record["sharedDefinition"]["origin"]["seasonId"] == "its-17"
    rules = {item["id"]: item for item in record["facts"]["mission"]["rules"]}
    assert "40 mm" not in rules["extraction-consoles"]["paragraphs"][0]
    issues = record["facts"]["mission"]["sourceIssues"]
    assert len(issues) == 3
    assert all("ITS 17 V0.2" in issue["description"] for issue in issues)
    assert {item["sourceId"] for item in record["citations"]} == {EN, ES}

    current = load_curated_document(ITS18)
    original = next(item for item in current["records"] if item["id"] == record["id"])
    # All typed objectives, end conditions, geometries and operational
    # Skills match both reviewed originals; only the edited prose and
    # source-owned metadata differ between versions.
    assert record["facts"]["mission"]["objectives"] == (
        original["facts"]["mission"]["objectives"]
    )
    assert record["facts"]["mission"]["endConditions"] == (
        original["facts"]["mission"]["endConditions"]
    )
    assert record["facts"]["configurations"] == original["facts"]["configurations"]
    assert record["facts"]["playRequirements"] == original["facts"]["playRequirements"]

    output = tmp_path / "its_17.db"
    first = build_its_database(SEASON, output, shared_library=SHARED)
    assert first["inputIdentity"]["seasonId"] == "its-17"
    assert first["inputIdentity"]["seasonRevision"] == "0.2"
    assert first["inputIdentity"]["sharedScenarioLibrary"]["sha256"] == (
        hashlib.sha256(SHARED.read_bytes()).hexdigest()
    )
    assert first["scenarios"][0]["configurationCount"] == 3
    assert first["scenarios"][0]["citations"] == 8
    assert len(first["scenarios"]) == 6
    assert first["scenarios"][1]["citations"] == 8
    assert first["skills"] == [] and first["states"] == []
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == first
    selected = select_its_scenario(
        output, season_id="its-17", revision="0.2", scenario_id="scenario:evacuation",
    )
    assert selected is not None
    assert selected["record"] == record
    assert [source["id"] for source in selected["publication"]["sources"]] == [EN, ES]
    second = build_its_database(
        SEASON, tmp_path / "its_17_repeat.db", shared_library=SHARED,
    )
    assert second["sha256"] == first["sha256"]


def test_pinned_its17_library_rejects_mutated_facts(tmp_path: Path) -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    changed = tmp_path / "changed.json"
    changed.write_bytes(SHARED.read_bytes() + b" ")
    source_path = tmp_path / "its17.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        build_its_database(source_path, tmp_path / "no.db", shared_library=changed)
