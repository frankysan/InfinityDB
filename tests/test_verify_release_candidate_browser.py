"""Fail-closed release-candidate identity and browser acceptance gate."""

from __future__ import annotations

import hashlib
import json
import shutil
from io import BytesIO
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from unittest.mock import Mock, patch
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db import __version__
from infinity_db.snapshot_revision import database_set_snapshot_revision
from infinity_db.web import create_app
from tools.report_reference_baseline import ReferenceBaselineError, build_baseline
from tools.verify_release_candidate_browser import (
    ReleaseCandidateError,
    local_revision,
    local_static_revision,
    main,
    verify_release_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/army.db"
RULES_DB = ROOT / "data/generated/rules_n5.db"
STATIC_ASSET_REVISION = local_static_revision(ARMY_DB)


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


def _copy_runtime_pair(tmp_path: Path, *, include_profile: bool) -> tuple[Path, Path, Path]:
    army, rules = tmp_path / "army.db", tmp_path / "rules_n5.db"
    profile = tmp_path / "weapon-profile-sources.json"
    shutil.copyfile(ARMY_DB, army)
    shutil.copyfile(RULES_DB, rules)
    if include_profile:
        profile.write_text("obsolete and invalid sidecar", encoding="utf-8")
    return army, rules, profile


@pytest.mark.parametrize("layout", ("attached", "absent", "independent-rules"))
def test_release_identity_matches_runtime_publication_layouts(
    tmp_path: Path, layout: str,
) -> None:
    army, rules, profile = _copy_runtime_pair(tmp_path, include_profile=layout != "absent")
    if layout == "independent-rules":
        other = tmp_path / "other"
        other.mkdir()
        independent_rules = other / rules.name
        shutil.copyfile(rules, independent_rules)
        rules = independent_rules

    army_sha = hashlib.sha256(army.read_bytes()).hexdigest()
    rules_sha = hashlib.sha256(rules.read_bytes()).hexdigest()
    expected = database_set_snapshot_revision({army.name: army_sha, rules.name: rules_sha})
    profile_sha = rules_sha

    app = create_app(army, rules_database_path=rules)
    report = build_baseline(army, rules)
    assert report["weaponProfilePublicationSha256"] == profile_sha
    assert report["runtimeSnapshotRevision"] == expected
    assert app.snapshot_revision == expected
    assert local_revision(army, rules) == expected


def test_runtime_snapshot_without_rules_uses_absent_artifact_markers(tmp_path: Path) -> None:
    army = tmp_path / "army.db"
    shutil.copyfile(ARMY_DB, army)
    army_sha = hashlib.sha256(army.read_bytes()).hexdigest()
    expected = database_set_snapshot_revision({army.name: army_sha})
    assert create_app(army).snapshot_revision == expected


class _VersionResponse(BytesIO):
    status = 200


def test_release_preflight_rejects_changed_database_bytes(tmp_path: Path) -> None:
    army, rules, profile = _copy_runtime_pair(tmp_path, include_profile=True)
    previous_app = create_app(army, rules_database_path=rules)
    previous_report = build_baseline(army, rules)

    content = bytearray(rules.read_bytes())
    content[96:100] = (3040000).to_bytes(4, "big")
    rules.write_bytes(content)
    changed_app = create_app(army, rules_database_path=rules)
    changed_report = build_baseline(army, rules)
    changed_sha = hashlib.sha256(rules.read_bytes()).hexdigest()
    assert changed_report["weaponProfilePublicationSha256"] == changed_sha
    assert changed_report["runtimeSnapshotRevision"] == changed_app.snapshot_revision
    assert changed_app.snapshot_revision == local_revision(army, rules)
    assert previous_report["runtimeSnapshotRevision"] == previous_app.snapshot_revision
    assert previous_app.snapshot_revision != changed_app.snapshot_revision

    payload = {
        "snapshot_revision": previous_app.snapshot_revision,
        "version": __version__,
        "static_revision": STATIC_ASSET_REVISION,
    }
    browser = Mock()
    with patch(
        "tools.report_reference_baseline.urlopen",
        return_value=_VersionResponse(json.dumps(payload).encode()),
    ):
        with pytest.raises(ReleaseCandidateError, match="snapshot preflight failed"):
            verify_release_candidate(
                "http://127.0.0.1:8000", expected_version=__version__,
                army_db=army, rules_db=rules, browser_check=browser,
            )
    browser.assert_not_called()


def test_release_identity_rejects_corrupt_embedded_weapon_publication(tmp_path: Path) -> None:
    import sqlite3
    army, rules, _ = _copy_runtime_pair(tmp_path, include_profile=True)
    with sqlite3.connect(rules) as connection:
        connection.execute("UPDATE weapon_chart_profile_metadata SET content_sha256=?", ("0" * 64,))
    with pytest.raises(ValueError, match="fingerprint differs"):
        create_app(army, rules_database_path=rules)
    with pytest.raises(ReferenceBaselineError, match="Weapon-profile publication"):
        build_baseline(army, rules)
    browser = Mock()
    with pytest.raises(ReleaseCandidateError, match="Weapon-profile publication"):
        verify_release_candidate(
            "http://127.0.0.1:8000", expected_version=__version__,
            army_db=army, rules_db=rules, browser_check=browser,
        )
    browser.assert_not_called()


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


def test_release_gate_runs_real_local_chromium_when_available(
    chromium_test_slot: None,
) -> None:
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
