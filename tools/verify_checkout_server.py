"""Verify the real checkout CLI server against the pinned P1 runtime baseline.

Launches an ephemeral loopback-only server and stops it even on failure.
No database builds, writes to tracked files, external network calls or deployment.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from infinity_db.database_set import validate_database_set
from infinity_db.snapshot_revision import database_set_snapshot_revision
from tools.runtime_semantic_baseline import DEFAULT_BASELINE, capture, check

ROOT = Path(__file__).resolve().parents[1]
LEGACY_FILES = ("deployed-objects.json", "variant-usage.json", "weapon-profile-sources.json")


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _get_json(origin: str, path: str) -> dict[str, Any]:
    with urlopen(origin + path, timeout=12) as response:
        if response.status != 200:
            raise ValueError(f"{path}: unexpected HTTP {response.status}")
        document = json.load(response)
    if not isinstance(document, dict):
        raise ValueError(f"{path}: expected a JSON document")
    return document


def verify_checkout_server(
    db_dir: Path | None = None, *, baseline: Path = DEFAULT_BASELINE,
) -> int:
    """Prove CLI startup, health, exact DB revision and HTTP semantic parity."""
    selected = (db_dir if db_dir is not None else ROOT / "data/generated").resolve()
    report = validate_database_set(selected, require_complete=True)
    # Leftover ignored sidecars may exist in old checkout directories. They
    # must not be required or consulted; only the selected SQLite pair counts.
    ignored_sidecars = [name for name in LEGACY_FILES if (selected / name).exists()]
    expected_revision = database_set_snapshot_revision(report["sha256"])
    expected = json.loads(baseline.read_text(encoding="utf-8"))
    paths = tuple(row["path"] for row in expected["probes"])

    port = _port()
    origin = f"http://127.0.0.1:{port}"
    command = [
        sys.executable, "-m", "infinity_db", "serve",
        "--host", "127.0.0.1", "--port", str(port),
    ]
    if db_dir is not None:
        command.extend(("--db-dir", str(selected)))

    environment = dict(os.environ)
    # Deliberately prove the CLI's default selection, not an inherited override.
    environment.pop("INFINITY_DB_DB_DIR", None)
    environment.pop("INFINITY_DB_DATABASE", None)
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        server = subprocess.Popen(
            command, cwd=ROOT, env=environment,
            stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 35
            while True:
                if server.poll() is not None:
                    raise ValueError(f"Checkout server exited with {server.returncode}")
                try:
                    with urlopen(origin + "/internal/health", timeout=12) as response:
                        health = response.read()
                        if response.status != 200 or health != b"ok\n":
                            raise ValueError("Checkout server health endpoint is unhealthy")
                    break
                except (OSError, ValueError):
                    if time.monotonic() >= deadline:
                        raise ValueError("Checkout server did not become healthy") from None
                    time.sleep(0.25)
            version = _get_json(origin, "/api/version")
            if version.get("snapshot_revision") != expected_revision:
                raise ValueError("Checkout server selected unexpected database bytes")

            def transport(environ: dict[str, Any], start_response: Any) -> list[bytes]:
                path = environ["PATH_INFO"]
                if environ.get("QUERY_STRING"):
                    path += "?" + environ["QUERY_STRING"]
                with urlopen(origin + path, timeout=15) as response:
                    start_response(
                        f"{response.status} {response.reason}",
                        list(response.headers.items()),
                    )
                    return [response.read()]

            observed = capture(
                transport, paths=paths,
                route_aliases={
                    "/static/restrictions-reference.json": "/api/restrictions/chart",
                },
            )
            count = check(expected, observed)
            # Guard against modifications to the selected immutable input pair.
            after = validate_database_set(selected, require_complete=True)
            if after["sha256"] != report["sha256"]:
                raise ValueError("Runtime database bytes changed during checkout acceptance")
            print(
                "Checkout CLI server parity PASS: "
                f"{count} pinned paths; health=ok; "
                f"snapshot={expected_revision}; databases={sorted(report['sha256'])}; "
                f"ignored-sidecars={ignored_sidecars}"
            )
            return count
        except Exception:
            log.flush()
            log.seek(0)
            print("Checkout server output (last 2400 chars):", file=sys.stderr)
            print(log.read()[-2400:], file=sys.stderr)
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-dir", type=Path,
        help="Explicit complete set (omit to test checkout's normal default)",
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args(argv)
    try:
        verify_checkout_server(args.db_dir, baseline=args.baseline)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Checkout hosting acceptance FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
