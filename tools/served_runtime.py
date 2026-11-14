"""Verify served runtime identity for project-infrastructure checks.

The helper returns in-memory evidence only and remains useful while the baseline
reporter or release-candidate verifier requires an exact served snapshot.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ServedRuntimeError(ValueError):
    """The served runtime identity could not be verified."""


def verify_served_runtime(expected_revision: str, base_url: str) -> dict[str, str]:
    """Compare an explicit runtime snapshot with a server's version endpoint."""
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ServedRuntimeError(
            "Server base URL must be an HTTP(S) origin without credentials, path or query"
        )
    version_url = base_url.rstrip("/") + "/api/version"
    try:
        request = Request(
            version_url,
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise ServedRuntimeError(
                    f"Runtime version endpoint returned HTTP {response.status}"
                )
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise ServedRuntimeError(f"Could not verify runtime version: {exc}") from exc
    if not isinstance(payload, dict):
        raise ServedRuntimeError("Runtime version endpoint did not return an object")
    actual = payload.get("snapshot_revision")
    if not isinstance(actual, str) or actual != expected_revision:
        raise ServedRuntimeError(
            "Runtime snapshot revision does not match inventoried runtime artifacts: "
            f"expected {expected_revision}, received {actual!r}"
        )
    return {
        "versionUrl": version_url,
        "snapshotRevision": actual,
        "appVersion": str(payload.get("version", "")),
        "staticRevision": str(payload.get("static_revision", "")),
        "status": "exact-runtime-revision-match-not-source-completeness",
    }
