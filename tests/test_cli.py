import os
from pathlib import Path

import pytest

from infinity_army_data.cli import (
    DEFAULT_RAW_DIRECTORY,
    build_parser,
    latest_snapshot,
    snapshot_downloaded_on,
)


def test_cli_build_parses() -> None:
    args = build_parser().parse_args(["build", "army.zip", "--compact"])
    assert args.command == "build"
    assert args.compact is True
    assert args.output_dir == Path("local/work/build/army")
    assert build_parser().parse_args(["merge", "source.zip"]).output == Path(
        "local/work/build/army/master.json"
    )
    assert build_parser().parse_args(["normalize", "master.json"]).output == Path(
        "local/work/build/army/normalized.json"
    )


def test_build_without_source_selects_acquisition_timestamp_not_copy_mtime(
    tmp_path: Path,
) -> None:
    assert DEFAULT_RAW_DIRECTORY == Path("local/data/raw/army")
    older = tmp_path / "JSON 20260909-120000.zip"
    newer = tmp_path / "JSON 20260910-120000.zip"
    repeated = tmp_path / "JSON 20260910-120000-2.zip"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    repeated.write_bytes(b"new repeat")
    os.utime(older, (2_000_000_000, 2_000_000_000))
    assert latest_snapshot(tmp_path) == repeated
    repeated.unlink()
    assert latest_snapshot(tmp_path) == newer
    (tmp_path / "JSON 20261310-120000.zip").write_bytes(b"invalid")
    (tmp_path / "symbols.zip").write_bytes(b"other family")
    assert latest_snapshot(tmp_path) == newer


def test_latest_snapshot_requires_an_archive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No timestamped Army ZIP snapshots"):
        latest_snapshot(tmp_path)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("JSON 20260910.zip", "2026-09-10"),
        ("JSON 20260910-123456-2.zip", "2026-09-10"),
        ("army.zip", None),
        ("JSON 20261310.zip", None),
    ],
)
def test_snapshot_downloaded_on_is_derived_from_downloader_archive_name(
    filename: str,
    expected: str | None,
) -> None:
    assert snapshot_downloaded_on(Path(filename)) == expected
