"""Published scoped filter input parity and corruption checks."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from infinity_db.database.repository import Database
from infinity_db.unit_input_storage import SCOPES, encode_contexts, read_filter_contexts

ARMY = Path("data/generated/army.db")


def test_published_contexts_match_every_source_occurrence() -> None:
    database = Database(ARMY)
    expected = database._compose_scoped_unit_filter_contexts()
    with closing(sqlite3.connect(ARMY)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] >= 34
        assert read_filter_contexts(db) == expected
        assert db.execute("SELECT body FROM unit_filter_contexts").fetchone()[0] == (
            encode_contexts(expected)
        )
    actual = database._scoped_unit_filter_contexts()
    assert actual == expected
    assert all(actual[scope] for scope in SCOPES)
    print("Published context counts:", {scope: len(rows) for scope, rows in actual.items()})


def test_all_scopes_preserve_dynamic_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    projected = Database(ARMY)
    canonical = Database(ARMY)
    contexts = canonical._compose_scoped_unit_filter_contexts()
    monkeypatch.setattr(canonical, "_scoped_unit_filter_contexts", lambda: contexts)
    cases = (
        {},
        {"skill_id": ("berserk", "engineer"), "and_filters": ("skill",)},
        {"skill_id": ("berserk", "engineer"), "and_filters": ()},
        {"equipment_id": "medikit", "points_min": 15, "points_max": 35},
        {"weapon_id": "combi-rifle", "swc_max": 1.0, "ava_min": 2},
        {"skill_id": "hacker", "army_id": "nomads", "limit": 5, "offset": 2},
        {"search": "Dragões", "mercs": True, "specops": True,
         "teamops": True, "reinforcement": True},
        {"skill_id": "no-such-skill-xyz", "specops": True},
    )
    for scope in SCOPES:
        for case in cases:
            args = {
                "matching_scope": scope, "limit": 10,
                "include_usage_counts": True, "include_raw_usage_counts": False,
                **case,
            }
            assert projected.list_units(**args) == canonical.list_units(**args), (scope, case)


@pytest.mark.parametrize("mutation, message", [
    ("DELETE FROM unit_filter_contexts", "Unit filter context projection"),
    ("UPDATE unit_filter_contexts SET body='not json'", "Unit filter context projection"),
    ("UPDATE unit_filter_contexts SET body='{}'", "published application content"),
    ("DROP TABLE unit_filter_contexts", "Incomplete database schema"),
])
def test_damaged_projection_fails_closed(tmp_path: Path, mutation: str, message: str) -> None:
    path = tmp_path / "army.db"
    shutil.copyfile(ARMY, path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match=message):
        Database(path).validate()
