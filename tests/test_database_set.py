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
    COMPLETE_RUNTIME_FILES,
    database_set_health_report,
    validate_database_set,
)

RELEASE = Path(__file__).resolve().parents[1] / "data/generated"


@pytest.fixture
def runtime_set(tmp_path: Path) -> Path:
    directory = tmp_path / "selected"
    directory.mkdir()
    for name in COMPLETE_RUNTIME_FILES:
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
    for name in ("deployed-objects.json", "variant-usage.json",
                 "weapon-profile-sources.json"):
        (runtime_set / name).write_text("invalid", encoding="utf-8")
    result = validate_database_set(Path("selected"), require_complete=True)
    assert result["layout"] == "v17-three-file"
    assert result["integrityCheck"] == "full"
    assert result["schemaVersion"] == 17
    assert result["deployedObjects"] == 17
    assert result["unresolvedDeliveries"] == 1
    assert result["variantPublicationVersion"] == 2
    assert result["variantGroups"] > 0
    assert result["reviewedWeapons"] > 0
    assert result["sha256"] == before
    assert set(result["sha256"]) == COMPLETE_RUNTIME_FILES
    assert result["seasons"]["its-18"]["revision"] == "2026.09.01"
    assert {k: v for k, v in fingerprints(runtime_set).items() if k in before} == before


@pytest.mark.parametrize("missing", sorted(COMPLETE_RUNTIME_FILES))
def test_missing_selected_file_does_not_fall_back_or_create_outputs(
    runtime_set: Path, missing: str, capsys: pytest.CaptureFixture[str],
) -> None:
    (runtime_set / missing).unlink()
    before = fingerprints(runtime_set)
    with pytest.raises(ValueError):
        validate_database_set(runtime_set, require_complete=True)
    assert fingerprints(runtime_set) == before
    assert main(["database-health", "--db-dir", str(runtime_set), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "unhealthy"
    assert "Incomplete database set" in report["error"]
    assert missing in report["error"]
    assert fingerprints(runtime_set) == before


@pytest.mark.parametrize("schema", [10, 11])
def test_json_dependent_schemas_are_retired_even_with_sidecars(
    runtime_set: Path, schema: int,
) -> None:
    (runtime_set / "variant-usage.json").write_text("invalid", encoding="utf-8")
    (runtime_set / "weapon-profile-sources.json").write_text("invalid", encoding="utf-8")
    with sqlite3.connect(runtime_set / "rules_n5.db") as connection:
        connection.execute(f"PRAGMA user_version={schema}")
    with pytest.raises(ValueError, match="Unsupported Rules schema"):
        validate_database_set(runtime_set)


def test_complete_set_rejects_stale_or_mismatched_its(runtime_set: Path) -> None:
    its = runtime_set / "its_18.db"
    with sqlite3.connect(its) as connection:
        connection.execute(
            "UPDATE __its_metadata SET value=? WHERE key='buildId'",
            (json.dumps("0" * 64),),
        )
    with pytest.raises(ValueError, match="ITS build provenance"):
        validate_database_set(runtime_set, require_complete=True)


def test_complete_set_rejects_its_from_a_different_source_build(
    runtime_set: Path, tmp_path: Path,
) -> None:
    from infinity_db.its_season_database import build_its_database

    source = (
        Path(__file__).resolve().parents[1]
        / "data/curated/rules/n5-its-season-18-2026.09.01.json"
    )
    modified = tmp_path / "same-semantics-different-source.json"
    modified.write_bytes(source.read_bytes() + b"\n")
    build_its_database(modified, runtime_set / "its_18.db")
    with pytest.raises(ValueError, match="does not match selected build source identity"):
        validate_database_set(runtime_set, require_complete=True)


def test_embedded_objects_must_match_selected_army(runtime_set: Path) -> None:
    with sqlite3.connect(runtime_set / "rules_n5.db") as connection:
        connection.execute(
            "UPDATE deployed_object_metadata SET value = ? WHERE key = ?",
            (json.dumps("0" * 64), "armyDatabaseSha256"),
        )
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert "Army" in report["error"]


@pytest.mark.parametrize("filename", ["army.db", "rules_n5.db"])
@pytest.mark.parametrize("pragma", ["application_id", "user_version"])
def test_unsupported_database_identity_is_rejected(
    runtime_set: Path, filename: str, pragma: str,
) -> None:
    with sqlite3.connect(runtime_set / filename) as connection:
        connection.execute(f"PRAGMA {pragma} = 123456")
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert "Unsupported" in report["error"] or "require Army schema" in report["error"]


def test_embedded_variant_fingerprint_rejects_tampering(runtime_set: Path) -> None:
    with sqlite3.connect(runtime_set / "rules_n5.db") as connection:
        connection.execute("UPDATE variant_usage_metadata SET content_sha256=?", ("0" * 64,))
    before = fingerprints(runtime_set)
    report = database_set_health_report(runtime_set)
    assert report["status"] == "unhealthy"
    assert report["error"]
    assert fingerprints(runtime_set) == before


@pytest.mark.parametrize("filename", sorted(COMPLETE_RUNTIME_FILES))
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


def test_complete_startup_rejects_transitional_set_without_fallback(
    runtime_set: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from infinity_db.web import create_app_from_database_set

    monkeypatch.setenv("INFINITY_DB_DB_DIR", str(RELEASE))
    monkeypatch.setenv("INFINITY_DB_DATABASE", str(RELEASE / "army.db"))
    with sqlite3.connect(runtime_set / "rules_n5.db") as connection:
        connection.execute("PRAGMA user_version=16")
    before = fingerprints(runtime_set)
    with pytest.raises(ValueError, match="require Rules schema v17"):
        create_app_from_database_set(runtime_set)
    assert fingerprints(runtime_set) == before


def test_complete_startup_does_not_create_missing_selected_directory(tmp_path: Path) -> None:
    from infinity_db.web import create_app_from_database_set

    directory = tmp_path / "missing"
    with pytest.raises(ValueError, match="directory does not exist"):
        create_app_from_database_set(directory)
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
