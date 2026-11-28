"""Measure canonical search composition against its compact SQLite projection."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from statistics import median
from time import perf_counter
from urllib.parse import urlencode

from infinity_db.database.repository import accent_insensitive_key
from infinity_db.database_set import SEASON_DATABASE_SOURCES
from infinity_db.search_index_storage import query_search_index, stage_search_index
from infinity_db.web.app import create_app
from tools.browser_wsgi_transport import wsgi_response


def benchmark_prefixes(db_dir: Path, iterations: int) -> None:
    """Compare bounded live suggestions to full search on one published database."""
    path = db_dir / "rules_n5.db"
    seasons = {
        season: db_dir / filename
        for season, (filename, _) in SEASON_DATABASE_SOURCES.items()
    }
    app = create_app(db_dir / "army.db", path, season_databases=seasons)
    assert app.api.search_catalog.published_search is not None
    limit = 8

    def search(query: str, *, sql_limit: bool):
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if not sql_limit:
                return query_search_index(db, query)[:limit]
            # Preserve Python's Unicode normalization, casefold and stable position tie.
            db.create_function("accent_key", 1, accent_insensitive_key, deterministic=True)
            db.create_function("casefold", 1, str.casefold, deterministic=True)
            needle = accent_insensitive_key(query)
            if not needle:
                return []
            return [json.loads(row[0]) for row in db.execute(
                """SELECT result FROM search_index WHERE position IN
                (SELECT position FROM search_index_terms WHERE instr(term,?)>0)
                ORDER BY
                    instr(accent_key(json_extract(result,'$.name')),?) != 1,
                    casefold(json_extract(result,'$.name')),
                    json_extract(result,'$.domain'), position
                LIMIT ?""",
                (needle, needle, limit),
            )]

    for query in ("a", "ar", "in", "co", "ra", "an", "re", "mi", "MSV", "Dragões", "zzzz"):
        full = app.api.search_catalog.search(query)
        expected = full[:limit]
        times: dict[str, list[float]] = {"index": [], "sql limit": [], "API": []}
        route = "http://localhost/api/search?" + urlencode({"q": query, "limit": limit})
        for iteration in range(iterations):
            for candidate in (False, True) if iteration % 2 == 0 else (True, False):
                started = perf_counter()
                actual = search(query, sql_limit=candidate)
                times["sql limit" if candidate else "index"].append(perf_counter() - started)
                assert actual == expected, query
            started = perf_counter()
            status, _, body = wsgi_response(app, route)
            times["API"].append(perf_counter() - started)
            assert status == 200 and json.loads(body)["items"] == expected, query
        metrics = "; ".join(
            f"{name} {median(samples)*1000:.3f} ms" for name, samples in times.items()
        )
        print(f"{query!r}: {len(full)} matches; {metrics}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--prefixes", action="store_true", help="Compare bounded live search.")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    if args.prefixes:
        benchmark_prefixes(args.db_dir, args.iterations)
        return
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
