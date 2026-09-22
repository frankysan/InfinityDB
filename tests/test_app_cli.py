from __future__ import annotations

import hashlib
import json
import socket
import sqlite3
import zipfile
from pathlib import Path

import pytest

import infinity_db.cli as app_cli
from infinity_army_data.merge import reconstruct_source
from infinity_db.cli import build_parser, main
from infinity_db.display_identities import (
    DISPLAY_IDENTITY_METADATA_KEY,
    DISPLAY_IDENTITY_SHA256_METADATA_KEY,
    load_display_identity_curated,
)
from infinity_db.identities import (
    IDENTITY_CONFIG_METADATA_KEY,
    IDENTITY_CONFIG_SHA256_METADATA_KEY,
    load_identity_config,
)


@pytest.fixture
def source_directory(tmp_path: Path) -> Path:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    unit = {"id": 17, "name": "Test Ranger", "canonical": 101, "factions": [101, 201]}
    for army_id, slug in [(101, "first_army"), (201, "second_army")]:
        document = {
            "version": "test",
            "reinforcements": None,
            "units": [
                {
                    **unit,
                    "profileGroups": [
                        {"id": 1, "profiles": [{"id": 1, "name": "Ranger"}], "options": []}
                    ],
                    "filters": {"army": army_id},
                }
            ],
        }
        (source_dir / f"{army_id}-{slug}.json").write_text(json.dumps(document), encoding="utf-8")
    (source_dir / "metadata.json").write_text(
        json.dumps(
            {
                "factions": [
                    {"id": 101, "name": "First Army"},
                    {"id": 201, "name": "Second Army"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return source_dir


@pytest.mark.parametrize("archive", [False, True])
def test_build_creates_verified_json_and_queryable_database(
    source_directory: Path, tmp_path: Path, archive: bool
) -> None:
    source = source_directory
    if archive:
        source = tmp_path / "army.zip"
        with zipfile.ZipFile(source, "w") as output:
            for path in source_directory.glob("*.json"):
                output.write(path, f"army/{path.name}")
    output_dir = tmp_path / "generated"
    assert main(["build", str(source), "--output-dir", str(output_dir), "--compact"]) == 0

    master = json.loads((output_dir / "master.json").read_text(encoding="utf-8"))
    normalized_text = (output_dir / "normalized.json").read_text(encoding="utf-8")
    normalized = json.loads(normalized_text)
    validation = json.loads((output_dir / "normalized-validation.json").read_text(encoding="utf-8"))
    identity_config = load_identity_config()
    assert "\n" not in normalized_text
    assert validation["passed"] is True
    assert normalized["_meta"]["validationPassed"] is True
    assert normalized[IDENTITY_CONFIG_METADATA_KEY] == identity_config.document
    assert normalized[IDENTITY_CONFIG_SHA256_METADATA_KEY] == identity_config.content_sha256
    if archive:
        assert normalized["_meta"]["snapshotArchiveSha256"] == hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
    for path in source_directory.glob("*.json"):
        if path.name == "metadata.json":
            continue
        army_id = int(path.name.split("-")[0])
        assert reconstruct_source(master, army_id) == json.loads(path.read_text(encoding="utf-8"))
    with sqlite3.connect(output_dir / "infinity.db") as connection:
        assert connection.execute("SELECT id, name FROM units").fetchall() == [(17, "Test Ranger")]
        assert connection.execute("SELECT COUNT(*) FROM army_units").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 2
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_separate_merge_normalize_export_commands(
    source_directory: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["merge", str(source_directory)]) == 0
    assert main(["normalize", "data/generated/master.json"]) == 0
    normalized = json.loads(Path("data/generated/normalized.json").read_text(encoding="utf-8"))
    identity_config = load_identity_config()
    assert normalized[IDENTITY_CONFIG_METADATA_KEY] == identity_config.document
    assert normalized[IDENTITY_CONFIG_SHA256_METADATA_KEY] == identity_config.content_sha256
    display_identities = load_display_identity_curated()
    assert normalized[DISPLAY_IDENTITY_METADATA_KEY] == display_identities.document
    assert (
        normalized[DISPLAY_IDENTITY_SHA256_METADATA_KEY]
        == display_identities.content_sha256
    )
    assert main(["export", "data/generated/normalized.json"]) == 0
    default_database = tmp_path / "data/generated/infinity.db"
    assert default_database.is_file()
    custom_database = tmp_path / "custom.db"
    assert main(["export", "data/generated/normalized.json", str(custom_database)]) == 0
    with sqlite3.connect(custom_database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 1


def test_normalize_derives_mercenary_display_identity_from_curated_data(tmp_path: Path) -> None:
    curated = load_display_identity_curated()
    canonical_faction_id = 1
    display_army_id = 901
    display_army_slug = curated.canonical_faction_display_armies[canonical_faction_id]
    assert display_army_slug == "non-aligned-armies"
    master_path = tmp_path / "master.json"
    normalized_path = tmp_path / "normalized.json"
    master_path.write_text(
        json.dumps(
            {
                "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
                "armyLists": {
                    str(display_army_id): {
                        "_meta": {"slug": display_army_slug, "kind": "faction"},
                        "unitIds": [1],
                    }
                },
                "units": {
                    "1": {
                        "shared": {
                            "id": 1,
                            "name": "Curated display identity test",
                            "canonical": canonical_faction_id,
                            "factions": [display_army_id],
                        },
                        "byArmy": {str(display_army_id): {}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    assert main(["normalize", str(master_path), str(normalized_path)]) == 0

    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    unit = normalized["tables"]["units"][0]
    assert unit["canonical_faction_id"] == canonical_faction_id
    assert unit["main_army_id"] is None
    assert unit["display_army_id"] == display_army_id


def test_invalid_source_reports_error_without_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_dir = tmp_path / "generated"
    assert main(["build", str(tmp_path / "missing"), "--output-dir", str(output_dir)]) == 1
    assert "ERROR" in capsys.readouterr().err
    assert not (output_dir / "infinity.db").exists()


def test_source_anomaly_regression_blocks_database_export(
    source_directory: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "generated"

    def reject(_source: Path) -> None:
        raise ValueError("synthetic source anomaly regression")

    monkeypatch.setattr(app_cli, "_validate_source_anomaly_baseline", reject)

    assert main(["build", str(source_directory), "--output-dir", str(output_dir)]) == 1
    assert "synthetic source anomaly regression" in capsys.readouterr().err
    assert (output_dir / "normalized.json").is_file()
    assert not (output_dir / "infinity.db").exists()


def test_serve_defaults_and_explicit_binding() -> None:
    parser = build_parser()
    defaults = parser.parse_args(["serve"])
    assert defaults.database == Path("data/generated/infinity.db")
    assert defaults.host == "0.0.0.0"
    assert defaults.port == 8000
    configured = parser.parse_args(
        ["serve", "--database", "custom.db", "--host", "0.0.0.0", "--port", "9000"]
    )
    assert configured.database == Path("custom.db")
    assert configured.host == "0.0.0.0"
    assert configured.port == 9000


def test_validate_curated_command_parses() -> None:
    parser = build_parser()
    args = parser.parse_args(["validate-curated", "data/curated/rules/example.json"])
    assert args.input == Path("data/curated/rules/example.json")


def test_build_rules_command_defaults_to_curated_rules() -> None:
    parser = build_parser()
    args = parser.parse_args(["build-rules", "--output", "rules.db"])
    assert args.input == Path("data/curated/rules")
    assert args.output == Path("rules.db")


def test_validate_peripheral_identities_command_defaults_to_curated_contract() -> None:
    parser = build_parser()
    args = parser.parse_args(["validate-peripheral-identities"])
    assert args.input == Path("data/curated/peripherals/army-identities.json")
    assert args.database is None
    assert args.output is None


def test_validate_peripheral_identities_command_accepts_coverage_database() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "validate-peripheral-identities",
            "--database",
            "data/generated/infinity.db",
            "--output",
            "reports/peripheral-coverage.json",
        ]
    )
    assert args.database == Path("data/generated/infinity.db")
    assert args.output == Path("reports/peripheral-coverage.json")


def test_serve_reports_an_already_bound_port(capsys: pytest.CaptureFixture[str]) -> None:
    with socket.socket() as occupied_socket:
        occupied_socket.bind(("127.0.0.1", 0))
        occupied_socket.listen()
        port = occupied_socket.getsockname()[1]

        assert main(["serve", "--host", "127.0.0.1", "--port", str(port)]) == 1

    assert f"Port {port} is already in use on 127.0.0.1" in capsys.readouterr().err
