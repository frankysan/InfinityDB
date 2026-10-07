#!/usr/bin/env python3
"""Collect bounded InfinityDB metrics history into a local SQLite store."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

FORMAT = "InfinityDB metrics history"
FORMAT_VERSION = 1
DEFAULT_METRICS_URL = "http://app:8000/internal/metrics"
DEFAULT_DATABASE = Path("reports/metrics-history.db")
DEFAULT_INTERVAL_SECONDS = 300.0
DEFAULT_RETENTION_WEEKS = 52
DEFAULT_MAX_BYTES = 64 * 1024 * 1024

_SAMPLE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?P<labels>\{.*\})?"
    r"\s+(?P<value>[-+0-9.eE]+)$"
)
_LABEL_RE = re.compile(r'(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)="(?P<value>(?:\\.|[^"\\])*)"')

# Fail closed if the application's bounded route vocabulary changes. This intentionally duplicates
# the runtime metrics vocabulary so the history collector cannot silently begin persisting a raw or
# otherwise unreviewed route label.
SAFE_ROUTES = frozenset(
    {
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
        "/search",
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
        "/api/search",
        "/api/scenarios",
        "/api/scenarios/:id",
        "/static/:asset",
        "/static/:symbol",
        "/other",
    }
)
SAFE_STATUS_CLASSES = frozenset({"1xx", "2xx", "3xx", "4xx", "5xx"})
SAFE_LATENCY_BOUNDS = frozenset(
    {"0.005", "0.01", "0.025", "0.05", "0.1", "0.25", "0.5", "1", "2.5", "5", "+Inf"}
)
SAFE_RESPONSE_SIZE_BOUNDS = frozenset({"1024", "10240", "102400", "1048576", "+Inf"})

_TRACKED_LABELS: dict[str, frozenset[str]] = {
    "infinitydb_http_requests_total": frozenset({"route", "status_class"}),
    "infinitydb_http_request_duration_seconds_bucket": frozenset({"route", "le"}),
    "infinitydb_http_request_duration_seconds_sum": frozenset({"route"}),
    "infinitydb_http_request_duration_seconds_count": frozenset({"route"}),
    "infinitydb_http_response_size_bytes_bucket": frozenset({"route", "le"}),
    "infinitydb_http_response_size_bytes_sum": frozenset({"route"}),
    "infinitydb_http_response_size_bytes_count": frozenset({"route"}),
}


@dataclass(frozen=True, order=True)
class SeriesKey:
    """One fixed-cardinality monotonic Prometheus series retained by history."""

    name: str
    labels: tuple[tuple[str, str], ...]

    @property
    def labels_json(self) -> str:
        return json.dumps(dict(self.labels), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ScrapeSnapshot:
    """Validated bounded snapshot of one application metrics generation."""

    version: str
    snapshot_revision: str
    generation_started_at: float
    last_request_at: float | None
    counters: Mapping[SeriesKey, float]

    @property
    def generation_key(self) -> tuple[str, str, str]:
        return (
            self.version,
            self.snapshot_revision,
            f"{self.generation_started_at:.6f}",
        )


@dataclass(frozen=True)
class HistoryStatus:
    """Bounded retention/storage summary suitable for operator output."""

    earliest_retained_at: float | None
    latest_retained_at: float | None
    retained_week_count: int
    database_bytes: int
    max_database_bytes: int
    over_size_limit: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "earliestRetainedAt": self.earliest_retained_at,
            "latestRetainedAt": self.latest_retained_at,
            "retainedWeekCount": self.retained_week_count,
            "databaseBytes": self.database_bytes,
            "maxDatabaseBytes": self.max_database_bytes,
            "overSizeLimit": self.over_size_limit,
        }


@dataclass(frozen=True)
class CollectionResult:
    """Result of one successful or safely recovered collection attempt."""

    outcome: str
    generation_changed: bool
    series_updated: int
    pruned_weeks: tuple[str, ...]
    status: HistoryStatus

    def as_dict(self) -> dict[str, object]:
        return {
            "format": FORMAT,
            "formatVersion": FORMAT_VERSION,
            "outcome": self.outcome,
            "generationChanged": self.generation_changed,
            "seriesUpdated": self.series_updated,
            "prunedWeeks": list(self.pruned_weeks),
            "retention": self.status.as_dict(),
        }


@dataclass(frozen=True)
class RetainedPeriod:
    """One retained ISO-week/version/snapshot aggregate identity."""

    week_start: str
    version: str
    snapshot_revision: str
    first_observed_at: float
    last_observed_at: float
    generation_count: int
    collection_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "weekStart": self.week_start,
            "version": self.version,
            "snapshotRevision": self.snapshot_revision,
            "firstObservedAt": self.first_observed_at,
            "lastObservedAt": self.last_observed_at,
            "generationCount": self.generation_count,
            "collectionCount": self.collection_count,
        }


@dataclass(frozen=True)
class RouteSummary:
    """Aggregate request metrics for one normalized route."""

    route: str
    requests: int
    errors: int
    average_latency_seconds: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "route": self.route,
            "requests": self.requests,
            "errors": self.errors,
            "averageLatencySeconds": self.average_latency_seconds,
        }


@dataclass(frozen=True)
class HistoricalReport:
    """Operator-facing aggregate report for one retained-history selection."""

    periods: tuple[RetainedPeriod, ...]
    requests: int
    status_counts: Mapping[str, int]
    error_rate: float
    server_error_rate: float
    average_latency_seconds: float | None
    latency_percentiles: Mapping[str, float | None]
    latency_histogram: Mapping[str, int]
    average_response_size_bytes: float | None
    response_size_percentiles: Mapping[str, float | None]
    response_size_histogram: Mapping[str, int]
    routes: tuple[RouteSummary, ...]

    @property
    def first_observed_at(self) -> float:
        return min(period.first_observed_at for period in self.periods)

    @property
    def last_observed_at(self) -> float:
        return max(period.last_observed_at for period in self.periods)

    def as_dict(self) -> dict[str, object]:
        return {
            "format": FORMAT,
            "formatVersion": FORMAT_VERSION,
            "periods": [period.as_dict() for period in self.periods],
            "firstObservedAt": self.first_observed_at,
            "lastObservedAt": self.last_observed_at,
            "requests": self.requests,
            "statusCounts": dict(self.status_counts),
            "errorRate": self.error_rate,
            "serverErrorRate": self.server_error_rate,
            "averageLatencySeconds": self.average_latency_seconds,
            "latencyPercentilesSeconds": dict(self.latency_percentiles),
            "latencyHistogram": dict(self.latency_histogram),
            "averageResponseSizeBytes": self.average_response_size_bytes,
            "responseSizePercentilesBytes": dict(self.response_size_percentiles),
            "responseSizeHistogram": dict(self.response_size_histogram),
            "routes": [route.as_dict() for route in self.routes],
        }


def _unescape_label(value: str) -> str:
    return value.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def _parse_labels(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    return {
        match.group("key"): _unescape_label(match.group("value"))
        for match in _LABEL_RE.finditer(raw)
    }


def _validate_series_labels(name: str, labels: Mapping[str, str]) -> None:
    expected = _TRACKED_LABELS[name]
    if frozenset(labels) != expected:
        raise ValueError(
            f"Unexpected label set for {name}: {sorted(labels)}; expected {sorted(expected)}"
        )
    route = labels["route"]
    if route not in SAFE_ROUTES:
        raise ValueError(f"Refusing unreviewed metrics route label: {route!r}")
    status_class = labels.get("status_class")
    if status_class is not None and status_class not in SAFE_STATUS_CLASSES:
        raise ValueError(f"Unexpected HTTP status-class label: {status_class!r}")
    bound = labels.get("le")
    if bound is not None and bound != "+Inf":
        try:
            parsed_bound = float(bound)
        except ValueError as exc:
            raise ValueError(f"Invalid histogram bound {bound!r}") from exc
        if not math.isfinite(parsed_bound) or parsed_bound < 0:
            raise ValueError(f"Invalid histogram bound {bound!r}")
    if name == "infinitydb_http_request_duration_seconds_bucket":
        if bound not in SAFE_LATENCY_BOUNDS:
            raise ValueError(f"Refusing unreviewed latency histogram bound: {bound!r}")
    elif name == "infinitydb_http_response_size_bytes_bucket":
        if bound not in SAFE_RESPONSE_SIZE_BOUNDS:
            raise ValueError(f"Refusing unreviewed response-size histogram bound: {bound!r}")


def parse_history_snapshot(
    text: str,
    *,
    fallback_generation_started_at: float | None = None,
) -> ScrapeSnapshot:
    """Parse and validate the fixed-cardinality history subset of `/metrics`."""

    version: str | None = None
    snapshot_revision: str | None = None
    generation_started_at: float | None = None
    last_request_at: float | None = None
    counters: dict[SeriesKey, float] = {}

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
        if not math.isfinite(value):
            raise ValueError(f"Non-finite metric value for {name}")

        if name == "infinitydb_build_info":
            version = labels.get("version")
            snapshot_revision = labels.get("snapshot_revision")
            continue
        if name == "infinitydb_metrics_started_timestamp_seconds":
            generation_started_at = value if value > 0 else None
            continue
        if name == "infinitydb_metrics_last_request_timestamp_seconds":
            last_request_at = value if value > 0 else None
            continue
        if name not in _TRACKED_LABELS:
            continue

        _validate_series_labels(name, labels)
        if value < 0:
            raise ValueError(f"Negative monotonic metric value for {name}")
        key = SeriesKey(name=name, labels=tuple(sorted(labels.items())))
        if key in counters:
            raise ValueError(f"Duplicate Prometheus series: {name} {labels}")
        counters[key] = value

    if not version or not snapshot_revision:
        raise ValueError("Metrics history requires build version and snapshot identity")
    if generation_started_at is None:
        generation_started_at = fallback_generation_started_at
    if generation_started_at is None:
        raise ValueError("Metrics history requires a generation-start timestamp")
    if not counters:
        raise ValueError("Metrics history found no bounded monotonic request series")
    if last_request_at is not None and last_request_at < generation_started_at:
        raise ValueError("Latest request timestamp predates the metrics generation")

    return ScrapeSnapshot(
        version=version,
        snapshot_revision=snapshot_revision,
        generation_started_at=generation_started_at,
        last_request_at=last_request_at,
        counters=counters,
    )


def fetch_metrics(url: str, *, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "InfinityDB metrics-history"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _create_metadata_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


def _migrate_0_to_1(connection: sqlite3.Connection) -> None:
    _create_metadata_table(connection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_state (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            version TEXT NOT NULL,
            snapshot_revision TEXT NOT NULL,
            generation_started_at REAL NOT NULL,
            last_request_at REAL,
            collected_at REAL NOT NULL,
            counters_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_periods (
            week_start TEXT NOT NULL,
            version TEXT NOT NULL,
            snapshot_revision TEXT NOT NULL,
            first_observed_at REAL NOT NULL,
            last_observed_at REAL NOT NULL,
            generation_count INTEGER NOT NULL,
            collection_count INTEGER NOT NULL,
            PRIMARY KEY (week_start, version, snapshot_revision)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_metrics (
            week_start TEXT NOT NULL,
            version TEXT NOT NULL,
            snapshot_revision TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            labels_json TEXT NOT NULL,
            value REAL NOT NULL,
            PRIMARY KEY (
                week_start,
                version,
                snapshot_revision,
                metric_name,
                labels_json
            ),
            FOREIGN KEY (week_start, version, snapshot_revision)
                REFERENCES weekly_periods (week_start, version, snapshot_revision)
                ON DELETE CASCADE
        )
        """
    )


# Each entry upgrades exactly one persisted format version. Add the migration before incrementing
# FORMAT_VERSION so every supported upgrade path is explicit and can be applied transactionally.
_SCHEMA_MIGRATIONS: dict[int, tuple[int, Callable[[sqlite3.Connection], None]]] = {
    0: (1, _migrate_0_to_1),
}


def _database_tables(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        )
    }


def _stored_format_version(connection: sqlite3.Connection) -> int:
    tables = _database_tables(connection)
    if not tables:
        return 0
    if "metadata" not in tables:
        raise ValueError(
            "Refusing unversioned non-empty metrics-history database; "
            "no safe forward migration can be selected"
        )

    row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'format_version'"
    ).fetchone()
    if row is None:
        other_metadata = connection.execute(
            "SELECT 1 FROM metadata LIMIT 1"
        ).fetchone()
        if tables != {"metadata"} or other_metadata is not None:
            raise ValueError(
                "Refusing metrics-history database without a format version; "
                "no safe forward migration can be selected"
            )
        return 0

    raw_version = str(row[0])
    try:
        version = int(raw_version)
    except ValueError as exc:
        raise ValueError(f"Unsupported metrics-history format version: {raw_version}") from exc
    if version < 1 or raw_version != str(version):
        raise ValueError(f"Unsupported metrics-history format version: {raw_version}")
    return version


def _migration_plan(
    current_version: int,
    target_version: int,
) -> tuple[tuple[int, int, Callable[[sqlite3.Connection], None]], ...]:
    if current_version > target_version:
        raise ValueError(
            f"Unsupported metrics-history format version: {current_version}; "
            f"this collector supports up to {target_version} and will not downgrade it"
        )

    plan: list[tuple[int, int, Callable[[sqlite3.Connection], None]]] = []
    version = current_version
    while version < target_version:
        migration = _SCHEMA_MIGRATIONS.get(version)
        if migration is None:
            raise RuntimeError(
                f"Missing metrics-history forward migration from format version {version}"
            )
        next_version, apply_migration = migration
        if next_version != version + 1:
            raise RuntimeError(
                "Metrics-history migrations must advance exactly one format version: "
                f"{version} -> {next_version}"
            )
        plan.append((version, next_version, apply_migration))
        version = next_version
    return tuple(plan)


def _record_format_version(
    connection: sqlite3.Connection,
    *,
    previous_version: int,
    next_version: int,
) -> None:
    if previous_version == 0:
        connection.execute(
            "INSERT INTO metadata(key, value) VALUES ('format_version', ?)",
            (str(next_version),),
        )
        return

    cursor = connection.execute(
        """
        UPDATE metadata
        SET value = ?
        WHERE key = 'format_version' AND value = ?
        """,
        (str(next_version), str(previous_version)),
    )
    if cursor.rowcount != 1:
        raise RuntimeError(
            "Metrics-history format version changed while applying a migration"
        )


def _initialize(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    current_version = _stored_format_version(connection)
    plan = _migration_plan(current_version, FORMAT_VERSION)
    for previous_version, next_version, apply_migration in plan:
        connection.execute("BEGIN IMMEDIATE")
        try:
            apply_migration(connection)
            _record_format_version(
                connection,
                previous_version=previous_version,
                next_version=next_version,
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()

    # Preserve the format-1 recovery behavior for an already-versioned database whose tables were
    # never fully materialized. Future versions should add their own migration/validation contract.
    if current_version == FORMAT_VERSION == 1:
        with connection:
            _migrate_0_to_1(connection)


def open_history_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        _initialize(connection)
    except Exception:
        connection.close()
        raise
    return connection


def _serialize_counters(counters: Mapping[SeriesKey, float]) -> str:
    payload = [
        {
            "name": key.name,
            "labels": dict(key.labels),
            "value": value,
        }
        for key, value in sorted(counters.items())
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _deserialize_counters(raw: str) -> dict[SeriesKey, float]:
    document = json.loads(raw)
    if not isinstance(document, list):
        raise ValueError("Stored metrics-history scrape state is malformed")
    counters: dict[SeriesKey, float] = {}
    for item in document:
        if not isinstance(item, dict):
            raise ValueError("Stored metrics-history scrape state is malformed")
        name = item.get("name")
        labels = item.get("labels")
        value = item.get("value")
        if not isinstance(name, str) or not isinstance(labels, dict):
            raise ValueError("Stored metrics-history scrape state is malformed")
        labels_are_strings = all(
            isinstance(key, str) and isinstance(label, str)
            for key, label in labels.items()
        )
        if not labels_are_strings:
            raise ValueError("Stored metrics-history scrape state is malformed")
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError("Stored metrics-history scrape state is malformed")
        counters[SeriesKey(name=name, labels=tuple(sorted(labels.items())))] = float(value)
    return counters


def _load_previous(
    connection: sqlite3.Connection,
) -> tuple[tuple[str, str, str], dict[SeriesKey, float]] | None:
    row = connection.execute(
        """
        SELECT version, snapshot_revision, generation_started_at, counters_json
        FROM scrape_state
        WHERE singleton = 1
        """
    ).fetchone()
    if row is None:
        return None
    version, snapshot_revision, generation_started_at, counters_json = row
    generation_key = (
        str(version),
        str(snapshot_revision),
        f"{float(generation_started_at):.6f}",
    )
    return generation_key, _deserialize_counters(str(counters_json))


def _week_start(timestamp: float) -> date:
    observed = datetime.fromtimestamp(timestamp, UTC).date()
    return observed - timedelta(days=observed.weekday())


def _counter_deltas(
    snapshot: ScrapeSnapshot,
    previous: tuple[tuple[str, str, str], dict[SeriesKey, float]] | None,
) -> tuple[bool, dict[SeriesKey, float], bool]:
    if previous is None or previous[0] != snapshot.generation_key:
        return True, dict(snapshot.counters), False

    old_counters = previous[1]
    reset_detected = False
    deltas: dict[SeriesKey, float] = {}
    for key, current in snapshot.counters.items():
        old = old_counters.get(key, 0.0)
        if current + 1e-9 < old:
            reset_detected = True
            continue
        delta = current - old
        if delta > 0:
            deltas[key] = delta
    for key, old in old_counters.items():
        if old > 0 and key not in snapshot.counters:
            reset_detected = True
    return False, deltas, reset_detected


def _upsert_period(
    connection: sqlite3.Connection,
    *,
    week_start: str,
    snapshot: ScrapeSnapshot,
    observed_at: float,
    generation_changed: bool,
) -> None:
    connection.execute(
        """
        INSERT INTO weekly_periods(
            week_start,
            version,
            snapshot_revision,
            first_observed_at,
            last_observed_at,
            generation_count,
            collection_count
        ) VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(week_start, version, snapshot_revision) DO UPDATE SET
            first_observed_at = MIN(first_observed_at, excluded.first_observed_at),
            last_observed_at = MAX(last_observed_at, excluded.last_observed_at),
            generation_count = generation_count + excluded.generation_count,
            collection_count = collection_count + 1
        """,
        (
            week_start,
            snapshot.version,
            snapshot.snapshot_revision,
            observed_at,
            observed_at,
            1 if generation_changed else 0,
        ),
    )


def _upsert_deltas(
    connection: sqlite3.Connection,
    *,
    week_start: str,
    snapshot: ScrapeSnapshot,
    deltas: Mapping[SeriesKey, float],
) -> int:
    updated = 0
    for key, delta in deltas.items():
        if delta <= 0:
            continue
        connection.execute(
            """
            INSERT INTO weekly_metrics(
                week_start,
                version,
                snapshot_revision,
                metric_name,
                labels_json,
                value
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(
                week_start,
                version,
                snapshot_revision,
                metric_name,
                labels_json
            ) DO UPDATE SET value = value + excluded.value
            """,
            (
                week_start,
                snapshot.version,
                snapshot.snapshot_revision,
                key.name,
                key.labels_json,
                delta,
            ),
        )
        updated += 1
    return updated


def _store_state(
    connection: sqlite3.Connection,
    *,
    snapshot: ScrapeSnapshot,
    collected_at: float,
) -> None:
    connection.execute(
        """
        INSERT INTO scrape_state(
            singleton,
            version,
            snapshot_revision,
            generation_started_at,
            last_request_at,
            collected_at,
            counters_json
        ) VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(singleton) DO UPDATE SET
            version = excluded.version,
            snapshot_revision = excluded.snapshot_revision,
            generation_started_at = excluded.generation_started_at,
            last_request_at = excluded.last_request_at,
            collected_at = excluded.collected_at,
            counters_json = excluded.counters_json
        """,
        (
            snapshot.version,
            snapshot.snapshot_revision,
            snapshot.generation_started_at,
            snapshot.last_request_at,
            collected_at,
            _serialize_counters(snapshot.counters),
        ),
    )


def _database_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _vacuum(connection: sqlite3.Connection) -> None:
    connection.commit()
    connection.execute("VACUUM")


def _prune_retention(
    connection: sqlite3.Connection,
    *,
    path: Path,
    now: float,
    retention_weeks: int,
    max_bytes: int,
) -> tuple[str, ...]:
    current_week = _week_start(now)
    cutoff = current_week - timedelta(weeks=retention_weeks)
    rows = connection.execute(
        "SELECT DISTINCT week_start FROM weekly_periods WHERE week_start < ? ORDER BY week_start",
        (cutoff.isoformat(),),
    ).fetchall()
    pruned = [str(row[0]) for row in rows]
    if pruned:
        connection.execute(
            "DELETE FROM weekly_periods WHERE week_start < ?",
            (cutoff.isoformat(),),
        )
        _vacuum(connection)

    while _database_size(path) > max_bytes:
        row = connection.execute(
            """
            SELECT MIN(week_start)
            FROM weekly_periods
            WHERE week_start < ?
            """,
            (current_week.isoformat(),),
        ).fetchone()
        oldest = None if row is None else row[0]
        if oldest is None:
            break
        oldest_text = str(oldest)
        connection.execute("DELETE FROM weekly_periods WHERE week_start = ?", (oldest_text,))
        if oldest_text not in pruned:
            pruned.append(oldest_text)
        _vacuum(connection)

    return tuple(pruned)


def history_status(
    connection: sqlite3.Connection,
    *,
    path: Path,
    max_bytes: int,
) -> HistoryStatus:
    earliest, latest, week_count = connection.execute(
        """
        SELECT MIN(first_observed_at), MAX(last_observed_at), COUNT(DISTINCT week_start)
        FROM weekly_periods
        """
    ).fetchone()
    database_bytes = _database_size(path)
    return HistoryStatus(
        earliest_retained_at=None if earliest is None else float(earliest),
        latest_retained_at=None if latest is None else float(latest),
        retained_week_count=int(week_count),
        database_bytes=database_bytes,
        max_database_bytes=max_bytes,
        over_size_limit=database_bytes > max_bytes,
    )


def list_retained_periods(connection: sqlite3.Connection) -> tuple[RetainedPeriod, ...]:
    """Return retained aggregate identities newest first."""

    rows = connection.execute(
        """
        SELECT
            week_start,
            version,
            snapshot_revision,
            first_observed_at,
            last_observed_at,
            generation_count,
            collection_count
        FROM weekly_periods
        ORDER BY week_start DESC, last_observed_at DESC, version, snapshot_revision
        """
    ).fetchall()
    return tuple(
        RetainedPeriod(
            week_start=str(row[0]),
            version=str(row[1]),
            snapshot_revision=str(row[2]),
            first_observed_at=float(row[3]),
            last_observed_at=float(row[4]),
            generation_count=int(row[5]),
            collection_count=int(row[6]),
        )
        for row in rows
    )


def _select_periods(
    connection: sqlite3.Connection,
    *,
    week_start: str | None = None,
    version: str | None = None,
    snapshot_revision: str | None = None,
) -> tuple[RetainedPeriod, ...]:
    periods = list_retained_periods(connection)
    if week_start is None and version is None and snapshot_revision is None:
        return periods[:1]
    return tuple(
        period
        for period in periods
        if (week_start is None or period.week_start == week_start)
        and (version is None or period.version == version)
        and (snapshot_revision is None or period.snapshot_revision == snapshot_revision)
    )


def _period_where_clause(periods: Sequence[RetainedPeriod]) -> tuple[str, list[str]]:
    clauses: list[str] = []
    parameters: list[str] = []
    for period in periods:
        clauses.append("(week_start = ? AND version = ? AND snapshot_revision = ?)")
        parameters.extend((period.week_start, period.version, period.snapshot_revision))
    return " OR ".join(clauses), parameters


def _parse_stored_labels(raw: str) -> dict[str, str]:
    document = json.loads(raw)
    if not isinstance(document, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in document.items()
    ):
        raise ValueError("Stored metrics-history labels are malformed")
    return document


def _histogram_percentile(
    histogram: Mapping[str, int],
    percentile: float,
) -> float | None:
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    total = histogram.get("+Inf", 0)
    if total <= 0:
        total = max(histogram.values(), default=0)
    if total <= 0:
        return None
    target = math.ceil(total * percentile)
    finite = sorted(
        (float(bound), count)
        for bound, count in histogram.items()
        if bound != "+Inf"
    )
    for bound, count in finite:
        if count >= target:
            return bound
    return None


def _build_historical_report(
    connection: sqlite3.Connection,
    periods: Sequence[RetainedPeriod],
) -> HistoricalReport:
    if not periods:
        raise ValueError("No retained metrics-history periods match the requested selection")

    where_clause, parameters = _period_where_clause(periods)
    rows = connection.execute(
        f"""
        SELECT metric_name, labels_json, SUM(value)
        FROM weekly_metrics
        WHERE {where_clause}
        GROUP BY metric_name, labels_json
        """,  # noqa: S608 - predicate is generated only from fixed SQL fragments.
        parameters,
    ).fetchall()

    status_counts = {status_class: 0 for status_class in sorted(SAFE_STATUS_CLASSES)}
    route_requests: dict[str, int] = {}
    route_errors: dict[str, int] = {}
    route_latency_sums: dict[str, float] = {}
    route_latency_counts: dict[str, int] = {}
    latency_histogram: dict[str, int] = {}
    response_histogram: dict[str, int] = {}
    latency_sum = 0.0
    latency_count = 0
    response_sum = 0.0
    response_count = 0

    for metric_name, labels_raw, value_raw in rows:
        labels = _parse_stored_labels(str(labels_raw))
        value = float(value_raw)
        route = labels.get("route")
        if route is not None and route not in SAFE_ROUTES:
            raise ValueError(f"Stored metrics history contains an unreviewed route: {route!r}")

        if metric_name == "infinitydb_http_requests_total":
            status_class = labels.get("status_class")
            if status_class not in SAFE_STATUS_CLASSES or route is None:
                raise ValueError("Stored request-count labels are malformed")
            count = int(round(value))
            status_counts[status_class] += count
            route_requests[route] = route_requests.get(route, 0) + count
            if status_class in {"4xx", "5xx"}:
                route_errors[route] = route_errors.get(route, 0) + count
        elif metric_name == "infinitydb_http_request_duration_seconds_bucket":
            bound = labels.get("le")
            if route is None or bound is None:
                raise ValueError("Stored latency-histogram labels are malformed")
            latency_histogram[bound] = latency_histogram.get(bound, 0) + int(round(value))
        elif metric_name == "infinitydb_http_request_duration_seconds_sum":
            if route is None:
                raise ValueError("Stored latency-sum labels are malformed")
            latency_sum += value
            route_latency_sums[route] = route_latency_sums.get(route, 0.0) + value
        elif metric_name == "infinitydb_http_request_duration_seconds_count":
            if route is None:
                raise ValueError("Stored latency-count labels are malformed")
            count = int(round(value))
            latency_count += count
            route_latency_counts[route] = route_latency_counts.get(route, 0) + count
        elif metric_name == "infinitydb_http_response_size_bytes_bucket":
            bound = labels.get("le")
            if route is None or bound is None:
                raise ValueError("Stored response-size histogram labels are malformed")
            response_histogram[bound] = response_histogram.get(bound, 0) + int(round(value))
        elif metric_name == "infinitydb_http_response_size_bytes_sum":
            if route is None:
                raise ValueError("Stored response-size sum labels are malformed")
            response_sum += value
        elif metric_name == "infinitydb_http_response_size_bytes_count":
            if route is None:
                raise ValueError("Stored response-size count labels are malformed")
            response_count += int(round(value))

    requests = sum(status_counts.values())
    errors = status_counts["4xx"] + status_counts["5xx"]
    routes = tuple(
        RouteSummary(
            route=route,
            requests=count,
            errors=route_errors.get(route, 0),
            average_latency_seconds=(
                route_latency_sums.get(route, 0.0) / route_latency_counts[route]
                if route_latency_counts.get(route, 0) > 0
                else None
            ),
        )
        for route, count in sorted(
            route_requests.items(),
            key=lambda item: (-item[1], item[0]),
        )
        if count > 0
    )
    return HistoricalReport(
        periods=tuple(periods),
        requests=requests,
        status_counts=status_counts,
        error_rate=(errors / requests if requests else 0.0),
        server_error_rate=(status_counts["5xx"] / requests if requests else 0.0),
        average_latency_seconds=(latency_sum / latency_count if latency_count else None),
        latency_percentiles={
            "p50": _histogram_percentile(latency_histogram, 0.50),
            "p95": _histogram_percentile(latency_histogram, 0.95),
            "p99": _histogram_percentile(latency_histogram, 0.99),
        },
        latency_histogram=latency_histogram,
        average_response_size_bytes=(response_sum / response_count if response_count else None),
        response_size_percentiles={
            "p50": _histogram_percentile(response_histogram, 0.50),
            "p95": _histogram_percentile(response_histogram, 0.95),
            "p99": _histogram_percentile(response_histogram, 0.99),
        },
        response_size_histogram=response_histogram,
        routes=routes,
    )


def load_historical_report(
    connection: sqlite3.Connection,
    *,
    week_start: str | None = None,
    version: str | None = None,
    snapshot_revision: str | None = None,
) -> HistoricalReport:
    """Load one exact or aggregated retained-history selection."""

    periods = _select_periods(
        connection,
        week_start=week_start,
        version=version,
        snapshot_revision=snapshot_revision,
    )
    return _build_historical_report(connection, periods)


def collect_snapshot(
    path: Path,
    snapshot: ScrapeSnapshot,
    *,
    collected_at: float,
    retention_weeks: int = DEFAULT_RETENTION_WEEKS,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> CollectionResult:
    """Accumulate one validated scrape into bounded weekly history."""

    if retention_weeks < 1:
        raise ValueError("retention_weeks must be at least 1")
    if max_bytes < 1:
        raise ValueError("max_bytes must be greater than zero")
    if collected_at < snapshot.generation_started_at:
        raise ValueError("Collection timestamp predates the metrics generation")

    connection = open_history_database(path)
    try:
        previous = _load_previous(connection)
        generation_changed, deltas, reset_detected = _counter_deltas(snapshot, previous)
        week_start = _week_start(collected_at).isoformat()

        if reset_detected:
            # Fail closed rather than converting an unexplained in-generation counter decrease
            # into a positive delta. Replace only the rolling state so the next collection can
            # continue from a known baseline without inflating retained history.
            _store_state(connection, snapshot=snapshot, collected_at=collected_at)
            connection.commit()
            pruned = _prune_retention(
                connection,
                path=path,
                now=collected_at,
                retention_weeks=retention_weeks,
                max_bytes=max_bytes,
            )
            status = history_status(connection, path=path, max_bytes=max_bytes)
            return CollectionResult(
                outcome="counter-reset",
                generation_changed=False,
                series_updated=0,
                pruned_weeks=pruned,
                status=status,
            )

        _upsert_period(
            connection,
            week_start=week_start,
            snapshot=snapshot,
            observed_at=collected_at,
            generation_changed=generation_changed,
        )
        series_updated = _upsert_deltas(
            connection,
            week_start=week_start,
            snapshot=snapshot,
            deltas=deltas,
        )
        _store_state(connection, snapshot=snapshot, collected_at=collected_at)
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('last_successful_collection', ?)",
            (f"{collected_at:.6f}",),
        )
        connection.commit()
        pruned = _prune_retention(
            connection,
            path=path,
            now=collected_at,
            retention_weeks=retention_weeks,
            max_bytes=max_bytes,
        )
        status = history_status(connection, path=path, max_bytes=max_bytes)
        return CollectionResult(
            outcome="collected" if not status.over_size_limit else "size-limit-exceeded",
            generation_changed=generation_changed,
            series_updated=series_updated,
            pruned_weeks=pruned,
            status=status,
        )
    finally:
        connection.close()


def _format_timestamp(value: float | None) -> str:
    if value is None:
        return "—"
    return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def render_status(status: HistoryStatus) -> str:
    return "\n".join(
        (
            "InfinityDB metrics history",
            f"Earliest retained: {_format_timestamp(status.earliest_retained_at)}",
            f"Latest retained: {_format_timestamp(status.latest_retained_at)}",
            f"Retained weeks: {status.retained_week_count}",
            f"Database size: {status.database_bytes} bytes",
            f"Safety ceiling: {status.max_database_bytes} bytes",
            f"Over size limit: {'yes' if status.over_size_limit else 'no'}",
        )
    )


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.1f} µs"
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    return f"{seconds:.3f} s"


def _format_bytes(value: float | None) -> str:
    if value is None:
        return "—"
    if value < 1024:
        return f"{value:.0f} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KiB"
    return f"{value / (1024 * 1024):.2f} MiB"


def _finite_histogram_bounds(histogram: Mapping[str, int]) -> tuple[float, ...]:
    return tuple(sorted(float(bound) for bound in histogram if bound != "+Inf"))


def _format_percentile(
    value: float | None,
    histogram: Mapping[str, int],
    *,
    formatter: Callable[[float | None], str],
) -> str:
    if value is not None:
        return f"≤ {formatter(value)}"
    if not histogram or max(histogram.values(), default=0) <= 0:
        return "—"
    finite = _finite_histogram_bounds(histogram)
    if not finite:
        return "—"
    return f"> {formatter(finite[-1])}"


def _format_rate(value: float) -> str:
    return f"{value * 100:.2f}%"


def _period_label(period: RetainedPeriod) -> str:
    snapshot = period.snapshot_revision
    short_snapshot = snapshot if len(snapshot) <= 16 else f"{snapshot[:12]}…"
    return f"{period.week_start} | {period.version} | {short_snapshot}"


def render_periods(periods: Sequence[RetainedPeriod]) -> str:
    lines = ["InfinityDB retained metrics periods"]
    if not periods:
        lines.append("No retained periods.")
        return "\n".join(lines)
    for period in periods:
        lines.append(
            f"{period.week_start} | {period.version} | {period.snapshot_revision} | "
            f"{_format_timestamp(period.first_observed_at)} → "
            f"{_format_timestamp(period.last_observed_at)} | "
            f"generations={period.generation_count} collections={period.collection_count}"
        )
    return "\n".join(lines)


def _format_histogram(
    histogram: Mapping[str, int],
    *,
    formatter: Callable[[float | None], str],
) -> str:
    ordered = sorted(
        ((float(bound), count) for bound, count in histogram.items() if bound != "+Inf"),
        key=lambda item: item[0],
    )
    parts = [f"≤{formatter(bound)}={count}" for bound, count in ordered]
    if "+Inf" in histogram:
        parts.append(f"+Inf={histogram['+Inf']}")
    return ", ".join(parts) if parts else "—"


def render_historical_report(report: HistoricalReport, *, top_routes: int) -> str:
    period_labels = ", ".join(_period_label(period) for period in report.periods)
    status_text = ", ".join(
        f"{status_class}={report.status_counts.get(status_class, 0)}"
        for status_class in sorted(SAFE_STATUS_CLASSES)
    )
    latency_percentiles = report.latency_percentiles
    response_percentiles = report.response_size_percentiles
    lines = [
        "InfinityDB metrics history report",
        f"Selection: {period_labels}",
        (
            f"Observed: {_format_timestamp(report.first_observed_at)} → "
            f"{_format_timestamp(report.last_observed_at)}"
        ),
        (
            f"Periods: {len(report.periods)} | "
            f"generations={sum(period.generation_count for period in report.periods)} | "
            f"collections={sum(period.collection_count for period in report.periods)}"
        ),
        f"Requests: {report.requests}",
        f"Status: {status_text}",
        (
            f"Error rate: {_format_rate(report.error_rate)} | "
            f"5xx rate: {_format_rate(report.server_error_rate)}"
        ),
        (
            "Latency: "
            f"avg {_format_duration(report.average_latency_seconds)} | "
            "p50 "
            + _format_percentile(
                latency_percentiles.get("p50"),
                report.latency_histogram,
                formatter=_format_duration,
            )
            + " | p95 "
            + _format_percentile(
                latency_percentiles.get("p95"),
                report.latency_histogram,
                formatter=_format_duration,
            )
            + " | p99 "
            + _format_percentile(
                latency_percentiles.get("p99"),
                report.latency_histogram,
                formatter=_format_duration,
            )
        ),
        (
            "Response size: "
            f"avg {_format_bytes(report.average_response_size_bytes)} | "
            "p50 "
            + _format_percentile(
                response_percentiles.get("p50"),
                report.response_size_histogram,
                formatter=_format_bytes,
            )
            + " | p95 "
            + _format_percentile(
                response_percentiles.get("p95"),
                report.response_size_histogram,
                formatter=_format_bytes,
            )
            + " | p99 "
            + _format_percentile(
                response_percentiles.get("p99"),
                report.response_size_histogram,
                formatter=_format_bytes,
            )
        ),
        "Latency histogram (cumulative): "
        + _format_histogram(report.latency_histogram, formatter=_format_duration),
        "Response-size histogram (cumulative): "
        + _format_histogram(report.response_size_histogram, formatter=_format_bytes),
    ]
    if top_routes > 0:
        lines.append(f"Top routes (max {top_routes}):")
        for route in report.routes[:top_routes]:
            share = route.requests / report.requests if report.requests else 0.0
            error_rate = route.errors / route.requests if route.requests else 0.0
            lines.append(
                f"  {route.route}: requests={route.requests} "
                f"share={_format_rate(share)} errors={_format_rate(error_rate)} "
                f"avg_latency={_format_duration(route.average_latency_seconds)}"
            )
    return "\n".join(lines)


def _format_change(before: float, after: float, *, percent: bool = False) -> str:
    delta = after - before
    if percent:
        return f"{before * 100:.2f}% → {after * 100:.2f}% ({delta * 100:+.2f} pp)"
    if before == 0:
        relative = "n/a" if after == 0 else "new"
    else:
        relative = f"{delta / before * 100:+.1f}%"
    return f"{before:.3g} → {after:.3g} ({delta:+.3g}, {relative})"


def render_comparison(
    before: HistoricalReport,
    after: HistoricalReport,
    *,
    top_routes: int,
) -> str:
    lines = [
        "InfinityDB metrics history comparison",
        "From: " + ", ".join(_period_label(period) for period in before.periods),
        "To:   " + ", ".join(_period_label(period) for period in after.periods),
        f"Requests: {_format_change(float(before.requests), float(after.requests))}",
        f"Error rate: {_format_change(before.error_rate, after.error_rate, percent=True)}",
        (
            "5xx rate: "
            + _format_change(before.server_error_rate, after.server_error_rate, percent=True)
        ),
    ]

    if before.average_latency_seconds is not None and after.average_latency_seconds is not None:
        lines.append(
            "Average latency: "
            f"{_format_duration(before.average_latency_seconds)} → "
            f"{_format_duration(after.average_latency_seconds)}"
        )
    lines.append(
        "p95 latency: "
        + _format_percentile(
            before.latency_percentiles.get("p95"),
            before.latency_histogram,
            formatter=_format_duration,
        )
        + " → "
        + _format_percentile(
            after.latency_percentiles.get("p95"),
            after.latency_histogram,
            formatter=_format_duration,
        )
    )
    if (
        before.average_response_size_bytes is not None
        and after.average_response_size_bytes is not None
    ):
        lines.append(
            "Average response size: "
            f"{_format_bytes(before.average_response_size_bytes)} → "
            f"{_format_bytes(after.average_response_size_bytes)}"
        )
    lines.append(
        "p95 response size: "
        + _format_percentile(
            before.response_size_percentiles.get("p95"),
            before.response_size_histogram,
            formatter=_format_bytes,
        )
        + " → "
        + _format_percentile(
            after.response_size_percentiles.get("p95"),
            after.response_size_histogram,
            formatter=_format_bytes,
        )
    )

    if top_routes > 0:
        before_routes = {route.route: route.requests for route in before.routes}
        after_routes = {route.route: route.requests for route in after.routes}
        changed_routes = sorted(
            set(before_routes) | set(after_routes),
            key=lambda route: (
                -abs(after_routes.get(route, 0) - before_routes.get(route, 0)),
                route,
            ),
        )
        lines.append(f"Largest route-count changes (max {top_routes}):")
        for route in changed_routes[:top_routes]:
            previous = before_routes.get(route, 0)
            current = after_routes.get(route, 0)
            lines.append(f"  {route}: {previous} → {current} ({current - previous:+d})")
    return "\n".join(lines)


def _collect_from_endpoint(args: argparse.Namespace) -> CollectionResult:
    collected_at = time.time()
    text = fetch_metrics(args.url, timeout=args.timeout)
    fallback_generation_started_at = (
        collected_at if getattr(args, "legacy_generation_at_collection", False) else None
    )
    snapshot = parse_history_snapshot(
        text,
        fallback_generation_started_at=fallback_generation_started_at,
    )
    return collect_snapshot(
        args.database,
        snapshot,
        collected_at=collected_at,
        retention_weeks=args.retention_weeks,
        max_bytes=args.max_bytes,
    )


def _print_collection(result: CollectionResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return
    print(f"Metrics history: {result.outcome}")
    print(f"Generation changed: {'yes' if result.generation_changed else 'no'}")
    print(f"Updated series: {result.series_updated}")
    if result.pruned_weeks:
        print("Pruned weeks: " + ", ".join(result.pruned_weeks))
    print(render_status(result.status))


def _add_collection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--url",
        default=os.environ.get("INFINITYDB_METRICS_HISTORY_URL", DEFAULT_METRICS_URL),
        help="private InfinityDB metrics URL",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--retention-weeks",
        type=int,
        default=DEFAULT_RETENTION_WEEKS,
        help="completed weeks retained in addition to the current week",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help="hard SQLite file-size safety ceiling",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")


def _add_report_selector_arguments(
    parser: argparse.ArgumentParser,
    *,
    prefix: str = "",
) -> None:
    option_prefix = f"{prefix}-" if prefix else ""
    destination_prefix = f"{prefix}_" if prefix else ""
    parser.add_argument(
        f"--{option_prefix}week",
        dest=f"{destination_prefix}week",
        help="ISO week start (Monday, YYYY-MM-DD)",
    )
    parser.add_argument(
        f"--{option_prefix}version",
        dest=f"{destination_prefix}version",
        help="InfinityDB version selector",
    )
    parser.add_argument(
        f"--{option_prefix}snapshot",
        dest=f"{destination_prefix}snapshot",
        help="exact snapshot revision selector",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect bounded InfinityDB aggregate metrics into weekly SQLite history."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(
            os.environ.get("INFINITYDB_METRICS_HISTORY_DATABASE", str(DEFAULT_DATABASE))
        ),
        help="SQLite history database",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="collect one metrics snapshot")
    _add_collection_arguments(collect_parser)
    collect_parser.add_argument(
        "--legacy-generation-at-collection",
        action="store_true",
        help=(
            "accept a legacy metrics surface without generation timestamps by treating this "
            "one-shot collection time as its generation boundary"
        ),
    )

    run_parser = subparsers.add_parser("run", help="collect continuously at a fixed interval")
    _add_collection_arguments(run_parser)
    run_parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="collection interval in seconds",
    )

    status_parser = subparsers.add_parser("status", help="show bounded retention/storage status")
    status_parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    status_parser.add_argument("--json", action="store_true")

    periods_parser = subparsers.add_parser(
        "periods",
        help="list retained week/version/snapshot periods",
    )
    periods_parser.add_argument("--json", action="store_true")

    report_parser = subparsers.add_parser("report", help="summarize retained aggregate history")
    _add_report_selector_arguments(report_parser)
    report_parser.add_argument(
        "--top-routes",
        type=int,
        default=10,
        help="maximum normalized routes shown in human-readable output",
    )
    report_parser.add_argument("--json", action="store_true")

    compare_parser = subparsers.add_parser(
        "compare",
        help="compare two retained aggregate selections (defaults to the latest two periods)",
    )
    _add_report_selector_arguments(compare_parser, prefix="from")
    _add_report_selector_arguments(compare_parser, prefix="to")
    compare_parser.add_argument(
        "--top-routes",
        type=int,
        default=10,
        help="maximum normalized route-count changes shown in human-readable output",
    )
    compare_parser.add_argument("--json", action="store_true")
    return parser


def _validate_collection_args(args: argparse.Namespace) -> None:
    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than zero")
    if args.retention_weeks < 1:
        raise SystemExit("--retention-weeks must be at least 1")
    if args.max_bytes < 1:
        raise SystemExit("--max-bytes must be greater than zero")
    if args.command == "run" and args.interval <= 0:
        raise SystemExit("--interval must be greater than zero")


def _collection_exit_code(result: CollectionResult) -> int:
    if result.outcome == "collected":
        return 0
    if result.outcome in {"counter-reset", "size-limit-exceeded"}:
        return 1
    return 2


def _run_forever(args: argparse.Namespace) -> int:
    while True:
        started = time.monotonic()
        try:
            result = _collect_from_endpoint(args)
        except (OSError, UnicodeError, ValueError, sqlite3.Error, urllib.error.URLError) as exc:
            print(f"metrics-history collection failed: {exc}", file=sys.stderr)
        else:
            _print_collection(result, as_json=args.json)
        elapsed = time.monotonic() - started
        time.sleep(max(args.interval - elapsed, 0.0))


def _validate_week_selector(value: str | None, option: str) -> None:
    if value is None:
        return
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"{option} must be YYYY-MM-DD") from exc
    if parsed.weekday() != 0:
        raise SystemExit(f"{option} must be the Monday starting an ISO week")


def _selector_from_args(args: argparse.Namespace, *, prefix: str = "") -> dict[str, str | None]:
    attribute_prefix = f"{prefix}_" if prefix else ""
    return {
        "week_start": getattr(args, f"{attribute_prefix}week"),
        "version": getattr(args, f"{attribute_prefix}version"),
        "snapshot_revision": getattr(args, f"{attribute_prefix}snapshot"),
    }


def _comparison_payload(
    before: HistoricalReport,
    after: HistoricalReport,
) -> dict[str, object]:
    before_routes = {route.route: route.requests for route in before.routes}
    after_routes = {route.route: route.requests for route in after.routes}
    route_deltas = [
        {
            "route": route,
            "fromRequests": before_routes.get(route, 0),
            "toRequests": after_routes.get(route, 0),
            "deltaRequests": after_routes.get(route, 0) - before_routes.get(route, 0),
        }
        for route in sorted(set(before_routes) | set(after_routes))
    ]
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "from": before.as_dict(),
        "to": after.as_dict(),
        "routeRequestDeltas": route_deltas,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"collect", "run"}:
        _validate_collection_args(args)
    elif args.command == "status" and args.max_bytes < 1:
        raise SystemExit("--max-bytes must be greater than zero")

    if args.command == "report":
        _validate_week_selector(args.week, "--week")
        if args.top_routes < 0:
            raise SystemExit("--top-routes must be zero or greater")
    elif args.command == "compare":
        _validate_week_selector(args.from_week, "--from-week")
        _validate_week_selector(args.to_week, "--to-week")
        if args.top_routes < 0:
            raise SystemExit("--top-routes must be zero or greater")

    if args.command == "status":
        connection = open_history_database(args.database)
        try:
            status = history_status(connection, path=args.database, max_bytes=args.max_bytes)
        finally:
            connection.close()
        if args.json:
            print(json.dumps(status.as_dict(), indent=2, sort_keys=True))
        else:
            print(render_status(status))
        return 1 if status.over_size_limit else 0

    if args.command == "periods":
        connection = open_history_database(args.database)
        try:
            periods = list_retained_periods(connection)
        finally:
            connection.close()
        if args.json:
            print(
                json.dumps(
                    {
                        "format": FORMAT,
                        "formatVersion": FORMAT_VERSION,
                        "periods": [period.as_dict() for period in periods],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(render_periods(periods))
        return 0

    if args.command == "report":
        connection = open_history_database(args.database)
        try:
            report = load_historical_report(connection, **_selector_from_args(args))
        except ValueError as exc:
            print(f"metrics-history report failed: {exc}", file=sys.stderr)
            return 2
        finally:
            connection.close()
        if args.json:
            print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        else:
            print(render_historical_report(report, top_routes=args.top_routes))
        return 0

    if args.command == "compare":
        from_selector = _selector_from_args(args, prefix="from")
        to_selector = _selector_from_args(args, prefix="to")
        selector_values = (*from_selector.values(), *to_selector.values())
        explicit_selector = any(value is not None for value in selector_values)
        if explicit_selector and (
            not any(value is not None for value in from_selector.values())
            or not any(value is not None for value in to_selector.values())
        ):
            raise SystemExit(
                "explicit compare requires at least one --from-* and one --to-* selector"
            )

        connection = open_history_database(args.database)
        try:
            if explicit_selector:
                before = load_historical_report(connection, **from_selector)
                after = load_historical_report(connection, **to_selector)
            else:
                periods = list_retained_periods(connection)
                if len(periods) < 2:
                    raise ValueError("At least two retained periods are required for comparison")
                after = _build_historical_report(connection, periods[:1])
                before = _build_historical_report(connection, periods[1:2])
        except ValueError as exc:
            print(f"metrics-history comparison failed: {exc}", file=sys.stderr)
            return 2
        finally:
            connection.close()
        if args.json:
            print(json.dumps(_comparison_payload(before, after), indent=2, sort_keys=True))
        else:
            print(render_comparison(before, after, top_routes=args.top_routes))
        return 0

    if args.command == "run":
        return _run_forever(args)

    try:
        result = _collect_from_endpoint(args)
    except (OSError, UnicodeError, ValueError, sqlite3.Error, urllib.error.URLError) as exc:
        print(f"metrics-history collection failed: {exc}", file=sys.stderr)
        return 2
    _print_collection(result, as_json=args.json)
    return _collection_exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
