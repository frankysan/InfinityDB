from __future__ import annotations

import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from infinity_db.snapshot_provenance import sha256_file, snapshot_content_sha256
from tools.snapshot_archive import create_timestamped_archive


def _write_custom_zip(
    path: Path,
    entries: list[tuple[str, bytes]],
    *,
    date_time: tuple[int, int, int, int, int, int],
    compression: int,
    compresslevel: int | None = None,
    external_attr: int = 0,
) -> None:
    with zipfile.ZipFile(
        path,
        "w",
        compression=compression,
        compresslevel=compresslevel,
    ) as output:
        for name, body in entries:
            info = zipfile.ZipInfo(name, date_time=date_time)
            info.compress_type = compression
            info.create_system = 0
            info.external_attr = external_attr
            output.writestr(
                info,
                body,
                compress_type=compression,
                compresslevel=compresslevel,
            )


def test_timestamped_archive_normalizes_member_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    first = source / "b.txt"
    second = source / "nested" / "a.txt"
    second.parent.mkdir()
    first.write_bytes(b"beta")
    second.write_bytes(b"alpha")

    archive = create_timestamped_archive(
        [first, second],
        tmp_path / "archives",
        prefix="TEST",
        root=source,
        now=datetime(2026, 9, 24, 20, 0, tzinfo=UTC),
    )

    with zipfile.ZipFile(archive) as snapshot:
        assert snapshot.namelist() == ["b.txt", "nested/a.txt"]
        for info in snapshot.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.create_system == 3
            assert info.external_attr == 0o100644 << 16
            assert info.extra == b""
            assert info.comment == b""
            assert info.compress_type == zipfile.ZIP_DEFLATED


def test_timestamped_archive_bytes_ignore_source_mtime_and_input_order(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    first = source / "a.txt"
    second = source / "b.txt"
    first.write_bytes(b"alpha")
    second.write_bytes(b"beta")

    first_archive = create_timestamped_archive(
        [second, first],
        tmp_path / "archives",
        prefix="TEST",
        root=source,
        now=datetime(2026, 9, 24, 20, 0, tzinfo=UTC),
    )
    os.utime(first, (1_000_000_000, 1_000_000_000))
    os.utime(second, (1_700_000_000, 1_700_000_000))
    second_archive = create_timestamped_archive(
        [first, second],
        tmp_path / "archives",
        prefix="TEST",
        root=source,
        now=datetime(2026, 9, 24, 21, 0, tzinfo=UTC),
    )

    assert first_archive.name != second_archive.name
    assert first_archive.read_bytes() == second_archive.read_bytes()
    assert sha256_file(first_archive) == sha256_file(second_archive)


def test_content_hash_ignores_zip_container_metadata_and_compression(tmp_path: Path) -> None:
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    entries = [("nested/a.txt", b"alpha"), ("b.txt", b"beta")]
    _write_custom_zip(
        first,
        entries,
        date_time=(2020, 1, 2, 3, 4, 6),
        compression=zipfile.ZIP_STORED,
        external_attr=0o100600 << 16,
    )
    _write_custom_zip(
        second,
        [*reversed(entries), ("nested/", b"")],
        date_time=(2026, 9, 24, 22, 0, 0),
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=1,
        external_attr=0o100777 << 16,
    )

    assert sha256_file(first) != sha256_file(second)
    assert snapshot_content_sha256(first) == snapshot_content_sha256(second)


def test_content_hash_changes_with_member_path_or_bytes(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.zip"
    renamed = tmp_path / "renamed.zip"
    changed = tmp_path / "changed.zip"
    common = {
        "date_time": (2026, 9, 24, 22, 0, 0),
        "compression": zipfile.ZIP_STORED,
    }
    _write_custom_zip(baseline, [("a.txt", b"alpha")], **common)
    _write_custom_zip(renamed, [("b.txt", b"alpha")], **common)
    _write_custom_zip(changed, [("a.txt", b"changed")], **common)

    identity = snapshot_content_sha256(baseline)
    assert snapshot_content_sha256(renamed) != identity
    assert snapshot_content_sha256(changed) != identity
