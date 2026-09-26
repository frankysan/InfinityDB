"""Privacy-preserving aggregate HTTP request metrics for the production WSGI app."""

from __future__ import annotations

import multiprocessing
import os
from collections.abc import Iterable
from dataclasses import dataclass

STATUS_CLASSES = ("1xx", "2xx", "3xx", "4xx", "5xx")
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
RESPONSE_SIZE_BUCKETS = (1024.0, 10_240.0, 102_400.0, 1_048_576.0)
MAX_WORKER_SLOTS = 64

# This vocabulary is intentionally fixed and bounded. Dynamic identifiers, query strings,
# and raw static paths must never become metric labels.
ROUTES = (
    "/",
    "/about",
    "/units",
    "/units/:id",
    "/skills",
    "/skills/:id",
    "/equipment",
    "/equipment/:id",
    "/weapons",
    "/weapons/:id",
    "/traits",
    "/traits/:id",
    "/states",
    "/states/:id",
    "/skill-extras",
    "/api/version",
    "/api/armies",
    "/api/units",
    "/api/units/:id",
    "/api/visible-unit-ids",
    "/api/skills",
    "/api/skills/:id",
    "/api/equipment",
    "/api/equipment/:id",
    "/api/weapons",
    "/api/weapons/:id",
    "/api/traits",
    "/api/traits/:id",
    "/api/states",
    "/api/states/:id",
    "/api/skill-extras",
    "/static/:asset",
    "/static/:symbol",
    "/other",
)

_ROUTE_INDEX = {route: index for index, route in enumerate(ROUTES)}
_STATUS_INDEX = {status: index for index, status in enumerate(STATUS_CLASSES)}


@dataclass(frozen=True)
class RequestMetricSnapshot:
    """Immutable copy of the shared counters used while rendering exposition text."""

    active_requests: int
    request_counts: tuple[int, ...]
    latency_bins: tuple[int, ...]
    latency_sums: tuple[float, ...]
    response_size_bins: tuple[int, ...]
    response_size_sums: tuple[float, ...]


def _status_class(status_code: int) -> str:
    if 100 <= status_code < 200:
        return "1xx"
    if 200 <= status_code < 300:
        return "2xx"
    if 300 <= status_code < 400:
        return "3xx"
    if 400 <= status_code < 500:
        return "4xx"
    return "5xx"


def _bucket_index(value: float, limits: tuple[float, ...]) -> int:
    for index, limit in enumerate(limits):
        if value <= limit:
            return index
    return len(limits)


def _label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_bound(value: float) -> str:
    return format(value, ".12g")


class RequestMetrics:
    """Fixed-cardinality counters shared by preloaded Gunicorn worker processes."""

    def __init__(self) -> None:
        # Gunicorn starts workers with fork on the Linux deployment target. The Docker command
        # uses --preload so these synchronization primitives are created once in the master and
        # inherited by every worker. Direct/local WSGI use remains valid without forking.
        self._lock = multiprocessing.RLock()
        self._worker_pids = multiprocessing.Array("q", MAX_WORKER_SLOTS, lock=False)
        self._worker_active = multiprocessing.Array("q", MAX_WORKER_SLOTS, lock=False)
        self._worker_slot: int | None = None
        self._request_counts = multiprocessing.Array(
            "q", len(ROUTES) * len(STATUS_CLASSES), lock=False
        )
        self._latency_bins = multiprocessing.Array(
            "q", len(ROUTES) * (len(LATENCY_BUCKETS) + 1), lock=False
        )
        self._latency_sums = multiprocessing.Array("d", len(ROUTES), lock=False)
        self._response_size_bins = multiprocessing.Array(
            "q", len(ROUTES) * (len(RESPONSE_SIZE_BUCKETS) + 1), lock=False
        )
        self._response_size_sums = multiprocessing.Array("d", len(ROUTES), lock=False)

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        if pid == os.getpid():
            return True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _worker_slot_for_current_process(self) -> int:
        pid = os.getpid()
        cached = self._worker_slot
        if cached is not None and self._worker_pids[cached] == pid:
            return cached

        available: int | None = None
        for index, registered_pid in enumerate(self._worker_pids):
            if registered_pid == pid:
                self._worker_slot = index
                return index
            if registered_pid <= 0:
                available = index if available is None else available
                continue
            if not self._pid_is_alive(registered_pid):
                self._worker_pids[index] = 0
                self._worker_active[index] = 0
                available = index if available is None else available

        if available is None:
            raise RuntimeError("No free request-metric worker slot")
        self._worker_pids[available] = pid
        self._worker_active[available] = 0
        self._worker_slot = available
        return available

    def start_request(self) -> int:
        """Increment this worker's active-request gauge and return its bounded slot."""

        with self._lock:
            worker_slot = self._worker_slot_for_current_process()
            self._worker_active[worker_slot] += 1
            return worker_slot

    def finish_request(
        self,
        worker_slot: int,
        route: str,
        status_code: int,
        duration_seconds: float,
        response_size_bytes: int,
    ) -> None:
        """Record one completed request using only bounded aggregate dimensions."""

        route_index = _ROUTE_INDEX.get(route, _ROUTE_INDEX["/other"])
        status_index = _STATUS_INDEX[_status_class(status_code)]
        latency_index = _bucket_index(max(duration_seconds, 0.0), LATENCY_BUCKETS)
        size_value = float(max(response_size_bytes, 0))
        size_index = _bucket_index(size_value, RESPONSE_SIZE_BUCKETS)
        latency_width = len(LATENCY_BUCKETS) + 1
        size_width = len(RESPONSE_SIZE_BUCKETS) + 1

        with self._lock:
            self._worker_active[worker_slot] = max(self._worker_active[worker_slot] - 1, 0)
            self._request_counts[route_index * len(STATUS_CLASSES) + status_index] += 1
            self._latency_bins[route_index * latency_width + latency_index] += 1
            self._latency_sums[route_index] += max(duration_seconds, 0.0)
            self._response_size_bins[route_index * size_width + size_index] += 1
            self._response_size_sums[route_index] += size_value

    def snapshot(self) -> RequestMetricSnapshot:
        """Copy all shared counters atomically for stable exposition output."""

        with self._lock:
            active_requests = 0
            for index, pid in enumerate(self._worker_pids):
                if pid <= 0:
                    continue
                if self._pid_is_alive(pid):
                    active_requests += max(self._worker_active[index], 0)
                else:
                    self._worker_pids[index] = 0
                    self._worker_active[index] = 0
            return RequestMetricSnapshot(
                active_requests=active_requests,
                request_counts=tuple(self._request_counts),
                latency_bins=tuple(self._latency_bins),
                latency_sums=tuple(self._latency_sums),
                response_size_bins=tuple(self._response_size_bins),
                response_size_sums=tuple(self._response_size_sums),
            )

    def render_prometheus(self, *, version: str, snapshot_revision: str) -> bytes:
        """Render the bounded aggregate registry in Prometheus text exposition format."""

        snapshot = self.snapshot()
        lines = [
            "# HELP infinitydb_build_info InfinityDB build and database snapshot identity.",
            "# TYPE infinitydb_build_info gauge",
            (
                'infinitydb_build_info{version="'
                + _label(version)
                + '",snapshot_revision="'
                + _label(snapshot_revision)
                + '"} 1'
            ),
            "# HELP infinitydb_http_requests_active Requests currently being handled.",
            "# TYPE infinitydb_http_requests_active gauge",
            f"infinitydb_http_requests_active {snapshot.active_requests}",
            (
                "# HELP infinitydb_http_requests_total Completed requests by normalized "
                "route and status class."
            ),
            "# TYPE infinitydb_http_requests_total counter",
        ]

        for route_index, route in enumerate(ROUTES):
            for status_index, status_class in enumerate(STATUS_CLASSES):
                count = snapshot.request_counts[
                    route_index * len(STATUS_CLASSES) + status_index
                ]
                lines.append(
                    f'infinitydb_http_requests_total{{route="{_label(route)}",'
                    f'status_class="{status_class}"}} {count}'
                )

        lines.extend(
            (
                (
                    "# HELP infinitydb_http_request_duration_seconds Request latency by "
                    "normalized route."
                ),
                "# TYPE infinitydb_http_request_duration_seconds histogram",
            )
        )
        self._append_histograms(
            lines,
            metric="infinitydb_http_request_duration_seconds",
            bins=snapshot.latency_bins,
            sums=snapshot.latency_sums,
            limits=LATENCY_BUCKETS,
        )

        lines.extend(
            (
                (
                    "# HELP infinitydb_http_response_size_bytes Response body size by "
                    "normalized route."
                ),
                "# TYPE infinitydb_http_response_size_bytes histogram",
            )
        )
        self._append_histograms(
            lines,
            metric="infinitydb_http_response_size_bytes",
            bins=snapshot.response_size_bins,
            sums=snapshot.response_size_sums,
            limits=RESPONSE_SIZE_BUCKETS,
        )
        return ("\n".join(lines) + "\n").encode("utf-8")

    @staticmethod
    def _append_histograms(
        lines: list[str],
        *,
        metric: str,
        bins: Iterable[int],
        sums: tuple[float, ...],
        limits: tuple[float, ...],
    ) -> None:
        bins_tuple = tuple(bins)
        width = len(limits) + 1
        for route_index, route in enumerate(ROUTES):
            cumulative = 0
            route_label = _label(route)
            for bucket_index, limit in enumerate(limits):
                cumulative += bins_tuple[route_index * width + bucket_index]
                lines.append(
                    f'{metric}_bucket{{route="{route_label}",le="{_format_bound(limit)}"}} '
                    f"{cumulative}"
                )
            cumulative += bins_tuple[route_index * width + len(limits)]
            lines.append(
                f'{metric}_bucket{{route="{route_label}",le="+Inf"}} {cumulative}'
            )
            lines.append(f'{metric}_sum{{route="{route_label}"}} {sums[route_index]:.12g}')
            lines.append(f'{metric}_count{{route="{route_label}"}} {cumulative}')
