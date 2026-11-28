"""Measure invariant Unit enrichment and bounded Specialist candidate inputs."""
from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import zlib
from contextlib import closing
from pathlib import Path
from statistics import median
from time import perf_counter

from infinity_db.army_slugs import enrich_army_references
from infinity_db.catalog_slugs import enrich_nested_catalog_slugs
from infinity_db.specialist_filter import SPECIALIST_CONTEXTS, candidate_unit_ids
from infinity_db.unit_slugs import attach_public_unit_slug
from infinity_db.web.app import create_app_from_database_set
from infinity_db.web.unit_comparison import comparison_unit
from tools.browser_wsgi_transport import wsgi_response


def benchmark_comparison(db_dir: Path, samples: int, *, compact: bool = False) -> None:
    """Compare current-only or compact requests against their preceding response shape."""
    app = create_app_from_database_set(db_dir)
    baseline_query = "?history=0" if compact else ""
    candidate_query = "?view=comparison&history=0" if compact else "?history=0"
    with closing(sqlite3.connect(db_dir / "army.db")) as db:
        rows = db.execute(
            "SELECT unit_id, length(body) FROM unit_history_payloads ORDER BY unit_id"
        ).fetchall()
    assert rows, "Published history is required for this benchmark"
    ids = [row[0] for row in rows[::max(1, len(rows) // samples)][:samples]]
    largest = [row[0] for row in sorted(rows, key=lambda row: (-row[1], row[0]))[:5]]
    for name, cohort in (("systematic", ids), ("history-rich", largest)):
        full_sizes, current_sizes, full_compressed, current_compressed = [], [], [], []
        full_times, current_times = [], []
        for unit_id in cohort:
            url = f"http://localhost/api/units/{unit_id}"
            status, _, body = wsgi_response(app, url + baseline_query)
            assert status == 200, unit_id
            expected = json.loads(body)
            if compact:
                expected = comparison_unit(expected)
            else:
                expected.pop("historical_contexts", None)
                for section in ("general_profiles", "armies"):
                    for card in expected[section]:
                        card.pop("history", None)
            status, _, current = wsgi_response(app, url + candidate_query)
            assert status == 200 and json.loads(current) == expected, unit_id
            full_sizes.append(len(body))
            current_sizes.append(len(current))
            full_compressed.append(len(zlib.compress(body)))
            current_compressed.append(len(zlib.compress(current)))
            for iteration in range(10):
                for omit in (False, True) if iteration % 2 == 0 else (True, False):
                    start = perf_counter()
                    query = candidate_query if omit else baseline_query
                    status, _, actual = wsgi_response(app, url + query)
                    (current_times if omit else full_times).append(perf_counter() - start)
                    assert status == 200 and actual == (current if omit else body), unit_id
            if name == "history-rich":
                print(
                    f"{unit_id}: {json.loads(body)['name']}; "
                    f"{len(body):,} -> {len(current):,} bytes", flush=True,
                )
        print(
            f"{name}: {len(cohort)} Units; total bytes "
            f"{sum(full_sizes):,} -> {sum(current_sizes):,}; "
            f"zlib bytes {sum(full_compressed):,} -> {sum(current_compressed):,}; "
            f"warm WSGI median {median(full_times)*1000:.2f} -> "
            f"{median(current_times)*1000:.2f} ms; expected response parity",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--comparison", action="store_true", help="Compare Unit history omission.")
    parser.add_argument("--compact", action="store_true", help="Compare compact Unit responses.")
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    if args.comparison or args.compact:
        benchmark_comparison(args.db_dir, args.samples, compact=args.compact)
        return
    app = create_app_from_database_set(args.db_dir)
    api = app.api
    database = app.database
    assert app.rules_database is not None
    ids = sorted(group["id"] for group in database._unit_graph()["groups"])
    ids = ids[::max(1, len(ids) // args.samples)][:args.samples]
    raw_sizes, enriched_sizes, compressed_sizes = [], [], []
    raw_times, enrichment_times, read_times, compressed_times = [], [], [], []
    with tempfile.TemporaryDirectory() as temp:
        with closing(sqlite3.connect(Path(temp) / "pilot.db")) as db, db:
            db.execute(
                "CREATE TABLE unit_detail (id INTEGER PRIMARY KEY, body TEXT, compressed BLOB)"
            )
            for unit_id in ids:
                start = perf_counter()
                raw = database.get_unit(unit_id)
                raw_times.append(perf_counter() - start)
                assert raw is not None
                start = perf_counter()
                enriched = api.skill_catalog.enrich_unit(raw)
                enriched = api.equipment_catalog.enrich_unit(enriched, in_place=True)
                enriched = enrich_nested_catalog_slugs(
                    database, enriched, frozenset({"equipment", "weapons"}), in_place=True,
                )
                attach_public_unit_slug(database, enriched)
                enriched = enrich_army_references(database, enriched, in_place=True)
                api.symbol_catalog.enrich_unit(enriched)
                enrichment_times.append(perf_counter() - start)
                body = json.dumps(enriched, ensure_ascii=False, separators=(",", ":"))
                compressed = zlib.compress(body.encode("utf-8"))
                raw_sizes.append(len(json.dumps(raw, ensure_ascii=False).encode("utf-8")))
                enriched_sizes.append(len(body.encode("utf-8")))
                compressed_sizes.append(len(compressed))
                db.execute("INSERT INTO unit_detail VALUES (?,?,?)", (unit_id, body, compressed))
                expected = json.loads(body)
                start = perf_counter()
                actual = json.loads(db.execute(
                    "SELECT body FROM unit_detail WHERE id=?", (unit_id,),
                ).fetchone()[0])
                read_times.append(perf_counter() - start)
                assert actual == expected
                start = perf_counter()
                actual = json.loads(zlib.decompress(db.execute(
                    "SELECT compressed FROM unit_detail WHERE id=?", (unit_id,),
                ).fetchone()[0]))
                compressed_times.append(perf_counter() - start)
                assert actual == expected
            print(f"Unit sample: {len(ids)}", flush=True)
            print(
                f"raw bytes={sum(raw_sizes):,}; enriched={sum(enriched_sizes):,}; "
                f"compressed={sum(compressed_sizes):,}", flush=True,
            )
            print(
                f"median ms: raw {median(raw_times)*1000:.2f}; "
                f"enrichment {median(enrichment_times)*1000:.2f}; "
                f"JSON read {median(read_times)*1000:.2f}; "
                f"compressed read {median(compressed_times)*1000:.2f}", flush=True,
            )
            db.execute("CREATE TABLE specialists (context TEXT PRIMARY KEY, body TEXT)")
            for context in sorted(SPECIALIST_CONTEXTS):
                times = []
                for _ in range(5):
                    start = perf_counter()
                    candidates = candidate_unit_ids(database, app.rules_database, context)
                    times.append(perf_counter() - start)
                body = json.dumps(sorted(candidates), separators=(",", ":"))
                db.execute("INSERT INTO specialists VALUES (?,?)", (context, body))
                start = perf_counter()
                result = frozenset(json.loads(db.execute(
                    "SELECT body FROM specialists WHERE context=?", (context,),
                ).fetchone()[0]))
                elapsed = perf_counter() - start
                assert result == candidates
                print(
                    f"{context}: {len(candidates)} IDs; {len(body)} bytes; "
                    f"first {times[0]*1000:.2f} ms; repeat median {median(times[1:])*1000:.2f} ms; "
                    f"projected {elapsed*1000:.2f} ms", flush=True,
                )
                projection = database.catalog_projection
                if projection is not None:
                    published_times = []
                    for _ in range(5):
                        start = perf_counter()
                        published = projection.specialist_candidates(context)
                        published_times.append(perf_counter() - start)
                        if published is None:
                            break
                        assert published == candidates
                    if published is not None:
                        print(
                            f"{context}: published median {median(published_times)*1000:.2f} ms",
                            flush=True,
                        )


if __name__ == "__main__":
    main()
