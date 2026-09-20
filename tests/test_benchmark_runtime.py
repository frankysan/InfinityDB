from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

from infinity_db.database import Database
from infinity_db.database.schema import APPLICATION_ID, SCHEMA_VERSION
from tools.benchmark_runtime import _summary, discover_cases, main


class FakeDatabase:
    def list_armies(self):
        return [{"id": 101, "playable": True}]

    def list_units(self, **kwargs):
        return {"items": [{"id": 1, "name": "Test Unit"}]}

    def get_unit(self, unit_id: int):
        return {"id": unit_id}

    def list_catalog_items(self, catalog: str):
        return [{"id": {"skills": 11, "equipment": 21, "weapons": 31}[catalog]}]

    def get_skill(self, item_id: int):
        return {"id": item_id}

    def get_catalog_item(self, catalog: str, item_id: int):
        return {"catalog": catalog, "id": item_id}

    def list_traits(self):
        return [{"id": "continuous-damage"}]

    def get_trait(self, item_id: str):
        return {"id": item_id}


def test_summary_reports_median_and_nearest_rank_p95_in_milliseconds() -> None:
    summary = _summary([0.001, 0.002, 0.004, 0.008])

    assert summary == {
        "medianMs": 3.0,
        "p95Ms": 8.0,
        "meanMs": 3.75,
        "minMs": 1.0,
        "maxMs": 8.0,
    }


def test_discover_cases_covers_representative_runtime_paths() -> None:
    cases = discover_cases(cast(Database, FakeDatabase()))

    assert [case.name for case in cases] == [
        "armies",
        "units",
        "traits",
        "units-by-army",
        "unit-detail",
        "unit-search",
        "skills-catalog",
        "skills-detail",
        "equipment-catalog",
        "equipment-detail",
        "weapons-catalog",
        "weapons-detail",
        "trait-detail",
    ]

def test_main_reports_outdated_database_without_traceback(
    tmp_path: Path, capsys
) -> None:
    path = tmp_path / "outdated.db"
    with sqlite3.connect(path) as connection:
        connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION - 1}")

    assert main([str(path), "--cold-iterations", "1", "--warm-iterations", "1"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "ERROR: Unsupported InfinityDB database; rebuild it from normalized JSON\n"
    )
    assert "Traceback" not in captured.err
