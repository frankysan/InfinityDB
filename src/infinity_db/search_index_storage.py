"""Compact SQLite projection of canonical public search results and terms."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .build_provenance import canonical_bytes, file_sha256
from .database.repository import Database, accent_insensitive_key
from .equipment_catalog import EquipmentCatalog
from .glossary_catalog import GlossaryCatalog
from .hacking_program_catalog import HackingProgramCatalog
from .publication_registry import PublicationRegistry
from .reference_catalog import LabelCatalog, RulesRecordCatalog
from .rules_database import (
    COMPOSED_SCHEMA_VERSION,
    RULES_METADATA_TABLE,
    SEARCH_INDEX_COMPATIBILITY_VERSION,
    SEARCH_INDEX_SCHEMA_VERSION,
    RulesDatabase,
)
from .scenario_catalog import ScenarioCatalog
from .search_catalog import SearchCatalog, SearchEntry, rank_results
from .skill_catalog import SkillCatalog
from .sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from .state_catalog import StateCatalog
from .trait_catalog import TraitCatalog


def stage_search_index(connection: sqlite3.Connection, entries: Iterable[SearchEntry]) -> None:
    """Store one result per canonical occurrence, with separate normalized terms."""
    connection.execute(
        "CREATE TABLE search_index (position INTEGER PRIMARY KEY, result TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE search_index_terms (position INTEGER NOT NULL "
        "REFERENCES search_index(position), term TEXT NOT NULL, "
        "PRIMARY KEY(position,term)) WITHOUT ROWID"
    )
    for position, (result, terms) in enumerate(entries):
        connection.execute(
            "INSERT INTO search_index VALUES (?,?)",
            (position, json.dumps(result, ensure_ascii=False, separators=(",", ":"))),
        )
        connection.executemany(
            "INSERT INTO search_index_terms VALUES (?,?)",
            [(position, term) for term in terms],
        )


def query_search_index(connection: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    """Apply the existing substring match and ranking to the compact projection."""
    needle = accent_insensitive_key(query)
    if not needle:
        return []
    results = [
        json.loads(row[0])
        for row in connection.execute(
            "SELECT result FROM search_index WHERE position IN "
            "(SELECT position FROM search_index_terms WHERE instr(term,?)>0) "
            "ORDER BY position",
            (needle,),
        )
    ]
    return rank_results(results, needle)


def search_scope(army_sha256: str, seasons: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    """Bind external publications, including registry order for stable result ties."""
    return {
        "army": army_sha256,
        "seasons": [[season, manifest["sha256"]] for season, manifest in seasons.items()],
    }


def _index_sha256(connection: sqlite3.Connection, scope: dict[str, Any]) -> str:
    entries = [tuple(row) for row in connection.execute(
        "SELECT position,result FROM search_index ORDER BY position"
    )]
    terms = [tuple(row) for row in connection.execute(
        "SELECT position,term FROM search_index_terms ORDER BY position,term"
    )]
    return hashlib.sha256(canonical_bytes([scope, entries, terms])).hexdigest()


def _metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='searchIndex'"
    ).fetchone()
    if row is None:
        raise ValueError("Missing global search publication metadata")
    return json.loads(row[0])


def validate_search_index(connection: sqlite3.Connection) -> None:
    metadata = _metadata(connection)
    if (
        not isinstance(metadata, dict)
        or set(metadata) != {"scope", "sha256"}
        or not isinstance(metadata["scope"], dict)
        or connection.execute("SELECT COUNT(*) FROM search_index").fetchone()[0] == 0
        or metadata["sha256"] != _index_sha256(connection, metadata["scope"])
    ):
        raise ValueError("Invalid global search publication fingerprint")


@dataclass(frozen=True)
class PublishedSearchIndex:
    """Read the matching immutable projection, or retain the explicit legacy path."""

    path: Path

    @classmethod
    def select(cls, rules_path: Path, scope: dict[str, Any]) -> PublishedSearchIndex | None:
        with closing(sqlite3.connect(rules_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA user_version").fetchone()[0] < SEARCH_INDEX_SCHEMA_VERSION:
                return None
            if _metadata(db)["scope"] != scope:
                return None
        return cls(rules_path)

    def search(self, query: str) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            return query_search_index(db, query)


def publish_search_index(
    army_path: Path, rules_path: Path, season_paths: Mapping[str, Path],
) -> None:
    """Finalize Rules after the other database bytes are stable."""
    database = Database(army_path)
    rules = RulesDatabase(rules_path, immutable_snapshot=True)
    registry = PublicationRegistry(rules, season_paths)
    catalog = SearchCatalog(
        database,
        SkillCatalog(database, rules, ScenarioCatalog(rules, registry)),
        EquipmentCatalog(database, rules),
        TraitCatalog(database, rules),
        StateCatalog(rules, registry),
        HackingProgramCatalog(database, rules),
        RulesRecordCatalog(rules, "ammunition"),
        LabelCatalog(rules),
        RulesRecordCatalog(rules, "rules"),
        GlossaryCatalog(database, rules),
        database.army_reference_data()[1],
    )
    entries = list(catalog.entries())
    scope = search_scope(file_sha256(army_path), registry.season_manifest())
    with closing(sqlite3.connect(rules_path)) as db:
        with db:
            if db.execute("PRAGMA user_version").fetchone()[0] != COMPOSED_SCHEMA_VERSION:
                raise ValueError("Global search publication requires composed Rules v18")
            stage_search_index(db, entries)
            metadata = {"scope": scope, "sha256": _index_sha256(db, scope)}
            db.execute(
                f"INSERT INTO {RULES_METADATA_TABLE} VALUES (?,?)",
                ("searchIndex", canonical_bytes(metadata).decode("utf-8")),
            )
            db.execute(f"PRAGMA user_version={SEARCH_INDEX_SCHEMA_VERSION}")
            for key, value in (
                ("formatVersion", SEARCH_INDEX_SCHEMA_VERSION),
                ("databaseCompatibilityVersion", SEARCH_INDEX_COMPATIBILITY_VERSION),
            ):
                db.execute(
                    f"UPDATE {RULES_METADATA_TABLE} SET value=? WHERE key=?", (str(value), key),
                )
            validate_search_index(db)
        vacuum_deterministic_sqlite(db)
    normalize_sqlite_header(rules_path)
