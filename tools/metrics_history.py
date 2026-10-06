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
from collections.abc import Mapping, Sequence
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
        "/static/:asset",
        "/static/:symbol",
        "/other",
    }
)
SAFE_STATUS_CLASSES = frozenset({"1xx", "2xx", "3xx", "4xx", "5xx"})

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


def _initialize(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'format_version'"
    ).fetchone()
    if row is not None and str(row[0]) != str(FORMAT_VERSION):
        raise ValueError(f"Unsupported metrics-history format version: {row[0]}")
    connection.execute(
        "INSERT OR IGNORE INTO metadata(key, value) VALUES ('format_version', ?)",
        (str(FORMAT_VERSION),),
    )
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS scrape_state (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            version TEXT NOT NULL,
            snapshot_revision TEXT NOT NULL,
            generation_started_at REAL NOT NULL,
            last_request_at REAL,
            collected_at REAL NOT NULL,
            counters_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS weekly_periods (
            week_start TEXT NOT NULL,
            version TEXT NOT NULL,
            snapshot_revision TEXT NOT NULL,
            first_observed_at REAL NOT NULL,
            last_observed_at REAL NOT NULL,
            generation_count INTEGER NOT NULL,
            collection_count INTEGER NOT NULL,
            PRIMARY KEY (week_start, version, snapshot_revision)
        );

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
        );
        """
    )
    connection.commit()


def open_history_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    _initialize(connection)
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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"collect", "run"}:
        _validate_collection_args(args)
    elif args.max_bytes < 1:
        raise SystemExit("--max-bytes must be greater than zero")

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
