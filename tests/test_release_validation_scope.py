"""Focused regression checks for the hosted release scope planner."""

from __future__ import annotations

from tools.ci import release_validation_scope
from tools.ci.prepare_release_ci_evidence import ReleaseEvidenceError, ReusedReleaseEvidence
from tools.ci.release_validation_scope import ChangeScope, classify_paths, plan_validation


def test_only_documentation_or_independent_tests_can_reuse_source_evidence(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tools.ci.release_validation_scope.baseline_is_valid",
        lambda repository, sha, token: True,
    )
    scope = plan_validation(
        ["README.md", "docs/CHANGELOG.md", "tests/test_release_notes.py"],
        repository="owner/repo", base_sha="a" * 40, token=None,
    )
    assert scope.full is False
    assert "tests/test_release_notes.py" in scope.test_targets
    assert "tests/test_release_metadata.py" not in scope.test_targets
    assert "tests/test_web.py::test_changes_page_renders_canonical_release_history" in (
        scope.test_targets
    )


def test_runtime_build_ci_or_shared_test_changes_fail_closed() -> None:
    for paths in (
        [],
        ["src/infinity_db/web/static/page-navigation.js"],
        ["data/generated/rules_n5.db"],
        ["pyproject.toml"],
        [".github/workflows/source-checks.yml"],
        ["tests/conftest.py"],
        ["tools/release_validation_scope.py"],
        ["tests/fixtures/sample.json"],
    ):
        assert classify_paths(paths).full, paths


def test_missing_green_baseline_forces_full_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        "tools.ci.release_validation_scope.baseline_is_valid",
        lambda repository, sha, token: False,
    )
    assert plan_validation(
        ["README.md"], repository="owner/repo", base_sha="a" * 40, token=None,
    ) == ChangeScope(True, "baseline has no complete hosted release evidence", ())


def test_verified_identical_merge_can_be_the_next_focused_baseline(monkeypatch) -> None:
    def missing_exact(*args, **kwargs):
        raise ReusedReleaseEvidence("main reused candidate CI")

    monkeypatch.setattr(release_validation_scope, "collect_release_evidence", missing_exact)
    monkeypatch.setattr(
        release_validation_scope, "collect_identical_merge_evidence", lambda *args, **kwargs: {},
    )
    assert release_validation_scope.baseline_is_valid("owner/repo", "a" * 40, None)
    monkeypatch.setattr(
        release_validation_scope, "collect_identical_merge_evidence", missing_exact,
    )
    assert not release_validation_scope.baseline_is_valid("owner/repo", "a" * 40, None)

    def failed_exact(*args, **kwargs):
        raise ReleaseEvidenceError("fresh main CI failed")

    monkeypatch.setattr(release_validation_scope, "collect_release_evidence", failed_exact)
    monkeypatch.setattr(
        release_validation_scope, "collect_identical_merge_evidence", lambda *args, **kwargs: {},
    )
    assert not release_validation_scope.baseline_is_valid("owner/repo", "a" * 40, None)


def test_docs_only_runs_history_checks_without_finalized_release_gate() -> None:
    scope = classify_paths(["docs/architecture.md"])
    assert scope.full is False
    assert "tests/test_release_notes.py" in scope.test_targets
    assert "tests/test_release_metadata.py" not in scope.test_targets
