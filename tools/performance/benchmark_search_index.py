"""Measure canonical search composition against its compact SQLite projection."""

from __future__ import annotations

import argparse
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from statistics import median
from time import perf_counter

from infinity_db.database_set import SEASON_DATABASE_SOURCES
from infinity_db.search_index_storage import query_search_index, stage_search_index
from infinity_db.web.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    seasons = {
        season: args.db_dir / filename
        for season, (filename, _) in SEASON_DATABASE_SOURCES.items()
    }

    def app():
        return create_app(
            args.db_dir / "army.db", args.db_dir / "rules_n5.db",
            season_databases=seasons,
        )

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "search.db"
        catalog = app().api.search_catalog
        started = perf_counter()
        entries = list(catalog.entries())
        with closing(sqlite3.connect(path)) as db, db:
            stage_search_index(db, entries)
        print(
            f"Projection: {len(entries)} entries, "
            f"{sum(len(terms) for _, terms in entries)} terms, "
            f"{path.stat().st_size:,} bytes, {perf_counter()-started:.3f}s build"
        )
        for query in ("mimetism", "activate console", "Dragões", "a", "no-such-result-987654"):
            startup, cold, warm, indexed_cold, indexed_warm = [], [], [], [], []
            for _ in range(args.iterations):
                started = perf_counter()
                catalog = app().api.search_catalog
                startup.append(perf_counter() - started)

                def indexed(catalog=catalog, query=query):
                    if catalog.published_search is not None:
                        return catalog.search(query)
                    with closing(sqlite3.connect(path)) as db:
                        return query_search_index(db, query)

                started = perf_counter()
                actual = indexed()
                indexed_cold.append(perf_counter() - started)
                started = perf_counter()
                assert indexed() == actual
                indexed_warm.append(perf_counter() - started)
                started = perf_counter()
                expected = catalog.search_composed(query)
                cold.append(perf_counter() - started)
                assert actual == expected
                started = perf_counter()
                assert catalog.search_composed(query) == expected
                warm.append(perf_counter() - started)
            print(
                f"{query!r}: {len(expected)} matches; "
                f"startup {median(startup)*1000:.2f}ms; "
                f"legacy cold/repeat {median(cold)*1000:.2f}/{median(warm)*1000:.2f}ms; "
                f"index cold/repeat {median(indexed_cold)*1000:.2f}/"
                f"{median(indexed_warm)*1000:.2f}ms"
            )


if __name__ == "__main__":
    main()
