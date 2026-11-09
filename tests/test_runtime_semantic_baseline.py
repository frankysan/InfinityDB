"""P1.3 compact, snapshot-pinned runtime parity and guardrail tests."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.runtime_semantic_baseline import (
    DEFAULT_BASELINE,
    BaselineError,
    _artifact_identity,
    capture,
    check,
    semantic_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _fake_app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    path = environ["PATH_INFO"]
    if path in {"/api/armies", "/api/new-armies"}:
        response = {
            "sourceSnapshot": {
                "armyDatabaseSha256": "a" * 64, "rulesDatabaseSha256": "b" * 64,
                "armyArchiveSha256": "c" * 64,
            },
            "items": [{"name": "Army", "id": 1}],
        }
        body = json.dumps(response).encode()
        content_type = "application/json"
    elif path == "/":
        body = b"<html><h1>InfinityDB</h1></html>"
        content_type = "text/html"
    else:
        body = b"not found"
        content_type = "text/plain"
    start_response(
        "200 OK" if path in {"/api/armies", "/api/new-armies", "/"} else "404 Not Found",
        [("Content-Type", content_type)],
    )
    return [body]


def test_immutable_source_hash_remains_in_semantic_digest() -> None:
    original = {
        "sourceSnapshot": {
            "armyDatabaseSha256": "a", "rulesDatabaseSha256": "b",
            "exportPairSha256": "c", "armyArchiveSha256": "source",
            "sourceDate": "2026-09-01",
        },
        "items": [{"id": "skill:camouflage", "citations": [{"sha256": "pdf"}]}],
    }
    updated = {
        "sourceSnapshot": {
            **original["sourceSnapshot"], "armyDatabaseSha256": "changed",
            "rulesDatabaseSha256": "changed", "exportPairSha256": "changed",
        },
        "items": deepcopy(original["items"]),
    }
    assert semantic_payload(original) == semantic_payload(updated)
    updated["sourceSnapshot"]["armyArchiveSha256"] = "different source"
    assert semantic_payload(original) != semantic_payload(updated)
    updated["sourceSnapshot"]["armyArchiveSha256"] = "source"
    updated["items"][0]["citations"][0]["sha256"] = "different pdf"
    assert semantic_payload(original) != semantic_payload(updated)


def test_capture_preserves_source_citations_and_html_markers() -> None:
    observed = capture(_fake_app, paths=("/api/armies", "/"))
    assert [row["kind"] for row in observed["probes"]] == ["json", "html"]
    assert len(observed["probes"][0]["semanticSha256"]) == 64
    assert observed["probes"][1]["markers"] == ["<html"]
    assert "semanticSha256" not in observed["probes"][1]


def test_guard_fails_on_response_mismatch_even_if_artifact_bytes_change() -> None:
    captured = capture(_fake_app, paths=("/api/armies", "/"),
                       artifacts={"armyDbSha256": "a"})
    same_semantics = {
        **captured, "artifacts": {"armyDbSha256": "changed"},
    }
    assert check(captured, same_semantics) == 2
    with pytest.raises(BaselineError, match="artifact hashes differ"):
        check(captured, same_semantics, identical_artifacts=True)
    mismatched = json.loads(json.dumps(same_semantics))
    mismatched["probes"][0]["semanticSha256"] = "0" * 64
    with pytest.raises(BaselineError, match="/api/armies"):
        check(captured, mismatched)
    mismatched = json.loads(json.dumps(same_semantics))
    mismatched["probes"][1]["markers"] = []
    with pytest.raises(BaselineError, match="runtime responses differ"):
        check(captured, mismatched)


def test_alias_allows_an_explicitly_migrated_route_but_not_an_unpinned_path() -> None:
    source = capture(_fake_app, paths=("/api/armies",))
    migrated = capture(
        _fake_app, paths=("/api/armies",),
        route_aliases={"/api/armies": "/api/new-armies"},
    )
    assert check(source, migrated) == 1
    with pytest.raises(BaselineError, match="pinned baseline request"):
        capture(_fake_app, paths=("/api/armies",),
                route_aliases={"/api/unknown": "/api/new-armies"})


def test_guard_rejects_duplicate_or_missing_requests() -> None:
    expected = capture(_fake_app, paths=("/api/armies", "/"))
    duplicate = json.loads(json.dumps(expected))
    duplicate["probes"].append(duplicate["probes"][0])
    with pytest.raises(BaselineError, match="Duplicate baseline paths"):
        check(duplicate, expected)
    shortened = capture(_fake_app, paths=("/api/armies",))
    with pytest.raises(BaselineError, match="Probe paths differ"):
        check(expected, shortened)


def test_released_data_matches_pinned_p1_baseline() -> None:
    fixture = json.loads(DEFAULT_BASELINE.read_text(encoding="utf-8"))
    army = ROOT / "data/generated/infinity.db"
    rules = ROOT / "data/generated/rules.db"
    app = create_app(army, rules)
    observed = capture(
        app,
        paths=tuple(row["path"] for row in fixture["probes"]),
        artifacts=_artifact_identity(army, rules),
    )
    assert check(fixture, observed, identical_artifacts=True) == len(fixture["probes"])
