from __future__ import annotations

import multiprocessing
from collections.abc import Callable
from typing import cast

import pytest

from infinity_db.web.metrics import RequestMetrics


def _record_from_worker(metrics: RequestMetrics) -> None:
    worker_slot = metrics.start_request()
    metrics.finish_request(worker_slot, "/api/units/:id", 200, 0.02, 2048)


def _leave_active_request_in_worker(metrics: RequestMetrics) -> None:
    metrics.start_request()


def test_request_metrics_record_bounded_histograms() -> None:
    metrics = RequestMetrics()
    worker_slot = metrics.start_request()
    metrics.finish_request(worker_slot, "/api/units/:id", 200, 0.02, 2048)

    body = metrics.render_prometheus(version="0.7.2", snapshot_revision="abc123")

    assert b"infinitydb_http_requests_active 0" in body
    assert (
        b'infinitydb_http_requests_total{route="/api/units/:id",status_class="2xx"} 1'
        in body
    )
    assert (
        b'infinitydb_http_request_duration_seconds_bucket{route="/api/units/:id",'
        b'le="0.025"} 1'
        in body
    )
    assert (
        b'infinitydb_http_response_size_bytes_bucket{route="/api/units/:id",le="10240"} 1'
        in body
    )


def _fork_process(
    target: Callable[[RequestMetrics], None], metrics: RequestMetrics
) -> multiprocessing.Process:
    context = multiprocessing.get_context("fork")
    process_factory = cast(
        Callable[..., multiprocessing.Process], context.Process
    )
    return process_factory(target=target, args=(metrics,))


def test_request_metrics_are_shared_across_preloaded_fork_workers() -> None:
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("Gunicorn production sharing uses the Linux fork start method")

    metrics = RequestMetrics()
    process = _fork_process(_record_from_worker, metrics)
    process.start()
    process.join(timeout=10)

    assert process.exitcode == 0
    body = metrics.render_prometheus(version="0.7.2", snapshot_revision="abc123")
    assert (
        b'infinitydb_http_requests_total{route="/api/units/:id",status_class="2xx"} 1'
        in body
    )


def test_dead_worker_does_not_leave_active_request_gauge_stale() -> None:
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("Gunicorn production sharing uses the Linux fork start method")

    metrics = RequestMetrics()
    process = _fork_process(_leave_active_request_in_worker, metrics)
    process.start()
    process.join(timeout=10)

    assert process.exitcode == 0
    assert b"infinitydb_http_requests_active 0" in metrics.render_prometheus(
        version="0.7.2", snapshot_revision="abc123"
    )
