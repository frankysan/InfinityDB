from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.deployment_alerts import (
    AlertThresholds,
    build_report,
    evaluate_resource_report,
    evaluate_server_errors,
    main,
)
from tools.report_metrics import parse_prometheus


def _resource_report(
    *,
    ended_at: str = "2026-10-06T08:00:00Z",
    duration: float = 70.0,
    cpu: float = 40.0,
    memory: float = 60.0,
    filesystem_used: float = 70.0,
    inode_used: float = 30.0,
    oom: bool = False,
    restart_delta: int = 0,
) -> dict[str, object]:
    events = ["oom"] if oom else []
    return {
        "format": "InfinityDB deployment resource capture",
        "formatVersion": 1,
        "startedAt": "2026-10-06T07:58:50Z",
        "endedAt": ended_at,
        "durationSeconds": duration,
        "sampleIntervalSeconds": 2.0,
        "sampleCount": 36,
        "host": {
            "cpuPercent": {"average": cpu, "max": cpu},
            "memory": {"maxUsedPercent": memory},
            "filesystem": {
                "maxUsedPercent": filesystem_used,
                "maxInodeUsedPercent": inode_used,
            },
        },
        "containers": {
            "infinitydb-app-1": {
                "memory": {"maxUsedPercent": memory},
                "state": {"oomKilled": oom, "restarting": False},
                "restartCountDelta": restart_delta,
                "events": events,
            }
        },
    }


def _metrics(*, ok: int, errors: int) -> str:
    return (
        '# TYPE infinitydb_http_requests_total counter\n'
        f'infinitydb_http_requests_total{{route="/units",status_class="2xx"}} {ok}\n'
        f'infinitydb_http_requests_total{{route="/units",status_class="5xx"}} {errors}\n'
    )


def test_resource_thresholds_cover_cpu_memory_disk_inode_oom_and_restarts() -> None:
    checks = evaluate_resource_report(
        _resource_report(
            cpu=96,
            memory=88,
            filesystem_used=96,
            inode_used=86,
            oom=True,
            restart_delta=1,
        ),
        AlertThresholds(),
        now=datetime(2026, 10, 6, 8, 1, tzinfo=UTC),
        max_age_seconds=300,
    )
    statuses = {check["name"]: check["status"] for check in checks}
    assert statuses == {
        "resource_freshness": "ok",
        "cpu_saturation": "critical",
        "memory_pressure": "warning",
        "filesystem_space": "critical",
        "filesystem_inodes": "warning",
        "container_oom": "critical",
        "container_restart": "warning",
    }


def test_cpu_requires_a_sustained_resource_window_and_fresh_evidence() -> None:
    checks = evaluate_resource_report(
        _resource_report(duration=30, ended_at="2026-10-06T07:00:00Z"),
        AlertThresholds(),
        now=datetime(2026, 10, 6, 8, 0, tzinfo=UTC),
        max_age_seconds=300,
    )
    statuses = {check["name"]: check["status"] for check in checks}
    assert statuses["resource_freshness"] == "unknown"
    assert statuses["cpu_saturation"] == "unknown"


def test_server_error_thresholds_use_counter_deltas_not_process_lifetime_totals() -> None:
    before = parse_prometheus(_metrics(ok=900, errors=100))
    warning = parse_prometheus(_metrics(ok=995, errors=105))
    critical = parse_prometheus(_metrics(ok=1080, errors=120))

    warning_check = evaluate_server_errors(before, warning, AlertThresholds())
    assert warning_check["status"] == "warning"
    assert warning_check["observed"] == {
        "requestCount": 100,
        "serverErrorCount": 5,
        "serverErrorPercent": 5.0,
    }

    critical_check = evaluate_server_errors(before, critical, AlertThresholds())
    assert critical_check["status"] == "critical"
    assert critical_check["observed"]["requestCount"] == 200
    assert critical_check["observed"]["serverErrorCount"] == 20
    assert critical_check["observed"]["serverErrorPercent"] == 10.0


def test_metrics_reset_is_unknown_instead_of_fabricating_a_rate() -> None:
    check = evaluate_server_errors(
        parse_prometheus(_metrics(ok=100, errors=10)),
        parse_prometheus(_metrics(ok=5, errors=0)),
        AlertThresholds(),
    )
    assert check["status"] == "unknown"
    assert "reset" in check["message"]


def test_report_exit_status_prioritizes_critical_health_failure() -> None:
    report = build_report(
        resource_report=_resource_report(),
        thresholds=AlertThresholds(),
        before_metrics=parse_prometheus(_metrics(ok=100, errors=0)),
        after_metrics=parse_prometheus(_metrics(ok=200, errors=0)),
        health_samples=[True, False],
        now=datetime(2026, 10, 6, 8, 1, tzinfo=UTC),
        max_resource_age_seconds=300,
        sample_seconds=60,
    )
    assert report["status"] == "critical"
    assert report["exitCode"] == 2
    assert "metrics-url" not in json.dumps(report).lower()
    assert "health-url" not in json.dumps(report).lower()


def test_main_writes_privacy_safe_report_and_returns_warning(tmp_path: Path) -> None:
    resource_path = tmp_path / "resources.json"
    output_path = tmp_path / "alerts.json"
    resource_path.write_text(
        json.dumps(_resource_report(memory=90)),
        encoding="utf-8",
        newline="\n",
    )
    metrics = iter((_metrics(ok=100, errors=0), _metrics(ok=200, errors=0)))
    slept: list[float] = []

    exit_code = main(
        [
            "--resource-report",
            str(resource_path),
            "--metrics-url",
            "http://192.0.2.10:9090/metrics",
            "--health-url",
            "http://192.0.2.10:9090/health",
            "--sample-seconds",
            "1",
            "--output",
            str(output_path),
        ],
        sleep=slept.append,
        now=lambda: datetime(2026, 10, 6, 8, 1, tzinfo=UTC),
        metrics_fetcher=lambda _url, *, timeout: next(metrics),
        health_fetcher=lambda _url, *, timeout: True,
    )

    assert exit_code == 1
    assert slept == [1.0]
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "warning"
    retained = output_path.read_text(encoding="utf-8")
    assert "192.0.2.10" not in retained
    assert str(resource_path) not in retained


def test_main_returns_unknown_when_metrics_cannot_be_sampled(tmp_path: Path) -> None:
    resource_path = tmp_path / "resources.json"
    resource_path.write_text(
        json.dumps(_resource_report()),
        encoding="utf-8",
        newline="\n",
    )

    def fail_metrics(_url: str, *, timeout: float) -> str:
        raise OSError("unavailable")

    exit_code = main(
        ["--resource-report", str(resource_path), "--sample-seconds", "1"],
        sleep=lambda _seconds: None,
        now=lambda: datetime(2026, 10, 6, 8, 1, tzinfo=UTC),
        metrics_fetcher=fail_metrics,
        health_fetcher=lambda _url, *, timeout: True,
    )
    assert exit_code == 3


def test_invalid_threshold_order_is_rejected(tmp_path: Path) -> None:
    resource_path = tmp_path / "resources.json"
    resource_path.write_text(
        json.dumps(_resource_report()),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(SystemExit, match="CPU warning threshold"):
        main(
            [
                "--resource-report",
                str(resource_path),
                "--cpu-warning",
                "95",
                "--cpu-critical",
                "90",
            ]
        )
