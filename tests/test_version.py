"""Tests for development version display behavior."""

import infinity_army_data


def test_display_version_uses_release_version_for_a_clean_checkout(monkeypatch) -> None:
    monkeypatch.setattr(
        infinity_army_data, "_source_checkout_has_unreleased_changes", lambda: False
    )

    assert infinity_army_data._display_version() == infinity_army_data.__version__


def test_display_version_marks_an_unreleased_checkout_as_development(monkeypatch) -> None:
    monkeypatch.setattr(infinity_army_data, "_source_checkout_has_unreleased_changes", lambda: True)

    assert infinity_army_data._display_version() == f"{infinity_army_data.__version__}+dev"


def test_commits_after_the_version_tag_are_unreleased(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(infinity_army_data, "_git_output", lambda *_: "3")

    assert infinity_army_data._has_commits_after_version_tag(tmp_path)


def test_version_tag_at_head_has_no_unreleased_commits(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(infinity_army_data, "_git_output", lambda *_: "0")

    assert not infinity_army_data._has_commits_after_version_tag(tmp_path)
