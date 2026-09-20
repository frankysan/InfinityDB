from __future__ import annotations

from typing import cast

from infinity_db.database import Database
from tools.benchmark_runtime import _summary, discover_cases


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
