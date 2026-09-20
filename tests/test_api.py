from __future__ import annotations

import json
import runpy
import zipfile
from datetime import datetime
from http.client import HTTPMessage
from pathlib import Path
from urllib.error import HTTPError

import pytest

DOWNLOADER = runpy.run_path(str(Path("tools/download_army_json.py")))
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


def test_download_snapshot_downloads_then_verifies_each_endpoint(tmp_path: Path) -> None:
    metadata = {
        "factions": [
            {"id": 101, "name": "PanOceania", "slug": "panoceania"},
            {"id": 201, "name": "Yu Jing"},
        ]
    }
    document = {"version": "test", "units": []}
    first_pass = [
        json.dumps(metadata).encode(),
        json.dumps(document).encode(),
        json.dumps(document).encode(),
    ]
    responses = first_pass + first_pass
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
    expected_urls = [
        "https://api.example/army/infinity/en/metadata",
        "https://api.example/army/units/en/101",
        "https://api.example/army/units/en/201",
    ]
    assert [url for url, _, _ in requests] == expected_urls * 2
    headers = {key.casefold(): value for key, value in requests[0][1].items()}
    assert headers["origin"] == "https://infinityuniverse.com"
    assert json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8")) == metadata


def test_download_snapshot_rejects_changed_second_pass_without_writing_files(
    tmp_path: Path,
) -> None:
    metadata = json.dumps({"factions": [{"id": 101, "name": "First"}]}).encode()
    first_document = json.dumps({"version": "7.1.1", "units": []}).encode()
    second_document = json.dumps({"version": "7.1.2", "units": []}).encode()
    responses = [metadata, first_document, metadata, second_document]
    target = tmp_path / "101-first.json"
    target.write_text("old", encoding="utf-8")

    def opener(request, timeout):  # noqa: ANN001
        return Response(responses.pop(0))

    with pytest.raises(ApiDownloadError, match=r"Changed endpoint\(s\): 101-first\.json"):
        download_snapshot(tmp_path, opener=opener)

    assert target.read_text(encoding="utf-8") == "old"
    assert not (tmp_path / "metadata.json").exists()


def test_download_snapshot_reports_all_changed_verification_endpoints(tmp_path: Path) -> None:
    metadata = {"factions": [{"id": 101, "name": "First"}]}
    first_metadata = json.dumps(metadata).encode()
    second_metadata = json.dumps({**metadata, "changed": True}).encode()
    first_document = json.dumps({"version": "7.1.1", "units": []}).encode()
    second_document = json.dumps({"version": "7.1.2", "units": []}).encode()
    responses = [first_metadata, first_document, second_metadata, second_document]

    def opener(request, timeout):  # noqa: ANN001
        return Response(responses.pop(0))

    with pytest.raises(ApiDownloadError) as error:
        download_snapshot(tmp_path, opener=opener)

    message = str(error.value)
    assert "Changed endpoint(s): metadata.json" in message
    assert "101-first.json" in message
    assert list(tmp_path.iterdir()) == []


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
        raise HTTPError(request.full_url, 403, "Forbidden", HTTPMessage(), None)

    with pytest.raises(ApiDownloadError, match="Could not download"):
        download_snapshot(tmp_path, opener=opener)


def test_archive_snapshot_uses_timestamp_and_only_downloaded_files(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.json"
    army = tmp_path / "101-first.json"
    unrelated = tmp_path / "unrelated.json"
    metadata.write_text("{}", encoding="utf-8")
    army.write_text('{"units": []}', encoding="utf-8")
    unrelated.write_text("not archived", encoding="utf-8")

    archive = archive_snapshot([army, metadata], tmp_path, now=datetime(2026, 9, 10, 12, 34, 56))

    assert archive.name == "JSON 20260910-123456.zip"
    with zipfile.ZipFile(archive) as output:
        assert output.namelist() == ["101-first.json", "metadata.json"]
