"""Verify the running release/test stack through its public and metrics listeners."""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _read(base: str, path: str, *, host: str | None = None) -> str:
    url = base.rstrip("/") + path
    request = Request(url, headers={"Host": host}) if host is not None else url
    with urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise ValueError(f"{path}: HTTP {response.status}")
        return response.read().decode("utf-8")


def verify_running_deployment(
    public_base: str, metrics_base: str, expected_version: str | None = None,
    *, public_host: str | None = None,
) -> dict[str, str]:
    """Check routing, identity and representative player-facing entry points."""
    payload = json.loads(_read(public_base, "/api/version", host=public_host))
    if not isinstance(payload, dict):
        raise ValueError("/api/version: expected JSON object")
    version = payload.get("version")
    snapshot_revision = payload.get("snapshot_revision")
    static_revision = payload.get("static_revision")
    if not all(
        isinstance(value, str) and value
        for value in (version, snapshot_revision, static_revision)
    ):
        raise ValueError("/api/version: missing runtime identity or revisions")
    assert isinstance(version, str)
    assert isinstance(snapshot_revision, str)
    assert isinstance(static_revision, str)
    if expected_version is not None and version != expected_version:
        raise ValueError(f"/api/version: expected {expected_version}, got {version}")

    page = _read(public_base, "/", host=public_host)
    if expected_version is not None:
        # Do not accept `Version 1.2.0+dev` for a released 1.2.0 image.
        footer = rf"Version\s+{re.escape(expected_version)}(?![\w.+-])"
    else:
        footer = rf"Version\s+{re.escape(version)}(?:\+dev)?(?![\w.+-])"
    if not re.search(footer, page):
        raise ValueError("Public home page does not show the expected version")

    for path in ("/changes", "/scenarios"):
        if not _read(public_base, path, host=public_host):
            raise ValueError(f"{path}: empty response")
    if not _read(metrics_base, "/health"):
        raise ValueError("/health: empty response")
    if not _read(metrics_base, "/metrics"):
        raise ValueError("/metrics: empty response")
    return {
        "version": version,
        "snapshot_revision": snapshot_revision,
        "static_revision": static_revision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-base", default="http://localhost:8080")
    parser.add_argument("--public-host", help="override Host header on public requests only")
    parser.add_argument("--metrics-base", default="http://127.0.0.1:8081")
    parser.add_argument("--expected-version", help="require exact released version (no +dev)")
    args = parser.parse_args(argv)
    try:
        identity = verify_running_deployment(
            args.public_base, args.metrics_base, args.expected_version,
            public_host=args.public_host,
        )
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Deployment smoke: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Deployment smoke: PASS ({identity})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
