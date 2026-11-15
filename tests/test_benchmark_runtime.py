from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

from infinity_db.database import Database
from infinity_db.database.schema import APPLICATION_ID, SCHEMA_VERSION
from tools.performance.benchmark_runtime import _summary, discover_cases, main


class FakeDatabase:
    def __init__(self) -> None:
        self.unit_queries: list[dict] = []

    def list_armies(self):
        return [{"id": 101, "playable": True}]

    def list_units(self, **kwargs):
        self.unit_queries.append(kwargs)
        return {"items": [{"id": 1, "name": "Test Unit"}]}

    def get_unit(self, unit_id: int):
        return {"id": unit_id}

    def list_catalog_items(self, catalog: str):
        if catalog == "skills":
            return [
                {"id": 11, "slug": "berserk", "use_count": 2},
                {"id": 12, "slug": "engineer", "use_count": 1},
            ]
        return [{"id": {"equipment": 21, "weapons": 31}[catalog]}]

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
    fake = FakeDatabase()
    cases = discover_cases(cast(Database, fake))

    assert [case.name for case in cases] == [
        "armies",
        "units",
        "units-counts",
        "units-counts-numeric",
        "traits",
        "units-by-army",
        "units-counts-by-army",
        "unit-detail",
        "unit-search",
        "skills-catalog",
        "units-counts-multiselect",
        "units-scoped-profile-counts",
        "units-scoped-loadout-counts",
        "units-scoped-unit-counts",
        "units-scoped-loadout-numeric-counts",
        "units-scoped-profile-after-index",
        "units-scoped-loadout-after-index",
        "units-scoped-unit-after-index",
        "skills-detail",
        "equipment-catalog",
        "equipment-detail",
        "weapons-catalog",
        "weapons-detail",
        "trait-detail",
    ]

    by_name = {case.name: case for case in cases}
    for scope in ("profile", "loadout", "unit"):
        by_name[f"units-scoped-{scope}-counts"].action(cast(Database, fake))
        assert fake.unit_queries[-1] == {
            "skill_id": (11, 12),
            "and_filters": ("skill",),
            "matching_scope": scope,
            "limit": 50,
            "include_usage_counts": True,
        }
        interaction = by_name[f"units-scoped-{scope}-after-index"]
        assert interaction.setup is not None
        interaction.setup(cast(Database, fake))
        assert fake.unit_queries[-1] == {
            "skill_id": 11,
            "matching_scope": scope,
            "limit": 50,
            "include_usage_counts": True,
        }
        interaction.action(cast(Database, fake))
        assert fake.unit_queries[-1]["skill_id"] == (11, 12)

    by_name["units-scoped-loadout-numeric-counts"].action(cast(Database, fake))
    assert fake.unit_queries[-1]["points_min"] == 10
    assert fake.unit_queries[-1]["points_max"] == 35
    assert fake.unit_queries[-1]["matching_scope"] == "loadout"


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
