"""Read-only, credential-redacted Syncthing health for the five InfinityDB families.

No synchronization, configuration writes, service control, or private payload reads.
API keys are used only in memory for local loopback GET requests; never logged.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

FAMILIES = {
    "raw": ("data/raw", "raw"),
    "wiki": ("data/wiki", "wiki"),
    "pdf": ("data/pdf", "pdf"),
    "snapshots": ("data/manifests/snapshots", "snapshots"),
    "image-overrides": ("image_overrides", "image-overrides"),
}
ROOT = Path(__file__).resolve().parents[2]
COUNTS = (
    "globalFiles", "localFiles", "globalBytes", "localBytes",
    "needFiles", "needBytes", "needDeletes", "pullErrors", "receiveOnlyChangedFiles",
)
FOLDER_ID = re.compile(r"[a-zA-Z0-9_-]{1,80}\Z")


def _discover_config() -> Path:
    explicit = os.environ.get("INFINITYDB_SYNCTHING_CONFIG")
    if explicit:
        return Path(explicit)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", "")) / "Syncthing" / "config.xml"
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / (
        "syncthing/config.xml"
    )


def _gui_endpoint(gui: ET.Element | None) -> tuple[str, str] | None:
    """Accept only a configured GUI that can be queried through loopback."""
    if gui is None or gui.get("enabled") == "false":
        return None
    key = (gui.findtext("apikey") or "").strip()
    address = (gui.findtext("address") or "").strip()
    if not key or not address:
        return None
    try:
        parsed = urllib.parse.urlsplit("http://" + address)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.hostname not in {"127.0.0.1", "localhost", "::1", "0.0.0.0", "::"}
        or port is None or not 1 <= port <= 65535
        or parsed.username or parsed.password or parsed.path
        or parsed.query or parsed.fragment
    ):
        return None
    scheme = "https" if gui.get("tls", "false") == "true" else "http"
    return f"{scheme}://127.0.0.1:{port}", key


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow a GUI redirect with an API key, even on localhost."""

    def redirect_request(
        self, request: urllib.request.Request, fp: Any, code: int,
        msg: str, headers: Any, newurl: str,
    ) -> None:
        return None


def _live_status(endpoint: tuple[str, str], folder_id: str) -> dict[str, Any]:
    base, key = endpoint
    url = f"{base}/rest/db/status?{urllib.parse.urlencode({'folder': folder_id})}"
    request = urllib.request.Request(url, headers={"X-API-Key": key}, method="GET")
    # Bypass environment-defined proxies; never send the key off-host.
    handlers: list[Any] = [urllib.request.ProxyHandler({}), _NoRedirect()]
    if base.startswith("https:"):
        handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with urllib.request.build_opener(*handlers).open(request, timeout=2) as response:
            payload = response.read(256 * 1024)
        doc = json.loads(payload)
    except (OSError, ValueError, urllib.error.URLError, ssl.SSLError):
        return {"status": "unavailable"}
    if not isinstance(doc, dict):
        return {"status": "invalid-response"}
    result: dict[str, Any] = {"status": "available"}
    for field in COUNTS:
        value = doc.get(field)
        if type(value) is int and value >= 0:
            result[field] = value
    state = doc.get("state")
    if state in {
        "idle", "scanning", "syncing", "sync-preparing", "error",
        "cleaning", "waiting-to-scan",
    }:
        result["state"] = state
    invalid = doc.get("invalid")
    result["invalid"] = isinstance(invalid, str) and bool(invalid)
    return result


def _same_path(value: str, expected: Path) -> bool:
    if not value:
        return False
    candidate = Path(value)
    if not candidate.is_absolute():
        return False
    return os.path.normcase(os.path.normpath(str(candidate))) == os.path.normcase(
        os.path.normpath(str(expected))
    )


def inspect(
    config: Path, *, role: str, sender_root: Path = ROOT, receiver_root: Path | None = None,
) -> dict[str, Any]:
    """Report bounded configuration and local live API evidence, with no secrets."""
    if role not in {"sender", "receiver"}:
        raise ValueError("unsupported role")
    if role == "receiver" and (receiver_root is None or not receiver_root.is_absolute()):
        return {"role": role, "status": "unavailable", "reason": "receiver-root-not-configured"}
    try:
        xml = ET.parse(config).getroot()
    except (ET.ParseError, OSError):
        return {"role": role, "status": "unavailable", "reason": "config-not-readable"}
    if xml.tag != "configuration":
        return {"role": role, "status": "unavailable", "reason": "config-invalid"}
    gui = _gui_endpoint(xml.find("gui"))
    root = sender_root if role == "sender" else receiver_root
    assert root is not None
    rows: dict[str, Any] = {}
    for family, (sender, receiver) in FAMILIES.items():
        expected = root / (sender if role == "sender" else receiver)
        matches = [item for item in xml.findall("folder")
                   if _same_path(item.get("path", ""), expected)]
        if len(matches) != 1:
            rows[family] = {"status": "missing" if not matches else "ambiguous"}
            continue
        item = matches[0]
        identifier = item.get("id", "")
        versioning = item.find("versioning")
        mode = item.get("type")
        record: dict[str, Any] = {
            "status": "configured",
            "id": identifier if FOLDER_ID.fullmatch(identifier) else None,
            "mode": mode,
            "mode_matches_role": mode == ("sendonly" if role == "sender" else "receiveonly"),
            "paused": item.get("paused") == "true",
            "versioning": bool(
                versioning is not None and (versioning.get("type") or "").strip()
            ),
        }
        if record["id"] is None:
            record["live"] = {"status": "invalid-folder-id"}
        elif gui is None:
            record["live"] = {"status": "gui-unavailable"}
        else:
            record["live"] = _live_status(gui, identifier)
        rows[family] = record
    return {
        "role": role, "status": "inspected", "config": "readable",
        "gui": "configured-local" if gui else "unavailable-or-not-local",
        "folders": rows,
        "scope": "read-only-local-api-and-config-not-independent-backup-or-restore",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("sender", "receiver"), required=True)
    args = parser.parse_args(argv)
    receiver_env = os.environ.get("INFINITYDB_SYNC_STAGING_ROOT")
    receiver_root = Path(receiver_env) if receiver_env else None
    result = inspect(
        _discover_config(), role=args.role, receiver_root=receiver_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "inspected" else 2


if __name__ == "__main__":
    raise SystemExit(main())
