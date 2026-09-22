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
    identity_metadata,
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


def test_export_prefers_identity_policy_pinned_in_normalized_data(tmp_path: Path) -> None:
    document = load_identity_config().document
    document["units"]["groups"].append(
        {
            "canonical_id": 41,
            "source_ids": [41, 42],
            "reason": "Test-only normalized provenance",
        }
    )
    config = parse_identity_config(document)
    data = normalized_empty()
    data.update(identity_metadata(config))
    path = tmp_path / "infinity.db"

    export_database(data, path)

    for database_path in (path, raw_database_path(path)):
        assert metadata_value(database_path, IDENTITY_CONFIG_METADATA_KEY) == config.document
        assert (
            metadata_value(database_path, IDENTITY_CONFIG_SHA256_METADATA_KEY)
            == config.content_sha256
        )


def test_export_rejects_explicit_identity_policy_mismatch(tmp_path: Path) -> None:
    pinned = load_identity_config()
    document = pinned.document
    document["units"]["groups"].append(
        {
            "canonical_id": 41,
            "source_ids": [41, 42],
            "reason": "Test-only mismatched policy",
        }
    )
    explicit = parse_identity_config(document)
    data = normalized_empty()
    data.update(identity_metadata(pinned))
    path = tmp_path / "infinity.db"

    with pytest.raises(ValueError, match="does not match the policy pinned"):
        export_database(data, path, identity_config=explicit)

    assert not path.exists()


def test_export_rejects_incomplete_normalized_identity_metadata(tmp_path: Path) -> None:
    data = normalized_empty()
    data[IDENTITY_CONFIG_METADATA_KEY] = load_identity_config().document

    with pytest.raises(ValueError, match="incomplete identity configuration metadata"):
        export_database(data, tmp_path / "infinity.db")


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


def test_application_army_materialization_resolves_reviewed_source_aliases(
    tmp_path: Path,
) -> None:
    data = normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyMetadata": {
                "sourceFile": "metadata.json",
                "sourceSha256": "test-metadata",
                "data": {
                    "factions": [
                        {
                            "id": 998,
                            "parent": 998,
                            "name": "Source Alias",
                            "slug": "source-alias",
                        },
                        {
                            "id": 999,
                            "parent": 999,
                            "name": "Canonical Army",
                            "slug": "canonical-army",
                        },
                    ]
                },
            },
            "armyLists": {
                "998": {
                    "_meta": {"slug": "source-alias", "kind": "army"},
                    "unitIds": [1],
                },
                "999": {
                    "_meta": {"slug": "canonical-army", "kind": "army"},
                    "unitIds": [1],
                },
            },
            "units": {
                "1": {
                    "shared": {
                        "id": 1,
                        "name": "Alias Test Unit",
                        "canonical": 999,
                        "factions": [998, 999],
                    },
                    "byArmy": {"998": {}, "999": {}},
                }
            },
        }
    )
    path = tmp_path / "infinity.db"

    export_database(data, path)

    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        armies = [
            dict(row)
            for row in connection.execute(
                "SELECT id, name, slug, role, playable, group_id, preferred_source_id "
                "FROM application_armies ORDER BY id"
            )
        ]
        sources = [
            dict(row)
            for row in connection.execute(
                "SELECT application_army_id, source_army_id, has_army_list, has_metadata "
                "FROM application_army_sources ORDER BY source_army_id"
            )
        ]

    assert armies == [
        {
            "id": 999,
            "name": "Canonical Army",
            "slug": "canonical-army",
            "role": "main",
            "playable": 1,
            "group_id": None,
            "preferred_source_id": 999,
        }
    ]
    assert sources == [
        {
            "application_army_id": 999,
            "source_army_id": 998,
            "has_army_list": 1,
            "has_metadata": 1,
        },
        {
            "application_army_id": 999,
            "source_army_id": 999,
            "has_army_list": 1,
            "has_metadata": 1,
        },
    ]

    database = Database(path)
    assert [army["id"] for army in database.list_armies()] == [999]
    alias_page = database.list_units(army_id=998)
    canonical_page = database.list_units(army_id=999)
    assert alias_page == canonical_page
    assert alias_page["total"] == 1
    assert alias_page["items"][0]["army_ids"] == [999]
    assert alias_page["items"][0]["armies"] == [{"id": 999, "name": "Canonical Army"}]


def test_database_validation_rejects_tampered_application_army_materialization(
    tmp_path: Path,
) -> None:
    path = tmp_path / "infinity.db"
    export_database(normalized_two_units(), path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE application_armies SET name = ? WHERE id = ?",
            ("Tampered Army", 101),
        )
        connection.commit()

    with pytest.raises(ValueError, match="published application content"):
        Database(path).validate()
