"""Cross-host agent claims tested with independent clones of a local bare remote."""
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from tools import agent_coordination as local
from tools import agent_global_coordination as global_coordination
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


def _proposal(tmp_path: Path, *, global_scope: str = "src/a.py") -> tuple:
    origin, primary, other = _clones(tmp_path)
    bootstrap(primary)
    workspace = _agent(primary, "agent-a", "task-a", "windows")
    baseline = _git(primary, "rev-parse", "HEAD")
    task = local.claim(workspace, "agent-a", "task-a", ["src/a.py"])
    global_task = claim(workspace, "agent-a", "task-a", [global_scope])
    (workspace / "src/a.py").write_text("VALUE = 42\n", encoding="utf-8")
    _git(workspace, "add", "src/a.py")
    _git(workspace, "commit", "-qm", "test: proposal")
    lease = local.acquire_integration(primary, "integrator", baseline)
    global_lease = acquire_integration(primary, "integrator", baseline)
    arguments = dict(
        owner="integrator", integration_id=lease["id"], expected_head=baseline,
        proposal_head=_git(workspace, "rev-parse", "HEAD"),
        global_claim_id=global_task["id"], global_integration_id=global_lease["id"],
        global_revision=status(primary)["revision"],
    )
    return origin, primary, other, workspace, task, arguments


def test_integration_requires_both_registries_and_keeps_reservations(tmp_path: Path) -> None:
    origin, primary, other, workspace, task, args = _proposal(tmp_path)
    result = local.integrate_proposal(workspace, "agent-a", "task-a", task["id"], **args)
    assert result["status"] == "integrated"
    assert _git(primary, "rev-parse", "HEAD") == args["proposal_head"]
    assert _git(origin, "rev-parse", "dev/v1.0.0") == args["expected_head"]
    remote = status(other)
    assert remote["version"] == 2
    assert remote["integration"]["operation"]["phase"] == "completed"
    assert local.status(primary)["integration"]["operation"]["phase"] == "completed"
    local_directory = local._common_dir(primary) / "infinitydb-agent-coordination"
    assert local._state(local_directory)["version"] == 2
    with pytest.raises(GlobalClaimError, match="Release integration"):
        release(workspace, "agent-a", "task-a", args["global_claim_id"])
    release_integration(primary, "integrator", args["global_integration_id"])
    local.release_integration(primary, "integrator", args["integration_id"])
    release(workspace, "agent-a", "task-a", args["global_claim_id"])


@pytest.mark.parametrize("change", [
    {"global_claim_id": "0" * 32}, {"global_integration_id": "0" * 32},
    {"global_revision": 1}, {"global_revision": True}, {"owner": "other"},
    {"proposal_head": "0" * 40}, {"expected_head": "0" * 40},
])
def test_integration_refuses_changed_identity_or_revision(tmp_path: Path, change: dict) -> None:
    _, primary, _, workspace, task, args = _proposal(tmp_path)
    before = args["expected_head"]
    args.update(change)
    with pytest.raises(local.CoordinationError):
        local.integrate_proposal(workspace, "agent-a", "task-a", task["id"], **args)
    assert _git(primary, "rev-parse", "HEAD") == before
    assert local.status(primary)["integration"] is not None
    assert status(primary)["integration"] is not None


def test_integration_refuses_global_scope_mismatch(tmp_path: Path) -> None:
    _, primary, _, workspace, task, args = _proposal(tmp_path, global_scope="src/")
    with pytest.raises(local.CoordinationError, match="file scope differs"):
        local.integrate_proposal(workspace, "agent-a", "task-a", task["id"], **args)
    assert _git(primary, "rev-parse", "HEAD") == args["expected_head"]


@pytest.mark.parametrize("remote_change", ["unreachable", "advanced", "missing-registry"])
def test_integration_refuses_unavailable_or_changed_remote(
    tmp_path: Path, remote_change: str,
) -> None:
    origin, primary, other, workspace, task, args = _proposal(tmp_path)
    if remote_change == "unreachable":
        _git(primary, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    elif remote_change == "missing-registry":
        _git(origin, "update-ref", "-d", global_coordination.REF)
    else:
        (other / "README.md").write_text("Concurrent source change\n", encoding="utf-8")
        _git(other, "add", "README.md")
        _git(other, "commit", "-qm", "test: concurrent source")
        _git(other, "push", "origin", "dev/v1.0.0")
    with pytest.raises(local.CoordinationError):
        local.integrate_proposal(workspace, "agent-a", "task-a", task["id"], **args)
    assert _git(primary, "rev-parse", "HEAD") == args["expected_head"]
    assert local.status(primary)["integration"] is not None


@pytest.mark.parametrize("mutation", ["working-tree", "index", "proposal-head", "branch"])
def test_rechecks_checkout_after_network_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    _, primary, _, workspace, task, args = _proposal(tmp_path)
    original = global_coordination.begin_integration

    def begin(*positional, **keywords):
        result = original(*positional, **keywords)
        if mutation in ("working-tree", "index"):
            (primary / "README.md").write_text("Concurrent edit\n", encoding="utf-8")
            if mutation == "index":
                _git(primary, "add", "README.md")
        elif mutation == "branch":
            _git(primary, "symbolic-ref", "HEAD", "refs/heads/other")
        else:
            _git(workspace, "commit", "--allow-empty", "-qm", "test: changed proposal")
        return result

    monkeypatch.setattr(global_coordination, "begin_integration", begin)
    with pytest.raises((local.CoordinationError, ValueError)):
        local.integrate_proposal(workspace, "agent-a", "task-a", task["id"], **args)
    assert _git(primary, "rev-parse", "dev/v1.0.0") == args["expected_head"]
    assert status(primary)["integration"]["operation"]["phase"] == "running"
    assert local.status(primary)["integration"]["operation"]["phase"] == "running"


@pytest.mark.parametrize("failure", [
    "merge-interrupted", "completion-unreachable", "begin-response-lost",
])
def test_interrupted_integration_preserves_claims_and_freezes_remote_mutations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    _, primary, other, workspace, task, args = _proposal(tmp_path)
    original_git = local._git
    original_begin = global_coordination.begin_integration

    def git(root, *command):
        if "merge" in command and failure == "merge-interrupted":
            raise subprocess.TimeoutExpired("git", 30)
        return original_git(root, *command)

    def finish(*positional, **keywords):
        raise GlobalClaimError("Completion unavailable; inspect before recovery")

    def begin(*positional, **keywords):
        original_begin(*positional, **keywords)
        raise subprocess.TimeoutExpired("git push", 45)

    monkeypatch.setattr(local, "_git", git)
    if failure == "completion-unreachable":
        monkeypatch.setattr(global_coordination, "finish_integration", finish)
    if failure == "begin-response-lost":
        monkeypatch.setattr(global_coordination, "begin_integration", begin)
    with pytest.raises((subprocess.TimeoutExpired, local.CoordinationError)):
        local.integrate_proposal(workspace, "agent-a", "task-a", task["id"], **args)
    expected = (
        args["proposal_head"] if failure == "completion-unreachable" else args["expected_head"]
    )
    assert _git(primary, "rev-parse", "HEAD") == expected
    assert status(other)["integration"]["operation"]["phase"] == "running"
    assert local.status(primary)["integration"]["operation"]["phase"] == "running"
    with pytest.raises(GlobalClaimError, match="unresolved"):
        release_integration(other, "integrator", args["global_integration_id"])
    with pytest.raises(GlobalClaimError, match="unresolved"):
        release(workspace, "agent-a", "task-a", args["global_claim_id"])
    with pytest.raises(local.CoordinationError, match="unresolved"):
        local.release_integration(primary, "integrator", args["integration_id"])
    with pytest.raises(local.CoordinationError, match="Release integration"):
        local.release(workspace, "agent-a", "task-a", task["id"])
    with pytest.raises(local.CoordinationError, match="unresolved"):
        local.integrate_proposal(workspace, "agent-a", "task-a", task["id"], **args)
    # A second independent clone cannot steal leadership or claim unrelated work.
    other_agent = _agent(other, "agent-b", "task-b", "devbox")
    with pytest.raises(GlobalClaimError, match="unresolved"):
        claim(other_agent, "agent-b", "task-b", ["src/b.py"])


def test_independent_clones_cannot_begin_two_operations_at_same_revision(tmp_path: Path) -> None:
    _, primary, other, workspace, task, args = _proposal(tmp_path)
    second = _agent(other, "agent-b", "task-b", "devbox")
    second_claim = claim(second, "agent-b", "task-b", ["src/b.py"])
    revision = status(primary)["revision"]
    barrier = Barrier(2)

    def attempt(root, agent, task_name, task_id, proposal, scope):
        barrier.wait(timeout=10)
        try:
            global_coordination.begin_integration(
                root, agent, task_name, task_id, owner="integrator",
                integration_id=args["global_integration_id"],
                expected_head=args["expected_head"], proposal_head=proposal,
                expected_revision=revision, scope=[scope], paths=[scope],
            )
        except GlobalClaimError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt, workspace, "agent-a", "task-a",
                            args["global_claim_id"], args["proposal_head"], "src/a.py")
        second_result = pool.submit(attempt, second, "agent-b", "task-b",
                                    second_claim["id"], args["expected_head"], "src/b.py")
        assert sorted([first.result(timeout=60), second_result.result(timeout=60)]) == [False, True]
    assert status(primary)["integration"]["operation"]["phase"] == "running"
    assert _git(primary, "rev-parse", "HEAD") == args["expected_head"]
    assert _git(other, "rev-parse", "HEAD") == args["expected_head"]
