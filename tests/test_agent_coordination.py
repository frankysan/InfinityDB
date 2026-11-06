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

from tools import agent_global_coordination as global_coordination
from tools.agent_coordination import (
    CoordinationError,
    _common_dir,
    acquire_integration,
    check,
    check_integration,
    claim,
    primary_for_agent,
    release,
    status,
)
from tools.agent_coordination import (
    integrate_proposal as _integrate_proposal,
)
from tools.agent_coordination import (
    release_integration as _release_integration,
)
from tools.agent_workspaces import create


def integrate_proposal(root: Path, agent: str, task: str, claim_id: str, **kwargs) -> dict:
    """Exercise existing local scenarios with real required global ownership."""
    primary = primary_for_agent(root)
    snapshot = global_coordination.status(root)
    entry = next((item for item in snapshot["claims"] if item["task"] == task), None)
    if entry is None:
        local = next(item for item in status(root)["claims"] if item["id"] == claim_id)
        entry = global_coordination.claim(root, agent, task, local["scope"])
    lease = snapshot["integration"]
    if lease is None:
        lease = global_coordination.acquire_integration(
            primary, kwargs["owner"], kwargs["expected_head"],
        )
    return _integrate_proposal(
        root, agent, task, claim_id, **kwargs,
        global_claim_id=entry["id"], global_integration_id=lease["id"],
        global_revision=global_coordination.status(root)["revision"],
    )


def release_integration(root: Path, owner: str, claim_id: str) -> dict:
    lease = global_coordination.status(root)["integration"]
    if lease is not None:
        global_coordination.release_integration(root, owner, lease["id"])
        # Source publication is a separate, explicit test-fixture step.
        _git(root, "push", "origin", "dev/v1.0.0")
    return _release_integration(root, owner, claim_id)


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
    origin = tmp_path / "origin.git"
    _git(root, "clone", "--bare", str(root), str(origin))
    _git(root, "remote", "add", "origin", str(origin))
    global_coordination.bootstrap(root)
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


def test_pinned_proposal_fast_forward_integration(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    assert primary_for_agent(a) == root
    item = claim(a, "agent-a", "task-a", ["src/a.py"])
    (a / "src/a.py").write_text("VALUE = 5\n", encoding="utf-8")
    _git(a, "add", "src/a.py")
    _git(a, "commit", "-qm", "feat: update source")
    proposal = _git(a, "rev-parse", "HEAD")
    lease = acquire_integration(root, "integrator", head)
    result = integrate_proposal(
        a, "agent-a", "task-a", item["id"],
        owner="integrator", integration_id=lease["id"],
        expected_head=head, proposal_head=proposal,
    )
    assert result["status"] == "integrated"
    assert result["paths"] == ["src/a.py"]
    assert _git(root, "rev-parse", "HEAD") == proposal
    assert _git(root, "status", "--porcelain") == ""
    assert (root / "src/a.py").read_text(encoding="utf-8") == "VALUE = 5\n"
    with pytest.raises(CoordinationError, match="HEAD differs"):
        integrate_proposal(
            a, "agent-a", "task-a", item["id"],
            owner="integrator", integration_id=lease["id"],
            expected_head=head, proposal_head=proposal,
        )
    release_integration(root, "integrator", lease["id"])


def test_integration_refuses_unclaimed_file_or_missing_lease(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    item = claim(a, "agent-a", "task-a", ["src/a.py"])
    (a / "README.md").write_text("Unclaimed\n", encoding="utf-8")
    _git(a, "add", "README.md")
    _git(a, "commit", "-qm", "test: unexpected path")
    proposal = _git(a, "rev-parse", "HEAD")
    with pytest.raises(CoordinationError, match="Integration reservation differs"):
        integrate_proposal(
            a, "agent-a", "task-a", item["id"],
            owner="integrator", integration_id="0" * 32,
            expected_head=head, proposal_head=proposal,
        )
    lease = acquire_integration(root, "integrator", head)
    with pytest.raises(CoordinationError, match="outside claimed scope"):
        integrate_proposal(
            a, "agent-a", "task-a", item["id"],
            owner="integrator", integration_id=lease["id"],
            expected_head=head, proposal_head=proposal,
        )
    assert _git(root, "rev-parse", "HEAD") == head
    release_integration(root, "integrator", lease["id"])


def test_second_agent_merges_primary_then_fast_forwards(tmp_path: Path) -> None:
    root, baseline = _repo(tmp_path)
    a = _worktree(root, "agent-a", "task-a")
    b = _worktree(root, "agent-b", "task-b")
    ca = claim(a, "agent-a", "task-a", ["src/a.py"])
    cb = claim(b, "agent-b", "task-b", ["README.md"])
    (a / "src/a.py").write_text("VALUE = 9\n", encoding="utf-8")
    _git(a, "add", "src/a.py")
    _git(a, "commit", "-qm", "feat: agent a")
    head_a = _git(a, "rev-parse", "HEAD")
    (b / "README.md").write_text("Agent B\n", encoding="utf-8")
    _git(b, "add", "README.md")
    _git(b, "commit", "-qm", "feat: agent b")
    head_b = _git(b, "rev-parse", "HEAD")

    lease_a = acquire_integration(root, "integrator", baseline)
    integrate_proposal(
        a, "agent-a", "task-a", ca["id"],
        owner="integrator", integration_id=lease_a["id"],
        expected_head=baseline, proposal_head=head_a,
    )
    release_integration(root, "integrator", lease_a["id"])

    lease_b = acquire_integration(root, "integrator", head_a)
    with pytest.raises(CoordinationError, match="Git merge-base"):
        integrate_proposal(
            b, "agent-b", "task-b", cb["id"],
            owner="integrator", integration_id=lease_b["id"],
            expected_head=head_a, proposal_head=head_b,
        )
    assert _git(root, "rev-parse", "HEAD") == head_a
    _git(b, "merge", "--no-edit", head_a)
    merged_b = _git(b, "rev-parse", "HEAD")
    assert check(b, "agent-b", "task-b", cb["id"])["files_checked"] == 1
    integrate_proposal(
        b, "agent-b", "task-b", cb["id"],
        owner="integrator", integration_id=lease_b["id"],
        expected_head=head_a, proposal_head=merged_b,
    )
    assert _git(root, "rev-parse", "HEAD") == merged_b
    release_integration(root, "integrator", lease_b["id"])


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
