"""Relational reviewed Combined Saving Roll annotations for exact Army Weapon modes.

Rules stores the reviewed source signatures, not inferred gameplay calculations.
The source JSON remains editable build input, never a v15 runtime dependency.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .build_provenance import file_sha256
from .database.repository import Database

SCHEMA_VERSION = 15
COMPATIBILITY_VERSION = 17
COLLECTION = "n5-core-v5.3"
PDF = "n5-core-v5.3-pdf"
PAGE = 67


def _digest(mapping: dict[tuple[int, str], dict[str, Any]]) -> str:
    ordered = [
        {"weaponId": key[0], "mode": key[1], "entry": mapping[key]}
        for key in sorted(mapping)
    ]
    return hashlib.sha256(
        json.dumps(
            ordered, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _source(connection: sqlite3.Connection) -> tuple[str, str]:
    row = connection.execute(
        "SELECT s.sha256,s.url FROM sources s JOIN collections c "
        "ON s.collection_id=c.id WHERE c.id=? AND c.status='current' "
        "AND s.id=? AND s.kind='pdf' AND s.authority='primary' "
        "AND s.page_count>=?",
        (COLLECTION, PDF, PAGE),
    ).fetchone()
    if row is None or not isinstance(row[0], str) or len(row[0]) != 64:
        raise ValueError("Combined Saving Roll source is not the current N5.3 PDF")
    return row[0], row[1]


def _checked_mapping(
    connection: sqlite3.Connection, mapping: dict[tuple[int, str], dict[str, Any]],
    army_path: Path | None = None,
) -> None:
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Missing reviewed Combined Saving Roll annotations")
    _source(connection)
    database = Database(army_path) if army_path is not None else None
    seen: dict[int, set[str]] = {}
    for key, entry in mapping.items():
        if (
            not isinstance(key, tuple) or len(key) != 2
            or type(key[0]) is not int or key[0] <= 0
            or not isinstance(key[1], str) or not key[1]
            or not isinstance(entry, dict)
            or set(entry) != {
                "weaponId", "weaponName", "modes", "ammunitionSourceId",
                "ammunition", "saving", "savingNum", "source",
            }
            or type(entry["weaponId"]) is not int or entry["weaponId"] != key[0]
            or not isinstance(entry["weaponName"], str) or not entry["weaponName"].strip()
            or type(entry["ammunitionSourceId"]) is not int
            or entry["ammunitionSourceId"] <= 0
            or entry["ammunition"] != "N"
            or entry["saving"] != "ARM and BTS"
            or entry["savingNum"] != "1 and 1"
            or entry["source"] != {"sourceId": COLLECTION, "page": PAGE}
            or not isinstance(entry["modes"], list)
            or not entry["modes"]
            or any(not isinstance(mode, str) or not mode for mode in entry["modes"])
            or len(set(entry["modes"])) != len(entry["modes"])
            or key[1] not in entry["modes"]
        ):
            raise ValueError("Invalid Combined Saving Roll source profile")
        seen.setdefault(key[0], set()).add(key[1])
    if len(seen) != 3 or sum(map(len, seen.values())) != 6:
        raise ValueError("Reviewed Combined Saving Roll inventory must contain six modes")
    for weapon_id, modes in seen.items():
        representative = mapping[weapon_id, next(iter(modes))]
        if modes != set(representative["modes"]):
            raise ValueError("Incomplete Combined Saving Roll Weapon mode coverage")
        if any(mapping[weapon_id, mode] != representative for mode in modes):
            raise ValueError("Conflicting Combined Saving Roll Weapon signatures")
        if database is None:
            continue
        item = database.get_catalog_item("weapons", weapon_id)
        if item is None or item["name"] != representative["weaponName"]:
            raise ValueError("Reviewed Combined Saving Roll Weapon identity changed")
        profiles = item["profiles"]
        if {profile.get("mode") for profile in profiles} != modes or len(profiles) != len(modes):
            raise ValueError("Reviewed Combined Saving Roll Army mode inventory changed")
        for profile in profiles:
            if any(
                profile.get(field) != representative[field_in_review]
                for field, field_in_review in (
                    ("id", "weaponId"), ("name", "weaponName"),
                    ("ammunition_source_id", "ammunitionSourceId"),
                    ("ammunition", "ammunition"), ("saving", "saving"),
                    ("saving_num", "savingNum"),
                )
            ):
                raise ValueError("Reviewed Combined Saving Roll Army profile changed")


def stage_combined_saving_rolls(
    connection: sqlite3.Connection, mapping: dict[tuple[int, str], dict[str, Any]],
    army_path: Path,
) -> None:
    """Materialize the fully validated reviewed mapping within a v14 export."""
    if connection.execute("PRAGMA user_version").fetchone()[0] != 14:
        raise ValueError("Combined Saving Roll embedding requires the Rules v14 baseline")
    _checked_mapping(connection, mapping, army_path)
    source_sha, _source_url = _source(connection)
    schema = (
        """CREATE TABLE combined_saving_roll_metadata (
            id INTEGER PRIMARY KEY CHECK(id=1),
            army_database_sha256 TEXT NOT NULL CHECK(length(army_database_sha256)=64),
            source_collection_id TEXT NOT NULL,
            source_pdf_id TEXT NOT NULL,
            source_pdf_sha256 TEXT NOT NULL CHECK(length(source_pdf_sha256)=64),
            source_page INTEGER NOT NULL CHECK(source_page>0),
            critical_additional_rolls INTEGER NOT NULL CHECK(critical_additional_rolls=1),
            critical_attribute TEXT NOT NULL CHECK(critical_attribute='ARM'),
            weapon_count INTEGER NOT NULL CHECK(weapon_count>0),
            profile_count INTEGER NOT NULL CHECK(profile_count>0),
            content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
            FOREIGN KEY(source_collection_id,source_pdf_id)
                REFERENCES sources(collection_id,id)
        )""",
        """CREATE TABLE weapon_combined_saving_roll_profiles (
            weapon_id INTEGER NOT NULL CHECK(weapon_id>0),
            mode TEXT NOT NULL CHECK(length(mode)>0),
            weapon_name TEXT NOT NULL,
            position INTEGER NOT NULL UNIQUE CHECK(position>=0),
            mode_position INTEGER NOT NULL CHECK(mode_position>=0),
            ammunition_source_id INTEGER NOT NULL CHECK(ammunition_source_id>0),
            ammunition TEXT NOT NULL,
            saving TEXT NOT NULL,
            saving_num TEXT NOT NULL,
            PRIMARY KEY(weapon_id,mode),
            UNIQUE(weapon_id,mode_position)
        )""",
    )
    for sql in schema:
        connection.execute(sql)
    connection.execute(
        "INSERT INTO combined_saving_roll_metadata VALUES (1,?,?,?,?,?,?,?,?,?,?)",
        (file_sha256(army_path), COLLECTION, PDF, source_sha, PAGE, 1, "ARM",
         3, len(mapping), _digest(mapping)),
    )
    position = 0
    for weapon_id in sorted({key[0] for key in mapping}):
        entry = next(entry for (id_, _), entry in mapping.items() if id_ == weapon_id)
        for mode_position, mode in enumerate(entry["modes"]):
            connection.execute(
                "INSERT INTO weapon_combined_saving_roll_profiles "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (weapon_id, mode, entry["weaponName"], position, mode_position,
                 entry["ammunitionSourceId"], entry["ammunition"],
                 entry["saving"], entry["savingNum"]),
            )
            position += 1
    read_combined_saving_rolls(connection, army_path)


def read_combined_saving_rolls(
    connection: sqlite3.Connection, army_path: Path | None = None,
) -> dict[tuple[int, str], dict[str, Any]]:
    """Read source-matched annotations, rejecting missing or altered relational facts."""
    meta = connection.execute(
        "SELECT army_database_sha256,source_collection_id,source_pdf_id,"
        "source_pdf_sha256,source_page,critical_additional_rolls,"
        "critical_attribute,weapon_count,profile_count,content_sha256 "
        "FROM combined_saving_roll_metadata WHERE id=1"
    ).fetchone()
    source_sha, _ = _source(connection)
    if (
        meta is None
        or tuple(meta[1:7]) != (COLLECTION, PDF, source_sha, PAGE, 1, "ARM")
        or (army_path is not None and meta[0] != file_sha256(army_path))
    ):
        raise ValueError("Combined Saving Roll source or Army identity differs")
    rows = connection.execute(
        "SELECT weapon_id,mode,weapon_name,position,mode_position,"
        "ammunition_source_id,ammunition,saving,saving_num "
        "FROM weapon_combined_saving_roll_profiles ORDER BY position"
    ).fetchall()
    if (
        len(rows) != meta[8]
        or len({row[0] for row in rows}) != meta[7]
        or any(row[3] != index for index, row in enumerate(rows))
    ):
        raise ValueError("Incomplete or unordered Combined Saving Roll profiles")
    groups: dict[int, list[tuple]] = {}
    for row in rows:
        groups.setdefault(row[0], []).append(tuple(row))
    mapping: dict[tuple[int, str], dict[str, Any]] = {}
    for weapon_id, weapon_rows in groups.items():
        modes = [row[1] for row in sorted(weapon_rows, key=lambda value: value[4])]
        if any(row[4] != index for index, row in enumerate(
            sorted(weapon_rows, key=lambda value: value[4])
        )):
            raise ValueError("Combined Saving Roll mode order differs")
        for row in weapon_rows:
            mapping[weapon_id, row[1]] = {
                "weaponId": weapon_id, "weaponName": row[2], "modes": modes,
                "ammunitionSourceId": row[5], "ammunition": row[6],
                "saving": row[7], "savingNum": row[8],
                "source": {"sourceId": COLLECTION, "page": PAGE},
            }
    _checked_mapping(connection, mapping, army_path)
    if _digest(mapping) != meta[9]:
        raise ValueError("Combined Saving Roll content fingerprint differs")
    return mapping


def validate_combined_saving_roll_snapshot(connection: sqlite3.Connection) -> None:
    read_combined_saving_rolls(connection)
