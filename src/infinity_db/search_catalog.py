"""Compose the public, cross-domain search index from existing read models."""

from __future__ import annotations

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
        """Return name matches across every player-facing database domain.

        Search deliberately reuses the application read models instead of flattening
        source identifiers into a separate index. This keeps public slugs, rules-only
        identities, and the Army/Fireteam relationship boundary consistent with their
        detail surfaces.
        """

        needle = accent_insensitive_key(query)
        if not needle:
            return []

        results: list[dict[str, Any]] = []
        for army in self.database.list_armies():
            if needle not in accent_insensitive_key(army["name"]):
                continue
            slug = public_slug_for_reference(self.database, "armies", army["id"])
            if slug is not None:
                results.append(
                    self._scoped_result(
                        "Army", army, "/units", "units", {"army_id": slug}
                    )
                )

        for army in self.legacy_armies:
            if needle not in accent_insensitive_key(army.name):
                continue
            results.append(
                self._result(
                    "Army",
                    {"name": army.name},
                    f"/armies#army-{quote(army.slug, safe='')}",
                )
            )

        units = self.database.list_units(
            search=query,
            limit=10_000,
            mercs=True,
            specops=True,
            teamops=True,
            reinforcement=True,
            _unbounded=True,
        )
        for unit in units["items"]:
            slug = public_slug_for_reference(self.database, "units", unit["id"])
            if slug is not None:
                results.append(self._result("Unit", unit, f"/units/{quote(slug, safe='')}"))

        catalog_sources = (
            ("Skill", "skills", self.skill_catalog.list_skills()),
            ("Equipment", "equipment", self.equipment_catalog.list_equipment()),
            ("Weapon", "weapons", self.database.list_catalog_items("weapons")),
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
                if needle not in accent_insensitive_key(item["name"]):
                    continue
                identifier = item.get("slug")
                if identifier is None and route in {"skills", "equipment", "weapons"}:
                    identifier = public_slug_for_reference(
                        self.database, route, item["id"]
                    )
                identifier = identifier or item["id"]
                results.append(
                    self._result(domain, item, f"/{route}/{quote(str(identifier), safe='')}")
                )

        for item in self.glossary_catalog.embedded_entries():
            labels = [item["name"], *item.get("aliases", [])]
            if not any(needle in accent_insensitive_key(label) for label in labels):
                continue
            results.append(
                {
                    "domain": item["domain"],
                    "name": item["name"],
                    "href": item["href"],
                }
            )

        for army in self.database.list_fireteam_armies():
            if needle not in accent_insensitive_key(army["name"]):
                continue
            slug = public_slug_for_reference(self.database, "armies", army["id"])
            if slug is not None:
                results.append(
                    self._scoped_result(
                        "Fireteam chart", army, "/fireteams", "fireteams", {"army": slug}
                    )
                )

        return sorted(
            results,
            key=lambda item: (
                0 if accent_insensitive_key(item["name"]).startswith(needle) else 1,
                item["name"].casefold(),
                item["domain"],
            ),
        )
