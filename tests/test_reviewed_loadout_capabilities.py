"""Reviewed, snapshot-pinned source omissions on exact loadout occurrences."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from infinity_db.database.reviewed_loadout_capabilities import (
    load_reviewed_capabilities,
    materialize_reviewed_loadout_capabilities,
)

SNAPSHOT, FACTS, SHA = load_reviewed_capabilities()


def connection() -> sqlite3.Connection:
    database = sqlite3.connect(":memory:")
    database.executescript("""
        CREATE TABLE loadout_payloads (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE loadout_payload_occurrences (
            army_id INTEGER, unit_id INTEGER, group_id INTEGER,
            option_id INTEGER, loadout_payload_id INTEGER
        );
        CREATE TABLE loadout_payload_equipment (loadout_payload_id INTEGER, item_id INTEGER);
        CREATE TABLE skills (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE equipment (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE weapons (id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO equipment VALUES (63, 'Repeater'), (111, 'Deployable Repeater');
        INSERT INTO loadout_payloads VALUES
            (601, 'KISS! (Repeater)'), (604, 'KISS! (Repeater)'),
            (605, 'KISS! (Repeater)'), (700, 'KISS!');
        INSERT INTO loadout_payload_occurrences VALUES
            (601,965,2,3,601), (604,965,2,3,604), (605,965,2,3,605),
            (601,965,2,1,700);
        INSERT INTO loadout_payload_equipment VALUES (700, 111);
    """)
    return database


def test_reviewed_kiss_repeater_facts_are_snapshot_bound_and_loadout_owned() -> None:
    assert len(FACTS) == 3
    assert {fact["armyId"] for fact in FACTS} == {601, 604, 605}
    assert {fact["itemId"] for fact in FACTS} == {63}
    assert {fact["loadoutName"] for fact in FACTS} == {"KISS! (Repeater)"}
    with connection() as database:
        metadata: dict[str, Any] = {"_meta": {"snapshotArchiveSha256": SNAPSHOT}}
        materialize_reviewed_loadout_capabilities(database, metadata)
        rows = metadata["reviewedLoadoutCapabilities"]
        assert [
            (row["army_id"], row["unit_id"], row["group_id"],
             row["option_id"], row["catalog"], row["item_id"]) for row in rows
        ] == [(army, 965, 2, 3, "equipment", 63) for army in (601, 604, 605)]
        assert metadata["reviewedLoadoutCapabilitiesSha256"] == SHA
        assert metadata["reviewedLoadoutCapabilitiesCount"] == 3
        assert database.execute(
            "SELECT item_id FROM loadout_payload_equipment WHERE loadout_payload_id=700"
        ).fetchone()[0] == 111


def test_reviewed_capabilities_do_not_apply_to_other_army_snapshot() -> None:
    with connection() as database:
        metadata = {"_meta": {"snapshotArchiveSha256": "0" * 64}}
        materialize_reviewed_loadout_capabilities(database, metadata)
        assert "reviewedLoadoutCapabilities" not in metadata
        assert "reviewedLoadoutCapabilitiesSha256" not in metadata


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        ("UPDATE loadout_payloads SET name = 'Changed' WHERE id = 601", "renamed"),
        ("UPDATE equipment SET name = 'Wrong' WHERE id = 63", "renamed"),
        ("INSERT INTO loadout_payload_equipment VALUES (601, 63)", "duplicates"),
        ("DELETE FROM loadout_payload_occurrences WHERE army_id = 601", "missing"),
    ],
)
def test_reviewed_capabilities_refuse_stale_facts(
    statement: str, message: str,
) -> None:
    with connection() as database:
        database.execute(statement)
        with pytest.raises(ValueError, match=message):
            materialize_reviewed_loadout_capabilities(
                database, {"_meta": {"snapshotArchiveSha256": SNAPSHOT}}
            )


def test_reviewed_capability_config_rejects_unreviewed_and_duplicate_facts(
    tmp_path: Path,
) -> None:
    original = json.loads(Path(
        "data/curated/relationships/loadout-capabilities.json"
    ).read_text(encoding="utf-8"))
    path = tmp_path / "capabilities.json"
    original["facts"].append(dict(original["facts"][0]))
    path.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_reviewed_capabilities(path)
    original["facts"].pop()
    original["facts"][0]["review"]["status"] = "unreviewed"
    path.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="review evidence"):
        load_reviewed_capabilities(path)


def test_published_kiss_repeater_filter_and_detail() -> None:
    from infinity_db.database import Database

    database = Database(Path("data/generated/army.db"))
    detail = database.get_unit(965)
    assert detail is not None
    kisses = [
        loadout for army in detail["armies"] for loadout in army["loadouts"]
        if loadout["name"] == "KISS! (Repeater)"
    ]
    assert kisses
    assert all(
        any(item["id"] == 63 for item in loadout["equipment"])
        for loadout in kisses
    )
    assert all(
        not any(item["id"] == 111 for item in loadout["equipment"])
        for loadout in kisses
    )
    catalog = database.get_catalog_item("equipment", "repeater")
    assert catalog is not None
    assert 965 in {
        unit["id"] for variant in catalog["variants"] for unit in variant["units"]
    }
    source_uses = {
        (unit["id"], tuple(extra["id"] for extra in variant["extras"]))
        for variant in catalog["variants"] for unit in variant["units"]
    }
    repeater_item = next(
        item for item in database.list_catalog_items("equipment")
        if item["id"] == catalog["id"]
    )
    # Catalogue list counts omit some optional Unit types; detail links include all.
    displayed_unit_ids = {
        unit["id"] for unit in database._visible_unit_items_by_source(
            frozenset({"specops"})
        ).values()
    }
    assert 965 in displayed_unit_ids
    assert repeater_item["use_count"] == len({
        source_use for source_use in source_uses
        if source_use[0] in displayed_unit_ids
    })
    repeater_id = database.application_catalog_id("equipment", "repeater")
    assert repeater_id is not None
    for scope, expected in (("profile", False), ("loadout", True), ("unit", True)):
        result = database.list_units(
            skill_id="hacker", equipment_id="repeater", matching_scope=scope,
            _unbounded=True,
        )
        assert (965 in {item["id"] for item in result["items"]}) is expected
        baseline = database.list_units(
            skill_id="hacker", matching_scope=scope, include_usage_counts=True,
        )
        assert baseline["prospective_counts"]["equipment"].get(
            str(repeater_id), 0
        ) == result["total"]
