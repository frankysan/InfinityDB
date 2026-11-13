#!/usr/bin/env python3
"""Fail-closed hosted Unit browser acceptance for an exact InfinityDB release candidate.

Runs no deployment actions. The server must match the selected immutable
complete Army/Rules/ITS database set, embedded citations, static fingerprint
and explicit release version before and after the browser checks.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.database_set import ARMY_DATABASE_FILENAME, validate_database_set
from infinity_db.snapshot_revision import database_set_snapshot_revision
from infinity_db.symbol_catalog import SymbolCatalog
from infinity_db.web.presentation import static_asset_revision
from tools.served_runtime import ServedRuntimeError, verify_served_runtime
from tools.verify_unit_skill_presentation_browser import (
    DEFAULT_SLUGS,
    WIDTHS,
    verify,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReleaseCandidateError(ValueError):
    """The served release candidate cannot be accepted."""


def local_static_revision(army_db: Path) -> str:
    """Resolve the candidate's selected mapping revision and actual package assets."""
    return static_asset_revision(SymbolCatalog(publication=Database(army_db).symbol_publication()))


def local_revision(db_dir: Path) -> str:
    """Validate and fingerprint the complete set through the serving contract."""
    try:
        report = validate_database_set(db_dir, require_complete=True)
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise ReleaseCandidateError(
            f"Cannot verify complete release database set: {exc}"
        ) from exc
    return database_set_snapshot_revision(report["sha256"])


def _check_served(
    origin: str, expected_revision: str, expected_version: str,
    expected_static_revision: str,
) -> dict[str, str]:
    try:
        observed = verify_served_runtime(expected_revision, origin)
    except ServedRuntimeError as exc:
        raise ReleaseCandidateError(f"Deployed snapshot preflight failed: {exc}") from exc
    if observed["appVersion"] != expected_version:
        raise ReleaseCandidateError(
            f"Deployed version mismatch: expected {expected_version!r}, "
            f"received {observed['appVersion']!r}"
        )
    if observed["staticRevision"] != expected_static_revision:
        raise ReleaseCandidateError(
            f"Deployed static assets mismatch: expected "
            f"{expected_static_revision!r}, received {observed['staticRevision']!r}"
        )
    return observed


def verify_release_candidate(
    origin: str, *, expected_version: str,
    db_dir: Path,
    slugs: tuple[str, ...] = DEFAULT_SLUGS,
    widths: tuple[int, ...] = WIDTHS,
    channel: str | None = None,
    browser_check: Callable[..., dict[str, Any]] = verify,
) -> dict[str, Any]:
    """Run browser checks only for the exact candidate, and recheck after completion."""
    if not expected_version or not expected_version.strip():
        raise ReleaseCandidateError("An explicit expected release version is required")
    if not slugs or any(not slug.strip() for slug in slugs):
        raise ReleaseCandidateError("At least one nonempty browser Unit is required")
    if not widths or any(width < 240 or width > 3840 for width in widths):
        raise ReleaseCandidateError("Browser widths must be between 240 and 3840 px")
    db_dir = Path(db_dir).resolve()
    revision = local_revision(db_dir)
    static_revision = local_static_revision(db_dir / ARMY_DATABASE_FILENAME)
    before = _check_served(
        origin, revision, expected_version, static_revision
    )
    browser = browser_check(
        origin, slugs=slugs, widths=widths, channel=channel
    )
    if (
        browser.get("passed") != browser.get("total")
        or browser.get("total") != len(slugs) * len(widths)
    ):
        failed = [
            {"unit": row.get("unit"), "width": row.get("width"),
             "error": row.get("error", "not passed")}
            for row in browser.get("results", ())
            if row.get("status") != "passed"
        ]
        raise ReleaseCandidateError(
            f"Hosted browser acceptance failed: "
            f"{browser.get('passed')}/{browser.get('total')} passed; "
            f"failures={failed[:12]!r}"
        )
    if (
        local_revision(db_dir) != revision
        or local_static_revision(db_dir / ARMY_DATABASE_FILENAME) != static_revision
    ):
        raise ReleaseCandidateError("Local candidate changed during browser acceptance")
    after = _check_served(
        origin, revision, expected_version, static_revision
    )
    if (before["snapshotRevision"], before["appVersion"], before["staticRevision"]) != (
        after["snapshotRevision"], after["appVersion"], after["staticRevision"]
    ):
        raise ReleaseCandidateError("Served candidate changed during browser acceptance")
    return {
        "status": "exact-runtime-and-representative-browser-match",
        "scope": "complete Army/Rules/ITS identity and selected Unit-detail browser cases, "
        "not full reference completeness",
        "origin": origin.rstrip("/"),
        "expectedVersion": expected_version,
        "snapshotRevision": revision,
        "staticRevision": static_revision,
        "servedVersion": before,
        "browser": browser,
        "postflightVersion": after,
    }


def _check_fresh_receipt(path: Path) -> None:
    """Do not replace earlier release acceptance, including a dangling symlink."""
    if path.exists() or path.is_symlink():
        raise ReleaseCandidateError(f"Release-candidate JSON output already exists: {path}")


def _write_success_receipt(path: Path, result: dict[str, Any]) -> None:
    _check_fresh_receipt(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also prevents a later writer from replacing this receipt.
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, sort_keys=True, indent=2) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Hosted candidate HTTP(S) origin")
    parser.add_argument("--expected-version", required=True, help="Exact deployed release version")
    parser.add_argument(
        "--db-dir", type=Path, default=PROJECT_ROOT / "data/generated",
        help="One complete Army/Rules/ITS directory (default: checkout data/generated)",
    )
    parser.add_argument("--channel", help="Playwright browser channel, e.g. chrome")
    parser.add_argument("--slug", action="append", dest="slugs")
    parser.add_argument("--width", action="append", type=int, dest="widths")
    parser.add_argument(
        "--json-output", type=Path,
        help="Write new acceptance evidence only on success (existing files are rejected)",
    )
    args = parser.parse_args(argv)

    try:
        if args.json_output is not None:
            _check_fresh_receipt(args.json_output)
        result = verify_release_candidate(
            args.base_url,
            expected_version=args.expected_version,
            db_dir=args.db_dir,
            slugs=tuple(args.slugs) if args.slugs else DEFAULT_SLUGS,
            widths=tuple(args.widths) if args.widths else WIDTHS,
            channel=args.channel,
        )
        if args.json_output is not None:
            _write_success_receipt(args.json_output, result)
    except Exception as exc:
        # CLI boundary: missing Chromium, network errors, browser assertion
        # failures and output collisions must block acceptance without
        # replacing previous evidence or reporting a successful receipt.
        print(f"Release-candidate acceptance BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(
        "Release-candidate acceptance PASS: "
        f"version={result['expectedVersion']}, "
        f"snapshot={result['snapshotRevision']}, "
        f"browser={result['browser']['passed']}/{result['browser']['total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
