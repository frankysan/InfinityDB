"""Validate normalized data and atomically publish a complete SQLite database."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from itertools import islice
from pathlib import Path
from typing import Any

from infinity_army_data.metadata import MetadataError, validate_metadata_envelope
from infinity_army_data.normalize import validate_normalized
from infinity_army_data.normalized_format import FORMAT_NAME, FORMAT_VERSION

from ..display_identities import (
    DISPLAY_IDENTITY_METADATA_KEY,
    DISPLAY_IDENTITY_SHA256_METADATA_KEY,
    DisplayIdentityError,
    parse_display_identity_metadata,
)
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
)
from ..peripheral_identities import (
    PeripheralIdentityCurated,
    peripheral_identity_metadata,
)
from .application_armies import materialize_application_armies
from .application_catalogs import materialize_application_catalogs
from .application_domain_slugs import materialize_application_domain_slugs
from .application_rule_references import materialize_application_rule_references
from .include_relationships import materialize_include_relationships
from .loadout_payloads import materialize_loadout_payloads
from .logical_unit_payloads import materialize_logical_unit_payloads
from .paths import raw_database_path
from .peripheral_relationships import materialize_peripheral_relationships
from .profile_payloads import materialize_profile_payloads
from .publication import PUBLISHED_CONTENT_SHA256_KEY, published_content_sha256
from .relation_constraints import materialize_relation_constraints
from .relation_group_dependencies import materialize_relation_group_dependencies
from .schema import (
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    PUBLISHED_DATABASE_TABLES,
    RAW_ROWS_TABLE,
    ROW_JSON,
    SOURCE_ONLY_TABLES,
    TABLES,
    columns_for,
    create_indexes,
    create_schema,
    quote,
)
from .unit_identity import reinforcement_unit_matches, resolve_logical_unit_identity

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

    has_display_document = DISPLAY_IDENTITY_METADATA_KEY in data
    has_display_hash = DISPLAY_IDENTITY_SHA256_METADATA_KEY in data
    if has_display_document != has_display_hash:
        raise ValueError("Normalized data has incomplete display-identity curated metadata")
    if has_display_document:
        try:
            display_identities = parse_display_identity_metadata(
                data[DISPLAY_IDENTITY_METADATA_KEY],
                data[DISPLAY_IDENTITY_SHA256_METADATA_KEY],
            )
        except DisplayIdentityError as exc:
            raise ValueError(
                "Normalized data has invalid display-identity curated metadata"
            ) from exc
        faction_rows = [
            *tables.get("metadata_factions", []),
            *tables.get("army_lists", []),
        ]
        active_canonical_ids = {
            row["canonical_faction_id"]
            for row in tables.get("units", [])
            if type(row.get("canonical_faction_id")) is int
        }
        try:
            display_army_overrides = display_identities.resolve_factions(
                faction_rows, active_canonical_ids=active_canonical_ids
            )
        except DisplayIdentityError as exc:
            raise ValueError(
                "Normalized data cannot resolve pinned display-identity references"
            ) from exc
        for row in tables.get("units", []):
            expected_display_army_id = display_army_overrides.get(
                row.get("canonical_faction_id"), row.get("main_army_id")
            )
            if row.get("display_army_id") != expected_display_army_id:
                raise ValueError(
                    "Normalized unit display identity does not match pinned curated data: "
                    f"unit {row.get('id')!r}"
                )
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


def reinforcement_identity_metadata(
    data: dict[str, Any],
    identity_config: IdentityConfig,
    reinforcement_matches: Mapping[int, int] | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic database metadata for audited reinforcement identity."""
    matches = (
        reinforcement_unit_matches(data, identity_config)
        if reinforcement_matches is None
        else reinforcement_matches
    )
    return [
        {
            "reinforcementUnitId": source_id,
            "standardUnitId": standard_id,
            "method": REINFORCEMENT_MATCH_METHOD,
        }
        for source_id, standard_id in sorted(matches.items())
    ]


def snapshot_metadata(
    data: dict[str, Any],
    identity_config: IdentityConfig,
    reinforcement_matches: Mapping[int, int] | None = None,
    *,
    peripheral_identities: PeripheralIdentityCurated | None = None,
) -> dict[str, Any]:
    """Return the metadata persisted with both database siblings."""
    metadata = {key: value for key, value in data.items() if key != "tables"}
    metadata.update(identity_metadata(identity_config))
    metadata[REINFORCEMENT_UNIT_MATCHES_KEY] = reinforcement_identity_metadata(
        data, identity_config, reinforcement_matches
    )
    metadata["imported_tables"] = list(data["tables"])
    metadata["published_tables"] = list(PUBLISHED_DATABASE_TABLES)
    metadata["source_only_tables"] = sorted(SOURCE_ONLY_TABLES)
    metadata[DATABASE_COMPATIBILITY_KEY] = DATABASE_COMPATIBILITY_VERSION
    if peripheral_identities is not None:
        metadata.update(peripheral_identity_metadata(peripheral_identities))
    return metadata


def create_raw_archive(
    connection: sqlite3.Connection,
    data: dict[str, Any],
    identity_config: IdentityConfig,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    """Store lossless rows plus queryable normalized source tables outside the app DB."""

    table_columns = {
        name: columns_for(name, rows) for name, rows in data["tables"].items()
    }
    create_schema(
        connection,
        data["tables"],
        table_columns=table_columns,
        definitions=TABLES,
    )
    connection.execute(
        f"CREATE TABLE {quote(RAW_ROWS_TABLE)} ("
        "table_name TEXT NOT NULL, row_position INTEGER NOT NULL, "
        f"{quote(ROW_JSON)} TEXT NOT NULL, "
        "PRIMARY KEY (table_name, row_position))"
    )
    metadata = dict(metadata or snapshot_metadata(data, identity_config))
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


def _database_columns(
    connection: sqlite3.Connection, table_names: Iterable[str]
) -> dict[str, tuple[str, ...]]:
    return {
        name: tuple(
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({quote(name)})")
        )
        for name in table_names
    }


def _publish_application_database(
    staging_path: Path,
    destination: Path,
    data: dict[str, Any],
    metadata: Mapping[str, Any],
) -> None:
    """Copy validated application tables from the full relational staging database."""

    staging = sqlite3.connect(staging_path)
    try:
        table_columns = _database_columns(staging, PUBLISHED_DATABASE_TABLES)
    finally:
        staging.close()

    connection = sqlite3.connect(destination)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("ATTACH DATABASE ? AS staging", (str(staging_path),))
        with connection:
            create_schema(
                connection,
                data["tables"],
                table_columns=table_columns,
                definitions=PUBLISHED_DATABASE_TABLES,
            )
            insert_batched(
                connection,
                f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
                [(key, json_text(value)) for key, value in metadata.items()],
            )
            for name in PUBLISHED_DATABASE_TABLES:
                connection.execute(
                    f"INSERT INTO {quote(name)} SELECT * FROM staging.{quote(name)}"
                )
            create_indexes(connection, table_names=PUBLISHED_DATABASE_TABLES)
            connection.execute("ANALYZE")
        violation = connection.execute("PRAGMA foreign_key_check").fetchone()
        if violation is not None:
            raise ValueError(f"Published database contains broken foreign keys: {tuple(violation)}")
    finally:
        connection.close()


def export_database(
    data: dict[str, Any],
    path: Path,
    *,
    identity_config: IdentityConfig | None = None,
    peripheral_identities: PeripheralIdentityCurated | None = None,
) -> None:
    """Validate the full normalized model, then publish application and raw siblings.

    Export first builds a complete relational staging database and runs every
    source-to-canonical consistency check against it. Only after that succeeds is
    the self-contained application subset copied into ``path``. The sibling raw
    database preserves exact normalized rows, including absent versus null fields,
    for development, audit, and reconstruction use.
    """
    table_columns = validate_input(data)
    identity_config = resolve_identity_config(data, identity_config)
    logical_identity = resolve_logical_unit_identity(data, identity_config)
    metadata = snapshot_metadata(
        data,
        identity_config,
        logical_identity.reinforcement_matches,
        peripheral_identities=peripheral_identities,
    )
    path = Path(path)
    archive_path = raw_database_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def temporary_path(target: Path) -> Path:
        descriptor, filename = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=path.parent
        )
        os.close(descriptor)
        return Path(filename)

    staging_temporary = temporary_path(path.with_name(f"{path.name}.staging"))
    published_temporary = temporary_path(path)
    archive_temporary = temporary_path(archive_path)
    try:
        connection = sqlite3.connect(staging_temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                create_schema(connection, data["tables"], table_columns=table_columns)
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
                insert_batched(
                    connection,
                    "INSERT INTO logical_units (id, representative_unit_id) VALUES (?, ?)",
                    (
                        (row["id"], row["representative_unit_id"])
                        for row in logical_identity.logical_units
                    ),
                )
                insert_batched(
                    connection,
                    "INSERT INTO logical_unit_sources (source_unit_id, logical_unit_id) "
                    "VALUES (?, ?)",
                    (
                        (row["source_unit_id"], row["logical_unit_id"])
                        for row in logical_identity.logical_unit_sources
                    ),
                )
                materialize_application_armies(connection, identity_config)
                materialize_application_catalogs(connection, identity_config)
                materialize_logical_unit_payloads(connection)
                materialize_application_domain_slugs(connection)
                materialize_application_rule_references(connection)
                materialize_profile_payloads(connection)
                materialize_loadout_payloads(connection)
                materialize_include_relationships(connection)
                materialize_peripheral_relationships(connection, peripheral_identities)
                materialize_relation_constraints(connection)
                materialize_relation_group_dependencies(connection)
                create_indexes(connection)
                connection.execute("ANALYZE")
                metadata[PUBLISHED_CONTENT_SHA256_KEY] = published_content_sha256(connection)
                connection.execute(
                    f"INSERT INTO {quote(METADATA_TABLE)} (key, value) VALUES (?, ?)",
                    (
                        PUBLISHED_CONTENT_SHA256_KEY,
                        json_text(metadata[PUBLISHED_CONTENT_SHA256_KEY]),
                    ),
                )
        except (sqlite3.IntegrityError, OverflowError) as exc:
            raise ValueError(f"Invalid normalized database data: {exc}") from exc
        finally:
            connection.close()

        from .repository import Database

        # Full source-to-canonical validation happens before source-only relational
        # tables are excluded from the published application database.
        Database(staging_temporary).validate(source_consistency=True)

        archive_connection = sqlite3.connect(archive_temporary)
        try:
            archive_connection.execute("PRAGMA foreign_keys = ON")
            with archive_connection:
                create_raw_archive(
                    archive_connection, data, identity_config, metadata=metadata
                )
            if archive_connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Raw archive integrity check failed")
            if archive_connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("Raw archive contains broken foreign keys")
        finally:
            archive_connection.close()

        _publish_application_database(
            staging_temporary, published_temporary, data, metadata
        )
        Database(published_temporary).validate()

        os.replace(archive_temporary, archive_path)
        os.replace(published_temporary, path)
    finally:
        staging_temporary.unlink(missing_ok=True)
        published_temporary.unlink(missing_ok=True)
        archive_temporary.unlink(missing_ok=True)
