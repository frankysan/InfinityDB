from __future__ import annotations

from pathlib import Path

import pytest

from tools.pytest_startup_profile import XdistStartupProfile, _runner_launch_timestamp
from tools.test_sections import load_test_sections, section_for_module


def test_test_section_config_covers_every_test_module_exactly_once() -> None:
    root = Path(__file__).resolve().parents[1]
    sections = load_test_sections()
    configured = {module for section in sections.values() for module in section.modules}
    discovered = {path.stem for path in (root / "tests").glob("test_*.py")}

    assert configured == discovered
    assert sum(len(section.modules) for section in sections.values()) == len(configured)


def test_test_section_markers_are_stable_and_named_from_sections() -> None:
    sections = load_test_sections()

    assert tuple(sections) == ("model", "web", "browser", "build", "ops", "assets")
    assert sections["browser"].marker == "section_browser"
    assert "test_verify_scenario_faq_browser" in sections["browser"].modules
    assert "test_verify_weapon_source_cards_browser" in sections["browser"].modules
    assert "test_verify_scenario_faq_browser" not in sections["web"].modules
    assert sections["model"].marker == "section_model"
    assert sections["web"].marker == "section_web"
    assert section_for_module("test_database", sections) == sections["model"]
    assert section_for_module("test_web", sections) == sections["web"]
    assert section_for_module("test_symbol_manifest", sections) == sections["assets"]


def test_xdist_startup_timing_tracks_ready_collection_and_first_test() -> None:
    profile = XdistStartupProfile()
    assert profile.summary_lines() == ()
    profile.start(2, 100.0)
    profile.ready("gw0", 101.5)
    profile.ready("gw1", 103.0)
    profile.collected("gw0", 104.0)
    profile.collected("gw1", 106.0)
    profile.first_test(106.25)
    profile.first_test(109.0)
    assert profile.summary_lines()[:3] == (
        "Workers ready: 2/2; first +1.50s, last +3.00s",
        "Collections complete: 2/2; first +4.00s, last +6.00s",
        "First test started: +6.25s",
    )
    assert "unavailable" in profile.summary_lines()[3]


def test_xdist_launch_includes_python_and_pytest_initialization() -> None:
    profile = XdistStartupProfile()
    profile.start(2, 100.0, launch_at=97.5)
    profile.ready("gw0", 100.5)
    profile.collected("gw0", 101.5)
    profile.first_test(102.0)
    assert profile.summary_lines()[3:5] == (
        "Runner process launch to xdist worker spawn: 2.50s",
        "Runner process launch to first test: 4.50s",
    )
    profile.start(1, 200.0, launch_at=205.0)
    assert "unavailable" in profile.summary_lines()[3]


def test_xdist_runner_launch_env_is_optional_and_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER", raising=False)
    assert _runner_launch_timestamp() is None
    monkeypatch.setenv("INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER", "invalid")
    assert _runner_launch_timestamp() is None
    monkeypatch.setenv("INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER", "42.5")
    assert _runner_launch_timestamp() == 42.5


def test_xdist_startup_timing_handles_incomplete_and_restarted_runs() -> None:
    profile = XdistStartupProfile()
    profile.start(3, 10.0)
    profile.ready("gw0", 11.0)
    assert profile.summary_lines()[:3] == (
        "Workers ready: 1/3; first +1.00s, last +1.00s",
        "Collections complete: 0/3",
        "First test started: not observed",
    )
    profile.start(1, 20.0)
    profile.ready("gw0", 21.0)
    profile.collected("gw0", 22.0)
    profile.first_test(23.0)
    assert profile.summary_lines()[:3] == (
        "Workers ready: 1/1; first +1.00s, last +1.00s",
        "Collections complete: 1/1; first +2.00s, last +2.00s",
        "First test started: +3.00s",
    )
