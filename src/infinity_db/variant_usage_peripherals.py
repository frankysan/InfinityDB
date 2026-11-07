"""Source-verified Peripheral context; never transfer rules to a Controller."""

from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import closing
from typing import Any

from infinity_db.database.peripheral_relationships import (
    PERIPHERAL_APPLICATION_TABLES,
    validate_peripheral_relationships,
)
from infinity_db.database.schema import quote


def _copy_table(
    destination: sqlite3.Connection, source: sqlite3.Connection, table: str,
) -> None:
    """Reconstitute only the existing validator's inputs, without changing either DB."""
    columns = [row[1] for row in source.execute(f"PRAGMA table_info({quote(table)})")]
    if not columns:
        raise ValueError(f"Missing Peripheral evidence table: {table}")
    fields = ", ".join(map(quote, columns))
    destination.execute(f"CREATE TABLE {quote(table)} ({fields})")
    destination.executemany(
        f"INSERT INTO {quote(table)} VALUES ({','.join('?' for _ in columns)})",
        source.execute(f"SELECT {fields} FROM {quote(table)}"),
    )


def _context(
    application: sqlite3.Connection, raw: sqlite3.Connection,
    kind: str, army: int, unit: int, group: int, parent: int,
) -> dict[str, Any]:
    prefix = "profile" if kind == "profile" else "loadout"
    identity = "profile_id" if kind == "profile" else "option_id"
    source_table = "profiles" if kind == "profile" else "loadout_options"
    key = (army, unit, group, parent)
    source = raw.execute(
        f"SELECT 1 FROM {source_table} WHERE army_id=? AND unit_id=? "
        f"AND group_id=? AND {identity}=?", key,
    ).fetchall()
    published = application.execute(
        "SELECT a.application_army_id, l.logical_unit_id, p.payload_sha256 "
        f"FROM {prefix}_payload_occurrences AS o "
        f"JOIN {prefix}_payloads AS p ON p.id=o.{prefix}_payload_id "
        "JOIN application_army_sources AS a ON a.source_army_id=o.army_id "
        "JOIN army_units AS u ON u.army_id=o.army_id AND u.unit_id=o.unit_id "
        "JOIN logical_unit_sources AS l ON l.source_unit_id=o.unit_id "
        "AND l.logical_unit_id=p.logical_unit_id "
        f"WHERE o.army_id=? AND o.unit_id=? AND o.group_id=? AND o.{identity}=?", key,
    ).fetchall()
    if len(source) != 1 or len(published) != 1:
        raise ValueError(f"Missing or ambiguous Peripheral source context: {kind}/{key}")
    return {
        "ownerKind": kind, "sourceArmyId": army, "sourceUnitId": unit,
        "groupId": group, "parentId": parent,
        "applicationArmyId": published[0][0], "logicalUnitId": published[0][1],
        "payloadSha256": published[0][2],
    }


def build_peripheral_provenance(
    application: sqlite3.Connection, raw: sqlite3.Connection,
) -> dict[str, Any]:
    """Validate the existing reviewed contract against independent raw source evidence."""
    with closing(sqlite3.connect(":memory:")) as evidence:
        for table in (
            "peripherals", "profile_peripherals", "option_peripherals", "units",
            "army_units", "profiles", "profile_skills", "skills", "profile_skill_extras",
            "extras", "loadout_options", "option_skills",
        ):
            _copy_table(evidence, raw, table)
        for table in (
            "__infinity_metadata", "logical_unit_sources",
            "application_peripheral_source_labels", *PERIPHERAL_APPLICATION_TABLES,
        ):
            _copy_table(evidence, application, table)
        validate_peripheral_relationships(evidence)

    attachments = []
    for kind in ("profile", "option"):
        table = f"{kind}_peripherals"
        source_rows = raw.execute(f"SELECT * FROM {table} ORDER BY occurrence_id").fetchall()
        published_rows = application.execute(f"SELECT * FROM {table}").fetchall()
        if Counter(map(tuple, source_rows)) != Counter(map(tuple, published_rows)):
            raise ValueError(f"Peripheral source/published attachments differ: {kind}")
        for row in source_rows:
            item = dict(row)
            parent = item["profile_id" if kind == "profile" else "option_id"]
            attachments.append({
                "source": item,
                "context": _context(application, raw, kind, item["army_id"],
                                    item["unit_id"], item["group_id"], parent),
            })

    edges = []
    for row in application.execute(
        "SELECT a.*, t.target_logical_unit_id "
        "FROM application_peripheral_controller_access AS a "
        "JOIN application_peripheral_controller_targets AS t ON t.access_id=a.id "
        "ORDER BY a.id, t.target_logical_unit_id"
    ):
        controller = _context(application, raw, row["controller_kind"], row["army_id"],
                              row["unit_id"], row["group_id"], row["parent_id"])
        targets = []
        for target in application.execute(
            "SELECT o.unit_id, o.group_id, o.profile_id "
            "FROM application_peripheral_unit_sources AS s "
            "JOIN profile_payload_occurrences AS o ON o.unit_id=s.source_unit_id "
            "WHERE s.logical_unit_id=? AND s.type_id=? AND o.army_id=? "
            "ORDER BY o.unit_id, o.group_id, o.profile_id",
            (row["target_logical_unit_id"], row["type_id"], row["army_id"]),
        ):
            targets.append(_context(application, raw, "profile", row["army_id"], *target))
        if not targets:
            raise ValueError("Missing Peripheral target source context")
        edges.append({**dict(row), "controllerContext": controller, "targetContexts": targets})
    return {"peripheralAttachments": attachments, "peripheralControllerEdges": edges}
