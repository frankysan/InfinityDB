"""Bounded, cross-platform host resource telemetry for Chromium benchmarks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tools.performance.sample_test_host_resources import (
    HostCounters,
    cpu_busy_percent,
    linux_cpu_counters,
    linux_memory_bytes,
    resolve_output,
    sample_host,
    validate_sample,
    windows_host_counters,
)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows kernel APIs only")
def test_windows_host_counters_use_native_ctypes_entry_points() -> None:
    counters = windows_host_counters()
    validate_sample(counters)


def test_linux_cpu_counters_exclude_duplicate_guest_fields() -> None:
    assert linux_cpu_counters(
        "cpu  100 10 25 400 40 5 5 15 20 2\n"
        "cpu0  25 3 5 100 10 1 1 4 4 1\n"
    ) == (600, 440)


@pytest.mark.parametrize("value", ("", "cpuX 4 5 6 7\n", "cpu 1 2 3 nope", "cpu -1 2 3 4"))
def test_linux_cpu_counters_reject_invalid_data(value: str) -> None:
    with pytest.raises(ValueError):
        linux_cpu_counters(value)


def test_linux_memory_available_from_proc_fields() -> None:
    assert linux_memory_bytes(
        "MemTotal:       1024 kB\nMemFree: 25 kB\nMemAvailable: 256 kB\n"
    ) == (1024 * 1024, 256 * 1024)


@pytest.mark.parametrize(
    "value",
    (
        "MemTotal: 1024 kB\n",
        "MemTotal: 1024 kB\nMemAvailable: 256 mb\n",
        "MemTotal: abc kB\nMemAvailable: 256 kB\n",
    ),
)
def test_linux_memory_rejects_missing_or_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        linux_memory_bytes(value)


def test_cpu_busy_percent_uses_counter_deltas() -> None:
    before = HostCounters(100, 40, 1000, 700)
    after = HostCounters(200, 65, 1000, 600)
    assert cpu_busy_percent(before, after) == 75.0
    assert cpu_busy_percent(after, before) is None
    assert cpu_busy_percent(before, before) is None


@pytest.mark.parametrize(
    "relative",
    (
        Path("../capture.jsonl"),
        Path("elsewhere/capture.jsonl"),
        Path("local/benchmarks/capture.txt"),
        Path("local/benchmarks/../../outside.jsonl"),
    ),
)
def test_resource_output_is_restricted_to_ignored_benchmark_tree(
    tmp_path: Path, relative: Path,
) -> None:
    with pytest.raises(ValueError):
        resolve_output(relative, root=tmp_path)
    assert resolve_output(
        Path("local/benchmarks/capture.jsonl"), root=tmp_path,
    ) == (tmp_path / "local/benchmarks/capture.jsonl").resolve()


def test_host_resource_sampler_writes_completed_jsonl_and_never_overwrites(
    tmp_path: Path,
) -> None:
    elapsed = [100.0]
    snapshots = iter((
        HostCounters(100, 40, 1600, 800),
        HostCounters(200, 65, 1600, 760),
        HostCounters(300, 90, 1600, 700),
    ))

    def now() -> float:
        return elapsed[0]

    def sleep(seconds: float) -> None:
        elapsed[0] += seconds

    output = tmp_path / "samples.jsonl"
    summary = sample_host(
        output, 2, 1, read=lambda: next(snapshots), clock=now, sleep=sleep,
    )
    rows = [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["kind"] for row in rows] == [
        "metadata", "sample", "sample", "sample", "summary",
    ]
    assert [row["elapsedSeconds"] for row in rows[1:4]] == [0, 1, 2]
    assert [row["cpuBusyPercent"] for row in rows[1:4]] == [None, 75, 75]
    assert [row["memoryUsedPercent"] for row in rows[1:4]] == [50, 52.5, 56.25]
    assert rows[-1]["samples"] == 3
    assert summary == {
        "samples": 3,
        "cpuAveragePercent": 75,
        "cpuPeakPercent": 75,
        "memoryAveragePercent": 52.92,
        "memoryPeakPercent": 56.25,
    }
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        sample_host(output, 1, 1, read=lambda: next(snapshots), clock=now, sleep=sleep)
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    ("seconds", "interval"),
    ((0, 1), (1801, 1), (10, 0), (3, 61), (float("nan"), 1), (1800, 0.5)),
)
def test_host_sampler_rejects_unbounded_settings(
    tmp_path: Path, seconds: float, interval: float,
) -> None:
    with pytest.raises(ValueError):
        sample_host(tmp_path / "invalid.jsonl", seconds, interval)
    assert not (tmp_path / "invalid.jsonl").exists()
