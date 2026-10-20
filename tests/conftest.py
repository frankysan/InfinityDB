"""Shared pytest collection policy."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.test_sections import load_test_sections, section_for_module

_TEST_SECTIONS = load_test_sections()


@pytest.fixture(scope="module")
def requires_pinned_raw_army_archive() -> None:
    """Only source-provenance tests need the ignored full Army raw archive."""
    path = Path(__file__).resolve().parents[1] / "data/generated/infinity.raw.db"
    if not path.is_file() or path.stat().st_size == 0:
        pytest.skip("Full Army raw archive is ignored and unavailable in clean CI")
    # A present but malformed archive is an error, not a reason to skip.
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
        tables = {
            name for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    required = {
        "metadata_skills",
        "profile_skills",
        "option_skills",
        "unit_option_skills",
        "profile_equipment",
        "option_equipment",
        "unit_option_equipment",
        "extras",
    }
    missing = required - tables
    assert not missing, f"Full Army raw archive has missing tables: {sorted(missing)}"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Assign every repository test module to exactly one maintained local section."""

    for item in items:
        path = Path(str(item.path))
        if path.parent.name != "tests" or not path.stem.startswith("test_"):
            continue
        section = section_for_module(path.stem, _TEST_SECTIONS)
        if section is None:
            raise pytest.UsageError(
                f"Test module {path.name} is not assigned in config/testing/test-sections.json"
            )
        item.add_marker(section.marker)
