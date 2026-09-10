from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_army_data.merge import make_source, merge_sources
from infinity_army_data.normalize import normalize_master
from infinity_db.database import export_database
from infinity_db.web import create_app


def request(
    app: Callable,
    path: str,
    *,
    query: str = "",
    method: str = "GET",
) -> tuple[int, dict[str, str], bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, QUERY_STRING=query, REQUEST_METHOD=method)
    response: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]], exc_info=None) -> None:
        response["status"] = int(status.split()[0])
        response["headers"] = {name.lower(): value for name, value in headers}

    result: Iterator[bytes] = app(environ, start_response)
    try:
        body = b"".join(result)
    finally:
        if hasattr(result, "close"):
            result.close()
    return response["status"], response["headers"], body


@pytest.fixture
def app(tmp_path: Path) -> Callable:
    shared = {"id": 1, "name": "Alpha Ranger", "canonical": 999, "factions": [101]}
    # Declared factions and canonical ownership deliberately differ from actual occurrences.
    blue_only = {"id": 3, "name": "100%_Guard", "canonical": 101, "factions": [201]}
    red_only = {"id": 2, "name": "Beta Scout", "canonical": 101, "factions": [101]}
    documents = [
        ("101-blue_company.json", [shared, blue_only]),
        ("201-red_company.json", [shared, red_only]),
    ]
    sources = []
    for filename, units in documents:
        document = {"version": "test", "reinforcements": None, "units": units}
        if filename.startswith("101-"):
            # This unresolved reference becomes a placeholder, not a browsable unit.
            document["relations"] = [{"units": [{"unit": 9099}]}]
        raw = json.dumps(document)
        source = make_source(filename, raw.encode())
        assert source is not None
        sources.append(source)
    normalized = normalize_master(merge_sources(sources))
    database_path = tmp_path / "infinity.db"
    export_database(normalized, database_path)
    return create_app(database_path)


def test_armies_list_contains_actual_armies_and_counts(app: Callable) -> None:
    status, headers, body = request(app, "/api/armies")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    armies = {item["id"]: item for item in json.loads(body)["items"]}
    assert set(armies) == {101, 201}
    assert armies[101]["slug"] == "blue_company"
    assert armies[101]["name"]
    assert armies[101]["kind"] == "army"
    assert {army["unit_count"] for army in armies.values()} == {2}


def test_army_filter_uses_actual_occurrences(app: Callable) -> None:
    for army_id, expected in [(101, {1, 3}), (201, {1, 2})]:
        status, _, body = request(app, "/api/units", query=urlencode({"army_id": army_id}))
        assert status == 200
        payload = json.loads(body)
        assert payload["total"] == 2
        assert {item["id"] for item in payload["items"]} == expected
        shared = next(item for item in payload["items"] if item["id"] == 1)
        assert set(shared["army_ids"]) == {101, 201}
        assert {army["id"] for army in shared["armies"]} == {101, 201}


def test_global_pagination_counts_unique_units(app: Callable) -> None:
    status, _, body = request(app, "/api/units")
    assert status == 200
    all_units = json.loads(body)
    assert all_units["total"] == 3
    assert all_units["limit"] == 50
    assert all_units["offset"] == 0
    expected_ids = [item["id"] for item in all_units["items"]]
    assert len(set(expected_ids)) == 3

    paged_ids = []
    for offset in range(4):
        status, _, body = request(app, "/api/units", query=f"limit=1&offset={offset}")
        assert status == 200
        page = json.loads(body)
        assert (page["total"], page["limit"], page["offset"]) == (3, 1, offset)
        paged_ids.extend(item["id"] for item in page["items"])
    assert paged_ids == expected_ids


def test_unit_details_are_available_by_id(app: Callable) -> None:
    status, _, body = request(app, "/api/units/1")
    assert status == 200
    unit = json.loads(body)
    assert unit["name"] == "Alpha Ranger"
    assert {army["id"] for army in unit["armies"]} == {101, 201}
    status, headers, body = request(app, "/units/1")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"unit.js" in body
    status, _, body = request(app, "/api/units/9099")
    assert status == 404
    assert json.loads(body)["error"] == "Unit not found"


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        ({"search": "ALPHA"}, {1}),
        ({"search": "%"}, {3}),
        ({"search": "_"}, {3}),
        ({"search": "' OR 1=1 --"}, set()),
        ({"search": "beta", "army_id": 101}, set()),
        ({"search": "beta", "army_id": 201}, {2}),
        ({"army_id": 999}, set()),
    ],
)
def test_unit_search_and_empty_results(
    app: Callable, query: dict[str, Any], expected_ids: set[int]
) -> None:
    status, _, body = request(app, "/api/units", query=urlencode(query))
    assert status == 200
    payload = json.loads(body)
    assert payload["total"] == len(expected_ids)
    assert {item["id"] for item in payload["items"]} == expected_ids


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=201",
        "limit=all",
        "offset=-1",
        "offset=1.5",
        "offset=9223372036854775808",
        "army_id=abc",
        "army_id=9223372036854775808",
        urlencode({"search": "x" * 201}),
    ],
)
def test_invalid_query_returns_json_error(app: Callable, query: str) -> None:
    status, headers, body = request(app, "/api/units", query=query)
    assert status == 400
    assert headers["content-type"].startswith("application/json")
    assert json.loads(body)["error"]


def test_largest_supported_offset_returns_empty_page(app: Callable) -> None:
    status, _, body = request(app, "/api/units", query="offset=9223372036854775807")
    assert status == 200
    assert json.loads(body)["items"] == []


def test_homepage_and_referenced_static_assets_are_served(app: Callable) -> None:
    status, headers, body = request(app, "/")
    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Infinity" in body
    assets = re.findall(r'(?:src|href)=["\'](/static/[^"\']+)', body.decode())
    assert assets
    for asset in assets:
        status, headers, body = request(app, asset)
        assert status == 200
        assert body
        assert int(headers["content-length"]) == len(body)
        head_status, head_headers, head_body = request(app, asset, method="HEAD")
        assert head_status == status
        assert head_headers == headers
        assert head_body == b""


def test_army_symbol_is_served(app: Callable) -> None:
    status, headers, body = request(app, "/static/army-symbols.js")
    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert b"armySymbolPath" in body
    status, headers, body = request(app, "/static/army-symbols/PanOceania/panoceania-1.1.svg")
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body
    status, headers, body = request(
        app, "/static/army-symbols/JSA/hayabusa-reconstructed-transparent.svg"
    )
    assert status == 200
    assert headers["content-type"] == "image/svg+xml"
    assert b"<svg" in body


@pytest.mark.parametrize("path", ["/", "/api/armies", "/api/units", "/missing"])
def test_head_matches_get_headers_without_response_body(app: Callable, path: str) -> None:
    get_status, get_headers, get_body = request(app, path)
    head_status, head_headers, head_body = request(app, path, method="HEAD")
    assert head_status == get_status
    assert head_headers == get_headers
    assert head_body == b""
    assert int(head_headers["content-length"]) == len(get_body)


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_unsupported_method_is_rejected(app: Callable, method: str) -> None:
    status, headers, body = request(app, "/api/units", method=method)
    assert status == 405
    assert {item.strip() for item in headers["allow"].split(",")} == {"GET", "HEAD"}
    assert json.loads(body)["error"]


@pytest.mark.parametrize("path", ["/missing", "/api/nope", "/static/../web.py"])
def test_unknown_and_parent_paths_are_not_served(app: Callable, path: str) -> None:
    status, _, _ = request(app, path)
    assert status == 404


def test_missing_database_fails_before_app_starts(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.db"
    with pytest.raises((OSError, ValueError)):
        create_app(database_path)
    assert not database_path.exists()
