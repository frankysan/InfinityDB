"""Build and inspect an isolated ITS season database, independent of the serving set.

P3.2: this database is an offline development artifact, not yet read by the web
runtime. The existing scenario authoring/geometry parser remains authoritative.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from .curated import load_curated_document
from .scenario_components import compose_scenario_document
from .scenario_definition import parse_scenario_definition_record
from .sqlite_determinism import (
    configure_deterministic_sqlite,
    normalize_sqlite_header,
    vacuum_deterministic_sqlite,
)

ITS_APPLICATION_ID = 0x49445331  # "IDS1", distinct from Rules/Army databases
ITS_SCHEMA_VERSION = 1
ITS_METADATA_TABLE = "__its_metadata"
SEASON_ID = "its-18"
DEFAULT_CORE_REVISION = "5.3"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _builder_revision() -> str:
    """Bind the output to the relevant parser/exporter code, not host paths."""
    modules = (
        "its_season_database.py", "curated.py", "scenario_components.py",
        "scenario_definition.py", "scenario_mission.py", "scenario_geometry.py",
        "sqlite_determinism.py",
    )
    directory = Path(__file__).resolve().parent
    fingerprints = {
        name: hashlib.sha256((directory / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in modules
    }
    return _digest(fingerprints)


def _input_identity(source: Path, document: dict[str, Any], core_revision: str) -> dict[str, Any]:
    collection = document["collection"]
    scenario_set = document["scenarioCollection"]
    return {
        "sourceCollectionId": collection["id"],
        "sourceSha256": _file_sha(source),
        "seasonId": scenario_set["id"],
        "seasonRevision": scenario_set["revision"],
        "effectiveFrom": collection["effectiveFrom"],
        "requiredCoreRulesRevision": core_revision,
        "builderRevision": _builder_revision(),
        "schemaVersion": ITS_SCHEMA_VERSION,
        "sources": [
            {"id": entry["id"], "sha256": entry.get("sha256")}
            for entry in document["sources"]
        ],
    }


def _validate_its_document(document: dict[str, Any], core_revision: str) -> None:
    collection = document["collection"]
    season = document.get("scenarioCollection")
    if (
        collection["domain"] != "its"
        or not collection["id"].startswith("its-season-18-")
        or not isinstance(season, dict)
        or season.get("id") != SEASON_ID
        or not isinstance(season.get("revision"), str)
        or not season["revision"]
    ):
        raise ValueError("ITS 18 builder requires an ITS 18 source collection and scenario set")
    if (
        not isinstance(core_revision, str)
        or not core_revision.strip()
        or core_revision != core_revision.strip()
    ):
        raise ValueError("An explicit N5 core rules revision is required")
    if not any(
        item["kind"] == "pdf"
        and item["authority"] == "primary"
        and item["version"] == season["revision"]
        and isinstance(item.get("sha256"), str)
        and len(item["sha256"]) == 64
        for item in document["sources"]
    ):
        raise ValueError("ITS publication requires a revision-matched primary PDF source")
    for record in document["records"]:
        scope = record["scope"]
        if scope.get("game") != "N5" or SEASON_ID not in scope.get("seasons", []):
            raise ValueError(f"ITS 18 publication contains out-of-season record {record['id']!r}")


def _schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        f"""
        BEGIN;
        PRAGMA application_id = {ITS_APPLICATION_ID};
        PRAGMA user_version = {ITS_SCHEMA_VERSION};
        CREATE TABLE {ITS_METADATA_TABLE} (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE collections (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, domain TEXT NOT NULL,
            status TEXT NOT NULL, effective_from TEXT NOT NULL, authority TEXT NOT NULL
        );
        CREATE TABLE sources (
            collection_id TEXT NOT NULL, id TEXT NOT NULL,
            descriptor_json TEXT NOT NULL,
            PRIMARY KEY (collection_id, id),
            FOREIGN KEY (collection_id) REFERENCES collections(id)
        );
        CREATE TABLE records (
            collection_id TEXT NOT NULL, id TEXT NOT NULL, kind TEXT NOT NULL,
            name TEXT NOT NULL, composition_role TEXT NOT NULL,
            payload_json TEXT NOT NULL, content_sha256 TEXT NOT NULL,
            PRIMARY KEY (collection_id, id),
            FOREIGN KEY (collection_id) REFERENCES collections(id)
        );
        CREATE TABLE record_citations (
            collection_id TEXT NOT NULL, record_id TEXT NOT NULL,
            position INTEGER NOT NULL, source_id TEXT NOT NULL,
            page INTEGER, member TEXT, heading TEXT, section TEXT,
            PRIMARY KEY (collection_id, record_id, position),
            FOREIGN KEY (collection_id, record_id) REFERENCES records(collection_id, id),
            FOREIGN KEY (collection_id, source_id) REFERENCES sources(collection_id, id)
        );
        CREATE TABLE scenario_sets (
            id TEXT NOT NULL, revision TEXT NOT NULL, title TEXT NOT NULL,
            source_collection_id TEXT NOT NULL,
            PRIMARY KEY (id, revision),
            UNIQUE (source_collection_id),
            FOREIGN KEY (source_collection_id) REFERENCES collections(id)
        );
        CREATE TABLE scenario_memberships (
            set_id TEXT NOT NULL, set_revision TEXT NOT NULL, position INTEGER NOT NULL,
            scenario_id TEXT NOT NULL, publication_collection_id TEXT NOT NULL,
            PRIMARY KEY (set_id, set_revision, scenario_id),
            UNIQUE (set_id, set_revision, position),
            FOREIGN KEY (set_id, set_revision) REFERENCES scenario_sets(id, revision),
            FOREIGN KEY (publication_collection_id, scenario_id)
                REFERENCES records(collection_id, id)
        );
        CREATE TABLE scenario_configurations (
            collection_id TEXT NOT NULL, scenario_id TEXT NOT NULL,
            configuration_id TEXT NOT NULL, army_points_json TEXT NOT NULL,
            geometry_json TEXT NOT NULL,
            PRIMARY KEY (collection_id, scenario_id, configuration_id),
            FOREIGN KEY (collection_id, scenario_id) REFERENCES records(collection_id, id)
        );
        CREATE INDEX scenario_memberships_by_identity ON scenario_memberships(scenario_id);
        """
    )


def _populate(
    connection: sqlite3.Connection, document: dict[str, Any], identity: dict[str, Any],
) -> None:
    collection = document["collection"]
    season = document["scenarioCollection"]
    collection_id = collection["id"]
    connection.execute(
        "INSERT INTO collections VALUES (?, ?, ?, ?, ?, ?)",
        (collection_id, collection["title"], collection["domain"], collection["status"],
         collection["effectiveFrom"], collection["authority"]),
    )
    connection.execute(
        "INSERT INTO scenario_sets VALUES (?, ?, ?, ?)",
        (season["id"], season["revision"], season["title"], collection_id),
    )
    for source in document["sources"]:
        connection.execute(
            "INSERT INTO sources VALUES (?, ?, ?)",
            (collection_id, source["id"], _canonical(source).decode("utf-8")),
        )
    for record in document["records"]:
        payload = _canonical(record)
        connection.execute(
            "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?)",
            (collection_id, record["id"], record["kind"], record["name"],
             record["composition"]["role"], payload.decode("utf-8"),
             hashlib.sha256(payload).hexdigest()),
        )
        for position, citation in enumerate(record["citations"]):
            connection.execute(
                "INSERT INTO record_citations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (collection_id, record["id"], position, citation["sourceId"],
                 citation.get("page"), citation.get("member"),
                 citation.get("heading"), citation.get("section")),
            )
        if record["kind"] == "scenario" and record["composition"]["role"] == "definition":
            parsed = parse_scenario_definition_record(record)
            for configuration in record["facts"]["configurations"]:
                connection.execute(
                    "INSERT INTO scenario_configurations VALUES (?, ?, ?, ?, ?)",
                    (collection_id, record["id"], configuration["id"],
                     _canonical(configuration["armyPoints"]).decode("utf-8"),
                     _canonical(configuration["geometry"]).decode("utf-8")),
                )
            if len(parsed.configurations) != len(record["facts"]["configurations"]):
                raise ValueError(f"Scenario configuration count mismatch: {record['id']}")
    for position, member in enumerate(season["members"]):
        connection.execute(
            "INSERT INTO scenario_memberships VALUES (?, ?, ?, ?, ?)",
            (season["id"], season["revision"], position, member["scenarioId"], collection_id),
        )
    for key, value in {
        "format": "InfinityDB ITS season database",
        "formatVersion": ITS_SCHEMA_VERSION,
        "inputIdentity": identity,
        "buildId": _digest(identity),
        "scenarioCount": len(season["members"]),
    }.items():
        connection.execute(
            f"INSERT INTO {ITS_METADATA_TABLE} VALUES (?, ?)",
            (key, _canonical(value).decode("utf-8")),
        )


def inspect_its_database(
    path: Path, *, source: Path | None = None, core_revision: str | None = None,
    require_current_builder: bool = False,
) -> dict[str, Any]:
    """Validate the stored publication; optionally require current builder inputs."""
    if not path.is_file():
        raise ValueError(f"ITS database does not exist: {path}")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id != ITS_APPLICATION_ID or version != ITS_SCHEMA_VERSION:
            raise ValueError("Not an ITS season database with supported schema")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("ITS database integrity check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("ITS database contains broken references")
        metadata = {
            row["key"]: json.loads(row["value"])
            for row in connection.execute(f"SELECT key, value FROM {ITS_METADATA_TABLE}")
        }
        if (
            set(metadata) != {
                "format", "formatVersion", "inputIdentity", "buildId", "scenarioCount"
            }
            or metadata["format"] != "InfinityDB ITS season database"
            or metadata["formatVersion"] != ITS_SCHEMA_VERSION
            or not isinstance(metadata["inputIdentity"], dict)
            or metadata["buildId"] != _digest(metadata["inputIdentity"])
        ):
            raise ValueError("ITS build provenance is invalid")
        identity = metadata["inputIdentity"]
        if (
            identity.get("seasonId") != SEASON_ID
            or identity.get("schemaVersion") != ITS_SCHEMA_VERSION
            or not isinstance(identity.get("builderRevision"), str)
            or len(identity["builderRevision"]) != 64
        ):
            raise ValueError("ITS season or builder identity is invalid")
        if require_current_builder and identity["builderRevision"] != _builder_revision():
            raise ValueError("ITS database requires rebuilding after builder change")
        if core_revision is not None and identity.get("requiredCoreRulesRevision") != core_revision:
            raise ValueError("ITS database requires a different N5 core revision")
        if source is not None and _file_sha(source) != identity.get("sourceSha256"):
            raise ValueError("ITS source bytes do not match the built database")
        publications = connection.execute(
            "SELECT s.id, s.revision, s.source_collection_id, m.scenario_id, m.position, "
            "r.payload_json, r.content_sha256 FROM scenario_sets AS s "
            "JOIN scenario_memberships AS m ON m.set_id=s.id AND m.set_revision=s.revision "
            "JOIN records AS r ON r.collection_id=m.publication_collection_id "
            "AND r.id=m.scenario_id ORDER BY m.position"
        ).fetchall()
        if not publications or len(publications) != metadata["scenarioCount"]:
            raise ValueError("ITS scenario membership count does not match provenance")
        scenarios = []
        for row in publications:
            if (row["id"], row["revision"], row["source_collection_id"]) != (
                identity["seasonId"], identity["seasonRevision"],
                identity["sourceCollectionId"],
            ):
                raise ValueError("ITS scenario membership belongs to another publication")
            record = json.loads(row["payload_json"])
            if _digest(record) != row["content_sha256"] or record.get("id") != row["scenario_id"]:
                raise ValueError("ITS scenario publication content hash mismatch")
            parsed = parse_scenario_definition_record(record)
            configs = connection.execute(
                "SELECT configuration_id, army_points_json, geometry_json "
                "FROM scenario_configurations WHERE collection_id=? AND scenario_id=? "
                "ORDER BY configuration_id",
                (identity["sourceCollectionId"], row["scenario_id"]),
            ).fetchall()
            if len(configs) != len(parsed.configurations):
                raise ValueError("ITS scenario configurations are incomplete")
            indexed = {
                row["configuration_id"]: (json.loads(row["army_points_json"]),
                                          json.loads(row["geometry_json"]))
                for row in configs
            }
            for configuration in record["facts"]["configurations"]:
                if indexed.get(configuration["id"]) != (
                    configuration["armyPoints"], configuration["geometry"]
                ):
                    raise ValueError("ITS scenario geometry or Army Points mismatch")
            citations = connection.execute(
                "SELECT source_id, page, member, heading, section "
                "FROM record_citations WHERE collection_id=? AND record_id=? ORDER BY position",
                (identity["sourceCollectionId"], row["scenario_id"]),
            ).fetchall()
            if [dict(r) for r in citations] != [
                {key: c.get(key2) for key, key2 in (
                    ("source_id", "sourceId"), ("page", "page"), ("member", "member"),
                    ("heading", "heading"), ("section", "section"),
                )} for c in record["citations"]
            ]:
                raise ValueError("ITS citation projection differs from source record")
            scenarios.append({
                "id": row["scenario_id"],
                "position": row["position"],
                "contentSha256": row["content_sha256"],
                "configurationCount": len(parsed.configurations),
                "citations": len(citations),
            })
        return {
            "schemaVersion": ITS_SCHEMA_VERSION,
            "inputIdentity": identity,
            "buildId": metadata["buildId"],
            "sha256": _file_sha(path),
            "scenarios": scenarios,
        }




def select_its_scenario(
    path: Path, *,
    season_id: str, revision: str, scenario_id: str,
) -> dict[str, Any] | None:
    """Read one exact published mission; never infer a season or revision.

    The output is a season-owned authored/composed record and its original
    citation-bearing publication metadata, not a second scenario read model.
    """
    from .domain_slugs import require_domain_slug, validate_typed_domain_id

    require_domain_slug(season_id, context="ITS scenario collection")
    if not isinstance(revision, str) or not revision.strip() or revision.strip() != revision:
        raise ValueError("ITS scenario revision must be provided exactly")
    validate_typed_domain_id(
        scenario_id, expected_domain="scenario", context="ITS scenario identity",
    )
    inspect_its_database(path)
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT r.payload_json, r.content_sha256, s.source_collection_id, "
            "s.title, c.effective_from, c.status, c.authority, m.position "
            "FROM scenario_memberships AS m "
            "JOIN scenario_sets AS s ON s.id=m.set_id AND s.revision=m.set_revision "
            "JOIN collections AS c ON c.id=s.source_collection_id "
            "JOIN records AS r ON r.collection_id=m.publication_collection_id "
            "AND r.id=m.scenario_id "
            "WHERE m.set_id=? AND m.set_revision=? AND m.scenario_id=?",
            (season_id, revision, scenario_id),
        ).fetchone()
        if row is None:
            return None
        sources = [
            json.loads(item["descriptor_json"])
            for item in connection.execute(
                "SELECT src.descriptor_json FROM record_citations AS cite "
                "JOIN sources AS src ON src.collection_id=cite.collection_id "
                "AND src.id=cite.source_id "
                "WHERE cite.collection_id=? AND cite.record_id=? "
                "ORDER BY cite.position",
                (row["source_collection_id"], scenario_id),
            )
        ]
        return {
            "record": json.loads(row["payload_json"]),
            "publication": {
                "collectionId": season_id,
                "revision": revision,
                "sourceCollectionId": row["source_collection_id"],
                "title": row["title"],
                "effectiveFrom": row["effective_from"],
                "status": row["status"],
                "authority": row["authority"],
                "position": row["position"],
                "contentSha256": row["content_sha256"],
                "sources": sources,
            },
        }

def build_its_database(
    source: Path, output: Path, *, core_revision: str = DEFAULT_CORE_REVISION,
) -> dict[str, Any]:
    """Build/validate in a disposable sibling, then atomically replace the output."""
    source, output = source.resolve(), output.resolve()
    if source == output or output.name in {"army.db", "rules_n5.db"}:
        raise ValueError("ITS output must not replace curated or core runtime artifacts")
    document = load_curated_document(source)
    _validate_its_document(document, core_revision)
    identity = _input_identity(source, document, core_revision)
    composed = compose_scenario_document(document)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmpname = tempfile.mkstemp(prefix=".its-season-", suffix=".db", dir=output.parent)
    os.close(fd)
    temporary = Path(tmpname)
    try:
        with closing(sqlite3.connect(temporary)) as connection:
            configure_deterministic_sqlite(connection)
            connection.execute("PRAGMA foreign_keys=ON")
            with connection:
                _schema(connection)
                _populate(connection, composed, identity)
            vacuum_deterministic_sqlite(connection)
        normalize_sqlite_header(temporary)
        result = inspect_its_database(
            temporary, source=source, core_revision=core_revision,
            require_current_builder=True,
        )
        if _input_identity(source, load_curated_document(source), core_revision) != identity:
            raise ValueError("ITS source changed during build; output retained")
        os.replace(temporary, output)
        return result
    finally:
        if temporary.exists():
            temporary.unlink()
