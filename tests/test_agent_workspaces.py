"""Cross-tool agent workspace safety checks (no MCP dependency)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools.agent_workspaces import WorkspaceError, create, guard


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "InfinityDB"
    root.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=dev/v1.0.0", str(root)],
        check=True, capture_output=True,
    )
    _git(root, "config", "user.name", "Test Agent")
    _git(root, "config", "user.email", "agent@example.invalid")
    (root / ".gitignore").write_text("/local/\n", encoding="utf-8")
    (root / "README.md").write_text("Initial content.\n", encoding="utf-8")
    _git(root, "add", ".gitignore", "README.md")
    _git(root, "commit", "-qm", "test: seed workspace fixture")
    return root, _git(root, "rev-parse", "HEAD")


def test_create_isolated_worktree_does_not_move_primary(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    result = create(root, "copilot-01", "V1S-082", machine="win-dev")
    agent = Path(result["path"])
    assert agent == tmp_path / "InfinityDB-agent-win-dev-copilot-01-v1s-082"
    assert _git(root, "rev-parse", "HEAD") == head
    assert _git(root, "symbolic-ref", "--short", "HEAD") == "dev/v1.0.0"
    assert _git(root, "status", "--porcelain") == ""
    assert _git(agent, "rev-parse", "HEAD") == head
    assert _git(agent, "symbolic-ref", "--short", "HEAD") == result["branch"]
    assert result["branch"] == "agent/win-dev/copilot-01/v1s-082"
    assert json.loads((agent / "local/agent-workspace.json").read_text())["baseline"] == head
    assert _git(agent, "status", "--porcelain") == ""
    assert guard(agent, "copilot-01", "V1S-082")["head"] == head
    (agent / "README.md").write_text("Changed only in agent workspace.\n", encoding="utf-8")
    assert (root / "README.md").read_text(encoding="utf-8") == "Initial content.\n"


@pytest.mark.parametrize("dirty", ["tracked", "untracked"])
def test_create_refuses_dirty_primary(tmp_path: Path, dirty: str) -> None:
    root, _ = _repo(tmp_path)
    if dirty == "tracked":
        (root / "README.md").write_text("Other agent's work\n", encoding="utf-8")
    else:
        (root / "untracked.md").write_text("Other work\n", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="not clean"):
        create(root, "agent-a", "V1S-082", machine="win-dev")
    assert not list(tmp_path.glob("InfinityDB-agent-*"))


def test_create_refuses_duplicate_branch_and_destination(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    create(root, "agent-a", "V1S-082", machine="win-dev")
    with pytest.raises(WorkspaceError, match="already exists"):
        create(root, "agent-a", "V1S-082", machine="win-dev")
    assert len(list(tmp_path.glob("InfinityDB-agent-*"))) == 1


def test_guard_fails_closed_on_primary_wrong_owner_and_branch(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    with pytest.raises(WorkspaceError, match="Missing agent ownership"):
        guard(root, "agent-a")
    result = create(root, "agent-a", "V1S-082", machine="win-dev")
    agent = Path(result["path"])
    with pytest.raises(WorkspaceError, match="owner or task"):
        guard(agent, "agent-b")
    with pytest.raises(WorkspaceError, match="owner or task"):
        guard(agent, "agent-a", "V1S-099")
    _git(agent, "checkout", "--detach")
    with pytest.raises(WorkspaceError, match="branch or metadata"):
        guard(agent, "agent-a")


def test_cannot_spawn_from_an_agent_checkout(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    result = create(root, "agent-a", "V1S-082", machine="win-dev")
    with pytest.raises(WorkspaceError, match="primary InfinityDB"):
        create(Path(result["path"]), "agent-b", "V1S-083", machine="win-dev")


def test_create_refuses_wrong_primary_branch(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    _git(root, "switch", "-c", "integration-experiment")
    with pytest.raises(WorkspaceError, match="Primary checkout must be"):
        create(root, "agent-a", "V1S-082", machine="win-dev")
