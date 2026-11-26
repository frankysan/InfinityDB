"""Deterministic Army General-profile projection publication and lookup."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

from .database.publication import PUBLISHED_CONTENT_SHA256_KEY, published_content_sha256
from .database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE, Table
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from .symbol_path_storage import ARMY_SCHEMA_VERSION as PREVIOUS_SCHEMA_VERSION
from .symbol_path_storage import ARMY_V31_PUBLISHED_TABLES

EXPLORER_SCHEMA_VERSION = 32
EXPLORER_COMPATIBILITY_VERSION = 41
ARMY_SCHEMA_VERSION = 33
ARMY_COMPATIBILITY_VERSION = 42
# This order is a persisted contract, not a UI ordering preference.
AVAILABILITY_MASK_FLAGS = ("mercs", "specops", "teamops", "reinforcement")
MASK_COUNT = 1 << len(AVAILABILITY_MASK_FLAGS)
GENERAL_PROFILE_TABLES = {
    "general_profile_payloads": Table(("id",), ("body",)),
    "general_profile_selections": Table(("unit_id", "mask"), ("payload_id",)),
}
ARMY_V32_PUBLISHED_TABLES = {**ARMY_V31_PUBLISHED_TABLES, **GENERAL_PROFILE_TABLES}
# v33 retains the relational layout but stores complete, pre-classification rows.
ARMY_V33_PUBLISHED_TABLES = ARMY_V32_PUBLISHED_TABLES


def availability_mask(flags: frozenset[str]) -> int:
    return sum(1 << bit for bit, flag in enumerate(AVAILABILITY_MASK_FLAGS) if flag in flags)


def flags_for_mask(mask: int) -> dict[str, bool]:
    return {flag: bool(mask & (1 << bit)) for bit, flag in enumerate(AVAILABILITY_MASK_FLAGS)}


def encode_profiles(profiles: object) -> str:
    return json.dumps(profiles, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def validate_general_profiles(connection: sqlite3.Connection) -> None:
    """Require a complete selection matrix and referenced, valid JSON payloads."""
    unit_count = connection.execute("SELECT COUNT(*) FROM logical_units").fetchone()[0]
    selection_count = connection.execute(
        "SELECT COUNT(*) FROM general_profile_selections"
    ).fetchone()[0]
    if selection_count != unit_count * MASK_COUNT or connection.execute(
        "SELECT 1 FROM general_profile_selections AS s "
        "LEFT JOIN logical_units AS u ON u.id=s.unit_id "
        "LEFT JOIN general_profile_payloads AS p ON p.id=s.payload_id "
        "WHERE u.id IS NULL OR p.id IS NULL OR s.mask NOT BETWEEN 0 AND 15 LIMIT 1"
    ).fetchone() is not None:
        raise ValueError("Incomplete General-profile selection matrix")
    if connection.execute(
        "SELECT 1 FROM general_profile_payloads AS p "
        "LEFT JOIN general_profile_selections AS s ON s.payload_id=p.id "
        "WHERE s.payload_id IS NULL OR NOT json_valid(p.body) "
        "OR json_type(p.body) != 'array' LIMIT 1"
    ).fetchone() is not None:
        raise ValueError("Invalid or unreferenced General-profile payload")


def read_general_profiles(
    connection: sqlite3.Connection, unit_ids: Sequence[int], mask: int,
) -> dict[int, list[dict[str, Any]]]:
    if not unit_ids:
        return {}
    placeholders = ", ".join("?" for _ in unit_ids)
    result = {
        unit_id: json.loads(body)
        for unit_id, body in connection.execute(
            "SELECT s.unit_id,p.body FROM general_profile_selections AS s "
            "JOIN general_profile_payloads AS p ON p.id=s.payload_id "
            f"WHERE s.mask=? AND s.unit_id IN ({placeholders})", (mask, *unit_ids),
        )
    }
    if set(result) != set(unit_ids):
        raise ValueError("Incomplete materialized General-profile selection")
    return result


def write_general_profiles(
    army: Path, compose: Callable[[int, dict[str, bool]], list[dict[str, Any]]],
) -> None:
    """Extend a validated v31 Army publication in deterministic Unit/mask order."""
    with closing(sqlite3.connect(army)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("PRAGMA user_version").fetchone()[0] != PREVIOUS_SCHEMA_VERSION:
            raise ValueError("General-profile publication requires Army v31")
        unit_ids = [row[0] for row in db.execute("SELECT id FROM logical_units ORDER BY id")]
        payload_ids: dict[str, int] = {}
        with db:
            db.execute("""CREATE TABLE general_profile_payloads (
                id INTEGER PRIMARY KEY, body TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE general_profile_selections (
                unit_id INTEGER NOT NULL REFERENCES logical_units(id),
                mask INTEGER NOT NULL CHECK(mask BETWEEN 0 AND 15),
                payload_id INTEGER NOT NULL REFERENCES general_profile_payloads(id),
                PRIMARY KEY(unit_id, mask)
            ) WITHOUT ROWID""")
            for unit_id in unit_ids:
                for mask in range(MASK_COUNT):
                    body = encode_profiles(compose(unit_id, flags_for_mask(mask)))
                    payload_id = payload_ids.get(body)
                    if payload_id is None:
                        payload_id = len(payload_ids) + 1
                        db.execute("INSERT INTO general_profile_payloads VALUES (?,?)",
                                   (payload_id, body))
                        payload_ids[body] = payload_id
                    db.execute("INSERT INTO general_profile_selections VALUES (?,?,?)",
                               (unit_id, mask, payload_id))
            validate_general_profiles(db)
            checksum = published_content_sha256(db, definitions=ARMY_V33_PUBLISHED_TABLES)
            db.executemany(
                f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                [(json.dumps(checksum), PUBLISHED_CONTENT_SHA256_KEY),
                 (json.dumps(ARMY_COMPATIBILITY_VERSION), DATABASE_COMPATIBILITY_KEY)],
            )
            db.execute(f"PRAGMA user_version={ARMY_SCHEMA_VERSION}")
        vacuum_deterministic_sqlite(db)
    normalize_sqlite_header(army)


def publish_general_profiles(army: Path, rules: Path) -> None:
    """Use the core Rules model and embedded Army catalogs/symbols, not HTTP."""
    from .database.repository import Database
    from .equipment_catalog import EquipmentCatalog
    from .rules_database import RulesDatabase
    from .skill_catalog import SkillCatalog
    from .symbol_catalog import SymbolCatalog
    from .unit_composition import present_unit
    from .unit_presentation import OPTIONAL_AVAILABILITY_FLAGS, extended_general_profiles

    if OPTIONAL_AVAILABILITY_FLAGS != AVAILABILITY_MASK_FLAGS:
        raise ValueError("General-profile availability mask contract changed")
    database = Database(army)
    database.validate()
    rules_database = RulesDatabase(rules)
    skill_catalog = SkillCatalog(database, rules_database)
    equipment_catalog = EquipmentCatalog(database, rules_database)
    symbol_catalog = SymbolCatalog(publication=database.symbol_publication())
    classifications = database.skill_source_classifications()

    # Compose before the write transaction so the read-only repository can open
    # independent connections without locking against SQLite's writer.
    with database._connect() as connection:
        unit_ids = [
            row[0] for row in connection.execute("SELECT id FROM logical_units ORDER BY id")
        ]
    projections: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for unit_id in unit_ids:
        unit = database.get_unit(unit_id)
        if unit is None:
            raise ValueError(f"Missing logical Unit {unit_id}")
        for mask in range(MASK_COUNT):
            flags = flags_for_mask(mask)
            projections[unit_id, mask] = extended_general_profiles(present_unit(
                unit, database=database, skill_catalog=skill_catalog,
                equipment_catalog=equipment_catalog, symbol_catalog=symbol_catalog,
                source_skill_classifications=classifications, optional_filters=flags,
                general_only=True, classify_general=False,
            ), include_hidden=True)
    write_general_profiles(army, lambda unit_id, flags: projections[
        unit_id, availability_mask(frozenset(flag for flag, enabled in flags.items() if enabled))
    ])
