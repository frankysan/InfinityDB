"""Attach additive public Army slugs to API reference structures."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.domain_references import public_slug_for_reference


def attach_public_army_slug(database: Database, item: dict[str, Any]) -> None:
    """Attach a routable Army slug without replacing source/context slug data."""

    army_id = item.get("id")
    if type(army_id) is not int:
        return
    slug = public_slug_for_reference(database, "armies", army_id)
    if slug is not None:
        item["public_slug"] = slug


def enrich_army_references(database: Database, value: dict[str, Any]) -> dict[str, Any]:
    """Attach public slugs to canonical Army references in one API payload copy."""

    result = deepcopy(value)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for id_key, slug_key in (
                ("main_army_id", "main_army_slug"),
                ("display_army_id", "display_army_slug"),
            ):
                army_id = node.get(id_key)
                if type(army_id) is int:
                    slug = public_slug_for_reference(database, "armies", army_id)
                    if slug is not None:
                        node[slug_key] = slug

            for key in ("main_faction", "display_faction", "faction"):
                item = node.get(key)
                if isinstance(item, dict):
                    attach_public_army_slug(database, item)

            for key in (
                "armies",
                "parent_armies",
                "reinforcement_sections",
            ):
                armies = node.get(key)
                if isinstance(armies, list):
                    for army in armies:
                        if isinstance(army, dict):
                            attach_public_army_slug(database, army)

            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(result)
    return result
