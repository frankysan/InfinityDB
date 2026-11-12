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
from infinity_db.database import SCHEMA_VERSION, raw_database_path
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


def build_source_fixture(arguments: list[str]) -> int:
    """Exercise the current complete builder Army callback with small source fixtures."""
    import sys

    from infinity_army_data.cli import build_parser as source_parser

    args = source_parser().parse_args(arguments)
    args.require_metadata_for_build = True
    try:
        return app_cli._build_army(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


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
    source_directory: Path,
    tmp_path: Path,
    archive: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = source_directory
    if archive:
        source = tmp_path / "army.zip"
        with zipfile.ZipFile(source, "w") as output:
            for path in source_directory.glob("*.json"):
                output.write(path, f"army/{path.name}")
    output_dir = tmp_path / "generated"
    assert (
        build_source_fixture(["build", str(source), "--output-dir", str(output_dir), "--compact"])
        == 0
    )
    output = capsys.readouterr().out
    size = (output_dir / "army.db").stat().st_size
    assert f"Application database size: {size:,} bytes" in output
    assert "Raw archive" not in output
    assert not (output_dir / "army.raw.db").exists()
    assert not list(output_dir.glob(".army.raw.db.*.tmp"))

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
        assert (
            normalized["_meta"]["snapshotArchiveSha256"]
            == hashlib.sha256(source.read_bytes()).hexdigest()
        )
    for path in source_directory.glob("*.json"):
        if path.name == "metadata.json":
            continue
        army_id = int(path.name.split("-")[0])
        assert reconstruct_source(master, army_id) == json.loads(path.read_text(encoding="utf-8"))
    with sqlite3.connect(output_dir / "army.db") as connection:
        assert connection.execute("SELECT id, name FROM units").fetchall() == [(17, "Test Ranger")]
        assert connection.execute("SELECT COUNT(*) FROM army_units").fetchone()[0] == 2
        assert (
            connection.execute("SELECT COUNT(*) FROM profile_payload_occurrences").fetchone()[0]
            == 2
        )
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'profiles'"
            ).fetchone()
            is None
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    with sqlite3.connect(output_dir / "army.db") as connection:
        assert connection.execute(
            "SELECT value FROM __infinity_metadata WHERE key='export_pair_sha256'"
        ).fetchone() is not None


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
    assert normalized[DISPLAY_IDENTITY_SHA256_METADATA_KEY] == display_identities.content_sha256
    assert main(["export", "data/generated/normalized.json", "data/generated/army.db"]) == 0
    default_database = tmp_path / "data/generated/army.db"
    assert default_database.is_file()
    assert raw_database_path(default_database).is_file()
    custom_database = tmp_path / "custom.db"
    assert main(["export", "data/generated/normalized.json", str(custom_database)]) == 0
    assert raw_database_path(custom_database).is_file()
    with sqlite3.connect(custom_database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 1
    with sqlite3.connect(raw_database_path(custom_database)) as raw_connection:
        assert raw_connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] > 0


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
    assert (
        build_source_fixture(["build", str(tmp_path / "missing"), "--output-dir", str(output_dir)])
        == 1
    )
    assert "ERROR" in capsys.readouterr().err
    assert not (output_dir / "army.db").exists()


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

    assert (
        build_source_fixture(["build", str(source_directory), "--output-dir", str(output_dir)]) == 1
    )
    assert "synthetic source anomaly regression" in capsys.readouterr().err
    assert (output_dir / "normalized.json").is_file()
    assert not (output_dir / "army.db").exists()


def test_serve_defaults_and_explicit_binding() -> None:
    parser = build_parser()
    defaults = parser.parse_args(["serve"])
    assert defaults.db_dir is None  # Auto-select complete checkout build, else tracked release
    assert defaults.host == "0.0.0.0"
    assert defaults.port == 8000
    configured = parser.parse_args(
        ["serve", "--db-dir", "custom.db", "--host", "0.0.0.0", "--port", "9000"]
    )
    assert configured.db_dir == Path("custom.db")
    assert configured.host == "0.0.0.0"
    assert configured.port == 9000


def test_server_directory_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from infinity_db.web import server

    selected = tmp_path / "selected"
    explicit = tmp_path / "explicit"
    opened: list[Path] = []
    monkeypatch.setattr(server, "_ensure_port_is_available", lambda *_args: None)
    monkeypatch.setenv("INFINITY_DB_DB_DIR", str(selected))
    monkeypatch.setattr(
        server,
        "create_app_from_database_set",
        lambda path: opened.append(path) or type("App", (), {"snapshot_revision": "test"})(),
    )

    class FakeServer:
        server_port = 8000

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def serve_forever(self) -> None:
            pass

    monkeypatch.setattr(server, "make_server", lambda *_args, **_kwargs: FakeServer())

    server.serve(None, host="127.0.0.1")
    server.serve(explicit, host="127.0.0.1")
    assert opened == [selected, explicit]


def test_database_health_command_defaults_and_options() -> None:
    parser = build_parser()
    defaults = parser.parse_args(["database-health"])
    assert defaults.database is None
    assert defaults.db_dir is None
    assert defaults.require_raw is False
    assert defaults.json is False

    configured = parser.parse_args(["database-health", "custom.db", "--require-raw", "--json"])
    assert configured.database == Path("custom.db")
    assert configured.require_raw is True
    assert configured.json is True


def test_database_health_command_reports_and_validates_pair(
    source_directory: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "generated"
    assert (
        build_source_fixture(
            ["build", str(source_directory), "--output-dir", str(output_dir), "--compact"]
        )
        == 0
    )
    capsys.readouterr()
    database = output_dir / "army.db"

    assert main(["database-health", str(database)]) == 0
    output = capsys.readouterr().out
    assert "Database health: healthy" in output
    assert f"Schema revision: {SCHEMA_VERSION} (expected {SCHEMA_VERSION})" in output
    assert "Compatibility revision:" in output
    assert "Raw archive: not checked" in output

    # Complete-build Army output is valid without a raw archive; requesting
    # paired audit health must fail rather than silently fabricate a sibling.
    assert main(["database-health", str(database), "--require-raw", "--json"]) == 1
    missing_raw = json.loads(capsys.readouterr().out)
    assert missing_raw["status"] == "unhealthy"
    assert missing_raw["application"]["status"] == "valid"
    assert missing_raw["rawArchive"]["status"] == "invalid"
    assert "does not exist" in missing_raw["rawArchive"]["error"]

    # Standalone export retains its independent queryable raw-pair contract.
    paired = output_dir / "standalone" / "army.db"
    assert main(["export", str(output_dir / "normalized.json"), str(paired)]) == 0
    capsys.readouterr()
    database = paired
    assert main(["database-health", str(database), "--require-raw", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "healthy"
    assert report["application"]["status"] == "valid"
    assert report["application"]["schemaRevision"] == SCHEMA_VERSION
    assert (
        report["application"]["compatibilityRevision"]
        == report["application"]["expectedCompatibilityRevision"]
    )
    assert report["application"]["bytes"] > 0
    assert report["application"]["validationMs"] >= 0
    assert report["rawArchive"]["status"] == "valid"
    assert report["rawArchive"]["bytes"] > 0
    assert len(report["rawArchive"]["pairSha256"]) == 64
    assert report["rawArchive"]["validationMs"] >= 0

    raw_database = raw_database_path(database)
    original_raw = raw_database.read_bytes()
    connection = sqlite3.connect(raw_database)
    try:
        connection.execute(
            "UPDATE __infinity_metadata SET value = ? WHERE key = 'export_pair_sha256'",
            (json.dumps("0" * 64),),
        )
        connection.commit()
    finally:
        connection.close()
    assert main(["database-health", str(database), "--require-raw", "--json"]) == 1
    mismatched_pair = json.loads(capsys.readouterr().out)
    assert mismatched_pair["status"] == "unhealthy"
    assert mismatched_pair["rawArchive"]["status"] == "invalid"
    assert "different exports" in mismatched_pair["rawArchive"]["error"]
    raw_database.write_bytes(original_raw)

    raw_database.unlink()
    assert main(["database-health", str(database)]) == 0
    capsys.readouterr()
    assert main(["database-health", str(database), "--require-raw", "--json"]) == 1
    missing_raw = json.loads(capsys.readouterr().out)
    assert missing_raw["status"] == "unhealthy"
    assert missing_raw["application"]["status"] == "valid"
    assert missing_raw["rawArchive"]["status"] == "invalid"
    assert "does not exist" in missing_raw["rawArchive"]["error"]

    # v27–v31 are supported opt-in layouts; test an unknown schema instead.
    unsupported = SCHEMA_VERSION + 100
    with sqlite3.connect(database) as connection:
        connection.execute(f"PRAGMA user_version = {unsupported}")
    assert main(["database-health", str(database), "--json"]) == 1
    wrong_schema = json.loads(capsys.readouterr().out)
    assert wrong_schema["status"] == "unhealthy"
    assert wrong_schema["application"]["schemaRevision"] == unsupported
    assert wrong_schema["application"]["expectedSchemaRevision"] == SCHEMA_VERSION
    assert "Unsupported InfinityDB database" in wrong_schema["application"]["error"]


def test_validate_curated_command_parses() -> None:
    parser = build_parser()
    args = parser.parse_args(["validate-curated", "data/curated/rules/example.json"])
    assert args.input == Path("data/curated/rules/example.json")


def test_build_rules_command_defaults_to_curated_rules() -> None:
    parser = build_parser()
    args = parser.parse_args(["build-rules"])
    assert args.input == Path("data/curated/rules")
    assert args.output is None

    explicit = parser.parse_args(["build-rules", "--output", "rules_n5.db"])
    assert explicit.output == Path("rules_n5.db")


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
            "data/generated/army.db",
            "--output",
            "reports/peripheral-coverage.json",
        ]
    )
    assert args.database == Path("data/generated/army.db")
    assert args.output == Path("reports/peripheral-coverage.json")


def test_serve_reports_an_already_bound_port(capsys: pytest.CaptureFixture[str]) -> None:
    with socket.socket() as occupied_socket:
        occupied_socket.bind(("127.0.0.1", 0))
        occupied_socket.listen()
        port = occupied_socket.getsockname()[1]

        assert main(["serve", "--host", "127.0.0.1", "--port", str(port)]) == 1

    assert f"Port {port} is already in use on 127.0.0.1" in capsys.readouterr().err


def test_render_scenario_map_command_writes_svg(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "map.json"
    output = tmp_path / "rendered" / "map.svg"
    source.write_text(
        json.dumps(
            {
                "format": "InfinityDB scenario geometry",
                "formatVersion": 1,
                "title": "Annihilation",
                "table": {"width": 24, "height": 32, "unit": "in"},
                "elements": [
                    {
                        "id": "deployment-a",
                        "kind": "rectangle",
                        "style": "deployment-a",
                        "x1": 0,
                        "y1": 0,
                        "x2": {"anchor": "right"},
                        "y2": 8,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["render-scenario-map", str(source), str(output)]) == 0
    assert output.is_file()
    assert 'viewBox="0 0 24 32"' in output.read_text(encoding="utf-8")
    assert f"Scenario map ready: {output}" in capsys.readouterr().out


def test_render_scenario_map_command_uses_maintained_scenario_definition(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    output = tmp_path / "domination-250.svg"

    assert (
        main(
            [
                "render-scenario-map",
                str(source),
                str(output),
                "--scenario-id",
                "scenario:domination",
                "--army-points",
                "250",
            ]
        )
        == 0
    )

    svg = output.read_text(encoding="utf-8")
    assert 'viewBox="0 0 32 48"' in svg
    assert 'data-marker-type="console" data-diameter-mm="40"' in svg
    assert 'id="deployment-a-depth" class="measurement"' in svg
    assert ">12″</text></g>" in svg
    # Reviewed Domination maps measure Console centers instead of labeling quadrant sizes.
    assert 'id="quadrant-1-size" class="area-size"' not in svg
    assert 'id="console-q1-center-left" class="center-measurement"' in svg
    assert 'id="console-q1-center-top" class="center-measurement"' in svg
    assert 'data-distance-inches="8"' in svg
    assert 'data-distance-inches="18"' in svg
    assert f"Scenario map ready: {output}" in capsys.readouterr().out


def test_render_scenario_map_command_uses_maintained_supplies_definition(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    output = tmp_path / "supplies-250.svg"

    assert (
        main(
            [
                "render-scenario-map",
                str(source),
                str(output),
                "--scenario-id",
                "scenario:supplies",
                "--army-points",
                "250",
            ]
        )
        == 0
    )

    svg = output.read_text(encoding="utf-8")
    assert 'viewBox="0 0 32 48"' in svg
    assert 'data-marker-type="supply-box" data-diameter-mm="25"' in svg
    assert 'id="supply-box-left-offset" class="measurement"' in svg
    assert 'id="supply-box-right-offset" class="measurement"' in svg
    assert svg.count(">8″</text></g>") >= 2
    assert f"Scenario map ready: {output}" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("scenario_id", "filename"),
    [
        ("scenario:annihilation", "annihilation-250.svg"),
        ("scenario:firefight", "firefight-250.svg"),
    ],
)
def test_render_scenario_map_command_uses_maintained_standard_deployment_scenarios(
    scenario_id: str,
    filename: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    output = tmp_path / filename

    assert (
        main(
            [
                "render-scenario-map",
                str(source),
                str(output),
                "--scenario-id",
                scenario_id,
                "--army-points",
                "250",
            ]
        )
        == 0
    )

    svg = output.read_text(encoding="utf-8")
    assert 'viewBox="0 0 32 48"' in svg
    assert 'id="deployment-a-depth" class="measurement"' in svg
    assert 'id="deployment-b-depth" class="measurement"' in svg
    assert svg.count(">12″</text></g>") == 2
    assert f"Scenario map ready: {output}" in capsys.readouterr().out


def test_render_scenario_map_command_reports_invalid_geometry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "invalid-map.json"
    output = tmp_path / "map.svg"
    source.write_text(
        json.dumps(
            {
                "format": "InfinityDB scenario geometry",
                "formatVersion": 99,
                "title": "Invalid",
                "table": {"width": 24, "height": 32, "unit": "in"},
                "elements": [],
            }
        ),
        encoding="utf-8",
    )

    assert main(["render-scenario-map", str(source), str(output)]) == 1
    assert "formatVersion must be 1" in capsys.readouterr().err
    assert not output.exists()
