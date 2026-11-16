"""Opt-in Army v28 relational classification of Army's skill-like source bucket.

These are reviewed Army source metadata, not new N5 Skill definitions.
Complete builds use independently verified normalized source provenance.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .database.normalized_source import verified_army_export_generation
from .database.publication import (
    PUBLISHED_CONTENT_SHA256_KEY,
    published_content_sha256,
    validate_database_pair,
)
from .database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE, Table
from .equipment_presentation_storage import (
    ARMY_SCHEMA_VERSION as PREVIOUS_SCHEMA_VERSION,
)
from .equipment_presentation_storage import (
    ARMY_V27_PUBLISHED_TABLES,
    read_equipment_encodings,
)
from .skill_config import (
    SKILL_SOURCE_CONFIG_FORMAT,
    SKILL_SOURCE_CONFIG_VERSION,
    SkillSourceClassification,
    load_skill_source_config,
    parse_skill_source_config,
)
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite

ARMY_SCHEMA_VERSION = 28
ARMY_COMPATIBILITY_VERSION = 37
SKILL_CLASSIFICATION_TABLES = {
    "skill_source_classification_metadata": Table(
        ("id",),
        ("format", "version", "source_sha256", "export_pair_sha256",
         "row_count", "content_sha256"),
    ),
    "skill_source_classifications": Table(
        ("ref_kind", "source_ref"),
        ("position", "catalog", "application_skill_id", "classification", "reason"),
    ),
}
ARMY_V28_PUBLISHED_TABLES = {
    **ARMY_V27_PUBLISHED_TABLES, **SKILL_CLASSIFICATION_TABLES,
}


def _fingerprint(items: tuple[SkillSourceClassification, ...]) -> str:
    rows = [
        {"skill_id": item.skill_ref, "classification": item.classification,
         "reason": item.reason}
        for item in items
    ]
    return hashlib.sha256(
        json.dumps(
            rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _source_identity(ref: int | str) -> tuple[str, str]:
    if isinstance(ref, int):
        return "numeric", str(ref)
    return "slug", ref


def _resolve_source(connection: sqlite3.Connection, ref: int | str) -> int:
    """Match the existing application Skills resolver without creating new identities."""
    if isinstance(ref, str):
        rows = connection.execute(
            "SELECT application_id FROM application_domain_slugs "
            "WHERE domain='skills' AND status='resolved' AND slug=? COLLATE NOCASE",
            (ref,),
        ).fetchall()
        if len(rows) != 1:
            raise ValueError(f"Skill classification has no unique Army source: {ref!r}")
        result = int(rows[0][0])
    else:
        direct = connection.execute(
            "SELECT id FROM application_catalog_items WHERE catalog='skills' AND id=?",
            (ref,),
        ).fetchone()
        if direct is not None:
            result = int(direct[0])
        else:
            rows = connection.execute(
                "SELECT DISTINCT application_item_id FROM application_catalog_sources "
                "WHERE catalog='skills' AND source_item_id=?",
                (ref,),
            ).fetchall()
            if len(rows) != 1:
                raise ValueError(f"Skill classification has no unique Army source: {ref!r}")
            result = int(rows[0][0])
    row = connection.execute(
        "SELECT 1 FROM application_catalog_items WHERE catalog='skills' AND id=?",
        (result,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Skill classification source has no published Skill identity: {ref!r}")
    return result


def read_skill_classifications(
    connection: sqlite3.Connection,
) -> tuple[SkillSourceClassification, ...]:
    """Return source-authored rows with their exact source Skill identities."""
    meta = connection.execute(
        "SELECT format,version,source_sha256,export_pair_sha256,row_count,content_sha256 "
        "FROM skill_source_classification_metadata WHERE id=1"
    ).fetchone()
    pair_row = connection.execute(
        f"SELECT value FROM {METADATA_TABLE} WHERE key='export_pair_sha256'"
    ).fetchone()
    try:
        generation = json.loads(pair_row[0]) if pair_row else None
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid Skill classification Army generation") from exc
    if (
        meta is None
        or tuple(meta[:2]) != (SKILL_SOURCE_CONFIG_FORMAT, SKILL_SOURCE_CONFIG_VERSION)
        or any(not isinstance(value, str) or len(value) != 64 for value in (meta[2], meta[5]))
        or meta[3] != generation or not isinstance(generation, str)
        or len(generation) != 64 or meta[4] != 6
    ):
        raise ValueError("Skill classification metadata does not match its reviewed source")
    rows = connection.execute(
        "SELECT ref_kind,source_ref,position,catalog,application_skill_id,"
        "classification,reason FROM skill_source_classifications ORDER BY position"
    ).fetchall()
    if len(rows) != 6 or any(row[2] != i for i, row in enumerate(rows)):
        raise ValueError("Skill classification rows are incomplete or unordered")
    values: list[dict[str, Any]] = []
    for kind, raw_ref, _pos, catalog, application_id, classification, reason in rows:
        if catalog != "skills" or kind not in {"slug", "numeric"}:
            raise ValueError("Skill classification source identity kind differs")
        if kind == "numeric":
            try:
                ref: int | str = int(raw_ref)
            except ValueError as exc:
                raise ValueError("Invalid numeric Skill classification source") from exc
            if str(ref) != raw_ref:
                raise ValueError("Noncanonical numeric Skill classification source")
        else:
            ref = raw_ref
        if _resolve_source(connection, ref) != application_id:
            raise ValueError(f"Skill classification source resolution differs: {ref!r}")
        values.append({
            "skill_id": ref, "classification": classification, "reason": reason,
        })
    items = parse_skill_source_config({
        "format": SKILL_SOURCE_CONFIG_FORMAT,
        "formatVersion": SKILL_SOURCE_CONFIG_VERSION,
        "classifications": values,
    })
    if _fingerprint(items) != meta[5]:
        raise ValueError("Skill classification content fingerprint differs")
    return items


def publish_skill_classifications(
    army: Path, raw: Path | None, source: Path,
    *, normalized: Path | None = None,
) -> None:
    """Publish v28 from an explicitly verified raw or normalized Army source."""
    rows = load_skill_source_config(source)
    if len(rows) != 6:
        raise ValueError("Reviewed Skill classification inventory requires six entries")
    generation = verified_army_export_generation(army, raw, normalized)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    with closing(sqlite3.connect(army)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Skill classification publication requires Army v27")
        read_equipment_encodings(connection)
        identities = [_resolve_source(connection, item.skill_ref) for item in rows]
        if len(set(identities)) != len(identities):
            raise ValueError("Skill classification aliases resolve to duplicate Army identities")
        with connection:
            connection.execute(
                """CREATE TABLE skill_source_classification_metadata (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    format TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK(version=1),
                    source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
                    export_pair_sha256 TEXT NOT NULL CHECK(length(export_pair_sha256)=64),
                    row_count INTEGER NOT NULL CHECK(row_count=6),
                    content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64)
                )"""
            )
            connection.execute(
                """CREATE TABLE skill_source_classifications (
                    ref_kind TEXT NOT NULL CHECK(ref_kind IN ('slug','numeric')),
                    source_ref TEXT NOT NULL,
                    position INTEGER NOT NULL UNIQUE CHECK(position>=0),
                    catalog TEXT NOT NULL DEFAULT 'skills' CHECK(catalog='skills'),
                    application_skill_id INTEGER NOT NULL UNIQUE,
                    classification TEXT NOT NULL CHECK(
                        classification IN (
                            'equipment','training','attribute-override','source-marker'
                        )
                    ),
                    reason TEXT NOT NULL CHECK(length(reason)>0),
                    PRIMARY KEY(ref_kind,source_ref),
                    FOREIGN KEY(catalog,application_skill_id)
                        REFERENCES application_catalog_items(catalog,id)
                )"""
            )
            connection.execute(
                "INSERT INTO skill_source_classification_metadata VALUES (1,?,?,?,?,?,?)",
                (
                    SKILL_SOURCE_CONFIG_FORMAT, SKILL_SOURCE_CONFIG_VERSION,
                    source_sha, generation, len(rows), _fingerprint(rows),
                ),
            )
            connection.executemany(
                "INSERT INTO skill_source_classifications VALUES (?,?,?,?,?,?,?)",
                (
                    (*_source_identity(item.skill_ref), index, "skills",
                     identities[index], item.classification, item.reason)
                    for index, item in enumerate(rows)
                ),
            )
            if read_skill_classifications(connection) != rows:
                raise ValueError("Embedded Skill source classifications differ from reviewed input")
            checksum = published_content_sha256(
                connection, definitions=ARMY_V28_PUBLISHED_TABLES,
            )
            new_metadata = {
                PUBLISHED_CONTENT_SHA256_KEY: checksum,
                DATABASE_COMPATIBILITY_KEY: ARMY_COMPATIBILITY_VERSION,
            }
            for key, value in new_metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                    (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(army)
    if raw is None:
        return
    with closing(sqlite3.connect(raw)) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("Skill classification raw export requires Army v27")
        with connection:
            for key, value in new_metadata.items():
                connection.execute(
                    f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                    (json.dumps(value), key),
                )
            connection.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(connection)
    normalize_sqlite_header(raw)
    validate_database_pair(army, raw_path=raw)
