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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    parser.add_argument("--samples", type=int, default=50)
    args = parser.parse_args()
    app = create_app_from_database_set(args.db_dir)
    api = app.api
    database = app.database
    assert app.rules_database is not None
    ids = sorted(group["id"] for group in database._unit_graph()["groups"])
    if args.samples < 1:
        parser.error("--samples must be positive")
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
