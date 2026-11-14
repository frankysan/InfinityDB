"""One-time Syncthing Windows sender path cutover via the loopback REST API.

Changes folder *paths only*; folder IDs, devices, modes and options stay intact.
Source files remain on disk. Default command previews all changes.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any

from tools.operations import audit_syncthing_health as health

ROOT = Path(__file__).resolve().parents[2]
FOLDERS = {
    "raw": ("data/raw", "local/data/raw"),
    "wiki": ("data/wiki", "local/data/wiki"),
    "pdf": ("data/pdf", "local/data/pdf"),
    "snapshots": ("data/manifests/snapshots", "local/data/manifests/snapshots"),
}


def _request(endpoint: tuple[str, str], path: str, payload: dict | None = None) -> Any:
    base, key = endpoint
    url = f"{base}{path}"
    request = urllib.request.Request(
        url,
        headers={
            "X-API-Key": key,
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method="PATCH" if payload is not None else "GET",
    )
    handlers: list[Any] = [
        urllib.request.ProxyHandler({}),
        health._NoRedirect(),
    ]
    with urllib.request.build_opener(*handlers).open(request, timeout=8) as response:
        output = response.read(256 * 1024)
    return json.loads(output) if output else None


def _plan(root: Path, folders: list[dict[str, Any]]) -> list[tuple[str, str, Path]]:
    changes = []
    selected_ids: set[str] = set()
    for family, (old, new) in FOLDERS.items():
        source = root / new
        if source.is_symlink() or not source.is_dir() or not any(
            entry.is_file() or entry.is_dir() for entry in source.iterdir()
        ):
            raise ValueError(f"Local sender input missing or empty: {source}")
        matches = [
            item for item in folders
            if health._same_path(str(item.get("path", "")), root / old)
            or health._same_path(str(item.get("path", "")), source)
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one matching sender folder for {family}")
        item = matches[0]
        folder_id = item.get("id")
        if (
            not isinstance(folder_id, str)
            or health.FOLDER_ID.fullmatch(folder_id) is None
            or folder_id in selected_ids
            or item.get("type") != "sendonly"
        ):
            raise ValueError(f"Unexpected Syncthing sender config for {family}")
        selected_ids.add(folder_id)
        if not health._same_path(str(item["path"]), source):
            changes.append((family, folder_id, source))
    return changes


def cutover(root: Path, endpoint: tuple[str, str], *, apply: bool) -> list[str]:
    folders = _request(endpoint, "/rest/config/folders")
    if not isinstance(folders, list) or not all(isinstance(item, dict) for item in folders):
        raise ValueError("Syncthing folder API returned an invalid configuration")
    changes = _plan(root, folders)
    updates = []
    for family, folder_id, source in changes:
        if apply:
            (source / ".stfolder").mkdir(exist_ok=True)
            _request(endpoint, f"/rest/config/folders/{folder_id}", {"path": str(source)})
            refreshed = _request(endpoint, f"/rest/config/folders/{folder_id}")
            if not isinstance(refreshed, dict) or not health._same_path(
                str(refreshed.get("path", "")), source
            ):
                raise ValueError(f"Syncthing did not confirm new path for {family}")
        updates.append(f"{family}: {'updated' if apply else 'would update'} -> {source}")
    return updates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Update the four sender folders")
    args = parser.parse_args(argv)
    if health.os.name != "nt":
        parser.exit(2, "Windows Syncthing sender required\n")
    try:
        import xml.etree.ElementTree as ET

        config = ET.parse(health._discover_config()).getroot()
        endpoint = health._gui_endpoint(config.find("gui"))
        if endpoint is None:
            raise ValueError("No local Syncthing API configured")
        changes = cutover(ROOT, endpoint, apply=args.apply)
        if not changes:
            print("All four Syncthing sender source paths already use local/data.")
        else:
            print("\n".join(changes))
        if args.apply:
            restart = _request(endpoint, "/rest/config/restart-required")
            required = restart.get("requiresRestart") if isinstance(restart, dict) else None
            print(f"Syncthing restart required: {required!r}")
    except (OSError, ValueError, TypeError, KeyError, ET.ParseError) as exc:
        parser.exit(1, f"Syncthing sender cutover refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
