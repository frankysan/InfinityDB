"""Fail-closed release-candidate identity and browser acceptance gate."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from unittest.mock import Mock, patch
from urllib.error import URLError
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db import __version__
from infinity_db.database_set import COMPLETE_RUNTIME_FILES
from infinity_db.snapshot_revision import database_set_snapshot_revision
from infinity_db.web import create_app, create_app_from_database_set
from tools import verify_release_candidate_browser as candidate_cli
from tools.served_runtime import ServedRuntimeError
from tools.verify_release_candidate_browser import (
    ReleaseCandidateError,
    local_revision,
    local_static_revision,
    main,
    verify_release_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "data/generated"
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


def _copy_runtime_set(tmp_path: Path) -> Path:
    for name in COMPLETE_RUNTIME_FILES:
        shutil.copyfile(DB_DIR / name, tmp_path / name)
    return tmp_path


@pytest.mark.parametrize("layout", ("attached", "absent"))
def test_release_identity_matches_runtime_publication_layouts(
    tmp_path: Path, layout: str,
) -> None:
    directory = _copy_runtime_set(tmp_path)
    if layout == "attached":
        (directory / "weapon-profile-sources.json").write_text("obsolete and invalid sidecar")
    expected = database_set_snapshot_revision({
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in COMPLETE_RUNTIME_FILES
    })
    app = create_app_from_database_set(directory)
    assert app.snapshot_revision == expected
    assert local_revision(directory) == expected


def test_runtime_snapshot_without_rules_uses_absent_artifact_markers(tmp_path: Path) -> None:
    army = tmp_path / "army.db"
    shutil.copyfile(ARMY_DB, army)
    army_sha = hashlib.sha256(army.read_bytes()).hexdigest()
    expected = database_set_snapshot_revision({army.name: army_sha})
    assert create_app(army).snapshot_revision == expected


class _VersionResponse(BytesIO):
    status = 200


class _UnavailableVersionResponse(BytesIO):
    status = 503


def test_release_verifier_import_does_not_load_reference_reporter() -> None:
    result = subprocess.run(
        [
            sys.executable, "-c",
            "import sys; import tools.verify_release_candidate_browser; "
            "assert 'tools.report_reference_baseline' not in sys.modules",
        ],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("changed_file", ("rules_n5.db", "its_18.db"))
def test_release_preflight_rejects_changed_database_bytes(
    tmp_path: Path, changed_file: str,
) -> None:
    directory = _copy_runtime_set(tmp_path)
    previous_app = create_app_from_database_set(directory)
    changed = directory / changed_file
    content = bytearray(changed.read_bytes())
    content[96:100] = (3040000).to_bytes(4, "big")
    changed.write_bytes(content)
    changed_app = create_app_from_database_set(directory)
    assert changed_app.snapshot_revision == local_revision(directory)
    assert previous_app.snapshot_revision != changed_app.snapshot_revision

    payload = {
        "snapshot_revision": previous_app.snapshot_revision,
        "version": __version__,
        "static_revision": STATIC_ASSET_REVISION,
    }
    browser = Mock()
    with patch(
        "tools.served_runtime.urlopen",
        return_value=_VersionResponse(json.dumps(payload).encode()),
    ):
        with pytest.raises(ReleaseCandidateError, match="snapshot preflight failed"):
            verify_release_candidate(
                "http://127.0.0.1:8000", expected_version=__version__,
                db_dir=directory, browser_check=browser,
            )
    browser.assert_not_called()


def test_release_identity_rejects_corrupt_embedded_weapon_publication(tmp_path: Path) -> None:
    directory = _copy_runtime_set(tmp_path)
    with sqlite3.connect(directory / "rules_n5.db") as connection:
        connection.execute("UPDATE weapon_chart_profile_metadata SET content_sha256=?", ("0" * 64,))
    with pytest.raises(ValueError, match="fingerprint differs"):
        create_app_from_database_set(directory)
    browser = Mock()
    with pytest.raises(ReleaseCandidateError, match="fingerprint differs"):
        verify_release_candidate(
            "http://127.0.0.1:8000", expected_version=__version__,
            db_dir=directory, browser_check=browser,
        )
    browser.assert_not_called()


@pytest.mark.parametrize("missing", sorted(COMPLETE_RUNTIME_FILES))
def test_release_gate_rejects_incomplete_set_before_network_or_browser(
    tmp_path: Path, missing: str,
) -> None:
    directory = _copy_runtime_set(tmp_path)
    (directory / missing).unlink()
    browser = Mock()
    with patch("tools.verify_release_candidate_browser.verify_served_runtime") as served:
        with pytest.raises(ReleaseCandidateError, match=missing):
            verify_release_candidate(
                "https://example.org", expected_version=__version__,
                db_dir=directory, browser_check=browser,
            )
    served.assert_not_called()
    browser.assert_not_called()


@pytest.mark.parametrize("invalid", ("corrupt", "schema", "provenance", "source"))
def test_release_gate_rejects_invalid_its_before_network_or_browser(
    tmp_path: Path, invalid: str,
) -> None:
    directory = _copy_runtime_set(tmp_path)
    its = directory / "its_18.db"
    if invalid == "corrupt":
        its.write_bytes(b"invalid SQLite database")
    elif invalid == "source":
        from infinity_db.its_season_database import build_its_database

        source = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"
        other_source = directory / "different-source.json"
        other_source.write_bytes(source.read_bytes() + b"\n")
        build_its_database(other_source, its)
    else:
        with sqlite3.connect(its) as connection:
            if invalid == "schema":
                connection.execute("PRAGMA user_version=999")
            else:
                connection.execute(
                    "UPDATE __its_metadata SET value=? WHERE key='buildId'",
                    (json.dumps("0" * 64),),
                )
    browser = Mock()
    with patch("tools.verify_release_candidate_browser.verify_served_runtime") as served:
        with pytest.raises(ReleaseCandidateError, match="complete release database set"):
            verify_release_candidate(
                "https://example.org", expected_version=__version__,
                db_dir=directory, browser_check=browser,
            )
    served.assert_not_called()
    browser.assert_not_called()


def test_release_gate_rejects_local_its_drift_during_browser(tmp_path: Path) -> None:
    directory = _copy_runtime_set(tmp_path)
    observed = {
        "snapshotRevision": local_revision(directory), "appVersion": __version__,
        "staticRevision": STATIC_ASSET_REVISION,
    }

    def change_its(origin: str, **kwargs: object) -> dict:
        path = directory / "its_18.db"
        content = bytearray(path.read_bytes())
        content[96:100] = (3040000).to_bytes(4, "big")
        path.write_bytes(content)
        return _browser_ok(origin, slugs=("dragoes",), widths=(390,), channel=None)

    with patch(
        "tools.verify_release_candidate_browser.verify_served_runtime", return_value=observed,
    ) as served:
        with pytest.raises(ReleaseCandidateError, match="Local candidate changed"):
            verify_release_candidate(
                "https://example.org", expected_version=__version__, db_dir=directory,
                slugs=("dragoes",), widths=(390,), browser_check=change_its,
            )
    assert served.call_count == 1


def test_release_gate_accepts_exact_local_runtime_before_and_after_browser() -> None:
    app = create_app_from_database_set(DB_DIR)

    class ThreadedServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadedServer,
        handler_class=QuietHandler,
    )
    origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = verify_release_candidate(
            origin,
            expected_version=__version__,
            db_dir=DB_DIR,
            slugs=("dragoes",), widths=(390, 768),
            browser_check=_browser_ok,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result["snapshotRevision"] == local_revision(DB_DIR)
    assert result["snapshotRevision"] == app.snapshot_revision
    assert result["staticRevision"] == STATIC_ASSET_REVISION
    assert result["servedVersion"] == result["postflightVersion"]
    assert result["servedVersion"] == {
        "versionUrl": f"{origin}/api/version",
        "snapshotRevision": app.snapshot_revision,
        "appVersion": __version__,
        "staticRevision": STATIC_ASSET_REVISION,
        "status": "exact-runtime-revision-match-not-source-completeness",
    }
    assert result["browser"]["passed"] == result["browser"]["total"] == 2


@pytest.mark.parametrize(
    "origin",
    (
        "file:///data/generated/army.db",
        "http://user:pass@localhost:8000",
        "http://localhost:8000/api",
        "http://localhost:8000?skip=1",
        "http://localhost:8000#fragment",
    ),
)
def test_release_gate_rejects_invalid_server_origin_before_network(origin: str) -> None:
    browser = Mock()
    with patch("tools.served_runtime.urlopen") as opened:
        with pytest.raises(ReleaseCandidateError, match="Server base URL"):
            verify_release_candidate(
                origin, expected_version=__version__, db_dir=DB_DIR, browser_check=browser,
            )
    opened.assert_not_called()
    browser.assert_not_called()


@pytest.mark.parametrize(
    ("response", "error"),
    (
        (_UnavailableVersionResponse(b""), "HTTP 503"),
        (_VersionResponse(b"{"), "Could not verify runtime version"),
        (_VersionResponse(b"[]"), "did not return an object"),
    ),
)
def test_release_gate_rejects_invalid_version_response(
    response: BytesIO, error: str,
) -> None:
    browser = Mock()
    with patch("tools.served_runtime.urlopen", return_value=response):
        with pytest.raises(ReleaseCandidateError, match=error):
            verify_release_candidate(
                "https://example.org", expected_version=__version__,
                db_dir=DB_DIR, browser_check=browser,
            )
    browser.assert_not_called()


def test_release_gate_reports_version_network_failure() -> None:
    browser = Mock()
    with patch("tools.served_runtime.urlopen", side_effect=URLError("unavailable")):
        with pytest.raises(ReleaseCandidateError, match="Could not verify runtime version"):
            verify_release_candidate(
                "https://example.org", expected_version=__version__,
                db_dir=DB_DIR, browser_check=browser,
            )
    browser.assert_not_called()


def test_release_gate_rejects_version_network_failure_after_browser() -> None:
    payload = {
        "snapshot_revision": local_revision(DB_DIR),
        "version": __version__,
        "static_revision": STATIC_ASSET_REVISION,
    }
    browser = Mock(side_effect=_browser_ok)
    with patch(
        "tools.served_runtime.urlopen",
        side_effect=[_VersionResponse(json.dumps(payload).encode()), URLError("unavailable")],
    ):
        with pytest.raises(ReleaseCandidateError, match="Could not verify runtime version"):
            verify_release_candidate(
                "https://example.org", expected_version=__version__, db_dir=DB_DIR,
                slugs=("dragoes",), widths=(390,), browser_check=browser,
            )
    browser.assert_called_once()


def test_release_gate_runs_real_local_chromium_when_available(
    chromium_test_slot: None,
) -> None:
    """Exercise exact identity preflight, real DOM, and identity postflight together."""
    pytest.importorskip("playwright.sync_api")
    app = create_app_from_database_set(DB_DIR)

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
                expected_version=__version__, db_dir=DB_DIR,
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
        "tools.verify_release_candidate_browser.verify_served_runtime",
        side_effect=ServedRuntimeError("runtime snapshot differs"),
    ):
        with pytest.raises(ReleaseCandidateError, match="snapshot preflight failed"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                db_dir=DB_DIR, browser_check=browser,
            )
    browser.assert_not_called()


@pytest.mark.parametrize("wrong_field", ["version", "static"])
def test_release_gate_rejects_wrong_version_or_assets_before_browser(
    wrong_field: str,
) -> None:
    observed = {
        "snapshotRevision": local_revision(DB_DIR),
        "appVersion": "1.0.0",
        "staticRevision": STATIC_ASSET_REVISION,
    }
    if wrong_field == "version":
        observed["appVersion"] = "0.10.1"
    else:
        observed["staticRevision"] = "stale"
    browser = Mock()
    with patch(
        "tools.verify_release_candidate_browser.verify_served_runtime",
        return_value=observed,
    ):
        with pytest.raises(ReleaseCandidateError, match="mismatch"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                db_dir=DB_DIR, browser_check=browser,
            )
    browser.assert_not_called()


def test_release_gate_rejects_failed_browser_acceptance() -> None:
    observed = {
        "snapshotRevision": local_revision(DB_DIR),
        "appVersion": "1.0.0", "staticRevision": STATIC_ASSET_REVISION,
    }
    browser = Mock(return_value={
        "passed": 0, "total": 1,
        "results": [{"unit": "dragoes", "width": 390,
                     "status": "failed", "error": "missing skill"}],
    })
    with patch(
        "tools.verify_release_candidate_browser.verify_served_runtime",
        return_value=observed,
    ) as served:
        with pytest.raises(ReleaseCandidateError, match="missing skill"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                db_dir=DB_DIR,
                slugs=("dragoes",), widths=(390,), browser_check=browser,
            )
    assert served.call_count == 1
    assert browser.call_count == 1


def test_release_gate_rejects_postflight_drift() -> None:
    observed = {
        "snapshotRevision": local_revision(DB_DIR),
        "appVersion": "1.0.0", "staticRevision": STATIC_ASSET_REVISION,
    }
    with patch(
        "tools.verify_release_candidate_browser._check_served",
        side_effect=[observed, {**observed, "appVersion": "1.0.1"}],
    ) as checked:
        with pytest.raises(ReleaseCandidateError, match="changed during"):
            verify_release_candidate(
                "https://example.org", expected_version="1.0.0",
                db_dir=DB_DIR,
                slugs=("dragoes",), widths=(390,), browser_check=_browser_ok,
            )
    assert checked.call_count == 2


def test_release_gate_rejects_missing_database_and_empty_version(tmp_path: Path) -> None:
    browser = Mock()
    with pytest.raises(ReleaseCandidateError, match="release version"):
        verify_release_candidate(
            "https://example.org", expected_version="",
            db_dir=DB_DIR, browser_check=browser,
        )
    with pytest.raises(ReleaseCandidateError, match="directory does not exist"):
        verify_release_candidate(
            "https://example.org", expected_version="1.0.0",
            db_dir=tmp_path / "missing",
            browser_check=browser,
        )
    with pytest.raises(ReleaseCandidateError, match="Browser widths"):
        verify_release_candidate(
            "https://example.org", expected_version="1.0.0",
            db_dir=DB_DIR,
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


@pytest.mark.parametrize("filename", ("acceptance.json", "nested/acceptance.json"))
def test_release_gate_cli_refuses_existing_receipt_before_browser(
    tmp_path: Path, filename: str, capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / filename
    output.parent.mkdir(parents=True, exist_ok=True)
    original = b'{"accepted":"earlier run"}\n'
    output.write_bytes(original)
    with patch(
        "tools.verify_release_candidate_browser.verify_release_candidate",
    ) as browser_gate:
        assert main([
            "--base-url", "https://example.org",
            "--expected-version", "1.0.0",
            "--json-output", str(output),
        ]) == 1
    browser_gate.assert_not_called()
    assert output.read_bytes() == original
    assert "already exists" in capsys.readouterr().err


def test_release_gate_cli_rejects_dangling_output_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "acceptance.json"
    # Portable Windows test: creating symlinks may require elevated permissions.
    monkeypatch.setattr(type(output), "is_symlink", lambda path: path == output)
    with patch(
        "tools.verify_release_candidate_browser.verify_release_candidate",
    ) as browser_gate:
        assert main([
            "--base-url", "https://example.org",
            "--expected-version", "1.0.0",
            "--json-output", str(output),
        ]) == 1
    browser_gate.assert_not_called()
    assert not output.exists()


def test_release_gate_cli_refuses_collision_arriving_during_browser_checks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "acceptance.json"
    original = b"another writer's successful acceptance\n"

    def browser_gate(*args: object, **kwargs: object) -> dict[str, object]:
        output.write_bytes(original)
        return {
            "expectedVersion": "1.0.0", "snapshotRevision": "a" * 64,
            "browser": {"passed": 1, "total": 1},
        }

    with patch(
        "tools.verify_release_candidate_browser.verify_release_candidate",
        side_effect=browser_gate,
    ):
        assert main([
            "--base-url", "https://example.org",
            "--expected-version", "1.0.0",
            "--json-output", str(output),
        ]) == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert "acceptance PASS" not in captured.out
    assert output.read_bytes() == original


def test_release_candidate_receipt_writer_uses_exclusive_creation(
    tmp_path: Path,
) -> None:
    output = tmp_path / "acceptance.json"
    original = b"immutable evidence\n"
    output.write_bytes(original)
    with pytest.raises(ReleaseCandidateError, match="already exists"):
        candidate_cli._write_success_receipt(output, {"status": "passed"})
    assert output.read_bytes() == original


def test_release_gate_cli_write_failure_blocks_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "acceptance.json"
    report = {
        "expectedVersion": "1.0.0", "snapshotRevision": "a" * 64,
        "browser": {"passed": 1, "total": 1},
    }
    with (
        patch("tools.verify_release_candidate_browser.verify_release_candidate",
              return_value=report),
        patch("tools.verify_release_candidate_browser._write_success_receipt",
              side_effect=OSError("disk full")),
    ):
        assert main([
            "--base-url", "https://example.org",
            "--expected-version", "1.0.0",
            "--json-output", str(output),
        ]) == 1
    captured = capsys.readouterr()
    assert "disk full" in captured.err
    assert "acceptance PASS" not in captured.out
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
    ) as verify_candidate:
        assert main([
            "--base-url", "https://example.org",
            "--expected-version", "1.0.0",
            "--db-dir", str(tmp_path),
            "--json-output", str(output),
        ]) == 0
    assert verify_candidate.call_args.kwargs["db_dir"] == tmp_path
    assert json.loads(output.read_text(encoding="utf-8")) == report
