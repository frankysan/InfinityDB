"""Local cross-process agent claims and integration ownership for InfinityDB.

Uses the Git common directory so sibling worktrees share durable state.
This registry is local to ONE Git repository/object store, NOT a cross-host
service, OS access-control mechanism, or replacement for remote Git checks.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tools.agent_workspaces import WorkspaceError, guard

_STATE_NAME = "infinitydb-agent-coordination"
_SHA = re.compile(r"[a-f0-9]{40}\Z")
_ID = re.compile(r"[a-f0-9]{32}\Z")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9-]{0,39}\Z")
_PROTECTED = (
    "docs/TODO.md", "docs/validation-queue.md", "data/generated/",
    "data/manifests/",
)


class CoordinationError(ValueError):
    """A requested coordination operation is unsafe or conflicted."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, capture_output=True, encoding="utf-8", errors="replace",
        check=False, timeout=30,
    )
    if result.returncode:
        raise CoordinationError(f"Git {args[0]} rejected the request")
    return result


def _root(path: Path) -> Path:
    return Path(_git(path.resolve(), "rev-parse", "--show-toplevel").stdout.strip()).resolve()


def _common_dir(root: Path) -> Path:
    value = _git(root, "rev-parse", "--git-common-dir").stdout.strip()
    directory = Path(value)
    if not directory.is_absolute():
        directory = root / directory
    return directory.resolve(strict=True)


def _token(value: str, label: str) -> str:
    if not _TOKEN.fullmatch(value):
        raise CoordinationError(f"Invalid {label}: use lowercase letters/digits/hyphens")
    return value


def _scope(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise CoordinationError("Invalid scope")
    text = value.replace("\\", "/")
    if text.startswith("/") or ":" in text or "//" in text:
        raise CoordinationError("Scope must be a repository-relative path")
    directory = text.endswith("/")
    parts = text.rstrip("/").split("/")
    if any(part in ("", ".", "..", ".git", ".gitmodules") for part in parts):
        raise CoordinationError("Invalid scope components")
    normalized = "/".join(parts) + ("/" if directory else "")
    if normalized in ("local/", ".venv/"):
        raise CoordinationError("Ignored workspaces cannot be claimed")
    return normalized


def _overlaps(a: str, b: str) -> bool:
    return (
        a == b
        or (a.endswith("/") and b.startswith(a))
        or (b.endswith("/") and a.startswith(b))
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def _mutex(root: Path) -> Iterator[Path]:
    directory = _common_dir(root) / _STATE_NAME
    if directory.is_symlink():
        raise CoordinationError("Coordination directory cannot be a link")
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink() or not directory.is_dir():
        raise CoordinationError("Coordination directory is unavailable")
    path = directory / "mutex"
    if path.is_symlink():
        raise CoordinationError("Coordination mutex cannot be a link")
    with path.open("a+b") as handle:
        handle.seek(0)
        if handle.read(1) != b"\0":
            handle.seek(0)
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + 5
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise CoordinationError("Coordination registry is busy") from exc
                time.sleep(0.05)
        try:
            yield directory
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _state(directory: Path) -> dict:
    path = directory / "state.json"
    if path.is_symlink():
        raise CoordinationError("Coordination state cannot be a link")
    if not path.exists():
        return {"version": 1, "revision": 0, "claims": {}, "integration": None}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CoordinationError("Coordination state is invalid; no writes permitted") from exc
    if (
        not isinstance(state, dict)
        or state.get("version") != 1
        or type(state.get("revision")) is not int
        or not isinstance(state.get("claims"), dict)
        or not (
            state.get("integration") is None
            or isinstance(state.get("integration"), dict)
        )
    ):
        raise CoordinationError("Coordination state schema is invalid")
    return state


def _save(directory: Path, state: dict) -> None:
    state["revision"] += 1
    output = directory / "state.json"
    temporary = directory / f"state-{uuid4().hex}.tmp"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def status(root: Path) -> dict:
    root = _root(root)
    with _mutex(root) as directory:
        state = _state(directory)
        return {
            "scope": "local-git-common-dir-only",
            "revision": state["revision"],
            "claims": list(state["claims"].values()),
            "integration": state["integration"],
        }


def claim(root: Path, agent: str, task: str, paths: list[str]) -> dict:
    root = _root(root)
    current = guard(root, agent, task)
    if not paths:
        raise CoordinationError("Provide one or more explicit path scopes")
    scope = sorted(set(_scope(path) for path in paths))
    if any(_overlaps(path, protected) for path in scope for protected in _PROTECTED):
        raise CoordinationError("Scope includes an integration-owned file or publication")
    with _mutex(root) as directory:
        state = _state(directory)
        for existing in state["claims"].values():
            if existing["workspace"] == str(root):
                raise CoordinationError("Workspace already has an active claim")
            if existing["task"] == task:
                raise CoordinationError("Task already claimed in this Git repository")
            if any(_overlaps(a, b) for a in scope for b in existing["scope"]):
                raise CoordinationError("Requested file scope overlaps another active claim")
        entry = {
            "id": uuid4().hex, "agent": agent, "task": task,
            "workspace": str(root), "branch": current["branch"],
            "baseline": current["baseline"], "scope": scope,
            "created_utc": _now(), "host": socket.gethostname(),
        }
        state["claims"][entry["id"]] = entry
        _save(directory, state)
        return entry


def _get_claim(root: Path, claim_id: str, agent: str, task: str, state: dict) -> dict:
    if not _ID.fullmatch(claim_id):
        raise CoordinationError("Invalid claim ID")
    entry = state["claims"].get(claim_id)
    if not entry or entry["workspace"] != str(root):
        raise CoordinationError("Claim is missing or belongs to another workspace")
    if entry["agent"] != agent or entry["task"] != task:
        raise CoordinationError("Claim owner or task differs")
    return entry


def check(root: Path, agent: str, task: str, claim_id: str) -> dict:
    root = _root(root)
    current = guard(root, agent, task)
    with _mutex(root) as directory:
        entry = _get_claim(root, claim_id, agent, task, _state(directory))
        if current["branch"] != entry["branch"] or current["baseline"] != entry["baseline"]:
            raise CoordinationError("Checkout identity differs from claimed identity")
        # Check both committed/staged/unstaged tracked changes AND nonignored new files.
        tracked = _git(
            root, "diff", "--no-renames", "--name-only", entry["baseline"],
        ).stdout.splitlines()
        untracked = _git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
        unexpected = [
            path for path in set(tracked + untracked)
            if not any(_overlaps(path, allowed) for allowed in entry["scope"])
        ]
        if unexpected:
            details = ", ".join(sorted(unexpected)[:8])
            raise CoordinationError(f"Changes outside claimed scope: {details}")
        return {
            "claim": claim_id, "status": "valid",
            "files_checked": len(set(tracked + untracked)),
        }


def release(root: Path, agent: str, task: str, claim_id: str) -> dict:
    root = _root(root)
    guard(root, agent, task)
    with _mutex(root) as directory:
        state = _state(directory)
        entry = _get_claim(root, claim_id, agent, task, state)
        del state["claims"][entry["id"]]
        _save(directory, state)
        return {"released": claim_id, "revision": state["revision"]}


def _primary(root: Path, expected_head: str) -> str:
    if root.name != "InfinityDB" or (root / "local/agent-workspace.json").exists():
        raise CoordinationError("Integration requires the primary InfinityDB checkout")
    branch = _git(root, "symbolic-ref", "--short", "HEAD").stdout.strip()
    if branch != "dev/v1.0.0":
        raise CoordinationError("Primary is not on dev/v1.0.0")
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if not _SHA.fullmatch(expected_head) or head != expected_head:
        raise CoordinationError("Primary HEAD differs from expected revision")
    return head


def acquire_integration(root: Path, owner: str, expected_head: str) -> dict:
    root = _root(root)
    owner = _token(owner, "owner")
    head = _primary(root, expected_head)
    if _git(root, "status", "--porcelain", "--untracked-files=normal").stdout.strip():
        raise CoordinationError("Primary checkout is dirty")
    with _mutex(root) as directory:
        state = _state(directory)
        if state["integration"] is not None:
            raise CoordinationError(
                "Integration already owned; recovery requires explicit inspection"
            )
        _primary(root, expected_head)
        entry = {
            "id": uuid4().hex, "owner": owner,
            "workspace": str(root), "expected_head": head,
            "created_utc": _now(), "host": socket.gethostname(),
        }
        state["integration"] = entry
        _save(directory, state)
        return entry


def check_integration(root: Path, owner: str, claim_id: str, expected_head: str) -> dict:
    root = _root(root)
    _primary(root, expected_head)
    with _mutex(root) as directory:
        entry = _state(directory)["integration"]
        if not entry or entry["id"] != claim_id or entry["owner"] != owner:
            raise CoordinationError("Integration ownership differs")
        if entry["workspace"] != str(root) or entry["expected_head"] != expected_head:
            raise CoordinationError("Integration baseline or workspace differs")
        return {"status": "valid", "integration": claim_id, "expected_head": expected_head}


def release_integration(root: Path, owner: str, claim_id: str) -> dict:
    root = _root(root)
    if root.name != "InfinityDB":
        raise CoordinationError("Integration release requires primary checkout")
    with _mutex(root) as directory:
        state = _state(directory)
        entry = state["integration"]
        if not entry or entry["id"] != claim_id or entry["owner"] != owner:
            raise CoordinationError("Integration owner or claim differs")
        if entry["workspace"] != str(root):
            raise CoordinationError("Integration checkout differs")
        state["integration"] = None
        _save(directory, state)
        return {"released": claim_id, "revision": state["revision"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Read local Git-common-directory claims")
    assign = commands.add_parser("claim", help="Claim an agent workspace and file scope")
    assign.add_argument("--agent", required=True)
    assign.add_argument("--task", required=True)
    assign.add_argument("--path", action="append", required=True, dest="paths")
    for operation in ("check", "release"):
        sub = commands.add_parser(operation, help=f"{operation} an existing task claim")
        sub.add_argument("--agent", required=True)
        sub.add_argument("--task", required=True)
        sub.add_argument("--claim-id", required=True)
    integration = commands.add_parser("acquire-integration", help="Claim local primary integration")
    integration.add_argument("--owner", required=True)
    integration.add_argument("--expected-head", required=True)
    integration_check = commands.add_parser(
        "check-integration", help="Verify local primary integration",
    )
    integration_check.add_argument("--owner", required=True)
    integration_check.add_argument("--claim-id", required=True)
    integration_check.add_argument("--expected-head", required=True)
    integration_release = commands.add_parser(
        "release-integration", help="Release local primary integration",
    )
    integration_release.add_argument("--owner", required=True)
    integration_release.add_argument("--claim-id", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path.cwd()
        if args.command == "status":
            result = status(root)
        elif args.command == "claim":
            result = claim(root, args.agent, args.task, args.paths)
        elif args.command == "check":
            result = check(root, args.agent, args.task, args.claim_id)
        elif args.command == "release":
            result = release(root, args.agent, args.task, args.claim_id)
        elif args.command == "acquire-integration":
            result = acquire_integration(root, args.owner, args.expected_head)
        elif args.command == "check-integration":
            result = check_integration(root, args.owner, args.claim_id, args.expected_head)
        else:
            result = release_integration(root, args.owner, args.claim_id)
    except (WorkspaceError, CoordinationError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"coordination refused: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
