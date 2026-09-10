from __future__ import annotations

import json
import runpy
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError

import pytest

DOWNLOADER = runpy.run_path(Path("tools/download_army_json.py"))
ApiDownloadError = DOWNLOADER["ApiDownloadError"]
download_snapshot = DOWNLOADER["download_snapshot"]
archive_snapshot = DOWNLOADER["archive_snapshot"]


class Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_download_snapshot_fetches_metadata_before_each_faction(tmp_path: Path) -> None:
    metadata = {
        "factions": [
            {"id": 101, "name": "PanOceania", "slug": "panoceania"},
            {"id": 201, "name": "Yu Jing"},
        ]
    }
    document = {"version": "test", "units": []}
    responses = [
        json.dumps(metadata).encode(),
        json.dumps(document).encode(),
        json.dumps(document).encode(),
    ]
    requests = []

    def opener(request, timeout):  # noqa: ANN001
        requests.append((request.full_url, dict(request.header_items()), timeout))
        return Response(responses.pop(0))

    files = download_snapshot(tmp_path, api_base_url="https://api.example/army", opener=opener)

    assert [path.name for path in files] == [
        "metadata.json",
        "101-panoceania.json",
        "201-yu-jing.json",
    ]
    assert [url for url, _, _ in requests] == [
        "https://api.example/army/infinity/en/metadata",
        "https://api.example/army/units/en/101",
        "https://api.example/army/units/en/201",
    ]
    headers = {key.casefold(): value for key, value in requests[0][1].items()}
    assert headers["origin"] == "https://infinityuniverse.com"
    assert json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8")) == metadata


def test_download_snapshot_rejects_bad_unit_response_without_overwriting_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "101-first.json"
    target.write_text("old", encoding="utf-8")
    responses = [json.dumps({"factions": [{"id": 101, "name": "First"}]}).encode(), b"{}"]

    def opener(request, timeout):  # noqa: ANN001
        return Response(responses.pop(0))

    with pytest.raises(ApiDownloadError, match="Invalid unit-list"):
        download_snapshot(tmp_path, opener=opener)
    assert target.read_text(encoding="utf-8") == "old"


def test_download_snapshot_wraps_http_errors(tmp_path: Path) -> None:
    def opener(request, timeout):  # noqa: ANN001
        raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

    with pytest.raises(ApiDownloadError, match="Could not download"):
        download_snapshot(tmp_path, opener=opener)


def test_archive_snapshot_uses_timestamp_and_only_downloaded_files(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.json"
    army = tmp_path / "101-first.json"
    unrelated = tmp_path / "unrelated.json"
    metadata.write_text("{}", encoding="utf-8")
    army.write_text('{"units": []}', encoding="utf-8")
    unrelated.write_text("not archived", encoding="utf-8")

    archive = archive_snapshot(
        [army, metadata], tmp_path, now=datetime(2026, 9, 10, 12, 34, 56)
    )

    assert archive.name == "JSON 20260910-123456.zip"
    with zipfile.ZipFile(archive) as output:
        assert output.namelist() == ["101-first.json", "metadata.json"]
