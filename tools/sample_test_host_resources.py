"""Sample host CPU and physical memory alongside independent test jobs.

This command never launches tests or changes their scheduling. Samples and
summary are written to a fresh, Git-ignored local/benchmarks/*.jsonl file.
Windows and Linux use their native cumulative system CPU counters.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import platform
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_SAMPLES = 2000


@dataclass(frozen=True)
class HostCounters:
    cpu_total: int
    cpu_idle: int
    memory_total: int
    memory_available: int


def linux_cpu_counters(text: str) -> tuple[int, int]:
    """Exclude guest CPU fields already included in user/nice."""
    first = text.splitlines()[0].split() if text else []
    if len(first) < 5 or first[0] != "cpu":
        raise ValueError("Expected aggregate Linux cpu counters")
    fields = [int(value) for value in first[1:9]]
    if len(fields) < 4 or any(value < 0 for value in fields):
        raise ValueError("Invalid Linux cpu counters")
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
    return sum(fields), idle


def linux_memory_bytes(text: str) -> tuple[int, int]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        key, separator, raw = line.partition(":")
        if separator and key in {"MemTotal", "MemAvailable"}:
            pieces = raw.split()
            if len(pieces) != 2 or pieces[1] != "kB":
                raise ValueError(f"Invalid Linux memory field: {key}")
            values[key] = int(pieces[0]) * 1024
    if set(values) != {"MemTotal", "MemAvailable"}:
        raise ValueError("Missing Linux MemTotal or MemAvailable")
    return values["MemTotal"], values["MemAvailable"]


def windows_host_counters() -> HostCounters:
    """Read host-wide Windows kernel CPU totals and physical memory."""
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

        def ticks(self) -> int:
            return (self.high << 32) | self.low

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.DWORD), ("load", wintypes.DWORD),
            ("total_phys", ctypes.c_ulonglong),
            ("avail_phys", ctypes.c_ulonglong),
            ("total_page", ctypes.c_ulonglong),
            ("avail_page", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("avail_virtual", ctypes.c_ulonglong),
            ("avail_extended", ctypes.c_ulonglong),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_times = kernel32.GetSystemTimes
    get_times.argtypes = [ctypes.POINTER(FileTime)] * 3
    get_times.restype = wintypes.BOOL
    idle, kernel, user = FileTime(), FileTime(), FileTime()
    if not get_times(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
        raise OSError(ctypes.get_last_error(), "GetSystemTimes failed")
    get_memory = kernel32.GlobalMemoryStatusEx
    get_memory.argtypes = [ctypes.POINTER(MemoryStatus)]
    get_memory.restype = wintypes.BOOL
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(MemoryStatus)
    if not get_memory(ctypes.byref(memory)):
        raise OSError(ctypes.get_last_error(), "GlobalMemoryStatusEx failed")
    return HostCounters(
        cpu_total=kernel.ticks() + user.ticks(),
        cpu_idle=idle.ticks(),
        memory_total=memory.total_phys,
        memory_available=memory.avail_phys,
    )


def read_host_counters() -> HostCounters:
    system = platform.system()
    if system == "Linux":
        total, idle = linux_cpu_counters(
            Path("/proc/stat").read_text(encoding="ascii")
        )
        memory_total, memory_available = linux_memory_bytes(
            Path("/proc/meminfo").read_text(encoding="ascii")
        )
        return HostCounters(total, idle, memory_total, memory_available)
    if system == "Windows":
        return windows_host_counters()
    raise ValueError(f"Host resource sampling is not supported on {system}")


def cpu_busy_percent(before: HostCounters, after: HostCounters) -> float | None:
    total = after.cpu_total - before.cpu_total
    idle = after.cpu_idle - before.cpu_idle
    if total <= 0 or idle < 0 or idle > total:
        return None
    return round(100 * (total - idle) / total, 2)


def validate_sample(counters: HostCounters) -> None:
    if (
        counters.cpu_total < 0 or counters.cpu_idle < 0
        or counters.cpu_idle > counters.cpu_total
        or counters.memory_total <= 0
        or not 0 <= counters.memory_available <= counters.memory_total
    ):
        raise ValueError("Invalid host CPU or memory counters")


def resolve_output(path: Path, *, root: Path = ROOT) -> Path:
    """Require a new .jsonl artifact under the ignored benchmark directory."""
    if path.is_absolute() or ".." in path.parts or path.suffix != ".jsonl":
        raise ValueError("Output must be a relative .jsonl path without parent traversal")
    base = (root / "local/benchmarks").resolve()
    output = (root / path).resolve()
    if not output.is_relative_to(base) or output == base:
        raise ValueError("Output must be beneath local/benchmarks")
    return output


def sample_host(
    output: Path,
    duration: float,
    interval: float,
    *,
    read: Callable[[], HostCounters] = read_host_counters,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, float | int | None]:
    """Take bounded monotonic samples and write a finished summary."""
    if not (math.isfinite(duration) and math.isfinite(interval)):
        raise ValueError("Duration and interval must be finite")
    if not 1 <= duration <= 1800 or not 0.5 <= interval <= 60:
        raise ValueError("Duration must be 1..1800s; interval 0.5..60s")
    count = math.ceil(duration / interval) + 1
    if count > MAX_SAMPLES:
        raise ValueError("Sampling configuration exceeds the sample limit")
    output.parent.mkdir(parents=True, exist_ok=True)
    started = clock()
    previous: HostCounters | None = None
    percentages: list[float] = []
    memory_percentages: list[float] = []
    with output.open("x", encoding="utf-8") as stream:
        def write(row: dict[str, object]) -> None:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            stream.flush()

        write({
            "kind": "metadata", "schema": 1,
            "platform": platform.platform(), "cpuCount": os.cpu_count(),
            "startedUtc": datetime.now(UTC).isoformat(),
            "durationSeconds": duration, "intervalSeconds": interval,
        })
        for index in range(count):
            target = started + min(index * interval, duration)
            sleep(max(0, target - clock()))
            snapshot = read()
            validate_sample(snapshot)
            cpu = cpu_busy_percent(previous, snapshot) if previous else None
            memory_used = round(
                100 * (snapshot.memory_total - snapshot.memory_available)
                / snapshot.memory_total, 2,
            )
            if cpu is not None:
                percentages.append(cpu)
            memory_percentages.append(memory_used)
            write({
                "kind": "sample",
                "elapsedSeconds": round(clock() - started, 3),
                "cpuBusyPercent": cpu,
                "memoryUsedPercent": memory_used,
                "memoryTotalBytes": snapshot.memory_total,
                "memoryAvailableBytes": snapshot.memory_available,
            })
            previous = snapshot
        summary: dict[str, float | int | None] = {
            "samples": count,
            "cpuAveragePercent": round(statistics.mean(percentages), 2)
            if percentages else None,
            "cpuPeakPercent": max(percentages) if percentages else None,
            "memoryAveragePercent": round(statistics.mean(memory_percentages), 2),
            "memoryPeakPercent": max(memory_percentages),
        }
        write({"kind": "summary", **summary})
        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=float, default=780)
    parser.add_argument("--interval-seconds", type=float, default=5)
    args = parser.parse_args()
    try:
        output = resolve_output(args.output)
        summary = sample_host(output, args.duration_seconds, args.interval_seconds)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Host resource samples: {output}")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
