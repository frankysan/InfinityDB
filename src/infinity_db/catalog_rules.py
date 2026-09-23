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
    def _application_refs(item: dict[str, Any]) -> tuple[ArmyLinkRef, ...]:
        item_id = int(item["id"])
        slug = item.get("slug")
        return (item_id, slug) if isinstance(slug, str) else (item_id,)

    @staticmethod
    def _source_ids(item: dict[str, Any]) -> tuple[int, ...]:
        source_ids = {int(variant["item_id"]) for variant in item.get("variants", [])}
        source_ids.add(int(item["id"]))
        return tuple(sorted(source_ids))

    def enrich_catalog_item(
        self, catalog: str, item: dict[str, Any]
    ) -> dict[str, Any]:
        """Add curated rules and special profiles to one catalog item."""
        result = deepcopy(item)
        rules_database = self.rules_database
        if rules_database is None:
            return result

        entities = {"equipment": "equipment", "weapons": "weapon"}
        entity = entities.get(catalog)
        if entity is None:
            return result

        family_rules: dict[str, dict[str, Any]] = {}
        source_rules: dict[int, dict[str, dict[str, Any]]] = {}

        def collect_rules(army_ref: ArmyLinkRef, source_id: int | None) -> None:
            for record in rules_database.composed_records_for_army_link(
                entity, army_ref
            ):
                inheritance = (record.get("variant_semantics") or {}).get(
                    "inheritance"
                )
                if inheritance == "source":
                    if source_id is None:
                        raise ValueError(
                            f"Source-specific {entity} rule {record['id']!r} must be "
                            "linked by numeric source id"
                        )
                    source_rules.setdefault(source_id, {}).setdefault(
                        record["id"], record
                    )
                else:
                    family_rules.setdefault(record["id"], record)

        for source_id in self._source_ids(result):
            collect_rules(source_id, source_id)
        for army_ref in self._application_refs(result):
            if isinstance(army_ref, str):
                collect_rules(army_ref, None)

        records = list(family_rules.values())
        if records:
            result["rules"] = records
        for variant in result.get("variants", []):
            variant_rules = source_rules.get(int(variant["item_id"]))
            if variant_rules:
                variant["rules"] = list(variant_rules.values())

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
