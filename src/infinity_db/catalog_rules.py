"""Compose Army catalog items with optional curated rules data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.rules_database import ArmyLinkRef, RulesDatabase

DECLARATION_KIND = "declaration-category"


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


def _source_label(category: dict[str, Any]) -> str | None:
    title = category.get("source_title")
    version = category.get("source_version")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(version, str) or not version.strip():
        return title
    if version.casefold() in title.casefold():
        return title
    return f"{title} v{version}"


class CatalogRules:
    """Enrich Army catalog items with curated rule records when available."""

    def __init__(self, rules_database: RulesDatabase | None) -> None:
        self.rules_database = rules_database
        self._category_indexes: dict[
            str, dict[ArmyLinkRef, list[dict[str, Any]]]
        ] = {}
        self._source_variant_indexes: dict[
            str, dict[ArmyLinkRef, dict[str, Any]]
        ] = {}

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

    def _category_index(self, entity: str) -> dict[ArmyLinkRef, list[dict[str, Any]]]:
        if entity in self._category_indexes:
            return self._category_indexes[entity]
        rules_database = self.rules_database
        if rules_database is None:
            self._category_indexes[entity] = {}
            return self._category_indexes[entity]
        index: dict[ArmyLinkRef, list[dict[str, Any]]] = {}
        for category in rules_database.declaration_categories(entity):
            index.setdefault(category["army_ref"], []).append(category)
        for categories in index.values():
            categories.sort(key=lambda item: (item["order"], item["name"], item["page"] or 0))
        self._category_indexes[entity] = index
        return index

    def _source_variant_index(
        self, entity: str
    ) -> dict[ArmyLinkRef, dict[str, Any]]:
        if entity in self._source_variant_indexes:
            return self._source_variant_indexes[entity]
        rules_database = self.rules_database
        if rules_database is None:
            self._source_variant_indexes[entity] = {}
            return self._source_variant_indexes[entity]
        self._source_variant_indexes[entity] = (
            rules_database.catalog_source_variant_semantics(entity)
        )
        return self._source_variant_indexes[entity]

    def _categories_for_refs(
        self, entity: str, refs: tuple[ArmyLinkRef, ...]
    ) -> list[dict[str, Any]]:
        categories: dict[tuple[str, str | None, int | None], tuple[int, dict[str, Any]]] = {}
        index = self._category_index(entity)
        for army_ref in refs:
            for category in index.get(army_ref, []):
                item = {
                    "name": category["name"],
                    "source": _source_label(category),
                    "page": category["page"],
                }
                key = (item["name"], item["source"], item["page"])
                categories.setdefault(key, (category["order"], item))
        return [
            item
            for _, item in sorted(
                categories.values(),
                key=lambda value: (
                    value[0],
                    value[1]["name"],
                    value[1]["page"] or 0,
                ),
            )
        ]

    def enrich_catalog_item(
        self, catalog: str, item: dict[str, Any]
    ) -> dict[str, Any]:
        """Add curated classifications, rules, and special profiles to one item."""
        result = deepcopy(item)
        rules_database = self.rules_database
        if rules_database is None:
            return result

        entities = {"equipment": "equipment", "weapons": "weapon"}
        entity = entities.get(catalog)
        if entity is None:
            return result

        application_refs = self._application_refs(result)
        source_ids = self._source_ids(result)
        if entity == "equipment":
            category_refs: tuple[ArmyLinkRef, ...] = (*source_ids, *application_refs)
            categories = self._categories_for_refs(entity, category_refs)
            if categories:
                result["categories"] = categories

        family_rules: dict[str, dict[str, Any]] = {}
        source_rules: dict[int, dict[str, dict[str, Any]]] = {}

        def collect_rules(army_ref: ArmyLinkRef, source_id: int | None) -> None:
            for record in rules_database.composed_records_for_army_link(
                entity, army_ref
            ):
                if record["kind"] == DECLARATION_KIND:
                    continue
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

        for source_id in source_ids:
            collect_rules(source_id, source_id)
        for army_ref in application_refs:
            if isinstance(army_ref, str):
                collect_rules(army_ref, None)

        records = list(family_rules.values())
        if records:
            result["rules"] = records
        source_variants = self._source_variant_index(entity)
        for variant in result.get("variants", []):
            source_id = int(variant["item_id"])
            source_variant = source_variants.get(source_id)
            if source_variant is not None:
                variant["source_variant"] = deepcopy(source_variant)
            variant_rules = source_rules.get(source_id)
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
