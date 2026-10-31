"""Attach conservative, source-occurrence-backed Unit uses to reviewed delivery edges.

The published Army database owns exact list/Unit/group/option relationships.
Only reviewed delivery origins may acquire reverse uses. Profile, loadout and
source-defined Unit-option occurrences remain distinct. Unit options do not
inherit an Army/group, and unresolved Mine subtypes are never inferred.
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
    # Some imported source Unit names are NULL. Prefer the exact source value,
    # then the existing normalized logical-unit name; never invent a carrier.
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
            "COALESCE(NULLIF(u.name, ''), lu.name) AS unit_name, lu.slug AS unit_slug "
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
    # Source-defined Unit options have no Army/group context. Preserve that
    # absence rather than assigning every Army containing this source Unit.
    for row in db.execute(
        f"SELECT o.unit_id, o.option_id, o.item_id AS source_item_id, "
        "o.position AS source_position, c.name AS context_name, "
        "COALESCE(NULLIF(u.name, ''), lu.name) AS unit_name, lu.slug AS unit_slug "
        f"FROM unit_option_{catalog} AS o "
        "JOIN unit_options AS c "
        "ON c.unit_id = o.unit_id AND c.option_id = o.option_id "
        "JOIN units AS u ON u.id = o.unit_id "
        "JOIN logical_unit_sources AS lus ON lus.source_unit_id = o.unit_id "
        "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
        f"WHERE o.item_id IN ({placeholders}) "
        "ORDER BY o.unit_id, o.option_id, o.position, o.item_id",
        source_ids,
    ):
        rows.append({
            "kind": "unit-option",
            "armyId": None, "armyName": None,
            "unitId": row["unit_id"], "unitName": row["unit_name"],
            "unitSlug": row["unit_slug"], "groupId": None,
            "profileId": None, "optionId": row["option_id"],
            "contextName": row["context_name"],
            "sourceItemId": row["source_item_id"],
            "sourcePosition": row["source_position"],
        })
    # Each Include retains a concrete Army/profile or Army/loadout parent and
    # targets an exact canonical loadout payload. This is one explicit edge,
    # not a recursively inferred family of Units/options.
    for kind in ("profile", "loadout"):
        parent_table = f"{kind}_payload_occurrences"
        parent_id = "profile_id" if kind == "profile" else "option_id"
        for row in db.execute(
            f"SELECT i.army_id, i.unit_id, i.group_id, i.{parent_id} AS identity_id, "
            "i.position AS include_position, i.target_loadout_payload_id, "
            "p.item_id AS source_item_id, p.position AS source_position, "
            "c.name AS context_name, target.name AS target_name, "
            "a.name AS army_name, "
            "COALESCE(NULLIF(u.name, ''), lu.name) AS unit_name, lu.slug AS unit_slug "
            f"FROM {kind}_occurrence_includes AS i "
            f"JOIN {parent_table} AS parent "
            f"ON parent.army_id = i.army_id AND parent.unit_id = i.unit_id "
            f"AND parent.group_id = i.group_id AND parent.{parent_id} = i.{parent_id} "
            f"JOIN {kind}_payloads AS c "
            f"ON c.id = parent.{kind}_payload_id "
            "JOIN loadout_payloads AS target ON target.id = i.target_loadout_payload_id "
            f"JOIN loadout_payload_{catalog} AS p "
            "ON p.loadout_payload_id = target.id "
            "JOIN army_lists AS a ON a.id = i.army_id "
            "JOIN units AS u ON u.id = i.unit_id "
            "JOIN logical_unit_sources AS lus ON lus.source_unit_id = i.unit_id "
            "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
            f"WHERE p.item_id IN ({placeholders}) "
            "ORDER BY i.army_id, i.unit_id, i.group_id, identity_id, "
            "i.position, target.id, p.position, p.item_id",
            source_ids,
        ):
            rows.append({
                "kind": f"{kind}-include",
                "armyId": row["army_id"], "armyName": row["army_name"],
                "unitId": row["unit_id"], "unitName": row["unit_name"],
                "unitSlug": row["unit_slug"], "groupId": row["group_id"],
                "profileId": row["identity_id"] if kind == "profile" else None,
                "optionId": row["identity_id"] if kind == "loadout" else None,
                "contextName": row["context_name"],
                "includePosition": row["include_position"],
                "targetLoadoutPayloadId": row["target_loadout_payload_id"],
                "targetName": row["target_name"],
                "sourceItemId": row["source_item_id"],
                "sourcePosition": row["source_position"],
            })
    # A source Unit option can Include a loadout whose target variant is
    # resolved in one or more Armies. The target Army identifies the included
    # payload only; it is not the parent Unit option's Army membership.
    for row in db.execute(
        "SELECT i.unit_id, i.option_id, i.position AS include_position, "
        "i.target_army_id, i.target_loadout_payload_id, "
        "p.item_id AS source_item_id, p.position AS source_position, "
        "c.name AS context_name, target.name AS target_name, "
        "a.name AS target_army_name, "
        "COALESCE(NULLIF(u.name, ''), lu.name) AS unit_name, lu.slug AS unit_slug "
        "FROM unit_option_include_targets AS i "
        "JOIN unit_options AS c "
        "ON c.unit_id = i.unit_id AND c.option_id = i.option_id "
        "JOIN loadout_payloads AS target ON target.id = i.target_loadout_payload_id "
        f"JOIN loadout_payload_{catalog} AS p "
        "ON p.loadout_payload_id = target.id "
        "JOIN army_lists AS a ON a.id = i.target_army_id "
        "JOIN units AS u ON u.id = i.unit_id "
        "JOIN logical_unit_sources AS lus ON lus.source_unit_id = i.unit_id "
        "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
        f"WHERE p.item_id IN ({placeholders}) "
        "ORDER BY i.unit_id, i.option_id, i.position, i.target_army_id, "
        "target.id, p.position, p.item_id",
        source_ids,
    ):
        rows.append({
            "kind": "unit-option-include",
            "armyId": None, "armyName": None,
            "unitId": row["unit_id"], "unitName": row["unit_name"],
            "unitSlug": row["unit_slug"], "groupId": None,
            "profileId": None, "optionId": row["option_id"],
            "contextName": row["context_name"],
            "includePosition": row["include_position"],
            "targetArmyId": row["target_army_id"],
            "targetArmyName": row["target_army_name"],
            "targetLoadoutPayloadId": row["target_loadout_payload_id"],
            "targetName": row["target_name"],
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
                    use["armyId"] if use["armyId"] is not None else -1,
                    use["unitId"], use["groupId"] if use["groupId"] is not None else -1,
                    use["kind"], use["optionId"] if use["optionId"] is not None else -1,
                    use["profileId"] if use["profileId"] is not None else -1,
                    use["sourceItemId"], use["sourcePosition"],
                    use["originRecordId"], use["method"],
                ),
            )
