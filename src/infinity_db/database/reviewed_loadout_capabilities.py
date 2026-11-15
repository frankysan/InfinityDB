"""Reviewed additions to loadout-owned source capabilities.

Curated facts are separate from Army's immutable payload and bound to one
archive and exact source Army/unit/group/option. No name-based inference runs.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_curated_path

CURATED_PATH = maintained_curated_path("relationships", "loadout-capabilities.json")
FORMAT = "InfinityDB reviewed loadout capabilities"
CATALOGS = frozenset({"skills", "equipment", "weapons"})


def _positive(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"Reviewed loadout capability {field} must be a positive integer")
    return value


def load_reviewed_capabilities(
    path: Path = CURATED_PATH,
) -> tuple[str, tuple[dict[str, Any], ...], str]:
    """Validate the curated contract and return (snapshot SHA, facts, JSON SHA)."""
    content = path.read_bytes()
    data = json.loads(content)
    if (
        not isinstance(data, dict)
        or set(data) != {
            "format", "formatVersion", "snapshotArchiveSha256", "sourceArchive", "facts"
        }
        or data["format"] != FORMAT
        or data["formatVersion"] != 1
    ):
        raise ValueError("Invalid reviewed loadout capability document")
    snapshot = data["snapshotArchiveSha256"]
    if (
        not isinstance(snapshot, str)
        or len(snapshot) != 64
        or any(char not in "0123456789abcdef" for char in snapshot)
        or not isinstance(data["sourceArchive"], str)
        or not data["sourceArchive"].strip()
    ):
        raise ValueError("Reviewed loadout capabilities require pinned Army archive provenance")
    records = data["facts"]
    if not isinstance(records, list):
        raise ValueError("Reviewed loadout capability facts must be an array")
    seen: set[tuple[int, int, int, int, str, int]] = set()
    for fact in records:
        if not isinstance(fact, dict) or set(fact) != {
            "armyId", "unitId", "groupId", "optionId", "loadoutName",
            "catalog", "itemId", "itemName", "review",
        }:
            raise ValueError("Invalid reviewed loadout capability fact fields")
        for key in ("armyId", "unitId", "groupId", "optionId", "itemId"):
            _positive(fact[key], key)
        if fact["catalog"] not in CATALOGS:
            raise ValueError("Unsupported reviewed loadout capability catalog")
        if not all(
            isinstance(fact[key], str) and fact[key].strip()
            for key in ("loadoutName", "itemName")
        ):
            raise ValueError("Reviewed loadout capability names must be non-empty")
        review = fact["review"]
        if (
            not isinstance(review, dict)
            or set(review) != {"status", "reviewedOn", "reason"}
            or review["status"] != "reviewed"
            or not all(
                isinstance(review[key], str) and review[key].strip()
                for key in ("reviewedOn", "reason")
            )
        ):
            raise ValueError("Reviewed loadout capability fact lacks review evidence")
        key = (
            fact["armyId"], fact["unitId"], fact["groupId"],
            fact["optionId"], fact["catalog"], fact["itemId"],
        )
        if key in seen:
            raise ValueError(f"Duplicate reviewed loadout capability: {key}")
        seen.add(key)
    return snapshot, tuple(records), hashlib.sha256(content).hexdigest()


def published_reviewed_loadout_capabilities(
    connection: sqlite3.Connection,
) -> tuple[dict[str, Any], ...]:
    """Read validated build-time facts from the database, not the curated file."""
    row = connection.execute(
        "SELECT value FROM __infinity_metadata "
        "WHERE key = 'reviewedLoadoutCapabilities'"
    ).fetchone()
    if row is None:
        return ()
    facts = json.loads(row[0])
    if not isinstance(facts, list) or any(not isinstance(item, dict) for item in facts):
        raise ValueError("Invalid published reviewed loadout capabilities")
    return tuple(facts)


def materialize_reviewed_loadout_capabilities(
    connection: sqlite3.Connection, metadata: dict[str, Any],
    *, path: Path = CURATED_PATH,
) -> None:
    """Add exact, reviewed source omissions; refuse stale/invalid matching rows."""
    snapshot, facts, fingerprint = load_reviewed_capabilities(path)
    source = metadata.get("_meta", {})
    actual_snapshot = source.get("snapshotArchiveSha256") if isinstance(source, dict) else None
    # Another snapshot needs its own review: never project a fact onto different source data.
    if actual_snapshot != snapshot:
        return
    resolved: list[dict[str, Any]] = []
    for fact in facts:
        coordinates = (
            fact["armyId"], fact["unitId"], fact["groupId"], fact["optionId"]
        )
        row = connection.execute(
            "SELECT lp.name, lpo.loadout_payload_id FROM loadout_payload_occurrences AS lpo "
            "JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id "
            "WHERE lpo.army_id = ? AND lpo.unit_id = ? "
            "AND lpo.group_id = ? AND lpo.option_id = ?",
            coordinates,
        ).fetchone()
        if row is None or row[0] != fact["loadoutName"]:
            raise ValueError(
                f"Reviewed loadout capability target is missing or renamed: {coordinates}"
            )
        item = connection.execute(
            f"SELECT name FROM {fact['catalog']} WHERE id = ?", (fact["itemId"],)
        ).fetchone()
        if item is None or item[0] != fact["itemName"]:
            raise ValueError(
                f"Reviewed loadout capability catalog item is missing or renamed: {coordinates}"
            )
        present = connection.execute(
            f"SELECT 1 FROM loadout_payload_{fact['catalog']} "
            "WHERE loadout_payload_id = ? AND item_id = ? LIMIT 1",
            (row[1], fact["itemId"]),
        ).fetchone()
        if present is not None:
            raise ValueError(
                f"Reviewed loadout capability duplicates an Army source fact: {coordinates}"
            )
        resolved.append({
            "army_id": coordinates[0], "unit_id": coordinates[1],
            "group_id": coordinates[2], "option_id": coordinates[3],
            "catalog": fact["catalog"], "item_id": fact["itemId"],
            "name": fact["itemName"],
        })
    metadata["reviewedLoadoutCapabilities"] = resolved
    metadata["reviewedLoadoutCapabilitiesSha256"] = fingerprint
    metadata["reviewedLoadoutCapabilitiesCount"] = len(facts)
