"""Focused checks for the shared running-deployment smoke probe."""

from __future__ import annotations

import json
from urllib.request import Request

import pytest

from tools.ci import verify_running_deployment as smoke


class _Response:
    status = 200

    def __init__(self, value: str):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.value.encode("utf-8")


def _responses(display: str = "1.2.0"):
    return {
        "http://localhost:8080/api/version": json.dumps({
            "version": "1.2.0",
            "static_revision": "static",
            "snapshot_revision": "snapshot",
        }),
        "http://localhost:8080/": f"<footer>Version {display}</footer>",
        "http://localhost:8080/changes": "<h1>Changes</h1>",
        "http://localhost:8080/scenarios": "<h1>Scenarios</h1>",
        "http://127.0.0.1:8081/health": "ok",
        "http://127.0.0.1:8081/metrics": "# HELP infinitydb_requests",
    }


def test_running_deployment_checks_both_listeners(monkeypatch) -> None:
    responses = _responses()
    visited = []

    def fake_urlopen(url, *, timeout):
        assert timeout > 0
        visited.append(url)
        return _Response(responses[url])

    monkeypatch.setattr(smoke, "urlopen", fake_urlopen)
    identity = smoke.verify_running_deployment(
        "http://localhost:8080", "http://127.0.0.1:8081", "1.2.0",
    )
    assert identity == {
        "version": "1.2.0", "snapshot_revision": "snapshot", "static_revision": "static",
    }
    assert set(visited) == set(responses)


def test_public_host_override_applies_only_to_public_listener(monkeypatch, capsys) -> None:
    responses = _responses()
    visited = []

    def fake_urlopen(request, *, timeout):
        assert timeout > 0
        if isinstance(request, Request):
            url = request.full_url
            assert url.startswith("http://localhost:8080/")
            assert request.get_header("Host") == "infinitydb.example"
        else:
            url = request
            assert url.startswith("http://127.0.0.1:8081/")
        visited.append(url)
        return _Response(responses[url])

    monkeypatch.setattr(smoke, "urlopen", fake_urlopen)
    assert smoke.main([
        "--public-base", "http://localhost:8080",
        "--public-host", "infinitydb.example",
        "--metrics-base", "http://127.0.0.1:8081",
        "--expected-version", "1.2.0",
    ]) == 0
    assert set(visited) == set(responses)
    assert "Deployment smoke: PASS" in capsys.readouterr().out


def test_release_smoke_rejects_development_footer(monkeypatch) -> None:
    responses = _responses(display="1.2.0+dev")
    monkeypatch.setattr(smoke, "urlopen", lambda url, **kwargs: _Response(responses[url]))
    with pytest.raises(ValueError, match="expected version"):
        smoke.verify_running_deployment(
            "http://localhost:8080", "http://127.0.0.1:8081", "1.2.0",
        )


def test_smoke_rejects_missing_revision_or_health(monkeypatch) -> None:
    responses = _responses()
    responses["http://localhost:8080/api/version"] = '{"version":"1.2.0"}'
    monkeypatch.setattr(smoke, "urlopen", lambda url, **kwargs: _Response(responses[url]))
    with pytest.raises(ValueError, match="missing runtime identity"):
        smoke.verify_running_deployment("http://localhost:8080", "http://127.0.0.1:8081")

    responses = _responses()
    responses["http://127.0.0.1:8081/health"] = ""
    with pytest.raises(ValueError, match="/health"):
        smoke.verify_running_deployment("http://localhost:8080", "http://127.0.0.1:8081")
