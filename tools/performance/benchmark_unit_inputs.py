"""Measure canonical Unit input construction against a compact SQLite projection."""
from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import tracemalloc
from contextlib import closing
from functools import partial
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.unit_input_storage import (
    decode_contexts,
    encode_contexts,
    read_filter_contexts,
    stage_filter_contexts,
)


def encode_graph(graph: dict[str, Any]) -> str:
    groups = [
        {
            **group,
            "armies": list(group["armies"].items()),
            "army_occurrences": [
                {**occurrence, "_required_flags": sorted(occurrence["_required_flags"])}
                for occurrence in group["army_occurrences"]
            ],
            "declared_faction_ids": sorted(group["declared_faction_ids"]),
            "search_terms": sorted(
                group["search_terms"], key=lambda value: (value is not None, value),
            ),
        }
        for group in graph["groups"]
    ]
    return json.dumps({
        "rows": [dict(row) for row in graph["rows"]],
        "army_names": sorted(graph["army_names"].items()),
        "declared_faction_ids_by_unit": [
            (source, sorted(ids)) for source, ids in sorted(
                graph["declared_faction_ids_by_unit"].items()
            )
        ],
        "groups": groups,
    }, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def decode_graph(body: str) -> dict[str, Any]:
    graph = json.loads(body)
    graph["army_names"] = dict(graph["army_names"])
    graph["declared_faction_ids_by_unit"] = {
        source: set(ids) for source, ids in graph["declared_faction_ids_by_unit"]
    }
    for group in graph["groups"]:
        group["armies"] = dict(group["armies"])
        for occurrence in group["army_occurrences"]:
            occurrence["_required_flags"] = frozenset(occurrence["_required_flags"])
        group["declared_faction_ids"] = set(group["declared_faction_ids"])
        group["search_terms"] = set(group["search_terms"])
    graph["groups_by_source"] = {
        source: group for group in graph["groups"] for source in group["source_ids"]
    }
    return graph


def measure(callback, *, memory: bool = False) -> tuple[Any, float, int]:
    if memory:
        tracemalloc.start()
    start = perf_counter()
    try:
        result = callback()
        seconds = perf_counter() - start
        peak = tracemalloc.get_traced_memory()[1] if memory else 0
        return result, seconds, peak
    finally:
        if memory:
            tracemalloc.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army", type=Path, default=Path("data/generated/army.db"))
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    database = Database(args.army)
    graph = encode_graph(database._unit_graph())
    contexts = encode_contexts(database._compose_scoped_unit_filter_contexts())
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "inputs.db"
        with closing(sqlite3.connect(path)) as db, db:
            stage_filter_contexts(db, contexts)
            db.execute("CREATE TABLE graph (body TEXT NOT NULL)")
            db.execute("INSERT INTO graph VALUES (?)", (graph,))
        print(
            f"graph={len(graph.encode('utf-8')):,} bytes, "
            f"contexts={len(contexts.encode('utf-8')):,} bytes, "
            f"database={path.stat().st_size:,} bytes",
            flush=True,
        )

        def read(kind, decode):
            with closing(sqlite3.connect(path)) as db:
                if kind == "contexts":
                    return read_filter_contexts(db)
                return decode(db.execute("SELECT body FROM graph").fetchone()[0])

        for kind, method, encode, decode in (
            ("graph", "_unit_graph", encode_graph, decode_graph),
            ("contexts", "_compose_scoped_unit_filter_contexts", encode_contexts, decode_contexts),
        ):
            old_times, new_times = [], []
            for _ in range(args.iterations):
                baseline = Database(args.army)
                expected, old, _ = measure(getattr(baseline, method))
                actual, new, _ = measure(partial(read, kind, decode))
                assert encode(actual) == encode(expected)
                old_times.append(old)
                new_times.append(new)
            _, _, old_peak = measure(getattr(Database(args.army), method), memory=True)
            _, _, new_peak = measure(partial(read, kind, decode), memory=True)
            print(
                f"{kind}: canonical {median(old_times)*1000:.2f} ms; "
                f"projected {median(new_times)*1000:.2f} ms; "
                f"peak allocations {old_peak:,}/{new_peak:,} bytes",
                flush=True,
            )


if __name__ == "__main__":
    main()
