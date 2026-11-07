"""Time-window alignment for recorded Windows/Linux host resource samples."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.analyze_test_host_resources import (
    _timestamp,
    read_capture,
    summarize_test_window,
)


def _capture(path: Path, *, defect: str | None = None) -> None:
    start = "2026-11-03T07:00:00+00:00"
    rows: list[dict[str, object]] = [
        {"kind": "metadata", "schema": 1, "startedUtc": start},
    ]
    for elapsed, cpu, memory in (
        (0, None, 50),
        (5, 20, 55),
        (10, 40, 60),
        (15, 60, 65),
        (20, 80, 70),
    ):
        rows.append({
            "kind": "sample", "elapsedSeconds": elapsed,
            "cpuBusyPercent": cpu, "memoryUsedPercent": memory,
        })
    rows.append({"kind": "summary", "samples": 5})
    if defect == "missing-summary":
        rows.pop()
    elif defect == "wrong-count":
        rows[-1]["samples"] = 4
    elif defect == "reordered":
        rows[3]["elapsedSeconds"] = 5
    elif defect == "missing-cpu":
        rows[3]["cpuBusyPercent"] = None
    elif defect == "bool-cpu":
        rows[3]["cpuBusyPercent"] = True
    elif defect == "out-of-range":
        rows[3]["memoryUsedPercent"] = 101
    elif defect == "naive-start":
        rows[0]["startedUtc"] = "2026-11-03T07:00:00"
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8", newline="\n",
    )


def test_resource_window_uses_interval_overlap_not_full_capture_average(
    tmp_path: Path,
) -> None:
    path = tmp_path / "samples.jsonl"
    _capture(path)
    result = summarize_test_window(
        path,
        test_start=datetime(2026, 11, 3, 7, 0, 3, tzinfo=UTC),
        duration_seconds=12,
    )
    assert result == {
        "testStartUtc": "2026-11-03T07:00:03+00:00",
        "testEndUtc": "2026-11-03T07:00:15+00:00",
        "testDurationSeconds": 12,
        "intervals": 3,
        "coveredSeconds": 12,
        "coveragePercent": 100,
        "cpuAveragePercent": 45,
        "cpuPeakPercent": 60,
        "memoryAveragePercent": 61.25,
        "memoryPeakPercent": 65,
    }


@pytest.mark.parametrize(
    "defect",
    ("missing-summary", "wrong-count", "reordered",
     "missing-cpu", "bool-cpu", "out-of-range", "naive-start"),
)
def test_resource_capture_rejects_incomplete_or_untrusted_rows(
    tmp_path: Path, defect: str,
) -> None:
    path = tmp_path / "bad.jsonl"
    _capture(path, defect=defect)
    with pytest.raises(ValueError):
        read_capture(path)


def test_partial_test_window_coverage_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "samples.jsonl"
    _capture(path)
    with pytest.raises(ValueError, match="coverage is incomplete"):
        summarize_test_window(
            path,
            test_start=datetime(2026, 11, 3, 6, 59, 59, tzinfo=UTC),
            duration_seconds=15,
        )


def test_resource_window_rejects_unbounded_and_naive_times(
    tmp_path: Path,
) -> None:
    path = tmp_path / "samples.jsonl"
    _capture(path)
    with pytest.raises(ValueError, match="offset-aware"):
        summarize_test_window(
            path, test_start=datetime(2026, 11, 3, 7, 0, 0),
            duration_seconds=12,
        )
    with pytest.raises(ValueError, match="1..1800"):
        summarize_test_window(
            path, test_start=datetime(2026, 11, 3, 7, 0, 0, tzinfo=UTC),
            duration_seconds=float("nan"),
        )
    with pytest.raises(ValueError, match="coverage is incomplete"):
        summarize_test_window(
            path,
            test_start=datetime(2026, 11, 3, 7, 0, 20, tzinfo=UTC)
            + timedelta(seconds=1),
            duration_seconds=10,
        )


def test_offset_aware_timestamps_convert_to_utc() -> None:
    assert _timestamp("2026-11-03T08:00:00+01:00") == datetime(
        2026, 11, 3, 7, 0, 0, tzinfo=UTC,
    )
    with pytest.raises(ValueError, match="timezone offset"):
        _timestamp("2026-11-03T07:00:00")
