"""Attach additive public slugs to Unit API representations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database


def attach_public_unit_slug(database: Database, item: dict[str, Any]) -> None:
    """Attach a routable Unit slug without replacing source/context slug data."""

    unit_id = item.get("id")
    if type(unit_id) is not int:
        return
    application_id = database.application_unit_id(unit_id)
    if application_id is None:
        return
    slug = database.application_slug("units", application_id)
    if slug is not None and not slug.isdigit():
        item["public_slug"] = slug


def enrich_unit_items(
    database: Database,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return detached Unit list items with public slugs attached."""

    result = deepcopy(items)
    for item in result:
        attach_public_unit_slug(database, item)
    return result


def enrich_nested_unit_slugs(database: Database, value: dict[str, Any]) -> dict[str, Any]:
    """Attach public slugs to nested ``units`` collections in a payload copy."""

    result = deepcopy(value)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "units" and isinstance(child, list):
                    for item in child:
                        if isinstance(item, dict):
                            attach_public_unit_slug(database, item)
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(result)
    return result
