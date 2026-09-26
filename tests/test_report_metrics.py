from __future__ import annotations

import pytest

from tools.report_metrics import parse_prometheus, render_report

SAMPLE = """\
# HELP infinitydb_build_info build info
infinitydb_build_info{version="0.8.0",snapshot_revision="snapshot-1"} 1
infinitydb_http_requests_active 2
infinitydb_http_requests_total{route="/units/:id",status_class="2xx"} 8
infinitydb_http_requests_total{route="/units/:id",status_class="4xx"} 2
infinitydb_http_requests_total{route="/api/units",status_class="2xx"} 5
infinitydb_http_request_duration_seconds_bucket{route="/units/:id",le="0.05"} 5
infinitydb_http_request_duration_seconds_bucket{route="/units/:id",le="0.1"} 9
infinitydb_http_request_duration_seconds_bucket{route="/units/:id",le="0.25"} 10
infinitydb_http_request_duration_seconds_bucket{route="/units/:id",le="+Inf"} 10
infinitydb_http_request_duration_seconds_sum{route="/units/:id"} 0.7
infinitydb_http_request_duration_seconds_count{route="/units/:id"} 10
infinitydb_http_request_duration_seconds_bucket{route="/api/units",le="0.05"} 4
infinitydb_http_request_duration_seconds_bucket{route="/api/units",le="0.1"} 5
infinitydb_http_request_duration_seconds_bucket{route="/api/units",le="0.25"} 5
infinitydb_http_request_duration_seconds_bucket{route="/api/units",le="+Inf"} 5
infinitydb_http_request_duration_seconds_sum{route="/api/units"} 0.2
infinitydb_http_request_duration_seconds_count{route="/api/units"} 5
infinitydb_http_response_size_bytes_sum{route="/units/:id"} 20480
infinitydb_http_response_size_bytes_count{route="/units/:id"} 10
infinitydb_http_response_size_bytes_sum{route="/api/units"} 10240
infinitydb_http_response_size_bytes_count{route="/api/units"} 5
"""


def test_parse_prometheus_aggregates_bounded_metrics() -> None:
    report = parse_prometheus(SAMPLE)

    assert report.version == "0.8.0"
    assert report.snapshot_revision == "snapshot-1"
    assert report.active_requests == 2
    assert report.total_requests == 15
    assert report.status_counts == {"2xx": 13, "4xx": 2}
    assert report.route_counts == {"/units/:id": 10, "/api/units": 5}
    assert report.duration_count == 15
    assert report.duration_sum_seconds == pytest.approx(0.9)
    assert report.duration_buckets[0.1] == 14
    assert report.response_size_count == 15
    assert report.response_size_sum_bytes == 30720


def test_render_report_is_compact_and_uses_normalized_routes() -> None:
    body = render_report(
        parse_prometheus(SAMPLE),
        source_url="http://192.0.2.10:9090/metrics",
        top_routes=1,
    )

    assert "Version: 0.8.0" in body
    assert "Completed requests: 15" in body
    assert "2xx: 13" in body
    assert "4xx: 2" in body
    assert "Average latency: 60.0 ms" in body
    assert "p95 latency bucket: <= 250.0 ms" in body
    assert "Average response size: 2.0 KiB" in body
    assert "        10  /units/:id" in body
    assert "/api/units" not in body
    assert "reset on restart" in body
