from __future__ import annotations

from tools.check_v1_backlog import BacklogAnalysis, analyze_backlog


def _analyze(markdown: str) -> BacklogAnalysis:
    return analyze_backlog(markdown, source="docs/TODO.md")


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
