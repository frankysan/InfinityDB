"""Materialize canonical logical-unit fields and source-attributed unit context."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

CANONICAL_UNIT_FIELDS = (
    "name",
    "isc",
    "isc_abbr",
    "slug",
    "canonical_faction_id",
    "main_army_id",
    "display_army_id",
)
ALIAS_FIELDS = ("name", "isc", "isc_abbr", "slug")


@dataclass(frozen=True)
class LogicalUnitPayloadMaterialization:
    """Summary of one canonical logical-unit/context materialization."""

    logical_unit_count: int
    source_link_count: int
    alias_count: int
    note_count: int
    spectables_count: int


def materialize_logical_unit_payloads(
    connection: sqlite3.Connection,
) -> LogicalUnitPayloadMaterialization:
    """Populate representative-backed logical-unit fields and explicit source context."""
    row_factory = connection.row_factory
    try:
        connection.row_factory = sqlite3.Row
        return _materialize_logical_unit_payloads(connection)
    finally:
        connection.row_factory = row_factory


def _materialize_logical_unit_payloads(
    connection: sqlite3.Connection,
) -> LogicalUnitPayloadMaterialization:
    units = {
        row["id"]: dict(row)
        for row in connection.execute(
            "SELECT * FROM units WHERE source_defined = 1 ORDER BY id"
        )
    }
    sources_by_logical: dict[int, list[int]] = {}
    representatives: dict[int, int] = {}
    for row in connection.execute(
        "SELECT lu.id AS logical_unit_id, lu.representative_unit_id, lus.source_unit_id "
        "FROM logical_units AS lu "
        "JOIN logical_unit_sources AS lus ON lus.logical_unit_id = lu.id "
        "ORDER BY lu.id, lus.source_unit_id"
    ):
        logical_unit_id = row["logical_unit_id"]
        representatives[logical_unit_id] = row["representative_unit_id"]
        sources_by_logical.setdefault(logical_unit_id, []).append(row["source_unit_id"])

    canonical_rows: list[tuple[Any, ...]] = []
    alias_rows: list[tuple[Any, ...]] = []
    note_rows: list[tuple[Any, ...]] = []
    spectables_rows: list[tuple[Any, ...]] = []

    for logical_unit_id, source_ids in sorted(sources_by_logical.items()):
        representative_id = representatives[logical_unit_id]
        try:
            representative = units[representative_id]
        except KeyError as exc:
            raise ValueError(
                f"Logical unit {logical_unit_id} has no source-defined representative"
            ) from exc

        canonical_rows.append(
            (
                *(representative[field] for field in CANONICAL_UNIT_FIELDS),
                logical_unit_id,
            )
        )

        for source_id in source_ids:
            try:
                source = units[source_id]
            except KeyError as exc:
                raise ValueError(
                    f"Logical unit {logical_unit_id} references missing source unit {source_id}"
                ) from exc

            if source_id != representative_id:
                for field in ALIAS_FIELDS:
                    value = source[field]
                    if value and value != representative[field]:
                        alias_rows.append(
                            (logical_unit_id, source_id, field, value)
                        )

            if source["notes"]:
                note_rows.append((logical_unit_id, source_id, source["notes"]))
            if source["spectables"]:
                spectables_rows.append(
                    (logical_unit_id, source_id, source["spectables"])
                )

    assignments = ", ".join(f"{field} = ?" for field in CANONICAL_UNIT_FIELDS)
    connection.executemany(
        f"UPDATE logical_units SET {assignments} WHERE id = ?",
        canonical_rows,
    )
    connection.executemany(
        "INSERT INTO logical_unit_aliases "
        "(logical_unit_id, source_unit_id, field, value) VALUES (?, ?, ?, ?)",
        alias_rows,
    )
    connection.executemany(
        "INSERT INTO logical_unit_notes "
        "(logical_unit_id, source_unit_id, note) VALUES (?, ?, ?)",
        note_rows,
    )
    connection.executemany(
        "INSERT INTO logical_unit_spectables "
        "(logical_unit_id, source_unit_id, spectables) VALUES (?, ?, ?)",
        spectables_rows,
    )

    return LogicalUnitPayloadMaterialization(
        logical_unit_count=len(canonical_rows),
        source_link_count=sum(len(source_ids) for source_ids in sources_by_logical.values()),
        alias_count=len(alias_rows),
        note_count=len(note_rows),
        spectables_count=len(spectables_rows),
    )
