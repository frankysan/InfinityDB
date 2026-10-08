"""Build the independent SQLite snapshot for curated rules references."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

from infinity_db.domain_slugs import require_domain_slug
from infinity_db.maintained_text import maintained_text_fields, maintained_text_targets
from infinity_db.maintained_text_policy import (
    inferred_review_policy_path,
    validate_maintained_text_link_coverage,
)
from infinity_db.rule_relations import relation_presentation
from infinity_db.scenario_components import compose_scenario_document, scenario_typed_id
from infinity_db.sqlite_determinism import (
    configure_deterministic_sqlite,
    normalize_sqlite_header,
    vacuum_deterministic_sqlite,
)

RULES_APPLICATION_ID = 0x49445231
RULES_SCHEMA_VERSION = 8
RULES_COMPATIBILITY_VERSION = 10
RULES_METADATA_TABLE = "__rules_metadata"
ArmyLinkRef = int | str


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _content_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
        CREATE TABLE scenario_collections (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL
        );
        CREATE TABLE scenario_collection_revisions (
            collection_id TEXT NOT NULL,
            revision TEXT NOT NULL,
            source_collection_id TEXT NOT NULL UNIQUE,
            PRIMARY KEY (collection_id, revision),
            FOREIGN KEY (collection_id) REFERENCES scenario_collections(id),
            FOREIGN KEY (source_collection_id) REFERENCES collections(id)
        );
        CREATE TABLE scenario_publications (
            source_collection_id TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            PRIMARY KEY (source_collection_id, scenario_id),
            FOREIGN KEY (source_collection_id, scenario_id)
                REFERENCES records(collection_id, id)
        );
        CREATE TABLE scenario_memberships (
            collection_id TEXT NOT NULL,
            collection_revision TEXT NOT NULL,
            position INTEGER NOT NULL,
            scenario_id TEXT NOT NULL,
            publication_collection_id TEXT NOT NULL,
            PRIMARY KEY (collection_id, collection_revision, scenario_id),
            UNIQUE (collection_id, collection_revision, position),
            FOREIGN KEY (collection_id, collection_revision)
                REFERENCES scenario_collection_revisions(collection_id, revision),
            FOREIGN KEY (publication_collection_id, scenario_id)
                REFERENCES scenario_publications(source_collection_id, scenario_id)
        );
        CREATE INDEX scenario_memberships_identity ON scenario_memberships(scenario_id);
        CREATE INDEX scenario_publications_identity ON scenario_publications(scenario_id);
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
    scenario_collection_titles: dict[str, tuple[str, Path]] = {}
    scenario_collection_revisions: dict[tuple[str, str], Path] = {}
    current_records: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    current_labels: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path, document in documents:
        collection_id = document["collection"]["id"]
        if collection_id in collection_ids:
            raise ValueError(f"Duplicate curated collection id {collection_id!r}: {path}")
        collection_ids.add(collection_id)
        scenario_collection = document.get("scenarioCollection")
        if scenario_collection is not None:
            scenario_collection_id = scenario_collection["id"]
            scenario_collection_title = scenario_collection["title"]
            previous = scenario_collection_titles.get(scenario_collection_id)
            if previous is not None and previous[0] != scenario_collection_title:
                raise ValueError(
                    f"Scenario collection {scenario_collection_id!r} has conflicting titles "
                    f"in {previous[1]} and {path}"
                )
            scenario_collection_titles[scenario_collection_id] = (
                scenario_collection_title,
                path,
            )
            revision_key = (scenario_collection_id, scenario_collection["revision"])
            previous_revision = scenario_collection_revisions.get(revision_key)
            if previous_revision is not None:
                raise ValueError(
                    f"Duplicate scenario collection revision {revision_key!r}: "
                    f"{previous_revision}, {path}"
                )
            scenario_collection_revisions[revision_key] = path
        if document["collection"]["status"] != "current":
            continue
        for label in document["labels"]:
            current_labels.setdefault(label["id"], []).append((path, label))
        for record in document["records"]:
            current_records.setdefault(record["id"], []).append((path, record))

    for label_id, definitions in current_labels.items():
        semantics = {(label["name"], label["description"]) for _, label in definitions}
        if len(semantics) > 1:
            sources = ", ".join(str(path) for path, _ in definitions)
            raise ValueError(
                f"Current rules label {label_id!r} has conflicting canonical "
                f"definitions across {sources}"
            )

    current_label_ids = set(current_labels)
    for path, document in documents:
        if document["collection"]["status"] != "current":
            continue
        for record in document["records"]:
            for label_id in record.get("labelIds", []):
                if label_id not in current_label_ids:
                    raise ValueError(
                        f"Current rules label reference {label_id!r} in {path}:{record['id']} "
                        "does not resolve to a current canonical Label"
                    )

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
            for targets in (record.get("facts") or {}).get("variantRuleReferences", {}).values():
                for target_id in targets:
                    if target_id not in current_ids:
                        raise ValueError(
                            f"Current variant rule reference {record_id!r} -> "
                            f"{target_id!r} in {path} does not resolve"
                        )

    for path, document in documents:
        if document["collection"]["status"] != "current":
            continue
        for text_context, text in maintained_text_fields(document):
            for target_id in maintained_text_targets(text, context=f"{path}:{text_context}"):
                if target_id not in current_ids:
                    raise ValueError(
                        f"Maintained-text reference {target_id!r} in "
                        f"{path}:{text_context} does not resolve to a current semantic record"
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

    review_policy_path = inferred_review_policy_path(documents)
    if review_policy_path is not None:
        validate_maintained_text_link_coverage(documents, review_policy_path)


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

    scenario_collection = document.get("scenarioCollection")
    if scenario_collection is not None:
        connection.execute(
            "INSERT OR IGNORE INTO scenario_collections (id, title) VALUES (?, ?)",
            (scenario_collection["id"], scenario_collection["title"]),
        )
        connection.execute(
            "INSERT INTO scenario_collection_revisions "
            "(collection_id, revision, source_collection_id) VALUES (?, ?, ?)",
            (
                scenario_collection["id"],
                scenario_collection["revision"],
                collection_id,
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
                (_json_text(record["variantSemantics"]) if "variantSemantics" in record else None),
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
    if scenario_collection is not None:
        records_by_id = {record["id"]: record for record in document["records"]}
        for position, member in enumerate(scenario_collection["members"]):
            scenario_id = member["scenarioId"]
            record = records_by_id[scenario_id]
            connection.execute(
                "INSERT INTO scenario_publications "
                "(source_collection_id, scenario_id, content_sha256) VALUES (?, ?, ?)",
                (collection_id, scenario_id, _content_sha256(record)),
            )
            connection.execute(
                "INSERT INTO scenario_memberships "
                "(collection_id, collection_revision, position, scenario_id, "
                "publication_collection_id) VALUES (?, ?, ?, ?, ?)",
                (
                    scenario_collection["id"],
                    scenario_collection["revision"],
                    position,
                    scenario_id,
                    collection_id,
                ),
            )


def export_rules_database(
    documents: list[tuple[Path, dict[str, Any]]],
    path: Path,
    *,
    finalize: bool = True,
) -> None:
    """Atomically replace a rules database from validated curated documents.

    ``finalize=False`` is intended for semantic tests that only need valid SQLite
    contents. Production/release builds keep the default byte-canonical finalization.
    """
    if not documents:
        raise ValueError("No curated documents supplied")
    _validate_documents(documents)
    documents = [(source, compose_scenario_document(document)) for source, document in documents]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(filename)
    try:
        connection = sqlite3.connect(temporary)
        try:
            configure_deterministic_sqlite(connection)
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
            if finalize:
                vacuum_deterministic_sqlite(connection)
        finally:
            connection.close()
        if finalize:
            normalize_sqlite_header(temporary)
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
    source_variant = raw.get("sourceVariant")
    if isinstance(source_variant, dict):
        result["source_variant"] = dict(source_variant)
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
        skill_type_category_names: dict[str, dict[str, str]] = {}
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
            if collection_id not in skill_type_category_names:
                category_names: dict[str, str] = {}
                for category_row in connection.execute(
                    "SELECT name, facts_json FROM records "
                    "WHERE collection_id = ? AND kind = 'declaration-category' "
                    "ORDER BY id",
                    (collection_id,),
                ).fetchall():
                    category_facts = _decode_json(category_row["facts_json"], {})
                    type_id = category_facts.get("typeId")
                    if isinstance(type_id, str):
                        category_names.setdefault(type_id, category_row["name"])
                skill_type_category_names[collection_id] = category_names
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
            scoped_ids = (record.get("scope") or {}).get("scenarios", [])
            if scoped_ids:
                names = {
                    str(item["id"]): str(item["name"])
                    for item in connection.execute(
                        "SELECT r.id, r.name FROM records r "
                        "JOIN collections c ON c.id=r.collection_id "
                        "WHERE c.status='current' AND r.kind='scenario' AND r.id IN ("
                        + ", ".join("?" for _ in scoped_ids)
                        + ")",
                        tuple(scoped_ids),
                    ).fetchall()
                }
                record["applicable_scenarios"] = [
                    {"id": identifier, "name": names[identifier]} for identifier in scoped_ids
                ]
            label_ids = record["label_ids"]
            if label_ids:
                labels_by_id = {
                    label["id"]: dict(label)
                    for label in connection.execute(
                        "SELECT id, name, description FROM labels "
                        "WHERE collection_id = ? AND id IN ("
                        + ", ".join("?" for _ in label_ids)
                        + ")",
                        (row["collection_id"], *label_ids),
                    ).fetchall()
                }
                if collection["status"] == "current":
                    missing_ids = [
                        label_id for label_id in label_ids if label_id not in labels_by_id
                    ]
                    if missing_ids:
                        placeholders = ", ".join("?" for _ in missing_ids)
                        for label in connection.execute(
                            "SELECT l.id, l.name, l.description FROM labels AS l "
                            "JOIN collections AS c ON c.id = l.collection_id "
                            "WHERE c.status = 'current' AND l.id IN (" + placeholders + ")",
                            tuple(missing_ids),
                        ).fetchall():
                            labels_by_id[label["id"]] = dict(label)
                record["labels"] = [
                    labels_by_id[label_id] for label_id in label_ids if label_id in labels_by_id
                ]
            facts = record["facts"]
            if isinstance(facts, dict):
                type_ids = facts.get("typeIds")
                if isinstance(type_ids, list) and type_ids:
                    skill_types = []
                    for type_id in type_ids:
                        skill_type = connection.execute(
                            "SELECT id, name, labels_json, descriptions_json FROM skill_types "
                            "WHERE collection_id = ? AND id = ?",
                            (row["collection_id"], type_id),
                        ).fetchone()
                        if skill_type is not None:
                            skill_types.append(
                                {
                                    "id": skill_type["id"],
                                    "name": skill_type["name"],
                                    "category_name": skill_type_category_names[collection_id].get(
                                        skill_type["id"], skill_type["name"]
                                    ),
                                    "labels": _decode_json(skill_type["labels_json"], []),
                                    "descriptions": _decode_json(
                                        skill_type["descriptions_json"], {}
                                    ),
                                }
                            )
                    if skill_types:
                        record["skill_types"] = skill_types
                        # Compatibility projection for API consumers that only know the
                        # former primary-category field. New code must use skill_types.
                        record["skill_type"] = skill_types[0]
                elif facts.get("typeId"):
                    skill_type = connection.execute(
                        "SELECT id, name, labels_json, descriptions_json FROM skill_types "
                        "WHERE collection_id = ? AND id = ?",
                        (row["collection_id"], facts["typeId"]),
                    ).fetchone()
                    if skill_type is not None:
                        record["skill_type"] = {
                            "id": skill_type["id"],
                            "name": skill_type["name"],
                            "category_name": skill_type_category_names[collection_id].get(
                                skill_type["id"], skill_type["name"]
                            ),
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
            record["related_records"] = [relation["record_id"] for relation in record["relations"]]
            records.append(record)
        return records

    @staticmethod
    def _compose_records(
        records: list[dict[str, Any]], *, scenario_id: str | None = None
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            scenarios = (record.get("scope") or {}).get("scenarios")
            if scenarios is not None and scenario_id not in scenarios:
                continue
            grouped.setdefault(record["id"], []).append(record)

        result = []
        for record_id in sorted(grouped):
            contributions = grouped[record_id]
            definitions = [
                record for record in contributions if record["composition"]["role"] == "definition"
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
    def _relation_endpoint_index(
        connection: sqlite3.Connection, record_ids: set[str]
    ) -> dict[str, dict[str, Any]]:
        if not record_ids:
            return {}
        placeholders = ", ".join("?" for _ in record_ids)
        rows = connection.execute(
            "SELECT r.collection_id, r.id, r.kind, r.name, r.facts_json "
            "FROM records AS r JOIN collections AS c ON c.id = r.collection_id "
            "WHERE r.id IN (" + placeholders + ") "
            "AND r.composition_role = 'definition' AND c.status = 'current' "
            "ORDER BY r.id",
            tuple(sorted(record_ids)),
        ).fetchall()
        endpoints: dict[str, dict[str, Any]] = {}
        for row in rows:
            links: list[dict[str, str]] = []
            for link in connection.execute(
                "SELECT entity, external_id, external_name FROM record_army_links "
                "WHERE collection_id = ? AND record_id = ? ORDER BY position",
                (row["collection_id"], row["id"]),
            ).fetchall():
                item = {"entity": link["entity"]}
                if link["external_id"] is not None:
                    item["id"] = link["external_id"]
                if link["external_name"] is not None:
                    item["name"] = link["external_name"]
                links.append(item)
            endpoints[row["id"]] = {
                "id": row["id"],
                "kind": row["kind"],
                "name": row["name"],
                "army_links": links,
            }
            if row["kind"] == "rule":
                facts = _decode_json(row["facts_json"], {})
                category = facts.get("category") if isinstance(facts, dict) else None
                if isinstance(category, str):
                    endpoints[row["id"]]["facts"] = {"category": category}
        return endpoints

    @classmethod
    def _attach_reverse_relations(
        cls, connection: sqlite3.Connection, records: list[dict[str, Any]]
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
            reverse_relations = [
                {
                    "type": row["relation_type"],
                    "record_id": row["record_id"],
                    "collection_id": row["collection_id"],
                }
                for row in rows
            ]
            if reverse_relations:
                record["reverse_relations"] = reverse_relations

            display_source = [
                {**relation, "direction": "outbound"} for relation in record.get("relations", [])
            ] + [{**relation, "direction": "inbound"} for relation in reverse_relations]
            endpoint_ids = {relation["record_id"] for relation in display_source}
            endpoints = cls._relation_endpoint_index(connection, endpoint_ids)
            display_relations = []
            for relation in display_source:
                endpoint = endpoints.get(relation["record_id"])
                if endpoint is None:
                    continue
                item = {**relation, "record": endpoint}
                presentation = relation_presentation(relation["type"], relation["direction"])
                if presentation is not None:
                    item["presentation"] = presentation
                display_relations.append(item)
            if display_relations:
                record["display_relations"] = display_relations

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

    @staticmethod
    def _attach_current_army_links(
        connection: sqlite3.Connection, records: list[dict[str, Any]]
    ) -> None:
        """Attach current Army/application links to composed semantic records."""

        for record in records:
            links = connection.execute(
                "SELECT l.entity, l.external_id, l.external_name "
                "FROM record_army_links AS l JOIN collections AS c "
                "ON c.id = l.collection_id "
                "WHERE l.record_id = ? AND c.status = 'current' "
                "ORDER BY l.collection_id, l.position",
                (record["id"],),
            ).fetchall()
            if not links:
                continue
            army_links: list[dict[str, str]] = []
            for link in links:
                item = {"entity": str(link["entity"])}
                if link["external_id"] is not None:
                    item["id"] = str(link["external_id"])
                if link["external_name"] is not None:
                    item["name"] = str(link["external_name"])
                army_links.append(item)
            record["army_links"] = army_links

    def composed_record(
        self, record_id: str, *, include_army_links: bool = False, scenario_id: str | None = None
    ) -> dict[str, Any] | None:
        """Return one current semantic record with supplements attached.

        Army/application links remain opt-in so ordinary rules payloads stay bounded.
        Consumers that must resolve a public application route can request them.
        """

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT r.* FROM records AS r JOIN collections AS c "
                "ON c.id = r.collection_id "
                "WHERE r.id = ? AND c.status = 'current' "
                "ORDER BY r.collection_id",
                (record_id,),
            ).fetchall()
            if not rows:
                return None
            records = self._compose_records(
                self._records_from_rows(connection, rows), scenario_id=scenario_id
            )
            self._attach_reverse_relations(connection, records)
            if include_army_links:
                self._attach_current_army_links(connection, records)
            if not records:
                return None
            if len(records) != 1:
                raise ValueError(
                    f"Current rules identity {record_id!r} resolved to {len(records)} records"
                )
            return records[0]

    def composed_records_by_kind(
        self, kind: str, *, scenario_id: str | None = None
    ) -> list[dict[str, Any]]:
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

    def scenario_publications(self, reference: str) -> list[dict[str, Any]]:
        """Return indexed collection memberships/publications for one scenario identity."""

        identifier = scenario_typed_id(reference)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT m.scenario_id, r.name, m.collection_id, sc.title AS collection_title, "
                "m.collection_revision, m.position, m.publication_collection_id, "
                "p.content_sha256, c.title AS publication_title, c.status, "
                "c.effective_from, c.authority "
                "FROM scenario_memberships AS m "
                "JOIN scenario_collections AS sc ON sc.id = m.collection_id "
                "JOIN scenario_publications AS p "
                "ON p.source_collection_id = m.publication_collection_id "
                "AND p.scenario_id = m.scenario_id "
                "JOIN collections AS c ON c.id = m.publication_collection_id "
                "JOIN records AS r ON r.collection_id = m.publication_collection_id "
                "AND r.id = m.scenario_id "
                "WHERE m.scenario_id = ? "
                "ORDER BY c.effective_from DESC, m.collection_id, "
                "m.collection_revision, m.position",
                (identifier,),
            ).fetchall()
            publications: list[dict[str, Any]] = []
            for row in rows:
                source_rows = connection.execute(
                    "SELECT s.id, s.kind, s.title, s.version, s.published_date, "
                    "s.retrieved_date, s.language, s.authority "
                    "FROM record_citations AS rc JOIN sources AS s "
                    "ON s.collection_id = rc.collection_id AND s.id = rc.source_id "
                    "WHERE rc.collection_id = ? AND rc.record_id = ? "
                    "ORDER BY rc.position",
                    (row["publication_collection_id"], identifier),
                ).fetchall()
                sources: list[dict[str, Any]] = []
                seen_source_ids: set[str] = set()
                for source in source_rows:
                    source_id = str(source["id"])
                    if source_id in seen_source_ids:
                        continue
                    seen_source_ids.add(source_id)
                    sources.append(dict(source))
                publications.append(
                    {
                        "scenario_id": str(row["scenario_id"]),
                        "name": str(row["name"]),
                        "collection": str(row["collection_id"]),
                        "collection_title": str(row["collection_title"]),
                        "revision": str(row["collection_revision"]),
                        "position": int(row["position"]),
                        "publication_revision": str(row["publication_collection_id"]),
                        "publication_title": str(row["publication_title"]),
                        "content_sha256": str(row["content_sha256"]),
                        "status": str(row["status"]),
                        "effective_from": str(row["effective_from"]),
                        "authority": str(row["authority"]),
                        "sources": sources,
                    }
                )
            return publications

    def resolve_scenario_publication(
        self,
        reference: str,
        *,
        collection: str | None = None,
        revision: str | None = None,
    ) -> dict[str, Any] | None:
        """Resolve one indexed scenario publication without collection/revision fallback.

        ``collection`` is the stable scenario-set identity (for example
        ``n5-core``); ``revision`` is that collection's exact revision (for
        example ``5.3``). Without an explicit revision only publications backed
        by a ``current`` source collection are eligible. Historical revisions
        therefore require both selectors. Unsupported selections return ``None``;
        malformed or ambiguous selections raise ``ValueError``.
        """

        identifier = scenario_typed_id(reference)
        if collection is not None:
            collection = require_domain_slug(collection, context="scenario collection")
        if revision is not None and (
            not isinstance(revision, str)
            or not revision.strip()
            or revision != revision.strip()
        ):
            raise ValueError("scenario revision must be a non-empty trimmed string")
        if revision is not None and collection is None:
            raise ValueError("scenario revision requires a scenario collection")

        publications = self.scenario_publications(identifier)
        candidates = [
            publication
            for publication in publications
            if (collection is None or publication["collection"] == collection)
            and (revision is None or publication["revision"] == revision)
            and (revision is not None or publication["status"] == "current")
        ]
        if not candidates:
            return None
        if len(candidates) != 1:
            selections = ", ".join(
                f"{item['collection']}@{item['revision']}" for item in candidates
            )
            raise ValueError(
                f"Scenario {identifier!r} selection is ambiguous: {selections}; "
                "select a collection and exact revision"
            )
        return candidates[0]

    def scenario_reference(self, reference: str) -> dict[str, Any] | None:
        """Return composed scenario Rules and standard Skill-detail records from rules.db."""
        identifier = scenario_typed_id(reference)
        scenario = self.composed_record(identifier)
        if scenario is None or scenario["kind"] != "scenario":
            return None
        mission = scenario["facts"].get("mission")
        if not isinstance(mission, dict):
            return {"scenario": scenario, "rules": [], "skills": []}
        rules = []
        for inclusion in mission["rules"]:
            definition_id = inclusion.get("definitionId")
            if definition_id is None:
                continue  # Legacy inline definitions remain readable.
            rule = self.composed_record(definition_id, scenario_id=identifier)
            if rule is None:
                raise ValueError(f"Missing scenario Rule {definition_id!r}")
            if "specialists" in inclusion:
                rule["facts"]["specialists"] = inclusion["specialists"]
            rules.append(rule)
        skills = []
        for skill_id in mission.get("skills", []):
            skill = self.composed_record(skill_id, scenario_id=identifier)
            if skill is None:
                raise ValueError(f"Missing scenario Skill {skill_id!r}")
            skills.append(skill)
        return {"scenario": scenario, "rules": rules, "skills": skills}

    def composed_records_using_label(self, label_id: str) -> list[dict[str, Any]]:
        """Return current semantic records whose contributions use one Label.

        Army links are attached only for this reverse-reference projection so public
        application routes can be resolved without widening ordinary rules payloads.
        """

        with self._connect() as connection:
            candidate_rows = connection.execute(
                "SELECT r.id, r.label_ids_json FROM records AS r "
                "JOIN collections AS c ON c.id = r.collection_id "
                "WHERE c.status = 'current' ORDER BY r.id, r.collection_id"
            ).fetchall()
            record_ids = sorted(
                {
                    row["id"]
                    for row in candidate_rows
                    if label_id in _decode_json(row["label_ids_json"], [])
                }
            )
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
            self._attach_current_army_links(connection, records)
            return records

    def current_labels(self) -> list[dict[str, Any]]:
        """Return labels from current rules collections with provenance."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT l.id, l.name, l.description, l.collection_id, "
                "c.title AS collection_title "
                "FROM labels AS l JOIN collections AS c ON c.id = l.collection_id "
                "WHERE c.status = 'current' ORDER BY l.collection_id, l.id"
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "collection": {
                        "id": row["collection_id"],
                        "title": row["collection_title"],
                    },
                }
                for row in rows
            ]

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
                        "record_id": (row["related_record_id"] if outbound else row["record_id"]),
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

    def catalog_source_variant_semantics(self, entity: str) -> dict[ArmyLinkRef, dict[str, Any]]:
        """Return reviewed exact-source variant semantics for one catalog domain."""
        if entity not in {"skill", "equipment", "weapon"}:
            raise ValueError("Source variants support skill, equipment, or weapon entities")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT l.external_id AS army_ref, r.variant_json "
                "FROM records AS r JOIN collections AS c ON c.id = r.collection_id "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "WHERE r.kind = ? AND r.composition_role = 'definition' "
                "AND c.status = 'current' AND l.entity = ? "
                "AND l.external_id IS NOT NULL "
                "ORDER BY l.external_id, r.collection_id, r.id",
                (entity, entity),
            ).fetchall()
            result: dict[ArmyLinkRef, dict[str, Any]] = {}
            for row in rows:
                variant = _variant_semantics(row["variant_json"])
                if not isinstance(variant, dict) or variant.get("inheritance") != "source":
                    continue
                source_variant = variant.get("source_variant")
                if not isinstance(source_variant, dict):
                    continue
                army_ref = _army_link_ref(row["army_ref"])
                existing = result.get(army_ref)
                if existing is not None and existing != source_variant:
                    raise ValueError(
                        f"{entity.title()} {army_ref!r} has conflicting source variant semantics"
                    )
                result[army_ref] = dict(source_variant)
            return result

    def skill_definition_categories(self) -> list[dict[str, Any]]:
        """Return ordered categories owned directly by current Skill definitions."""
        with self._connect() as connection:
            category_names: dict[tuple[str, str], str] = {}
            for category_row in connection.execute(
                "SELECT collection_id, name, facts_json FROM records "
                "WHERE kind = 'declaration-category' ORDER BY collection_id, id"
            ).fetchall():
                category_facts = _decode_json(category_row["facts_json"], {})
                type_id = category_facts.get("typeId")
                if isinstance(type_id, str):
                    category_names.setdefault(
                        (category_row["collection_id"], type_id), category_row["name"]
                    )
            rows = connection.execute(
                "SELECT l.external_id AS army_ref, r.collection_id, r.id, r.facts_json "
                "FROM records AS r JOIN collections AS col ON col.id = r.collection_id "
                "JOIN record_army_links AS l ON l.collection_id = r.collection_id "
                "AND l.record_id = r.id "
                "WHERE r.kind = 'skill' AND r.composition_role = 'definition' "
                "AND col.status = 'current' AND l.entity = 'skill' "
                "AND l.external_id IS NOT NULL "
                "ORDER BY l.external_id, r.collection_id, r.id"
            ).fetchall()
            result = []
            for row in rows:
                facts = _decode_json(row["facts_json"], {})
                type_ids = facts.get("typeIds")
                if not isinstance(type_ids, list) or not type_ids:
                    continue
                citation = connection.execute(
                    "SELECT s.title AS source_title, s.version AS source_version, c.page "
                    "FROM record_citations AS c JOIN sources AS s "
                    "ON s.collection_id = c.collection_id AND s.id = c.source_id "
                    "WHERE c.collection_id = ? AND c.record_id = ? "
                    "ORDER BY (c.page IS NULL), c.position LIMIT 1",
                    (row["collection_id"], row["id"]),
                ).fetchone()
                for order, type_id in enumerate(type_ids):
                    skill_type = connection.execute(
                        "SELECT name FROM skill_types WHERE collection_id = ? AND id = ?",
                        (row["collection_id"], type_id),
                    ).fetchone()
                    if skill_type is None:
                        continue
                    result.append(
                        {
                            "skill_ref": _army_link_ref(row["army_ref"]),
                            "type_id": type_id,
                            "name": category_names.get(
                                (row["collection_id"], type_id), skill_type["name"]
                            ),
                            "order": order,
                            "source_title": (
                                citation["source_title"] if citation is not None else None
                            ),
                            "source_version": (
                                citation["source_version"] if citation is not None else None
                            ),
                            "page": citation["page"] if citation is not None else None,
                        }
                    )
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

    def unit_profile_help(self) -> list[dict[str, Any]]:
        """Return reviewed Unit Profile notation help in authored display order."""

        items: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for record in self.composed_records_by_kind("rule"):
            facts = record.get("facts")
            if not isinstance(facts, dict) or facts.get("category") != "unit-profile-help":
                continue
            key = str(facts["key"])
            if key in seen_keys:
                raise ValueError(f"Duplicate current Unit Profile help key {key!r}")
            seen_keys.add(key)
            items.append(
                {
                    "id": record["id"],
                    "key": key,
                    "name": record["name"],
                    "summary": record["summary"],
                    "order": int(facts["order"]),
                }
            )
        return sorted(items, key=lambda item: (item["order"], item["key"]))

    def training_by_order_type(self) -> dict[str, dict[str, Any]]:
        """Map reviewed Training to normal source Order-generation types only.

        Tactical and Lieutenant Orders are distinct generated Order types, not
        additional Training values. Multiple current Training identities claiming
        one Order type fail closed rather than depending on publication order.
        """
        index: dict[str, dict[str, Any]] = {}
        for record in self.composed_records_by_kind("training"):
            order_type = record["facts"]["orderType"]
            if order_type in index:
                raise ValueError(f"Multiple current Training definitions for Order {order_type!r}")
            index[order_type] = record
        return index

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
                    "SELECT r.* FROM records AS r WHERE r.kind = ? ORDER BY r.collection_id, r.id",
                    (kind,),
                ).fetchall()
            return self._records_from_rows(connection, rows)
