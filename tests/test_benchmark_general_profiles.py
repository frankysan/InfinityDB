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


@pytest.mark.parametrize("mask", range(16))
def test_published_mask_contract_matches_prototype(mask: int) -> None:
    from infinity_db.general_profile_storage import availability_mask, flags_for_mask

    assert availability_mask(pilot._flags(mask)) == mask
    assert {flag for flag, enabled in flags_for_mask(mask).items() if enabled} == pilot._flags(mask)


@pytest.mark.parametrize("mutation, message", [
    ("DELETE FROM general_profile_selections WHERE mask=0", "selection matrix"),
    ("UPDATE general_profile_payloads SET body='[]'", "published application content"),
])
def test_published_projection_rejects_corrupt_content(
    tmp_path: Path, mutation: str, message: str,
) -> None:
    import shutil

    from infinity_db.database import Database

    path = tmp_path / "army.db"
    shutil.copyfile(Path("data/generated/army.db"), path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match=message):
        Database(path).validate()


def test_legacy_schema_and_empty_batch_are_distinct(tmp_path: Path) -> None:
    import json
    import shutil

    from infinity_db.database import Database
    from infinity_db.database.publication import published_content_sha256
    from infinity_db.symbol_path_storage import ARMY_V31_PUBLISHED_TABLES

    path = tmp_path / "army.db"
    shutil.copyfile(Path("data/generated/army.db"), path)
    assert Database(path).general_profiles([], frozenset()) == {}
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("DROP TABLE general_profile_selections")
        db.execute("DROP TABLE general_profile_payloads")
        db.execute("PRAGMA user_version=31")
        db.execute(
            "UPDATE __infinity_metadata SET value='40' WHERE key='database_compatibility_version'"
        )
        db.execute(
            "UPDATE __infinity_metadata SET value=? WHERE key='published_content_sha256'",
            (json.dumps(published_content_sha256(db, definitions=ARMY_V31_PUBLISHED_TABLES)),),
        )
    legacy = Database(path)
    legacy.validate()
    assert legacy.general_profiles([], frozenset()) is None
