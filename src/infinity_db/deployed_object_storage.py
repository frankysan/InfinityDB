"""Normalized, source-pinned deployed-object storage and build/read validation.

Cross-database Army references are tied to the exact Army database fingerprint,
never inferred at runtime. The shared model guard validates source identity,
attribute evidence, reviewed delivery edges and exact Unit/Include ownership.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

DEPLOYED_OBJECT_SCHEMA_VERSION = 10
DEPLOYED_OBJECT_COMPATIBILITY_VERSION = 12

_SCHEMA = (
    """CREATE TABLE deployed_object_metadata (
        key TEXT PRIMARY KEY, value TEXT NOT NULL
    )""",
    """CREATE TABLE deployed_objects (
        id TEXT PRIMARY KEY, name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('model-or-token', 'trooper-profile', 'scenery')),
        origin_rule_id TEXT, source_profile_json TEXT
    )""",
    """CREATE TABLE deployed_object_attributes (
        object_id TEXT NOT NULL REFERENCES deployed_objects(id),
        attribute TEXT NOT NULL CHECK (attribute IN ('ARM','BTS','STR','S')),
        status TEXT NOT NULL CHECK (status IN ('known','unreported','disputed')),
        value TEXT,
        PRIMARY KEY (object_id, attribute)
    )""",
    """CREATE TABLE deployed_object_attribute_sources (
        object_id TEXT NOT NULL, attribute TEXT NOT NULL,
        position INTEGER NOT NULL CHECK (position >= 0),
        value TEXT NOT NULL, source_json TEXT NOT NULL,
        PRIMARY KEY (object_id, attribute, position),
        FOREIGN KEY (object_id, attribute)
            REFERENCES deployed_object_attributes(object_id, attribute)
    )""",
    """CREATE TABLE deployed_object_deliveries (
        object_id TEXT NOT NULL REFERENCES deployed_objects(id),
        position INTEGER NOT NULL CHECK (position >= 0),
        record_id TEXT NOT NULL, method TEXT NOT NULL,
        source_pages_json TEXT NOT NULL,
        PRIMARY KEY (object_id, position),
        UNIQUE (object_id, record_id, method)
    )""",
    """CREATE TABLE deployed_object_unit_uses (
        object_id TEXT NOT NULL REFERENCES deployed_objects(id),
        position INTEGER NOT NULL CHECK (position >= 0),
        delivery_position INTEGER NOT NULL,
        kind TEXT NOT NULL,
        army_id INTEGER, army_name TEXT,
        unit_id INTEGER NOT NULL, unit_name TEXT NOT NULL, unit_slug TEXT NOT NULL,
        group_id INTEGER, profile_id INTEGER, option_id INTEGER,
        context_name TEXT NOT NULL,
        source_item_id INTEGER NOT NULL, source_position INTEGER NOT NULL,
        include_position INTEGER, target_army_id INTEGER, target_army_name TEXT,
        target_loadout_payload_id INTEGER, target_name TEXT,
        PRIMARY KEY (object_id, position),
        FOREIGN KEY (object_id, delivery_position)
            REFERENCES deployed_object_deliveries(object_id, position)
    )""",
    """CREATE INDEX deployed_object_uses_unit
        ON deployed_object_unit_uses(unit_id, kind)""",
    """CREATE TABLE deployed_object_unresolved (
        position INTEGER PRIMARY KEY CHECK (position >= 0),
        origin_record_id TEXT NOT NULL,
        delivery TEXT NOT NULL, reason TEXT NOT NULL
    )""",
)

_USE_FIELDS = (
    "kind", "armyId", "armyName", "unitId", "unitName", "unitSlug",
    "groupId", "profileId", "optionId", "contextName", "sourceItemId",
    "sourcePosition", "includePosition", "targetArmyId", "targetArmyName",
    "targetLoadoutPayloadId", "targetName",
)
_USE_COLUMNS = (
    "kind", "army_id", "army_name", "unit_id", "unit_name", "unit_slug",
    "group_id", "profile_id", "option_id", "context_name", "source_item_id",
    "source_position", "include_position", "target_army_id", "target_army_name",
    "target_loadout_payload_id", "target_name",
)
_OPTIONAL_USE_FIELDS = (
    "includePosition", "targetArmyId", "targetArmyName",
    "targetLoadoutPayloadId", "targetName",
)


def _encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validate_model(document: dict[str, Any]) -> None:
    """Validate the shared build/read model without a loose-file publication."""
    snapshot = document.get("sourceSnapshot")
    if (
        document.get("formatVersion") != 1
        or document.get("scope") != "reviewed-projection-not-complete-unit-usage"
        or not isinstance(document.get("objects"), list)
        or not isinstance(document.get("unresolvedDeliveries"), list)
        or not isinstance(snapshot, dict)
        or "rulesDatabaseSha256" in snapshot
        or any(not isinstance(snapshot.get(key), str) or len(snapshot[key]) != 64
               for key in ("armyDatabaseSha256", "curatedSourceSha256",
                           "deliveryReviewSha256", "candidateReviewSha256"))
    ):
        raise ValueError("Invalid deployed-object model or source provenance")
    identifiers: set[str] = set()
    source_keys: set[tuple[str, int, str | None]] = set()
    for entry in document["objects"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid deployed-object entry")
        identifier = entry.get("id")
        if (
            not isinstance(identifier, str) or not identifier
            or identifier in identifiers
            or not isinstance(entry.get("name"), str)
            or not isinstance(entry.get("deliverySources"), list)
        ):
            raise ValueError("Invalid/duplicate deployed-object identity")
        identifiers.add(identifier)
        source = entry.get("sourceProfile")
        if source is not None:
            if (
                not isinstance(source, dict)
                or source.get("catalog") not in {"weapon", "equipment"}
                or type(source.get("sourceId")) is not int
                or source["sourceId"] <= 0
                or (source.get("mode") is not None and not isinstance(source["mode"], str))
            ):
                raise ValueError("Invalid deployed-object Army source selector")
            key = (source["catalog"], source["sourceId"], source["mode"])
            if key in source_keys:
                raise ValueError("Duplicate deployed-object Army source selector")
            source_keys.add(key)
        attrs = entry.get("attributes")
        if not isinstance(attrs, dict) or set(attrs) != {"ARM", "BTS", "STR", "S"}:
            raise ValueError("Incomplete deployed-object attribute contract")
        for attribute in attrs.values():
            if not isinstance(attribute, dict):
                raise ValueError("Invalid deployed-object attribute")
            status = attribute.get("status")
            value = attribute.get("value")
            evidence = attribute.get("provenance")
            if (
                status not in {"known", "unreported", "disputed"}
                or not isinstance(evidence, list)
            ):
                raise ValueError("Invalid deployed-object attribute status")
            if status == "unreported":
                if value is not None or evidence:
                    raise ValueError("Unreported attribute cannot invent a value")
            elif (
                not isinstance(value, str)
                or len(evidence) != (2 if status == "disputed" else 1)
                or any(not isinstance(row, dict) or not row.get("source") for row in evidence)
            ):
                raise ValueError("Deployed-object attribute missing source provenance")
        reviewed_edges: set[tuple[str, str]] = set()
        for delivery in entry["deliverySources"]:
            if (
                not isinstance(delivery, dict)
                or not isinstance(delivery.get("recordId"), str)
                or not isinstance(delivery.get("method"), str)
                or not isinstance(delivery.get("sourcePages"), list)
            ):
                raise ValueError("Invalid reviewed delivery edge")
            reviewed_edges.add((delivery["recordId"], delivery["method"]))
        uses = entry.get("unitUses")
        if not isinstance(uses, list):
            raise ValueError("Missing or invalid deployed-object Unit usage collection")
        for use in uses:
            if (
                not isinstance(use, dict)
                or (use.get("originRecordId"), use.get("method")) not in reviewed_edges
                or use.get("kind") not in {
                    "profile", "loadout", "unit-option",
                    "profile-include", "loadout-include", "unit-option-include",
                }
                or any(type(use.get(key)) is not int for key in (
                    "unitId", "sourceItemId", "sourcePosition"
                ))
                or any(not isinstance(use.get(key), str) or not use[key]
                       for key in ("unitName", "unitSlug", "contextName"))
            ):
                raise ValueError("Invalid or unreviewed deployed-object Unit usage")
            if use["kind"] in {"unit-option", "unit-option-include"}:
                if (
                    use.get("armyId") is not None or use.get("armyName") is not None
                    or use.get("groupId") is not None
                    or use.get("profileId") is not None
                    or type(use.get("optionId")) is not int
                ):
                    raise ValueError("Unit-wide option cannot invent Army or group ownership")
                if use["kind"] == "unit-option-include" and (
                    type(use.get("includePosition")) is not int
                    or type(use.get("targetArmyId")) is not int
                    or not isinstance(use.get("targetArmyName"), str)
                    or not use["targetArmyName"]
                    or type(use.get("targetLoadoutPayloadId")) is not int
                    or not isinstance(use.get("targetName"), str)
                    or not use["targetName"]
                ):
                    raise ValueError("Invalid Unit-option Include target provenance")
            else:
                kind = use["kind"].removesuffix("-include")
                identity_key = "profileId" if kind == "profile" else "optionId"
                other_key = "optionId" if kind == "profile" else "profileId"
                if (
                    type(use.get("armyId")) is not int
                    or type(use.get("groupId")) is not int
                    or not isinstance(use.get("armyName"), str)
                    or not use["armyName"]
                    or type(use.get(identity_key)) is not int
                    or use.get(other_key) is not None
                ):
                    raise ValueError("Invalid deployed-object profile/loadout usage context")
                if use["kind"].endswith("-include") and (
                    type(use.get("includePosition")) is not int
                    or type(use.get("targetLoadoutPayloadId")) is not int
                    or not isinstance(use.get("targetName"), str)
                    or not use["targetName"]
                ):
                    raise ValueError("Invalid deployed-object Include provenance")


def stage_deployed_objects(connection: sqlite3.Connection, document: dict[str, Any]) -> None:
    """Insert the reviewed read model as relational rows in an open build transaction."""
    _validate_model(document)
    snapshot = document["sourceSnapshot"]
    for statement in _SCHEMA:
        connection.execute(statement)

    metadata = {
        "formatVersion": 1,
        "scope": document["scope"],
        **snapshot,
    }
    connection.executemany(
        "INSERT INTO deployed_object_metadata (key, value) VALUES (?, ?)",
        [(key, _encode(value)) for key, value in sorted(metadata.items())],
    )
    for obj in document["objects"]:
        identifier = obj["id"]
        connection.execute(
            "INSERT INTO deployed_objects "
            "(id,name,type,origin_rule_id,source_profile_json) VALUES (?,?,?,?,?)",
            (identifier, obj["name"], obj["type"], obj["originRuleId"],
             _encode(obj["sourceProfile"]) if obj["sourceProfile"] is not None else None),
        )
        for attribute in ("ARM", "BTS", "STR", "S"):
            item = obj["attributes"][attribute]
            connection.execute(
                "INSERT INTO deployed_object_attributes "
                "(object_id,attribute,status,value) VALUES (?,?,?,?)",
                (identifier, attribute, item["status"], item["value"]),
            )
            for pos, evidence in enumerate(item["provenance"]):
                connection.execute(
                    "INSERT INTO deployed_object_attribute_sources "
                    "(object_id,attribute,position,value,source_json) VALUES (?,?,?,?,?)",
                    (identifier, attribute, pos, evidence["value"],
                     _encode(evidence["source"])),
                )
        delivery_indices = {}
        for pos, edge in enumerate(obj["deliverySources"]):
            connection.execute(
                "INSERT INTO deployed_object_deliveries "
                "(object_id,position,record_id,method,source_pages_json) "
                "VALUES (?,?,?,?,?)",
                (identifier, pos, edge["recordId"], edge["method"],
                 _encode(edge["sourcePages"])),
            )
            delivery_indices[(edge["recordId"], edge["method"])] = pos
        placeholders = ",".join("?" for _ in range(3 + len(_USE_COLUMNS)))
        names = ",".join(("object_id", "position", "delivery_position", *_USE_COLUMNS))
        for pos, use in enumerate(obj["unitUses"]):
            edge = (use["originRecordId"], use["method"])
            if edge not in delivery_indices:
                raise ValueError("Unit use lacks a reviewed deployed-object delivery")
            connection.execute(
                f"INSERT INTO deployed_object_unit_uses ({names}) VALUES ({placeholders})",
                (identifier, pos, delivery_indices[edge],
                 *(use.get(key) for key in _USE_FIELDS)),
            )
    for pos, item in enumerate(document["unresolvedDeliveries"]):
        connection.execute(
            "INSERT INTO deployed_object_unresolved "
            "(position,origin_record_id,delivery,reason) VALUES (?,?,?,?)",
            (pos, item["originRecordId"], item["delivery"], item["reason"]),
        )


def validate_deployed_object_snapshot(connection: sqlite3.Connection) -> None:
    """Validate the normalized v10 snapshot without loading the Army database."""
    required_tables = {
        "deployed_object_metadata", "deployed_objects",
        "deployed_object_attributes", "deployed_object_attribute_sources",
        "deployed_object_deliveries", "deployed_object_unit_uses",
        "deployed_object_unresolved",
    }
    actual_tables = {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if not required_tables <= actual_tables:
        raise ValueError("Incomplete normalized deployed-object schema")
    metadata = {
        key: json.loads(value)
        for key, value in connection.execute(
            "SELECT key,value FROM deployed_object_metadata"
        )
    }
    if (
        metadata.get("formatVersion") != 1
        or metadata.get("scope") != "reviewed-projection-not-complete-unit-usage"
        or "rulesDatabaseSha256" in metadata
        or any(
            not isinstance(metadata.get(key), str)
            or len(metadata[key]) != 64
            for key in (
                "armyDatabaseSha256", "curatedSourceSha256",
                "deliveryReviewSha256", "candidateReviewSha256",
            )
        )
    ):
        raise ValueError("Invalid normalized deployed-object provenance")
    count = connection.execute("SELECT COUNT(*) FROM deployed_objects").fetchone()[0]
    if count == 0:
        raise ValueError("Empty normalized deployed-object snapshot")
    if connection.execute(
        "SELECT COUNT(*) FROM deployed_object_attributes"
    ).fetchone()[0] != 4 * count:
        raise ValueError("Incomplete normalized deployed-object attributes")
    if connection.execute(
        "SELECT 1 FROM deployed_object_attributes AS a "
        "WHERE (a.status = 'unreported' AND (a.value IS NOT NULL OR EXISTS ("
        " SELECT 1 FROM deployed_object_attribute_sources AS s"
        " WHERE s.object_id = a.object_id AND s.attribute = a.attribute))) "
        "OR (a.status <> 'unreported' AND (a.value IS NULL OR ("
        " SELECT COUNT(*) FROM deployed_object_attribute_sources AS s"
        " WHERE s.object_id = a.object_id AND s.attribute = a.attribute)"
        " <> CASE WHEN a.status = 'disputed' THEN 2 ELSE 1 END)) LIMIT 1"
    ).fetchone():
        raise ValueError("Invalid normalized deployed-object attribute provenance")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("Invalid normalized deployed-object relationships")


def read_deployed_objects(
    connection: sqlite3.Connection, army_database: Path,
) -> dict[str, Any]:
    """Reconstruct the stable API projection, rejecting stale Army pairings."""
    rows = connection.execute("SELECT key,value FROM deployed_object_metadata").fetchall()
    metadata = {key: json.loads(value) for key, value in rows}
    with army_database.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if metadata.get("armyDatabaseSha256") != digest:
        raise ValueError("Deployed objects do not match the Army database")
    if metadata.get("scope") != "reviewed-projection-not-complete-unit-usage":
        raise ValueError("Unsupported deployed-object scope")

    objects = []
    for identifier, name, type_, origin_rule_id, profile_json in connection.execute(
        "SELECT id,name,type,origin_rule_id,source_profile_json "
        "FROM deployed_objects ORDER BY id"
    ):
        attributes = {}
        for attribute, status, value in connection.execute(
            "SELECT attribute,status,value FROM deployed_object_attributes "
            "WHERE object_id = ? ORDER BY attribute", (identifier,)
        ):
            provenance = [
                {"value": val, "source": json.loads(source)}
                for val, source in connection.execute(
                    "SELECT value,source_json FROM deployed_object_attribute_sources "
                    "WHERE object_id = ? AND attribute = ? ORDER BY position",
                    (identifier, attribute),
                )
            ]
            attributes[attribute] = {
                "status": status, "value": value, "provenance": provenance,
            }
        if set(attributes) != {"ARM", "BTS", "STR", "S"}:
            raise ValueError("Incomplete deployed-object attributes")
        deliveries = [
            {
                "recordId": record_id, "method": method,
                "sourcePages": json.loads(source_pages),
            }
            for record_id, method, source_pages in connection.execute(
                "SELECT record_id,method,source_pages_json "
                "FROM deployed_object_deliveries WHERE object_id = ? ORDER BY position",
                (identifier,),
            )
        ]
        uses = []
        query = ("SELECT d.record_id,d.method," + ",".join(
            f"u.{column}" for column in _USE_COLUMNS
        ) + " FROM deployed_object_unit_uses AS u "
             "JOIN deployed_object_deliveries AS d "
             "ON d.object_id = u.object_id AND d.position = u.delivery_position "
             "WHERE u.object_id = ? ORDER BY u.position")
        for row in connection.execute(query, (identifier,)):
            use = {"originRecordId": row[0], "method": row[1]}
            use.update(zip(_USE_FIELDS, row[2:], strict=True))
            for field in _OPTIONAL_USE_FIELDS:
                if use[field] is None:
                    del use[field]
            uses.append(use)
        objects.append({
            "id": identifier, "name": name, "type": type_,
            "originRuleId": origin_rule_id,
            "sourceProfile": json.loads(profile_json) if profile_json is not None else None,
            "attributes": attributes, "deliverySources": deliveries, "unitUses": uses,
        })
    unresolved = [
        {"originRecordId": origin, "delivery": delivery, "reason": reason}
        for origin, delivery, reason in connection.execute(
            "SELECT origin_record_id,delivery,reason "
            "FROM deployed_object_unresolved ORDER BY position"
        )
    ]
    snapshot = {
        key: value for key, value in metadata.items()
        if key not in ("scope", "formatVersion")
    }
    document = {
        "formatVersion": metadata["formatVersion"],
        "scope": metadata["scope"],
        "sourceSnapshot": snapshot,
        "objects": objects,
        "unresolvedDeliveries": unresolved,
    }
    _validate_model(document)
    return document
