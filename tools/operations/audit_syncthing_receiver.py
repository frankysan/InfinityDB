"""Read-only, bounded Linux Syncthing receiver access evidence.

This checks only five configured staging families and three fixed known input
paths. It does not inspect Syncthing credentials, enumerate private payloads,
test writes, certify backups, or authorize source relocation.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

FOLDERS = ("raw", "wiki", "pdf", "snapshots", "image-overrides")
PROBES = {
    "army-archive": "raw/JSON 20260929-114335.zip",
    "army-manifest": "snapshots/JSON 20260929-114335.json",
    "n5.3-english-pdf": "pdf/rules/n5-rules-v5.3-en.pdf",
}


class ReceiverAuditError(ValueError):
    """Receiver cannot safely be inspected."""


def _guarded_status(root: Path, relative: str, *, directory: bool) -> dict[str, Any]:
    path = root
    for part in Path(relative).parts:
        path /= part
        try:
            info = path.lstat()
        except FileNotFoundError:
            return {"status": "missing"}
        except OSError as exc:
            return {"status": "unreadable-metadata", "error": type(exc).__name__}
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            return {"status": "link-refused"}
        if path != root / relative and not stat.S_ISDIR(info.st_mode):
            return {"status": "parent-not-directory"}
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode):
        return {"status": "wrong-kind"}
    flags = os.R_OK | (os.X_OK if directory else 0)
    get_euid = getattr(os, "geteuid", None)
    return {
        "status": "present",
        "readable": os.access(path, flags),
        "writable": os.access(path, os.W_OK),
        "owner_is_inspector": (
            info.st_uid == get_euid() if callable(get_euid) else None
        ),
    }


def _acl_evidence(path: Path, user: str) -> dict[str, str | None]:
    tool = shutil.which("getfacl")
    if not tool:
        return {"status": "tool-unavailable", "access": None, "default": None}
    try:
        result = subprocess.run(
            [tool, "-c", str(path)], capture_output=True, text=True,
            check=False, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "inspection-failed", "access": None, "default": None}
    if result.returncode:
        return {"status": "inspection-failed", "access": None, "default": None}
    values = {}
    for line in result.stdout.splitlines():
        if line.startswith(("user:", "default:user:")):
            key = "default" if line.startswith("default:") else "access"
            prefix = "default:user:" if key == "default" else "user:"
            entry = line[len(prefix):].split(":", 1)
            if len(entry) == 2 and entry[0] == user:
                values[key] = entry[1].split("#", 1)[0].strip()
    return {
        "status": "available",
        "access": values.get("access"),
        "default": values.get("default"),
    }


def _recursive_access(root: Path, *, max_entries: int = 100_000) -> dict[str, Any]:
    """Census effective access without reading contents or following links."""
    counts = {
        "directories": 0, "files": 0, "links": 0, "other": 0,
        "unreadable": 0, "unreadable_directories": 0,
        "writable": 0, "metadata_errors": 0,
        "scan_errors": 0, "entries_inspected": 0,
    }
    pending = [root]
    while pending and counts["entries_inspected"] < max_entries:
        path = pending.pop()
        counts["entries_inspected"] += 1
        try:
            info = path.lstat()
        except OSError:
            counts["metadata_errors"] += 1
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            counts["links"] += 1
            continue
        if stat.S_ISDIR(info.st_mode):
            counts["directories"] += 1
            readable = os.access(path, os.R_OK | os.X_OK)
            if not readable:
                counts["unreadable"] += 1
                counts["unreadable_directories"] += 1
            if os.access(path, os.W_OK):
                counts["writable"] += 1
            if readable:
                try:
                    with os.scandir(path) as entries:
                        pending.extend(Path(item.path) for item in entries)
                except OSError:
                    counts["scan_errors"] += 1
        elif stat.S_ISREG(info.st_mode):
            counts["files"] += 1
            if not os.access(path, os.R_OK):
                counts["unreadable"] += 1
            if os.access(path, os.W_OK):
                counts["writable"] += 1
        else:
            counts["other"] += 1
    complete = (
        not pending and not counts["metadata_errors"] and not counts["scan_errors"]
        and not counts["unreadable_directories"]
    )
    return {
        **counts,
        "complete": bool(complete),
        "entry_limit_reached": bool(pending),
        "effective_readonly": bool(
            complete and not counts["unreadable"] and not counts["writable"]
            and not counts["links"] and not counts["other"]
        ),
    }


def inspect_receiver(
    root: Path, *, user: str | None = None, recursive: bool = False,
) -> dict[str, Any]:
    """Inspect the configured receiver, without reading payloads or writing."""
    if not root.is_absolute():
        raise ReceiverAuditError("Receiver root must be absolute")
    # Refuse to traverse a linked parent, not just a linked final directory.
    for parent in (root, *root.parents):
        if parent.is_symlink():
            raise ReceiverAuditError("Receiver root traverses a symlink")
    if not root.is_dir():
        raise ReceiverAuditError("Receiver root is unavailable")
    inspector = user if user is not None else getpass.getuser()
    folders = {}
    for relative in FOLDERS:
        status = _guarded_status(root, relative, directory=True)
        if status["status"] == "present":
            status["named_acl"] = _acl_evidence(root / relative, inspector)
        folders[relative] = status
    report = {
        "scope": "read-only-receiver-access-not-backup-or-sync-certification",
        "inspector": inspector,
        "folders": folders,
        "selected_input_paths": {
            name: _guarded_status(root, relative, directory=False)
            for name, relative in PROBES.items()
        },
        "recursive_acl_verified": False,
        "syncthing_live_status_verified": False,
        "independent_backup_restore_verified": False,
    }
    if recursive:
        report["recursive_access"] = {
            family: _recursive_access(root / family)
            if folders[family]["status"] == "present"
            else {"complete": False, "reason": "family-unavailable"}
            for family in FOLDERS
        }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recursive", action="store_true",
        help="Census effective read/write access for all selected family entries.",
    )
    args = parser.parse_args(argv)
    root = os.environ.get("INFINITYDB_SYNC_STAGING_ROOT")
    if not root:
        print(json.dumps({"status": "unavailable", "reason": "staging-root-not-configured"}))
        return 2
    try:
        result = inspect_receiver(Path(root), recursive=args.recursive)
    except ReceiverAuditError as exc:
        print(json.dumps({"status": "unavailable", "reason": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
