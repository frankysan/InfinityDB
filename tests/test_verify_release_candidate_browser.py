"""Fail-closed release-candidate identity and browser acceptance gate."""

from __future__ import annotations

import json
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from unittest.mock import Mock, patch
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db import __version__
from infinity_db.web import create_app
from infinity_db.web.presentation import STATIC_ASSET_REVISION
from tools.report_reference_baseline import ReferenceBaselineError
from tools.verify_release_candidate_browser import (
    ReleaseCandidateError,
    local_revision,
    main,
    verify_release_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"


def _browser_ok(origin: str, *, slugs: tuple[str, ...],
                widths: tuple[int, ...], channel: str | None) -> dict:
    assert origin.startswith(("http://", "https://"))
    return {
        "passed": len(slugs) * len(widths),
        "total": len(slugs) * len(widths),
        "results": [
            {"unit": slug, "width": width, "status": "passed"}
            for width in widths for slug in slugs
        ],
    }


def test_release_gate_accepts_exact_local_runtime_before_and_after_browser() -> None:
    app = create_app(ARMY_DB, rules_database_path=RULES_DB)

    class ThreadedServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadedServer,
        handler_class=QuietHandler,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = verify_release_candidate(
            f"http://127.0.0.1:{server.server_port}",
            expected_version=__version__,
            army_db=ARMY_DB, rules_db=RULES_DB,
            slugs=("dragoes",), widths=(390, 768),
            browser_check=_browser_ok,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result["snapshotRevision"] == local_revision(ARMY_DB, RULES_DB)
    assert result["snapshotRevision"] == app.snapshot_revision
    assert result["staticRevision"] == STATIC_ASSET_REVISION
    assert result["servedVersion"] == result["postflightVersion"]
    assert result["browser"]["passed"] == result["browser"]["total"] == 2


def test_release_gate_runs_real_local_chromium_when_available() -> None:
    """Exercise exact identity preflight, real DOM, and identity postflight together."""
    pytest.importorskip("playwright.sync_api")
    app = create_app(ARMY_DB, rules_database_path=RULES_DB)

    class ThreadedServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadedServer,
        handler_class=QuietHandler,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            result = verify_release_candidate(
                f"http://127.0.0.1:{server.server_port}",
                expected_version=__version__, army_db=ARMY_DB, rules_db=RULES_DB,
                slugs=("dragoes",), widths=(390,), channel="chrome",
            )
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or (
                "chrome" in str(exc).lower() and "not found" in str(exc).lower()
            ):
                pytest.skip(f"Chromium browser unavailable: {exc}")
            raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result["status"] == "exact-runtime-and-representative-browser-match"
    assert result["browser"]["passed"] == result["browser"]["total"] == 1


def test_release_gate_rejects_wrong_snapshot_before_browser() -> None:
    browser = Mock()
    with patch(
        "tools.verify_release_candidate_browser.verify_served_revision",
        side_effect=ReferenceBaselineError("source pair differs"),
    ):
        with pytest.raises(ReleaseCandidateError, match="snapshot preflight failed"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                army_db=ARMY_DB, rules_db=RULES_DB, browser_check=browser,
            )
    browser.assert_not_called()


@pytest.mark.parametrize("wrong_field", ["version", "static"])
def test_release_gate_rejects_wrong_version_or_assets_before_browser(
    wrong_field: str,
) -> None:
    observed = {
        "snapshotRevision": local_revision(ARMY_DB, RULES_DB),
        "appVersion": "1.0.0",
        "staticRevision": STATIC_ASSET_REVISION,
    }
    if wrong_field == "version":
        observed["appVersion"] = "0.10.1"
    else:
        observed["staticRevision"] = "stale"
    browser = Mock()
    with patch(
        "tools.verify_release_candidate_browser.verify_served_revision",
        return_value=observed,
    ):
        with pytest.raises(ReleaseCandidateError, match="mismatch"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                army_db=ARMY_DB, rules_db=RULES_DB, browser_check=browser,
            )
    browser.assert_not_called()


def test_release_gate_rejects_failed_browser_acceptance() -> None:
    observed = {
        "snapshotRevision": local_revision(ARMY_DB, RULES_DB),
        "appVersion": "1.0.0", "staticRevision": STATIC_ASSET_REVISION,
    }
    browser = Mock(return_value={
        "passed": 0, "total": 1,
        "results": [{"unit": "dragoes", "width": 390,
                     "status": "failed", "error": "missing skill"}],
    })
    with patch(
        "tools.verify_release_candidate_browser.verify_served_revision",
        return_value=observed,
    ) as served:
        with pytest.raises(ReleaseCandidateError, match="missing skill"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                army_db=ARMY_DB, rules_db=RULES_DB,
                slugs=("dragoes",), widths=(390,), browser_check=browser,
            )
    assert served.call_count == 1
    assert browser.call_count == 1


def test_release_gate_rejects_postflight_drift() -> None:
    observed = {
        "snapshotRevision": local_revision(ARMY_DB, RULES_DB),
        "appVersion": "1.0.0", "staticRevision": STATIC_ASSET_REVISION,
    }
    with patch(
        "tools.verify_release_candidate_browser._check_served",
        side_effect=[observed, {**observed, "appVersion": "1.0.1"}],
    ) as checked:
        with pytest.raises(ReleaseCandidateError, match="changed during"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                army_db=ARMY_DB, rules_db=RULES_DB,
                slugs=("dragoes",), widths=(390,), browser_check=_browser_ok,
            )
    assert checked.call_count == 2


def test_release_gate_rejects_missing_database_and_empty_version(tmp_path: Path) -> None:
    browser = Mock()
    with pytest.raises(ReleaseCandidateError, match="release version"):
        verify_release_candidate(
            "https://example.org", expected_version="",
            army_db=ARMY_DB, rules_db=RULES_DB, browser_check=browser,
        )
    with pytest.raises(ReleaseCandidateError, match="Missing release database"):
        verify_release_candidate(
            "https://example.org", expected_version="1.0.0",
            army_db=tmp_path / "missing.db", rules_db=RULES_DB,
            browser_check=browser,
        )
    with pytest.raises(ReleaseCandidateError, match="Browser widths"):
        verify_release_candidate(
            "https://example.org", expected_version="1.0.0",
            army_db=ARMY_DB, rules_db=RULES_DB,
            widths=(), browser_check=browser,
        )
    browser.assert_not_called()


def test_release_gate_cli_does_not_write_report_after_failure(tmp_path: Path) -> None:
    output = tmp_path / "acceptance.json"
    with patch(
        "tools.verify_release_candidate_browser.verify_release_candidate",
        side_effect=ReleaseCandidateError("deployed snapshot mismatch"),
    ):
        assert main([
            "--base-url", "https://example.org",
            "--expected-version", "1.0.0",
            "--json-output", str(output),
        ]) == 1
    assert not output.exists()


def test_release_gate_cli_writes_successful_report(tmp_path: Path) -> None:
    output = tmp_path / "acceptance.json"
    report = {
        "status": "exact-runtime-and-representative-browser-match",
        "expectedVersion": "1.0.0",
        "snapshotRevision": "a" * 64,
        "browser": {"passed": 1, "total": 1},
    }
    with patch(
        "tools.verify_release_candidate_browser.verify_release_candidate",
        return_value=report,
    ):
        assert main([
            "--base-url", "https://example.org",
            "--expected-version", "1.0.0",
            "--json-output", str(output),
        ]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == report
