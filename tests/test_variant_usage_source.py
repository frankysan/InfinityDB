"""Parity and provenance tests for transient normalized variant-source materialization."""

from __future__ import annotations

import copy
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from infinity_db import variant_usage
from infinity_db.database import export_database, raw_database_path
from infinity_db.database.normalized_source import (
    verified_army_export_generation,
    verified_normalized_generation,
)
from infinity_db.database.schema import TABLES, quote
from infinity_db.variant_usage import (
    build_variant_usage_from_normalized,
    build_variant_usage_projection,
)
from infinity_db.variant_usage_reference import publication_from_candidate
from infinity_db.variant_usage_source import normalized_source_connection
from tests.test_database import _normalized_fixture_data


@pytest.fixture
def source_pair(tmp_path: Path) -> tuple[Path, Path, dict]:
    document = _normalized_fixture_data()
    document["_meta"]["snapshotArchiveSha256"] = "a" * 64
    army = tmp_path / "army.db"
    normalized = tmp_path / "normalized.json"
    export_database(document, army, finalize=False)
    normalized.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return army, normalized, document


def test_normalized_source_matches_every_raw_relational_table(
    source_pair: tuple[Path, Path, dict],
) -> None:
    army, normalized, _ = source_pair
    raw_path = raw_database_path(army)
    with (
        normalized_source_connection(army, normalized) as (source, generation),
        closing(sqlite3.connect(raw_path.resolve().as_uri() + "?mode=ro", uri=True)) as raw,
    ):
        exported_generation = json.loads(raw.execute(
            "SELECT value FROM __infinity_metadata WHERE key='export_pair_sha256'"
        ).fetchone()[0])
        assert generation == exported_generation
        for name, definition in TABLES.items():
            order = ", ".join(map(quote, definition.key))
            statement = f"SELECT * FROM {quote(name)} ORDER BY {order}"
            assert [tuple(row) for row in source.execute(statement)] == raw.execute(
                statement
            ).fetchall(), name
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            source.execute("DELETE FROM units")

    # Transient reads do not require or recreate a retained raw archive.
    raw_path.unlink()
    with normalized_source_connection(army, normalized) as (source, pinned):
        assert pinned == generation
        assert source.execute("SELECT COUNT(*) FROM units").fetchone()[0] > 0
    assert not raw_path.exists()


def test_overlay_source_requires_exactly_one_verified_input(
    source_pair: tuple[Path, Path, dict],
) -> None:
    army, normalized, _ = source_pair
    with normalized_source_connection(army, normalized) as (_source, generation):
        assert verified_normalized_generation(army, normalized) == generation
        assert verified_army_export_generation(army, None, normalized) == generation
        assert verified_army_export_generation(
            army, raw_database_path(army), None,
        ) == generation
    for raw, source in (
        (None, None),
        (raw_database_path(army), normalized),
    ):
        with pytest.raises(ValueError, match="exactly one"):
            verified_army_export_generation(army, raw, source)


@pytest.mark.parametrize("mutation", ("source-row", "source-metadata", "export-generation"))
def test_normalized_source_fails_closed_on_identity_drift(
    source_pair: tuple[Path, Path, dict], mutation: str,
) -> None:
    army, normalized, data = source_pair
    if mutation == "source-row":
        changed = copy.deepcopy(data)
        changed["tables"]["units"][0]["name"] = "altered"
        normalized.write_text(json.dumps(changed), encoding="utf-8")
    elif mutation == "source-metadata":
        changed = copy.deepcopy(data)
        changed["_meta"]["formatVersion"] = 99
        normalized.write_text(json.dumps(changed), encoding="utf-8")
    else:
        with closing(sqlite3.connect(army)) as connection, connection:
            connection.execute(
                "UPDATE __infinity_metadata SET value=? WHERE key='export_pair_sha256'",
                (json.dumps("0" * 64),),
            )
    with pytest.raises(ValueError):
        with normalized_source_connection(army, normalized):
            pytest.fail("Invalid normalized source was accepted")


def test_variant_usage_normalized_and_raw_publications_are_identical(
    source_pair: tuple[Path, Path, dict], monkeypatch: pytest.MonkeyPatch,
) -> None:
    army, normalized, _ = source_pair
    rules = army.with_name("rules_n5.db")
    with closing(sqlite3.connect(rules)) as connection, connection:
        connection.execute("CREATE TABLE marker (id)")

    monkeypatch.setattr(
        variant_usage.RulesDatabase, "deployed_objects_payload",
        lambda _self, _army: {"objects": [{"id": "test:object"}]},
    )
    mapping = {
        (catalog, 1): {
            "applicationItemId": 1,
            "rules": {
                "recordId": f"{'skill' if catalog == 'skills' else 'equipment'}:test",
                "collectionId": "test",
                "variant": {"source_variant": {"kind": "test", "value": 1}},
            },
        }
        for catalog in ("skills", "equipment")
    }
    monkeypatch.setattr(variant_usage, "_source_mapping", lambda *_: mapping)
    # This generic normalization fixture is not a reviewed variant-usage source.
    # Compare the transformation of its real source rows without asserting a
    # curated owner mapping; dedicated variant tests exercise that validation.
    def context(_application: sqlite3.Connection, row: dict, owner: str) -> dict:
        shared = owner == "unit_option"
        return {
            "ownerKind": owner,
            "sourceUnitId": row["unitId"],
            "applicationArmyId": None if shared else row["armyId"],
            "logicalUnitId": None if shared else row["unitId"],
            "payloadSha256": None if shared else "a" * 64,
            "contextPosition": row["position"],
        }

    monkeypatch.setattr(variant_usage, "_direct_context", context)
    monkeypatch.setattr(
        variant_usage, "_include_peripheral_provenance",
        lambda *_: {"policy": "context-only", "includes": [], "peripheralAttachments": []},
    )
    archived = build_variant_usage_projection(army, raw_database_path(army), rules)
    transient = build_variant_usage_from_normalized(army, normalized, rules)
    raw_database_path(army).unlink()
    without_archive = build_variant_usage_from_normalized(army, normalized, rules)

    assert publication_from_candidate(transient) == publication_from_candidate(archived)
    assert publication_from_candidate(without_archive) == publication_from_candidate(archived)
    assert transient["relationships"] == archived["relationships"]
    assert transient["diagnosticCounts"] == archived["diagnosticCounts"]
    assert transient["unresolvedSourceRows"] or transient["variants"]
    assert "rawDatabaseSha256" not in transient["sourceSnapshot"]
