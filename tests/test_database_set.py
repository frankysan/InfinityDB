"""Selected runtime directories fail closed without raw inputs or source rebuilds."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from infinity_db.cli import build_parser, main
from infinity_db.database_set import (
    V10_RUNTIME_FILES,
    database_set_health_report,
    validate_database_set,
)
from tools.prepare_runtime_bundle import expected_files

RELEASE = Path(__file__).resolve().parents[1] / "data/generated"


@pytest.fixture
def runtime_set(tmp_path: Path) -> Path:
    directory = tmp_path / "selected"
    directory.mkdir()
    for name in V10_RUNTIME_FILES:
        shutil.copyfile(RELEASE / name, directory / name)
    return directory


def fingerprints(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.iterdir() if path.is_file()
    }


def test_selected_set_validates_without_build_sources_or_raw_archive(
    runtime_set: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = fingerprints(runtime_set)
    monkeypatch.chdir(tmp_path)
    # A legacy file is not a source or fallback for the embedded v10 model.
    (runtime_set / "deployed-objects.json").write_text("invalid", encoding="utf-8")
    result = validate_database_set(Path("selected"))
    assert result["layout"] == "v10-four-file"
    assert result["integrityCheck"] == "full"
    assert result["schemaVersion"] == 10
    assert result["deployedObjects"] == 17
    assert result["unresolvedDeliveries"] == 1
    assert result["variantPublicationVersion"] == 2
    assert result["variantGroups"] > 0
    assert result["reviewedWeapons"] > 0
    assert result["sha256"] == before
    assert expected_files(runtime_set) == V10_RUNTIME_FILES
    assert {k: v for k, v in fingerprints(runtime_set).items() if k in before} == before


@pytest.mark.parametrize("missing", sorted(V10_RUNTIME_FILES))
def test_missing_selected_file_does_not_fall_back_or_create_outputs(
    runtime_set: Path, missing: str, capsys: pytest.CaptureFixture[str],
) -> None:
    (runtime_set / missing).unlink()
    before = fingerprints(runtime_set)
    with pytest.raises(ValueError):
        expected_files(runtime_set)
    assert fingerprints(runtime_set) == before
    assert main(["database-health", "--db-dir", str(runtime_set), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "unhealthy"
    assert "Incomplete database set" in report["error"]
    assert missing in report["error"]
    assert fingerprints(runtime_set) == before


@pytest.mark.parametrize("publication", ["variant-usage.json", "weapon-profile-sources.json"])
def test_unmatched_publications_are_rejected(runtime_set: Path, publication: str) -> None:
    path = runtime_set / publication
    document = json.loads(path.read_text(encoding="utf-8"))
    document["sourceSnapshot"]["rulesDatabaseSha256"] = "0" * 64
    path.write_text(json.dumps(document), encoding="utf-8")
    before = fingerprints(runtime_set)
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert "does not match release" in report["error"]
    assert fingerprints(runtime_set) == before


def test_embedded_objects_must_match_selected_army(runtime_set: Path) -> None:
    with sqlite3.connect(runtime_set / "rules.db") as connection:
        connection.execute(
            "UPDATE deployed_object_metadata SET value = ? WHERE key = ?",
            (json.dumps("0" * 64), "armyDatabaseSha256"),
        )
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert "Army" in report["error"]


@pytest.mark.parametrize("filename", ["infinity.db", "rules.db"])
@pytest.mark.parametrize("pragma", ["application_id", "user_version"])
def test_unsupported_database_identity_is_rejected(
    runtime_set: Path, filename: str, pragma: str,
) -> None:
    with sqlite3.connect(runtime_set / filename) as connection:
        connection.execute(f"PRAGMA {pragma} = 123456")
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert "Unsupported" in report["error"]


def test_mixed_rules_bytes_invalidate_the_selected_publications(runtime_set: Path) -> None:
    # SQLite's writer version is not game data, but runtime publications still
    # bind exact completed database bytes until their P2 embedding migration.
    path = runtime_set / "rules.db"
    data = bytearray(path.read_bytes())
    data[96:100] = (3040000).to_bytes(4, "big")
    assert data != path.read_bytes()
    path.write_bytes(data)
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert "does not match release artifacts" in report["error"]


@pytest.mark.parametrize("filename", sorted(V10_RUNTIME_FILES))
def test_corrupt_selected_artifact_is_an_unhealthy_report(
    runtime_set: Path, filename: str,
) -> None:
    (runtime_set / filename).write_bytes(b"corrupt")
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert report["error"]


def test_health_cli_reports_the_explicit_directory_and_validation_scope(
    runtime_set: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INFINITY_DB_DB_DIR", str(runtime_set / "wrong"))
    before = fingerprints(runtime_set)
    assert main(["database-health", "--db-dir", str(runtime_set), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "healthy"
    assert report["directory"] == str(runtime_set.resolve())
    assert report["sha256"] == before
    assert report["sourcePolicyFreshness"] == "not-checked"
    assert report["graphicalAssets"] == "not-checked"
    assert main(["database-health", "--db-dir", str(runtime_set)]) == 0
    output = capsys.readouterr().out
    assert "Database-set health: healthy" in output
    assert "integrity: full" in output
    assert fingerprints(runtime_set) == before


def test_missing_directory_is_never_created(tmp_path: Path) -> None:
    directory = tmp_path / "absent"
    report = database_set_health_report(directory)
    assert report["status"] == "unhealthy"
    assert "directory does not exist" in report["error"]
    assert not directory.exists()


def test_directory_selection_conflicts_with_individual_database_or_raw_inspection(
    runtime_set: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["database-health", "custom.db", "--db-dir", "selected"])
    assert exc.value.code == 2
    capsys.readouterr()
    assert main(["database-health", "--db-dir", str(runtime_set), "--require-raw"]) == 1
    assert "--require-raw applies to an Army database" in capsys.readouterr().err
