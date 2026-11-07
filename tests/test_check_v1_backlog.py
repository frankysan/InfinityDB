from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools.check_v1_backlog import (
    BacklogAnalysis,
    analyze_backlog,
    audit_pending_retirements,
    audit_retirements,
    main,
    review_selection,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, text=True,
        capture_output=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "InfinityDB"
    root.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--initial-branch=main", str(root)],
        check=True, capture_output=True,
    )
    _git(root, "config", "user.name", "Test Agent")
    _git(root, "config", "user.email", "agent@example.invalid")
    backlog = root / "docs" / "TODO.md"
    backlog.parent.mkdir()
    backlog.write_text(_todo(1, 2, 3), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "Seed V1S backlog")
    return root, _git(root, "rev-parse", "HEAD")


def _todo(*numbers: int) -> str:
    return (
        "# Backlog\n### Pre-planned 1.0 execution slices\n"
        "#### Workstream\n"
        + "".join(
            f"- [ ] V1S-{number:03d} (S, test): Task {number}.\n"
            for number in numbers
        )
    )


def _analyze(markdown: str) -> BacklogAnalysis:
    return analyze_backlog(markdown, source="docs/TODO.md")


def test_git_retirement_accepts_cited_id_and_evidence(tmp_path: Path) -> None:
    root, base = _repo(tmp_path)
    (root / "docs" / "TODO.md").write_text(_todo(2, 3), encoding="utf-8")
    (root / "docs" / "testing.md").write_text("Accepted test results.\n", encoding="utf-8")
    _git(root, "add", "docs/TODO.md", "docs/testing.md")
    _git(root, "commit", "-qm", "docs: close V1S-001 after tests/test_audit.py")
    assert audit_retirements(base, repository=root, enforce=True) == ()


@pytest.mark.parametrize("enforce", [False, True])
def test_git_retirement_requires_each_id_and_advises_evidence(
    tmp_path: Path, enforce: bool,
) -> None:
    root, base = _repo(tmp_path)
    (root / "docs" / "TODO.md").write_text(_todo(2, 3), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: shorten the backlog")
    report = audit_retirements(base, repository=root, enforce=enforce)
    assert [item.code for item in report] == ["V1B005", "V1B006"]
    assert report[0].severity == ("error" if enforce else "warning")
    assert report[1].severity == "warning"


def test_git_retirement_multiple_ids_casefold_and_reorder_are_safe(
    tmp_path: Path,
) -> None:
    root, base = _repo(tmp_path)
    (root / "docs" / "TODO.md").write_text(_todo(3, 2, 1), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: reorder V1S rows")
    assert audit_retirements(base, repository=root, enforce=True) == ()

    (root / "docs" / "TODO.md").write_text(_todo(3), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: close v1s-001 and V1S-002; verified: checks")
    assert audit_retirements(base, repository=root, enforce=True) == ()


def test_git_retirement_does_not_misattribute_first_parent_merges(tmp_path: Path) -> None:
    root, base = _repo(tmp_path)
    _git(root, "checkout", "-qb", "feature")
    (root / "docs" / "TODO.md").write_text(_todo(2, 3), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: close V1S-001 verified: example")
    feature = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-q", "main")
    (root / "docs" / "other.md").write_text("Independent change.\n", encoding="utf-8")
    _git(root, "add", "docs/other.md")
    _git(root, "commit", "-qm", "docs: separate change")
    _git(root, "merge", "-q", "--no-ff", "-m", "Merge feature", "feature")
    assert [item.code for item in audit_retirements(feature, repository=root)] == [
        "V1B008"
    ]
    # A first-parent comparison is still allowed, but never silently
    # attributes the feature's original commit message as the merge's message.
    report = audit_retirements(base, repository=root, enforce=True)
    assert any(item.code == "V1B005" for item in report)


@pytest.mark.parametrize("fault", ["missing-base", "diverged", "invalid-backlog"])
def test_git_retirement_fails_closed_on_invalid_ranges(
    tmp_path: Path, fault: str,
) -> None:
    root, base = _repo(tmp_path)
    if fault == "missing-base":
        assert [item.code for item in audit_retirements(
            "deadbeef" * 5, repository=root
        )] == ["V1B007"]
        return
    if fault == "diverged":
        _git(root, "checkout", "-qb", "feature")
        (root / "docs" / "side.md").write_text("Side history.\n", encoding="utf-8")
        _git(root, "add", "docs/side.md")
        _git(root, "commit", "-qm", "Side commit")
        side = _git(root, "rev-parse", "HEAD")
        _git(root, "checkout", "-q", "main")
        assert [item.code for item in audit_retirements(
            side, base, repository=root
        )] == ["V1B008"]
        return
    (root / "docs" / "TODO.md").write_text(
        _todo(1, 2, 3) + "- [ ] V1S-bad: Malformed.\n",
        encoding="utf-8",
    )
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "Malformed backlog")
    assert [item.code for item in audit_retirements(
        base, repository=root
    )] == ["V1B007"]


def test_git_retirement_reopened_id_does_not_hide_unattributed_removal(
    tmp_path: Path,
) -> None:
    root, base = _repo(tmp_path)
    (root / "docs" / "TODO.md").write_text(_todo(2, 3), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: removed old entry without evidence")
    (root / "docs" / "TODO.md").write_text(_todo(1, 2, 3), encoding="utf-8")
    _git(root, "add", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: reopen V1S-001")
    report = audit_retirements(base, repository=root, enforce=True)
    assert [item.code for item in report] == ["V1B005", "V1B006"]


def test_git_retirement_missing_target_todo_fails_closed(tmp_path: Path) -> None:
    root, base = _repo(tmp_path)
    _git(root, "rm", "docs/TODO.md")
    _git(root, "commit", "-qm", "docs: file accidentally deleted")
    assert [item.code for item in audit_retirements(
        base, repository=root,
    )] == ["V1B007"]


def test_pending_retirement_distinguishes_worktree_index_and_evidence(
    tmp_path: Path,
) -> None:
    root, _ = _repo(tmp_path)
    assert audit_pending_retirements(state="worktree", repository=root) == ()
    assert audit_pending_retirements(state="index", repository=root) == ()
    (root / "docs" / "TODO.md").write_text(_todo(2, 3), encoding="utf-8")
    assert [item.code for item in audit_pending_retirements(
        state="worktree", repository=root,
    )] == ["V1B009", "V1B006"]
    assert audit_pending_retirements(state="index", repository=root) == ()
    _git(root, "add", "docs/TODO.md")
    assert [item.code for item in audit_pending_retirements(
        state="index", repository=root,
    )] == ["V1B009", "V1B006"]
    (root / "docs" / "testing.md").write_text("Verified details.\n", encoding="utf-8")
    _git(root, "add", "docs/testing.md")
    assert [item.code for item in audit_pending_retirements(
        state="index", repository=root,
    )] == ["V1B009"]


def test_pending_retirement_rejects_malformed_worktree_and_invalid_state(
    tmp_path: Path,
) -> None:
    root, _ = _repo(tmp_path)
    (root / "docs" / "TODO.md").write_text(
        _todo(1) + "- [ ] V1S-bad: Incorrect declaration.\n",
        encoding="utf-8",
    )
    assert [item.code for item in audit_pending_retirements(
        state="worktree", repository=root,
    )] == ["V1B007"]
    with pytest.raises(ValueError, match="Pending closeout state"):
        audit_pending_retirements(state="commit", repository=root)


@pytest.mark.parametrize("arguments", [
    ["--target-state", "worktree"],
    ["--base", "HEAD", "--target-state", "index", "--target", "HEAD~1"],
    ["--enforce-closeout"],
])
def test_retirement_cli_rejects_ambiguous_options(
    arguments: list[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2


def test_selection_orders_earlier_open_ids_across_workstreams() -> None:
    analysis = _analyze("""# Backlog
### Pre-planned 1.0 execution slices
#### Later workstream
- [ ] **V1S-052 (S, review):** Earlier actionable task.
#### First workstream
- [x] **V1S-034 (S, review):** Accepted and checked.
- [ ] **V1S-062 (S, review):** Proposed selection.
#### Middle workstream
- [ ] **V1S-041 (S, review):** Earlier task, source is ambiguous.
""")
    review = review_selection(analysis, "V1S-062")
    assert review.earlier_open == ("V1S-041", "V1S-052")
    assert review.actionable == ("V1S-041", "V1S-052")
    assert review.documented_pauses == ()
    assert [(item.code, item.severity) for item in review.diagnostics] == [
        ("V1B012", "error"),
    ]
    assert "V1S-041, V1S-052" in review.diagnostics[0].message
    assert not review.override_applied


@pytest.mark.parametrize("selected", ["V1S-002", "V1S-003", "V1S-1", "v1s-001"])
def test_selection_rejects_closed_missing_and_malformed_ids(
    selected: str,
) -> None:
    analysis = _analyze("""# Backlog
### Pre-planned 1.0 execution slices
#### Workstream
- [ ] **V1S-001 (S, review):** Open.
- [x] **V1S-002 (S, review):** Closed.
""")
    review = review_selection(analysis, selected)
    assert [item.code for item in review.diagnostics] == ["V1B010"]
    assert review.diagnostics[0].severity == "error"


def test_selection_accepts_only_documented_pauses_and_not_ambiguous_sources() -> None:
    analysis = _analyze("""# Backlog
### Pre-planned 1.0 execution slices
#### First workstream
- [ ] **V1S-034 (S, review):** Need upstream response.
  Blocked: Missing primary-source pages; owner: curator; retry: when SRC-034 is answered.
- [ ] **V1S-041 (S, review):** Release candidate work.
  Deferred: Needs pinned release inputs; authority: release owner; revisit: after source freeze.
#### Second workstream
- [ ] **V1S-052 (S, review):** Work remains possible despite uncertain rules.
#### Final workstream
- [ ] **V1S-062 (S, review):** Proposed task.
""")
    review = review_selection(analysis, "V1S-062")
    assert review.documented_pauses == ("V1S-034", "V1S-041")
    assert review.actionable == ("V1S-052",)
    assert [item.code for item in review.diagnostics] == ["V1B012"]


@pytest.mark.parametrize("annotation", [
    "Blocked: Waiting for clarification; owner: rules reviewer",
    "Blocked: Waiting; owner: rules reviewer; retry: after source update",
    "Deferred: Release milestone; revisit: after input freeze",
    "Deferred: Release milestone; owner: release owner; revisit: soon",
    "Blocked: Need source check; owner: curator; retry: after response "
    "Deferred: Wait for later date; owner: maintainer; revisit: after freeze",
])
def test_selection_incomplete_pauses_remain_actionable(annotation: str) -> None:
    analysis = _analyze(
        "# Backlog\n### Pre-planned 1.0 execution slices\n#### Workstream\n"
        f"- [ ] **V1S-041 (S, review):** Preceding work.\n  {annotation}\n"
        "- [ ] **V1S-062 (S, review):** Selected.\n"
    )
    review = review_selection(analysis, "V1S-062")
    assert review.actionable == ("V1S-041",)
    assert [item.code for item in review.diagnostics] == ["V1B011", "V1B012"]
    assert review.diagnostics[0].severity == "warning"


def test_selection_all_documented_pauses_allow_later_work_without_override() -> None:
    analysis = _analyze("""# Backlog
### Pre-planned 1.0 execution slices
#### First workstream
- [ ] **V1S-034 (S, review):** Blocked by an external answer.
  Blocked: Requires original source erratum; owner: curator; retry: when erratum arrives.
#### Other workstream
- [ ] **V1S-041 (S, review):** Deferred until freeze.
  Deferred: Source rebuild is gated; owner: release owner; revisit: once snapshot is frozen.
- [ ] **V1S-062 (S, review):** Proposed.
""")
    review = review_selection(analysis, "V1S-062")
    assert review.earlier_open == ("V1S-034", "V1S-041")
    assert review.documented_pauses == review.earlier_open
    assert review.actionable == ()
    assert review.diagnostics == ()


def test_selection_priority_requires_matching_durable_reason() -> None:
    reason = "Finish backlog safeguards first"
    analysis = _analyze("""# Backlog
### Pre-planned 1.0 execution slices
#### First workstream
- [ ] **V1S-034 (S, review):** Still open.
#### Final workstream
- [ ] **V1S-062 (S, review):** Selected.
  Priority: Finish backlog safeguards first; authority: user; revisit: after V1S-062 closeout.
""")
    assert analysis.diagnostics == ()
    no_override = review_selection(analysis, "V1S-062")
    assert [item.code for item in no_override.diagnostics] == ["V1B012"]
    selected = review_selection(analysis, "V1S-062", priority_reason=reason)
    assert selected.override_applied
    assert [item.code for item in selected.diagnostics] == ["V1B014"]
    assert selected.diagnostics[0].severity == "warning"
    assert selected.actionable == ("V1S-034",)
    for invalid in ("", "User requested", reason + " and other changes"):
        rejected = review_selection(analysis, "V1S-062", priority_reason=invalid)
        assert [item.code for item in rejected.diagnostics] == ["V1B013", "V1B012"]


@pytest.mark.parametrize("annotation", [
    "",
    "Priority: Complete requested backlog safeguards before final candidate",
    "Priority: Complete requested backlog safeguards before final candidate; "
    "authority: user",
    "Priority: Complete requested backlog safeguards before final candidate; "
    "authority: user; revisit: soon",
])
def test_priority_override_without_complete_durable_note_is_refused(
    annotation: str,
) -> None:
    analysis = _analyze(
        "# Backlog\n### Pre-planned 1.0 execution slices\n#### Workstream\n"
        "- [ ] **V1S-034 (S, review):** Preceding.\n"
        f"- [ ] **V1S-062 (S, review):** Chosen.\n  {annotation}\n"
    )
    report = review_selection(
        analysis, "V1S-062",
        priority_reason="Complete requested backlog safeguards before final candidate",
    )
    assert not report.override_applied
    assert [item.code for item in report.diagnostics] == ["V1B013", "V1B012"]


def test_selection_cli_reports_earlier_open_and_explicit_override(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    reason = "Finish the user-requested backlog checker first"
    todo = tmp_path / "selected.md"
    todo.write_text(
        "# Backlog\n### Pre-planned 1.0 execution slices\n#### First\n"
        "- [ ] **V1S-041 (S, review):** Other task.\n"
        "#### Second\n"
        "- [ ] **V1S-062 (S, review):** Selected task.\n"
        f"  Priority: {reason}; authority: user; "
        "revisit: when this selected task is completed.\n",
        encoding="utf-8",
    )
    assert main(["--todo", str(todo), "--select", "V1S-062"]) == 1
    assert "Earliest actionable: V1S-041" in capsys.readouterr().out
    assert main([
        "--todo", str(todo), "--select", "V1S-062",
        "--priority-reason", reason,
    ]) == 0
    output = capsys.readouterr().out
    assert "Priority override: explicitly documented" in output
    assert "V1S-041" in output


def test_selection_cli_rejects_priority_without_selection() -> None:
    with pytest.raises(SystemExit) as error:
        main(["--priority-reason", "User requested work"])
    assert error.value.code == 2


def test_json_cli_reports_selection_failure_without_console_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(_todo(34, 62), encoding="utf-8")
    assert main(["--todo", str(todo), "--select", "V1S-062", "--json"]) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert captured.err == ""
    assert payload["formatVersion"] == 1
    assert payload["status"] == "fail"
    assert payload["declarations"] == 2
    assert payload["errors"] == 1
    assert payload["warnings"] == 0
    assert [item["code"] for item in payload["diagnostics"]] == ["V1B012"]
    assert payload["selection"] == {
        "selected": "V1S-062",
        "earlierOpen": ["V1S-034"],
        "documentedPauses": [],
        "actionable": ["V1S-034"],
        "overrideApplied": False,
    }


def test_json_cli_preserves_warning_success_and_file_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    reason = "Finish requested backlog audit first"
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "# Backlog\n### Pre-planned 1.0 execution slices\n#### Workstream\n"
        "- [ ] **V1S-034 (S, review):** An earlier task.\n"
        "- [ ] **V1S-062 (S, review):** Current task.\n"
        f"  Priority: {reason}; authority: user; revisit: after auditor acceptance.\n",
        encoding="utf-8",
    )
    assert main([
        "--todo", str(todo), "--select", "V1S-062",
        "--priority-reason", reason, "--json",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["errors"] == 0
    assert payload["warnings"] == 1
    assert payload["selection"]["overrideApplied"] is True
    assert payload["diagnostics"][0]["code"] == "V1B014"

    assert main(["--todo", str(tmp_path / "missing.md"), "--json"]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "error"
    assert missing["formatVersion"] == 1
    assert "Unable to read backlog" in missing["message"]


def test_duplicate_and_malformed_v1s_declarations_have_stable_diagnostics() -> None:
    result = _analyze(
        """# Backlog
### Pre-planned 1.0 execution slices
#### Workstream
- [ ] **V1S-001 (S, review):** First declaration.
- [ ] **V1S-001 (S, review):** Duplicate declaration.
- [ ] **V1S-1 (S, review):** Malformed identifier.
"""
    )

    assert [(item.code, item.severity, item.line) for item in result.diagnostics] == [
        ("V1B001", "error", 5),
        ("V1B002", "error", 6),
    ]


def test_valid_numeric_gaps_are_not_reported_as_missing_tasks() -> None:
    result = _analyze(
        """# Backlog
### Pre-planned 1.0 execution slices
#### Workstream
- [ ] **V1S-001 (S, review):** First declaration.
- [ ] **V1S-003 (S, review):** Third declaration.
"""
    )

    assert [task.task_id for task in result.tasks] == ["V1S-001", "V1S-003"]
    assert result.diagnostics == ()


def test_nested_checked_items_allow_checked_descendants() -> None:
    result = _analyze(
        """# Backlog
### Pre-planned 1.0 execution slices
#### Workstream
- [x] **V1S-001 (S, review):** Completed parent.
  - [x] Supporting checklist item.
    - [x] **V1S-002 (S, review):** Completed nested slice.
"""
    )

    assert [task.task_id for task in result.tasks] == ["V1S-001", "V1S-002"]
    assert result.diagnostics == ()


def test_checked_v1s_parent_rejects_open_nested_descendant() -> None:
    result = _analyze(
        """# Backlog
### Pre-planned 1.0 execution slices
#### Workstream
- [x] **V1S-001 (S, review):** Contradictory parent.
  - [x] Supporting checklist item.
    - [ ] **V1S-002 (S, review):** Still open.
"""
    )

    assert [(item.code, item.severity, item.line) for item in result.diagnostics] == [
        ("V1B003", "error", 6),
    ]


def test_prose_links_code_and_out_of_scope_mentions_are_not_declarations() -> None:
    result = _analyze(
        """# Backlog
Mention V1S-001 and [V1S-002](#v1s-002) in prose.
### Pre-planned 1.0 execution slices
#### Workstream
- [ ] **V1S-003 (S, review):** Actual declaration.
The earlier ID V1S-004 is only a reference.
`- [ ] **V1S-005 (S, review):** Inline code.`
```markdown
- [ ] **V1S-006 (S, review):** Fenced example.
```
### Post-1.0 work
- [ ] **V1S-007 (S, review):** Outside the active register.
"""
    )

    assert [task.task_id for task in result.tasks] == ["V1S-003"]
    assert result.diagnostics == ()
