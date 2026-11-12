"""Army v31 symbol mappings and source-bound graphical publication hashes."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .army_reference_storage import ARMY_SCHEMA_VERSION as PREVIOUS_SCHEMA_VERSION
from .army_reference_storage import ARMY_V30_PUBLISHED_TABLES, read_army_reference_data
from .database.publication import (
    PUBLISHED_CONTENT_SHA256_KEY,
    published_content_sha256,
    validate_database_pair,
)
from .database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE, Table
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from .symbol_catalog import PUBLICATION_FORMAT, PUBLICATION_VERSION, SymbolCatalog

ARMY_SCHEMA_VERSION = 31
ARMY_COMPATIBILITY_VERSION = 40
MAPPING_FIELDS = (
    "factionIdToPublishedPath", "unitSlugToPublishedPath",
    "unitProfileLogoToPublishedPath", "profileIdentityToPublishedPath",
)
SYMBOL_PATH_TABLES = {
    "symbol_path_metadata": Table(
        ("id",), ("format", "version", "source_sha256", "army_archive_sha256",
                  "export_pair_sha256", "mapping_count", "asset_count", "content_sha256"),
    ),
    "published_symbol_assets": Table(("path",), ("sha256",)),
    "published_symbol_paths": Table(("kind", "identity"), ("path",)),
}
ARMY_V31_PUBLISHED_TABLES = {**ARMY_V30_PUBLISHED_TABLES, **SYMBOL_PATH_TABLES}


def _snapshot(connection: sqlite3.Connection) -> tuple[str, str]:
    values = {key: json.loads(value) for key, value in connection.execute(
        f"SELECT key,value FROM {METADATA_TABLE} WHERE key IN ('_meta','export_pair_sha256')"
    )}
    archive = values.get("_meta", {}).get("snapshotArchiveSha256")
    generation = values.get("export_pair_sha256")
    if not isinstance(archive, str) or not isinstance(generation, str):
        raise ValueError("Symbol mappings require exact Army archive and export identities")
    if any(
        not isinstance(value, str) or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
        for value in (archive, generation)
    ):
        raise ValueError("Symbol mappings require exact Army archive and export identities")
    return archive, generation


def _projection(document: dict) -> tuple[dict[str, Any], SymbolCatalog]:
    catalog = SymbolCatalog(publication=document)
    maps = (catalog.armies, catalog.units, catalog.profile_logos, catalog.profile_identities)
    if not catalog.asset_hashes or any(not value for value in maps[:3]):
        raise ValueError("Symbol publication lacks runtime mappings or published asset hashes")
    for field, mapping in zip(MAPPING_FIELDS, maps, strict=True):
        for identity, path in mapping.items():
            if not identity or identity.strip() != identity or path not in catalog.asset_hashes:
                raise ValueError("Symbol mapping has an invalid identity or unpublished asset")
            if field == MAPPING_FIELDS[0] and (
                not identity.isascii() or not identity.isdigit() or str(int(identity)) != identity
                or int(identity) <= 0
            ):
                raise ValueError("Faction symbol mapping requires an exact positive source ID")
    return {
        "format": PUBLICATION_FORMAT, "formatVersion": PUBLICATION_VERSION,
        **dict(zip(MAPPING_FIELDS, maps, strict=True)),
        "publishedSha256ByPath": catalog.asset_hashes,
    }, catalog


def read_symbol_publication(connection: sqlite3.Connection) -> dict[str, Any]:
    """Reconstruct and validate the exact serving projection, never its build manifest."""
    meta = connection.execute(
        "SELECT format,version,source_sha256,army_archive_sha256,export_pair_sha256,"
        "mapping_count,asset_count,content_sha256 FROM symbol_path_metadata WHERE id=1"
    ).fetchone()
    archive, generation = _snapshot(connection)
    if (
        meta is None or tuple(meta[:2]) != (PUBLICATION_FORMAT, PUBLICATION_VERSION)
        or meta[3] != archive or meta[4] != generation
        or any(
            not isinstance(value, str) or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            for value in (meta[2], meta[7])
        )
    ):
        raise ValueError("Symbol mapping metadata differs from its source publication")
    paths = connection.execute(
        "SELECT kind,identity,path FROM published_symbol_paths ORDER BY kind,identity"
    ).fetchall()
    assets = connection.execute(
        "SELECT path,sha256 FROM published_symbol_assets ORDER BY path"
    ).fetchall()
    if (len(paths), len(assets)) != tuple(meta[5:7]):
        raise ValueError("Symbol mapping inventory is incomplete")
    document: dict[str, Any] = {
        "format": PUBLICATION_FORMAT, "formatVersion": PUBLICATION_VERSION,
        **{field: {} for field in MAPPING_FIELDS}, "publishedSha256ByPath": dict(assets),
    }
    for kind, identity, path in paths:
        if kind not in MAPPING_FIELDS or identity in document[kind]:
            raise ValueError("Unknown or duplicate symbol mapping identity")
        document[kind][identity] = path
    result, catalog = _projection(document)
    if catalog.revision != meta[7]:
        raise ValueError("Symbol mapping content fingerprint differs")
    return result


def publish_symbol_paths(army: Path, raw: Path, source: Path, assets: Path) -> None:
    """Extend one disposable v30 pair after verifying source and actual SVG bytes."""
    source_bytes = source.read_bytes()
    document = json.loads(source_bytes)
    projection, catalog = _projection(document)
    snapshot = document.get("sourceSnapshot")
    artifact = snapshot.get("armyArtifact") if isinstance(snapshot, dict) else None
    source_archive = artifact.get("sha256") if isinstance(artifact, dict) else None
    for relative, expected in catalog.asset_hashes.items():
        path = assets.joinpath(*relative.split("/"))
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Published symbol bytes differ or are missing: {relative}")
    generation = validate_database_pair(army, raw_path=raw)
    with closing(sqlite3.connect(army)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Symbol path publication requires Army v30")
        archive, paired_generation = _snapshot(connection)
        if generation != paired_generation or source_archive != archive:
            raise ValueError("Symbol publication names a different Army archive")
        read_army_reference_data(connection)
        rows = [
            (field, identity, path) for field in MAPPING_FIELDS
            for identity, path in sorted(projection[field].items())
        ]
        with connection:
            connection.execute("""CREATE TABLE symbol_path_metadata (
                id INTEGER PRIMARY KEY CHECK(id=1), format TEXT NOT NULL,
                version INTEGER NOT NULL CHECK(version=2),
                source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
                army_archive_sha256 TEXT NOT NULL CHECK(length(army_archive_sha256)=64),
                export_pair_sha256 TEXT NOT NULL CHECK(length(export_pair_sha256)=64),
                mapping_count INTEGER NOT NULL CHECK(mapping_count>0),
                asset_count INTEGER NOT NULL CHECK(asset_count>0),
                content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64)
            )""")
            connection.execute("""CREATE TABLE published_symbol_assets (
                path TEXT PRIMARY KEY NOT NULL,
                sha256 TEXT NOT NULL CHECK(length(sha256)=64)
            )""")
            connection.execute("""CREATE TABLE published_symbol_paths (
                kind TEXT NOT NULL CHECK(kind IN ('factionIdToPublishedPath',
                    'unitSlugToPublishedPath','unitProfileLogoToPublishedPath',
                    'profileIdentityToPublishedPath')),
                identity TEXT NOT NULL, path TEXT NOT NULL,
                PRIMARY KEY(kind,identity),
                FOREIGN KEY(path) REFERENCES published_symbol_assets(path)
            )""")
            connection.execute("INSERT INTO symbol_path_metadata VALUES (1,?,?,?,?,?,?,?,?)", (
                PUBLICATION_FORMAT, PUBLICATION_VERSION, hashlib.sha256(source_bytes).hexdigest(),
                archive, generation, len(rows), len(catalog.asset_hashes), catalog.revision,
            ))
            connection.executemany(
                "INSERT INTO published_symbol_assets VALUES (?,?)",
                sorted(catalog.asset_hashes.items()),
            )
            connection.executemany("INSERT INTO published_symbol_paths VALUES (?,?,?)", rows)
            if read_symbol_publication(connection) != projection:
                raise ValueError("Embedded symbol mappings differ from the selected publication")
            metadata = {
                PUBLISHED_CONTENT_SHA256_KEY: published_content_sha256(
                    connection, definitions=ARMY_V31_PUBLISHED_TABLES,
                ),
                DATABASE_COMPATIBILITY_KEY: ARMY_COMPATIBILITY_VERSION,
            }
            for key, value in metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?", (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(army)
    with closing(sqlite3.connect(raw)) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Symbol raw export requires Army v30")
        with connection:
            for key, value in metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?", (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(raw)
    validate_database_pair(army, raw_path=raw)
