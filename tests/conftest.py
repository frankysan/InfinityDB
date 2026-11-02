"""Shared pytest collection policy."""

from __future__ import annotations

import importlib.util
import os
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tools.browser_test_capacity import (
    browser_lane_groups,
    browser_slot,
    scenario_faq_split_lane,
)
from tools.test_sections import load_test_sections, section_for_module

pytest_plugins = ("tools.pytest_startup_profile",)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--browser-lanes",
        action="store_true",
        default=False,
        help="Group Chromium tests into dedicated workers with --dist loadgroup.",
    )
    parser.addoption(
        "--split-scenario-faq", action="store_true", default=False,
        help="Experimentally split Scenario FAQ cases across lanes A and D (four lanes only).",
    )
    parser.addoption(
        "--browser-slot-count", type=int, choices=(2, 3, 4), default=2,
        help="Maximum simultaneous Chromium acceptance tests (default: 2).",
    )
    parser.addoption(
        "--browser-lane-count", type=int, choices=(2, 3, 4), default=2,
        help="Number of grouped Chromium workers when --browser-lanes is enabled.",
    )


_TEST_SECTIONS = load_test_sections()
# Despite its filename, this module tests a browser verifier entirely with mocks.
_NON_CHROMIUM_BROWSER_MODULES = frozenset({"test_verify_rule_fragment_browser.py"})
# These modules mix contract checks with a single real Chromium test. Their
# browser tests acquire the slot individually instead of blocking the module.
_PER_TEST_CHROMIUM_MODULES = frozenset({
    "test_verify_release_candidate_browser.py",
    "test_verify_deployed_object_publication_browser.py",
    "test_verify_unit_skill_presentation_browser.py",
})


def _uses_chromium(path: Path) -> bool:
    return path.name.endswith("_browser.py") and path.name not in _NON_CHROMIUM_BROWSER_MODULES


def _browser_slot_directory(factory: pytest.TempPathFactory) -> Path:
    return factory.getbasetemp().parent / "infinitydb-chromium-slots"


def _needs_chromium_slot() -> bool:
    return (
        "PYTEST_XDIST_WORKER" in os.environ
        and importlib.util.find_spec("playwright") is not None
    )


@pytest.fixture(scope="module", autouse=True)
def limit_concurrent_browser_tests(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Keep Chromium resource use bounded across xdist workers, not pytest jobs."""
    path = Path(str(request.node.path))
    if (
        not _uses_chromium(path)
        or path.name in _PER_TEST_CHROMIUM_MODULES
        or not _needs_chromium_slot()
    ):
        yield
        return
    with browser_slot(
        _browser_slot_directory(tmp_path_factory),
        slots=int(request.config.getoption("--browser-slot-count") or 2),
        label=str(request.node.nodeid),
    ):
        yield


@pytest.fixture
def chromium_test_slot(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Reserve capacity only while a mixed module executes a real browser test."""
    if not _needs_chromium_slot():
        yield
        return
    with browser_slot(
        _browser_slot_directory(tmp_path_factory),
        slots=int(request.config.getoption("--browser-slot-count") or 2),
        label=str(request.node.nodeid),
    ):
        yield


@pytest.fixture(scope="module")
def require_source_files() -> Callable[..., None]:
    """Skip only absent local evidence; present bytes must still pass their audit."""
    def require(*paths: Path) -> None:
        missing = [path.name for path in paths if not path.exists()]
        if missing:
            pytest.skip(f"Ignored local source files unavailable: {', '.join(missing)}")

    return require


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


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item],
) -> None:
    """Assign every repository test module to exactly one maintained local section."""
    browser_lanes = bool(config.getoption("--browser-lanes"))
    split_scenario = bool(config.getoption("--split-scenario-faq"))
    lane_count = int(config.getoption("--browser-lane-count") or 2)
    if split_scenario and (not browser_lanes or lane_count != 4):
        raise pytest.UsageError("--split-scenario-faq requires --browser-lanes and four lanes")
    groups = (
        browser_lane_groups(lane_count)
        if browser_lanes else {}
    )

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
        if _uses_chromium(path):
            # Dedicated groups keep Chromium work on bounded xdist workers.
            group = groups[path.stem] if browser_lanes else path.stem
            if split_scenario and path.stem == "test_verify_scenario_faq_browser":
                group = scenario_faq_split_lane(item.nodeid)
            item.add_marker(pytest.mark.xdist_group(name=group))
