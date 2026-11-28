"""Compare canonical maintained-text resolution with compact prepared targets."""
from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from statistics import median
from time import perf_counter

from infinity_db.database.repository import Database
from infinity_db.maintained_text_references import (
    _enrich_rule_record,
    _Resolver,
    collect_reference_targets,
)
from infinity_db.rules_database import RulesDatabase


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    database = Database(args.db_dir / "army.db")
    rules = RulesDatabase(args.db_dir / "rules_n5.db", immutable_snapshot=True)
    start = perf_counter()
    targets = collect_reference_targets(database, rules)
    elapsed = perf_counter() - start
    body = json.dumps(targets, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    print(
        f"targets={len(targets['records'])}; "
        f"selections={sum(map(len, targets['records'].values()))}; "
        f"properties={len(targets['properties'])}; "
        f"bytes={len(body.encode('utf-8')):,}; build={elapsed:.3f} s",
        flush=True,
    )
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "pilot.db"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE targets (body TEXT)")
            db.execute("INSERT INTO targets VALUES (?)", (body,))
        start = perf_counter()
        with closing(sqlite3.connect(path)) as db:
            targets = json.loads(db.execute("SELECT body FROM targets").fetchone()[0])
        print(f"SQLite bytes={path.stat().st_size:,}; read={(perf_counter()-start)*1000:.2f} ms")
    with rules._connect() as db:
        rows = [(context, json.loads(raw)) for context, raw in db.execute(
            "SELECT scenario_id,body FROM composed_rule_records ORDER BY record_id,scenario_id"
        )]
    canonical_times, prepared_times = [], []
    failed = []
    for context, record in rows:
        scenario_id = record["id"] if record["kind"] == "scenario" else context or None
        kwargs = {"scenario_id": scenario_id, "local_rule_ids": frozenset({record["id"]})}
        expected, actual = deepcopy(record), deepcopy(record)
        start = perf_counter()
        try:
            _enrich_rule_record(expected, _Resolver(database, rules, **kwargs))
        except ValueError as exc:
            failed.append((record["id"], str(exc)))
            continue
        canonical_times.append(perf_counter() - start)
        start = perf_counter()
        _enrich_rule_record(actual, _Resolver(database, rules, reference_targets=targets, **kwargs))
        prepared_times.append(perf_counter() - start)
        assert expected == actual, (record["id"], context)
    print(
        f"parity={len(canonical_times)}; skipped canonical errors={len(failed)}; "
        f"canonical median={median(canonical_times)*1000:.2f} ms; "
        f"prepared median={median(prepared_times)*1000:.2f} ms; "
        f"aggregate canonical={sum(canonical_times):.3f} s; "
        f"prepared={sum(prepared_times):.3f} s",
        flush=True,
    )
    for error in failed[:5]:
        print(error)


if __name__ == "__main__":
    main()
