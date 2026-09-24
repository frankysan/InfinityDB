"""Compose raw Army skill usage with optional curated rules data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.catalog_slugs import attach_public_catalog_slug
from infinity_db.database.repository import Database
from infinity_db.domain_references import public_slug_for_reference
from infinity_db.rules_database import ArmyLinkRef, RulesDatabase
from infinity_db.skill_config import load_skill_source_config

UNCLASSIFIED_CATEGORY = {"name": "Unclassified", "source": None, "page": None}
DECLARATION_KIND = "declaration-category"
COMMON_SKILL_CATEGORY = "Common Skills"
SPECIAL_SKILL_CATEGORY = "Special Skills"


def _skill_category(record: dict[str, Any] | None) -> str:
    """Return the player-facing source category for a Skill record."""
    category = (record or {}).get("facts", {}).get("category")
    return COMMON_SKILL_CATEGORY if category == "common-skill" else SPECIAL_SKILL_CATEGORY


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
        self._category_index: dict[ArmyLinkRef, list[dict[str, Any]]] | None = None
        self._skill_record_category_index: (
            dict[ArmyLinkRef, list[dict[str, Any]]] | None
        ) = None
        self._parameter_index: dict[ArmyLinkRef, dict[str, str]] | None = None
        self._source_variant_index: dict[ArmyLinkRef, dict[str, Any]] | None = None
        self._training_index: dict[str, dict[str, Any]] | None = None
        self._excluded_rules_catalog_ids: set[int] | None = None

    def _rules_catalog_excluded_source_ids(self) -> set[int]:
        """Return Army skill-like application identities excluded from rules Skills."""
        if self._excluded_rules_catalog_ids is not None:
            return self._excluded_rules_catalog_ids
        excluded: set[int] = set()
        if self.rules_database is not None:
            for classification in load_skill_source_config():
                application_id = self.database.application_catalog_id(
                    "skills", classification.skill_ref
                )
                if application_id is not None:
                    excluded.add(application_id)
        self._excluded_rules_catalog_ids = excluded
        return excluded

    def _ensure_category_index(self) -> None:
        if self._category_index is not None:
            return
        if self.rules_database is None:
            self._category_index = {}
            return
        index: dict[ArmyLinkRef, list[dict[str, Any]]] = {}
        for category in self.rules_database.declaration_categories("skill"):
            index.setdefault(category["army_ref"], []).append(category)
        for categories in index.values():
            categories.sort(key=lambda item: (item["order"], item["name"], item["page"]))
        self._category_index = index

    @staticmethod
    def _categories_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
        skill_types = record.get("skill_types")
        if not isinstance(skill_types, list) or not skill_types:
            return []
        citations = record.get("citations") or []
        citation = next(
            (item for item in citations if item.get("page") is not None),
            citations[0] if citations else {},
        )
        source = _source_label(citation) if citation else None
        page = citation.get("page") if citation else None
        return [
            {
                "name": skill_type.get("category_name", skill_type["name"]),
                "source": source,
                "page": page,
            }
            for skill_type in skill_types
        ]

    def _ensure_skill_record_category_index(self) -> None:
        if self._skill_record_category_index is not None:
            return
        if self.rules_database is None:
            self._skill_record_category_index = {}
            return
        index: dict[ArmyLinkRef, list[dict[str, Any]]] = {}
        for category in self.rules_database.skill_definition_categories():
            index.setdefault(category["skill_ref"], []).append(category)
        for categories in index.values():
            categories.sort(key=lambda item: item["order"])
        self._skill_record_category_index = index

    def _record_categories_for_ids(
        self, skill_ids: set[int]
    ) -> list[dict[str, Any]] | None:
        self._ensure_skill_record_category_index()
        assert self._skill_record_category_index is not None
        candidates: list[list[dict[str, Any]]] = []
        for skill_ref in sorted(
            self._army_refs_for_ids(skill_ids),
            key=lambda value: (0 if isinstance(value, int) else 1, str(value)),
        ):
            categories = self._skill_record_category_index.get(skill_ref)
            if categories:
                candidates.append(categories)
        if not candidates:
            return None
        category_sets = {
            tuple(category["type_id"] for category in categories)
            for categories in candidates
        }
        if len(category_sets) > 1:
            raise ValueError(
                f"Skill identity {sorted(skill_ids)} has conflicting curated categories"
            )
        chosen = candidates[0]

        return [
            {
                "name": category["name"],
                "source": _source_label(category),
                "page": category["page"],
            }
            for category in chosen
        ]

    def _ensure_parameter_index(self) -> None:
        if self._parameter_index is not None:
            return
        self._parameter_index = (
            {}
            if self.rules_database is None
            else self.rules_database.skill_parameter_semantics()
        )

    def _ensure_source_variant_index(self) -> None:
        if self._source_variant_index is not None:
            return
        self._source_variant_index = (
            {}
            if self.rules_database is None
            else self.rules_database.catalog_source_variant_semantics("skill")
        )

    def _source_variant_semantics(self, skill_id: int) -> dict[str, Any] | None:
        self._ensure_source_variant_index()
        assert self._source_variant_index is not None
        semantics = self._source_variant_index.get(skill_id)
        return deepcopy(semantics) if semantics is not None else None

    def _army_refs_for_ids(self, skill_ids: set[int]) -> set[ArmyLinkRef]:
        refs: set[ArmyLinkRef] = set(skill_ids)
        for skill_id in skill_ids:
            application_id = self.database.application_catalog_id("skills", skill_id)
            if application_id is None:
                continue
            refs.update(self.database.skill_source_ids(application_id))
            slug = self.database.application_slug("skills", application_id)
            if slug is not None:
                refs.add(slug)
        return refs

    def _parameter_semantics_for_ids(
        self, skill_ids: set[int]
    ) -> dict[str, str] | None:
        self._ensure_parameter_index()
        assert self._parameter_index is not None
        values = {
            tuple(sorted(semantics.items()))
            for skill_ref in self._army_refs_for_ids(skill_ids)
            if (semantics := self._parameter_index.get(skill_ref)) is not None
        }
        if len(values) > 1:
            raise ValueError(
                f"Skill identity {sorted(skill_ids)} has conflicting parameter semantics"
            )
        if not values:
            return None
        return dict(next(iter(values)))

    def _attach_public_slug(self, item: dict[str, Any]) -> None:
        """Attach the additive public Skill slug when available."""
        attach_public_catalog_slug(self.database, "skills", item)

    def _enrich_skill_item(self, item: dict[str, Any]) -> None:
        skill_id = item.get("id")
        if type(skill_id) is not int:
            return
        self._attach_public_slug(item)
        semantics = self._parameter_semantics_for_ids({skill_id})
        if semantics is not None:
            item["parameter_semantics"] = semantics
        source_variant = self._source_variant_semantics(skill_id)
        if source_variant is not None:
            item["source_variant"] = source_variant

    def _categories_for_ids(self, skill_ids: set[int]) -> list[dict[str, Any]]:
        record_categories = self._record_categories_for_ids(skill_ids)
        if record_categories is not None:
            return record_categories
        self._ensure_category_index()
        assert self._category_index is not None
        categories: dict[tuple[str, str | None, int | None], tuple[int, dict[str, Any]]] = {}
        for skill_ref in self._army_refs_for_ids(skill_ids):
            for category in self._category_index.get(skill_ref, []):
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
        """Return rules-domain Skills plus unresolved Army Skill identities."""
        excluded = self._rules_catalog_excluded_source_ids()
        items = [
            item
            for item in deepcopy(self.database.list_catalog_items("skills"))
            if int(item["id"]) not in excluded
        ]
        definition_records: list[dict[str, Any]] = []
        if self.rules_database is not None:
            for record in self.rules_database.composed_records_by_kind("skill"):
                if (record.get("variant_semantics") or {}).get("inheritance") == "source":
                    continue
                if record.get("facts", {}).get("category") not in {
                    "common-skill",
                    "special-skill",
                }:
                    continue
                definition_records.append(record)
        definitions_by_ref: dict[ArmyLinkRef, dict[str, Any]] = {}
        for record in definition_records:
            for link in record.get("army_links", []):
                if link.get("entity") == "skill" and "id" in link:
                    definitions_by_ref[link["id"]] = record
        definitions_by_slug = {
            record["id"].removeprefix("skill:"): record for record in definition_records
        }
        definitions_by_name = {
            " ".join(record["name"].split()).casefold(): record
            for record in definition_records
        }
        represented_definition_ids: set[str] = set()
        for item in items:
            item["categories"] = self._categories_for_ids({int(item["id"])})
            self._enrich_skill_item(item)
            record = next(
                (
                    definitions_by_ref[reference]
                    for reference in self._army_refs_for_ids({int(item["id"])})
                    if reference in definitions_by_ref
                ),
                None,
            )
            if record is None:
                record = definitions_by_slug.get(str(item.get("slug", "")))
            if record is None:
                normalized_name = " ".join(str(item.get("name", "")).split()).casefold()
                record = definitions_by_name.get(normalized_name)
            if record is not None:
                represented_definition_ids.add(record["id"])
            item["category"] = _skill_category(record)
        for record in definition_records:
            if record["id"] in represented_definition_ids:
                continue
            semantic_id = record["id"].removeprefix("skill:")
            items.append(
                {
                    "id": semantic_id,
                    "slug": semantic_id,
                    "name": record["name"],
                    "use_count": 0,
                    "category": _skill_category(record),
                    "categories": self._categories_for_record(record),
                }
            )
        return items

    def get_skill(self, skill_ref: int | str) -> dict[str, Any] | None:
        """Return one Army Skill reference enriched with curated declarations and rules."""
        item = self.database.get_skill(skill_ref)
        if (
            item is not None
            and self.rules_database is not None
            and int(item["id"]) in self._rules_catalog_excluded_source_ids()
        ):
            return None
        if item is None:
            if not isinstance(skill_ref, str) or self.rules_database is None:
                return None
            record_id = f"skill:{skill_ref}"
            item = next(
                (
                    {
                        "id": skill_ref,
                        "slug": skill_ref,
                        "name": record["name"],
                        "use_count": 0,
                        "category": _skill_category(record),
                        "categories": self._categories_for_record(record),
                        "rules": [record],
                        "variants": [],
                    }
                    for record in self.rules_database.composed_records_by_kind("skill")
                    if record["id"] == record_id
                    and record.get("facts", {}).get("category")
                    in {"common-skill", "special-skill"}
                    and (record.get("variant_semantics") or {}).get("inheritance")
                    != "source"
                ),
                None,
            )
            return item
        result = deepcopy(item)
        self._attach_public_slug(result)
        source_ids = set(self.database.skill_source_ids(int(result["id"])))
        if not source_ids:
            source_ids = {int(result["id"])}
        result["categories"] = self._categories_for_ids(source_ids)
        semantics = self._parameter_semantics_for_ids(source_ids)
        if semantics is not None:
            result["parameter_semantics"] = semantics

        rules_database = self.rules_database
        if rules_database is not None:
            family_rules: dict[str, dict[str, Any]] = {}
            source_rules: dict[int, dict[str, dict[str, Any]]] = {}

            def collect_rules(army_ref: ArmyLinkRef, source_id: int | None) -> None:
                for record in rules_database.composed_records_for_army_link(
                    "skill", army_ref
                ):
                    if record["kind"] == DECLARATION_KIND:
                        continue
                    inheritance = (record.get("variant_semantics") or {}).get(
                        "inheritance"
                    )
                    if inheritance == "source":
                        if source_id is None:
                            raise ValueError(
                                f"Source-specific Skill rule {record['id']!r} must be "
                                "linked by numeric source id"
                            )
                        source_rules.setdefault(source_id, {}).setdefault(
                            record["id"], record
                        )
                    else:
                        family_rules.setdefault(record["id"], record)

            for source_id in sorted(source_ids):
                collect_rules(source_id, source_id)
            application_slug = self.database.application_slug(
                "skills", int(result["id"])
            )
            if application_slug is not None:
                collect_rules(application_slug, None)

            # Common Skills are canonical rules identities even where the Army
            # snapshot supplies only a same-named source occurrence.  Match the
            # list view's category composition so numeric detail routes expose
            # that rules definition as well.
            common_rule = next(
                (
                    record
                    for record in rules_database.composed_records_by_kind("skill")
                    if record.get("facts", {}).get("category") == "common-skill"
                    and (record.get("variant_semantics") or {}).get("inheritance")
                    != "source"
                    and record["name"].casefold()
                    == str(result.get("name", "")).casefold()
                ),
                None,
            )
            if common_rule is not None:
                family_rules.setdefault(common_rule["id"], common_rule)

            if family_rules:
                result["rules"] = list(family_rules.values())
            for variant in result.get("variants", []):
                skill_id = int(variant["skill_id"])
                source_variant = self._source_variant_semantics(skill_id)
                if source_variant is not None:
                    variant["source_variant"] = source_variant
                variant_rules = source_rules.get(skill_id)
                if variant_rules:
                    variant["rules"] = list(variant_rules.values())
        return result

    def list_skill_extras(self) -> list[dict[str, Any]]:
        """Return source-typed distance extras with optional curated display semantics."""
        items = deepcopy(self.database.list_skill_extras())
        for item in items:
            skill_id = int(item["skill_id"])
            slug = public_slug_for_reference(self.database, "skills", skill_id)
            if slug is not None:
                item["skill_slug"] = slug
            semantics = self._parameter_semantics_for_ids({skill_id})
            if semantics is not None:
                item["parameter_semantics"] = semantics
        return items

    def enrich_unit(self, unit: dict[str, Any]) -> dict[str, Any]:
        """Annotate source-backed Skill and Order occurrences with curated context."""
        result = deepcopy(unit)
        training_index = self._training_index
        if training_index is None:
            training_index = (
                self.rules_database.training_by_order_type()
                if self.rules_database is not None
                else {}
            )
            self._training_index = training_index

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "skills" and isinstance(child, list):
                        for item in child:
                            if isinstance(item, dict):
                                self._enrich_skill_item(item)
                    if key == "orders" and isinstance(child, list):
                        for order in child:
                            if isinstance(order, dict):
                                order_type = order.get("type")
                                if isinstance(order_type, str) and order_type in training_index:
                                    order["training_reference"] = deepcopy(
                                        training_index[order_type]
                                    )
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(result)
        return result
