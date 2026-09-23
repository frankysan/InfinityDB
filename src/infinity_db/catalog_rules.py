"""Compose Army catalog items with optional curated rules data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.rules_database import ArmyLinkRef, RulesDatabase


def _special_profile(record: dict[str, Any]) -> dict[str, Any] | None:
    facts = record.get("facts")
    if not isinstance(facts, dict):
        return None
    profile = facts.get("specialProfile")
    if not isinstance(profile, dict):
        return None
    return {
        "stats": deepcopy(profile["stats"]),
        "equipment": list(profile["equipment"]),
        "skills": list(profile["skills"]),
        "cc_weapon": profile["ccWeapon"],
    }


class CatalogRules:
    """Enrich Army catalog items with curated rule records when available."""

    def __init__(self, rules_database: RulesDatabase | None) -> None:
        self.rules_database = rules_database

    @staticmethod
    def _army_refs(item: dict[str, Any]) -> tuple[ArmyLinkRef, ...]:
        item_id = int(item["id"])
        slug = item.get("slug")
        return (item_id, slug) if isinstance(slug, str) else (item_id,)

    def enrich_catalog_item(
        self, catalog: str, item: dict[str, Any]
    ) -> dict[str, Any]:
        """Add curated rules and special profiles to one catalog item."""
        result = deepcopy(item)
        if self.rules_database is None:
            return result

        entities = {"equipment": "equipment", "weapons": "weapon"}
        entity = entities.get(catalog)
        if entity is None:
            return result

        records_by_id: dict[str, dict[str, Any]] = {}
        for army_ref in self._army_refs(result):
            for record in self.rules_database.composed_records_for_army_link(
                entity, army_ref
            ):
                records_by_id.setdefault(record["id"], record)
        records = list(records_by_id.values())
        if records:
            result["rules"] = records

        if catalog != "weapons":
            return result

        profiles = [
            profile
            for record in records
            if (profile := _special_profile(record)) is not None
        ]
        if len(profiles) > 1:
            raise ValueError(
                f"Weapon {result['id']} has multiple curated special profiles"
            )
        if profiles:
            result["special_profile"] = profiles[0]
        return result
