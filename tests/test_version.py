"""Tests for development version display behavior."""

import tomllib
from pathlib import Path

import infinity_army_data


def test_display_version_uses_release_version_for_a_clean_checkout(monkeypatch) -> None:
    monkeypatch.delenv("INFINITY_DB_DISPLAY_VERSION", raising=False)
    monkeypatch.setattr(
        infinity_army_data, "_source_checkout_has_unreleased_changes", lambda: False
    )

    assert infinity_army_data._display_version() == infinity_army_data.__version__


def test_display_version_marks_an_unreleased_checkout_as_development(monkeypatch) -> None:
    monkeypatch.delenv("INFINITY_DB_DISPLAY_VERSION", raising=False)
    monkeypatch.setattr(
        infinity_army_data, "_source_checkout_has_unreleased_changes", lambda: True
    )

    assert infinity_army_data._display_version() == f"{infinity_army_data.__version__}+dev"


def test_display_version_prefers_explicit_runtime_value(monkeypatch) -> None:
    monkeypatch.setenv("INFINITY_DB_DISPLAY_VERSION", "custom-display-version")
    monkeypatch.setattr(
        infinity_army_data, "_source_checkout_has_unreleased_changes", lambda: False
    )

    assert infinity_army_data._display_version() == "custom-display-version"


def test_untracked_files_do_not_mark_a_tagged_release_as_development(
    monkeypatch, tmp_path,
) -> None:
    monkeypatch.delenv("INFINITY_DB_DISPLAY_VERSION", raising=False)
    monkeypatch.setattr(infinity_army_data, "_repository_root", lambda: tmp_path)

    def git_output(repository, *args):
        assert repository == tmp_path
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        if args == ("rev-list", "--count", f"v{infinity_army_data.__version__}..HEAD"):
            return "0"
        raise AssertionError(f"Unexpected Git command: {args}")

    monkeypatch.setattr(infinity_army_data, "_git_output", git_output)
    assert infinity_army_data._display_version() == infinity_army_data.__version__


def test_tracked_changes_still_mark_a_tagged_release_as_development(
    monkeypatch, tmp_path,
) -> None:
    monkeypatch.delenv("INFINITY_DB_DISPLAY_VERSION", raising=False)
    monkeypatch.setattr(infinity_army_data, "_repository_root", lambda: tmp_path)

    def git_output(repository, *args):
        assert repository == tmp_path
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return " M src/infinity_db/__init__.py"
        raise AssertionError(f"Unexpected Git command: {args}")

    monkeypatch.setattr(infinity_army_data, "_git_output", git_output)
    assert infinity_army_data._display_version() == f"{infinity_army_data.__version__}+dev"


def test_commits_after_the_version_tag_are_unreleased(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(infinity_army_data, "_git_output", lambda *_: "3")

    assert infinity_army_data._has_commits_after_version_tag(tmp_path)


def test_version_tag_at_head_has_no_unreleased_commits(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(infinity_army_data, "_git_output", lambda *_: "0")

    assert not infinity_army_data._has_commits_after_version_tag(tmp_path)


def test_project_metadata_matches_runtime_version() -> None:
    project_root = Path(__file__).resolve().parents[1]
    with (project_root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["version"] == infinity_army_data.__version__
