from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from tools.performance.capacity_test import (
    RequestResult,
    ScenarioCase,
    _base_url,
    _report_path,
    capacity_test,
    discover_scenario,
    main,
    run_phase,
    summarize_phase,
)


def test_discover_scenario_covers_representative_pages_and_apis() -> None:
    payloads: dict[str, dict[str, Any]] = {
        "/api/version": {
            "version": "0.10.0+dev",
            "snapshot_revision": "snapshot-1",
            "static_revision": "static-1",
        },
        "/api/units?limit=1": {
            "items": [{"id": 1, "public_slug": "ranger-prototype", "name": "Ranger Prototype"}]
        },
        "/api/skills": {"items": [{"id": 11, "slug": "mimetism"}]},
        "/api/equipment": {"items": [{"id": 21, "slug": "medikit"}]},
        "/api/weapons": {"items": [{"id": 31, "public_slug": "combi-rifle"}]},
    }

    def fetch_json(_base_url: str, path: str):
        return payloads[path]

    target, cases = discover_scenario(
        "https://example.invalid",
        timeout=1,
        fetch_json=fetch_json,
    )

    assert target == {
        "version": "0.10.0+dev",
        "snapshotRevision": "snapshot-1",
        "staticRevision": "static-1",
    }
    assert [(case.name, case.path, case.kind) for case in cases] == [
        ("unit-list-page", "/units", "page"),
        ("unit-list-api", "/api/units?limit=50", "api"),
        ("search-page", "/search?q=Ranger", "page"),
        ("search-api", "/api/search?q=Ranger", "api"),
        ("unit-detail-page", "/units/ranger-prototype", "page"),
        ("unit-detail-api", "/api/units/ranger-prototype", "api"),
        ("skill-catalog-page", "/skills", "page"),
        ("skill-catalog-api", "/api/skills", "api"),
        ("skill-detail-page", "/skills/mimetism", "page"),
        ("skill-detail-api", "/api/skills/mimetism", "api"),
        ("equipment-catalog-page", "/equipment", "page"),
        ("equipment-catalog-api", "/api/equipment", "api"),
        ("equipment-detail-page", "/equipment/medikit", "page"),
        ("equipment-detail-api", "/api/equipment/medikit", "api"),
        ("weapon-catalog-page", "/weapons", "page"),
        ("weapon-catalog-api", "/api/weapons", "api"),
        ("weapon-detail-page", "/weapons/combi-rifle", "page"),
        ("weapon-detail-api", "/api/weapons/combi-rifle", "api"),
    ]


def test_unit_explorer_scenario_uses_scoped_counts_and_extended_pages() -> None:
    from urllib.parse import parse_qs, urlsplit

    def fetch_json(_base_url: str, path: str):
        if path == "/api/version":
            return {
                "version": "1.2.2+dev",
                "snapshot_revision": "snapshot-1",
                "static_revision": "static-1",
            }
        parsed = urlsplit(path)
        assert parsed.path == "/api/units"
        assert parse_qs(parsed.query)["counts"] == ["prospective"]
        return {
            "items": [{"id": 1, "name": "Ranger Prototype"}],
            "prospective_counts": {
                "skills": {"11": 2, "12": 10, "13": 0},
                "equipment": {"21": 3, "22": 7, "cube": 99},
            },
        }

    _, cases = discover_scenario(
        "http://example.invalid", timeout=1, fetch_json=fetch_json, scenario="unit-explorer",
    )
    paths = {case.name: case.path for case in cases}
    assert len(paths) == len(cases) == 15
    assert paths["explorer-filters"] == "/api/unit-filters?catalogs=1"
    assert paths["explorer-armies"] == "/api/armies"
    for scope in ("profile", "loadout", "unit"):
        params = parse_qs(urlsplit(paths[f"explorer-{scope}"]).query)
        assert params["matching_scope"] == [scope]
        assert params["skill_id"] == ["12"]
        assert params["equipment_id"] == ["22"]
        assert params["counts"] == ["prospective"]
    extended = parse_qs(urlsplit(paths["explorer-extended-next"]).query)
    assert extended["extended"] == ["1"]
    assert extended["offset"] == ["50"]
    standard = parse_qs(urlsplit(paths["explorer-standard"]).query)
    assert all(standard[key] == ["0"] for key in ("mercs", "specops", "teamops", "reinforcement"))
    assert "Ranger" not in _report_path(paths["explorer-search"])


def test_report_path_redacts_synthetic_search_terms_but_keeps_bounded_parameters() -> None:
    assert _report_path("/api/search?q=Ranger") == "/api/search?q=%3Csynthetic%3E"
    assert _report_path("/api/units?limit=50") == "/api/units?limit=50"


def test_summarize_phase_reports_percentiles_rate_errors_and_status_classes() -> None:
    case = ScenarioCase("units", "/units", "page")
    results = [
        RequestResult(case, 0.010, 200, 100),
        RequestResult(case, 0.020, 200, 120),
        RequestResult(case, 0.040, 200, 140),
        RequestResult(case, 0.080, 503, 20, "http-503"),
    ]

    report = summarize_phase(
        results,
        name="steady",
        concurrency=2,
        requested_seconds=2.0,
        elapsed_seconds=2.0,
    )

    assert report["requests"] == 4
    assert report["successes"] == 3
    assert report["errors"] == 1
    assert report["errorRate"] == pytest.approx(0.25)
    assert report["requestsPerSecond"] == pytest.approx(2.0)
    assert report["responseBytes"] == 380
    assert report["statusClasses"] == {"2xx": 3, "5xx": 1}
    assert report["errorTypes"] == {"http-503": 1}
    assert report["latency"] == {
        "p50Ms": 20.0,
        "p95Ms": 40.0,
        "p99Ms": 40.0,
        "meanMs": pytest.approx(70 / 3),
        "minMs": 10.0,
        "maxMs": 40.0,
    }


def test_run_phase_supports_deterministic_request_limit() -> None:
    cases = [
        ScenarioCase("page", "/units", "page"),
        ScenarioCase("api", "/api/units", "api"),
    ]

    def requester(_base_url: str, case: ScenarioCase) -> RequestResult:
        return RequestResult(case, 0.001, 200, 10)

    results, elapsed = run_phase(
        "http://example.invalid",
        cases,
        concurrency=3,
        duration_seconds=1.0,
        timeout=1.0,
        requester=requester,
        request_limit=7,
    )

    assert len(results) == 7
    assert [result.case.name for result in results] == [
        "page",
        "api",
        "page",
        "api",
        "page",
        "api",
        "page",
    ]
    assert elapsed > 0


@pytest.mark.parametrize("first_error", [False, True])
def test_first_access_precedes_discovery_and_warmup(
    monkeypatch: pytest.MonkeyPatch, first_error: bool,
) -> None:
    calls: list[str] = []

    def phase(_url, cases, *, concurrency, duration_seconds, timeout, request_limit=None):
        assert len(cases) == 1
        case = cases[0]
        assert case.path == "/api/units/minutemen"
        calls.append("first" if request_limit is not None else "load")
        if request_limit is not None:
            assert request_limit == concurrency == 3
            assert duration_seconds == 0
        error = first_error and request_limit is not None
        return [
            RequestResult(case, 0.01, 503 if error else 200, 10, "http-503" if error else None)
        ] * concurrency, 0.1

    def fetch(_url, path, *, timeout):
        calls.append("identity")
        assert path == "/api/version"
        return {"version": "test", "snapshot_revision": "snapshot", "static_revision": "static"}

    def warm(_url, cases, *, passes, timeout):
        calls.append("warm")
        return [RequestResult(cases[0], 0.01, 200, 10)] * passes

    module = "tools.performance.capacity_test"
    monkeypatch.setattr(f"{module}.run_phase", phase)
    monkeypatch.setattr(f"{module}._fetch_json", fetch)
    monkeypatch.setattr(f"{module}._warm_scenario", warm)
    report = capacity_test(
        "http://example.invalid", timeout=1, warmup_passes=2, steady_seconds=1,
        steady_concurrency=3, burst_seconds=1, burst_concurrency=4,
        first_access_case="unit-detail",
    )
    assert calls == (
        ["first", "identity"] if first_error else ["first", "identity", "warm", "load", "load"]
    )
    assert report["scenario"]["name"] == "first-access"
    assert report["scenario"]["warmupPasses"] == (0 if first_error else 2)
    assert [p["name"] for p in report["phases"]] == (
        ["first-access"] if first_error else ["first-access", "steady", "burst"]
    )
    first = report["phases"][0]
    assert first["requestedRequests"] == first["requests"] == 3
    assert first["errors"] == (3 if first_error else 0)


def test_base_url_rejects_credentials_query_and_non_http_scheme() -> None:
    assert _base_url("https://example.invalid/path/") == "https://example.invalid/path"
    with pytest.raises(argparse.ArgumentTypeError):
        _base_url("file:///tmp/app")
    with pytest.raises(argparse.ArgumentTypeError):
        _base_url("https://user:secret@example.invalid")
    with pytest.raises(argparse.ArgumentTypeError):
        _base_url("https://example.invalid/?x=1")


def test_main_writes_report_and_fails_when_load_phase_has_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {
        "format": "InfinityDB HTTP capacity test",
        "formatVersion": 1,
        "startedAt": "2026-10-06T00:00:00+00:00",
        "client": {"python": "3.11", "platform": "test"},
        "target": {
            "baseUrl": "http://example.invalid",
            "version": "0.10.0+dev",
            "snapshotRevision": "snapshot-1",
            "staticRevision": "static-1",
            "searchQuery": "Ranger",
        },
        "scenario": {"warmupPasses": 1, "cases": []},
        "phases": [
            {
                "name": "steady",
                "concurrency": 1,
                "requests": 10,
                "errors": 0,
                "errorRate": 0.0,
                "requestsPerSecond": 5.0,
                "latency": {"p50Ms": 10.0, "p95Ms": 20.0, "p99Ms": 30.0},
            },
            {
                "name": "burst",
                "concurrency": 2,
                "requests": 10,
                "errors": 1,
                "errorRate": 0.1,
                "requestsPerSecond": 8.0,
                "latency": {"p50Ms": 15.0, "p95Ms": 25.0, "p99Ms": 35.0},
            },
        ],
    }
    monkeypatch.setattr(
        "tools.performance.capacity_test.capacity_test", lambda *_args, **_kwargs: report
    )
    output = tmp_path / "capacity.json"

    assert main(["http://example.invalid", "--output", str(output)]) == 1

    assert json.loads(output.read_text(encoding="utf-8")) == report
    stdout = capsys.readouterr().out
    assert "Steady: concurrency 1 | 5.0 req/s | 0.00% errors" in stdout
    assert "Burst: concurrency 2 | 8.0 req/s | 10.00% errors" in stdout
    assert f"Report: {output}" in stdout
