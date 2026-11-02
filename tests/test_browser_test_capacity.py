"""Cross-process browser admission is bounded and releases on exit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.browser_test_capacity import (
    CHROMIUM_SCHEDULING_LANES,
    browser_lane_groups,
    browser_slot,
    scenario_faq_split_lane,
)
from tools.test_sections import load_test_sections


def test_two_browser_lanes_cover_all_real_chromium_modules() -> None:
    browser_modules = set(load_test_sections()["browser"].modules)
    # The verifier-contract module is pure mocks; it must never hold a slot.
    browser_modules.remove("test_verify_rule_fragment_browser")
    assert set(CHROMIUM_SCHEDULING_LANES) == browser_modules
    assert set(CHROMIUM_SCHEDULING_LANES.values()) == {"chromium-a", "chromium-b"}
    assert CHROMIUM_SCHEDULING_LANES["test_verify_unit_skill_presentation_browser"] != (
        CHROMIUM_SCHEDULING_LANES["test_verify_weapon_source_cards_browser"]
    )


@pytest.mark.parametrize("lanes", (2, 3, 4))
def test_experimental_browser_lanes_cover_all_modules_once(lanes: int) -> None:
    groups = browser_lane_groups(lanes)
    assert set(groups) == set(CHROMIUM_SCHEDULING_LANES)
    assert set(groups.values()) == {
        f"chromium-{chr(ord('a') + i)}" for i in range(lanes)
    }
    if lanes == 2:
        assert groups == CHROMIUM_SCHEDULING_LANES


def test_browser_lane_count_rejects_unsupported_values() -> None:
    with pytest.raises(ValueError, match="lane count"):
        browser_lane_groups(5)


def test_scenario_faq_split_is_stable_and_uses_only_existing_lanes() -> None:
    ids = [
        f"tests/test_verify_scenario_faq_browser.py::test_matrix[case-{i}]"
        for i in range(400)
    ]
    first = [scenario_faq_split_lane(nodeid) for nodeid in ids]
    assert first == [scenario_faq_split_lane(nodeid) for nodeid in ids]
    assert set(first) == {"chromium-a", "chromium-d"}
    assert 150 < first.count("chromium-a") < 250


def test_browser_slots_reject_invalid_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Browser slots"):
        with browser_slot(tmp_path, slots=0):
            pass
    with pytest.raises(ValueError, match="Browser slots"):
        with browser_slot(tmp_path, timeout_seconds=-1):
            pass


def test_browser_slot_is_exclusive_across_processes_and_reusable(tmp_path: Path) -> None:
    # Subprocesses use a separate OS lock owner (also on Windows, where the
    # multiprocessing start method differs from POSIX).
    probe = (
        "import sys\n"
        "from pathlib import Path\n"
        "from tools.browser_test_capacity import browser_slot\n"
        "try:\n"
        "    with browser_slot(Path(sys.argv[1]), slots=1, timeout_seconds=0.2):\n"
        "        pass\n"
        "except TimeoutError:\n"
        "    sys.exit(17)\n"
    )
    command = [sys.executable, "-c", probe, str(tmp_path)]
    with browser_slot(tmp_path, slots=1):
        blocked = subprocess.run(command, capture_output=True, text=True, timeout=10)
        assert blocked.returncode == 17, blocked.stderr
    released = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert released.returncode == 0, released.stderr


def test_browser_metrics_capture_wait_and_hold_without_changing_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = tmp_path / "metrics"
    monkeypatch.setenv("INFINITYDB_BROWSER_METRICS_DIRECTORY", str(metrics))
    with browser_slot(tmp_path / "locks", slots=2, label="example-node") as index:
        assert index == 0
    files = list(metrics.glob("slot-*.jsonl"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert record["label"] == "example-node"
    assert record["slot"] == 0
    assert record["wait_seconds"] >= 0
    assert record["hold_seconds"] >= 0


@pytest.mark.parametrize("capacity", (2, 3, 4))
def test_browser_slots_admit_distinct_slots(tmp_path: Path, capacity: int) -> None:
    from contextlib import ExitStack

    with ExitStack() as stack:
        acquired = {
            stack.enter_context(browser_slot(tmp_path, slots=capacity, timeout_seconds=0.1))
            for _ in range(capacity)
        }
        assert acquired == set(range(capacity))
        with pytest.raises(TimeoutError):
            with browser_slot(tmp_path, slots=capacity, timeout_seconds=0):
                pass
