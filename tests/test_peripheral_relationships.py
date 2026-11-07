from __future__ import annotations

import json
import sqlite3

import pytest

from infinity_db.database.peripheral_relationships import (
    materialize_peripheral_relationships,
    materialize_peripheral_source_labels,
    validate_peripheral_relationships,
    validate_peripheral_source_labels,
)
from infinity_db.database.schema import create_schema
from infinity_db.peripheral_identities import (
    PeripheralIdentityCurated,
    parse_peripheral_identity_curated,
    peripheral_identity_metadata,
)
from infinity_db.variant_usage_peripherals import build_peripheral_provenance


def _usage_connection(kind: str = "loadout") -> sqlite3.Connection:
    connection, curated = _connection()
    connection.row_factory = sqlite3.Row
    if kind == "profile":
        document = curated.document
        access = document["controllerAccess"][0]
        access["controllerKind"] = "profile"
        connection.execute(
            "INSERT INTO profiles (army_id,unit_id,group_id,profile_id,name) "
            "VALUES (101,20,1,1,'Cyberplug Controller')"
        )
        connection.execute(
            "INSERT INTO profile_skills "
            "(occurrence_id,army_id,unit_id,group_id,profile_id,position,item_id) "
            "VALUES (2,101,20,1,1,1,277)"
        )
        curated = parse_peripheral_identity_curated(document)
        for key, value in peripheral_identity_metadata(curated).items():
            connection.execute("UPDATE __infinity_metadata SET value=? WHERE key=?",
                               (json.dumps(value), key))
    materialize_peripheral_relationships(connection, curated)
    connection.execute(
        "INSERT INTO application_army_sources (source_army_id,application_army_id) "
        "VALUES (101,10)"
    )
    prefix = "profile" if kind == "profile" else "loadout"
    identity = "profile_id" if kind == "profile" else "option_id"
    connection.execute(
        f"INSERT INTO {prefix}_payloads (id,logical_unit_id,payload_sha256) "
        "VALUES (20,20,'controller')"
    )
    connection.execute(
        f"INSERT INTO {prefix}_payload_occurrences "
        f"(army_id,unit_id,group_id,{identity},{prefix}_payload_id) VALUES (101,20,1,1,20)"
    )
    connection.execute(
        "INSERT INTO profile_payloads (id,logical_unit_id,payload_sha256) "
        "VALUES (30,30,'peripheral')"
    )
    connection.execute(
        "INSERT INTO profile_payload_occurrences "
        "(army_id,unit_id,group_id,profile_id,profile_payload_id) VALUES (101,30,1,1,30)"
    )
    return connection


@pytest.mark.parametrize("kind", ["profile", "loadout"])
def test_variant_peripheral_reviewed_pool_preserves_independent_owner_contexts(kind: str) -> None:
    connection = _usage_connection(kind)
    try:
        result = build_peripheral_provenance(connection, connection)
        edge, = result["peripheralControllerEdges"]
        assert edge["relationship"] == "access-pool"
        assert edge["controllerContext"]["logicalUnitId"] == 20
        assert edge["controllerContext"]["ownerKind"] == kind
        target, = edge["targetContexts"]
        assert target["logicalUnitId"] == 30
        assert target["sourceArmyId"] == 101
        assert target["payloadSha256"] == "peripheral"
        assert "skills" not in edge and "sourceRows" not in edge
        assert result["peripheralAttachments"] == []
    finally:
        connection.close()


@pytest.mark.parametrize("mutation", [
    "DELETE FROM __infinity_metadata WHERE key LIKE 'peripheralIdentity%'",
    "UPDATE application_peripheral_controller_targets SET target_logical_unit_id=20",
    "DELETE FROM application_peripheral_controller_targets",
    "UPDATE application_peripheral_unit_sources SET type_id='rule:peripheral-type:servant'",
    "UPDATE application_peripheral_controller_access SET source_id='other'",
    "DELETE FROM profile_skills WHERE unit_id=30",
    "DELETE FROM army_units WHERE unit_id=30",
    "DELETE FROM loadout_payload_occurrences WHERE unit_id=20",
    "DELETE FROM profile_payload_occurrences WHERE unit_id=30",
    "UPDATE profile_payload_occurrences SET army_id=102 WHERE unit_id=30",
    "UPDATE profile_payloads SET logical_unit_id=20 WHERE id=30",
    "DELETE FROM application_army_sources",
])
def test_variant_peripheral_unreviewed_or_drifted_relationships_fail_closed(mutation: str) -> None:
    connection = _usage_connection()
    try:
        connection.execute(mutation)
        with pytest.raises(ValueError):
            build_peripheral_provenance(connection, connection)
    finally:
        connection.close()


def test_variant_peripheral_duplicate_published_context_fails_closed() -> None:
    connection = _usage_connection()
    try:
        connection.execute(
            "CREATE TABLE bad_rows AS SELECT * FROM profile_payload_occurrences"
        )
        connection.execute("DROP TABLE profile_payload_occurrences")
        connection.execute("ALTER TABLE bad_rows RENAME TO profile_payload_occurrences")
        connection.execute(
            "INSERT INTO profile_payload_occurrences "
            "SELECT * FROM profile_payload_occurrences WHERE unit_id=30"
        )
        with pytest.raises(ValueError, match="ambiguous Peripheral source context"):
            build_peripheral_provenance(connection, connection)
    finally:
        connection.close()


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


def test_source_only_peripheral_labels_preserve_army_names_without_inferred_types() -> None:
    connection, _ = _connection()
    try:
        connection.executemany(
            "INSERT INTO peripherals (army_id, id, name) VALUES (?, ?, ?)",
            [(101, 7, "Servant Bot"), (101, 8, "Auxiliary Drone")],
        )
        connection.execute(
            "INSERT INTO profile_peripherals "
            "(occurrence_id, army_id, unit_id, group_id, profile_id, position, item_id, quantity) "
            "VALUES (1, 101, 30, 1, 1, 1, 7, 2)"
        )
        connection.execute(
            "INSERT INTO option_peripherals "
            "(occurrence_id, army_id, unit_id, group_id, option_id, position, item_id, quantity) "
            "VALUES (2, 101, 20, 1, 1, 1, 8, 3)"
        )
        materialize_peripheral_source_labels(connection)
        assert connection.execute(
            "SELECT army_id, peripheral_id, source_name "
            "FROM application_peripheral_source_labels ORDER BY peripheral_id"
        ).fetchall() == [
            (101, 7, "Servant Bot"), (101, 8, "Auxiliary Drone"),
        ]
        assert connection.execute(
            "SELECT COUNT(*) FROM application_peripheral_entities"
        ).fetchone()[0] == 0
        validate_peripheral_source_labels(connection)
        connection.execute(
            "UPDATE application_peripheral_source_labels SET source_name = 'Wrong' "
            "WHERE peripheral_id = 7"
        )
        import pytest

        with pytest.raises(ValueError, match="drifted"):
            validate_peripheral_source_labels(connection)
    finally:
        connection.close()


def test_source_peripheral_attachment_without_definition_fails_publication() -> None:
    import pytest

    connection, _ = _connection()
    try:
        connection.execute(
            "INSERT INTO option_peripherals "
            "(occurrence_id, army_id, unit_id, group_id, option_id, position, item_id) "
            "VALUES (1, 101, 20, 1, 1, 1, 999)"
        )
        with pytest.raises(ValueError, match="missing a source name"):
            materialize_peripheral_source_labels(connection)
    finally:
        connection.close()


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
