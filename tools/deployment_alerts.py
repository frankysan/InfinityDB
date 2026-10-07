#!/usr/bin/env python3
"""Evaluate privacy-safe operational alert thresholds for an InfinityDB deployment."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.deployment_resources import FORMAT as RESOURCE_FORMAT
from tools.report_metrics import DEFAULT_METRICS_URL, MetricsReport, fetch_metrics, parse_prometheus

FORMAT = "InfinityDB deployment alert evaluation"
FORMAT_VERSION = 1
DEFAULT_SAMPLE_SECONDS = 60.0
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_RESOURCE_AGE_SECONDS = 300.0


class AlertEvaluationError(RuntimeError):
    """Raised when retained alert evidence cannot be evaluated safely."""


@dataclass(frozen=True)
class AlertThresholds:
    cpu_warning_percent: float = 85.0
    cpu_critical_percent: float = 95.0
    cpu_minimum_duration_seconds: float = 60.0
    memory_warning_percent: float = 85.0
    memory_critical_percent: float = 95.0
    filesystem_free_warning_percent: float = 15.0
    filesystem_free_critical_percent: float = 5.0
    inode_free_warning_percent: float = 15.0
    inode_free_critical_percent: float = 5.0
    server_error_warning_percent: float = 1.0
    server_error_critical_percent: float = 5.0
    server_error_warning_count: int = 5
    server_error_critical_count: int = 10


_STATUS_PRIORITY = {"ok": 0, "warning": 1, "unknown": 2, "critical": 3}
_EXIT_CODE = {"ok": 0, "warning": 1, "critical": 2, "unknown": 3}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise AlertEvaluationError(f"resource report {field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AlertEvaluationError(f"resource report {field} is not a valid ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise AlertEvaluationError(f"resource report {field} must include a timezone")
    return parsed.astimezone(UTC)


def _number(value: object, *, field: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise AlertEvaluationError(f"resource report {field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise AlertEvaluationError(f"resource report {field} must be finite")
    return number


def _mapping(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AlertEvaluationError(f"resource report {field} must be an object")
    return value


def load_resource_report(path: Path) -> dict[str, Any]:
    """Load one retained deployment-resource report."""

    try:
        document: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AlertEvaluationError(f"unable to read deployment resource report: {exc}") from exc
    report = _mapping(document, field="root")
    if report.get("format") != RESOURCE_FORMAT:
        raise AlertEvaluationError("input is not an InfinityDB deployment resource report")
    return report


def _check(
    name: str,
    status: str,
    message: str,
    *,
    observed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name, "status": status, "message": message}
    if observed is not None:
        result["observed"] = observed
    return result


def _threshold_status(
    value: float,
    *,
    warning: float,
    critical: float,
    higher_is_worse: bool,
) -> str:
    if higher_is_worse:
        if value >= critical:
            return "critical"
        if value >= warning:
            return "warning"
    else:
        if value <= critical:
            return "critical"
        if value <= warning:
            return "warning"
    return "ok"


def evaluate_resource_report(
    report: dict[str, Any],
    thresholds: AlertThresholds,
    *,
    now: datetime,
    max_age_seconds: float,
) -> list[dict[str, Any]]:
    """Evaluate host/container thresholds from one bounded resource report."""

    ended_at = _parse_timestamp(report.get("endedAt"), field="endedAt")
    age_seconds = max(0.0, (now.astimezone(UTC) - ended_at).total_seconds())
    checks: list[dict[str, Any]] = []
    if age_seconds > max_age_seconds:
        checks.append(
            _check(
                "resource_freshness",
                "unknown",
                "resource evidence is older than the configured maximum age",
                observed={"ageSeconds": round(age_seconds, 3)},
            )
        )
    else:
        checks.append(
            _check(
                "resource_freshness",
                "ok",
                "resource evidence is recent enough for alert evaluation",
                observed={"ageSeconds": round(age_seconds, 3)},
            )
        )

    duration = _number(report.get("durationSeconds"), field="durationSeconds")
    host = _mapping(report.get("host"), field="host")
    cpu = _mapping(host.get("cpuPercent"), field="host.cpuPercent")
    cpu_average = _number(cpu.get("average"), field="host.cpuPercent.average")
    if duration < thresholds.cpu_minimum_duration_seconds:
        checks.append(
            _check(
                "cpu_saturation",
                "unknown",
                "resource capture is too short to establish sustained CPU saturation",
                observed={"averagePercent": cpu_average, "durationSeconds": duration},
            )
        )
    else:
        status = _threshold_status(
            cpu_average,
            warning=thresholds.cpu_warning_percent,
            critical=thresholds.cpu_critical_percent,
            higher_is_worse=True,
        )
        checks.append(
            _check(
                "cpu_saturation",
                status,
                "sustained host CPU utilization evaluated over the resource window",
                observed={"averagePercent": cpu_average, "durationSeconds": duration},
            )
        )

    memory = _mapping(host.get("memory"), field="host.memory")
    host_memory_used = _number(
        memory.get("maxUsedPercent"), field="host.memory.maxUsedPercent"
    )
    containers = _mapping(report.get("containers"), field="containers")
    container_memory_values: list[float] = []
    for name, raw_container in sorted(containers.items()):
        container = _mapping(raw_container, field=f"containers.{name}")
        container_memory = _mapping(container.get("memory"), field=f"containers.{name}.memory")
        container_memory_values.append(
            _number(
                container_memory.get("maxUsedPercent"),
                field=f"containers.{name}.memory.maxUsedPercent",
            )
        )
    container_memory_used = max(container_memory_values, default=0.0)
    memory_used = max(host_memory_used, container_memory_used)
    memory_status = _threshold_status(
        memory_used,
        warning=thresholds.memory_warning_percent,
        critical=thresholds.memory_critical_percent,
        higher_is_worse=True,
    )
    checks.append(
        _check(
            "memory_pressure",
            memory_status,
            "maximum host/container memory utilization evaluated over the resource window",
            observed={
                "hostMaxUsedPercent": host_memory_used,
                "containerMaxUsedPercent": container_memory_used,
            },
        )
    )

    filesystem = _mapping(host.get("filesystem"), field="host.filesystem")
    filesystem_used = _number(
        filesystem.get("maxUsedPercent"), field="host.filesystem.maxUsedPercent"
    )
    filesystem_free = max(0.0, 100.0 - filesystem_used)
    filesystem_status = _threshold_status(
        filesystem_free,
        warning=thresholds.filesystem_free_warning_percent,
        critical=thresholds.filesystem_free_critical_percent,
        higher_is_worse=False,
    )
    checks.append(
        _check(
            "filesystem_space",
            filesystem_status,
            "minimum filesystem free-space percentage evaluated over the resource window",
            observed={"minimumFreePercent": round(filesystem_free, 3)},
        )
    )

    inode_used = _number(
        filesystem.get("maxInodeUsedPercent"), field="host.filesystem.maxInodeUsedPercent"
    )
    inode_free = max(0.0, 100.0 - inode_used)
    inode_status = _threshold_status(
        inode_free,
        warning=thresholds.inode_free_warning_percent,
        critical=thresholds.inode_free_critical_percent,
        higher_is_worse=False,
    )
    checks.append(
        _check(
            "filesystem_inodes",
            inode_status,
            "minimum filesystem free-inode percentage evaluated over the resource window",
            observed={"minimumFreePercent": round(inode_free, 3)},
        )
    )

    oom_containers: list[str] = []
    restarting_containers: list[str] = []
    restarted_containers: list[str] = []
    for name, raw_container in sorted(containers.items()):
        container = _mapping(raw_container, field=f"containers.{name}")
        state = _mapping(container.get("state"), field=f"containers.{name}.state")
        events = container.get("events")
        if not isinstance(events, list) or not all(isinstance(event, str) for event in events):
            raise AlertEvaluationError(f"resource report containers.{name}.events must be strings")
        if bool(state.get("oomKilled")) or "oom" in events:
            oom_containers.append(name)
        if bool(state.get("restarting")):
            restarting_containers.append(name)
        restart_delta = container.get("restartCountDelta", 0)
        if not isinstance(restart_delta, int) or isinstance(restart_delta, bool):
            raise AlertEvaluationError(
                f"resource report containers.{name}.restartCountDelta must be an integer"
            )
        if restart_delta > 0 or "restart" in events:
            restarted_containers.append(name)

    if oom_containers:
        checks.append(
            _check(
                "container_oom",
                "critical",
                "one or more deployment containers were OOM-killed",
                observed={"containerCount": len(oom_containers)},
            )
        )
    else:
        checks.append(_check("container_oom", "ok", "no container OOM kills were observed"))

    if restarting_containers or restarted_containers:
        checks.append(
            _check(
                "container_restart",
                "warning",
                "one or more deployment containers restarted or are restarting",
                observed={
                    "restartedContainerCount": len(set(restarted_containers)),
                    "restartingContainerCount": len(set(restarting_containers)),
                },
            )
        )
    else:
        checks.append(
            _check("container_restart", "ok", "no container restarts were observed")
        )
    return checks


def evaluate_server_errors(
    before: MetricsReport,
    after: MetricsReport,
    thresholds: AlertThresholds,
) -> dict[str, Any]:
    """Evaluate the 5xx delta between two process-lifetime metrics snapshots."""

    request_delta = after.total_requests - before.total_requests
    error_delta = after.status_counts.get("5xx", 0) - before.status_counts.get("5xx", 0)
    if request_delta < 0 or error_delta < 0:
        return _check(
            "server_errors",
            "unknown",
            "application metrics reset during the sampling interval",
        )
    if request_delta == 0:
        return _check(
            "server_errors",
            "ok",
            "no completed requests were observed during the metrics interval",
            observed={"requestCount": 0, "serverErrorCount": 0, "serverErrorPercent": 0.0},
        )

    error_percent = error_delta / request_delta * 100.0
    status = "ok"
    if (
        error_delta >= thresholds.server_error_critical_count
        and error_percent >= thresholds.server_error_critical_percent
    ):
        status = "critical"
    elif (
        error_delta >= thresholds.server_error_warning_count
        and error_percent >= thresholds.server_error_warning_percent
    ):
        status = "warning"
    return _check(
        "server_errors",
        status,
        "5xx response rate evaluated from bounded aggregate counter deltas",
        observed={
            "requestCount": request_delta,
            "serverErrorCount": error_delta,
            "serverErrorPercent": round(error_percent, 3),
        },
    )


def fetch_health(url: str, *, timeout: float) -> bool:
    """Return whether the deployment health endpoint responds successfully."""

    request = urllib.request.Request(url, headers={"User-Agent": "InfinityDB alert evaluator"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= int(response.status) < 300
    except (OSError, urllib.error.URLError):
        return False


def evaluate_health(samples: Sequence[bool]) -> dict[str, Any]:
    failed = sum(1 for sample in samples if not sample)
    if failed:
        return _check(
            "health",
            "critical",
            "one or more deployment health probes failed",
            observed={"sampleCount": len(samples), "failedCount": failed},
        )
    return _check(
        "health",
        "ok",
        "all deployment health probes succeeded",
        observed={"sampleCount": len(samples), "failedCount": 0},
    )


def _overall_status(checks: Sequence[dict[str, Any]]) -> str:
    return max(
        (str(check["status"]) for check in checks),
        key=lambda status: _STATUS_PRIORITY[status],
        default="unknown",
    )


def build_report(
    *,
    resource_report: dict[str, Any],
    thresholds: AlertThresholds,
    before_metrics: MetricsReport | None,
    after_metrics: MetricsReport | None,
    health_samples: Sequence[bool],
    now: datetime,
    max_resource_age_seconds: float,
    sample_seconds: float,
    metrics_error: bool = False,
) -> dict[str, Any]:
    checks = evaluate_resource_report(
        resource_report,
        thresholds,
        now=now,
        max_age_seconds=max_resource_age_seconds,
    )
    checks.append(evaluate_health(health_samples))
    if metrics_error or before_metrics is None or after_metrics is None:
        checks.append(
            _check(
                "server_errors",
                "unknown",
                "aggregate application metrics could not be sampled",
            )
        )
    else:
        checks.append(evaluate_server_errors(before_metrics, after_metrics, thresholds))
    status = _overall_status(checks)
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "evaluatedAt": _iso_timestamp(now),
        "status": status,
        "exitCode": _EXIT_CODE[status],
        "sampleSeconds": sample_seconds,
        "thresholds": _threshold_document(thresholds),
        "checks": checks,
    }


def _positive(name: str, value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise SystemExit(f"{name} must be greater than zero")
    return value


def _percentage(name: str, value: float) -> float:
    if not math.isfinite(value) or value < 0 or value > 100:
        raise SystemExit(f"{name} must be between 0 and 100")
    return value


def _health_url(metrics_url: str) -> str:
    parts = urllib.parse.urlsplit(metrics_url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/health", "", ""))


def _threshold_document(thresholds: AlertThresholds) -> dict[str, float | int]:
    return {
        "cpuWarningPercent": thresholds.cpu_warning_percent,
        "cpuCriticalPercent": thresholds.cpu_critical_percent,
        "cpuMinimumDurationSeconds": thresholds.cpu_minimum_duration_seconds,
        "memoryWarningPercent": thresholds.memory_warning_percent,
        "memoryCriticalPercent": thresholds.memory_critical_percent,
        "filesystemFreeWarningPercent": thresholds.filesystem_free_warning_percent,
        "filesystemFreeCriticalPercent": thresholds.filesystem_free_critical_percent,
        "inodeFreeWarningPercent": thresholds.inode_free_warning_percent,
        "inodeFreeCriticalPercent": thresholds.inode_free_critical_percent,
        "serverErrorWarningPercent": thresholds.server_error_warning_percent,
        "serverErrorCriticalPercent": thresholds.server_error_critical_percent,
        "serverErrorWarningCount": thresholds.server_error_warning_count,
        "serverErrorCriticalCount": thresholds.server_error_critical_count,
    }


def _validate_thresholds(thresholds: AlertThresholds) -> None:
    if thresholds.cpu_warning_percent >= thresholds.cpu_critical_percent:
        raise SystemExit("CPU warning threshold must be lower than critical")
    if thresholds.memory_warning_percent >= thresholds.memory_critical_percent:
        raise SystemExit("memory warning threshold must be lower than critical")
    if thresholds.filesystem_free_warning_percent <= thresholds.filesystem_free_critical_percent:
        raise SystemExit("filesystem free warning threshold must be higher than critical")
    if thresholds.inode_free_warning_percent <= thresholds.inode_free_critical_percent:
        raise SystemExit("inode free warning threshold must be higher than critical")
    if thresholds.server_error_warning_percent >= thresholds.server_error_critical_percent:
        raise SystemExit("5xx warning percentage must be lower than critical")
    if thresholds.server_error_warning_count >= thresholds.server_error_critical_count:
        raise SystemExit("5xx warning count must be lower than critical")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate InfinityDB operational alert thresholds from a recent resource report, "
            "bounded aggregate metrics, and the deployment health endpoint."
        )
    )
    parser.add_argument("--resource-report", type=Path, required=True)
    parser.add_argument(
        "--metrics-url",
        default=os.environ.get("INFINITYDB_METRICS_URL", DEFAULT_METRICS_URL),
    )
    parser.add_argument(
        "--health-url",
        default=None,
        help=(
            "health URL (default: INFINITYDB_HEALTH_URL or /health beside the metrics URL)"
        ),
    )
    parser.add_argument("--sample-seconds", type=float, default=DEFAULT_SAMPLE_SECONDS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--max-resource-age",
        type=float,
        default=DEFAULT_MAX_RESOURCE_AGE_SECONDS,
        help="maximum age of the resource report in seconds",
    )
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    parser.add_argument("--cpu-warning", type=float, default=85.0)
    parser.add_argument("--cpu-critical", type=float, default=95.0)
    parser.add_argument("--memory-warning", type=float, default=85.0)
    parser.add_argument("--memory-critical", type=float, default=95.0)
    parser.add_argument("--filesystem-free-warning", type=float, default=15.0)
    parser.add_argument("--filesystem-free-critical", type=float, default=5.0)
    parser.add_argument("--inode-free-warning", type=float, default=15.0)
    parser.add_argument("--inode-free-critical", type=float, default=5.0)
    parser.add_argument("--server-error-warning-percent", type=float, default=1.0)
    parser.add_argument("--server-error-critical-percent", type=float, default=5.0)
    parser.add_argument("--server-error-warning-count", type=int, default=5)
    parser.add_argument("--server-error-critical-count", type=int, default=10)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = _utc_now,
    metrics_fetcher: Callable[..., str] = fetch_metrics,
    health_fetcher: Callable[..., bool] = fetch_health,
) -> int:
    args = build_parser().parse_args(argv)
    sample_seconds = _positive("--sample-seconds", args.sample_seconds)
    timeout = _positive("--timeout", args.timeout)
    max_resource_age = _positive("--max-resource-age", args.max_resource_age)
    thresholds = AlertThresholds(
        cpu_warning_percent=_percentage("--cpu-warning", args.cpu_warning),
        cpu_critical_percent=_percentage("--cpu-critical", args.cpu_critical),
        memory_warning_percent=_percentage("--memory-warning", args.memory_warning),
        memory_critical_percent=_percentage("--memory-critical", args.memory_critical),
        filesystem_free_warning_percent=_percentage(
            "--filesystem-free-warning", args.filesystem_free_warning
        ),
        filesystem_free_critical_percent=_percentage(
            "--filesystem-free-critical", args.filesystem_free_critical
        ),
        inode_free_warning_percent=_percentage("--inode-free-warning", args.inode_free_warning),
        inode_free_critical_percent=_percentage(
            "--inode-free-critical", args.inode_free_critical
        ),
        server_error_warning_percent=_percentage(
            "--server-error-warning-percent", args.server_error_warning_percent
        ),
        server_error_critical_percent=_percentage(
            "--server-error-critical-percent", args.server_error_critical_percent
        ),
        server_error_warning_count=args.server_error_warning_count,
        server_error_critical_count=args.server_error_critical_count,
    )
    if thresholds.server_error_warning_count < 1 or thresholds.server_error_critical_count < 1:
        raise SystemExit("5xx count thresholds must be positive integers")
    _validate_thresholds(thresholds)

    try:
        resource_report = load_resource_report(args.resource_report)
    except AlertEvaluationError as exc:
        print(f"Alert evaluation failed: {exc}", file=sys.stderr)
        return 3

    health_url = args.health_url or os.environ.get("INFINITYDB_HEALTH_URL") or _health_url(
        args.metrics_url
    )
    health_samples = [health_fetcher(health_url, timeout=timeout)]
    before_metrics: MetricsReport | None = None
    after_metrics: MetricsReport | None = None
    metrics_error = False
    try:
        before_metrics = parse_prometheus(metrics_fetcher(args.metrics_url, timeout=timeout))
    except (OSError, UnicodeError, urllib.error.URLError, ValueError):
        metrics_error = True

    sleep(sample_seconds)
    health_samples.append(health_fetcher(health_url, timeout=timeout))
    if not metrics_error:
        try:
            after_metrics = parse_prometheus(metrics_fetcher(args.metrics_url, timeout=timeout))
        except (OSError, UnicodeError, urllib.error.URLError, ValueError):
            metrics_error = True

    try:
        report = build_report(
            resource_report=resource_report,
            thresholds=thresholds,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            health_samples=health_samples,
            now=now(),
            max_resource_age_seconds=max_resource_age,
            sample_seconds=sample_seconds,
            metrics_error=metrics_error,
        )
    except AlertEvaluationError as exc:
        print(f"Alert evaluation failed: {exc}", file=sys.stderr)
        return 3

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
        print(f"Deployment alert report: {args.output}")
    else:
        print(payload, end="")
    return int(report["exitCode"])


if __name__ == "__main__":
    raise SystemExit(main())
