"""Federate canonical rules concepts into the player-facing Glossary."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.application_domains import (
    APPLICATION_DOMAINS,
    application_domain,
    record_matches_domain,
)
from infinity_db.database.repository import Database, accent_insensitive_key
from infinity_db.domain_references import rule_record_public_reference
from infinity_db.domain_slugs import normalize_domain_slug
from infinity_db.equipment_catalog import EquipmentCatalog
from infinity_db.fireteam_reference import GENERAL_FIRETEAM_RULE_ID
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_properties import WeaponProperties


class GlossaryCatalog:
    """Expose canonical definitions without creating a second semantic owner."""

    def __init__(self, database: Database, rules_database: RulesDatabase | None) -> None:
        self.database = database
        self.rules_database = rules_database
        self._entries_cache: list[dict[str, Any]] | None = None
        self._embedded_entries_cache: list[dict[str, Any]] | None = None
        self._weapon_properties = (
            WeaponProperties(rules_database, database=database)
            if rules_database is not None else None
        )

    @staticmethod
    def _href(reference: dict[str, str] | None) -> str | None:
        if reference is None:
            return None
        if href := reference.get("href"):
            return href
        catalog = reference.get("catalog")
        identifier = reference.get("id")
        if not catalog or not identifier:
            return None
        return f"/{catalog}/{identifier}"

    def _record_entries(
        self, *, domain_slug: str | None = None, embedded_only: bool = False,
    ) -> list[dict[str, Any]]:
        if self.rules_database is None:
            return []
        entries: list[dict[str, Any]] = []
        equipment_slugs = (
            frozenset(
                item["slug"]
                for item in EquipmentCatalog(
                    self.database, self.rules_database,
                ).list_equipment(filter_only=True)
                if isinstance(item.get("slug"), str)
            )
            if not embedded_only and domain_slug in (None, "equipment") else frozenset()
        )
        for domain in APPLICATION_DOMAINS:
            if not domain.published or not domain.glossary:
                continue
            if domain_slug is not None and domain.slug != domain_slug:
                continue
            if embedded_only and domain.level != "embedded":
                continue
            for kind in domain.record_kinds:
                for record in self.rules_database.composed_records_by_kind(
                    kind, include_army_links=(kind in {"equipment", "weapon"})
                ):
                    if not record_matches_domain(domain, record):
                        continue
                    if (record.get("variant_semantics") or {}).get("inheritance") == "source":
                        continue
                    reference = rule_record_public_reference(
                        self.database,
                        record,
                        validate_army_links=(kind == "equipment"),
                        additional_route_slugs=(
                            equipment_slugs if kind == "equipment" else frozenset()
                        ),
                    )
                    href = self._href(reference)
                    if href is None:
                        # A route-backed concept without a valid public identity should not
                        # gain a parallel Glossary-only identity by accident.
                        continue
                    entry = {
                        "id": record["id"],
                        "kind": kind,
                        "domain": domain.singular_name,
                        "domain_slug": domain.slug,
                        "name": record["name"],
                        "description": record["summary"],
                        "aliases": list(record.get("aliases", [])),
                        "href": href,
                        "embedded": domain.level == "embedded",
                    }
                    if entry["embedded"]:
                        entry["citations"] = record["citations"]
                    entries.append(entry)
        return entries

    def _fireteam_terminology_entries(self) -> list[dict[str, Any]]:
        """Project the existing curated Fireteam terminology without copying definitions."""
        if self.rules_database is None:
            return []
        general = self.rules_database.composed_record(GENERAL_FIRETEAM_RULE_ID)
        if general is None:
            return []
        entries = []
        for term in general["facts"].get("terminology", []):
            slug = normalize_domain_slug(term["term"])
            provenance = term["provenance"]
            label = (
                "Historical official terminology" if provenance == "historical-official"
                else "Community / historical shorthand"
            )
            entries.append({
                "id": f"fireteam-term:{slug}",
                "kind": "fireteam-term",
                "domain": "Game term",
                "domain_slug": "terms",
                "name": term["term"],
                "description": f"{label}. {term['meaning']} "
                               "See [[rule:fireteam-general|Fireteam rules]].",
                "aliases": [],
                "href": f"/glossary#fireteam-term-{slug}",
                "embedded": True,
                "citations": general["citations"],
                "provenance": provenance,
            })
        return entries

    def _profile_help_entries(self) -> list[dict[str, Any]]:
        if self.rules_database is None:
            return []

        aliases_by_key = {
            "unit-profile": ["Unit Profile"],
            "attributes": [],
            "training-orders": ["Training", "Orders"],
            "troop-type": ["Type"],
            "classification": ["Classification"],
            "isc": [],
            "hackable": [],
            "peripheral": ["Peripherals", "Controller access"],
            "skills": ["Skill"],
            "equipment": [],
            "weapons": ["Weapon"],
            "profile-options": ["Profiles", "Loadouts"],
        }
        entries: list[dict[str, Any]] = []
        for item in self.rules_database.unit_profile_help():
            identifier = str(item["id"])
            entries.append(
                {
                    "id": identifier,
                    "kind": "rule",
                    "domain": "Unit Profile",
                    "domain_slug": "rules",
                    "name": item["name"],
                    "description": item["summary"],
                    "aliases": aliases_by_key.get(str(item["key"]), []),
                    "href": f"/glossary#{identifier.replace(':', '-')}",
                    "embedded": True,
                    "citations": item["citations"],
                }
            )
        return entries

    def _label_entries(self) -> list[dict[str, Any]]:
        if self.rules_database is None:
            return []
        domain = application_domain("labels")
        # Labels are stored in the canonical Label vocabulary rather than records.
        entries: list[dict[str, Any]] = []
        labels: dict[str, dict[str, Any]] = {}
        for label in self.rules_database.current_labels():
            identifier = str(label["id"])
            existing = labels.get(identifier)
            if existing is not None:
                if (existing["name"], existing["description"]) != (
                    label["name"],
                    label["description"],
                ):
                    raise ValueError(
                        f"Current Label {identifier!r} has conflicting definitions"
                    )
                continue
            labels[identifier] = label

        for identifier, label in labels.items():
            entries.append(
                {
                    "id": f"label:{identifier}",
                    "kind": "label",
                    "domain": domain.singular_name,
                    "domain_slug": domain.slug,
                    "name": label["name"],
                    "description": label["description"],
                    "aliases": [],
                    "href": f"/labels/{identifier}",
                    "embedded": False,
                }
            )
        return entries

    def _weapon_property_entries(self) -> list[dict[str, Any]]:
        if self._weapon_properties is None:
            return []
        return [
            {
                "id": item["id"], "kind": "weapon-property",
                "domain": "Weapon Property",
                "domain_slug": "weapon-properties",
                "name": item["name"],
                "description": item["summary"],
                "origins": item["origins"],
                "aliases": [], "embedded": True,
                "href": item["public_reference"]["href"],
            }
            for item in self._weapon_properties.entries()
        ]

    def entries(self) -> list[dict[str, Any]]:
        """Return current canonical Glossary entries in stable display order."""

        projection = self.database.catalog_projection
        if (projection is not None and self.rules_database is not None
                and projection.path == self.rules_database.path):
            published = projection.reference_page("glossary")
            if published is not None:
                return published
        if self._entries_cache is None:
            self._entries_cache = sorted(
                [
                    *self._record_entries(),
                    *self._profile_help_entries(),
                    *self._fireteam_terminology_entries(),
                    *self._label_entries(),
                    *self._weapon_property_entries(),
                ],
                key=lambda item: (
                    accent_insensitive_key(item["name"]),
                    item["kind"],
                    item["id"],
                ),
            )
        return self._detached_entries(self._entries_cache)

    @staticmethod
    def _detached_entries(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        entries = []
        for item in items:
            entry = dict(item, aliases=list(item["aliases"]))
            if "citations" in item:
                entry["citations"] = deepcopy(item["citations"])
            entries.append(entry)
        return entries

    def attribute_entries(self) -> list[dict[str, Any]]:
        """Return canonical Attribute entries without constructing other Glossary domains."""
        return sorted(
            self._record_entries(domain_slug="attributes"),
            key=lambda item: (accent_insensitive_key(item["name"]), item["kind"], item["id"]),
        )

    def embedded_entries(self) -> list[dict[str, Any]]:
        """Return embedded concepts for global search without duplicating catalogs."""

        if self._entries_cache is not None:
            return self._detached_entries(
                [item for item in self._entries_cache if item["embedded"]]
            )
        if self._embedded_entries_cache is None:
            self._embedded_entries_cache = sorted(
                [
                    *self._record_entries(embedded_only=True),
                    *self._profile_help_entries(),
                    *self._fireteam_terminology_entries(),
                    *self._weapon_property_entries(),
                ],
                key=lambda item: (
                    accent_insensitive_key(item["name"]), item["kind"], item["id"],
                ),
            )
        return self._detached_entries(self._embedded_entries_cache)
