#!/usr/bin/env python3
"""Capture privacy-safe host/container resource evidence for an InfinityDB deployment."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FORMAT = "InfinityDB deployment resource capture"
FORMAT_VERSION = 1
DEFAULT_DURATION_SECONDS = 60.0
DEFAULT_INTERVAL_SECONDS = 2.0
DEFAULT_SERVICES = ("app", "caddy")
DEFAULT_PROC_ROOT = Path("/proc")
DEFAULT_FILESYSTEM_PATH = Path(".")
_SIZE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([kmgt]?i?b)?\s*$", re.IGNORECASE)
_PROC_MOUNT_ESCAPE_RE = re.compile(r"\\([0-7]{3})")


class ResourceCaptureError(RuntimeError):
    """Raised when deployment resource evidence cannot be collected safely."""


@dataclass(frozen=True)
class HostSnapshot:
    monotonic_seconds: float
    cpu_total: int
    cpu_idle: int
    memory_total_bytes: int
    memory_available_bytes: int
    swap_total_bytes: int
    swap_free_bytes: int
    filesystem_total_bytes: int
    filesystem_available_bytes: int
    inode_total: int
    inode_available: int
    disk_device: str | None
    disk_read_bytes: int | None
    disk_write_bytes: int | None
    network_rx_bytes: int
    network_tx_bytes: int


@dataclass(frozen=True)
class ContainerSnapshot:
    name: str
    cpu_percent: float
    memory_percent: float
    memory_used_bytes: int
    memory_limit_bytes: int
    network_rx_bytes: int
    network_tx_bytes: int
    block_read_bytes: int
    block_write_bytes: int


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_cpu_stat(text: str) -> tuple[int, int]:
    first = text.splitlines()[0].split()
    if not first or first[0] != "cpu" or len(first) < 5:
        raise ResourceCaptureError("/proc/stat does not expose aggregate CPU counters")
    counters = [int(value) for value in first[1:]]
    idle = counters[3] + (counters[4] if len(counters) > 4 else 0)
    return sum(counters), idle


def _parse_meminfo(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for raw_line in text.splitlines():
        key, separator, remainder = raw_line.partition(":")
        if not separator:
            continue
        parts = remainder.strip().split()
        if not parts:
            continue
        value = int(parts[0])
        if len(parts) > 1 and parts[1].lower() == "kb":
            value *= 1024
        values[key] = value
    required = ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")
    missing = [key for key in required if key not in values]
    if missing:
        raise ResourceCaptureError(f"/proc/meminfo is missing: {', '.join(missing)}")
    return values


def _parse_net_dev(text: str) -> tuple[int, int]:
    rx_total = 0
    tx_total = 0
    for raw_line in text.splitlines()[2:]:
        if ":" not in raw_line:
            continue
        interface, payload = raw_line.split(":", 1)
        if interface.strip() == "lo":
            continue
        fields = payload.split()
        if len(fields) < 9:
            continue
        rx_total += int(fields[0])
        tx_total += int(fields[8])
    return rx_total, tx_total


def _unescape_mount_field(value: str) -> str:
    return _PROC_MOUNT_ESCAPE_RE.sub(lambda match: chr(int(match.group(1), 8)), value)


def _mount_device_for_path(text: str, path: Path) -> tuple[str, str] | None:
    target = str(path.resolve())
    candidates: list[tuple[int, str, str]] = []
    for raw_line in text.splitlines():
        left, separator, right = raw_line.partition(" - ")
        if not separator:
            continue
        fields = left.split()
        right_fields = right.split()
        if len(fields) < 5 or len(right_fields) < 2:
            continue
        major_minor = fields[2]
        mountpoint = _unescape_mount_field(fields[4])
        source = _unescape_mount_field(right_fields[1])
        prefix = mountpoint.rstrip("/") or "/"
        if target == prefix or target.startswith(prefix.rstrip("/") + "/"):
            candidates.append((len(prefix), major_minor, source))
    if not candidates:
        return None
    _, major_minor, source = max(candidates)
    return major_minor, source


def _parse_diskstats(text: str, major_minor: str) -> tuple[str, int, int] | None:
    wanted_major, separator, wanted_minor = major_minor.partition(":")
    if not separator:
        return None
    for raw_line in text.splitlines():
        fields = raw_line.split()
        if len(fields) < 10 or fields[0] != wanted_major or fields[1] != wanted_minor:
            continue
        device = fields[2]
        sectors_read = int(fields[5])
        sectors_written = int(fields[9])
        return device, sectors_read * 512, sectors_written * 512
    return None


def _filesystem_usage(path: Path) -> tuple[int, int, int, int]:
    statvfs = getattr(os, "statvfs", None)
    if statvfs is None:
        raise ResourceCaptureError("POSIX statvfs is required for deployment resource capture")
    stats = statvfs(path)
    block_size = stats.f_frsize or stats.f_bsize
    total_bytes = stats.f_blocks * block_size
    available_bytes = stats.f_bavail * block_size
    return total_bytes, available_bytes, stats.f_files, stats.f_favail


def capture_host_snapshot(
    *,
    proc_root: Path = DEFAULT_PROC_ROOT,
    filesystem_path: Path = DEFAULT_FILESYSTEM_PATH,
    monotonic: Callable[[], float] = time.monotonic,
) -> HostSnapshot:
    """Capture one Linux host snapshot without recording request/user identity data."""

    if not proc_root.exists():
        raise ResourceCaptureError("Linux /proc is required for deployment resource capture")
    cpu_total, cpu_idle = _parse_cpu_stat(_read_text(proc_root / "stat"))
    memory = _parse_meminfo(_read_text(proc_root / "meminfo"))
    network_rx, network_tx = _parse_net_dev(_read_text(proc_root / "net" / "dev"))
    fs_total, fs_available, inode_total, inode_available = _filesystem_usage(filesystem_path)

    disk_device: str | None = None
    disk_read: int | None = None
    disk_write: int | None = None
    mount = _mount_device_for_path(_read_text(proc_root / "self" / "mountinfo"), filesystem_path)
    if mount is not None:
        major_minor, source = mount
        disk = _parse_diskstats(_read_text(proc_root / "diskstats"), major_minor)
        if disk is not None:
            disk_name, disk_read, disk_write = disk
            disk_device = source if source.startswith("/dev/") else disk_name

    return HostSnapshot(
        monotonic_seconds=monotonic(),
        cpu_total=cpu_total,
        cpu_idle=cpu_idle,
        memory_total_bytes=memory["MemTotal"],
        memory_available_bytes=memory["MemAvailable"],
        swap_total_bytes=memory["SwapTotal"],
        swap_free_bytes=memory["SwapFree"],
        filesystem_total_bytes=fs_total,
        filesystem_available_bytes=fs_available,
        inode_total=inode_total,
        inode_available=inode_available,
        disk_device=disk_device,
        disk_read_bytes=disk_read,
        disk_write_bytes=disk_write,
        network_rx_bytes=network_rx,
        network_tx_bytes=network_tx,
    )


def _parse_size(value: str) -> int:
    match = _SIZE_RE.match(value)
    if match is None:
        raise ResourceCaptureError(f"Unsupported Docker size value: {value!r}")
    number = float(match.group(1))
    unit = (match.group(2) or "B").lower()
    factors = {
        "b": 1,
        "kb": 1000,
        "kib": 1024,
        "mb": 1000**2,
        "mib": 1024**2,
        "gb": 1000**3,
        "gib": 1024**3,
        "tb": 1000**4,
        "tib": 1024**4,
    }
    factor = factors.get(unit)
    if factor is None:
        raise ResourceCaptureError(f"Unsupported Docker size unit: {unit!r}")
    return int(number * factor)


def _parse_io_pair(value: str) -> tuple[int, int]:
    left, separator, right = value.partition("/")
    if not separator:
        raise ResourceCaptureError(f"Unsupported Docker I/O pair: {value!r}")
    return _parse_size(left), _parse_size(right)


def parse_docker_stats(text: str) -> dict[str, ContainerSnapshot]:
    """Parse ``docker stats --format '{{json .}}'`` output into bounded fields."""

    snapshots: dict[str, ContainerSnapshot] = {}
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        payload: dict[str, Any] = json.loads(raw_line)
        name = str(payload.get("Name") or "").strip()
        if not name:
            raise ResourceCaptureError("Docker stats record has no container name")
        memory_used, memory_limit = _parse_io_pair(str(payload["MemUsage"]))
        network_rx, network_tx = _parse_io_pair(str(payload["NetIO"]))
        block_read, block_write = _parse_io_pair(str(payload["BlockIO"]))
        snapshots[name] = ContainerSnapshot(
            name=name,
            cpu_percent=float(str(payload["CPUPerc"]).rstrip("%")),
            memory_percent=float(str(payload["MemPerc"]).rstrip("%")),
            memory_used_bytes=memory_used,
            memory_limit_bytes=memory_limit,
            network_rx_bytes=network_rx,
            network_tx_bytes=network_tx,
            block_read_bytes=block_read,
            block_write_bytes=block_write,
        )
    return snapshots


def _run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: float = 15.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def discover_containers(
    repo_root: Path,
    services: Sequence[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
) -> list[str]:
    result = runner(
        ["docker", "compose", "ps", "-q", *services],
        cwd=repo_root,
    )
    if result.returncode != 0:
        raise ResourceCaptureError(f"docker compose ps failed: {result.stderr.strip()}")
    container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not container_ids:
        raise ResourceCaptureError("No running deployment containers were found")
    return container_ids


def capture_container_stats(
    repo_root: Path,
    container_ids: Sequence[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
) -> dict[str, ContainerSnapshot]:
    result = runner(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}", *container_ids],
        cwd=repo_root,
    )
    if result.returncode != 0:
        raise ResourceCaptureError(f"docker stats failed: {result.stderr.strip()}")
    snapshots = parse_docker_stats(result.stdout)
    if not snapshots:
        raise ResourceCaptureError("docker stats returned no container records")
    return snapshots


def inspect_container_state(
    repo_root: Path,
    container_ids: Sequence[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
) -> dict[str, dict[str, Any]]:
    result = runner(["docker", "inspect", *container_ids], cwd=repo_root)
    if result.returncode != 0:
        raise ResourceCaptureError(f"docker inspect failed: {result.stderr.strip()}")
    document: list[dict[str, Any]] = json.loads(result.stdout)
    state: dict[str, dict[str, Any]] = {}
    for item in document:
        name = str(item.get("Name") or "").lstrip("/")
        container_state = item.get("State") or {}
        state[name] = {
            "status": str(container_state.get("Status") or "unknown"),
            "restartCount": int(item.get("RestartCount") or 0),
            "oomKilled": bool(container_state.get("OOMKilled")),
            "restarting": bool(container_state.get("Restarting")),
            "exitCode": int(container_state.get("ExitCode") or 0),
        }
    return state


def capture_container_events(
    repo_root: Path,
    container_ids: Sequence[str],
    *,
    since: datetime,
    until: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
) -> list[dict[str, str]]:
    command = [
        "docker",
        "events",
        "--since",
        _iso_timestamp(since),
        "--until",
        _iso_timestamp(until),
        "--filter",
        "type=container",
        "--filter",
        "event=oom",
        "--filter",
        "event=restart",
        "--format",
        "{{json .}}",
    ]
    for container_id in container_ids:
        command.extend(("--filter", f"container={container_id}"))
    result = runner(command, cwd=repo_root, timeout=20.0)
    if result.returncode != 0:
        raise ResourceCaptureError(f"docker events failed: {result.stderr.strip()}")
    events: list[dict[str, str]] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line.strip():
            continue
        payload: dict[str, Any] = json.loads(raw_line)
        actor = payload.get("Actor") or {}
        attributes = actor.get("Attributes") or {}
        action = str(payload.get("Action") or payload.get("status") or "unknown")
        events.append(
            {
                "container": str(attributes.get("name") or "unknown"),
                "action": action,
            }
        )
    return events


def _percent_used(total: int, available: int) -> float | None:
    if total <= 0:
        return None
    return (total - available) / total * 100.0


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _round_optional(value: float | None, digits: int = 3) -> float | None:
    return round(value, digits) if value is not None else None


def summarize_host(samples: Sequence[HostSnapshot]) -> dict[str, Any]:
    if len(samples) < 2:
        raise ResourceCaptureError("At least two host samples are required")

    cpu_percent: list[float] = []
    disk_read_rates: list[float] = []
    disk_write_rates: list[float] = []
    network_rx_rates: list[float] = []
    network_tx_rates: list[float] = []
    for previous, current in zip(samples[:-1], samples[1:], strict=True):
        elapsed = current.monotonic_seconds - previous.monotonic_seconds
        if elapsed <= 0:
            continue
        cpu_delta = current.cpu_total - previous.cpu_total
        idle_delta = current.cpu_idle - previous.cpu_idle
        if cpu_delta > 0:
            cpu_percent.append((cpu_delta - idle_delta) / cpu_delta * 100.0)
        network_rx_rates.append((current.network_rx_bytes - previous.network_rx_bytes) / elapsed)
        network_tx_rates.append((current.network_tx_bytes - previous.network_tx_bytes) / elapsed)
        if (
            current.disk_read_bytes is not None
            and previous.disk_read_bytes is not None
            and current.disk_write_bytes is not None
            and previous.disk_write_bytes is not None
            and current.disk_device == previous.disk_device
        ):
            disk_read_rates.append((current.disk_read_bytes - previous.disk_read_bytes) / elapsed)
            disk_write_rates.append(
                (current.disk_write_bytes - previous.disk_write_bytes) / elapsed
            )

    memory_used = [
        _percent_used(sample.memory_total_bytes, sample.memory_available_bytes)
        for sample in samples
    ]
    swap_used = [
        _percent_used(sample.swap_total_bytes, sample.swap_free_bytes) for sample in samples
    ]
    filesystem_used = [
        _percent_used(sample.filesystem_total_bytes, sample.filesystem_available_bytes)
        for sample in samples
    ]
    inode_used = [
        _percent_used(sample.inode_total, sample.inode_available) for sample in samples
    ]

    def present(values: Sequence[float | None]) -> list[float]:
        return [value for value in values if value is not None]

    memory_values = present(memory_used)
    swap_values = present(swap_used)
    filesystem_values = present(filesystem_used)
    inode_values = present(inode_used)
    last = samples[-1]
    return {
        "logicalCpuCount": os.cpu_count(),
        "cpuPercent": {
            "average": _round_optional(_mean(cpu_percent)),
            "max": _round_optional(max(cpu_percent) if cpu_percent else None),
        },
        "memory": {
            "totalBytes": last.memory_total_bytes,
            "minimumAvailableBytes": min(sample.memory_available_bytes for sample in samples),
            "averageUsedPercent": _round_optional(_mean(memory_values)),
            "maxUsedPercent": _round_optional(max(memory_values) if memory_values else None),
        },
        "swap": {
            "totalBytes": last.swap_total_bytes,
            "minimumFreeBytes": min(sample.swap_free_bytes for sample in samples),
            "averageUsedPercent": _round_optional(_mean(swap_values)),
            "maxUsedPercent": _round_optional(max(swap_values) if swap_values else None),
        },
        "filesystem": {
            "totalBytes": last.filesystem_total_bytes,
            "minimumAvailableBytes": min(sample.filesystem_available_bytes for sample in samples),
            "maxUsedPercent": _round_optional(
                max(filesystem_values) if filesystem_values else None
            ),
            "inodeTotal": last.inode_total,
            "minimumAvailableInodes": min(sample.inode_available for sample in samples),
            "maxInodeUsedPercent": _round_optional(max(inode_values) if inode_values else None),
        },
        "diskIo": {
            "device": last.disk_device,
            "averageReadBytesPerSecond": _round_optional(_mean(disk_read_rates)),
            "maxReadBytesPerSecond": _round_optional(
                max(disk_read_rates) if disk_read_rates else None
            ),
            "averageWriteBytesPerSecond": _round_optional(_mean(disk_write_rates)),
            "maxWriteBytesPerSecond": _round_optional(
                max(disk_write_rates) if disk_write_rates else None
            ),
        },
        "network": {
            "averageReceiveBytesPerSecond": _round_optional(_mean(network_rx_rates)),
            "maxReceiveBytesPerSecond": _round_optional(
                max(network_rx_rates) if network_rx_rates else None
            ),
            "averageTransmitBytesPerSecond": _round_optional(_mean(network_tx_rates)),
            "maxTransmitBytesPerSecond": _round_optional(
                max(network_tx_rates) if network_tx_rates else None
            ),
        },
    }


def summarize_containers(
    samples: Sequence[dict[str, ContainerSnapshot]],
    *,
    start_state: dict[str, dict[str, Any]],
    end_state: dict[str, dict[str, Any]],
    events: Sequence[dict[str, str]],
) -> dict[str, Any]:
    names = sorted({name for sample in samples for name in sample})
    summary: dict[str, Any] = {}
    for name in names:
        values = [sample[name] for sample in samples if name in sample]
        first = values[0]
        last = values[-1]
        start = start_state.get(name, {})
        end = end_state.get(name, {})
        summary[name] = {
            "cpuPercent": {
                "average": _round_optional(_mean([value.cpu_percent for value in values])),
                "max": _round_optional(max(value.cpu_percent for value in values)),
            },
            "memory": {
                "limitBytes": last.memory_limit_bytes,
                "maxUsedBytes": max(value.memory_used_bytes for value in values),
                "averageUsedPercent": _round_optional(
                    _mean([value.memory_percent for value in values])
                ),
                "maxUsedPercent": _round_optional(max(value.memory_percent for value in values)),
            },
            "networkDeltaBytes": {
                "receive": max(0, last.network_rx_bytes - first.network_rx_bytes),
                "transmit": max(0, last.network_tx_bytes - first.network_tx_bytes),
            },
            "blockIoDeltaBytes": {
                "read": max(0, last.block_read_bytes - first.block_read_bytes),
                "write": max(0, last.block_write_bytes - first.block_write_bytes),
            },
            "state": end,
            "restartCountDelta": max(
                0,
                int(end.get("restartCount", 0)) - int(start.get("restartCount", 0)),
            ),
            "events": [event["action"] for event in events if event["container"] == name],
        }
    return summary


def _validate_number(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise SystemExit(f"{name} must be greater than zero")


def capture_resources(
    repo_root: Path,
    *,
    duration_seconds: float,
    interval_seconds: float,
    services: Sequence[str] = DEFAULT_SERVICES,
    command: Sequence[str] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = _utc_now,
) -> tuple[dict[str, Any], int]:
    """Capture host/container resource evidence, optionally while running a command."""

    if sys.platform != "linux":
        raise ResourceCaptureError("deployment resource capture must run on the Linux host")
    container_ids = discover_containers(repo_root, services)
    started_at = now()
    start_state = inspect_container_state(repo_root, container_ids)
    host_samples = [capture_host_snapshot(filesystem_path=repo_root)]
    container_samples = [capture_container_stats(repo_root, container_ids)]

    child: subprocess.Popen[Any] | None = None
    command_exit_code = 0
    if command:
        child = subprocess.Popen(list(command), cwd=repo_root)

    start_monotonic = time.monotonic()
    while True:
        if child is not None:
            if child.poll() is not None:
                command_exit_code = int(child.returncode or 0)
                break
        elif time.monotonic() - start_monotonic >= duration_seconds:
            break
        sleep(interval_seconds)
        host_samples.append(capture_host_snapshot(filesystem_path=repo_root))
        container_samples.append(capture_container_stats(repo_root, container_ids))

    host_samples.append(capture_host_snapshot(filesystem_path=repo_root))
    container_samples.append(capture_container_stats(repo_root, container_ids))
    ended_at = now()
    end_state = inspect_container_state(repo_root, container_ids)
    events = capture_container_events(
        repo_root,
        container_ids,
        since=started_at,
        until=ended_at,
    )
    report = {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "startedAt": _iso_timestamp(started_at),
        "endedAt": _iso_timestamp(ended_at),
        "durationSeconds": round(
            host_samples[-1].monotonic_seconds - host_samples[0].monotonic_seconds, 3
        ),
        "sampleIntervalSeconds": interval_seconds,
        "sampleCount": len(host_samples),
        "command": {
            "ran": bool(command),
            "exitCode": command_exit_code if command else None,
        },
        "host": summarize_host(host_samples),
        "containers": summarize_containers(
            container_samples,
            start_state=start_state,
            end_state=end_state,
            events=events,
        ),
    }
    return report, command_exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture privacy-safe Linux host and Docker resource evidence, optionally while "
            "running another command."
        )
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION_SECONDS,
        help=f"capture duration without a wrapped command (default: {DEFAULT_DURATION_SECONDS:g}s)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"resource sample interval (default: {DEFAULT_INTERVAL_SECONDS:g}s)",
    )
    parser.add_argument(
        "--service",
        action="append",
        dest="services",
        help="Compose service to sample; repeat as needed (default: app and caddy)",
    )
    parser.add_argument("--output", type=Path, required=True, help="JSON report path")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="optional command to run while sampling; prefix it with --",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _validate_number("--duration", args.duration)
    _validate_number("--interval", args.interval)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if args.command and not command:
        raise SystemExit("wrapped command cannot be empty")
    services = tuple(args.services or DEFAULT_SERVICES)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        report, command_exit_code = capture_resources(
            repo_root,
            duration_seconds=args.duration,
            interval_seconds=args.interval,
            services=services,
            command=command or None,
        )
    except (OSError, ResourceCaptureError, subprocess.SubprocessError, ValueError) as exc:
        print(f"Resource capture failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Deployment resource report: {args.output}")
    return command_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
