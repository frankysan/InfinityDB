"""Offline GitHub-event ancestry contracts for the V1S CI closeout helper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools.check_v1_backlog_ci import choose_ci_range, main

ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, check=True, text=True,
    ).stdout.strip()


def _todo(*numbers: int) -> str:
    return (
        "# Backlog\n### Pre-planned 1.0 execution slices\n#### Workstream\n"
        + "".join(
            f"- [ ] **V1S-{number:03d} (S, review):** Task {number}.\n"
            for number in numbers
        )
    )


def _repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "InfinityDB"
    root.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=main", str(root)],
        check=True, capture_output=True,
    )
    _git(root, "config", "user.name", "Test CI")
    _git(root, "config", "user.email", "ci@example.invalid")
    todo = root / "docs" / "TODO.md"
    todo.parent.mkdir()
    todo.write_text(_todo(1, 2, 3), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "Initial register")
    return root, _git(root, "rev-parse", "HEAD")


def _new_commit(root: Path, name: str, content: str, message: str) -> str:
    target = root / "docs" / name
    target.parent.mkdir(exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(root, "add", f"docs/{name}")
    _git(root, "commit", "-qm", message)
    return _git(root, "rev-parse", "HEAD")


def test_ci_push_rejects_non_first_parent_before_and_wrong_checkout(
    tmp_path: Path,
) -> None:
    root, initial = _repository(tmp_path)
    latest = _new_commit(root, "notes.md", "Review.\n", "docs: write notes")
    audit_range = choose_ci_range(
        "push", {"before": initial, "after": latest}, latest, repository=root,
    )
    assert (audit_range.base, audit_range.target, audit_range.origin) == (
        initial, latest, "push",
    )
    assert audit_range.complete
    with pytest.raises(ValueError, match="checked-out"):
        choose_ci_range(
            "push", {"before": initial, "after": latest}, initial, repository=root,
        )
    with pytest.raises(ValueError, match="invalid push before"):
        choose_ci_range(
            "push", {"before": "not-a-sha", "after": latest}, latest, repository=root,
        )
    with pytest.raises(ValueError, match="first-parent"):
        choose_ci_range(
            "push", {"before": "0" * 40, "after": latest}, latest, repository=root,
        )


@pytest.mark.parametrize("attributed", [True, False])
def test_ci_push_adoption_merge_audits_full_feature_history(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], attributed: bool,
) -> None:
    root, old_main = _repository(tmp_path)
    _new_commit(root, "TODO.md", "# Legacy backlog without a V1S register\n",
                "docs: legacy backlog")
    old_main = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-qb", "feature")
    adoption = _new_commit(root, "TODO.md", _todo(1, 2),
                           "feat: adopt V1S retirement check")
    message = ("docs: retire V1S-001 verified: tests/test_audit.py"
               if attributed else "docs: shorten backlog")
    feature = _new_commit(root, "TODO.md", _todo(2), message)
    _git(root, "checkout", "-q", "main")
    _git(root, "merge", "-q", "--no-ff", "-m", "Merge feature", "feature")
    merged = _git(root, "rev-parse", "HEAD")

    event = {"before": old_main, "after": merged}
    selected = choose_ci_range("push", event, merged, repository=root,
                               adoption_base=adoption)
    assert (selected.base, selected.target, selected.integrated_target) == (
        adoption, feature, merged,
    )
    assert selected.origin == "push-feature-merge"
    assert selected.complete

    event_path = tmp_path / "merge-event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    env = {"GITHUB_EVENT_NAME": "push", "GITHUB_SHA": merged,
           "GITHUB_EVENT_PATH": str(event_path)}
    assert main(env, repository=root, adoption_base=adoption) == (0 if attributed else 1)
    report = capsys.readouterr().out
    assert f"integrated as {merged[:12]}" in report
    assert ("V1S CI retirement: PASS" if attributed else "V1B005") in report


def test_ci_push_adoption_merge_refuses_unreviewed_merge_resolution(
    tmp_path: Path,
) -> None:
    root, _ = _repository(tmp_path)
    _new_commit(root, "TODO.md", "# Legacy backlog\n", "docs: legacy backlog")
    old_main = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-qb", "feature")
    adoption = _new_commit(root, "TODO.md", _todo(1, 2), "feat: adopt V1S checks")
    _git(root, "checkout", "-q", "main")
    _git(root, "merge", "-q", "--no-ff", "--no-commit", "feature")
    (root / "docs" / "TODO.md").write_text(_todo(2), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "Merge feature with unreviewed TODO changes")
    merged = _git(root, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="merge changed the audited V1S backlog"):
        choose_ci_range("push", {"before": old_main, "after": merged},
                        merged, repository=root, adoption_base=adoption)


def test_ci_push_legacy_without_adopted_merge_fails_closed(tmp_path: Path) -> None:
    root, _ = _repository(tmp_path)
    _new_commit(root, "TODO.md", "# Legacy backlog\n", "docs: legacy backlog")
    old_main = _git(root, "rev-parse", "HEAD")
    latest = _new_commit(root, "TODO.md", _todo(1), "docs: add new register")
    with pytest.raises(ValueError, match="direct two-parent merge"):
        choose_ci_range("push", {"before": old_main, "after": latest},
                        latest, repository=root)


def test_ci_push_merges_approved_development_closeout_without_requiring_id_in_merge_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    root, common = _repository(tmp_path)
    _git(root, "checkout", "-qb", "feature")
    feature = _new_commit(root, "TODO.md", _todo(2, 3),
                          "docs: transfer V1S-001; evidence: docs/releasing.md")
    _git(root, "checkout", "-q", "main")
    old_main = _new_commit(root, "notes.md", "Main change.\n", "docs: main notes")
    _git(root, "merge", "-q", "--no-ff", "-m", "Merge feature", "feature")
    merged = _git(root, "rev-parse", "HEAD")

    selected = choose_ci_range(
        "push", {"before": old_main, "after": merged}, merged, repository=root,
    )
    assert (selected.base, selected.target, selected.integrated_target) == (
        common, feature, merged,
    )
    assert selected.origin == "push-feature-merge"
    event_path = tmp_path / "merge-event.json"
    event_path.write_text(json.dumps({
        "before": old_main, "after": merged,
    }), encoding="utf-8")
    env = {"GITHUB_EVENT_NAME": "push", "GITHUB_SHA": merged,
           "GITHUB_EVENT_PATH": str(event_path)}
    assert main(env, repository=root) == 0
    assert "V1S CI retirement: PASS" in capsys.readouterr().out


def test_ci_pr_uses_head_first_parent_not_synthetic_merge_ref(
    tmp_path: Path,
) -> None:
    root, initial = _repository(tmp_path)
    _git(root, "checkout", "-qb", "feature")
    feature = _new_commit(root, "feature.md", "Feature.\n", "docs: feature")
    _git(root, "checkout", "-q", "main")
    base = _new_commit(root, "main.md", "Base.\n", "docs: main")
    _git(root, "checkout", "-q", "feature")
    _git(root, "merge", "-q", "--no-ff", "-m", "Merge main", "main")
    head = _git(root, "rev-parse", "HEAD")
    event = {"pull_request": {
        "head": {"sha": head}, "base": {"sha": base},
    }}
    earliest = choose_ci_range(
        "pull_request", event, head, repository=root, adoption_base=initial,
    )
    assert earliest.base == initial
    assert earliest.target == head
    assert earliest.origin == "pull_request"
    assert earliest.complete

    adopted = choose_ci_range(
        "pull_request", event, head, repository=root, adoption_base=feature,
    )
    assert adopted.base == feature
    assert adopted.target == head
    with pytest.raises(ValueError, match="missing head/base"):
        choose_ci_range(
            "pull_request", {"pull_request": {"head": {}}},
            head, repository=root,
        )


def test_ci_manual_explicit_adoption_and_limited_fallback(
    tmp_path: Path,
) -> None:
    root, initial = _repository(tmp_path)
    head = _new_commit(root, "notes.md", "Review.\n", "docs: review")
    explicit = choose_ci_range(
        "workflow_dispatch", {"inputs": {"backlog_base": initial}},
        head, repository=root,
    )
    assert (explicit.base, explicit.target, explicit.origin, explicit.complete) == (
        initial, head, "manual-explicit", True,
    )
    adopted = choose_ci_range(
        "workflow_dispatch", {"inputs": {}}, head, repository=root,
        adoption_base=initial,
    )
    assert adopted.base == initial
    assert adopted.origin == "manual-adoption"
    assert adopted.complete

    limited = choose_ci_range(
        "workflow_dispatch", {}, head, repository=root,
        adoption_base="f" * 40,
    )
    assert limited.base == initial
    assert limited.target == head
    assert limited.origin == "manual-last-commit"
    assert not limited.complete

    with pytest.raises(ValueError, match="manual backlog base"):
        choose_ci_range(
            "workflow_dispatch", {"inputs": {"backlog_base": "x" * 40}},
            head, repository=root,
        )
    with pytest.raises(ValueError, match="first-parent"):
        choose_ci_range(
            "workflow_dispatch", {"inputs": {"backlog_base": "0" * 40}},
            head, repository=root,
        )


def test_ci_event_entrypoint_rejects_unaccounted_removal_and_accepts_closeout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    root, initial = _repository(tmp_path)
    missing_id = _new_commit(
        root, "TODO.md", _todo(2, 3), "docs: removed an entry without evidence",
    )
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({
        "before": initial, "after": missing_id,
    }), encoding="utf-8")
    environment = {
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_SHA": missing_id,
        "GITHUB_EVENT_PATH": str(event_path),
    }
    assert main(environment, repository=root) == 1
    result = capsys.readouterr()
    assert "V1B005" in result.out
    assert "V1S CI retirement: FAIL" in result.out

    accepted = _new_commit(
        root, "TODO.md", _todo(3), "docs: close V1S-002 verified: tests/test_audit.py",
    )
    event_path.write_text(json.dumps({
        "before": missing_id, "after": accepted,
    }), encoding="utf-8")
    environment["GITHUB_SHA"] = accepted
    assert main(environment, repository=root) == 0
    assert "V1S CI retirement: PASS" in capsys.readouterr().out


def test_ci_entrypoint_fail_closed_on_missing_event_invalid_target_and_no_todo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    root, initial = _repository(tmp_path)
    event_path = tmp_path / "event.json"
    env = {
        "GITHUB_EVENT_NAME": "push", "GITHUB_SHA": initial,
        "GITHUB_EVENT_PATH": str(event_path),
    }
    assert main(env, repository=root) == 2
    assert "SETUP ERROR" in capsys.readouterr().err

    event_path.write_text("{invalid", encoding="utf-8")
    assert main(env, repository=root) == 2
    assert "SETUP ERROR" in capsys.readouterr().err

    event_path.write_text(json.dumps({
        "before": initial, "after": "0" * 40,
    }), encoding="utf-8")
    assert main(env, repository=root) == 2
    assert "SETUP ERROR" in capsys.readouterr().err

    _git(root, "rm", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: accidentally delete TODO")
    deleted = _git(root, "rev-parse", "HEAD")
    event_path.write_text(json.dumps({
        "before": initial, "after": deleted,
    }), encoding="utf-8")
    env["GITHUB_SHA"] = deleted
    assert main(env, repository=root) == 2
    assert "SETUP ERROR" in capsys.readouterr().err


def test_ci_source_workflow_checks_history_with_full_checkout() -> None:
    workflow = (ROOT / ".github" / "workflows" / "source-checks.yml").read_text(
        encoding="utf-8",
    )
    assert "fetch-depth: 0" in workflow
    assert "python -m tools.check_v1_backlog_ci" in workflow
    assert "if: matrix.check_args == '--all'" in workflow
    assert "backlog_base:" in workflow
