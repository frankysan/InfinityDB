"""Relational, source-reviewed Weapon Property vocabulary for Rules v17.

Properties are application-maintained concepts distinct from canonical N5
Ammunition and Traits. Profiles are exact Army source signatures, not inferred
from names, punctuation, or ammunition types.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .build_provenance import file_sha256
from .weapon_properties import validate_weapon_property_entries

SCHEMA_VERSION = 17
COMPATIBILITY_VERSION = 19
COLLECTION = "n5-core-v5.3"
SOURCE = "n5-core-v5.3-pdf"
FORMAT = "InfinityDB reviewed weapon properties"
FORMAT_VERSION = 1


def _digest(entries: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(
            entries, sort_keys=True, ensure_ascii=False, allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _source_sha(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT s.sha256 FROM sources s JOIN collections c ON c.id=s.collection_id "
        "WHERE s.collection_id=? AND s.id=? AND s.kind='pdf' "
        "AND s.authority='primary' AND c.status='current'",
        (COLLECTION, SOURCE),
    ).fetchone()
    if row is None or not isinstance(row[0], str) or len(row[0]) != 64:
        raise ValueError("Weapon Property source authority is not the current N5.3 PDF")
    return row[0]


def _origin_collection(connection: sqlite3.Connection, record_id: str) -> str:
    rows = connection.execute(
        "SELECT r.collection_id FROM records r JOIN collections c "
        "ON c.id=r.collection_id WHERE r.id=? AND c.status='current' "
        "AND r.composition_role='definition'",
        (record_id,),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError(f"Weapon Property origin lacks one current rule definition: {record_id}")
    return rows[0][0]


def _check_army(entries: list[dict[str, Any]], army: Path) -> None:
    # The Connection context manager commits/rolls back, but never closes the
    # file handle. Explicit closing is essential for Windows build directories.
    with closing(sqlite3.connect(army.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        names = dict(source.execute("SELECT id,name FROM metadata_ammunitions"))
        profiles = {
            (row[0], row[2]): row
            for row in source.execute(
                "SELECT id,name,mode,ammunition,saving,savingNum,properties "
                "FROM metadata_weapons"
            )
        }
    for entry in entries:
        for signature in entry["profiles"]:
            key = (signature["weaponId"], signature["mode"])
            row = profiles.get(key)
            if row is None or (
                row[1] != signature["weaponName"]
                or row[3] != signature["ammunitionSourceId"]
                or names.get(row[3]) != signature["ammunition"]
                or row[4] != signature["saving"]
                or row[5] != signature["savingNum"]
                or json.loads(row[6]) != signature["traits"]
            ):
                raise ValueError(f"Weapon Property source profile no longer matches Army: {key}")


def _validate(
    connection: sqlite3.Connection,
    entries: list[dict[str, Any]],
    army: Path | None = None,
) -> None:
    if len(validate_weapon_property_entries(entries)) != 12:
        raise ValueError("Weapon Property inventory no longer contains 12 reviewed concepts")
    _source_sha(connection)
    for entry in entries:
        for origin in entry["origins"]:
            if record_id := origin.get("recordId"):
                _origin_collection(connection, record_id)
    if army is not None:
        _check_army(entries, army)


def stage_weapon_properties(
    connection: sqlite3.Connection, entries: list[dict[str, Any]], army: Path,
) -> None:
    """Add exact authored property/source rows to the current v16 export."""
    if connection.execute("PRAGMA user_version").fetchone()[0] != 16:
        raise ValueError("Weapon Property embedding requires the Rules v16 baseline")
    _validate(connection, entries, army)
    statements = (
        """CREATE TABLE weapon_property_metadata (
            id INTEGER PRIMARY KEY CHECK(id=1),
            army_database_sha256 TEXT NOT NULL CHECK(length(army_database_sha256)=64),
            source_collection_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
            source_format TEXT NOT NULL,
            source_version INTEGER NOT NULL CHECK(source_version=1),
            property_count INTEGER NOT NULL CHECK(property_count>0),
            origin_count INTEGER NOT NULL CHECK(origin_count>0),
            profile_count INTEGER NOT NULL CHECK(profile_count>0),
            trait_count INTEGER NOT NULL CHECK(trait_count>=0),
            content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
            FOREIGN KEY(source_collection_id,source_id)
                REFERENCES sources(collection_id,id)
        )""",
        """CREATE TABLE weapon_properties (
            id TEXT PRIMARY KEY CHECK(length(id)>0),
            position INTEGER NOT NULL UNIQUE CHECK(position>=0),
            name TEXT NOT NULL CHECK(length(name)>0),
            summary TEXT NOT NULL CHECK(length(summary)>0)
        )""",
        """CREATE TABLE weapon_property_origins (
            property_id TEXT NOT NULL,
            position INTEGER NOT NULL CHECK(position>=0),
            domain TEXT NOT NULL,
            role TEXT NOT NULL,
            rule_collection_id TEXT,
            record_id TEXT,
            source_section TEXT,
            PRIMARY KEY(property_id,position),
            FOREIGN KEY(property_id) REFERENCES weapon_properties(id),
            FOREIGN KEY(rule_collection_id,record_id)
                REFERENCES records(collection_id,id),
            CHECK((rule_collection_id IS NULL) = (record_id IS NULL)),
            CHECK(record_id IS NOT NULL OR source_section IS NOT NULL)
        )""",
        """CREATE TABLE weapon_property_profiles (
            property_id TEXT NOT NULL,
            position INTEGER NOT NULL CHECK(position>=0),
            weapon_id INTEGER NOT NULL CHECK(weapon_id>0),
            mode_key TEXT NOT NULL,
            mode TEXT,
            weapon_name TEXT NOT NULL,
            ammunition_source_id INTEGER NOT NULL CHECK(ammunition_source_id>0),
            ammunition TEXT,
            saving TEXT,
            saving_num TEXT,
            PRIMARY KEY(property_id,position),
            UNIQUE(property_id,weapon_id,mode_key),
            FOREIGN KEY(property_id) REFERENCES weapon_properties(id),
            CHECK(mode_key=COALESCE(mode,''))
        )""",
        """CREATE TABLE weapon_property_profile_traits (
            property_id TEXT NOT NULL,
            profile_position INTEGER NOT NULL,
            position INTEGER NOT NULL CHECK(position>=0),
            text TEXT NOT NULL,
            PRIMARY KEY(property_id,profile_position,position),
            FOREIGN KEY(property_id,profile_position)
                REFERENCES weapon_property_profiles(property_id,position)
        )""",
    )
    for statement in statements:
        connection.execute(statement)
    count_origins = sum(len(entry["origins"]) for entry in entries)
    count_profiles = sum(len(entry["profiles"]) for entry in entries)
    count_traits = sum(
        len(profile["traits"])
        for entry in entries for profile in entry["profiles"]
    )
    connection.execute(
        "INSERT INTO weapon_property_metadata VALUES (1,?,?,?,?,?,?,?,?,?,?,?)",
        (
            file_sha256(army), COLLECTION, SOURCE, _source_sha(connection),
            FORMAT, FORMAT_VERSION, len(entries), count_origins, count_profiles,
            count_traits, _digest(entries),
        ),
    )
    for position, entry in enumerate(entries):
        property_id = entry["id"]
        connection.execute(
            "INSERT INTO weapon_properties VALUES (?,?,?,?)",
            (property_id, position, entry["name"], entry["summary"]),
        )
        for index, origin in enumerate(entry["origins"]):
            record_id = origin.get("recordId")
            connection.execute(
                "INSERT INTO weapon_property_origins VALUES (?,?,?,?,?,?,?)",
                (
                    property_id, index, origin["domain"], origin["role"],
                    _origin_collection(connection, record_id) if record_id else None,
                    record_id, origin.get("sourceSection"),
                ),
            )
        for index, profile in enumerate(entry["profiles"]):
            connection.execute(
                "INSERT INTO weapon_property_profiles VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    property_id, index, profile["weaponId"], profile["mode"] or "",
                    profile["mode"], profile["weaponName"], profile["ammunitionSourceId"],
                    profile["ammunition"], profile["saving"], profile["savingNum"],
                ),
            )
            for trait_position, trait in enumerate(profile["traits"]):
                connection.execute(
                    "INSERT INTO weapon_property_profile_traits VALUES (?,?,?,?)",
                    (property_id, index, trait_position, trait),
                )
    read_weapon_properties(connection, army)


def read_weapon_properties(
    connection: sqlite3.Connection,
    army: Path | None = None,
) -> list[dict[str, Any]]:
    """Reconstruct exact property/ordered origins/ordered source profiles."""
    meta = connection.execute(
        "SELECT army_database_sha256,source_collection_id,source_id,source_sha256,"
        "source_format,source_version,property_count,origin_count,profile_count,"
        "trait_count,content_sha256 FROM weapon_property_metadata WHERE id=1"
    ).fetchone()
    if (
        meta is None
        or tuple(meta[1:6]) != (COLLECTION, SOURCE, _source_sha(connection), FORMAT, FORMAT_VERSION)
        or (army is not None and meta[0] != file_sha256(army))
    ):
        raise ValueError("Weapon Property source metadata or selected Army identity differs")
    properties = connection.execute(
        "SELECT id,position,name,summary FROM weapon_properties ORDER BY position"
    ).fetchall()
    if len(properties) != meta[6] or any(row[1] != i for i, row in enumerate(properties)):
        raise ValueError("Incomplete or unordered Weapon Property vocabulary")
    entries: list[dict[str, Any]] = []
    origin_count = profile_count = trait_count = 0
    for property_id, _position, name, summary in properties:
        origin_rows = connection.execute(
            "SELECT position,domain,role,rule_collection_id,record_id,source_section "
            "FROM weapon_property_origins WHERE property_id=? ORDER BY position",
            (property_id,),
        ).fetchall()
        profile_rows = connection.execute(
            "SELECT position,weapon_id,mode_key,mode,weapon_name,ammunition_source_id,"
            "ammunition,saving,saving_num FROM weapon_property_profiles "
            "WHERE property_id=? ORDER BY position",
            (property_id,),
        ).fetchall()
        if (
            any(row[0] != i for i, row in enumerate(origin_rows))
            or any(row[0] != i for i, row in enumerate(profile_rows))
        ):
            raise ValueError("Weapon Property source ordering differs")
        origins = []
        for _index, domain, role, collection_id, record_id, section in origin_rows:
            if record_id is not None and _origin_collection(connection, record_id) != collection_id:
                raise ValueError("Weapon Property origin no longer resolves to its current source")
            origins.append({
                "domain": domain, "role": role,
                **({"recordId": record_id} if record_id is not None else {}),
                **({"sourceSection": section} if section is not None else {}),
            })
        profiles = []
        for row in profile_rows:
            index, weapon_id, mode_key, mode, weapon_name, ammunition_id, ammo, saving, num = row
            if mode_key != (mode or ""):
                raise ValueError("Weapon Property mode key differs from source")
            traits = connection.execute(
                "SELECT position,text FROM weapon_property_profile_traits "
                "WHERE property_id=? AND profile_position=? ORDER BY position",
                (property_id, index),
            ).fetchall()
            if any(row[0] != i for i, row in enumerate(traits)):
                raise ValueError("Weapon Property Trait ordering differs")
            profiles.append({
                "weaponId": weapon_id, "weaponName": weapon_name, "mode": mode,
                "ammunitionSourceId": ammunition_id, "ammunition": ammo,
                "saving": saving, "savingNum": num,
                "traits": [row[1] for row in traits],
            })
            trait_count += len(traits)
        entries.append({
            "id": property_id, "name": name, "summary": summary,
            "origins": origins, "profiles": profiles,
        })
        origin_count += len(origins)
        profile_count += len(profiles)
    if (origin_count, profile_count, trait_count) != tuple(meta[7:10]):
        raise ValueError("Weapon Property source-row counts differ")
    _validate(connection, entries, army)
    if _digest(entries) != meta[10]:
        raise ValueError("Weapon Property source fingerprint differs")
    return entries


def validate_weapon_property_snapshot(connection: sqlite3.Connection) -> None:
    read_weapon_properties(connection)
