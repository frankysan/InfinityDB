"""Validate normalized data and atomically publish a complete SQLite database."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from itertools import islice
from pathlib import Path
from typing import Any

from infinity_army_data.availability import (
    GENERIC_MATCH_METHOD,
    GENERIC_UNIT_MATCHES_KEY,
    MERCENARY_SOURCE_ROLE,
)
from infinity_army_data.metadata import MetadataError, validate_metadata_envelope
from infinity_army_data.normalize import FORMAT_NAME, FORMAT_VERSION, validate_normalized

from ..identities import (
    IDENTITY_CONFIG_METADATA_KEY,
    IDENTITY_CONFIG_SHA256_METADATA_KEY,
    REINFORCEMENT_MATCH_METHOD,
    REINFORCEMENT_UNIT_MATCHES_KEY,
    IdentityConfig,
    IdentityConfigError,
    identity_metadata,
    load_identity_config,
    parse_identity_metadata,
    unit_match_identities,
)
from .schema import (
    APPLICATION_ID,
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    RAW_ROWS_TABLE,
    ROW_JSON,
    TABLES,
    columns_for,
    create_indexes,
    create_schema,
    quote,
)

BATCH_SIZE = 1_000


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def validate_input(data: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    if not isinstance(data, dict) or not isinstance(data.get("_meta"), dict):
        raise ValueError("Normalized data must contain a _meta object")
    meta = data["_meta"]
    if meta.get("format") != FORMAT_NAME or type(meta.get("formatVersion")) is not int:
        raise ValueError(f"Expected {FORMAT_NAME!r}, version {FORMAT_VERSION}")
    if meta["formatVersion"] != FORMAT_VERSION:
        raise ValueError(f"Unsupported normalized format version: {meta['formatVersion']}")
    metadata = data.get("armyMetadata")
    if metadata is None:
        raise ValueError("Normalized data must contain required Army metadata")
    try:
        validate_metadata_envelope(metadata)
    except MetadataError as exc:
        raise ValueError(f"Invalid Army metadata: {exc}") from exc
    tables = data.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Normalized data must contain a tables object")
    table_columns: dict[str, tuple[str, ...]] = {}
    for name, rows in tables.items():
        if name not in TABLES:
            raise ValueError(f"Unsupported normalized table: {name}")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Normalized table {name} must be an array of objects")
        table_columns[name] = columns_for(name, rows)
        for row in rows:
            for field in TABLES[name].key:
                if type(row.get(field)) not in (int, str):
                    raise ValueError(f"{name}.{field} must be a non-null integer or string key")
                if type(row[field]) is int and not -(2**63) <= row[field] < 2**63:
                    raise ValueError(f"{name}.{field} exceeds SQLite's integer key range")
            for field in ("army_id", "unit_id"):
                if field in row and row[field] is not None and type(row[field]) is not int:
                    raise ValueError(f"{name}.{field} must be an integer")
            if name in ("units", "army_lists", "factions") and type(row["id"]) is not int:
                raise ValueError(f"{name}.id must be an integer")
            if "name" in row and row["name"] is not None and not isinstance(row["name"], str):
                raise ValueError(f"{name}.name must be a string or null")
            if name == "army_lists":
                for field in ("slug", "kind"):
                    if row.get(field) is not None and not isinstance(row[field], str):
                        raise ValueError(f"army_lists.{field} must be a string or null")
            if name == "units" and type(row.get("source_defined")) is not bool:
                raise ValueError("units.source_defined must be a boolean")
    try:
        json_text(data)
        validate_normalized(data)
    except (KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError(f"Invalid normalized data: {exc}") from exc
    return table_columns


def resolve_identity_config(
    data: dict[str, Any], explicit: IdentityConfig | None = None
) -> IdentityConfig:
    """Resolve the identity policy for export, preferring normalized provenance."""
    has_document = IDENTITY_CONFIG_METADATA_KEY in data
    has_hash = IDENTITY_CONFIG_SHA256_METADATA_KEY in data
    if has_document != has_hash:
        raise ValueError("Normalized data has incomplete identity configuration metadata")

    if has_document:
        try:
            pinned = parse_identity_metadata(
                data[IDENTITY_CONFIG_METADATA_KEY],
                data[IDENTITY_CONFIG_SHA256_METADATA_KEY],
            )
        except IdentityConfigError as exc:
            raise ValueError("Normalized data has invalid identity configuration metadata") from exc
        if explicit is not None and explicit.content_sha256 != pinned.content_sha256:
            raise ValueError(
                "Explicit identity configuration does not match the policy "
                "pinned in normalized data"
            )
        return pinned

    return explicit or load_identity_config()


def sql_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json_text(value)
    # SQLite's integer range is narrower than JSON's; the original row remains exact.
    if type(value) is int and not -(2**63) <= value < 2**63:
        return str(value)
    return value


def raw_database_path(path: Path) -> Path:
    """Return the development archive path associated with a frontend database."""
    return path.with_name(f"{path.stem}.raw{path.suffix}")


def batched(
    rows: Iterable[tuple[Any, ...]], size: int = BATCH_SIZE
) -> Iterator[list[tuple[Any, ...]]]:
    """Yield bounded parameter batches without retaining an entire table."""
    iterator = iter(rows)
    while batch := list(islice(iterator, size)):
        yield batch


def insert_batched(
    connection: sqlite3.Connection, statement: str, rows: Iterable[tuple[Any, ...]]
) -> None:
    for batch in batched(rows):
        connection.executemany(statement, batch)


def reinforcement_unit_matches(
    data: dict[str, Any], identity_config: IdentityConfig
) -> dict[int, int]:
    """Audit unambiguous reinforcement-only source units against standard groups."""
    tables = data["tables"]
    units = {
        row["id"]: row
        for row in tables.get("units", [])
        if row.get("source_defined") is not False and isinstance(row.get("id"), int)
    }
    army_kinds = {
        row.get("id"): row.get("kind")
        for row in tables.get("army_lists", [])
        if isinstance(row.get("id"), int)
    }
    memberships: dict[int, list[int]] = {unit_id: [] for unit_id in units}
    for row in tables.get("army_units", []):
        unit_id = row.get("unit_id")
        army_id = row.get("army_id")
        if unit_id in memberships and isinstance(army_id, int):
            memberships[unit_id].append(army_id)

    reinforcement_ids = {
        unit_id
        for unit_id, army_ids in memberships.items()
        if army_ids and all(army_kinds.get(army_id) == "reinforcement" for army_id in army_ids)
    }

    generic_matches: dict[int, int] | None = None
    raw_generic = data.get(GENERIC_UNIT_MATCHES_KEY)
    if raw_generic is not None:
        if not isinstance(raw_generic, list):
            raise ValueError("Normalized data has invalid generic unit identity metadata")
        generic_matches = {}
        for item in raw_generic:
            if (
                not isinstance(item, dict)
                or set(item) != {"sourceUnitId", "representativeUnitId", "method"}
                or type(item["sourceUnitId"]) is not int
                or type(item["representativeUnitId"]) is not int
                or item["method"] != GENERIC_MATCH_METHOD
                or item["sourceUnitId"] in generic_matches
            ):
                raise ValueError("Normalized data has invalid generic unit identity metadata")
            generic_matches[item["sourceUnitId"]] = item["representativeUnitId"]

    def standard_group_key(unit_id: int) -> tuple[object, ...]:
        if unit_id in identity_config.unit_aliases:
            return ("configured", identity_config.canonical_unit_id(unit_id))
        if generic_matches is not None:
            return ("persisted", generic_matches.get(unit_id, unit_id))
        unit = units[unit_id]
        label = unit.get("isc") or unit.get("name") or ""
        return ("legacy", unit_id % 10_000, str(label).casefold())

    standard_groups: dict[tuple[object, ...], list[int]] = {}
    for unit_id, unit in sorted(units.items()):
        if unit_id in reinforcement_ids or unit.get("source_role") == MERCENARY_SOURCE_ROLE:
            continue
        standard_groups.setdefault(standard_group_key(unit_id), []).append(unit_id)

    identities_by_group: dict[tuple[object, ...], set[str]] = {}
    representative_by_group: dict[tuple[object, ...], int] = {}
    for key, source_ids in standard_groups.items():
        representative_by_group[key] = min(source_ids)
        identities = identities_by_group.setdefault(key, set())
        for source_id in source_ids:
            identities.update(unit_match_identities(units[source_id], identity_config))

    reinforcement_groups: dict[str, list[int]] = {}
    reinforcement_identities: dict[str, set[str]] = {}
    for reinforcement_id in sorted(reinforcement_ids):
        identities = unit_match_identities(units[reinforcement_id], identity_config)
        base_identity = min(identities, default="")
        reinforcement_groups.setdefault(base_identity, []).append(reinforcement_id)
        reinforcement_identities.setdefault(base_identity, set()).update(identities)

    matches: dict[int, int] = {}
    for base_identity, source_ids in reinforcement_groups.items():
        identities = reinforcement_identities[base_identity]
        candidates = [
            key
            for key, standard_identities in identities_by_group.items()
            if identities & standard_identities
        ]
        if len(candidates) == 1:
            standard_id = representative_by_group[candidates[0]]
            matches.update({source_id: standard_id for source_id in source_ids})
    return matches


def reinforcement_identity_metadata(
    data: dict[str, Any], identity_config: IdentityConfig
) -> list[dict[str, Any]]:
    """Return deterministic database metadata for audited reinforcement identity."""
    return [
        {
            "reinforcementUnitId": source_id,
            "standardUnitId": standard_id,
            "method": REINFORCEMENT_MATCH_METHOD,
        }
        for source_id, standard_id in sorted(
            reinforcement_unit_matches(data, identity_config).items()
        )
    ]


def snapshot_metadata(data: dict[str, Any], identity_config: IdentityConfig) -> dict[str, Any]:
    """Return the metadata persisted with both database siblings."""
    metadata = {key: value for key, value in data.items() if key != "tables"}
    metadata.update(identity_metadata(identity_config))
    metadata[REINFORCEMENT_UNIT_MATCHES_KEY] = reinforcement_identity_metadata(
        data, identity_config
    )
    metadata["imported_tables"] = list(data["tables"])
    metadata[DATABASE_COMPATIBILITY_KEY] = DATABASE_COMPATIBILITY_VERSION
    return metadata


def create_raw_archive(
    connection: sqlite3.Connection, data: dict[str, Any], identity_config: IdentityConfig
) -> None:
    """Store lossless normalized records outside the frontend database."""
    connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    connection.execute(
        f"CREATE TABLE {quote(METADATA_TABLE)} (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        f"CREATE TABLE {quote(RAW_ROWS_TABLE)} ("
        "table_name TEXT NOT NULL, row_position INTEGER NOT NULL, "
        f"{quote(ROW_JSON)} TEXT NOT NULL, "
        "PRIMARY KEY (table_name, row_position))"
    )
    metadata = snapshot_metadata(data, identity_config)
    insert_batched(
        connection,
        f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
        [(key, json_text(value)) for key, value in metadata.items()],
    )
    insert_batched(
        connection,
        f"INSERT INTO {quote(RAW_ROWS_TABLE)} (table_name, row_position, {quote(ROW_JSON)}) "
        "VALUES (?, ?, ?)",
        (
            (name, position, json_text(row))
            for name, rows in data["tables"].items()
            for position, row in enumerate(rows)
        ),
    )


def export_database(
    data: dict[str, Any], path: Path, *, identity_config: IdentityConfig | None = None
) -> None:
    """Replace ``path`` only after the complete normalized import passes validation.

    The frontend database contains queryable normalized columns only. A sibling
    ``.raw`` database preserves exact normalized rows, including absent versus
    null fields, for development use. If normalized data already pins an identity
    policy, export validates and preserves that exact policy; otherwise it falls
    back to an explicitly supplied policy or the authored project manifest.
    """
    table_columns = validate_input(data)
    identity_config = resolve_identity_config(data, identity_config)
    path = Path(path)
    archive_path = raw_database_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(filename)
    archive_descriptor, archive_filename = tempfile.mkstemp(
        prefix=f".{archive_path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(archive_descriptor)
    archive_temporary = Path(archive_filename)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                create_schema(connection, data["tables"], table_columns=table_columns)
                metadata = snapshot_metadata(data, identity_config)
                insert_batched(
                    connection,
                    f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
                    [(key, json_text(value)) for key, value in metadata.items()],
                )
                for name, rows in data["tables"].items():
                    columns = table_columns[name]
                    fields = ", ".join(map(quote, columns))
                    placeholders = ", ".join("?" for _ in columns)
                    insert_batched(
                        connection,
                        f"INSERT INTO {quote(name)} ({fields}) VALUES ({placeholders})",
                        (tuple(sql_value(row.get(field)) for field in columns) for row in rows),
                    )
                create_indexes(connection)
                # The frontend database is an immutable snapshot. Persist planner
                # statistics at build time so read-only connections make informed
                # join-order choices without request-time analysis.
                connection.execute("ANALYZE")
        except (sqlite3.IntegrityError, OverflowError) as exc:
            raise ValueError(f"Invalid normalized database data: {exc}") from exc
        finally:
            connection.close()
        from .repository import Database

        Database(temporary).validate()
        archive_connection = sqlite3.connect(archive_temporary)
        try:
            with archive_connection:
                create_raw_archive(archive_connection, data, identity_config)
            if archive_connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Raw archive integrity check failed")
        finally:
            archive_connection.close()
        os.replace(archive_temporary, archive_path)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
        archive_temporary.unlink(missing_ok=True)
