"""Shared pytest collection policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.test_sections import load_test_sections, section_for_module

_TEST_SECTIONS = load_test_sections()


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
