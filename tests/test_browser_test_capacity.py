"""Cross-process browser admission is bounded and releases on exit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.analyze_chromium_timeline import load_slot_records, summarize_timeline
from tools.analyze_chromium_timeline import (
    main as timeline_main,
)
from tools.browser_test_capacity import (
    CHROMIUM_SCHEDULING_LANES,
    browser_lane_groups,
    browser_slot,
    scenario_faq_split_lane,
)
from tools.pytest_startup_profile import XdistStartupProfile, summarized_skip_reasons
from tools.resource_waits import capture_resource_waits, record_resource_wait
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


def test_resource_wait_capture_is_scoped_and_never_includes_held_time(
    tmp_path: Path,
) -> None:
    record_resource_wait("chromium", 9.0)  # No active capture.
    with capture_resource_waits() as waits:
        with browser_slot(tmp_path, slots=1, label="setup"):
            pass
        with browser_slot(tmp_path, slots=1, timeout_seconds=0) as index:
            assert index == 0
        assert len(waits) == 2
        assert all(resource == "chromium" and seconds >= 0 for resource, seconds in waits)
        with capture_resource_waits() as inner:
            record_resource_wait("database", 0.25)
        assert inner == [("database", 0.25)]
        assert len(waits) == 2
    record_resource_wait("chromium", 10.0)
    assert len(waits) == 2


def test_wait_summary_keeps_original_setup_and_labels_remainder() -> None:
    report = pytest.TestReport(
        nodeid="tests/test_example.py::test_case",
        location=("tests/test_example.py", 1, "test_case"),
        keywords={}, outcome="passed", longrepr=None, when="setup", sections=[],
        duration=12.0, user_properties=[("infinitydb_wait_chromium", 9.0)],
    )
    profile = XdistStartupProfile()
    profile.record_setup_wait(report)
    lines = "\\n".join(profile.wait_summary_lines())
    assert "9.00s" in lines
    assert "3.00s" in lines
    assert "12.00s" in lines
    assert "summed worker time" in lines
    assert "do not add the two" in lines


def test_browser_lane_worker_summary_detects_dispersed_group() -> None:
    profile = XdistStartupProfile()
    def report(lane: str, worker: str) -> pytest.TestReport:
        return pytest.TestReport(
            nodeid="tests/test_example.py::test_case",
            location=("tests/test_example.py", 1, "test_case"),
            keywords={}, outcome="passed", longrepr=None,
            when="setup", sections=[], duration=0.0,
            user_properties=[
                ("infinitydb_browser_lane", lane),
                ("infinitydb_browser_worker", worker),
            ],
        )

    profile.record_lane_worker(report("chromium-a", "gw0"))
    profile.record_lane_worker(report("chromium-a", "gw0"))
    profile.record_lane_worker(report("chromium-b", "gw1"))
    assert profile.lane_violations() == ()
    assert "PASS:" in "\n".join(profile.lane_summary_lines())
    profile.record_lane_worker(report("chromium-a", "gw2"))
    assert profile.lane_violations() == ("chromium-a: gw0, gw2",)
    assert "FAIL:" in "\n".join(profile.lane_summary_lines())
    profile.start(4, 1.0)
    assert not profile.lane_violations()


def test_skip_reasons_group_actual_skip_reports_without_duplicate_counts() -> None:
    def report(reason: str) -> pytest.TestReport:
        return pytest.TestReport(
            nodeid="tests/test_example.py::test_case",
            location=("tests/test_example.py", 1, "test_case"),
            keywords={}, outcome="skipped",
            longrepr=("tests/test_example.py", 1, "Skipped: " + reason),
            when="setup", sections=[], duration=0.0,
        )

    lines = summarized_skip_reasons([
        report("Pinned Army ZIP unavailable"),
        report("Pinned N5.3 PDF unavailable"),
        report("Pinned Army ZIP unavailable"),
    ])
    assert lines[0] == "Skipped: 3 tests; 2 distinct reasons."
    assert lines[1].strip() == "2  Pinned Army ZIP unavailable"
    assert lines[2].strip() == "1  Pinned N5.3 PDF unavailable"
    assert summarized_skip_reasons([]) == ()
    assert summarized_skip_reasons([report("Only reason")])[0] == (
        "Skipped: 1 test; 1 distinct reason."
    )


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
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw-test")
    with browser_slot(tmp_path / "locks", slots=2, label="example-node") as index:
        assert index == 0
    files = list(metrics.glob("slot-*.jsonl"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert record["label"] == "example-node"
    assert record["slot"] == 0
    assert record["wait_seconds"] >= 0
    assert record["hold_seconds"] >= 0
    assert (
        record["request_monotonic_seconds"]
        <= record["acquired_monotonic_seconds"]
        <= record["released_monotonic_seconds"]
    )
    assert record["wait_seconds"] == pytest.approx(
        record["acquired_monotonic_seconds"] - record["request_monotonic_seconds"]
    )
    assert record["hold_seconds"] == pytest.approx(
        record["released_monotonic_seconds"] - record["acquired_monotonic_seconds"]
    )
    assert record["worker"] == "gw-test"


def test_chromium_timeline_reconstructs_waiting_and_slot_occupancy(tmp_path: Path) -> None:
    samples = (
        (0, "tests/test_a.py::one", 0.0, 1.0, 4.0),
        (1, "tests/test_b.py::two", 0.0, 2.0, 5.0),
        (0, "tests/test_a.py::three", 2.0, 4.0, 6.0),
        (2, "outside-capacity", 0.0, 0.0, 0.01),
    )
    rows = [
        {"slot": slot, "label": label, "worker": f"gw{slot}", "pid": 100 + slot,
         "request_monotonic_seconds": start, "acquired_monotonic_seconds": acquired,
         "released_monotonic_seconds": released,
         "wait_seconds": acquired - start, "hold_seconds": released - acquired}
        for slot, label, start, acquired, released in samples
    ]
    (tmp_path / "slot-123.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8",
    )
    records, excluded = load_slot_records(tmp_path, slots=2)
    assert len(records) == 3
    assert excluded == 1
    data = summarize_timeline(records, slots=2)
    assert data["observed_seconds"] == pytest.approx(6.0)
    assert data["wait_seconds"] == pytest.approx(5.0)
    assert data["held_seconds"] == pytest.approx(8.0)
    assert data["occupied_slot_seconds"] == pytest.approx(8.0)
    assert data["full_capacity_seconds"] == pytest.approx(3.0)
    assert data["idle_with_waiters_seconds"] == pytest.approx(2.0)
    assert data["max_occupied"] == 2
    assert data["max_waiters"] == 2
    assert not data["same_slot_overlap"]
    assert data["module_totals"][0] == ("test_a.py", 3.0, 5.0)
    assert data["module_workers"]["test_a.py"] == ["gw0"]
    assert data["module_pids"]["test_a.py"] == 1


def test_chromium_timeline_cli_reports_reconstructed_intervals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "slot-1.jsonl").write_text(
        json.dumps({
            "slot": 0, "label": "tests/test_example.py",
            "request_monotonic_seconds": 1.0,
            "acquired_monotonic_seconds": 2.0,
            "released_monotonic_seconds": 4.0,
        }) + "\n",
        encoding="utf-8",
    )
    assert timeline_main([str(tmp_path), "--slots", "1"]) == 0
    output = capsys.readouterr().out
    assert "Waiting: 1.00 worker-seconds" in output
    assert "Held: 2.00 worker-seconds" in output
    assert "Peak occupied slots: 1/1" in output


def test_chromium_timeline_refuses_legacy_duration_only_metrics(tmp_path: Path) -> None:
    (tmp_path / "slot-1.jsonl").write_text(
        json.dumps({"slot": 0, "wait_seconds": 3, "hold_seconds": 2}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="legacy slot metrics"):
        load_slot_records(tmp_path, slots=2)


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
