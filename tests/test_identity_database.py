from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infinity_army_data.normalize import normalize_master
from infinity_db.database import Database, export_database, raw_database_path
from infinity_db.database.schema import METADATA_TABLE, quote
from infinity_db.identities import (
    IDENTITY_CONFIG_METADATA_KEY,
    IDENTITY_CONFIG_SHA256_METADATA_KEY,
    load_identity_config,
    parse_identity_config,
)


def normalized_empty() -> dict:
    return normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyMetadata": {
                "sourceFile": "metadata.json",
                "sourceSha256": "test-metadata",
                "data": {"factions": []},
            },
            "armyLists": {},
            "units": {},
        }
    )


def normalized_two_units() -> dict:
    return normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyMetadata": {
                "sourceFile": "metadata.json",
                "sourceSha256": "test-metadata",
                "data": {"factions": []},
            },
            "armyLists": {
                "101": {
                    "_meta": {"slug": "first", "kind": "faction"},
                    "unitIds": [1],
                },
                "201": {
                    "_meta": {"slug": "second", "kind": "faction"},
                    "unitIds": [2],
                },
            },
            "units": {
                "1": {
                    "shared": {
                        "id": 1,
                        "name": "First identity",
                        "isc": "First identity",
                        "canonical": 101,
                        "factions": [101],
                    },
                    "byArmy": {"101": {}},
                },
                "2": {
                    "shared": {
                        "id": 2,
                        "name": "Second identity",
                        "isc": "Second identity",
                        "canonical": 201,
                        "factions": [201],
                    },
                    "byArmy": {"201": {}},
                },
            },
        }
    )


def metadata_value(path: Path, key: str) -> object:
    connection = sqlite3.connect(path)
    try:
        row = connection.execute(
            f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?", (key,)
        ).fetchone()
        assert row is not None
        return json.loads(row[0])
    finally:
        connection.close()


def test_export_pins_identity_manifest_and_hash_in_both_database_siblings(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    config = load_identity_config()

    export_database(normalized_empty(), path)

    for database_path in (path, raw_database_path(path)):
        assert metadata_value(database_path, IDENTITY_CONFIG_METADATA_KEY) == config.document
        assert (
            metadata_value(database_path, IDENTITY_CONFIG_SHA256_METADATA_KEY)
            == config.content_sha256
        )


def test_database_validation_rejects_tampered_identity_metadata(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    export_database(normalized_empty(), path)

    connection = sqlite3.connect(path)
    try:
        connection.execute(
            f"UPDATE {quote(METADATA_TABLE)} SET value = ? WHERE key = ?",
            (json.dumps("0" * 64), IDENTITY_CONFIG_SHA256_METADATA_KEY),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="identity configuration metadata"):
        Database(path).validate()


def test_repository_uses_identity_policy_pinned_into_database(tmp_path: Path) -> None:
    document = load_identity_config().document
    document["units"]["groups"].append(
        {
            "canonical_id": 1,
            "source_ids": [1, 2],
            "reason": "Test-only group proving the database snapshot owns identity policy",
        }
    )
    config = parse_identity_config(document)
    path = tmp_path / "infinity.db"

    export_database(normalized_two_units(), path, identity_config=config)

    database = Database(path)
    database.validate()
    page = database.list_units()
    assert page["total"] == 1
    assert page["items"][0]["id"] == 1
    assert page["items"][0]["source_ids"] == [1, 2]
    assert page["items"][0]["army_ids"] == [101, 201]
