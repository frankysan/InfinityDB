"""Current active-backlog checks, separate from the historical V1S register."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.ci import check_v1_backlog as checker


def test_active_checkboxes_include_unnumbered_parents_and_children() -> None:
    markdown = """# Backlog
## Active development
- [x] Completed parent.
  - [x] Completed child.
    - [ ] Open grandchild.
- [ ] **TASK-001:** First task.
### Another workstream
- [ ] TASK-001: Duplicate task.
Prose mentioning TASK-002 is not a task.
```markdown
- [ ] TASK-001: Example only.
```
## History
- [x] Done.
  - [ ] Archived open item.
"""
    analysis = checker.analyze_active_backlog(markdown)
    assert len(analysis.tasks) == 5
    assert [(item.code, item.line) for item in analysis.diagnostics] == [
        ("BKL002", 5), ("BKL001", 8),
    ]
    assert analysis.tasks[3].task_id == "TASK-001"


def test_checked_parent_under_noncheckbox_bullet_is_rejected() -> None:
    markdown = """## Active development
- [x] Finished parent.
  - Notes grouping
    - [ ] Still pending.
"""
    report = checker.analyze_active_backlog(markdown)
    assert [item.code for item in report.diagnostics] == ["BKL002"]


def test_active_titles_and_anchors_are_not_task_identifiers() -> None:
    markdown = """## Active development
- [ ] Implement thing (see SRC-001).
- [ ] **Improve release policy**, citing SRC-001.
- [ ] **TASK-1234** Explicit identity.
### Another area
- [ ] task-1234: Duplicate regardless of case.
"""
    report = checker.analyze_active_backlog(markdown)
    assert [task.task_id for task in report.tasks] == [
        None, None, "TASK-1234", "TASK-1234",
    ]
    assert [item.code for item in report.diagnostics] == ["BKL001"]


def test_unfinished_removals_are_advisory_and_edits_do_not_count() -> None:
    before = """## Active development
- [ ] TASK-001: Stable task.
- [ ] An unnamed task with several useful details.
  - [ ] Nested unfinished step.
- [ ] A long task whose wording is slightly adjusted.
"""
    after = """## Active development
- [ ] TASK-002: Replacement task.
- [ ] An unnamed task with several useful details.
- [ ] A long task whose wording is adjusted slightly.
"""
    report = checker.review_active_removals(before, after)
    assert [item.code for item in report] == ["BKL003", "BKL003"]
    assert [item.severity for item in report] == ["warning", "warning"]
    assert "TASK-001" in report[0].message
    assert "Nested unfinished" in report[1].message


def test_removed_parent_does_not_repeat_descendant_warnings() -> None:
    before = """## Active development
- [ ] Major task.
  - [ ] Unfinished subtask.
    - [ ] Sub-subtask.
"""
    report = checker.review_active_removals(before, "## Active development\n")
    assert len(report) == 1
    assert report[0].line == 2


def test_cli_reports_active_errors_without_changing_legacy_result(
    tmp_path: Path, capsys,
) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "## Active development\n- [x] Completed.\n"
        "  - [ ] Open.\n- [ ] TASK-001: A.\n- [ ] TASK-001: B.\n",
        encoding="utf-8",
    )
    assert checker.main(["--todo", str(todo), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["declarations"] == 0
    assert report["activeTasks"] == 4
    assert [entry["code"] for entry in report["diagnostics"]] == [
        "BKL002", "BKL001",
    ]


def test_default_docs_check_advises_on_pending_removal(
    tmp_path: Path, capsys, monkeypatch,
) -> None:
    root = tmp_path / "repo"
    docs = root / "docs"
    docs.mkdir(parents=True)
    todo = docs / "TODO.md"
    todo.write_text("## Active development\n- [ ] TASK-001: Pending.\n", encoding="utf-8")
    subprocess.run(
        ["git", "init", "-q", str(root)], check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "add", "docs/TODO.md"], check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Test", "-c",
         "user.email=test@example.invalid", "commit", "-qm", "Seed backlog"],
        check=True, capture_output=True,
    )
    todo.write_text("## Active development\n", encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", root)
    assert checker.main(["--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [entry["code"] for entry in report["diagnostics"]] == ["BKL003"]
    assert report["warnings"] == 1
