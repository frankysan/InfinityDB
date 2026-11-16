"""Linux-only host-local Chromium capacity profile and safe overrides."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from tools.performance.browser_test_host_profile import (
    PROFILE_NAME,
    linux_four_slots_enabled,
    profile_path,
    set_linux_four_slots,
)
from tools.run_checks import apply_host_browser_test_defaults, build_parser, stage_definitions


def test_linux_host_opt_in_is_ignored_on_windows_and_reversible(tmp_path: Path) -> None:
    assert not linux_four_slots_enabled(tmp_path, platform="linux")
    set_linux_four_slots(True, tmp_path, platform="linux")
    assert linux_four_slots_enabled(tmp_path, platform="linux")
    assert not linux_four_slots_enabled(tmp_path, platform="win32")
    assert json.loads(profile_path(tmp_path).read_text(encoding="utf-8")) == {
        "profile": PROFILE_NAME,
    }
    set_linux_four_slots(True, tmp_path, platform="linux")
    set_linux_four_slots(False, tmp_path, platform="linux")
    assert not linux_four_slots_enabled(tmp_path, platform="linux")


@pytest.mark.parametrize(
    "data",
    (
        '{"profile":"unknown"}',
        '{"profile":"linux-four-browser-slots","browserSlotCount":999}',
        "{",
        "[]",
    ),
)
def test_unknown_or_corrupt_profile_fails_closed(tmp_path: Path, data: str) -> None:
    path = profile_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(data, encoding="utf-8")
    with pytest.raises(ValueError, match="profile"):
        linux_four_slots_enabled(tmp_path, platform="linux")
    with pytest.raises(ValueError, match="profile"):
        set_linux_four_slots(True, tmp_path, platform="linux")


def test_symlink_profile_refused(tmp_path: Path) -> None:
    destination = tmp_path / "other.json"
    destination.write_text('{"profile":"linux-four-browser-slots"}', encoding="utf-8")
    path = profile_path(tmp_path)
    path.parent.mkdir(parents=True)
    try:
        path.symlink_to(destination)
    except OSError:
        pytest.skip("Host cannot create a test symlink")
    with pytest.raises(ValueError, match="regular local file"):
        linux_four_slots_enabled(tmp_path, platform="linux")


def test_windows_cannot_enable_linux_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be configured"):
        set_linux_four_slots(True, tmp_path, platform="win32")
    assert not profile_path(tmp_path).exists()


def test_host_profile_selects_tested_four_lane_configuration() -> None:
    args = build_parser().parse_args(["--stage", "test"])
    assert apply_host_browser_test_defaults(args, ["--stage", "test"], profile_enabled=True)
    assert (args.test_workers, args.test_dist) == ("8", "browserlanes")
    assert (args.browser_slot_count, args.browser_lane_count) == (4, 4)
    assert args.split_scenario_faq
    [stage] = stage_definitions(
        ("test",), [], build_source=None,
        test_workers=args.test_workers, test_distribution=args.test_dist,
        browser_slot_count=args.browser_slot_count,
        browser_lane_count=args.browser_lane_count,
        split_scenario_faq=args.split_scenario_faq,
    )
    assert stage.command[3:13] == (
        "-n", "8", "--dist", "loadgroup", "--browser-lanes",
        "--split-scenario-faq", "--browser-slot-count", "4",
        "--browser-lane-count", "4",
    )


@pytest.mark.parametrize(
    "override",
    (
        ["--browser-slot-count", "2"],
        ["--browser-slot-count=2"],
        ["--browser-lane-count", "2"],
        ["--test-workers", "4"],
        ["--test-dist", "worksteal"],
        ["--split-scenario-faq"],
        ["--reuse-browser"],
    ),
)
def test_explicit_browser_options_bypass_host_profile(override: list[str]) -> None:
    argv = ["--stage", "test", *override]
    args = build_parser().parse_args(argv)
    assert not apply_host_browser_test_defaults(args, argv, profile_enabled=True)
    assert args.browser_slot_count == 2
    assert args.browser_lane_count == 2
    assert args.test_workers == ("4" if "--test-workers" in override else None)


def test_disabled_host_profile_leaves_windows_and_ci_defaults() -> None:
    args = build_parser().parse_args(["--stage", "test"])
    assert not apply_host_browser_test_defaults(
        args, ["--stage", "test"], profile_enabled=False,
    )
    assert args.browser_slot_count == 2
    assert args.browser_lane_count == 2
    assert args.test_workers is None
    assert args.test_dist is None
    assert not args.split_scenario_faq


def test_extra_unrelated_cli_flags_keep_host_profile() -> None:
    args = Namespace(
        test_workers=None, test_dist=None,
        browser_slot_count=2, browser_lane_count=2,
        split_scenario_faq=False,
    )
    assert apply_host_browser_test_defaults(
        args, ["--stage", "test", "--test-section", "browser", "--browser-metrics"],
        profile_enabled=True,
    )
    assert args.browser_slot_count == 4
