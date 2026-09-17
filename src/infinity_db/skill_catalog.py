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
        return items

    def get_skill(self, skill_id: int) -> dict[str, Any] | None:
        """Return one Army skill enriched with curated declarations and rules."""
        item = self.database.get_skill(skill_id)
        if item is None:
            return None
        result = deepcopy(item)
        source_ids = set(self.database.skill_source_ids(skill_id))
        if not source_ids:
            source_ids = {int(result["id"])}
        result["categories"] = self._categories_for_ids(source_ids)

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
