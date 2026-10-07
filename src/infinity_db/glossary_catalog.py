"""Federate canonical rules concepts into the player-facing Glossary."""

from __future__ import annotations

from typing import Any

from infinity_db.application_domains import (
    APPLICATION_DOMAINS,
    application_domain,
    record_matches_domain,
)
from infinity_db.database.repository import Database, accent_insensitive_key
from infinity_db.domain_references import rule_record_public_reference
from infinity_db.rules_database import RulesDatabase


class GlossaryCatalog:
    """Expose canonical definitions without creating a second semantic owner."""

    def __init__(self, database: Database, rules_database: RulesDatabase | None) -> None:
        self.database = database
        self.rules_database = rules_database
        self._entries_cache: list[dict[str, Any]] | None = None

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

    def _record_entries(self) -> list[dict[str, Any]]:
        if self.rules_database is None:
            return []
        entries: list[dict[str, Any]] = []
        for domain in APPLICATION_DOMAINS:
            if not domain.published or not domain.glossary:
                continue
            for kind in domain.record_kinds:
                for record in self.rules_database.composed_records_by_kind(kind):
                    if not record_matches_domain(domain, record):
                        continue
                    if (record.get("variant_semantics") or {}).get("inheritance") == "source":
                        continue
                    reference = rule_record_public_reference(self.database, record)
                    href = self._href(reference)
                    if href is None:
                        # A route-backed concept without a valid public identity should not
                        # gain a parallel Glossary-only identity by accident.
                        continue
                    entries.append(
                        {
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
                    )
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

    def entries(self) -> list[dict[str, Any]]:
        """Return current canonical Glossary entries in stable display order."""

        if self._entries_cache is None:
            self._entries_cache = sorted(
                [
                    *self._record_entries(),
                    *self._profile_help_entries(),
                    *self._label_entries(),
                ],
                key=lambda item: (
                    accent_insensitive_key(item["name"]),
                    item["kind"],
                    item["id"],
                ),
            )
        return [dict(item, aliases=list(item["aliases"])) for item in self._entries_cache]

    def embedded_entries(self) -> list[dict[str, Any]]:
        """Return embedded concepts for global search without duplicating catalogs."""

        return [item for item in self.entries() if item["embedded"]]
