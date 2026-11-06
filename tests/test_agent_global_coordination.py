"""Cross-host agent claims tested with independent clones of a local bare remote."""
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from tools.agent_global_coordination import (
    GlobalClaimError,
    acquire_integration,
    bootstrap,
    check,
    check_integration,
    claim,
    release,
    release_integration,
    status,
)
from tools.agent_workspaces import create


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True,
        text=True, check=True, timeout=30,
    )
    return result.stdout.strip()


def _clones(tmp_path: Path) -> tuple[Path, Path, Path]:
    seed = tmp_path / "seed"
    seed.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=dev/v1.0.0", str(seed)],
        check=True, capture_output=True,
    )
    _git(seed, "config", "user.name", "Test")
    _git(seed, "config", "user.email", "test@example.invalid")
    (seed / ".gitignore").write_text("/local/\n", encoding="utf-8")
    (seed / "README.md").write_text("Seed\n", encoding="utf-8")
    (seed / "src").mkdir()
    (seed / "src" / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
    (seed / "src" / "b.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(seed, "add", ".")
    _git(seed, "commit", "-qm", "test: seed")
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(seed), str(origin)],
        check=True, capture_output=True,
    )
    for name in ("windows", "linux"):
        host = tmp_path / name
        host.mkdir()
        subprocess.run(
            ["git", "clone", "-q", str(origin), str(host / "InfinityDB")],
            check=True, capture_output=True,
        )
        primary = host / "InfinityDB"
        _git(primary, "config", "user.name", "Test")
        _git(primary, "config", "user.email", "test@example.invalid")
    return origin, tmp_path / "windows/InfinityDB", tmp_path / "linux/InfinityDB"


def _agent(primary: Path, agent: str, task: str, machine: str) -> Path:
    return Path(create(primary, agent, task, machine=machine)["path"])


def test_bootstrap_status_across_independent_clones(tmp_path: Path) -> None:
    origin, windows, linux = _clones(tmp_path)
    before_win, before_linux = _git(windows, "rev-parse", "HEAD"), _git(linux, "rev-parse", "HEAD")
    assert status(windows)["status"] == "uninitialized"
    assert bootstrap(windows)["status"] == "initialized"
    assert "claims.json" in _git(origin, "ls-tree", "refs/heads/coordination/agent-claims")
    assert status(linux)["status"] == "available"
    assert status(windows)["revision"] == 1
    assert bootstrap(windows)["status"] == "unchanged"
    assert _git(windows, "rev-parse", "HEAD") == before_win
    assert _git(linux, "rev-parse", "HEAD") == before_linux
    assert _git(origin, "rev-parse", "refs/heads/coordination/agent-claims") != before_win


def test_conflicting_cross_machine_scopes_and_release(tmp_path: Path) -> None:
    _, windows, linux = _clones(tmp_path)
    bootstrap(windows)
    a = _agent(windows, "agent-a", "task-a", "windows")
    b = _agent(linux, "agent-b", "task-b", "devbox")
    ca = claim(a, "agent-a", "task-a", ["src/A.PY"])
    assert check(a, "agent-a", "task-a", ca["id"])["status"] == "valid"
    assert status(linux)["claims"][0]["id"] == ca["id"]
    with pytest.raises(GlobalClaimError, match="already claimed"):
        claim(b, "agent-b", "task-b", ["src/"])
    cb = claim(b, "agent-b", "task-b", ["src/b.py"])
    assert len(status(a)["claims"]) == 2
    with pytest.raises(GlobalClaimError, match="another agent"):
        release(b, "agent-b", "task-b", ca["id"])
    assert release(a, "agent-a", "task-a", ca["id"])["released"] == ca["id"]
    assert release(b, "agent-b", "task-b", cb["id"])["released"] == cb["id"]
    assert status(linux)["claims"] == []


def test_two_process_like_clones_cannot_claim_same_scope(tmp_path: Path) -> None:
    _, windows, linux = _clones(tmp_path)
    bootstrap(windows)
    a = _agent(windows, "agent-a", "task-a", "windows")
    b = _agent(linux, "agent-b", "task-b", "devbox")
    barrier = Barrier(2)

    def attempt(root: Path, agent: str, task: str) -> bool:
        barrier.wait(timeout=10)
        try:
            claim(root, agent, task, ["src/"])
        except GlobalClaimError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt, a, "agent-a", "task-a")
        second = pool.submit(attempt, b, "agent-b", "task-b")
        assert sorted([first.result(timeout=60), second.result(timeout=60)]) == [False, True]
    assert len(status(windows)["claims"]) == 1


def test_global_integration_reservation_is_shared(tmp_path: Path) -> None:
    _, windows, linux = _clones(tmp_path)
    bootstrap(windows)
    head = _git(windows, "rev-parse", "HEAD")
    entry = acquire_integration(windows, "integrator", head)
    assert status(linux)["integration"]["id"] == entry["id"]
    assert check_integration(linux, "integrator", entry["id"], head)["status"] == "valid"
    with pytest.raises(GlobalClaimError, match="already reserved"):
        acquire_integration(linux, "other", head)
    with pytest.raises(GlobalClaimError, match="mismatch"):
        release_integration(windows, "other", entry["id"])
    release_integration(windows, "integrator", entry["id"])
    assert status(linux)["integration"] is None


def test_uninitialized_or_failed_remote_refuses_claim(tmp_path: Path) -> None:
    origin, windows, _ = _clones(tmp_path)
    a = _agent(windows, "agent-a", "task-a", "windows")
    with pytest.raises(GlobalClaimError, match="not initialized"):
        claim(a, "agent-a", "task-a", ["src/"])
    bootstrap(windows)
    _git(a, "remote", "set-url", "origin", str(origin.parent / "missing.git"))
    with pytest.raises(GlobalClaimError, match="failed"):
        claim(a, "agent-a", "task-a", ["src/"])
