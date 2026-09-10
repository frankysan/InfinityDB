"""Read-only application queries over the versioned normalized database."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from infinity_army_data.normalize import FORMAT_NAME, FORMAT_VERSION

from .schema import APPLICATION_ID, METADATA_TABLE, ROW_JSON, SCHEMA_VERSION, TABLES, quote

SQLITE_INTEGER_MIN = -(2**63)
SQLITE_INTEGER_MAX = 2**63 - 1
UNIT_NAME_SQL = "COALESCE(NULLIF(u.name, ''), 'Unit ' || u.id)"


def unit_sort_key(value: object) -> str:
    """Return a case-insensitive, punctuation-free key for unit-name ordering."""
    decomposed = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(character for character in decomposed if character.isalnum())


def unit_group_key(row: sqlite3.Row) -> tuple[int, str]:
    """Identify duplicate unit records that belong to the same 10,000-ID family."""
    return (
        row["id"] % 10_000,
        (row["isc"] or row["name"]).casefold(),
    )


def unit_base_identity(row: sqlite3.Row) -> str:
    """Return an ISC identity that treats reinforcement labels as secondary."""
    identity = row["isc"] or row["name"]
    return re.sub(r"^reinf\.\s*", "", identity, flags=re.IGNORECASE).casefold()


def logical_unit_groups(
    rows: list[sqlite3.Row], memberships: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Combine 10,000-ID duplicates and their reinforcement-only variants."""
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        armies = memberships[row["id"]]
        reinforcement_only = bool(armies) and all(army["id"] % 100 == 99 for army in armies)
        base_identity = unit_base_identity(row)
        key = (
            ("reinforcement", base_identity) if reinforcement_only
            else ("standard", *unit_group_key(row))
        )
        group = groups.setdefault(key, {
            "id": row["id"], "name": row["name"], "isc": row["isc"],
            "slug": row["slug"] if "slug" in row.keys() else None,
            "source_ids": [],
            "names": [], "armies": {},
            "base_identity": base_identity, "reinforcement_only": reinforcement_only,
        })
        group["source_ids"].append(row["id"])
        group["names"].append(row["name"])
        for army in armies:
            group["armies"][army["id"]] = army

    standard_groups: dict[str, list[dict[str, Any]]] = {}
    for group in groups.values():
        if not group["reinforcement_only"]:
            standard_groups.setdefault(group["base_identity"], []).append(group)
    for key, group in list(groups.items()):
        candidates = standard_groups.get(group["base_identity"], [])
        if group["reinforcement_only"] and len(candidates) == 1:
            target = candidates[0]
            target["source_ids"].extend(group["source_ids"])
            target["names"].extend(group["names"])
            target["armies"].update(group["armies"])
            del groups[key]
    return list(groups.values())


def army_name(row: sqlite3.Row) -> str:
    if row["name"]:
        return row["name"]
    if row["slug"] == "reinf":
        return f"Reinforcements ({row['id']})"
    if row["slug"]:
        derived_name = re.sub(r"[_-]+", " ", row["slug"]).strip().title()
        if derived_name:
            return derived_name
    return f"Army {row['id']}"


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise ValueError(f"Database does not exist: {self.path}. Build it before serving.")
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function("casefold", 1, lambda value: (value or "").casefold())
        connection.create_function("unit_sort_key", 1, unit_sort_key)
        try:
            connection.execute("BEGIN")
            yield connection
        finally:
            connection.close()

    def validate(self) -> None:
        """Reject missing, unrelated, unsupported, incomplete, or corrupt databases."""
        with self._connect() as connection:
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if application_id != APPLICATION_ID or version != SCHEMA_VERSION:
                raise ValueError("Unsupported InfinityDB database; rebuild it from normalized JSON")
            for name, definition in TABLES.items():
                columns = {
                    row["name"]
                    for row in connection.execute(f"PRAGMA table_info({quote(name)})")
                }
                if not {*definition.key, *definition.fields, ROW_JSON} <= columns:
                    raise ValueError(f"Incomplete database schema: {name}; rebuild the database")
            row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?", ("_meta",)
            ).fetchone()
            try:
                meta = json.loads(row["value"]) if row else None
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("Database has invalid import metadata") from exc
            if (
                not isinstance(meta, dict)
                or meta.get("format") != FORMAT_NAME
                or meta.get("formatVersion") != FORMAT_VERSION
            ):
                raise ValueError("Database has invalid normalized format metadata")
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Database integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("Database contains broken foreign keys")

    def list_armies(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.id, a.name, a.slug, a.kind, COUNT(u.id) AS unit_count "
                "FROM army_lists AS a "
                "LEFT JOIN army_units AS au ON au.army_id = a.id "
                "LEFT JOIN units AS u ON u.id = au.unit_id AND u.source_defined = 1 "
                "GROUP BY a.id ORDER BY casefold(COALESCE(a.name, a.slug, '')), a.id"
            ).fetchall()
            return [
                {
                    "id": row["id"], "name": army_name(row), "slug": row["slug"],
                    "kind": row["kind"], "unit_count": row["unit_count"],
                }
                for row in rows
            ]

    def list_units(
        self, army_id: int | None = None, search: str = "", limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        if army_id is not None and (
            type(army_id) is not int or not SQLITE_INTEGER_MIN <= army_id <= SQLITE_INTEGER_MAX
        ):
            raise ValueError("army_id must be an integer within SQLite's signed 64-bit range")
        if not isinstance(search, str):
            raise ValueError("search must be a string")
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500")
        if type(offset) is not int or not 0 <= offset <= SQLITE_INTEGER_MAX:
            raise ValueError("offset must be a nonnegative integer at most 9223372036854775807")
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.slug, u.canonical_faction_id "
                "FROM units AS u WHERE u.source_defined = 1 ORDER BY u.id"
            ).fetchall()
            memberships: dict[int, list[dict[str, Any]]] = {row["id"]: [] for row in rows}
            if rows:
                army_rows = connection.execute(
                    "SELECT au.unit_id, a.id, a.name, a.slug FROM army_units AS au "
                    "JOIN army_lists AS a ON a.id = au.army_id "
                    "ORDER BY a.id"
                )
                for army in army_rows:
                    if army["unit_id"] in memberships:
                        memberships[army["unit_id"]].append(
                        {"id": army["id"], "name": army_name(army)}
                        )
            groups = logical_unit_groups(rows, memberships)
            search_key = search.casefold()
            grouped = [
                group for group in groups
                if (army_id is None or army_id in group["armies"])
                and (not search or any(search_key in name.casefold() for name in group["names"]))
            ]
            grouped.sort(key=lambda group: (unit_sort_key(group["name"]), group["id"]))
            total = len(grouped)
            items = [
                {
                    "id": group["id"], "name": group["name"], "isc": group["isc"],
                    "slug": group["slug"],
                    "source_ids": group["source_ids"],
                    "army_ids": list(group["armies"]), "armies": list(group["armies"].values()),
                }
                for group in grouped[offset:offset + limit]
            ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_unit(self, unit_id: int) -> dict[str, Any] | None:
        """Return a browsable unit and its army-specific profiles and loadouts."""
        if type(unit_id) is not int or not 0 <= unit_id <= SQLITE_INTEGER_MAX:
            raise ValueError("unit_id must be a nonnegative SQLite signed 64-bit integer")
        with self._connect() as connection:
            selected = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.isc_abbr, u.slug, u.notes, "
                "u.canonical_faction_id "
                "FROM units AS u WHERE u.id = ? AND u.source_defined = 1", (unit_id,)
            ).fetchone()
            if selected is None:
                return None
            siblings = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.isc_abbr, u.slug, u.notes, "
                "u.canonical_faction_id FROM units AS u WHERE u.source_defined = 1 ORDER BY u.id"
            ).fetchall()
            memberships: dict[int, list[dict[str, Any]]] = {row["id"]: [] for row in siblings}
            membership_rows = connection.execute(
                "SELECT au.unit_id, a.id, a.name, a.slug FROM army_units AS au "
                "JOIN army_lists AS a ON a.id = au.army_id ORDER BY a.id"
            )
            for army in membership_rows:
                if army["unit_id"] in memberships:
                    memberships[army["unit_id"]].append(
                        {"id": army["id"], "name": army_name(army)}
                    )
            group = next(
                group for group in logical_unit_groups(siblings, memberships)
                if selected["id"] in group["source_ids"]
            )
            source_ids = group["source_ids"]
            unit = next(sibling for sibling in siblings if sibling["id"] == group["id"])
            placeholders = ", ".join("?" for _ in source_ids)
            armies = [
                {"id": army["id"], "name": army["name"], "profiles": [], "loadouts": []}
                for army in group["armies"].values()
            ]
            by_army = {army["id"]: army for army in armies}
            profile_rows = connection.execute(
                "SELECT p.army_id, p.group_id, p.profile_id, p.name, p.move_1, p.move_2, "
                "p.cc, p.bs, p.ph, p.wip, p.arm, p.bts, p.vitality, p.silhouette, p.ava "
                f"FROM profiles AS p WHERE p.unit_id IN ({placeholders}) "
                "ORDER BY p.army_id, p.group_id, p.position, p.profile_id", source_ids
            )
            for profile in profile_rows:
                item = {
                    key: profile[key] for key in profile.keys() if key != "army_id"
                }
                if item not in by_army[profile["army_id"]]["profiles"]:
                    by_army[profile["army_id"]]["profiles"].append(item)
            loadout_rows = connection.execute(
                "SELECT o.army_id, o.group_id, o.option_id, o.name, o.points, o.swc, "
                "o.minis, o.disabled "
                f"FROM loadout_options AS o WHERE o.unit_id IN ({placeholders}) "
                "ORDER BY o.army_id, o.group_id, o.position, o.option_id", source_ids
            )
            for loadout in loadout_rows:
                item = {
                    key: loadout[key] for key in loadout.keys() if key != "army_id"
                }
                if item not in by_army[loadout["army_id"]]["loadouts"]:
                    by_army[loadout["army_id"]]["loadouts"].append(item)
        return {
            "id": unit["id"], "name": unit["name"], "isc": unit["isc"], "slug": unit["slug"],
            "isc_abbr": unit["isc_abbr"], "notes": unit["notes"], "source_ids": source_ids,
            "armies": armies,
        }
