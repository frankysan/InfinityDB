"""Attach conservative, source-occurrence-backed Unit uses to reviewed delivery edges.

The published Army database owns exact list/Unit/group/option relationships.
Only reviewed delivery origins may acquire reverse uses. Profile and loadout
occurrences are distinct; generic Unit options and inferred Mine subtypes are
intentionally excluded until their contextual semantics are separately audited.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def _source_ids(db: sqlite3.Connection, record_id: str) -> tuple[int, ...]:
    domain, separator, slug = record_id.partition(":")
    catalog = {"weapon": "weapons", "equipment": "equipment"}.get(domain)
    if not separator or not slug or catalog is None:
        raise ValueError(f"Invalid reviewed delivery origin: {record_id}")
    rows = db.execute(
        "SELECT s.application_item_id, s.source_item_id "
        "FROM application_domain_slugs AS d "
        "JOIN application_catalog_sources AS s "
        "ON s.catalog = d.domain AND s.application_item_id = d.application_id "
        "WHERE d.domain = ? AND d.slug = ? "
        "ORDER BY s.source_item_id",
        (catalog, slug),
    ).fetchall()
    if not rows or len({row["application_item_id"] for row in rows}) != 1:
        raise ValueError(f"Unresolved reviewed delivery origin: {record_id}")
    return tuple(int(row["source_item_id"]) for row in rows)


def _occurrences(
    db: sqlite3.Connection, catalog: str, source_ids: tuple[int, ...],
) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in source_ids)
    rows: list[dict[str, Any]] = []
    for kind, owner, key, payload in (
        ("profile", "profile_payload_occurrences", "profile_payload_id", "profile_payloads"),
        ("loadout", "loadout_payload_occurrences", "loadout_payload_id", "loadout_payloads"),
    ):
        table = f"{kind}_payload_{catalog}"
        identity = "profile_id" if kind == "profile" else "option_id"
        query = (
            f"SELECT o.army_id, o.unit_id, o.group_id, o.{identity} AS identity_id, "
            "p.item_id AS source_item_id, p.position AS source_position, "
            "c.name AS context_name, a.name AS army_name, "
            "u.name AS unit_name, lu.slug AS unit_slug "
            f"FROM {owner} AS o "
            f"JOIN {table} AS p ON p.{key} = o.{key} "
            f"JOIN {payload} AS c ON c.id = o.{key} "
            "JOIN army_lists AS a ON a.id = o.army_id "
            "JOIN units AS u ON u.id = o.unit_id "
            "JOIN logical_unit_sources AS lus ON lus.source_unit_id = o.unit_id "
            "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
            f"WHERE p.item_id IN ({placeholders}) "
            "ORDER BY o.army_id, o.unit_id, o.group_id, identity_id, "
            "p.position, p.item_id"
        )
        for row in db.execute(query, source_ids):
            rows.append({
                "kind": kind,
                "armyId": row["army_id"], "armyName": row["army_name"],
                "unitId": row["unit_id"], "unitName": row["unit_name"],
                "unitSlug": row["unit_slug"], "groupId": row["group_id"],
                "profileId": row["identity_id"] if kind == "profile" else None,
                "optionId": row["identity_id"] if kind == "loadout" else None,
                "contextName": row["context_name"],
                "sourceItemId": row["source_item_id"],
                "sourcePosition": row["source_position"],
            })
    return rows


def attach_reviewed_unit_uses(army_db: Path, publication: dict[str, Any]) -> None:
    """Mutate the release projection with uses proven by both review and Army rows."""
    with sqlite3.connect(f"{army_db.resolve().as_uri()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        origin_cache: dict[str, list[dict[str, Any]]] = {}
        for obj in publication["objects"]:
            uses: list[dict[str, Any]] = []
            for edge in obj["deliverySources"]:
                record_id = edge["recordId"]
                if record_id not in origin_cache:
                    source_ids = _source_ids(db, record_id)
                    catalog = "weapons" if record_id.startswith("weapon:") else "equipment"
                    origin_cache[record_id] = _occurrences(db, catalog, source_ids)
                for occurrence in origin_cache[record_id]:
                    uses.append({
                        "originRecordId": record_id,
                        "method": edge["method"],
                        **occurrence,
                    })
            obj["unitUses"] = sorted(
                uses,
                key=lambda use: (
                    use["armyId"], use["unitId"], use["groupId"],
                    use["kind"], use["optionId"] if use["optionId"] is not None else -1,
                    use["profileId"] if use["profileId"] is not None else -1,
                    use["sourceItemId"], use["sourcePosition"],
                    use["originRecordId"], use["method"],
                ),
            )
