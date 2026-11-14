"""Create isolated, named Git worktrees for trusted InfinityDB agents.

This tool is intentionally independent of MCP and never fetches, stages, commits,
pushes, resets, or changes the primary checkout's current branch.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
from pathlib import Path

_MARKER = Path("local/agent-workspace.json")
_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,39}\Z")
_BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*\Z")


class WorkspaceError(ValueError):
    """A workspace precondition was not met."""


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, timeout=120,
    )
    if check and result.returncode != 0:
        raise WorkspaceError(
            f"Git {args[0]} failed: {(result.stderr or result.stdout).strip()[:500]}"
        )
    return result


def _root(path: Path) -> Path:
    result = _git(path.resolve(), "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve()


def _token(value: str, label: str) -> str:
    token = value.lower()
    if not _NAME.fullmatch(token):
        raise WorkspaceError(f"{label} must be 1-40 lowercase letters, digits or hyphens")
    return token


def create(
    root: Path, agent: str, task: str, *,
    machine: str | None = None,
    integration_branch: str = "dev/v1.0.0",
) -> dict[str, str]:
    """Create an agent branch/worktree from a pinned clean integration checkout."""
    root = _root(root)
    agent = _token(agent, "agent")
    task = _token(task, "task")
    machine = _token(machine or re.sub(r"[^a-z0-9-]", "-", socket.gethostname().lower()), "machine")
    if root.name != "InfinityDB":
        raise WorkspaceError("Run creation from the primary InfinityDB checkout")
    if (root / _MARKER).exists():
        raise WorkspaceError("Cannot create an agent workspace from another agent workspace")
    if not _BRANCH.fullmatch(integration_branch) or integration_branch.startswith("-"):
        raise WorkspaceError("Invalid integration branch")
    actual_branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if actual_branch.returncode != 0 or actual_branch.stdout.strip() != integration_branch:
        raise WorkspaceError(f"Primary checkout must be on {integration_branch}")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=normal").stdout.strip():
        raise WorkspaceError("Primary checkout is not clean; review existing changes first")

    baseline = _git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
    branch = f"agent/{machine}/{agent}/{task}"
    destination = root.parent / f"InfinityDB-agent-{machine}-{agent}-{task}"
    if destination.exists() or destination.is_symlink():
        raise WorkspaceError("Agent worktree destination already exists")
    branch_exists = _git(
        root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False,
    )
    if branch_exists.returncode == 0:
        raise WorkspaceError("Agent Git branch already exists")

    # Pin the exact baseline: a concurrent primary HEAD movement must not
    # silently change this worktree's contents between checks and creation.
    _git(root, "worktree", "add", "--no-track", "-b", branch, str(destination), baseline)
    marker = destination / _MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": 1, "role": "development", "agent": agent, "task": task,
        "machine": machine, "branch": branch, "baseline": baseline,
    }
    # Exclusive creation: never replace an existing ownership record.
    with marker.open("x", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return {"path": str(destination), **metadata}


def guard(root: Path, agent: str, task: str | None = None) -> dict[str, str]:
    """Fail closed if the current checkout is not the named agent's workspace."""
    root = _root(root)
    agent = _token(agent, "agent")
    if task is not None:
        task = _token(task, "task")
    marker = root / _MARKER
    if not marker.is_file() or marker.is_symlink():
        raise WorkspaceError("Missing agent ownership marker; refusing shared checkout")
    try:
        metadata = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkspaceError("Invalid agent ownership marker") from exc
    if (
        not isinstance(metadata, dict)
        or metadata.get("version") != 1
        or metadata.get("role") != "development"
        or metadata.get("agent") != agent
        or (task is not None and metadata.get("task") != task)
    ):
        raise WorkspaceError("Workspace owner or task differs from requested identity")
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if (
        branch.returncode != 0
        or branch.stdout.strip() != metadata.get("branch")
        or not isinstance(metadata.get("baseline"), str)
        or not re.fullmatch(r"[0-9a-f]{40}", metadata["baseline"])
    ):
        raise WorkspaceError("Workspace Git branch or metadata differs from expected state")
    return {
        "path": str(root), "agent": agent, "task": metadata["task"],
        "branch": metadata["branch"], "baseline": metadata["baseline"],
        "head": _git(root, "rev-parse", "HEAD").stdout.strip(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("create", help="Create a sibling worktree from the clean primary")
    new.add_argument("--agent", required=True)
    new.add_argument("--task", required=True)
    new.add_argument("--machine", help="Optional stable machine identifier")
    new.add_argument("--integration-branch", default="dev/v1.0.0")
    check = commands.add_parser("guard", help="Verify agent ownership before local edits")
    check.add_argument("--agent", required=True)
    check.add_argument("--task")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create(
                Path.cwd(), args.agent, args.task,
                machine=args.machine, integration_branch=args.integration_branch,
            )
        else:
            result = guard(Path.cwd(), args.agent, args.task)
    except (WorkspaceError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"workspace refused: {exc}\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
