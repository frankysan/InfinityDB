from __future__ import annotations

import json
import socket
import sqlite3
import zipfile
from pathlib import Path

import pytest

from infinity_army_data.merge import reconstruct_source
from infinity_db.cli import build_parser, main


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
    assert "\n" not in normalized_text
    assert validation["passed"] is True
    assert normalized["_meta"]["validationPassed"] is True
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
    assert main(["export", "data/generated/normalized.json"]) == 0
    default_database = tmp_path / "data/generated/infinity.db"
    assert default_database.is_file()
    custom_database = tmp_path / "custom.db"
    assert main(["export", "data/generated/normalized.json", str(custom_database)]) == 0
    with sqlite3.connect(custom_database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 1


def test_invalid_source_reports_error_without_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_dir = tmp_path / "generated"
    assert main(["build", str(tmp_path / "missing"), "--output-dir", str(output_dir)]) == 1
    assert "ERROR" in capsys.readouterr().err
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


def test_serve_reports_an_already_bound_port(capsys: pytest.CaptureFixture[str]) -> None:
    with socket.socket() as occupied_socket:
        occupied_socket.bind(("127.0.0.1", 0))
        occupied_socket.listen()
        port = occupied_socket.getsockname()[1]

        assert main(["serve", "--host", "127.0.0.1", "--port", str(port)]) == 1

    assert f"Port {port} is already in use on 127.0.0.1" in capsys.readouterr().err
