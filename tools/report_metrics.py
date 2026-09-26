#!/usr/bin/env python3
"""Fetch InfinityDB aggregate metrics and print a compact operator report."""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass

DEFAULT_METRICS_URL = "http://127.0.0.1:9090/metrics"
_SAMPLE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?P<labels>\{.*\})?"
    r"\s+(?P<value>[-+0-9.eE]+)$"
)
_LABEL_RE = re.compile(r'(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)="(?P<value>(?:\\.|[^"\\])*)"')


@dataclass(frozen=True)
class MetricsReport:
    version: str
    snapshot_revision: str
    active_requests: int
    status_counts: dict[str, int]
    route_counts: dict[str, int]
    duration_sum_seconds: float
    duration_count: int
    duration_buckets: dict[float, int]
    response_size_sum_bytes: float
    response_size_count: int

    @property
    def total_requests(self) -> int:
        return sum(self.status_counts.values())


def _unescape_label(value: str) -> str:
    return value.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def _parse_labels(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    return {
        match.group("key"): _unescape_label(match.group("value"))
        for match in _LABEL_RE.finditer(raw)
    }


def parse_prometheus(text: str) -> MetricsReport:
    """Parse the bounded InfinityDB metrics surface into operator-level aggregates."""

    version = "unknown"
    snapshot_revision = "unknown"
    active_requests = 0
    status_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    duration_sum_seconds = 0.0
    duration_count = 0
    duration_buckets: defaultdict[float, int] = defaultdict(int)
    response_size_sum_bytes = 0.0
    response_size_count = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _SAMPLE_RE.match(line)
        if match is None:
            continue
        name = match.group("name")
        labels = _parse_labels(match.group("labels"))
        value = float(match.group("value"))

        if name == "infinitydb_build_info":
            version = labels.get("version", version)
            snapshot_revision = labels.get("snapshot_revision", snapshot_revision)
        elif name == "infinitydb_http_requests_active":
            active_requests = int(value)
        elif name == "infinitydb_http_requests_total":
            count = int(value)
            status_counts[labels.get("status_class", "unknown")] += count
            route_counts[labels.get("route", "/other")] += count
        elif name == "infinitydb_http_request_duration_seconds_sum":
            duration_sum_seconds += value
        elif name == "infinitydb_http_request_duration_seconds_count":
            duration_count += int(value)
        elif name == "infinitydb_http_request_duration_seconds_bucket":
            bound = labels.get("le")
            if bound and bound != "+Inf":
                duration_buckets[float(bound)] += int(value)
        elif name == "infinitydb_http_response_size_bytes_sum":
            response_size_sum_bytes += value
        elif name == "infinitydb_http_response_size_bytes_count":
            response_size_count += int(value)

    return MetricsReport(
        version=version,
        snapshot_revision=snapshot_revision,
        active_requests=active_requests,
        status_counts=dict(status_counts),
        route_counts=dict(route_counts),
        duration_sum_seconds=duration_sum_seconds,
        duration_count=duration_count,
        duration_buckets=dict(duration_buckets),
        response_size_sum_bytes=response_size_sum_bytes,
        response_size_count=response_size_count,
    )


def _percentile_bucket(report: MetricsReport, percentile: float) -> float | None:
    if report.duration_count <= 0:
        return None
    threshold = math.ceil(report.duration_count * percentile)
    for bound in sorted(report.duration_buckets):
        if report.duration_buckets[bound] >= threshold:
            return bound
    return None


def _format_duration(seconds: float) -> str:
    if seconds < 1.0:
        return f"{seconds * 1000:.1f} ms"
    return f"{seconds:.2f} s"


def _format_bytes(value: float) -> str:
    if value < 1024:
        return f"{value:.0f} B"
    if value < 1024**2:
        return f"{value / 1024:.1f} KiB"
    return f"{value / 1024**2:.1f} MiB"


def render_report(report: MetricsReport, *, source_url: str, top_routes: int) -> str:
    """Render a human-readable process-lifetime metrics summary."""

    average_duration = (
        report.duration_sum_seconds / report.duration_count if report.duration_count else 0.0
    )
    average_size = (
        report.response_size_sum_bytes / report.response_size_count
        if report.response_size_count
        else 0.0
    )
    p95 = _percentile_bucket(report, 0.95)
    status_order = ("1xx", "2xx", "3xx", "4xx", "5xx")
    status_summary = " | ".join(
        f"{status}: {report.status_counts.get(status, 0)}" for status in status_order
    )

    lines = [
        "InfinityDB metrics",
        f"Source: {source_url}",
        f"Version: {report.version}",
        f"Snapshot: {report.snapshot_revision}",
        f"Active requests: {report.active_requests}",
        f"Completed requests: {report.total_requests}",
        f"Status classes: {status_summary}",
    ]
    if report.duration_count:
        lines.append(f"Average latency: {_format_duration(average_duration)}")
        lines.append(
            "p95 latency bucket: "
            + (f"<= {_format_duration(p95)}" if p95 is not None else "> highest configured bucket")
        )
    else:
        lines.extend(("Average latency: —", "p95 latency bucket: —"))
    lines.append(
        f"Average response size: {_format_bytes(average_size)}"
        if report.response_size_count
        else "Average response size: —"
    )

    populated_routes = [
        (route, count) for route, count in report.route_counts.items() if count > 0
    ]
    populated_routes.sort(key=lambda item: (-item[1], item[0]))
    lines.append("Top routes:")
    if not populated_routes:
        lines.append("  —")
    else:
        for route, count in populated_routes[:top_routes]:
            lines.append(f"  {count:>8}  {route}")
    lines.append("Counters cover the current application process lifetime and reset on restart.")
    return "\n".join(lines)


def fetch_metrics(url: str, *, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "InfinityDB metrics reporter"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch InfinityDB's LAN metrics endpoint and print an aggregate report."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=os.environ.get("INFINITYDB_METRICS_URL", DEFAULT_METRICS_URL),
        help=(
            "metrics URL (default: INFINITYDB_METRICS_URL or "
            f"{DEFAULT_METRICS_URL})"
        ),
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds")
    parser.add_argument("--top", type=int, default=10, help="number of busiest routes to show")
    parser.add_argument("--raw", action="store_true", help="print the raw Prometheus text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than zero")
    if args.top <= 0:
        raise SystemExit("--top must be greater than zero")

    try:
        text = fetch_metrics(args.url, timeout=args.timeout)
    except (OSError, UnicodeError, urllib.error.URLError) as exc:
        print(f"Unable to fetch InfinityDB metrics from {args.url}: {exc}", file=sys.stderr)
        return 2

    if args.raw:
        print(text, end="" if text.endswith("\n") else "\n")
        return 0

    print(render_report(parse_prometheus(text), source_url=args.url, top_routes=args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
