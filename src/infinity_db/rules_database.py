"""Build the independent SQLite snapshot for curated rules references."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

RULES_APPLICATION_ID = 0x49445231
RULES_SCHEMA_VERSION = 1
RULES_COMPATIBILITY_VERSION = 1
RULES_METADATA_TABLE = "__rules_metadata"


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _insert_many(
    connection: sqlite3.Connection, statement: str, rows: list[tuple[Any, ...]]
) -> None:
    if rows:
        connection.executemany(statement, rows)


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(f"PRAGMA application_id = {RULES_APPLICATION_ID}")
    connection.execute(f"PRAGMA user_version = {RULES_SCHEMA_VERSION}")
    connection.executescript(
        f"""
        CREATE TABLE {RULES_METADATA_TABLE} (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE collections (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            domain TEXT NOT NULL,
            status TEXT NOT NULL,
            effective_from TEXT NOT NULL,
            authority TEXT NOT NULL
        );
        CREATE TABLE sources (
            collection_id TEXT NOT NULL,
            id TEXT NOT NULL,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            version TEXT NOT NULL,
            published_date TEXT,
            snapshot_date TEXT,
            local_path TEXT,
            url TEXT,
            page_count INTEGER,
            authority TEXT NOT NULL,
            PRIMARY KEY (collection_id, id),
            FOREIGN KEY (collection_id) REFERENCES collections(id)
        );
        CREATE TABLE vocabulary_sources (
            collection_id TEXT NOT NULL,
            vocabulary TEXT NOT NULL,
            position INTEGER NOT NULL,
            source_id TEXT NOT NULL,
            path TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            heading TEXT NOT NULL,
            page INTEGER NOT NULL,
            PRIMARY KEY (collection_id, vocabulary, position),
            FOREIGN KEY (collection_id, source_id)
                REFERENCES sources(collection_id, id)
        );
        CREATE TABLE skill_types (
            collection_id TEXT NOT NULL,
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            labels_json TEXT NOT NULL,
            descriptions_json TEXT NOT NULL,
            PRIMARY KEY (collection_id, id),
            FOREIGN KEY (collection_id) REFERENCES collections(id)
        );
        CREATE TABLE labels (
            collection_id TEXT NOT NULL,
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            PRIMARY KEY (collection_id, id),
            FOREIGN KEY (collection_id) REFERENCES collections(id)
        );
        CREATE TABLE records (
            collection_id TEXT NOT NULL,
            id TEXT NOT NULL,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            summary TEXT NOT NULL,
            aliases_json TEXT,
            label_ids_json TEXT,
            scope_json TEXT,
            facts_json TEXT,
            review_json TEXT,
            PRIMARY KEY (collection_id, id),
            FOREIGN KEY (collection_id) REFERENCES collections(id)
        );
        CREATE TABLE record_citations (
            collection_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            source_id TEXT NOT NULL,
            page INTEGER,
            path TEXT,
            snapshot_date TEXT,
            heading TEXT,
            section TEXT,
            PRIMARY KEY (collection_id, record_id, position),
            FOREIGN KEY (collection_id, record_id)
                REFERENCES records(collection_id, id),
            FOREIGN KEY (collection_id, source_id)
                REFERENCES sources(collection_id, id)
        );
        CREATE TABLE record_army_links (
            collection_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            entity TEXT NOT NULL,
            external_id TEXT,
            external_name TEXT,
            PRIMARY KEY (collection_id, record_id, position),
            FOREIGN KEY (collection_id, record_id)
                REFERENCES records(collection_id, id)
        );
        CREATE TABLE record_relations (
            collection_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            related_record_id TEXT NOT NULL,
            PRIMARY KEY (collection_id, record_id, position),
            FOREIGN KEY (collection_id, record_id)
                REFERENCES records(collection_id, id)
        );
        CREATE INDEX records_kind_name ON records(kind, name COLLATE NOCASE);
        CREATE INDEX record_citations_source ON record_citations(collection_id, source_id);
        CREATE INDEX record_army_links_entity ON record_army_links(entity, external_id);
        """
    )


def _validate_documents(documents: list[tuple[Path, dict[str, Any]]]) -> None:
    collection_ids: set[str] = set()
    for path, document in documents:
        collection_id = document["collection"]["id"]
        if collection_id in collection_ids:
            raise ValueError(f"Duplicate curated collection id {collection_id!r}: {path}")
        collection_ids.add(collection_id)


def _insert_document(connection: sqlite3.Connection, document: dict[str, Any]) -> None:
    collection = document["collection"]
    collection_id = collection["id"]
    connection.execute(
        "INSERT INTO collections "
        "(id, title, domain, status, effective_from, authority) VALUES (?, ?, ?, ?, ?, ?)",
        (
            collection_id,
            collection["title"],
            collection["domain"],
            collection["status"],
            collection["effectiveFrom"],
            collection["authority"],
        ),
    )

    _insert_many(
        connection,
        "INSERT INTO sources "
        "(collection_id, id, kind, title, version, published_date, snapshot_date, "
        "local_path, url, page_count, authority) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                collection_id,
                source["id"],
                source["kind"],
                source["title"],
                source["version"],
                source.get("publishedDate"),
                source.get("snapshotDate"),
                source.get("localPath"),
                source.get("url"),
                source.get("pageCount"),
                source["authority"],
            )
            for source in document["sources"]
        ],
    )

    for vocabulary_name in ("skillTypes", "labels"):
        _insert_many(
            connection,
            "INSERT INTO vocabulary_sources "
            "(collection_id, vocabulary, position, source_id, path, snapshot_date, heading, page) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    collection_id,
                    vocabulary_name,
                    position,
                    source["sourceId"],
                    source["path"],
                    source["snapshotDate"],
                    source["heading"],
                    source["page"],
                )
                for position, source in enumerate(document["vocabularySources"][vocabulary_name])
            ],
        )

    _insert_many(
        connection,
        "INSERT INTO skill_types "
        "(collection_id, id, name, labels_json, descriptions_json) VALUES (?, ?, ?, ?, ?)",
        [
            (
                collection_id,
                skill_type["id"],
                skill_type["name"],
                _json_text(skill_type["labels"]),
                _json_text(skill_type["descriptions"]),
            )
            for skill_type in document["skillTypes"]
        ],
    )
    _insert_many(
        connection,
        "INSERT INTO labels (collection_id, id, name, description) VALUES (?, ?, ?, ?)",
        [
            (collection_id, label["id"], label["name"], label["description"])
            for label in document["labels"]
        ],
    )

    _insert_many(
        connection,
        "INSERT INTO records "
        "(collection_id, id, kind, name, summary, aliases_json, label_ids_json, scope_json, "
        "facts_json, review_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                collection_id,
                record["id"],
                record["kind"],
                record["name"],
                record["summary"],
                _json_text(record["aliases"]) if "aliases" in record else None,
                _json_text(record["labelIds"]) if "labelIds" in record else None,
                _json_text(record["scope"]) if "scope" in record else None,
                _json_text(record["facts"]) if "facts" in record else None,
                _json_text(record["review"]) if "review" in record else None,
            )
            for record in document["records"]
        ],
    )

    for record in document["records"]:
        record_id = record["id"]
        _insert_many(
            connection,
            "INSERT INTO record_citations "
            "(collection_id, record_id, position, source_id, page, path, "
            "snapshot_date, heading, section) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    collection_id,
                    record_id,
                    position,
                    citation["sourceId"],
                    citation.get("page"),
                    citation.get("path"),
                    citation.get("snapshotDate"),
                    citation.get("heading"),
                    citation.get("section"),
                )
                for position, citation in enumerate(record["citations"])
            ],
        )
        _insert_many(
            connection,
            "INSERT INTO record_army_links "
            "(collection_id, record_id, position, entity, external_id, external_name) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    collection_id,
                    record_id,
                    position,
                    link["entity"],
                    str(link["id"]) if "id" in link else None,
                    link.get("name"),
                )
                for position, link in enumerate(record.get("armyLinks", []))
            ],
        )
        _insert_many(
            connection,
            "INSERT INTO record_relations "
            "(collection_id, record_id, position, related_record_id) VALUES (?, ?, ?, ?)",
            [
                (collection_id, record_id, position, related_id)
                for position, related_id in enumerate(record.get("relatedRecords", []))
            ],
        )


def export_rules_database(documents: list[tuple[Path, dict[str, Any]]], path: Path) -> None:
    """Atomically replace a rules database from validated curated documents."""
    if not documents:
        raise ValueError("No curated documents supplied")
    _validate_documents(documents)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(filename)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                _create_schema(connection)
                for _, document in documents:
                    _insert_document(connection, document)
                metadata = {
                    "format": "InfinityDB curated rules database",
                    "formatVersion": 1,
                    "collectionCount": len(documents),
                    "databaseCompatibilityVersion": RULES_COMPATIBILITY_VERSION,
                }
                _insert_many(
                    connection,
                    f"INSERT INTO {RULES_METADATA_TABLE} (key, value) VALUES (?, ?)",
                    [(key, _json_text(value)) for key, value in metadata.items()],
                )
                connection.execute("ANALYZE")
        finally:
            connection.close()
        check = sqlite3.connect(temporary)
        try:
            if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Rules database integrity check failed")
            if check.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("Rules database contains broken foreign keys")
        finally:
            check.close()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _decode_json(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


class RulesDatabase:
    """Read-only queries over the independent curated rules snapshot."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise ValueError(f"Rules database does not exist: {self.path}")
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def validate(self) -> None:
        with self._connect() as connection:
            if connection.execute("PRAGMA application_id").fetchone()[0] != RULES_APPLICATION_ID:
                raise ValueError("Unsupported rules database application ID")
            if connection.execute("PRAGMA user_version").fetchone()[0] != RULES_SCHEMA_VERSION:
                raise ValueError("Unsupported rules database schema; rebuild rules.db")
            metadata = connection.execute(
                f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key = ?",
                ("databaseCompatibilityVersion",),
            ).fetchone()
            if (
                metadata is None
                or _decode_json(metadata["value"], None) != RULES_COMPATIBILITY_VERSION
            ):
                raise ValueError(
                    "Rules database compatibility revision does not match this application"
                )
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Rules database integrity check failed")

    def _records_from_rows(
        self, connection: sqlite3.Connection, rows: list[sqlite3.Row]
    ) -> list[dict[str, Any]]:
        records = []
        for row in rows:
            record = {
                "id": row["id"],
                "kind": row["kind"],
                "name": row["name"],
                "summary": row["summary"],
                "aliases": _decode_json(row["aliases_json"], []),
                "label_ids": _decode_json(row["label_ids_json"], []),
                "scope": _decode_json(row["scope_json"], None),
                "facts": _decode_json(row["facts_json"], None),
                "review": _decode_json(row["review_json"], None),
            }
            label_ids = record["label_ids"]
            if label_ids:
                placeholders = ", ".join("?" for _ in label_ids)
                label_rows = connection.execute(
                    "SELECT id, name, description FROM labels "
                    "WHERE collection_id = ? AND id IN (" + placeholders + ")",
                    (row["collection_id"], *label_ids),
                ).fetchall()
                record["labels"] = [dict(label) for label in label_rows]
            facts = record["facts"]
            if isinstance(facts, dict) and facts.get("typeId"):
                skill_type = connection.execute(
                    "SELECT id, name, labels_json, descriptions_json FROM skill_types "
                    "WHERE collection_id = ? AND id = ?",
                    (row["collection_id"], facts["typeId"]),
                ).fetchone()
                if skill_type is not None:
                    record["skill_type"] = {
                        "id": skill_type["id"],
                        "name": skill_type["name"],
                        "labels": _decode_json(skill_type["labels_json"], []),
                        "descriptions": _decode_json(skill_type["descriptions_json"], {}),
                    }
            record["citations"] = [
                dict(citation)
                for citation in connection.execute(
                    "SELECT c.source_id, s.title AS source_title, s.version AS source_version, "
                    "c.page, c.path, c.snapshot_date, c.heading, c.section "
                    "FROM record_citations AS c JOIN sources AS s "
                    "ON s.collection_id = c.collection_id AND s.id = c.source_id "
                    "WHERE c.collection_id = ? AND c.record_id = ? ORDER BY c.position",
                    (row["collection_id"], row["id"]),
                ).fetchall()
            ]
            record["related_records"] = [
                relation["related_record_id"]
                for relation in connection.execute(
                    "SELECT related_record_id FROM record_relations "
                    "WHERE collection_id = ? AND record_id = ? ORDER BY position",
                    (row["collection_id"], row["id"]),
                ).fetchall()
            ]
            records.append(record)
        return records

    def records_for_army_link(self, entity: str, external_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT r.* FROM records AS r "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "WHERE l.entity = ? AND l.external_id = ? "
                "ORDER BY r.collection_id, r.id",
                (entity, str(external_id)),
            ).fetchall()
            return self._records_from_rows(connection, rows)

    def skill_parameter_semantics(self) -> dict[int, dict[str, str]]:
        """Return curated skill parameter semantics keyed to Army skill ids."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT CAST(l.external_id AS INTEGER) AS skill_id, r.facts_json "
                "FROM records AS r JOIN collections AS c ON c.id = r.collection_id "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "WHERE r.kind = 'skill' AND c.status = 'current' "
                "AND l.entity = 'skill' AND l.external_id IS NOT NULL "
                "ORDER BY skill_id, r.collection_id, r.id"
            ).fetchall()
            result: dict[int, dict[str, str]] = {}
            for row in rows:
                facts = _decode_json(row["facts_json"], {})
                semantics = facts.get("parameterSemantics") if isinstance(facts, dict) else None
                if not isinstance(semantics, dict):
                    continue
                value = {
                    "kind": semantics["kind"],
                    "positive_sign": semantics["positiveSign"],
                }
                existing = result.get(row["skill_id"])
                if existing is not None and existing != value:
                    raise ValueError(
                        f"Skill {row['skill_id']} has conflicting curated parameter semantics"
                    )
                result[row["skill_id"]] = value
            return result

    def skill_declaration_categories(self) -> list[dict[str, Any]]:
        """Return curated skill declaration categories keyed to Army skill ids."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT CAST(l.external_id AS INTEGER) AS skill_id, r.name, r.facts_json, "
                "s.title AS source_title, s.version AS source_version, c.page "
                "FROM records AS r JOIN collections AS col ON col.id = r.collection_id "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "JOIN record_citations AS c ON c.collection_id = r.collection_id "
                "AND c.record_id = r.id "
                "JOIN sources AS s ON s.collection_id = c.collection_id "
                "AND s.id = c.source_id "
                "WHERE r.kind = 'skill-declaration-category' "
                "AND col.status = 'current' AND l.entity = 'skill' "
                "AND l.external_id IS NOT NULL "
                "ORDER BY skill_id, r.collection_id, r.id, c.position"
            ).fetchall()
            result = []
            for row in rows:
                facts = _decode_json(row["facts_json"], {})
                result.append(
                    {
                        "skill_id": row["skill_id"],
                        "name": row["name"],
                        "order": facts["order"],
                        "source_title": row["source_title"],
                        "source_version": row["source_version"],
                        "page": row["page"],
                    }
                )
            return result

    def records_by_kind(self, kind: str, *, current_only: bool = True) -> list[dict[str, Any]]:
        """Return curated records of one kind, preferring current collections."""
        with self._connect() as connection:
            if current_only:
                rows = connection.execute(
                    "SELECT r.* FROM records AS r JOIN collections AS c "
                    "ON c.id = r.collection_id "
                    "WHERE r.kind = ? AND c.status = 'current' "
                    "ORDER BY r.collection_id, r.id",
                    (kind,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT r.* FROM records AS r WHERE r.kind = ? "
                    "ORDER BY r.collection_id, r.id",
                    (kind,),
                ).fetchall()
            return self._records_from_rows(connection, rows)
