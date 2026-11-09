"""Focused regression checks for the hosted release scope planner."""

from __future__ import annotations

from tools.release_validation_scope import ChangeScope, classify_paths, plan_validation


def test_only_documentation_or_independent_tests_can_reuse_source_evidence(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tools.release_validation_scope.baseline_is_valid",
        lambda repository, sha, token: True,
    )
    scope = plan_validation(
        ["README.md", "docs/CHANGELOG.md", "tests/test_release_notes.py"],
        repository="owner/repo", base_sha="a" * 40, token=None,
    )
    assert scope.full is False
    assert "tests/test_release_notes.py" in scope.test_targets
    assert "tests/test_release_metadata.py" in scope.test_targets
    assert "tests/test_web.py::test_changes_page_renders_canonical_release_history" in (
        scope.test_targets
    )


def test_runtime_build_ci_or_shared_test_changes_fail_closed() -> None:
    for paths in (
        [],
        ["src/infinity_db/web/static/page-navigation.js"],
        ["data/generated/rules.db"],
        ["pyproject.toml"],
        [".github/workflows/source-checks.yml"],
        ["tests/conftest.py"],
        ["tools/release_validation_scope.py"],
        ["tests/fixtures/sample.json"],
    ):
        assert classify_paths(paths).full, paths


def test_missing_green_baseline_forces_full_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        "tools.release_validation_scope.baseline_is_valid",
        lambda repository, sha, token: False,
    )
    assert plan_validation(
        ["README.md"], repository="owner/repo", base_sha="a" * 40, token=None,
    ) == ChangeScope(True, "baseline has no complete hosted release evidence", ())


def test_docs_only_still_runs_release_metadata_and_history_checks() -> None:
    scope = classify_paths(["docs/architecture.md"])
    assert scope.full is False
    assert "tests/test_release_notes.py" in scope.test_targets
    assert "tests/test_release_metadata.py" in scope.test_targets
