"""Exercise the disposable projection's selection and payload storage."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from infinity_db.web.app import Application
from tools.performance import benchmark_general_profiles as pilot


def test_all_availability_masks_are_distinct() -> None:
    combinations = {pilot._flags(mask) for mask in range(16)}
    assert len(combinations) == 16
    assert pilot._flags(0) == frozenset()
    assert pilot._flags(15) == frozenset({"mercs", "specops", "teamops", "reinforcement"})


def test_projection_deduplicates_payloads_and_preserves_requested_order(
    tmp_path: Path, monkeypatch,
) -> None:
    def present(unit, *, optional_filters, general_only):
        assert general_only
        return [{"unit": unit["id"], "mercs": optional_filters["mercs"]}]

    monkeypatch.setattr(pilot, "extended_general_profiles", lambda result: result)
    app = cast(Application, SimpleNamespace(
        database=SimpleNamespace(get_unit=lambda unit_id: {"id": unit_id}),
        api=SimpleNamespace(_present_unit=present),
    ))
    path = tmp_path / "projection.db"
    expected = pilot._build_projection(app, path, [1, 2])
    assert len(expected) == 32
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT COUNT(*) FROM selection").fetchone() == (32,)
        assert db.execute("SELECT COUNT(*) FROM payload").fetchone() == (4,)
    assert pilot._read_batch(path, [2, 1, 2], 15) == [
        [{"unit": 2, "mercs": True}],
        [{"unit": 1, "mercs": True}],
        [{"unit": 2, "mercs": True}],
    ]
    assert pilot._read_batch(path, [1], 0) == [[{"unit": 1, "mercs": False}]]
    with pytest.raises(ValueError, match="Incomplete materialized selection"):
        pilot._read_batch(path, [3], 0)
