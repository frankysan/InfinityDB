from pathlib import Path

import pytest

from infinity_army_data.cli import build_parser, latest_snapshot, snapshot_downloaded_on


def test_cli_build_parses() -> None:
    args = build_parser().parse_args(["build", "army.zip", "--compact"])
    assert args.command == "build"
    assert args.compact is True


def test_build_without_source_uses_newest_raw_zip(tmp_path: Path) -> None:
    older = tmp_path / "JSON 20260909-120000.zip"
    newer = tmp_path / "JSON 20260910-120000.zip"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    assert latest_snapshot(tmp_path) == newer


def test_latest_snapshot_requires_an_archive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No ZIP snapshots"):
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
