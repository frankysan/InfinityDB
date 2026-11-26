"""Parity and integrity of the generated current Rules read model."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from time import perf_counter

import pytest

from infinity_db.rules_database import RulesDatabase

RELEASE = Path("data/generated/rules_n5.db")


@pytest.fixture(scope="module")
def legacy(tmp_path_factory: pytest.TempPathFactory) -> RulesDatabase:
    path = tmp_path_factory.mktemp("rules-v17") / "rules_n5.db"
    shutil.copyfile(RELEASE, path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("DROP TABLE IF EXISTS catalog_details")
        db.execute("DROP TABLE IF EXISTS catalog_usage_units")
        db.execute("DROP TABLE IF EXISTS catalog_summaries")
        db.execute("DELETE FROM __rules_metadata WHERE key='catalogProjectionSha256'")
        db.execute("DROP TABLE IF EXISTS search_index_terms")
        db.execute("DROP TABLE IF EXISTS search_index")
        db.execute("DELETE FROM __rules_metadata WHERE key='searchIndex'")
        db.execute("DROP TABLE composed_rule_records")
        db.execute("DELETE FROM __rules_metadata WHERE key='composedRecordsSha256'")
        db.execute("PRAGMA user_version=17")
        db.execute("UPDATE __rules_metadata SET value='17' WHERE key='formatVersion'")
        db.execute(
            "UPDATE __rules_metadata SET value='19' WHERE key='databaseCompatibilityVersion'"
        )
    result = RulesDatabase(path)
    result.validate()
    return result


def test_every_current_selection_matches_legacy(legacy: RulesDatabase) -> None:
    published = RulesDatabase(RELEASE)
    published.validate()
    with closing(sqlite3.connect(RELEASE)) as db:
        rows = db.execute(
            "SELECT r.id,r.kind,r.scope_json FROM records r "
            "JOIN collections c ON c.id=r.collection_id WHERE c.status='current'"
        ).fetchall()
        count = db.execute("SELECT COUNT(*) FROM composed_rule_records").fetchone()[0]
    selections = {(record_id, None) for record_id, _, _ in rows}
    selections.update(
        (record_id, context)
        for record_id, _, scope in rows
        for context in (json.loads(scope or "null") or {}).get("scenarios", [])
    )
    for record_id, context in sorted(selections, key=lambda item: (item[0], item[1] or "")):
        for linked in (False, True):
            kwargs = {"scenario_id": context, "include_army_links": linked}
            assert published.composed_record(record_id, **kwargs) == legacy.composed_record(
                record_id, **kwargs
            ), (record_id, context, linked)
    kinds = sorted({kind for _, kind, _ in rows})
    timings = []
    for reader in (legacy, published):
        started = perf_counter()
        for kind in kinds:
            reader.composed_records_by_kind(kind, include_army_links=True)
        timings.append(perf_counter() - started)
    for kind in kinds:
        for linked in (False, True):
            assert published.composed_records_by_kind(
                kind, include_army_links=linked
            ) == legacy.composed_records_by_kind(kind, include_army_links=linked), kind
    assert published.composed_record("rule:not-a-real-record") is None
    print(
        f"Rules: {count} published rows; {len(selections)} current selections; "
        f"{len(kinds)} kinds"
    )
    print(f"Linked kind sweep: legacy {timings[0]:.3f}s; published {timings[1]:.3f}s")


def test_reverse_lookup_parity(legacy: RulesDatabase) -> None:
    published = RulesDatabase(RELEASE)
    with closing(sqlite3.connect(RELEASE)) as db:
        links = db.execute(
            "SELECT DISTINCT l.entity,l.external_id FROM record_army_links l "
            "JOIN collections c ON c.id=l.collection_id WHERE c.status='current' "
            "AND l.external_id IS NOT NULL ORDER BY l.entity,l.external_id"
        ).fetchall()
        labels = db.execute(
            "SELECT DISTINCT l.id FROM labels l JOIN collections c ON c.id=l.collection_id "
            "WHERE c.status='current' ORDER BY l.id"
        ).fetchall()
    for entity, external_id in links:
        assert published.composed_records_for_army_link(
            entity, external_id
        ) == legacy.composed_records_for_army_link(entity, external_id)
    for (label_id,) in labels:
        assert published.composed_records_using_label(
            label_id
        ) == legacy.composed_records_using_label(label_id)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("DELETE FROM composed_rule_records", "selection coverage"),
        ("UPDATE composed_rule_records SET body='{}'", "content fingerprint"),
    ],
)
def test_corrupt_publication_fails_closed(tmp_path: Path, mutation: str, message: str) -> None:
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(RELEASE, path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match=message):
        RulesDatabase(path).validate()
