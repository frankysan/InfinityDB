"""Compose the public, cross-domain search index from existing read models."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import quote

from infinity_db.application_domains import application_domain
from infinity_db.database.repository import Database, accent_insensitive_key
from infinity_db.domain_references import public_slug_for_reference
from infinity_db.equipment_catalog import EquipmentCatalog
from infinity_db.glossary_catalog import GlossaryCatalog
from infinity_db.hacking_program_catalog import HackingProgramCatalog
from infinity_db.legacy_armies import LegacyArmy
from infinity_db.reference_catalog import LabelCatalog, RulesRecordCatalog
from infinity_db.skill_catalog import SkillCatalog
from infinity_db.state_catalog import StateCatalog
from infinity_db.trait_catalog import TraitCatalog

SearchEntry = tuple[dict[str, Any], tuple[str, ...]]


def normalized_terms(*labels: object) -> tuple[str, ...]:
    return tuple(sorted({key for label in labels if (key := accent_insensitive_key(label))}))


def rank_results(results: list[dict[str, Any]], needle: str) -> list[dict[str, Any]]:
    return sorted(
        results,
        key=lambda item: (
            0 if accent_insensitive_key(item["name"]).startswith(needle) else 1,
            item["name"].casefold(),
            item["domain"],
        ),
    )


class SearchCatalog:
    """Expose one player-facing result shape across all route-backed domains."""

    def __init__(
        self,
        database: Database,
        skill_catalog: SkillCatalog,
        equipment_catalog: EquipmentCatalog,
        trait_catalog: TraitCatalog,
        state_catalog: StateCatalog,
        hacking_program_catalog: HackingProgramCatalog,
        ammunition_catalog: RulesRecordCatalog,
        label_catalog: LabelCatalog,
        general_rules_catalog: RulesRecordCatalog,
        glossary_catalog: GlossaryCatalog,
        legacy_armies: tuple[LegacyArmy, ...] = (),
        *,
        published_search: Callable[[str], list[dict[str, Any]]] | None = None,
    ) -> None:
        self.database = database
        self.skill_catalog = skill_catalog
        self.equipment_catalog = equipment_catalog
        self.trait_catalog = trait_catalog
        self.state_catalog = state_catalog
        self.hacking_program_catalog = hacking_program_catalog
        self.ammunition_catalog = ammunition_catalog
        self.label_catalog = label_catalog
        self.general_rules_catalog = general_rules_catalog
        self.glossary_catalog = glossary_catalog
        self.legacy_armies = legacy_armies
        self.published_search = published_search

    @staticmethod
    def _result(domain: str, item: dict[str, Any], href: str) -> dict[str, Any]:
        return {"domain": domain, "name": str(item["name"]), "href": href}

    @staticmethod
    def _scoped_result(
        domain: str,
        item: dict[str, Any],
        href: str,
        schema: str,
        values: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "domain": domain,
            "name": str(item["name"]),
            "href": href,
            "share_state": {"schema": schema, "values": values},
        }

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return name/curated-alias matches across player-facing database domains."""
        if self.published_search is not None:
            return self.published_search(query)
        return self.search_composed(query)

    def search_composed(self, query: str) -> list[dict[str, Any]]:
        needle = accent_insensitive_key(query)
        if not needle:
            return []
        return rank_results([result for result, _terms in self.entries(query)], needle)

    def entries(self, query: str | None = None) -> Iterator[SearchEntry]:
        """Enumerate canonical search identities and normalized terms.

        A query keeps the legacy Unit listing selective. Without one, the
        complete public projection is suitable for offline publication.
        """
        needle = accent_insensitive_key(query)

        def matches(terms: tuple[str, ...]) -> bool:
            return not needle or any(needle in term for term in terms)

        for army in self.database.list_armies():
            terms = normalized_terms(army["name"])
            if not matches(terms):
                continue
            slug = public_slug_for_reference(self.database, "armies", army["id"])
            if slug is not None:
                yield self._scoped_result(
                    "Army", army, "/units", "units", {"army_id": slug}
                ), terms

        for army in self.legacy_armies:
            terms = normalized_terms(army.name)
            if matches(terms):
                yield self._result(
                    "Army",
                    {"name": army.name},
                    f"/armies#army-{quote(army.slug, safe='')}",
                ), terms

        units = self.database.list_units(
            search=query or "",
            limit=10_000,
            mercs=True,
            specops=True,
            teamops=True,
            reinforcement=True,
            _unbounded=True,
        )
        unit_terms = self.database.unit_search_terms()
        for unit in units["items"]:
            slug = public_slug_for_reference(self.database, "units", unit["id"])
            if slug is not None:
                yield (
                    self._result("Unit", unit, f"/units/{quote(slug, safe='')}"),
                    normalized_terms(*unit_terms[unit["id"]]),
                )

        catalog_sources = (
            ("Skill", "skills", self.skill_catalog.list_skills(filter_only=True)),
            ("Equipment", "equipment", self.equipment_catalog.list_equipment(filter_only=True)),
            ("Weapon", "weapons", self.database.list_catalog_filter_items("weapons")),
            ("Trait", "traits", self.trait_catalog.list_traits()),
            ("State", "states", self.state_catalog.list_states()),
            ("Hacking Program", "hacking-programs", self.hacking_program_catalog.list_programs()),
            (
                application_domain("ammunition").singular_name,
                "ammunition",
                self.ammunition_catalog.list_items(),
            ),
            (
                application_domain("labels").singular_name,
                "labels",
                self.label_catalog.list_items(),
            ),
            (
                application_domain("rules").singular_name,
                "rules",
                self.general_rules_catalog.list_items(),
            ),
        )
        for domain, route, items in catalog_sources:
            for item in items:
                labels = [item["name"], *item.get("aliases", []), *item.get("alternate_names", [])]
                terms = normalized_terms(*labels)
                if not matches(terms):
                    continue
                identifier = item.get("slug")
                if identifier is None and route in {"skills", "equipment", "weapons"}:
                    identifier = public_slug_for_reference(
                        self.database, route, item["id"]
                    )
                identifier = identifier or item["id"]
                display_item = (
                    {**item, "name": f"{item['name']} ({item['scenario']['name']})"}
                    if route == "skills" and item.get("scenario") else item
                )
                yield self._result(
                    domain, display_item, f"/{route}/{quote(str(identifier), safe='')}"
                ), terms

        for item in self.glossary_catalog.embedded_entries():
            labels = [item["name"], *item.get("aliases", [])]
            terms = normalized_terms(*labels)
            if not matches(terms):
                continue
            yield {
                "domain": item["domain"],
                "name": item["name"],
                "href": item["href"],
            }, terms

        for army in self.database.list_fireteam_armies():
            terms = normalized_terms(army["name"])
            if not matches(terms):
                continue
            slug = public_slug_for_reference(self.database, "armies", army["id"])
            if slug is not None:
                yield self._scoped_result(
                    "Fireteam chart", army, "/fireteams", "fireteams", {"army": slug}
                ), terms
