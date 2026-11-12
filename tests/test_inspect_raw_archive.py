"""Development raw-archive CLI never mixes export generations or writes data."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database import export_database, raw_database_path
from infinity_db.database.schema import METADATA_TABLE, RAW_ROWS_TABLE, ROW_JSON, TABLES
from tests.test_database import _normalized_fixture_data
from tools.inspect_raw_archive import inspect_raw_archive, main


def _paired_fixture(tmp_path: Path) -> tuple[Path, Path]:
    app = tmp_path / "army.db"
    raw = tmp_path / "army.raw.db"
    metadata = {
        "export_pair_sha256": json.dumps("a" * 64),
        "source_version": json.dumps("fixture"),
        "imported_tables": json.dumps(list(TABLES)),
    }
    for path in (app, raw):
        with sqlite3.connect(path) as db:
            db.execute(f'CREATE TABLE "{METADATA_TABLE}" (key TEXT, value TEXT)')
            db.executemany(
                f'INSERT INTO "{METADATA_TABLE}" VALUES (?, ?)', list(metadata.items()),
            )
            if path == raw:
                db.execute(
                    f'CREATE TABLE "{RAW_ROWS_TABLE}" (table_name TEXT, '
                    f'row_position INTEGER, "{ROW_JSON}" TEXT, '
                    "PRIMARY KEY (table_name, row_position))"
                )
                db.executemany(
                    f'INSERT INTO "{RAW_ROWS_TABLE}" VALUES (?, ?, ?)',
                    [
                        (name, 0, json.dumps({"source": name, "position": 0}))
                        for name in TABLES if name != "factions"
                    ] + [
                        ("skills", 1, json.dumps({"source": "skills", "position": 1})),
                    ],
                )
    return app, raw


def test_paired_raw_archive_inspection_preserves_exact_rows(tmp_path: Path) -> None:
    app, raw = _paired_fixture(tmp_path)
    verified = inspect_raw_archive(app)
    assert verified["pairStatus"] == "verified"
    assert verified["pairSha256"] == "a" * 64
    assert verified["raw"] == str(raw)
    tables = inspect_raw_archive(app, command="tables")["tables"]
    assert {entry["name"] for entry in tables} == set(TABLES)
    assert next(entry for entry in tables if entry["name"] == "skills")["rawRows"] == 2
    assert next(entry for entry in tables if entry["name"] == "factions")["rawRows"] == 0
    assert inspect_raw_archive(app, command="row", table="skills", position=1)["row"] == {
        "source": "skills", "position": 1,
    }
    assert inspect_raw_archive(app, command="rows", table="skills")["rows"] == [
        {"position": 0, "row": {"source": "skills", "position": 0}},
        {"position": 1, "row": {"source": "skills", "position": 1}},
    ]
    assert inspect_raw_archive(
        app, command="rows", table="skills", position=1, limit=1,
    )["rows"] == [{"position": 1, "row": {"source": "skills", "position": 1}}]
    assert inspect_raw_archive(
        app, command="rows", table="skills", position=3,
    )["rows"] == []


@pytest.mark.parametrize(
    "command,table,position,limit,error",
    (
        ("row", "skills", -1, 20, "nonnegative"),
        ("row", "not_a_table", 0, 20, "Unknown normalized source table"),
        ("row", "skills; DROP TABLE skills", 0, 20, "Unknown normalized source table"),
        ("row", "skills", 999, 20, "Raw row absent"),
        ("rows", "skills", 0, 0, "page size"),
        ("rows", "skills", 0, 101, "page size"),
        ("unknown", None, 0, 20, "Unknown inspection command"),
    ),
)
def test_raw_inspection_rejects_unbounded_or_invalid_requests(
    tmp_path: Path, command: str, table: str | None,
    position: int, limit: int, error: str,
) -> None:
    app, _raw = _paired_fixture(tmp_path)
    with pytest.raises(ValueError, match=error):
        inspect_raw_archive(
            app, command=command, table=table, position=position, limit=limit,
        )


def test_raw_inspection_fails_closed_on_unpaired_generation(tmp_path: Path) -> None:
    app, raw = _paired_fixture(tmp_path)
    with sqlite3.connect(raw) as db:
        db.execute(
            f'UPDATE "{METADATA_TABLE}" SET value = ? WHERE key = ?',
            (json.dumps("b" * 64), "export_pair_sha256"),
        )
    with pytest.raises(ValueError, match="different exports"):
        inspect_raw_archive(app, command="row", table="skills", position=0)


def test_raw_inspection_cli_read_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    app, _raw = _paired_fixture(tmp_path)
    assert main(["--application", str(app), "row", "skills", "0"]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["row"] == {"source": "skills", "position": 0}
    assert main(["--application", str(app), "rows", "skills", "--limit", "101"]) == 1
    assert "page size" in capsys.readouterr().err


@pytest.fixture
def normalized_pair(tmp_path: Path) -> tuple[Path, Path]:
    document = _normalized_fixture_data()
    document["_meta"]["snapshotArchiveSha256"] = "a" * 64
    application = tmp_path / "army.db"
    normalized = tmp_path / "normalized.json"
    export_database(document, application, finalize=False)
    normalized.write_text(json.dumps(document), encoding="utf-8")
    return application, normalized


def test_verified_normalized_inspection_has_exact_raw_row_parity(
    normalized_pair: tuple[Path, Path],
) -> None:
    application, normalized = normalized_pair
    raw = raw_database_path(application)
    verified = inspect_raw_archive(application, normalized=normalized, command="verify")
    legacy = inspect_raw_archive(application, command="verify")
    assert verified["pairSha256"] == legacy["pairSha256"]
    assert verified["pairStatus"] == "verified"

    raw_tables = inspect_raw_archive(application, command="tables")["tables"]
    normalized_tables = inspect_raw_archive(
        application, normalized=normalized, command="tables",
    )["tables"]
    assert normalized_tables == raw_tables
    for name in ("units", "skills", "profiles", "army_lists", "option_includes"):
        legacy_rows = inspect_raw_archive(application, command="rows", table=name, limit=100)
        normalized_rows = inspect_raw_archive(
            application, normalized=normalized, command="rows", table=name, limit=100,
        )
        assert normalized_rows["rows"] == legacy_rows["rows"]
        if normalized_rows["rows"]:
            selected = normalized_rows["rows"][0]
            assert inspect_raw_archive(
                application, normalized=normalized, command="row",
                table=name, position=selected["position"],
            )["row"] == selected["row"]

    raw.unlink()
    assert inspect_raw_archive(
        application, normalized=normalized, command="tables",
    )["tables"] == raw_tables
    assert not raw.exists()


def test_normalized_inspection_rejects_changed_source_and_conflicting_inputs(
    normalized_pair: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    application, normalized = normalized_pair
    with pytest.raises(ValueError, match="exactly one"):
        inspect_raw_archive(
            application, raw=raw_database_path(application), normalized=normalized,
        )
    assert main([
        "--application", str(application), "--normalized", str(normalized),
        "row", "units", "0",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["pairStatus"] == "verified"

    document = json.loads(normalized.read_text(encoding="utf-8"))
    document["tables"]["units"][0]["name"] = "unreviewed name"
    normalized.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        inspect_raw_archive(application, normalized=normalized, command="verify")
    assert main([
        "--application", str(application), "--normalized", str(normalized), "tables",
    ]) == 1
    assert "does not match" in capsys.readouterr().err


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_pinned_real_raw_archive_has_same_export_pair() -> None:
    app = Path(__file__).resolve().parents[1] / "data/generated/army.db"
    report = inspect_raw_archive(app, command="tables")
    assert report["pairStatus"] == "verified"
    assert {entry["name"] for entry in report["tables"]} <= set(TABLES)
    assert {"skills", "army_lists", "units"} <= {
        entry["name"] for entry in report["tables"]
    }
    sample = inspect_raw_archive(app, command="row", table="skills", position=0)
    assert isinstance(sample["row"], dict)
