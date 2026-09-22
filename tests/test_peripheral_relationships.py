from __future__ import annotations

import json
import sqlite3

from infinity_db.database.peripheral_relationships import (
    materialize_peripheral_relationships,
    validate_peripheral_relationships,
)
from infinity_db.database.schema import create_schema
from infinity_db.peripheral_identities import (
    PeripheralIdentityCurated,
    parse_peripheral_identity_curated,
    peripheral_identity_metadata,
)


def _curated() -> PeripheralIdentityCurated:
    return parse_peripheral_identity_curated(
        {
            "format": "InfinityDB curated Peripheral identities",
            "formatVersion": 3,
            "sources": [
                {
                    "id": "army-json-test",
                    "kind": "army-snapshot",
                    "artifact": "JSON test.zip",
                    "sha256": "a" * 64,
                    "acquiredAt": "2026-09-22T06:00:00+02:00",
                    "authority": "primary",
                }
            ],
            "entities": [],
            "profiles": [],
            "mappings": [],
            "unitMappings": [
                {
                    "id": "peripheral-unit-mapping:unit-30",
                    "sourceId": "army-json-test",
                    "unitId": 30,
                    "sourceName": "Cyberplug Peripheral",
                    "logicalUnitId": 30,
                    "typeId": "rule:peripheral-type:cyberplug",
                    "review": {
                        "status": "reviewed",
                        "reviewedOn": "2026-09-22",
                        "reason": "Reviewed synthetic Unit-backed identity.",
                    },
                }
            ],
            "controllerAccess": [
                {
                    "id": "peripheral-controller-access:army-101-unit-20-group-1-option-1",
                    "sourceId": "army-json-test",
                    "controllerKind": "loadout",
                    "armyId": 101,
                    "unitId": 20,
                    "groupId": 1,
                    "parentId": 1,
                    "sourceName": "Cyberplug Controller",
                    "typeId": "rule:peripheral-type:cyberplug",
                    "targetLogicalUnitIds": [30],
                    "relationship": "access-pool",
                    "review": {
                        "status": "reviewed",
                        "reviewedOn": "2026-09-22",
                        "reason": "Reviewed synthetic access pool.",
                    },
                }
            ],
        }
    )


def _connection() -> tuple[sqlite3.Connection, PeripheralIdentityCurated]:
    connection = sqlite3.connect(":memory:")
    create_schema(connection, {})
    curated = _curated()
    metadata = {
        "_meta": {"snapshotArchiveSha256": "a" * 64},
        **peripheral_identity_metadata(curated),
    }
    connection.executemany(
        "INSERT INTO __infinity_metadata (key, value) VALUES (?, ?)",
        [(key, json.dumps(value)) for key, value in metadata.items()],
    )
    connection.executemany(
        "INSERT INTO units (id, source_defined, name) VALUES (?, 1, ?)",
        [(20, "Controller"), (30, "Cyberplug Peripheral")],
    )
    connection.executemany(
        "INSERT INTO logical_units (id, representative_unit_id) VALUES (?, ?)",
        [(20, 20), (30, 30)],
    )
    connection.executemany(
        "INSERT INTO logical_unit_sources (source_unit_id, logical_unit_id) VALUES (?, ?)",
        [(20, 20), (30, 30)],
    )
    connection.execute("INSERT INTO army_lists (id) VALUES (101)")
    connection.executemany(
        "INSERT INTO army_units (army_id, unit_id) VALUES (101, ?)", [(20,), (30,)]
    )
    connection.execute(
        "INSERT INTO profile_groups (army_id, unit_id, group_id) VALUES (101, 30, 1)"
    )
    connection.execute(
        "INSERT INTO profiles (army_id, unit_id, group_id, profile_id, name) "
        "VALUES (101, 30, 1, 1, 'Cyberplug Peripheral')"
    )
    connection.execute(
        "INSERT INTO skills (id, name, source_defined) VALUES (243, 'Peripheral', 1)"
    )
    connection.execute("INSERT INTO skills (id, name, source_defined) VALUES (277, 'Cyberplug', 1)")
    connection.execute("INSERT INTO extras (id, name, source_defined) VALUES (374, 'Cyberplug', 1)")
    connection.execute(
        "INSERT INTO profile_skills "
        "(occurrence_id, army_id, unit_id, group_id, profile_id, position, item_id) "
        "VALUES (1, 101, 30, 1, 1, 1, 243)"
    )
    connection.execute(
        "INSERT INTO profile_skill_extras (occurrence_id, position, extra_id) VALUES (1, 1, 374)"
    )
    connection.execute(
        "INSERT INTO profile_groups (army_id, unit_id, group_id) VALUES (101, 20, 1)"
    )
    connection.execute(
        "INSERT INTO loadout_options "
        "(army_id, unit_id, group_id, option_id, name) "
        "VALUES (101, 20, 1, 1, 'Cyberplug Controller')"
    )
    connection.execute(
        "INSERT INTO option_skills "
        "(occurrence_id, army_id, unit_id, group_id, option_id, position, item_id) "
        "VALUES (2, 101, 20, 1, 1, 1, 277)"
    )
    return connection, curated


def test_materialize_peripheral_controller_access_pool() -> None:
    connection, curated = _connection()
    try:
        materialize_peripheral_relationships(connection, curated)
        assert connection.execute(
            "SELECT source_unit_id, logical_unit_id, type_id "
            "FROM application_peripheral_unit_sources"
        ).fetchall() == [(30, 30, "rule:peripheral-type:cyberplug")]
        assert connection.execute(
            "SELECT army_id, unit_id, group_id, parent_id, relationship "
            "FROM application_peripheral_controller_access"
        ).fetchall() == [(101, 20, 1, 1, "access-pool")]
        assert connection.execute(
            "SELECT access_id, target_logical_unit_id "
            "FROM application_peripheral_controller_targets"
        ).fetchall() == [
            (
                "peripheral-controller-access:army-101-unit-20-group-1-option-1",
                30,
            )
        ]
        validate_peripheral_relationships(connection)
    finally:
        connection.close()
