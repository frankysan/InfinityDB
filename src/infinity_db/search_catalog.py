"""Compose the public, cross-domain search index from existing read models."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from infinity_db.database.repository import Database, accent_insensitive_key
from infinity_db.domain_references import public_slug_for_reference
from infinity_db.equipment_catalog import EquipmentCatalog
from infinity_db.hacking_program_catalog import HackingProgramCatalog
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
    ) -> None:
        self.database = database
        self.skill_catalog = skill_catalog
        self.equipment_catalog = equipment_catalog
        self.trait_catalog = trait_catalog
        self.state_catalog = state_catalog
        self.hacking_program_catalog = hacking_program_catalog

    @staticmethod
    def _result(domain: str, item: dict[str, Any], href: str) -> dict[str, str]:
        return {"domain": domain, "name": str(item["name"]), "href": href}

    def search(self, query: str) -> list[dict[str, str]]:
        """Return name matches across every player-facing database domain.

        Search deliberately reuses the application read models instead of flattening
        source identifiers into a separate index. This keeps public slugs, rules-only
        identities, and the Army/Fireteam relationship boundary consistent with their
        detail surfaces.
        """

        needle = accent_insensitive_key(query)
        if not needle:
            return []

        results: list[dict[str, str]] = []
        for army in self.database.list_armies():
            if needle not in accent_insensitive_key(army["name"]):
                continue
            slug = public_slug_for_reference(self.database, "armies", army["id"])
            if slug is not None:
                results.append(
                    self._result("Army", army, f"/units?army_id={quote(slug, safe='')}")
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

        for army in self.database.list_fireteam_armies():
            if needle not in accent_insensitive_key(army["name"]):
                continue
            slug = public_slug_for_reference(self.database, "armies", army["id"])
            if slug is not None:
                results.append(
                    {
                        "domain": "Fireteam chart",
                        "name": army["name"],
                        "href": f"/fireteams?army={quote(slug, safe='')}",
                    }
                )

        return sorted(
            results,
            key=lambda item: (
                0 if accent_insensitive_key(item["name"]).startswith(needle) else 1,
                item["name"].casefold(),
                item["domain"],
            ),
        )
