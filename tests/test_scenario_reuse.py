"""Synthetic ITS 17/18 reuse tests; fixture content is not historical ITS 17 evidence."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    build_its_database,
    inspect_its_database,
    select_its_scenario,
)
from infinity_db.its_source_family import project_its_source_family
from infinity_db.scenario_components import ScenarioComponents
from infinity_db.scenario_reuse import (
    LIBRARY_FORMAT,
    materialize_shared_scenarios,
)

ROOT = Path(__file__).resolve().parents[1]
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
SCENARIO_ID = "scenario:battleground"
VERSION = "synthetic-v1"
REVISION17 = "2025.09.01"


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> tuple[dict, Path, Path, dict]:
    # Use historical ITS 18 facts as an authoring *shape*. The second
    # season and its citations are synthetic and must never be shipped.
    original = project_its_source_family(
        load_curated_document(ITS18), revision="2026.09.01",
    )
    record = deepcopy(original["records"][0])
    assert record["id"] == SCENARIO_ID
    source_id = "synthetic-its17-pdf"
    local_citations = deepcopy(record["citations"])
    for citation in local_citations:
        citation["sourceId"] = source_id
    library = {
        "format": LIBRARY_FORMAT, "formatVersion": 1, "id": "synthetic-shared",
        "definitions": [{
            "id": SCENARIO_ID, "version": VERSION,
            "origin": {
                "sourceCollectionId": original["collection"]["id"],
                "seasonId": "its-18",
                "revision": original["scenarioCollection"]["revision"],
                "sourceIds": sorted({c["sourceId"] for c in record["citations"]}),
            },
            "record": record, "components": [],
        }],
    }
    library_path = _write(tmp_path / "shared.json", library)
    source = deepcopy(original)
    source["collection"].update(
        id="its-season-17-synthetic", title="Synthetic ITS 17",
        effectiveFrom="2025-09-01",
    )
    source["scenarioCollection"].update(
        id="its-17", title="Synthetic ITS 17", revision=REVISION17,
        members=[{
            "scenarioId": SCENARIO_ID,
            "sharedDefinition": {
                "version": VERSION, "citations": local_citations,
                "review": deepcopy(record["review"]),
                "componentCitations": {},
                "overrides": [{
                    "target": SCENARIO_ID, "field": "summary",
                    "value": "Synthetic alternate-season summary, not historical evidence.",
                }],
            },
        }],
    )
    source["sources"] = [{
        **source["sources"][0],
        "id": source_id, "title": "Synthetic ITS 17 publication",
        "version": REVISION17, "publishedDate": "2025-09-01",
        "sha256": "ab" * 32,
        "localPath": "tests/fixtures/nonexistent-its17.pdf",
        "url": "https://example.invalid/synthetic-its17",
    }]
    source["records"] = []
    source["seasonPolicies"] = []
    source["sharedScenarioLibrary"] = {
        "id": library["id"],
        "sha256": hashlib.sha256(library_path.read_bytes()).hexdigest(),
    }
    return source, library_path, _write(tmp_path / "synthetic17.json", source), record


def test_two_season_reuse_preserves_publication_and_materialized_records(
    tmp_path: Path,
) -> None:
    source, library_path, source_path, original = _fixture(tmp_path)
    output = tmp_path / "its_17.db"
    built = build_its_database(source_path, output, shared_library=library_path)
    inspected = inspect_its_database(
        output, source=source_path, shared_library=library_path, core_revision="5.3",
        require_current_builder=True,
    )
    assert built == inspected
    assert built["inputIdentity"]["sharedScenarioLibrary"] == source["sharedScenarioLibrary"]
    selected = select_its_scenario(
        output, season_id="its-17", revision=REVISION17, scenario_id=SCENARIO_ID,
    )
    assert selected is not None
    record = selected["record"]
    assert record["id"] == original["id"]
    assert record["facts"] == original["facts"]
    assert record["summary"].startswith("Synthetic alternate-season")
    assert record["citations"] == source["scenarioCollection"]["members"][0][
        "sharedDefinition"
    ]["citations"]
    assert record["scope"]["seasons"] == ["its-17"]
    assert record["sharedDefinition"] == {
        "libraryId": "synthetic-shared", "id": SCENARIO_ID, "version": VERSION,
        "origin": {
            "sourceCollectionId": "its-season-18-2026.09.01",
            "seasonId": "its-18", "revision": "2026.09.01",
            "sourceIds": ["its-season-18-en-pdf"],
        },
    }
    assert [source["id"] for source in selected["publication"]["sources"]] == [
        "synthetic-its17-pdf",
    ]
    assert selected["publication"]["revision"] == REVISION17
    assert selected["publication"]["sourceCollectionId"] == "its-season-17-synthetic"
    # No cross-database dependency: all record facts and citations are local.
    assert output.is_file() and output.stat().st_size > 0
    assert build_its_database(source_path, tmp_path / "repeat.db",
                              shared_library=library_path)["sha256"] == built["sha256"]
    with pytest.raises(ValueError, match="library bytes"):
        inspect_its_database(output, shared_library=ITS18)


@pytest.mark.parametrize(("edit", "message"), [
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"].update(
        version="unregistered"), "Unknown pinned"),
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"]["overrides"].append(
        {"target": SCENARIO_ID, "field": "summary", "value": "Second"}
    ), "Conflicting"),
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"]["overrides"][0].update(
        target="scenario:not-battleground"), "unknown target"),
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"]["overrides"][0].update(
        field="facts.mission.rules"), "Unsupported"),
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"]["overrides"][0].update(
        field="facts.playRequirements.hvts", value=-1), "non-negative"),
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"].update(
        citations=[{"sourceId": "its-season-18-en-pdf", "page": 1}]
    ), "outside its publication"),
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"].update(
        componentCitations={"geometry:unknown": []}
    ), "must match"),
    (lambda s: s["scenarioCollection"]["members"][0]["sharedDefinition"]["review"].update(
        status="draft"
    ), "requires reviewed evidence"),
    (lambda s: s["records"].append({"id": SCENARIO_ID}), "conflicts with a local"),
])
def test_reuse_fails_closed_on_invalid_season_binding(
    tmp_path: Path, edit, message: str,
) -> None:
    source, library, _, _ = _fixture(tmp_path)
    edit(source)
    with pytest.raises(ValueError, match=message):
        materialize_shared_scenarios(source, library)


def test_missing_library_and_wrong_digest_fail_closed(tmp_path: Path) -> None:
    source, library, source_path, _ = _fixture(tmp_path)
    with pytest.raises(ValueError, match="path is required"):
        build_its_database(source_path, tmp_path / "missing.db")
    source["sharedScenarioLibrary"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256"):
        materialize_shared_scenarios(source, library)




def test_version_pinned_shared_components_compose_in_season_database(tmp_path: Path) -> None:
    source, library_path, source_path, original = _fixture(tmp_path)
    library = json.loads(library_path.read_text(encoding="utf-8"))
    record = deepcopy(original)
    facts = record["facts"]
    mission = facts["mission"]
    facts["definitionVersion"] = 2
    components = []

    def component(kind: str, name: str, payload: dict) -> dict:
        identity = f"{kind}:{name}"
        components.append({
            "id": identity, "kind": kind, "version": "v1",
            "payload": deepcopy(payload), "citations": deepcopy(record["citations"]),
            "scenarios": [SCENARIO_ID],
        })
        return {"ref": identity, "version": "v1"}

    for config in facts["configurations"]:
        config["geometry"] = component(
            "geometry", f"synthetic-{config['id']}", config["geometry"],
        )
    setup = {key: mission[key] for key in ("sides", "gameSizes")}
    objectives = mission["objectives"]
    endings = mission["endConditions"]
    facts["mission"] = {
        "setup": component("setup", "synthetic-battleground", setup),
        "objectives": [
            component("objective", f"synthetic-{index}", objective)
            for index, objective in enumerate(objectives)
        ],
        "rules": [],
        "endConditions": [
            component("end-condition", f"synthetic-{index}", ending)
            for index, ending in enumerate(endings)
        ],
        "sourceIssues": deepcopy(mission["sourceIssues"]),
    }
    library["definitions"][0]["record"] = record
    library["definitions"][0]["components"] = components
    _write(library_path, library)
    source["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(
        library_path.read_bytes()
    ).hexdigest()
    binding = source["scenarioCollection"]["members"][0]["sharedDefinition"]
    binding["componentCitations"] = {
        component["id"]: deepcopy(binding["citations"])
        for component in components
    }
    _write(source_path, source)
    output = tmp_path / "composed.db"
    built = build_its_database(source_path, output, shared_library=library_path)
    assert built["scenarios"][0]["id"] == SCENARIO_ID
    selected = select_its_scenario(
        output, season_id="its-17", revision=REVISION17, scenario_id=SCENARIO_ID,
    )
    assert selected is not None
    resolved = selected["record"]
    assert resolved["facts"]["definitionVersion"] == 1
    assert len(resolved["facts"]["componentSources"]) == len(components)
    assert {c["citations"][0]["sourceId"] for c in resolved["facts"]["componentSources"]} == {
        "synthetic-its17-pdf",
    }
    assert resolved["facts"]["configurations"] == original["facts"]["configurations"]
    for entry in library["definitions"][0]["components"]:
        if entry["kind"] == "geometry":
            entry["payload"] = {"ref": entry["id"], "version": "v1"}
            break
    _write(library_path, library)
    source["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(
        library_path.read_bytes()
    ).hexdigest()
    _write(source_path, source)
    with pytest.raises(ValueError, match="Cyclic"):
        build_its_database(source_path, tmp_path / "cyclic.db", shared_library=library_path)

def _shared_component_across_scenarios(tmp_path: Path) -> tuple[dict, dict, Path, Path]:
    """Two synthetic scenario definitions share one versioned, source-cited setup."""
    source, library_path, _, original = _fixture(tmp_path)
    library = json.loads(library_path.read_text(encoding="utf-8"))
    second_id = "scenario:synthetic-neighbor"
    setup_id = "setup:synthetic-shared-sizes"
    mission = original["facts"]["mission"]
    setup = {
        "id": setup_id,
        "kind": "setup",
        "version": "v1",
        "payload": {
            "sides": deepcopy(mission["sides"]),
            "gameSizes": deepcopy(mission["gameSizes"]),
        },
        "citations": deepcopy(original["citations"]),
        "scenarios": [SCENARIO_ID, second_id],
    }
    library["components"] = [setup]
    base = deepcopy(library["definitions"][0])
    definitions = []
    for scenario_id in (SCENARIO_ID, second_id):
        definition = deepcopy(base)
        definition["id"] = scenario_id
        record = definition["record"]
        record["id"] = scenario_id
        if scenario_id == second_id:
            record["name"] = "Synthetic neighboring scenario"
        facts = record["facts"]
        facts["definitionVersion"] = 2
        old = facts["mission"]
        facts["mission"] = {
            "setup": {"ref": setup_id, "version": "v1"},
            "objectives": deepcopy(old["objectives"]),
            "rules": [],
            "endConditions": deepcopy(old["endConditions"]),
            "sourceIssues": deepcopy(old["sourceIssues"]),
        }
        definition["components"] = [{"ref": setup_id, "version": "v1"}]
        definitions.append(definition)
    library["definitions"] = definitions

    base_member = source["scenarioCollection"]["members"][0]
    base_member["sharedDefinition"]["componentCitations"] = {
        setup_id: [{
            "sourceId": "synthetic-its17-pdf",
            "page": 30,
            "section": "Synthetic first scenario setup",
        }],
    }
    alternate = deepcopy(base_member)
    alternate["scenarioId"] = second_id
    alternate["sharedDefinition"]["overrides"] = []
    alternate["sharedDefinition"]["componentCitations"][setup_id][0].update(
        page=31, section="Synthetic second scenario setup",
    )
    source["scenarioCollection"]["members"].append(alternate)
    library_path = _write(library_path, library)
    source["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(
        library_path.read_bytes(),
    ).hexdigest()
    return source, library, _write(tmp_path / "two-scenarios.json", source), library_path


def test_reused_component_has_one_definition_and_per_scenario_citations(
    tmp_path: Path,
) -> None:
    source, library, source_path, library_path = _shared_component_across_scenarios(tmp_path)
    setup_id = library["components"][0]["id"]
    assert len(library["components"]) == 1
    assert all(definition["components"] == [{"ref": setup_id, "version": "v1"}]
               for definition in library["definitions"])
    resolved = materialize_shared_scenarios(source, library_path)
    definitions = resolved["scenarioComponents"]["definitions"]
    assert len(definitions) == 1
    assert definitions[0]["scenarios"] == [
        SCENARIO_ID, "scenario:synthetic-neighbor",
    ]
    assert {key: pins[0]["page"] for key, pins
            in definitions[0]["scenarioCitations"].items()} == {
        SCENARIO_ID: 30, "scenario:synthetic-neighbor": 31,
    }
    output = tmp_path / "its-17-reused-components.db"
    built = build_its_database(source_path, output, shared_library=library_path)
    assert {row["id"] for row in built["scenarios"]} == {
        SCENARIO_ID, "scenario:synthetic-neighbor",
    }
    for scenario_id, expected_page in (
        (SCENARIO_ID, 30), ("scenario:synthetic-neighbor", 31),
    ):
        selected = select_its_scenario(
            output, season_id="its-17", revision=REVISION17,
            scenario_id=scenario_id,
        )
        assert selected is not None
        record = selected["record"]
        assert record["facts"]["definitionVersion"] == 1
        assert record["facts"]["mission"]["gameSizes"] == (
            library["components"][0]["payload"]["gameSizes"]
        )
        assert record["facts"]["componentSources"] == [{
            "id": setup_id,
            "citations": [{
                "sourceId": "synthetic-its17-pdf",
                "page": expected_page,
                "section": (
                    "Synthetic first scenario setup" if expected_page == 30
                    else "Synthetic second scenario setup"
                ),
            }],
        }]
    assert build_its_database(
        source_path, tmp_path / "reused-components-repeat.db",
        shared_library=library_path,
    )["sha256"] == built["sha256"]


@pytest.mark.parametrize(("mutate", "message"), [
    (
        lambda source, library: library["definitions"][1]["components"][0].update(
            version="v2",
        ),
        "Unknown pinned shared component",
    ),
    (
        lambda source, library: library["definitions"][1]["components"].append({
            **deepcopy(library["components"][0]),
            "payload": {"sides": [], "gameSizes": []},
        }),
        "Conflicting pinned shared component",
    ),
    (
        lambda source, library: library["components"][0].update(
            scenarios=[SCENARIO_ID],
        ),
        "incompatible scenario scope",
    ),
    (
        lambda source, library: source["scenarioCollection"]["members"][1][
            "sharedDefinition"
        ].update(componentCitations={}),
        "must match pinned component identities",
    ),
    (
        lambda source, library: source["scenarioCollection"]["members"][1][
            "sharedDefinition"
        ]["componentCitations"]["setup:synthetic-shared-sizes"][0].update(
            sourceId="its-season-18-en-pdf",
        ),
        "outside its publication",
    ),
])
def test_shared_component_reuse_rejects_unsafe_versions_and_sources(
    tmp_path: Path, mutate, message: str,
) -> None:
    source, library, _, library_path = _shared_component_across_scenarios(tmp_path)
    mutate(source, library)
    library_path = _write(library_path, library)
    source["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(
        library_path.read_bytes(),
    ).hexdigest()
    with pytest.raises(ValueError, match=message):
        materialize_shared_scenarios(source, library_path)


def test_shared_component_citation_map_rejects_missing_scenario(tmp_path: Path) -> None:
    source, _library, _, library_path = _shared_component_across_scenarios(tmp_path)
    document = materialize_shared_scenarios(source, library_path)
    definition = document["scenarioComponents"]["definitions"][0]
    del definition["scenarioCitations"]["scenario:synthetic-neighbor"]
    with pytest.raises(ValueError, match="exact scenario scope"):
        ScenarioComponents(document)


def test_shared_scenario_membership_preserves_current_and_archived_source_family(
    tmp_path: Path,
) -> None:
    """One logical source retains fact tags after a definition moves to a library."""
    original = load_curated_document(ITS18)
    scenario_id = "scenario:battleground"
    record = next(item for item in original["records"] if item["id"] == scenario_id)
    library = {
        "format": LIBRARY_FORMAT, "formatVersion": 1,
        "id": "synthetic-revisioned-scenarios",
        "definitions": [{
            "id": scenario_id, "version": "v1",
            "origin": {
                "sourceCollectionId": original["collection"]["id"],
                "seasonId": "its-18",
                "revision": original["scenarioCollection"]["revision"],
                "sourceIds": sorted({cite["sourceId"] for cite in record["citations"]}),
            },
            "record": deepcopy(record),
            "components": [],
        }],
    }
    library_path = _write(tmp_path / "source-family-library.json", library)
    shared = deepcopy(original)
    shared["records"] = [item for item in shared["records"] if item["id"] != scenario_id]
    member = next(
        item for item in shared["scenarioCollection"]["members"]
        if item["scenarioId"] == scenario_id
    )
    member["sharedDefinition"] = {
        "version": "v1",
        "citations": deepcopy(record["citations"]),
        "review": deepcopy(record["review"]),
        "componentCitations": {},
        "overrides": [],
    }
    shared["sharedScenarioLibrary"] = {
        "id": library["id"], "sha256": hashlib.sha256(library_path.read_bytes()).hexdigest(),
    }
    source_path = _write(tmp_path / "its-family.json", shared)
    loaded = load_curated_document(source_path, shared_scenario_library=library_path)
    for revision in ("2026.09.11", "2026.09.01"):
        expected = project_its_source_family(original, revision=revision)
        actual = project_its_source_family(loaded, revision=revision)
        # Shared composition may move a scenario record, but neither scenario
        # membership nor independent season Skill/State records may change.
        expected_by_id = {item["id"]: item for item in expected["records"]}
        actual_by_id = {item["id"]: item for item in actual["records"]}
        assert len(expected_by_id) == len(expected["records"])
        assert len(actual_by_id) == len(actual["records"])
        assert set(actual_by_id) == set(expected_by_id)
        assert [item for item in actual["records"] if item["kind"] != "scenario"] == [
            item for item in expected["records"] if item["kind"] != "scenario"
        ]
        assert {
            item["id"] for item in actual["records"] if item["kind"] == "scenario"
        } == {
            member["scenarioId"] for member in actual["scenarioCollection"]["members"]
        }
        for identity, left in actual_by_id.items():
            right = expected_by_id[identity]
            without_origin = {key: value for key, value in left.items()
                              if key != "sharedDefinition"}
            assert without_origin == right
        assert actual["sources"] == expected["sources"]
        assert actual["scenarioCollection"] == expected["scenarioCollection"]
    built = build_its_database(
        source_path, tmp_path / "revisioned.db", shared_library=library_path,
    )
    assert built["scenarios"]
    selected = select_its_scenario(
        tmp_path / "revisioned.db", season_id="its-18",
        revision="2026.09.11", scenario_id=scenario_id,
    )
    assert selected is not None
    assert selected["record"]["sharedDefinition"]["version"] == "v1"



def test_complete_set_builder_registers_shared_library_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registered season builds use pinned library bytes and remain self-contained."""
    from infinity_db import database_set, database_set_builder

    source, library_path, _, _ = _fixture(tmp_path)
    root = tmp_path / "checkout"
    season_relative = "data/curated/its/n5-its-season-17.json"
    library_relative = "data/curated/its/shared/synthetic-library.json"
    season_file = root / season_relative
    shared_file = root / library_relative
    shared_file.parent.mkdir(parents=True, exist_ok=True)
    shared_file.write_bytes(library_path.read_bytes().replace(b"\r\n", b"\n"))
    source["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(
        shared_file.read_bytes()
    ).hexdigest()
    season_file.parent.mkdir(parents=True, exist_ok=True)
    season_file.write_bytes(
        (json.dumps(source, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    assert b"\r\n" not in shared_file.read_bytes()
    assert source["sharedScenarioLibrary"]["sha256"] == hashlib.sha256(
        shared_file.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    registration = {"its-17": ("its_17.db", season_relative)}
    monkeypatch.setattr(database_set, "SEASON_DATABASE_SOURCES", registration)
    monkeypatch.setattr(database_set_builder, "SEASON_DATABASE_SOURCES", registration)
    monkeypatch.setitem(
        database_set.SEASON_SHARED_LIBRARY_SOURCES, "its-17", library_relative,
    )
    stage = tmp_path / "stage"
    stage.mkdir()
    database_set_builder._build_registered_seasons(stage, root, "5.3")
    output = stage / "its_17.db"
    report = inspect_its_database(
        output, source=season_file, core_revision="5.3",
        shared_library=shared_file, require_current_builder=True,
    )
    assert report["inputIdentity"]["sharedScenarioLibrary"] == source[
        "sharedScenarioLibrary"
    ]
    assert report["scenarios"][0]["id"] == SCENARIO_ID
    from infinity_db.publication_registry import PublicationRegistry
    from infinity_db.rules_database import RulesDatabase

    registry = PublicationRegistry(
        RulesDatabase(ROOT / "data/generated/rules_n5.db"), {"its-17": output},
    )
    assert registry.season_manifest()["its-17"]["sharedScenarioLibrary"] == source[
        "sharedScenarioLibrary"
    ]
    before = output.read_bytes()

    shared_file.write_bytes(shared_file.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SHA-256"):
        database_set_builder._build_registered_seasons(stage, root, "5.3")
    assert output.read_bytes() == before

    shared_file.write_bytes(library_path.read_bytes())
    monkeypatch.delitem(database_set.SEASON_SHARED_LIBRARY_SOURCES, "its-17")
    with pytest.raises(ValueError, match="library path is required"):
        database_set_builder._build_registered_seasons(stage, root, "5.3")
    assert output.read_bytes() == before


@pytest.mark.parametrize("relative", [
    "../shared.json",
    "data/curated/its/other.json",
    "data/curated/its/shared/../library.json",
    "C:/source/shared.json",
    "local/data/curated/its/shared/library.json",
    "data\\curated\\its\\shared\\library.json",
])
def test_registered_library_paths_are_restricted(
    monkeypatch: pytest.MonkeyPatch, relative: str,
) -> None:
    from infinity_db import database_set

    monkeypatch.setitem(
        database_set.SEASON_SHARED_LIBRARY_SOURCES, "its-18", relative,
    )
    with pytest.raises(ValueError, match="Invalid shared ITS library source"):
        database_set.season_shared_library_source("its-18")


def test_library_registration_cannot_activate_an_unregistered_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from infinity_db import database_set

    monkeypatch.setitem(
        database_set.SEASON_SHARED_LIBRARY_SOURCES, "its-17",
        "data/curated/its/shared/synthetic-library.json",
    )
    with pytest.raises(ValueError, match="unknown season"):
        database_set.season_shared_library_source("its-18")


def test_shared_component_versions_and_reference_cycles_are_checked() -> None:
    # The existing resolver remains the only component composition engine.
    document = {
        "records": [{"id": SCENARIO_ID, "kind": "scenario",
                     "facts": {"definitionVersion": 1}}],
        "scenarioComponents": {
            "formatVersion": 1,
            "definitions": [{
                "id": "geometry:test", "kind": "geometry", "version": "v1",
                "payload": {"ref": "geometry:test", "version": "v1"},
                "scenarios": [SCENARIO_ID], "citations": [{"sourceId": "synthetic"}],
            }],
        },
    }
    with pytest.raises(ValueError, match="Cyclic"):
        ScenarioComponents(document)
    document["scenarioComponents"]["definitions"][0]["payload"] = {
        "ref": "geometry:other", "version": "v1",
    }
    with pytest.raises(ValueError, match="Unknown"):
        ScenarioComponents(document)
