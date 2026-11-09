"""Ensure the finalized-release metadata preflight fails on stale headers."""

from __future__ import annotations

from tools.release_metadata import metadata_errors

README = (
    "Current release: **1.0.1** (2026-11-09). "
    "docs/CHANGELOG.md#101---2026-11-09"
)


def test_finalized_metadata_fixture_is_valid() -> None:
    assert metadata_errors("1.0.1", "1.0.1", README, "## [1.0.1] - 2026-11-09\n") == []


def test_stale_and_mismatched_release_metadata_fails() -> None:
    dated = "## [1.0.1] - 2026-11-09\n"
    assert metadata_errors("1.0.1", "1.0.1", README, dated) == []
    assert "Unreleased" in " ".join(
        metadata_errors("1.0.1", "1.0.1", README, "## [1.0.1] - Unreleased\n")
    )
    assert "differs" in " ".join(
        metadata_errors("1.0.1", "1.0.1", README, "## [1.0.1] - 2026-11-08\n")
    )
    assert "module versions differ" in " ".join(
        metadata_errors("1.0.1", "1.0.0", README, dated)
    )
    assert "README" in " ".join(
        metadata_errors("1.0.1", "1.0.1", "Prepared release: 1.0.1", dated)
    )


def test_first_release_heading_controls_gate() -> None:
    pending = "## [1.0.1] - Unreleased\n\n## [1.0.0] - 2026-11-07\n"
    assert metadata_errors("1.0.1", "1.0.1", README, pending)
