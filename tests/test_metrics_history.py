from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from infinity_db.web.metrics import ROUTES
from tools import metrics_history
from tools.metrics_history import (
    SAFE_ROUTES,
    collect_snapshot,
    history_status,
    open_history_database,
    parse_history_snapshot,
)


def _timestamp(year: int, month: int, day: int, hour: int = 12) -> float:
    return datetime(year, month, day, hour, tzinfo=UTC).timestamp()


def _metrics_text(
    *,
    version: str = "0.10.0",
    snapshot_revision: str = "snapshot-a",
    started_at: float,
    requests: int,
    duration_sum: float | None = None,
    response_sum: int | None = None,
    route: str = "/units",
) -> str:
    duration_sum = float(requests) / 10 if duration_sum is None else duration_sum
    response_sum = requests * 2048 if response_sum is None else response_sum
    latest = started_at + 30 if requests else 0
    return "\n".join(
        (
            (
                "infinitydb_build_info{"
                f'version="{version}",snapshot_revision="{snapshot_revision}"'
                "} 1"
            ),
            f"infinitydb_metrics_started_timestamp_seconds {started_at:.6f}",
            f"infinitydb_metrics_last_request_timestamp_seconds {latest:.6f}",
            (
                "infinitydb_http_requests_total{"
                f'route="{route}",status_class="2xx"'
                f"}} {requests}"
            ),
            (
                "infinitydb_http_request_duration_seconds_bucket{"
                f'route="{route}",le="0.1"'
                f"}} {requests}"
            ),
            f'infinitydb_http_request_duration_seconds_sum{{route="{route}"}} {duration_sum}',
            f'infinitydb_http_request_duration_seconds_count{{route="{route}"}} {requests}',
            (
                "infinitydb_http_response_size_bytes_bucket{"
                f'route="{route}",le="10240"'
                f"}} {requests}"
            ),
            f'infinitydb_http_response_size_bytes_sum{{route="{route}"}} {response_sum}',
            f'infinitydb_http_response_size_bytes_count{{route="{route}"}} {requests}',
            "",
        )
    )


def _weekly_value(
    path: Path,
    *,
    metric_name: str,
    version: str = "0.10.0",
    week_start: str = "2026-10-05",
) -> float:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            """
            SELECT value
            FROM weekly_metrics
            WHERE week_start = ? AND version = ? AND metric_name = ?
            """,
            (week_start, version, metric_name),
        ).fetchone()
    assert row is not None
    return float(row[0])


def test_history_route_allowlist_matches_runtime_metrics_vocabulary() -> None:
    assert SAFE_ROUTES == frozenset(ROUTES)


def test_history_database_rejects_unknown_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "history.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO metadata(key, value) VALUES ('format_version', '99')"
        )

    with pytest.raises(ValueError, match="Unsupported metrics-history format version"):
        open_history_database(path)


def test_parse_history_snapshot_rejects_unreviewed_route_labels() -> None:
    text = _metrics_text(
        started_at=_timestamp(2026, 10, 6),
        requests=1,
        route="/units/private-user-value",
    )

    with pytest.raises(ValueError, match="unreviewed metrics route"):
        parse_history_snapshot(text)


def test_collect_accumulates_first_generation_from_zero_then_only_deltas(tmp_path: Path) -> None:
    path = tmp_path / "history.db"
    collected_at = _timestamp(2026, 10, 6)
    started_at = collected_at - 60

    first = collect_snapshot(
        path,
        parse_history_snapshot(_metrics_text(started_at=started_at, requests=10)),
        collected_at=collected_at,
    )
    second = collect_snapshot(
        path,
        parse_history_snapshot(_metrics_text(started_at=started_at, requests=14)),
        collected_at=collected_at + 300,
    )

    assert first.outcome == "collected"
    assert first.generation_changed is True
    assert second.generation_changed is False
    assert _weekly_value(path, metric_name="infinitydb_http_requests_total") == 14
    assert _weekly_value(path, metric_name="infinitydb_http_request_duration_seconds_sum") == 1.4
    with sqlite3.connect(path) as connection:
        period = connection.execute(
            """
            SELECT generation_count, collection_count
            FROM weekly_periods
            WHERE week_start = '2026-10-05' AND version = '0.10.0'
            """
        ).fetchone()
    assert period == (1, 2)


def test_new_generation_and_version_do_not_subtract_previous_counters(tmp_path: Path) -> None:
    path = tmp_path / "history.db"
    first_collected = _timestamp(2026, 10, 6)
    first_started = first_collected - 60
    second_started = first_collected + 240

    collect_snapshot(
        path,
        parse_history_snapshot(
            _metrics_text(version="0.9.1", started_at=first_started, requests=20)
        ),
        collected_at=first_collected,
    )
    result = collect_snapshot(
        path,
        parse_history_snapshot(
            _metrics_text(version="0.10.0", started_at=second_started, requests=3)
        ),
        collected_at=first_collected + 300,
    )

    assert result.generation_changed is True
    assert _weekly_value(
        path,
        metric_name="infinitydb_http_requests_total",
        version="0.9.1",
    ) == 20
    assert _weekly_value(
        path,
        metric_name="infinitydb_http_requests_total",
        version="0.10.0",
    ) == 3


def test_counter_decrease_within_generation_resets_state_without_inflation(tmp_path: Path) -> None:
    path = tmp_path / "history.db"
    collected_at = _timestamp(2026, 10, 6)
    started_at = collected_at - 60

    collect_snapshot(
        path,
        parse_history_snapshot(_metrics_text(started_at=started_at, requests=10)),
        collected_at=collected_at,
    )
    reset = collect_snapshot(
        path,
        parse_history_snapshot(_metrics_text(started_at=started_at, requests=4)),
        collected_at=collected_at + 300,
    )
    recovered = collect_snapshot(
        path,
        parse_history_snapshot(_metrics_text(started_at=started_at, requests=6)),
        collected_at=collected_at + 600,
    )

    assert reset.outcome == "counter-reset"
    assert reset.series_updated == 0
    assert recovered.outcome == "collected"
    assert _weekly_value(path, metric_name="infinitydb_http_requests_total") == 12


def test_age_retention_keeps_current_week_plus_requested_completed_weeks(tmp_path: Path) -> None:
    path = tmp_path / "history.db"
    current = _timestamp(2026, 10, 7)
    weeks = (
        _timestamp(2026, 9, 16),
        _timestamp(2026, 9, 23),
        _timestamp(2026, 9, 30),
        current,
    )
    for index, collected_at in enumerate(weeks):
        collect_snapshot(
            path,
            parse_history_snapshot(
                _metrics_text(
                    snapshot_revision=f"snapshot-{index}",
                    started_at=collected_at - 60,
                    requests=1,
                )
            ),
            collected_at=collected_at,
            retention_weeks=2,
        )

    with sqlite3.connect(path) as connection:
        retained = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT week_start FROM weekly_periods ORDER BY week_start"
            )
        ]
    assert retained == ["2026-09-21", "2026-09-28", "2026-10-05"]


def test_size_pruning_removes_oldest_completed_weeks_before_current_week(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "history.db"
    connection = open_history_database(path)
    try:
        for week_start in ("2026-09-21", "2026-09-28", "2026-10-05"):
            connection.execute(
                """
                INSERT INTO weekly_periods VALUES (?, '0.10.0', 'snapshot', 1, 2, 1, 1)
                """,
                (week_start,),
            )
        connection.commit()
        sizes = iter((100, 100, 50))
        monkeypatch.setattr(metrics_history, "_database_size", lambda _path: next(sizes))
        monkeypatch.setattr(metrics_history, "_vacuum", lambda conn: conn.commit())

        pruned = metrics_history._prune_retention(
            connection,
            path=path,
            now=_timestamp(2026, 10, 7),
            retention_weeks=52,
            max_bytes=64,
        )

        retained = [
            row[0]
            for row in connection.execute(
                "SELECT week_start FROM weekly_periods ORDER BY week_start"
            )
        ]
    finally:
        connection.close()

    assert pruned == ("2026-09-21", "2026-09-28")
    assert retained == ["2026-10-05"]


def test_history_status_reports_retained_span_weeks_and_database_size(tmp_path: Path) -> None:
    path = tmp_path / "history.db"
    collected_at = _timestamp(2026, 10, 6)
    collect_snapshot(
        path,
        parse_history_snapshot(_metrics_text(started_at=collected_at - 60, requests=2)),
        collected_at=collected_at,
    )

    connection = open_history_database(path)
    try:
        status = history_status(connection, path=path, max_bytes=64 * 1024 * 1024)
    finally:
        connection.close()

    assert status.earliest_retained_at == collected_at
    assert status.latest_retained_at == collected_at
    assert status.retained_week_count == 1
    assert status.database_bytes > 0
    assert status.over_size_limit is False


def test_cli_status_json_does_not_retain_metrics_url(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "history.db"

    assert metrics_history.main(["--database", str(path), "status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["retainedWeekCount"] == 0
    assert "url" not in json.dumps(payload).lower()
