"""Build the independent SQLite snapshot for curated rules references."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

RULES_APPLICATION_ID = 0x49445231
RULES_SCHEMA_VERSION = 5
RULES_COMPATIBILITY_VERSION = 5
RULES_METADATA_TABLE = "__rules_metadata"
ArmyLinkRef = int | str


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _army_link_ref(value: object) -> ArmyLinkRef:
    text = str(value)
    return int(text) if text.isdecimal() else text


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
            retrieved_date TEXT,
            acquired_at TEXT,
            local_path TEXT,
            url TEXT,
            sha256 TEXT,
            language TEXT,
            document_count INTEGER,
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
            page INTEGER,
            member TEXT,
            heading TEXT NOT NULL,
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
            composition_role TEXT NOT NULL,
            aliases_json TEXT,
            label_ids_json TEXT,
            scope_json TEXT,
            facts_json TEXT,
            variant_json TEXT,
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
            member TEXT,
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
            relation_type TEXT NOT NULL,
            related_record_id TEXT NOT NULL,
            PRIMARY KEY (collection_id, record_id, position),
            FOREIGN KEY (collection_id, record_id)
                REFERENCES records(collection_id, id)
        );
        CREATE INDEX records_kind_name ON records(kind, name COLLATE NOCASE);
        CREATE INDEX record_citations_source ON record_citations(collection_id, source_id);
        CREATE INDEX record_army_links_entity ON record_army_links(entity, external_id);
        CREATE INDEX record_relations_target ON record_relations(related_record_id);
        """
    )


def _validate_documents(documents: list[tuple[Path, dict[str, Any]]]) -> None:
    collection_ids: set[str] = set()
    current_records: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path, document in documents:
        collection_id = document["collection"]["id"]
        if collection_id in collection_ids:
            raise ValueError(f"Duplicate curated collection id {collection_id!r}: {path}")
        collection_ids.add(collection_id)
        if document["collection"]["status"] != "current":
            continue
        for record in document["records"]:
            current_records.setdefault(record["id"], []).append((path, record))

    current_ids = set(current_records)
    definitions_by_id: dict[str, tuple[Path, dict[str, Any]]] = {}
    for record_id, contributions in current_records.items():
        definitions = [
            (path, record)
            for path, record in contributions
            if record["composition"]["role"] == "definition"
        ]
        if len(definitions) != 1:
            sources = ", ".join(str(path) for path, _ in contributions)
            raise ValueError(
                f"Current rules record {record_id!r} requires exactly one definition "
                f"contribution; found {len(definitions)} across {sources}"
            )
        definitions_by_id[record_id] = definitions[0]

        for path, record in contributions:
            for relation in record.get("relations", []):
                target_id = relation["recordId"]
                if target_id not in current_ids:
                    raise ValueError(
                        f"Current rules relation {record_id!r} -> {target_id!r} in {path} "
                        "does not resolve to a current semantic record"
                    )

    for record_id, (path, definition) in definitions_by_id.items():
        variant = definition.get("variantSemantics")
        if not isinstance(variant, dict) or variant.get("inheritance") != "source":
            continue
        family_targets = [
            relation["recordId"]
            for relation in definition.get("relations", [])
            if relation["type"] == "variant-of"
        ]
        if len(family_targets) != 1:
            raise ValueError(
                f"Source-specific rules record {record_id!r} in {path} requires exactly "
                "one 'variant-of' relation"
            )
        family_id = family_targets[0]
        family_definition = definitions_by_id.get(family_id)
        if family_definition is None:
            raise ValueError(
                f"Source-specific rules record {record_id!r} references missing family "
                f"definition {family_id!r}"
            )
        _, family = family_definition
        if family["kind"] != definition["kind"]:
            raise ValueError(
                f"Source-specific rules record {record_id!r} must reference a family "
                "record of the same kind"
            )
        family_variant = family.get("variantSemantics")
        if not isinstance(family_variant, dict) or family_variant.get("inheritance") != "family":
            raise ValueError(
                f"Source-specific rules record {record_id!r} requires family target "
                f"{family_id!r} to declare family inheritance"
            )


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
        "(collection_id, id, kind, title, version, published_date, retrieved_date, "
        "acquired_at, local_path, url, sha256, language, document_count, page_count, authority) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                collection_id,
                source["id"],
                source["kind"],
                source["title"],
                source["version"],
                source.get("publishedDate"),
                source.get("retrievedDate"),
                source.get("acquiredAt"),
                source.get("localPath"),
                source.get("url"),
                source.get("sha256"),
                source.get("language"),
                source.get("documentCount"),
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
            "(collection_id, vocabulary, position, source_id, page, member, heading) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    collection_id,
                    vocabulary_name,
                    position,
                    source["sourceId"],
                    source.get("page"),
                    source.get("member"),
                    source["heading"],
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
        "(collection_id, id, kind, name, summary, composition_role, aliases_json, "
        "label_ids_json, scope_json, facts_json, variant_json, review_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                collection_id,
                record["id"],
                record["kind"],
                record["name"],
                record["summary"],
                record["composition"]["role"],
                _json_text(record["aliases"]) if "aliases" in record else None,
                _json_text(record["labelIds"]) if "labelIds" in record else None,
                _json_text(record["scope"]) if "scope" in record else None,
                _json_text(record["facts"]) if "facts" in record else None,
                (
                    _json_text(record["variantSemantics"])
                    if "variantSemantics" in record
                    else None
                ),
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
            "(collection_id, record_id, position, source_id, page, member, heading, section) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    collection_id,
                    record_id,
                    position,
                    citation["sourceId"],
                    citation.get("page"),
                    citation.get("member"),
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
            "(collection_id, record_id, position, relation_type, related_record_id) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (
                    collection_id,
                    record_id,
                    position,
                    relation["type"],
                    relation["recordId"],
                )
                for position, relation in enumerate(record.get("relations", []))
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
                    "formatVersion": RULES_SCHEMA_VERSION,
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


def _variant_semantics(value: str | None) -> dict[str, Any] | None:
    raw = _decode_json(value, None)
    if not isinstance(raw, dict):
        return None
    parameters = []
    for parameter in raw.get("occurrenceParameters", []):
        item = {
            "source": parameter["source"],
            "kind": parameter["kind"],
        }
        if "positiveSign" in parameter:
            item["positive_sign"] = parameter["positiveSign"]
        parameters.append(item)
    result: dict[str, Any] = {"inheritance": raw["inheritance"]}
    if parameters:
        result["occurrence_parameters"] = parameters
    return result


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
        collections: dict[str, dict[str, Any]] = {}
        for row in rows:
            collection_id = str(row["collection_id"])
            collection = collections.get(collection_id)
            if collection is None:
                collection_row = connection.execute(
                    "SELECT id, title, domain, status, effective_from, authority "
                    "FROM collections WHERE id = ?",
                    (collection_id,),
                ).fetchone()
                if collection_row is None:
                    raise ValueError(f"Rules record {row['id']!r} has no collection")
                collection = dict(collection_row)
                collections[collection_id] = collection
            record = {
                "id": row["id"],
                "kind": row["kind"],
                "name": row["name"],
                "summary": row["summary"],
                "composition": {"role": row["composition_role"]},
                "aliases": _decode_json(row["aliases_json"], []),
                "label_ids": _decode_json(row["label_ids_json"], []),
                "scope": _decode_json(row["scope_json"], None),
                "facts": _decode_json(row["facts_json"], None),
                "variant_semantics": _variant_semantics(row["variant_json"]),
                "review": _decode_json(row["review_json"], None),
                "collection": dict(collection),
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
                    "s.url AS source_url, c.page, c.member, c.heading, c.section "
                    "FROM record_citations AS c JOIN sources AS s "
                    "ON s.collection_id = c.collection_id AND s.id = c.source_id "
                    "WHERE c.collection_id = ? AND c.record_id = ? ORDER BY c.position",
                    (row["collection_id"], row["id"]),
                ).fetchall()
            ]
            record["relations"] = [
                {
                    "type": relation["relation_type"],
                    "record_id": relation["related_record_id"],
                }
                for relation in connection.execute(
                    "SELECT relation_type, related_record_id FROM record_relations "
                    "WHERE collection_id = ? AND record_id = ? ORDER BY position",
                    (row["collection_id"], row["id"]),
                ).fetchall()
            ]
            record["related_records"] = [
                relation["record_id"] for relation in record["relations"]
            ]
            records.append(record)
        return records

    @staticmethod
    def _compose_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            grouped.setdefault(record["id"], []).append(record)

        result = []
        for record_id in sorted(grouped):
            contributions = grouped[record_id]
            definitions = [
                record
                for record in contributions
                if record["composition"]["role"] == "definition"
            ]
            if len(definitions) != 1:
                raise ValueError(
                    f"Current rules record {record_id!r} requires exactly one definition"
                )
            definition = deepcopy(definitions[0])
            supplements = [
                deepcopy(record)
                for record in contributions
                if record["composition"]["role"] == "supplement"
            ]
            supplements.sort(
                key=lambda record: (
                    record["collection"]["effective_from"],
                    record["collection"]["id"],
                )
            )
            if supplements:
                definition["supplements"] = supplements

            combined_relations: list[dict[str, Any]] = []
            seen_relations: set[tuple[str, str, str]] = set()
            for contribution in [definition, *supplements]:
                collection_id = contribution["collection"]["id"]
                for relation in contribution.get("relations", []):
                    key = (relation["type"], relation["record_id"], collection_id)
                    if key in seen_relations:
                        continue
                    seen_relations.add(key)
                    combined_relations.append(
                        {
                            **relation,
                            "collection_id": collection_id,
                        }
                    )
            definition["relations"] = combined_relations
            definition["related_records"] = list(
                dict.fromkeys(relation["record_id"] for relation in combined_relations)
            )
            result.append(definition)
        return result

    @staticmethod
    def _attach_reverse_relations(
        connection: sqlite3.Connection, records: list[dict[str, Any]]
    ) -> None:
        for record in records:
            rows = connection.execute(
                "SELECT rr.collection_id, rr.record_id, rr.relation_type "
                "FROM record_relations AS rr JOIN collections AS c "
                "ON c.id = rr.collection_id "
                "WHERE rr.related_record_id = ? AND c.status = 'current' "
                "ORDER BY rr.collection_id, rr.record_id, rr.position",
                (record["id"],),
            ).fetchall()
            if rows:
                record["reverse_relations"] = [
                    {
                        "type": row["relation_type"],
                        "record_id": row["record_id"],
                        "collection_id": row["collection_id"],
                    }
                    for row in rows
                ]

    def composed_records_for_army_link(
        self,
        entity: str,
        external_id: ArmyLinkRef,
    ) -> list[dict[str, Any]]:
        """Return one current semantic record per Army-linked rules identity.

        The Army link may live on any current contribution. Once a semantic record
        ID is selected, all current contributions for that ID are composed without
        field-wise precedence: one definition remains authoritative and any
        supplements retain their own scope, collection provenance, facts, and
        citations.
        """
        with self._connect() as connection:
            linked_rows = connection.execute(
                "SELECT DISTINCT r.id FROM records AS r "
                "JOIN collections AS c ON c.id = r.collection_id "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "WHERE l.entity = ? AND l.external_id = ? AND c.status = 'current' "
                "ORDER BY r.id",
                (entity, str(external_id)),
            ).fetchall()
            record_ids = [row["id"] for row in linked_rows]
            if not record_ids:
                return []
            placeholders = ", ".join("?" for _ in record_ids)
            rows = connection.execute(
                "SELECT r.* FROM records AS r JOIN collections AS c "
                "ON c.id = r.collection_id "
                f"WHERE r.id IN ({placeholders}) AND c.status = 'current' "
                "ORDER BY r.id, r.collection_id",
                record_ids,
            ).fetchall()
            records = self._compose_records(self._records_from_rows(connection, rows))
            self._attach_reverse_relations(connection, records)
            return records

    def composed_records_by_kind(self, kind: str) -> list[dict[str, Any]]:
        """Return current semantic records of one kind with supplements attached."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT r.* FROM records AS r JOIN collections AS c "
                "ON c.id = r.collection_id "
                "WHERE r.kind = ? AND c.status = 'current' "
                "ORDER BY r.id, r.collection_id",
                (kind,),
            ).fetchall()
            records = self._compose_records(self._records_from_rows(connection, rows))
            self._attach_reverse_relations(connection, records)
            return records

    def relations_for_record(
        self, record_id: str, *, current_only: bool = True
    ) -> list[dict[str, Any]]:
        """Return authored outbound and derived reverse links for one semantic record."""
        with self._connect() as connection:
            status_clause = "AND c.status = 'current' " if current_only else ""
            rows = connection.execute(
                "SELECT rr.collection_id, rr.record_id, rr.relation_type, "
                "rr.related_record_id, c.title AS collection_title, "
                "c.status AS collection_status, c.effective_from "
                "FROM record_relations AS rr JOIN collections AS c "
                "ON c.id = rr.collection_id "
                "WHERE (rr.record_id = ? OR rr.related_record_id = ?) "
                + status_clause
                + "ORDER BY rr.collection_id, rr.record_id, rr.position",
                (record_id, record_id),
            ).fetchall()
            result = []
            for row in rows:
                outbound = row["record_id"] == record_id
                result.append(
                    {
                        "type": row["relation_type"],
                        "direction": "outbound" if outbound else "inbound",
                        "record_id": (
                            row["related_record_id"] if outbound else row["record_id"]
                        ),
                        "collection": {
                            "id": row["collection_id"],
                            "title": row["collection_title"],
                            "status": row["collection_status"],
                            "effective_from": row["effective_from"],
                        },
                    }
                )
            return result

    def records_for_army_link(
        self,
        entity: str,
        external_id: ArmyLinkRef,
        *,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Return curated records linked to an Army identity.

        Runtime composition uses current collections by default so superseded or
        historical collections cannot affect catalog enrichment merely by being
        present in the rules database.
        """
        with self._connect() as connection:
            if current_only:
                rows = connection.execute(
                    "SELECT r.* FROM records AS r "
                    "JOIN collections AS c ON c.id = r.collection_id "
                    "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                    "AND l.record_id = r.id "
                    "WHERE l.entity = ? AND l.external_id = ? AND c.status = 'current' "
                    "ORDER BY r.collection_id, r.id",
                    (entity, str(external_id)),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT r.* FROM records AS r "
                    "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                    "AND l.record_id = r.id "
                    "WHERE l.entity = ? AND l.external_id = ? "
                    "ORDER BY r.collection_id, r.id",
                    (entity, str(external_id)),
                ).fetchall()
            return self._records_from_rows(connection, rows)

    def skill_parameter_semantics(self) -> dict[ArmyLinkRef, dict[str, str]]:
        """Return curated skill parameter semantics keyed to authored Army refs."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT l.external_id AS skill_ref, r.variant_json "
                "FROM records AS r JOIN collections AS c ON c.id = r.collection_id "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "WHERE r.kind = 'skill' AND c.status = 'current' "
                "AND l.entity = 'skill' AND l.external_id IS NOT NULL "
                "ORDER BY l.external_id, r.collection_id, r.id"
            ).fetchall()
            result: dict[ArmyLinkRef, dict[str, str]] = {}
            for row in rows:
                variant = _variant_semantics(row["variant_json"])
                if not isinstance(variant, dict):
                    continue
                parameters = variant.get("occurrence_parameters", [])
                semantics = next(
                    (
                        parameter
                        for parameter in parameters
                        if parameter.get("source") == "army-extra"
                        and parameter.get("kind") == "distance"
                    ),
                    None,
                )
                if semantics is None:
                    continue
                value = {
                    "kind": semantics["kind"],
                    "positive_sign": semantics["positive_sign"],
                }
                skill_ref = _army_link_ref(row["skill_ref"])
                existing = result.get(skill_ref)
                if existing is not None and existing != value:
                    raise ValueError(
                        f"Skill {skill_ref!r} has conflicting curated parameter semantics"
                    )
                result[skill_ref] = value
            return result

    def declaration_categories(self, entity: str) -> list[dict[str, Any]]:
        """Return current declaration categories for one Army catalog entity."""
        if entity not in {"skill", "equipment"}:
            raise ValueError("Declaration categories support skill or equipment entities")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT l.external_id AS army_ref, r.name, r.facts_json, "
                "s.title AS source_title, s.version AS source_version, c.page "
                "FROM records AS r JOIN collections AS col ON col.id = r.collection_id "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "JOIN record_citations AS c ON c.collection_id = r.collection_id "
                "AND c.record_id = r.id "
                "JOIN sources AS s ON s.collection_id = c.collection_id "
                "AND s.id = c.source_id "
                "WHERE r.kind = 'declaration-category' "
                "AND col.status = 'current' AND l.entity = ? "
                "AND l.external_id IS NOT NULL "
                "ORDER BY l.external_id, r.collection_id, r.id, c.position",
                (entity,),
            ).fetchall()
            result = []
            for row in rows:
                facts = _decode_json(row["facts_json"], {})
                result.append(
                    {
                        "army_ref": _army_link_ref(row["army_ref"]),
                        "type_id": facts["typeId"],
                        "name": row["name"],
                        "order": facts["order"],
                        "source_title": row["source_title"],
                        "source_version": row["source_version"],
                        "page": row["page"],
                    }
                )
            result.sort(
                key=lambda item: (
                    str(item["army_ref"]),
                    item["order"],
                    item["name"],
                    item["page"] or 0,
                )
            )
            return result

    def skill_declaration_categories(self) -> list[dict[str, Any]]:
        """Return current Skill declaration categories keyed to authored Army refs."""
        return [
            {
                "skill_ref": item["army_ref"],
                "name": item["name"],
                "order": item["order"],
                "source_title": item["source_title"],
                "source_version": item["source_version"],
                "page": item["page"],
            }
            for item in self.declaration_categories("skill")
        ]

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
