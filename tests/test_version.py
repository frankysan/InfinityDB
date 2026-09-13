"""Tests for development version display behavior."""

import infinity_army_data


def test_display_version_uses_release_version_for_a_clean_worktree(monkeypatch) -> None:
    monkeypatch.setattr(infinity_army_data, "_working_tree_has_changes", lambda: False)

    assert infinity_army_data._display_version() == infinity_army_data.__version__


def test_display_version_marks_a_changed_worktree_as_development(monkeypatch) -> None:
    monkeypatch.setattr(infinity_army_data, "_working_tree_has_changes", lambda: True)

    assert infinity_army_data._display_version() == f"{infinity_army_data.__version__}+dev"
