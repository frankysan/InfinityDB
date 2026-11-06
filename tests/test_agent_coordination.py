"""Local multi-agent coordination tests using disposable Git repositories."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from tools.agent_coordination import (
    CoordinationError,
    _common_dir,
    acquire_integration,
    check,
    check_integration,
    claim,
    release,
    release_integration,
    status,
)
from tools.agent_workspaces import create


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "InfinityDB"
    root.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=dev/v1.0.0", str(root)],
        check=True, capture_output=True,
    )
    _git(root, "config", "user.name", "Coordination Tester")
    _git(root, "config", "user.email", "coordination@example.invalid")
    (root / ".gitignore").write_text("/local/\n", encoding="utf-8")
    (root / "README.md").write_text("Baseline\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src/a.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "test: initial revision")
    return root, _git(root, "rev-parse", "HEAD")


def _worktree(root: Path, agent: str, task: str) -> Path:
    return Path(create(root, agent, task, machine="testhost")["path"])


def test_scope_claim_check_and_release(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    entry = claim(a, "agent-a", "task-a", ["src/"])
    assert status(root)["claims"][0]["id"] == entry["id"]
    assert check(a, "agent-a", "task-a", entry["id"])["status"] == "valid"
    (a / "src/a.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert check(a, "agent-a", "task-a", entry["id"])["files_checked"] == 1
    (a / "README.md").write_text("Unowned change\n", encoding="utf-8")
    with pytest.raises(CoordinationError, match="outside claimed scope"):
        check(a, "agent-a", "task-a", entry["id"])
    with pytest.raises(CoordinationError, match="Claim is missing"):
        release(a, "agent-a", "task-a", "0" * 32)
    assert release(a, "agent-a", "task-a", entry["id"])["released"] == entry["id"]
    assert status(a)["claims"] == []


def test_duplicate_task_or_workspace_refused(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    b = _worktree(root, "agent-b", "task-a")
    entry = claim(a, "agent-a", "task-a", ["src/a.py"])
    with pytest.raises(CoordinationError, match="Task already claimed"):
        claim(b, "agent-b", "task-a", ["README.md"])
    with pytest.raises(CoordinationError, match="Workspace already"):
        claim(a, "agent-a", "task-a", ["README.md"])
    release(a, "agent-a", "task-a", entry["id"])


def test_overlapping_paths_and_protected_files_refused(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    b = _worktree(root, "agent-b", "task-b")
    claim(a, "agent-a", "task-a", ["src/"])
    with pytest.raises(CoordinationError, match="overlaps"):
        claim(b, "agent-b", "task-b", ["src/a.py"])
    for protected in ("docs/TODO.md", "docs/", "data/generated/rules.db"):
        with pytest.raises(CoordinationError, match="integration-owned"):
            claim(b, "agent-b", "task-b", [protected])
    with pytest.raises(CoordinationError, match="Invalid scope"):
        claim(b, "agent-b", "task-b", ["../src/a.py"])


def test_concurrent_claims_only_one_wins(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    b = _worktree(root, "agent-b", "task-b")
    barrier = Barrier(2)

    def attempt(workspace: Path, agent: str, task: str) -> str:
        barrier.wait(timeout=10)
        try:
            claim(workspace, agent, task, ["src/"])
        except CoordinationError:
            return "conflict"
        return "claimed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(attempt, a, "agent-a", "task-a")
        two = pool.submit(attempt, b, "agent-b", "task-b")
        results = [one.result(timeout=30), two.result(timeout=30)]
    assert sorted(results) == ["claimed", "conflict"]
    assert len(status(root)["claims"]) == 1


def test_local_integration_exclusive_and_revision_pinned(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    lease = acquire_integration(root, "integrator", head)
    with pytest.raises(CoordinationError, match="already owned"):
        acquire_integration(root, "other", head)
    assert check_integration(root, "integrator", lease["id"], head)["status"] == "valid"
    with pytest.raises(CoordinationError, match="owner or claim"):
        release_integration(root, "other", lease["id"])
    (root / "README.md").write_text("Another revision\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-qm", "test: advance primary")
    with pytest.raises(CoordinationError, match="HEAD differs"):
        check_integration(root, "integrator", lease["id"], head)
    assert release_integration(root, "integrator", lease["id"])["released"] == lease["id"]


def test_separate_processes_cannot_claim_same_scope(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    b = _worktree(root, "agent-b", "task-b")
    project = str(Path(__file__).resolve().parents[1])
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [project, os.environ.get("PYTHONPATH", "")],
    )}
    def start(workspace: Path, agent: str, task: str) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-m", "tools.agent_coordination", "claim",
             "--agent", agent, "--task", task, "--path", "src/"],
            cwd=workspace, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    first = start(a, "agent-a", "task-a")
    second = start(b, "agent-b", "task-b")
    results = [first.communicate(timeout=30), second.communicate(timeout=30)]
    assert sorted([first.returncode, second.returncode]) == [0, 2], results
    assert len(status(root)["claims"]) == 1


def test_state_corruption_fails_closed(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    registry = _common_dir(root) / "infinitydb-agent-coordination"
    registry.mkdir()
    (registry / "state.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(CoordinationError, match="invalid"):
        claim(a, "agent-a", "task-a", ["src/"])
    assert (registry / "state.json").read_text(encoding="utf-8") == "{broken"


def test_claim_registry_is_shared_by_all_local_worktrees(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    b = _worktree(root, "agent-b", "task-b")
    claim(a, "agent-a", "task-a", ["src/a.py"])
    claim(b, "agent-b", "task-b", ["README.md"])
    assert len(status(root)["claims"]) == len(status(a)["claims"]) == len(status(b)["claims"]) == 2
    directory = _common_dir(a)
    assert directory == _common_dir(b) == _common_dir(root)
    data = json.loads((directory / "infinitydb-agent-coordination/state.json").read_text())
    assert data["revision"] == 2
