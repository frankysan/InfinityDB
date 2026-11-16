"""Reviewed Ammunition-to-N5 links stored as relational source facts in Rules v16.

Ammunition display segmentation and composition are authored relationships.
Never infer effects, saving rolls, or components by parsing the source label.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .build_provenance import file_sha256
from .weapon_ammunition_references import validate_ammunition_reference_entries

SCHEMA_VERSION = 16
COMPATIBILITY_VERSION = 18
COLLECTION = "n5-core-v5.3"
SOURCE = "n5-core-v5.3-pdf"
FORMAT = "InfinityDB weapon ammunition references"
FORMAT_VERSION = 2


def _digest(mapping: dict[int, dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(
            [{"sourceId": source_id, "entry": entry} for source_id, entry in mapping.items()],
            ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _authority(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT s.sha256 FROM sources s JOIN collections c ON c.id=s.collection_id "
        "WHERE s.collection_id=? AND s.id=? AND c.status='current' "
        "AND s.kind='pdf' AND s.authority='primary'",
        (COLLECTION, SOURCE),
    ).fetchone()
    if row is None or not isinstance(row[0], str) or len(row[0]) != 64:
        raise ValueError("Ammunition reference N5 source authority is unavailable")
    return row[0]


def _validate(
    connection: sqlite3.Connection,
    mapping: dict[int, dict[str, Any]],
    army: Path | None = None,
) -> None:
    if not isinstance(mapping, dict) or len(mapping) != 16 or any(
        type(source_id) is not int or source_id <= 0 for source_id in mapping
    ):
        raise ValueError("Reviewed Ammunition reference inventory differs")
    source_entries = {str(source_id): entry for source_id, entry in mapping.items()}
    if validate_ammunition_reference_entries(source_entries) != mapping:
        raise ValueError("Reviewed Ammunition reference semantics differ")
    _authority(connection)
    current = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT r.id,r.kind FROM records r "
            "JOIN collections c ON c.id=r.collection_id "
            "WHERE c.status='current' AND r.collection_id=? AND r.kind='ammunition'",
            (COLLECTION,),
        )
    }
    for entry in mapping.values():
        targets = [
            segment["ruleId"] for segment in entry["segments"]
            if "ruleId" in segment
        ]
        targets.extend(entry.get("components", []))
        if any(current.get(target) != "ammunition" for target in targets):
            raise ValueError("Reviewed Ammunition link lacks a current canonical N5 rule")
    if army is not None:
        # sqlite3.Connection.__exit__ does not close the handle on Windows.
        with closing(sqlite3.connect(army.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            published = dict(source.execute("SELECT id,name FROM metadata_ammunitions"))
        if any(published.get(source_id) != entry["name"] for source_id, entry in mapping.items()):
            raise ValueError("Reviewed Ammunition source ID/name differs from selected Army")


def stage_ammunition_references(
    connection: sqlite3.Connection, mapping: dict[int, dict[str, Any]], army: Path,
) -> None:
    """Stage reviewed links within the v15 export transaction."""
    if connection.execute("PRAGMA user_version").fetchone()[0] != 15:
        raise ValueError("Ammunition reference embedding requires the Rules v15 baseline")
    _validate(connection, mapping, army)
    schema = (
        """CREATE TABLE weapon_ammunition_reference_metadata (
            id INTEGER PRIMARY KEY CHECK(id=1),
            army_database_sha256 TEXT NOT NULL CHECK(length(army_database_sha256)=64),
            source_collection_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
            source_format TEXT NOT NULL,
            source_version INTEGER NOT NULL CHECK(source_version=2),
            entry_count INTEGER NOT NULL CHECK(entry_count>0),
            segment_count INTEGER NOT NULL CHECK(segment_count>0),
            component_count INTEGER NOT NULL CHECK(component_count>=0),
            content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
            FOREIGN KEY(source_collection_id,source_id)
                REFERENCES sources(collection_id,id)
        )""",
        """CREATE TABLE weapon_ammunition_links (
            ammunition_source_id INTEGER PRIMARY KEY CHECK(ammunition_source_id>0),
            position INTEGER NOT NULL UNIQUE CHECK(position>=0),
            source_name TEXT NOT NULL
        )""",
        """CREATE TABLE weapon_ammunition_segments (
            ammunition_source_id INTEGER NOT NULL,
            position INTEGER NOT NULL CHECK(position>=0),
            text TEXT NOT NULL CHECK(length(text)>0),
            rule_collection_id TEXT,
            rule_id TEXT,
            PRIMARY KEY(ammunition_source_id,position),
            FOREIGN KEY(ammunition_source_id)
                REFERENCES weapon_ammunition_links(ammunition_source_id),
            FOREIGN KEY(rule_collection_id,rule_id)
                REFERENCES records(collection_id,id),
            CHECK((rule_collection_id IS NULL) = (rule_id IS NULL))
        )""",
        """CREATE TABLE weapon_ammunition_components (
            ammunition_source_id INTEGER NOT NULL,
            position INTEGER NOT NULL CHECK(position>=0),
            rule_collection_id TEXT NOT NULL,
            rule_id TEXT NOT NULL,
            PRIMARY KEY(ammunition_source_id,position),
            UNIQUE(ammunition_source_id,rule_id),
            FOREIGN KEY(ammunition_source_id)
                REFERENCES weapon_ammunition_links(ammunition_source_id),
            FOREIGN KEY(rule_collection_id,rule_id)
                REFERENCES records(collection_id,id)
        )""",
    )
    for sql in schema:
        connection.execute(sql)
    connection.execute(
        "INSERT INTO weapon_ammunition_reference_metadata VALUES (1,?,?,?,?,?,?,?,?,?,?)",
        (
            file_sha256(army), COLLECTION, SOURCE, _authority(connection),
            FORMAT, FORMAT_VERSION, len(mapping),
            sum(len(entry["segments"]) for entry in mapping.values()),
            sum(len(entry.get("components", [])) for entry in mapping.values()),
            _digest(mapping),
        ),
    )
    for position, (source_id, entry) in enumerate(mapping.items()):
        connection.execute(
            "INSERT INTO weapon_ammunition_links VALUES (?,?,?)",
            (source_id, position, entry["name"]),
        )
        for index, segment in enumerate(entry["segments"]):
            rule_id = segment.get("ruleId")
            connection.execute(
                "INSERT INTO weapon_ammunition_segments VALUES (?,?,?,?,?)",
                (source_id, index, segment["text"], COLLECTION if rule_id else None, rule_id),
            )
        for index, rule_id in enumerate(entry.get("components", [])):
            connection.execute(
                "INSERT INTO weapon_ammunition_components VALUES (?,?,?,?)",
                (source_id, index, COLLECTION, rule_id),
            )
    read_ammunition_references(connection, army)


def read_ammunition_references(
    connection: sqlite3.Connection,
    army: Path | None = None,
) -> dict[int, dict[str, Any]]:
    """Rebuild the former loader dictionary from typed, ordered SQL rows."""
    meta = connection.execute(
        "SELECT army_database_sha256,source_collection_id,source_id,source_sha256,"
        "source_format,source_version,entry_count,segment_count,component_count,content_sha256 "
        "FROM weapon_ammunition_reference_metadata WHERE id=1"
    ).fetchone()
    if (
        meta is None
        or tuple(meta[1:6]) != (COLLECTION, SOURCE, _authority(connection), FORMAT, FORMAT_VERSION)
        or (army is not None and meta[0] != file_sha256(army))
    ):
        raise ValueError("Reviewed Ammunition source metadata or Army identity differs")
    links = connection.execute(
        "SELECT ammunition_source_id,position,source_name "
        "FROM weapon_ammunition_links ORDER BY position"
    ).fetchall()
    if len(links) != meta[6] or any(link[1] != pos for pos, link in enumerate(links)):
        raise ValueError("Incomplete or unordered Ammunition links")
    mapping: dict[int, dict[str, Any]] = {}
    segment_total = component_total = 0
    for source_id, _position, name in links:
        segments = connection.execute(
            "SELECT position,text,rule_collection_id,rule_id "
            "FROM weapon_ammunition_segments WHERE ammunition_source_id=? ORDER BY position",
            (source_id,),
        ).fetchall()
        components = connection.execute(
            "SELECT position,rule_collection_id,rule_id "
            "FROM weapon_ammunition_components WHERE ammunition_source_id=? ORDER BY position",
            (source_id,),
        ).fetchall()
        if (
            not segments or any(row[0] != pos for pos, row in enumerate(segments))
            or any(row[0] != pos for pos, row in enumerate(components))
            or any(row[2] != COLLECTION for row in segments if row[3] is not None)
            or any(row[1] != COLLECTION for row in components)
            or any(row[2] is not None for row in segments if row[3] is None)
        ):
            raise ValueError("Invalid ordered Ammunition segment/component provenance")
        entry: dict[str, Any] = {
            "name": name,
            "segments": [
                {"text": row[1], **({"ruleId": row[3]} if row[3] is not None else {})}
                for row in segments
            ],
        }
        if components:
            entry["components"] = [row[2] for row in components]
        mapping[source_id] = entry
        segment_total += len(segments)
        component_total += len(components)
    if (segment_total, component_total) != (meta[7], meta[8]):
        raise ValueError("Incomplete reviewed Ammunition publication")
    _validate(connection, mapping, army)
    if _digest(mapping) != meta[9]:
        raise ValueError("Reviewed Ammunition link fingerprint differs")
    return mapping


def validate_ammunition_reference_snapshot(connection: sqlite3.Connection) -> None:
    read_ammunition_references(connection)
