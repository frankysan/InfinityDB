"""Attach additive public slugs to catalog API representations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.domain_references import public_slug_for_reference


def attach_public_catalog_slug(
    database: Database,
    catalog: str,
    item: dict[str, Any],
) -> None:
    """Attach a routable catalog slug without shadowing numeric compatibility URLs."""

    item_id = item.get("id")
    if type(item_id) is not int:
        return
    slug = public_slug_for_reference(database, catalog, item_id)
    if slug is not None:
        item["slug"] = slug


def enrich_nested_catalog_slugs(
    database: Database,
    value: dict[str, Any],
    catalogs: frozenset[str],
) -> dict[str, Any]:
    """Attach public slugs to named catalog occurrence lists in a nested payload."""

    result = deepcopy(value)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if key in catalogs and isinstance(child, list):
                    for item in child:
                        if isinstance(item, dict):
                            attach_public_catalog_slug(database, key, item)
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(result)
    return result
