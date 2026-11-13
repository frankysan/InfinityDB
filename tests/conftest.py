"""Shared pytest collection policy."""

from __future__ import annotations

import importlib.util
import os
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

import pytest

from tools.browser_test_capacity import (
    browser_lane_groups,
    browser_slot,
    scenario_faq_split_lane,
)
from tools.browser_test_metrics import POOLED_BROWSER_MODULES, ChromiumLanePool
from tools.test_sections import load_test_sections, section_for_module

pytest_plugins = ("tools.pytest_startup_profile",)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--reference-pdf-layout", choices=("legacy", "local"), default="legacy",
        help="Explicit PDF layout for selected pinned source tests; never search a fallback.",
    )
    parser.addoption(
        "--browser-lanes",
        action="store_true",
        default=False,
        help="Group Chromium tests into dedicated workers with --dist loadgroup.",
    )
    parser.addoption(
        "--reuse-browser", action="store_true", default=False,
        help="Experimentally reuse one capacity-owned Chrome across four-lane group B.",
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
        or (request.config.getoption("--reuse-browser")
            and path.stem in POOLED_BROWSER_MODULES)
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


@pytest.fixture(scope="session")
def _pooled_chromium_lane(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[ChromiumLanePool]:
    pool = ChromiumLanePool(_browser_slot_directory(tmp_path_factory), slots=4)
    try:
        yield pool
    finally:
        pool.close()


@pytest.fixture(scope="module")
def pooled_chromium_browser(
    request: pytest.FixtureRequest, _pooled_chromium_lane: ChromiumLanePool,
) -> Iterator[object | None]:
    """Optional shared browser for the three four-lane B modules only."""
    if not request.config.getoption("--reuse-browser"):
        yield None
        return
    module = Path(str(request.node.path)).stem
    if module not in POOLED_BROWSER_MODULES:
        raise pytest.UsageError(f"Module is not eligible for Chromium reuse: {module}")
    pytest.importorskip("playwright.sync_api")
    try:
        browser = _pooled_chromium_lane.get()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
            pytest.skip(f"Chrome unavailable: {exc}")
        raise
    try:
        yield browser
    finally:
        _pooled_chromium_lane.finished_module(module)


@pytest.fixture(scope="module")
def reference_pdf_layout(request: pytest.FixtureRequest) -> str:
    """Opt-in physical PDF selection for bounded pinned source test families."""
    return str(request.config.getoption("--reference-pdf-layout"))


@pytest.fixture(scope="module")
def pinned_n53_core_pdf(reference_pdf_layout: str) -> Path:
    """Select exactly one pinned N5.3 Core PDF for source-only acceptance tests."""
    from tools.research.source_paths import pinned_pdf_path

    label = "data/pdf/rules/n5-rules-v5.3-en.pdf"
    sha256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    path = pinned_pdf_path(
        Path(__file__).resolve().parents[1], label, sha256,
        layout=reference_pdf_layout, missing_ok=True,
    )
    if path is None:
        pytest.skip(f"Pinned N5.3 Core PDF unavailable in {reference_pdf_layout} layout")
    return path


def _verified_pdf_sources(
    root: Path, sources: Mapping[str, str], *, layout: str,
) -> tuple[dict[str, Path], tuple[str, ...]]:
    """Validate every supplied PDF before reporting any missing sibling."""
    from tools.research.source_paths import pinned_pdf_path

    selected: dict[str, Path] = {}
    missing: list[str] = []
    for label, pin in sources.items():
        path = pinned_pdf_path(root, label, pin, layout=layout, missing_ok=True)
        if path is None:
            missing.append(label)
        else:
            selected[label] = path
    return selected, tuple(missing)


@pytest.fixture(scope="module")
def pinned_pdf_sources(
    reference_pdf_layout: str,
) -> Callable[[Mapping[str, str]], dict[str, Path]]:
    """Test-only exact-version PDF bindings, with no cross-layout fallback."""
    root = Path(__file__).resolve().parents[1]

    def select(sources: Mapping[str, str]) -> dict[str, Path]:
        selected, missing = _verified_pdf_sources(
            root, sources, layout=reference_pdf_layout,
        )
        if missing:
            pytest.skip(
                f"Pinned PDFs unavailable in {reference_pdf_layout} layout: "
                + ", ".join(missing)
            )
        return selected

    return select


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
    path = Path(__file__).resolve().parents[1] / "data/work/build/army.raw.db"
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


def pytest_itemcollected(item: pytest.Item) -> None:
    """Assign xdist groups before collection-modify hooks consume test markers.

    pytest-xdist reads xdist_group during its own collection-modify hook;
    assigning them in our modifyitems hook depends on plugin ordering.
    """
    path = Path(str(item.path))
    if path.parent.name != "tests" or not path.stem.startswith("test_"):
        return
    if not _uses_chromium(path):
        return
    config = item.config
    browser_lanes = bool(config.getoption("--browser-lanes"))
    count = int(config.getoption("--browser-lane-count") or 2)
    groups = browser_lane_groups(count) if browser_lanes else {}
    group = groups[path.stem] if browser_lanes else path.stem
    if config.getoption("--split-scenario-faq") and path.stem == (
        "test_verify_scenario_faq_browser"
    ):
        group = scenario_faq_split_lane(item.nodeid)
    item.add_marker(pytest.mark.xdist_group(name=group))


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item],
) -> None:
    """Assign every repository test module to exactly one maintained local section."""
    browser_lanes = bool(config.getoption("--browser-lanes"))
    split_scenario = bool(config.getoption("--split-scenario-faq"))
    reuse_browser = bool(config.getoption("--reuse-browser"))
    lane_count = int(config.getoption("--browser-lane-count") or 2)
    if split_scenario and (not browser_lanes or lane_count != 4):
        raise pytest.UsageError("--split-scenario-faq requires --browser-lanes and four lanes")
    if reuse_browser and (
        not browser_lanes or lane_count != 4
        or int(config.getoption("--browser-slot-count") or 2) != 4
    ):
        raise pytest.UsageError(
            "--reuse-browser requires --browser-lanes, four lanes and four slots"
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
