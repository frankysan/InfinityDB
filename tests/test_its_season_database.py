"""P3.2 isolated ITS 18 database build, source binding and fail-closed tests."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    ITS_APPLICATION_ID,
    ITS_SCHEMA_VERSION,
    build_its_database,
    inspect_its_database,
    select_its_scenario,
)
from infinity_db.rules_database import RulesDatabase
from tools.build_its_season import main

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"
TRACKED_RULES = ROOT / "data/generated/rules_n5.db"


def _modified_source(tmp_path: Path, mutator) -> Path:
    document = load_curated_document(SOURCE)
    mutator(document)
    target = tmp_path / "modified-its.json"
    target.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return target


def test_isolated_its_database_is_deterministic_and_matches_existing_publication(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "one.db", tmp_path / "two.db"
    report = build_its_database(SOURCE, first)
    repeated = build_its_database(SOURCE, second)

    assert first.read_bytes() == second.read_bytes()
    assert report == repeated
    assert report == inspect_its_database(first, source=SOURCE, core_revision="5.3")
    assert report["schemaVersion"] == ITS_SCHEMA_VERSION
    assert report["inputIdentity"]["seasonId"] == "its-18"
    assert report["inputIdentity"]["seasonRevision"] == "2026.09.01"
    assert report["inputIdentity"]["sourceCollectionId"] == "its-season-18-2026.09.01"
    assert len(report["inputIdentity"]["builderRevision"]) == 64
    assert report["inputIdentity"]["sources"] == [
        {
            "id": "its-season-18-en-pdf",
            "sha256": "9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf",
        }
    ]
    assert report["scenarios"][0]["id"] == "scenario:battleground"
    assert report["scenarios"][0]["configurationCount"] == 3
    assert report["scenarios"][0]["citations"] == 3
    current = RulesDatabase(TRACKED_RULES).scenario_publications("scenario:battleground")
    assert len(current) == 1
    assert current[0]["content_sha256"] == report["scenarios"][0]["contentSha256"]

    with sqlite3.connect(first) as connection:
        assert connection.execute("PRAGMA application_id").fetchone()[0] == ITS_APPLICATION_ID
        assert connection.execute("PRAGMA user_version").fetchone()[0] == ITS_SCHEMA_VERSION
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert tables >= {
            "collections", "sources", "records", "record_citations", "scenario_sets",
            "scenario_memberships", "scenario_configurations",
        }
        assert connection.execute("SELECT count(*) FROM sources").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM scenario_memberships").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM scenario_configurations").fetchone()[0] == 3


def test_select_its_scenario_requires_exact_season_and_revision(tmp_path: Path) -> None:
    path = tmp_path / "its_18.db"
    build_its_database(SOURCE, path)
    publication = select_its_scenario(
        path, season_id="its-18", revision="2026.09.01", scenario_id="scenario:battleground",
    )
    assert publication is not None
    assert publication["record"]["name"] == "Battleground"
    assert publication["publication"]["sourceCollectionId"] == "its-season-18-2026.09.01"
    assert publication["publication"]["position"] == 0
    assert {source["id"] for source in publication["publication"]["sources"]} == {
        "its-season-18-en-pdf"
    }
    assert len(publication["record"]["facts"]["configurations"]) == 3
    assert select_its_scenario(
        path, season_id="its-17", revision="2026.09.01", scenario_id="scenario:battleground",
    ) is None
    assert select_its_scenario(
        path, season_id="its-18", revision="2025.09.01", scenario_id="scenario:battleground",
    ) is None
    assert select_its_scenario(
        path, season_id="its-18", revision="2026.09.01", scenario_id="scenario:unknown",
    ) is None
    with pytest.raises(ValueError, match="revision must be provided exactly"):
        select_its_scenario(
            path, season_id="its-18", revision="", scenario_id="scenario:battleground",
        )


def test_builder_replaces_only_validated_output_and_is_repeatable(tmp_path: Path) -> None:
    output = tmp_path / "its_18.db"
    original = build_its_database(SOURCE, output)
    assert build_its_database(SOURCE, output) == original
    assert not list(tmp_path.glob(".its-season-*.db"))


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda doc: doc["collection"].update(domain="core-rules"), "ITS 18 source"),
        (lambda doc: doc["scenarioCollection"].update(id="its-17"), "ITS 18 source"),
        (lambda doc: doc["records"][0]["scope"].update(seasons=["its-17"]), "out-of-season"),
        (lambda doc: doc["sources"][0].update(version="2025.09.01"), "revision-matched"),
        (
            lambda doc: doc["records"][0]["facts"]["configurations"][0]["geometry"].update(
                format="invalid"
            ),
            "scenario",
        ),
    ),
)
def test_invalid_source_preserves_existing_database(
    tmp_path: Path, mutation, message: str,
) -> None:
    output = tmp_path / "its_18.db"
    build_its_database(SOURCE, output)
    before = output.read_bytes()
    source = _modified_source(tmp_path, mutation)
    with pytest.raises(ValueError, match=message):
        build_its_database(source, output)
    assert output.read_bytes() == before
    assert not list(tmp_path.glob(".its-season-*.db"))


def test_inspection_rejects_changed_source_and_core_revision(tmp_path: Path) -> None:
    path = tmp_path / "its.db"
    build_its_database(SOURCE, path)
    changed = _modified_source(
        tmp_path, lambda doc: doc["collection"].update(title="Changed title")
    )
    with pytest.raises(ValueError, match="source bytes"):
        inspect_its_database(path, source=changed)
    with pytest.raises(ValueError, match="different N5 core revision"):
        inspect_its_database(path, core_revision="5.4")
    assert inspect_its_database(path, source=SOURCE)["scenarios"]


def test_historical_schema_compatible_artifact_does_not_require_current_builder(
    tmp_path: Path,
) -> None:
    from infinity_db.its_season_database import _digest

    path = tmp_path / "historical.db"
    build_its_database(SOURCE, path)
    with closing(sqlite3.connect(path)) as connection, connection:
        metadata = json.loads(connection.execute(
            "SELECT value FROM __its_metadata WHERE key='inputIdentity'"
        ).fetchone()[0])
        metadata["builderRevision"] = "0" * 64
        connection.execute(
            "UPDATE __its_metadata SET value=? WHERE key='inputIdentity'",
            (json.dumps(metadata, sort_keys=True),),
        )
        connection.execute(
            "UPDATE __its_metadata SET value=? WHERE key='buildId'",
            (json.dumps(_digest(metadata)),),
        )
    assert inspect_its_database(path, source=SOURCE)["scenarios"]
    with pytest.raises(ValueError, match="requires rebuilding after builder change"):
        inspect_its_database(path, source=SOURCE, require_current_builder=True)


def test_corrupted_scenario_and_geometry_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "its.db"
    build_its_database(SOURCE, path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "UPDATE scenario_configurations SET geometry_json='{}' "
            "WHERE configuration_id='150-points'"
        )
    with pytest.raises(ValueError, match="geometry or Army Points mismatch"):
        inspect_its_database(path)
    build_its_database(SOURCE, path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "UPDATE records SET content_sha256=? WHERE id='scenario:battleground'",
            ("0" * 64,),
        )
    with pytest.raises(ValueError, match="content hash mismatch"):
        inspect_its_database(path)


def test_isolated_tool_rejects_serving_target_and_supports_read_only_check(
    tmp_path: Path,
) -> None:
    output = tmp_path / "its_18.db"
    assert main(["--source", str(SOURCE), "--output", str(output)]) == 0
    before = output.read_bytes()
    assert main([
        "--source", str(SOURCE), "--output", str(output), "--check"
    ]) == 0
    assert output.read_bytes() == before
    with pytest.raises(SystemExit) as exc:
        main(["--output", str(ROOT / "data/generated/its_18.db")])
    assert exc.value.code == 2
    assert not (ROOT / "data/generated/its_18.db").exists()


def test_missing_or_wrong_database_fails_without_creating_outputs(tmp_path: Path) -> None:
    absent = tmp_path / "missing.db"
    with pytest.raises(ValueError, match="does not exist"):
        inspect_its_database(absent)
    assert not absent.exists()
    with pytest.raises(ValueError, match="core rules revision"):
        build_its_database(SOURCE, tmp_path / "bad.db", core_revision=" ")
    assert not (tmp_path / "bad.db").exists()
