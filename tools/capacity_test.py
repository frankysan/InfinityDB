#!/usr/bin/env python3
"""Run a representative HTTP capacity scenario against a deployed InfinityDB stack."""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

FORMAT = "InfinityDB HTTP capacity test"
FORMAT_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_WARMUP_PASSES = 2
DEFAULT_STEADY_SECONDS = 60.0
DEFAULT_STEADY_CONCURRENCY = 8
DEFAULT_BURST_SECONDS = 10.0
DEFAULT_BURST_CONCURRENCY = 32
USER_AGENT = "InfinityDB capacity test/1"


@dataclass(frozen=True)
class ScenarioCase:
    name: str
    path: str
    kind: str


@dataclass(frozen=True)
class RequestResult:
    case: ScenarioCase
    latency_seconds: float
    status: int | None
    response_bytes: int
    error: str | None = None

    @property
    def successful(self) -> bool:
        return self.status is not None and 200 <= self.status < 300 and self.error is None


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("cannot calculate a percentile of an empty sample")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def _latency_summary(results: Sequence[RequestResult]) -> dict[str, float] | None:
    successful = [result.latency_seconds * 1000 for result in results if result.successful]
    if not successful:
        return None
    return {
        "p50Ms": _percentile(successful, 0.50),
        "p95Ms": _percentile(successful, 0.95),
        "p99Ms": _percentile(successful, 0.99),
        "meanMs": statistics.fmean(successful),
        "minMs": min(successful),
        "maxMs": max(successful),
    }


def _status_class(status: int | None) -> str:
    if status is None:
        return "network"
    return f"{status // 100}xx"


def _result_summary(results: Sequence[RequestResult], elapsed_seconds: float) -> dict[str, Any]:
    total = len(results)
    successes = sum(result.successful for result in results)
    errors = total - successes
    response_bytes = sum(result.response_bytes for result in results)
    status_classes = Counter(_status_class(result.status) for result in results)
    error_types = Counter(result.error for result in results if result.error)
    return {
        "requests": total,
        "successes": successes,
        "errors": errors,
        "errorRate": errors / total if total else 0.0,
        "requestsPerSecond": total / elapsed_seconds if elapsed_seconds > 0 else 0.0,
        "responseBytes": response_bytes,
        "averageResponseBytes": response_bytes / total if total else 0.0,
        "latency": _latency_summary(results),
        "statusClasses": dict(sorted(status_classes.items())),
        "errorTypes": dict(sorted(error_types.items())),
    }


def summarize_phase(
    results: Sequence[RequestResult],
    *,
    name: str,
    concurrency: int,
    requested_seconds: float,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Summarize one steady/burst phase without retaining individual requests."""

    by_case: dict[str, list[RequestResult]] = {}
    for result in results:
        by_case.setdefault(result.case.name, []).append(result)
    cases = []
    for case_name in sorted(by_case):
        case_results = by_case[case_name]
        case = case_results[0].case
        cases.append(
            {
                "name": case.name,
                "path": _report_path(case.path),
                "kind": case.kind,
                **_result_summary(case_results, elapsed_seconds),
            }
        )
    return {
        "name": name,
        "concurrency": concurrency,
        "requestedSeconds": requested_seconds,
        "elapsedSeconds": elapsed_seconds,
        **_result_summary(results, elapsed_seconds),
        "cases": cases,
    }


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _report_path(path: str) -> str:
    parsed = urllib.parse.urlsplit(path)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    sanitized = [(key, "<synthetic>") if key == "q" else (key, value) for key, value in query]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(sanitized),
            parsed.fragment,
        )
    )


def _request_once(base_url: str, case: ScenarioCase, *, timeout: float) -> RequestResult:
    request = urllib.request.Request(
        _join_url(base_url, case.path),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.1"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = int(response.status)
        error = None if 200 <= status < 300 else f"http-{status}"
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = int(exc.code)
        error = f"http-{status}"
    except OSError as exc:
        body = b""
        status = None
        error = type(exc).__name__
    return RequestResult(
        case=case,
        latency_seconds=time.perf_counter() - started,
        status=status,
        response_bytes=len(body),
        error=error,
    )


def _fetch_json(base_url: str, path: str, *, timeout: float) -> Mapping[str, Any]:
    case = ScenarioCase("discovery", path, "api")
    request = urllib.request.Request(
        _join_url(base_url, path),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise ValueError(f"{path} returned HTTP {response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"{case.path} returned HTTP {exc.code}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read {case.path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{case.path} did not return a JSON object")
    return payload


def _first_item(payload: Mapping[str, Any], context: str) -> Mapping[str, Any]:
    items = payload.get("items")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise ValueError(f"{context} returned no discoverable items")
    return items[0]


def _identifier(item: Mapping[str, Any], context: str) -> str:
    for key in ("public_slug", "slug", "id"):
        value = item.get(key)
        if isinstance(value, (str, int)) and str(value):
            return urllib.parse.quote(str(value), safe="-")
    raise ValueError(f"{context} has no usable public identifier")


def discover_scenario(
    base_url: str,
    *,
    timeout: float,
    fetch_json: Callable[[str, str], Mapping[str, Any]] | None = None,
) -> tuple[dict[str, str], list[ScenarioCase]]:
    """Discover stable public identities and build the representative capacity scenario."""

    if fetch_json is None:
        fetch_json = partial(_fetch_json, timeout=timeout)

    version_payload = fetch_json(base_url, "/api/version")
    version = version_payload.get("version")
    snapshot_revision = version_payload.get("snapshot_revision")
    static_revision = version_payload.get("static_revision")
    if not isinstance(version, str) or not version:
        raise ValueError("/api/version did not identify an InfinityDB deployment")
    if not isinstance(snapshot_revision, str) or not snapshot_revision:
        raise ValueError("/api/version did not identify an InfinityDB deployment")
    if not isinstance(static_revision, str) or not static_revision:
        raise ValueError("/api/version did not identify an InfinityDB deployment")

    unit = _first_item(fetch_json(base_url, "/api/units?limit=1"), "/api/units")
    unit_identifier = _identifier(unit, "Unit")
    unit_name = unit.get("name")
    if not isinstance(unit_name, str) or not unit_name.strip():
        raise ValueError("Discovered Unit has no usable name for the search scenario")
    search_query = unit_name.strip().split()[0]
    encoded_query = urllib.parse.urlencode({"q": search_query})

    cases = [
        ScenarioCase("unit-list-page", "/units", "page"),
        ScenarioCase("unit-list-api", "/api/units?limit=50", "api"),
        ScenarioCase("search-page", f"/search?{encoded_query}", "page"),
        ScenarioCase("search-api", f"/api/search?{encoded_query}", "api"),
        ScenarioCase("unit-detail-page", f"/units/{unit_identifier}", "page"),
        ScenarioCase("unit-detail-api", f"/api/units/{unit_identifier}", "api"),
    ]

    for catalog in ("skills", "equipment", "weapons"):
        item = _first_item(fetch_json(base_url, f"/api/{catalog}"), f"/api/{catalog}")
        identifier = _identifier(item, catalog.title())
        singular = catalog.removesuffix("s")
        cases.extend(
            [
                ScenarioCase(f"{singular}-catalog-page", f"/{catalog}", "page"),
                ScenarioCase(f"{singular}-catalog-api", f"/api/{catalog}", "api"),
                ScenarioCase(f"{singular}-detail-page", f"/{catalog}/{identifier}", "page"),
                ScenarioCase(f"{singular}-detail-api", f"/api/{catalog}/{identifier}", "api"),
            ]
        )

    target = {
        "version": version,
        "snapshotRevision": snapshot_revision,
        "staticRevision": static_revision,
    }
    return target, cases


def _warm_scenario(
    base_url: str,
    cases: Sequence[ScenarioCase],
    *,
    passes: int,
    timeout: float,
    requester: Callable[[str, ScenarioCase], RequestResult] | None = None,
) -> list[RequestResult]:
    if requester is None:
        requester = partial(_request_once, timeout=timeout)
    results = []
    for _ in range(passes):
        for case in cases:
            results.append(requester(base_url, case))
    return results


def run_phase(
    base_url: str,
    cases: Sequence[ScenarioCase],
    *,
    concurrency: int,
    duration_seconds: float,
    timeout: float,
    requester: Callable[[str, ScenarioCase], RequestResult] | None = None,
    request_limit: int | None = None,
) -> tuple[list[RequestResult], float]:
    """Run one fixed-concurrency phase; request_limit exists for deterministic tests."""

    if requester is None:
        requester = partial(_request_once, timeout=timeout)
    started = time.perf_counter()
    deadline = started + duration_seconds

    if request_limit is not None:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            results = list(
                executor.map(
                    lambda index: requester(base_url, cases[index % len(cases)]),
                    range(request_limit),
                )
            )
        return results, max(time.perf_counter() - started, 1e-9)

    lock = threading.Lock()
    next_case = 0

    def worker() -> list[RequestResult]:
        nonlocal next_case
        local_results = []
        while time.perf_counter() < deadline:
            with lock:
                case = cases[next_case % len(cases)]
                next_case += 1
            local_results.append(requester(base_url, case))
        return local_results

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        results = [result for future in futures for result in future.result()]
    return results, max(time.perf_counter() - started, 1e-9)


def capacity_test(
    base_url: str,
    *,
    timeout: float,
    warmup_passes: int,
    steady_seconds: float,
    steady_concurrency: int,
    burst_seconds: float,
    burst_concurrency: int,
) -> dict[str, Any]:
    target, cases = discover_scenario(base_url, timeout=timeout)
    warmup_results = _warm_scenario(
        base_url,
        cases,
        passes=warmup_passes,
        timeout=timeout,
    )
    warmup_errors = [result for result in warmup_results if not result.successful]
    if warmup_errors:
        first = warmup_errors[0]
        raise ValueError(
            f"Warm-up failed for {first.case.name} ({first.case.path}): "
            f"{first.error or first.status}"
        )

    steady_results, steady_elapsed = run_phase(
        base_url,
        cases,
        concurrency=steady_concurrency,
        duration_seconds=steady_seconds,
        timeout=timeout,
    )
    burst_results, burst_elapsed = run_phase(
        base_url,
        cases,
        concurrency=burst_concurrency,
        duration_seconds=burst_seconds,
        timeout=timeout,
    )
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "startedAt": datetime.now(UTC).isoformat(),
        "client": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "target": {
            "baseUrl": base_url.rstrip("/"),
            **target,
        },
        "scenario": {
            "warmupPasses": warmup_passes,
            "cases": [
                {
                    "name": case.name,
                    "path": _report_path(case.path),
                    "kind": case.kind,
                }
                for case in cases
            ],
        },
        "phases": [
            summarize_phase(
                steady_results,
                name="steady",
                concurrency=steady_concurrency,
                requested_seconds=steady_seconds,
                elapsed_seconds=steady_elapsed,
            ),
            summarize_phase(
                burst_results,
                name="burst",
                concurrency=burst_concurrency,
                requested_seconds=burst_seconds,
                elapsed_seconds=burst_elapsed,
            ),
        ],
    }


def _base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("base URL must be an absolute http:// or https:// URL")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise argparse.ArgumentTypeError(
            "base URL must not contain credentials, query, or fragment"
        )
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", type=_base_url, help="deployed InfinityDB base URL")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--warmup-passes", type=int, default=DEFAULT_WARMUP_PASSES)
    parser.add_argument("--steady-seconds", type=float, default=DEFAULT_STEADY_SECONDS)
    parser.add_argument("--steady-concurrency", type=int, default=DEFAULT_STEADY_CONCURRENCY)
    parser.add_argument("--burst-seconds", type=float, default=DEFAULT_BURST_SECONDS)
    parser.add_argument("--burst-concurrency", type=int, default=DEFAULT_BURST_CONCURRENCY)
    parser.add_argument("--output", type=Path, help="write the complete JSON report to this path")
    parser.add_argument("--json", action="store_true", help="print the complete JSON report")
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than zero")
    if args.warmup_passes < 1:
        raise SystemExit("--warmup-passes must be positive")
    for name in ("steady_seconds", "burst_seconds"):
        if getattr(args, name) <= 0:
            raise SystemExit(f"--{name.replace('_', '-')} must be greater than zero")
    for name in ("steady_concurrency", "burst_concurrency"):
        if getattr(args, name) < 1:
            raise SystemExit(f"--{name.replace('_', '-')} must be positive")


def _render_summary(report: Mapping[str, Any]) -> str:
    target = report["target"]
    lines = [
        "InfinityDB capacity test",
        f"Target: {target['baseUrl']}",
        f"Version: {target['version']}",
        f"Snapshot: {target['snapshotRevision']}",
    ]
    for phase in report["phases"]:
        latency = phase["latency"]
        latency_text = "no successful samples"
        if latency is not None:
            latency_text = (
                f"p50 {latency['p50Ms']:.1f} ms | p95 {latency['p95Ms']:.1f} ms | "
                f"p99 {latency['p99Ms']:.1f} ms"
            )
        lines.append(
            f"{phase['name'].title()}: concurrency {phase['concurrency']} | "
            f"{phase['requestsPerSecond']:.1f} req/s | "
            f"{phase['errorRate'] * 100:.2f}% errors | {latency_text}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _validate_args(args)
    try:
        report = capacity_test(
            args.base_url,
            timeout=args.timeout,
            warmup_passes=args.warmup_passes,
            steady_seconds=args.steady_seconds,
            steady_concurrency=args.steady_concurrency,
            burst_seconds=args.burst_seconds,
            burst_concurrency=args.burst_concurrency,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    if args.json:
        print(rendered, end="")
    else:
        print(_render_summary(report))
        if args.output is not None:
            print(f"Report: {args.output}")
    return 1 if any(phase["errors"] for phase in report["phases"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
