from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from tools.deployment_resources import (
    ContainerSnapshot,
    HostSnapshot,
    ResourceCaptureError,
    _mount_device_for_path,
    _parse_cpu_stat,
    _parse_diskstats,
    _parse_meminfo,
    _parse_net_dev,
    _parse_size,
    capture_container_events,
    discover_containers,
    main,
    parse_docker_stats,
    summarize_containers,
    summarize_host,
)


def test_linux_proc_parsers_keep_only_bounded_resource_counters(tmp_path: Path) -> None:
    assert _parse_cpu_stat("cpu  100 20 30 400 10 5 6 7\ncpu0 1 2 3 4\n") == (578, 410)
    memory = _parse_meminfo(
        "MemTotal: 1024 kB\nMemAvailable: 512 kB\nSwapTotal: 256 kB\nSwapFree: 128 kB\n"
    )
    assert memory == {
        "MemTotal": 1024 * 1024,
        "MemAvailable": 512 * 1024,
        "SwapTotal": 256 * 1024,
        "SwapFree": 128 * 1024,
    }
    network = _parse_net_dev(
        "Inter-| Receive | Transmit\n"
        " face |bytes packets errs drop fifo frame compressed multicast|"
        "bytes packets errs drop fifo colls carrier compressed\n"
        " lo: 999 0 0 0 0 0 0 0 999 0 0 0 0 0 0 0\n"
        " eth0: 1000 0 0 0 0 0 0 0 2000 0 0 0 0 0 0 0\n"
    )
    assert network == (1000, 2000)

    mountpoint = tmp_path / "deploy root"
    mountpoint.mkdir()
    escaped = str(mountpoint).replace(" ", "\\040")
    mount = _mount_device_for_path(
        f"24 1 253:0 / {escaped} rw,relatime - ext4 /dev/mapper/vg-root rw\n",
        mountpoint,
    )
    assert mount == ("253:0", "/dev/mapper/vg-root")
    assert _parse_diskstats("253 0 dm-0 1 0 8 0 2 0 16 0 0 0 0 0\n", "253:0") == (
        "dm-0",
        4096,
        8192,
    )


def test_docker_stat_parser_supports_binary_and_decimal_units() -> None:
    payload = json.dumps(
        {
            "Name": "infinitydb-app-1",
            "CPUPerc": "12.50%",
            "MemPerc": "25.00%",
            "MemUsage": "512MiB / 2GiB",
            "NetIO": "1.5MB / 2MiB",
            "BlockIO": "4kB / 8KiB",
        }
    )
    result = parse_docker_stats(payload)["infinitydb-app-1"]
    assert result.cpu_percent == 12.5
    assert result.memory_used_bytes == 512 * 1024**2
    assert result.memory_limit_bytes == 2 * 1024**3
    assert result.network_rx_bytes == 1_500_000
    assert result.network_tx_bytes == 2 * 1024**2
    assert result.block_read_bytes == 4000
    assert result.block_write_bytes == 8192
    assert _parse_size("0B") == 0


def _host_sample(
    timestamp: float,
    *,
    cpu_total: int,
    cpu_idle: int,
    network_rx: int,
    network_tx: int,
    disk_read: int,
    disk_write: int,
) -> HostSnapshot:
    return HostSnapshot(
        monotonic_seconds=timestamp,
        cpu_total=cpu_total,
        cpu_idle=cpu_idle,
        memory_total_bytes=1000,
        memory_available_bytes=400,
        swap_total_bytes=100,
        swap_free_bytes=75,
        filesystem_total_bytes=2000,
        filesystem_available_bytes=500,
        inode_total=1000,
        inode_available=800,
        disk_device="dm-0",
        disk_read_bytes=disk_read,
        disk_write_bytes=disk_write,
        network_rx_bytes=network_rx,
        network_tx_bytes=network_tx,
    )


def test_host_summary_reports_rates_without_identity_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tools.deployment_resources.os.cpu_count", lambda: 4)
    report = summarize_host(
        [
            _host_sample(
                10.0,
                cpu_total=100,
                cpu_idle=40,
                network_rx=1000,
                network_tx=2000,
                disk_read=3000,
                disk_write=4000,
            ),
            _host_sample(
                12.0,
                cpu_total=200,
                cpu_idle=60,
                network_rx=3000,
                network_tx=6000,
                disk_read=7000,
                disk_write=10_000,
            ),
        ]
    )
    assert report["logicalCpuCount"] == 4
    assert report["cpuPercent"] == {"average": 80.0, "max": 80.0}
    assert report["memory"]["maxUsedPercent"] == 60.0
    assert report["swap"]["maxUsedPercent"] == 25.0
    assert report["filesystem"]["maxUsedPercent"] == 75.0
    assert report["diskIo"]["averageReadBytesPerSecond"] == 2000.0
    assert report["network"]["averageTransmitBytesPerSecond"] == 2000.0
    assert "hostname" not in json.dumps(report).lower()


def _container(
    cpu: float,
    memory: int,
    rx: int,
    tx: int,
    read: int,
    write: int,
) -> ContainerSnapshot:
    return ContainerSnapshot(
        name="infinitydb-app-1",
        cpu_percent=cpu,
        memory_percent=memory / 10,
        memory_used_bytes=memory,
        memory_limit_bytes=1000,
        network_rx_bytes=rx,
        network_tx_bytes=tx,
        block_read_bytes=read,
        block_write_bytes=write,
    )


def test_container_summary_retains_resource_and_restart_oom_evidence_only() -> None:
    report = summarize_containers(
        [
            {"infinitydb-app-1": _container(10, 200, 100, 200, 300, 400)},
            {"infinitydb-app-1": _container(30, 400, 500, 800, 900, 1400)},
        ],
        start_state={"infinitydb-app-1": {"restartCount": 2}},
        end_state={
            "infinitydb-app-1": {
                "status": "running",
                "restartCount": 3,
                "oomKilled": False,
                "restarting": False,
                "exitCode": 0,
            }
        },
        events=[{"container": "infinitydb-app-1", "action": "restart"}],
    )["infinitydb-app-1"]
    assert report["cpuPercent"] == {"average": 20.0, "max": 30}
    assert report["memory"]["maxUsedBytes"] == 400
    assert report["networkDeltaBytes"] == {"receive": 400, "transmit": 600}
    assert report["blockIoDeltaBytes"] == {"read": 600, "write": 1000}
    assert report["restartCountDelta"] == 1
    assert report["events"] == ["restart"]


def test_container_discovery_and_events_do_not_retain_unbounded_docker_payloads(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[:4] == ["docker", "compose", "ps", "-q"]:
            return subprocess.CompletedProcess(command, 0, "aaa\nbbb\n", "")
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "Action": "oom",
                    "Actor": {
                        "ID": "secret-container-id",
                        "Attributes": {"name": "infinitydb-app-1", "url": "/search?q=private"},
                    },
                }
            )
            + "\n",
            "",
        )

    assert discover_containers(tmp_path, ("app", "caddy"), runner=runner) == ["aaa", "bbb"]
    events = capture_container_events(
        tmp_path,
        ("aaa", "bbb"),
        since=datetime_from_iso("2026-10-06T07:00:00Z"),
        until=datetime_from_iso("2026-10-06T07:01:00Z"),
        runner=runner,
    )
    assert events == [{"container": "infinitydb-app-1", "action": "oom"}]
    assert "private" not in json.dumps(events)
    assert any("event=oom" in command for command in calls)
    assert any("event=restart" in command for command in calls)


def datetime_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))



def test_main_wraps_command_but_does_not_retain_command_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "resources.json"
    observed: dict[str, object] = {}

    def fake_capture(
        _repo_root: Path,
        **kwargs: object,
    ) -> tuple[dict[str, object], int]:
        observed.update(kwargs)
        return {
            "format": "InfinityDB deployment resource capture",
            "command": {"ran": True, "exitCode": 7},
        }, 7

    monkeypatch.setattr("tools.deployment_resources.capture_resources", fake_capture)
    exit_code = main(
        [
            "--output",
            str(output),
            "--",
            "python",
            "tools/capacity_test.py",
            "http://127.0.0.1:8080",
        ]
    )
    assert exit_code == 7
    assert observed["command"] == [
        "python",
        "tools/capacity_test.py",
        "http://127.0.0.1:8080",
    ]
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["command"] == {"ran": True, "exitCode": 7}
    assert "127.0.0.1" not in output.read_text(encoding="utf-8")

def test_meminfo_rejects_missing_required_counters() -> None:
    with pytest.raises(ResourceCaptureError, match="SwapFree"):
        _parse_meminfo("MemTotal: 1 kB\nMemAvailable: 1 kB\nSwapTotal: 0 kB\n")
