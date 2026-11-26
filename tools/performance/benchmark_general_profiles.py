"""Measure a disposable General-profile SQLite projection against runtime composition."""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import tempfile
from contextlib import closing
from hashlib import file_digest
from pathlib import Path
from time import perf_counter
from typing import Any

from infinity_db.database_set import SEASON_DATABASE_SOURCES
from infinity_db.unit_presentation import OPTIONAL_AVAILABILITY_FLAGS, extended_general_profiles
from infinity_db.web.app import Application
from tools.performance.benchmark_runtime import _summary


def _flags(mask: int) -> frozenset[str]:
    return frozenset(
        flag for bit, flag in enumerate(OPTIONAL_AVAILABILITY_FLAGS)
        if mask & (1 << bit)
    )


def _encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _app(army: Path) -> Application:
    return Application(
        army, army.with_name("rules_n5.db"),
        season_databases={
            season: army.with_name(filename)
            for season, (filename, _) in SEASON_DATABASE_SOURCES.items()
        },
    )


def _unit_ids(army: Path) -> list[int]:
    with closing(sqlite3.connect(army.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return [row[0] for row in db.execute("SELECT id FROM logical_units ORDER BY id")]


def _build_projection(
    app: Application, destination: Path, unit_ids: list[int],
) -> dict[tuple[int, int], str]:
    """Evaluate all 16 selections, deduplicating exact serialized payloads."""
    expected = {}
    with closing(sqlite3.connect(destination)) as db, db:
        db.executescript("""
            CREATE TABLE payload (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE selection (
                unit_id INTEGER NOT NULL, mask INTEGER NOT NULL,
                payload_id INTEGER NOT NULL REFERENCES payload(id),
                PRIMARY KEY (unit_id, mask)
            ) WITHOUT ROWID;
        """)
        payload_ids: dict[str, int] = {}
        for index, unit_id in enumerate(unit_ids, 1):
            detail = app.database.get_unit(unit_id)
            if detail is None:
                raise ValueError(f"Missing logical Unit {unit_id}")
            for mask in range(1 << len(OPTIONAL_AVAILABILITY_FLAGS)):
                flags = _flags(mask)
                # The production Explorer composer is the reference. No alternate
                # skill, symbol, availability or General-profile semantics here.
                projected = extended_general_profiles(app.api._present_unit(
                    detail, optional_filters={
                        flag: flag in flags for flag in OPTIONAL_AVAILABILITY_FLAGS
                    }, general_only=True,
                ))
                body = _encode(projected)
                if body not in payload_ids:
                    payload_id = len(payload_ids) + 1
                    db.execute("INSERT INTO payload VALUES (?, ?)", (payload_id, body))
                    payload_ids[body] = payload_id
                db.execute(
                    "INSERT INTO selection VALUES (?, ?, ?)",
                    (unit_id, mask, payload_ids[body]),
                )
                expected[unit_id, mask] = body
            if index % 100 == 0:
                print(f"Composed {index}/{len(unit_ids)} Units", flush=True)
    return expected


def _read_batch(
    database: Path, unit_ids: list[int], mask: int,
) -> list[list[dict[str, Any]]]:
    if not unit_ids:
        return []
    placeholders = ", ".join("?" for _ in unit_ids)
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = dict(db.execute(
            "SELECT s.unit_id, p.body FROM selection AS s JOIN payload AS p "
            "ON p.id = s.payload_id WHERE s.mask = ? "
            f"AND s.unit_id IN ({placeholders})", (mask, *unit_ids),
        ))
    if set(rows) != set(unit_ids):
        raise ValueError("Incomplete materialized selection")
    return [json.loads(rows[unit_id]) for unit_id in unit_ids]


def benchmark(army: Path, destination: Path, *, iterations: int) -> dict[str, Any]:
    unit_ids = _unit_ids(army)
    if not unit_ids:
        raise ValueError("No logical Units to benchmark")
    started = perf_counter()
    app = _app(army)
    startup_seconds = perf_counter() - started
    started = perf_counter()
    expected = _build_projection(app, destination, unit_ids)
    generation_seconds = perf_counter() - started

    # Verify persisted coverage and exact JSON round-trip for every selection.
    published_selections = 0
    for mask in range(1 << len(OPTIONAL_AVAILABILITY_FLAGS)):
        for offset in range(0, len(unit_ids), 100):
            batch = unit_ids[offset:offset + 100]
            actual = _read_batch(destination, batch, mask)
            if [_encode(value) for value in actual] != [
                expected[unit_id, mask] for unit_id in batch
            ]:
                raise ValueError(f"Projection parity failed for mask {mask}, offset {offset}")
            published = app.database.general_profiles(batch, _flags(mask))
            if published is not None:
                if [_encode(published[unit_id]) for unit_id in batch] != [
                    expected[unit_id, mask] for unit_id in batch
                ]:
                    raise ValueError(f"Published parity failed for mask {mask}, offset {offset}")
                published_selections += len(batch)
    with closing(sqlite3.connect(destination)) as db:
        unique_payloads = db.execute("SELECT COUNT(*) FROM payload").fetchone()[0]
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Projection SQLite integrity check failed")

    batch = [item["id"] for item in app.database.list_units(limit=50)["items"]]
    flags = _flags(0)
    cold, warm, persisted, startup, after_list, published_times = [], [], [], [], [], []
    for _ in range(iterations):
        started = perf_counter()
        fresh = _app(army)
        startup.append(perf_counter() - started)
        started = perf_counter()
        reference = [fresh.api._extended_profiles(unit_id, flags) for unit_id in batch]
        cold.append(perf_counter() - started)
        started = perf_counter()
        repeated = [fresh.api._extended_profiles(unit_id, flags) for unit_id in batch]
        warm.append(perf_counter() - started)
        started = perf_counter()
        materialized = _read_batch(destination, batch, 0)
        persisted.append(perf_counter() - started)
        if _encode(reference) != _encode(repeated) or _encode(reference) != _encode(materialized):
            raise ValueError("Runtime Explorer batch differs from persisted projection")
        if published_selections:
            started = perf_counter()
            published = fresh.database.general_profiles(batch, flags)
            published_times.append(perf_counter() - started)
            if published is None or _encode(reference) != _encode([
                published[unit_id] for unit_id in batch
            ]):
                raise ValueError("Runtime Explorer batch differs from published projection")

        # Extended is normally selected after the initial compact list.
        list_ready = _app(army)
        list_ready.database.list_units(limit=50)
        started = perf_counter()
        list_reference = [list_ready.api._extended_profiles(unit_id, flags) for unit_id in batch]
        after_list.append(perf_counter() - started)
        if _encode(reference) != _encode(list_reference):
            raise ValueError("Initial compact list changed General-profile output")

    input_hashes = {}
    for path in (
        army, army.with_name("rules_n5.db"),
        *(army.with_name(filename) for filename, _ in SEASON_DATABASE_SOURCES.values()),
    ):
        with path.open("rb") as source:
            input_hashes[path.name] = file_digest(source, "sha256").hexdigest()
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "inputSha256": input_hashes,
        "armyBytes": army.stat().st_size,
        "logicalUnits": len(unit_ids),
        "selections": len(expected),
        "uniquePayloads": unique_payloads,
        "projectionBytes": destination.stat().st_size,
        "generationSeconds": generation_seconds,
        "initialStartupSeconds": startup_seconds,
        "sampleUnits": len(batch),
        "iterations": iterations,
        "applicationStartup": _summary(startup),
        "runtimeCold": _summary(cold),
        "runtimeAfterList": _summary(after_list),
        "runtimeWarm": _summary(warm),
        "persistedBatch": _summary(persisted),
        "publishedSelections": published_selections,
        **({"publishedBatch": _summary(published_times)} if published_times else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("army", type=Path)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Exclusive JSON report path")
    args = parser.parse_args(argv)
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    if args.output is not None and args.output.exists():
        parser.error("Report already exists")
    scratch = Path("local/work/performance")
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="general-profile-pilot-", dir=scratch) as work:
        report = benchmark(args.army, Path(work) / "projection.db", iterations=args.iterations)
        content = json.dumps(report, indent=2, sort_keys=True)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(content + "\n")
        print(content, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
