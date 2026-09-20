"""Compose raw Army skill usage with optional curated rules data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase

UNCLASSIFIED_CATEGORY = {"name": "Unclassified", "source": None, "page": None}
DECLARATION_KIND = "skill-declaration-category"


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


class SkillCatalog:
    """Enrich Army skills with curated declaration categories and rules."""

    def __init__(self, database: Database, rules_database: RulesDatabase | None) -> None:
        self.database = database
        self.rules_database = rules_database
        self._category_index: dict[int, list[dict[str, Any]]] | None = None
        self._parameter_index: dict[int, dict[str, str]] | None = None

    def _ensure_category_index(self) -> None:
        if self._category_index is not None:
            return
        if self.rules_database is None:
            self._category_index = {}
            return
        index: dict[int, list[dict[str, Any]]] = {}
        for category in self.rules_database.skill_declaration_categories():
            index.setdefault(category["skill_id"], []).append(category)
        for categories in index.values():
            categories.sort(key=lambda item: (item["order"], item["name"], item["page"]))
        self._category_index = index

    def _ensure_parameter_index(self) -> None:
        if self._parameter_index is not None:
            return
        self._parameter_index = (
            {}
            if self.rules_database is None
            else self.rules_database.skill_parameter_semantics()
        )

    def _parameter_semantics_for_ids(
        self, skill_ids: set[int]
    ) -> dict[str, str] | None:
        self._ensure_parameter_index()
        assert self._parameter_index is not None
        values = {
            tuple(sorted(semantics.items()))
            for skill_id in skill_ids
            if (semantics := self._parameter_index.get(skill_id)) is not None
        }
        if len(values) > 1:
            raise ValueError(
                f"Skill identity {sorted(skill_ids)} has conflicting parameter semantics"
            )
        if not values:
            return None
        return dict(next(iter(values)))

    def _attach_public_slug(self, item: dict[str, Any]) -> None:
        """Attach the additive public Skill slug when it cannot shadow a numeric route."""
        skill_id = item.get("id")
        if type(skill_id) is not int:
            return
        slug = self.database.application_slug("skills", skill_id)
        if slug is not None and not slug.isdigit():
            item["slug"] = slug

    def _enrich_skill_item(self, item: dict[str, Any]) -> None:
        skill_id = item.get("id")
        if type(skill_id) is not int:
            return
        self._attach_public_slug(item)
        semantics = self._parameter_semantics_for_ids({skill_id})
        if semantics is not None:
            item["parameter_semantics"] = semantics

    def _categories_for_ids(self, skill_ids: set[int]) -> list[dict[str, Any]]:
        self._ensure_category_index()
        assert self._category_index is not None
        categories: dict[tuple[str, str | None, int | None], tuple[int, dict[str, Any]]] = {}
        for skill_id in skill_ids:
            source_categories = self._category_index.get(skill_id, [])
            if not source_categories:
                item = dict(UNCLASSIFIED_CATEGORY)
                key = (item["name"], item["source"], item["page"])
                categories.setdefault(key, (10_000, item))
                continue
            for category in source_categories:
                item = {
                    "name": category["name"],
                    "source": _source_label(category),
                    "page": category["page"],
                }
                key = (item["name"], item["source"], item["page"])
                categories.setdefault(key, (category["order"], item))
        if not categories:
            return [dict(UNCLASSIFIED_CATEGORY)]
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

    def list_skills(self) -> list[dict[str, Any]]:
        """Return Army skills with curated declaration categories when available."""
        items = deepcopy(self.database.list_catalog_items("skills"))
        for item in items:
            item["categories"] = self._categories_for_ids({int(item["id"])})
            self._enrich_skill_item(item)
        return items

    def get_skill(self, skill_id: int) -> dict[str, Any] | None:
        """Return one Army skill enriched with curated declarations and rules."""
        item = self.database.get_skill(skill_id)
        if item is None:
            return None
        result = deepcopy(item)
        self._attach_public_slug(result)
        source_ids = set(self.database.skill_source_ids(skill_id))
        if not source_ids:
            source_ids = {int(result["id"])}
        result["categories"] = self._categories_for_ids(source_ids)
        semantics = self._parameter_semantics_for_ids(source_ids)
        if semantics is not None:
            result["parameter_semantics"] = semantics

        if self.rules_database is not None:
            rules: dict[str, dict[str, Any]] = {}
            for source_id in source_ids:
                for record in self.rules_database.records_for_army_link("skill", source_id):
                    if record["kind"] == DECLARATION_KIND:
                        continue
                    rules.setdefault(record["id"], record)
            if rules:
                result["rules"] = list(rules.values())
        return result

    def list_skill_extras(self) -> list[dict[str, Any]]:
        """Return source-typed distance extras with optional curated display semantics."""
        items = deepcopy(self.database.list_skill_extras())
        for item in items:
            semantics = self._parameter_semantics_for_ids({int(item["skill_id"])})
            if semantics is not None:
                item["parameter_semantics"] = semantics
        return items

    def enrich_unit(self, unit: dict[str, Any]) -> dict[str, Any]:
        """Attach curated parameter semantics to skill occurrences in a unit payload."""
        result = deepcopy(unit)

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "skills" and isinstance(child, list):
                        for item in child:
                            if isinstance(item, dict):
                                self._enrich_skill_item(item)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(result)
        return result
