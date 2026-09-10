"""Supplementary metadata from the Infinity Army API.

This source complements, but never replaces, the Army list snapshots.  In
particular, Army list files remain the authority for a unit's availability.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class MetadataError(ValueError):
    pass


# Source field, normalized table name, primary-key field.  Weapon records have
# repeated IDs for alternate modes, so their source ordering is their identity.
METADATA_TABLES = {
    "factions": ("metadata_factions", "id"),
    "ammunitions": ("metadata_ammunitions", "id"),
    "weapons": ("metadata_weapons", "position"),
    "skills": ("metadata_skills", "id"),
    "equips": ("metadata_equipment", "id"),
    "hack": ("metadata_hacking_programs", "position"),
    "martialArts": ("metadata_martial_arts", "position"),
    "metachemistry": ("metadata_metachemistry", "id"),
    "booty": ("metadata_booty", "id"),
}


def decode_metadata(raw: bytes, filename: str) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MetadataError(f"Could not parse {filename}: {exc}") from exc
    envelope = {
        "sourceFile": Path(filename).name,
        "sourceSha256": hashlib.sha256(raw).hexdigest(),
        "data": data,
    }
    validate_metadata_envelope(envelope)
    return envelope


def load_metadata(path: Path) -> dict[str, Any]:
    try:
        return decode_metadata(path.read_bytes(), path.name)
    except OSError as exc:
        raise MetadataError(f"Could not read {path}: {exc}") from exc


def validate_metadata_envelope(envelope: dict[str, Any]) -> None:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), dict):
        raise MetadataError("Army metadata must contain a data object")
    if not isinstance(envelope.get("sourceFile"), str) or not isinstance(
        envelope.get("sourceSha256"), str
    ):
        raise MetadataError("Army metadata source information is invalid")
    data = envelope["data"]
    if not isinstance(data.get("factions"), list):
        raise MetadataError("Army metadata must contain a factions array")
    for source_name, (_, key) in METADATA_TABLES.items():
        rows = data.get(source_name)
        if rows is None:
            continue
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise MetadataError(f"metadata.{source_name} must be an array of objects")
        seen: set[int] = set()
        for position, row in enumerate(rows, start=1):
            identity = position if key == "position" else row.get(key)
            if type(identity) is not int:
                raise MetadataError(f"metadata.{source_name}.{key} must be an integer")
            if identity in seen:
                raise MetadataError(f"metadata.{source_name} has duplicate {key} {identity}")
            seen.add(identity)
    for faction in data["factions"]:
        if not isinstance(faction.get("name"), str) or not faction["name"].strip():
            raise MetadataError("metadata.factions entries need nonempty names")
        if faction.get("parent") is not None and type(faction["parent"]) is not int:
            raise MetadataError("metadata.factions.parent must be an integer or null")


def normalize_metadata(envelope: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return tables that preserve source fields exactly, adding a position if needed."""
    validate_metadata_envelope(envelope)
    result: dict[str, list[dict[str, Any]]] = {}
    for source_name, (table_name, key) in METADATA_TABLES.items():
        rows: list[dict[str, Any]] = []
        for position, source_row in enumerate(envelope["data"].get(source_name, []), start=1):
            row = dict(source_row)
            if key == "position":
                if "position" in row:
                    raise MetadataError(f"metadata.{source_name}.position is reserved")
                row["position"] = position
            rows.append(row)
        result[table_name] = rows
    return result
