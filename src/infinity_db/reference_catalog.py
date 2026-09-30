"""Reusable rules-backed catalogs for simple reference domains."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.application_domains import (
    APPLICATION_DOMAINS,
    application_domain,
    record_matches_domain,
)
from infinity_db.domain_references import rule_record_public_reference
from infinity_db.domain_slugs import (
    route_slug_from_qualified_typed_domain_id,
    route_slug_from_typed_domain_id,
)
from infinity_db.rules_database import RulesDatabase


class RulesRecordCatalog:
    """Expose one simple curated rules-record kind as a public catalog."""

    def __init__(self, rules_database: RulesDatabase | None, domain_slug: str) -> None:
        domain = application_domain(domain_slug)
        if not domain.catalog or not domain.detail or len(domain.record_kinds) != 1:
            raise ValueError(
                f"Application domain {domain_slug!r} is not a simple rules-record catalog"
            )
        self.rules_database = rules_database
        self.domain = domain
        self.record_kind = domain.record_kinds[0]
        self._records_cache: list[dict[str, Any]] | None = None

    def _records(self) -> list[dict[str, Any]]:
        if self._records_cache is None:
            self._records_cache = (
                []
                if self.rules_database is None
                else [
                    record
                    for record in self.rules_database.composed_records_by_kind(self.record_kind)
                    if record_matches_domain(self.domain, record)
                ]
            )
        return self._records_cache

    def _slug(self, record: dict[str, Any]) -> str:
        slugger = (
            route_slug_from_qualified_typed_domain_id
            if self.domain.record_categories
            else route_slug_from_typed_domain_id
        )
        return slugger(
            record.get("id"),
            expected_domain=self.record_kind,
            context=f"curated {self.domain.singular_name.lower()} id",
        )

    def _related_category_peers(
        self, category: str, *, exclude_id: str
    ) -> list[dict[str, Any]]:
        if self.rules_database is None:
            return []
        peers = []
        seen: set[tuple[str, str]] = set()
        for domain in APPLICATION_DOMAINS:
            if not domain.published or not domain.detail:
                continue
            for kind in domain.record_kinds:
                for candidate in self.rules_database.composed_records_by_kind(kind):
                    if not record_matches_domain(domain, candidate):
                        continue
                    if candidate.get("id") == exclude_id:
                        continue
                    facts = candidate.get("facts")
                    related_categories = (
                        facts.get("relatedCategories", [])
                        if isinstance(facts, dict)
                        else []
                    )
                    if category not in related_categories:
                        continue
                    if (candidate.get("variant_semantics") or {}).get("inheritance") == "source":
                        continue
                    reference = rule_record_public_reference(None, candidate)
                    if reference is None:
                        continue
                    key = (str(candidate["id"]), domain.slug)
                    if key in seen:
                        continue
                    seen.add(key)
                    peers.append(
                        {
                            "id": candidate["id"],
                            "name": candidate["name"],
                            "domain": domain.singular_name,
                            "public_reference": reference,
                        }
                    )
        return sorted(peers, key=lambda peer: (peer["name"].casefold(), peer["id"]))

    def list_items(self) -> list[dict[str, Any]]:
        """Return the current player-facing identities in stable display order."""

        items = [
            {
                "id": self._slug(record),
                "slug": self._slug(record),
                "name": record["name"],
                "description": record["summary"],
            }
            for record in self._records()
        ]
        slugs = [item["slug"] for item in items]
        if len(slugs) != len(set(slugs)):
            raise ValueError(
                f"{self.domain.plural_name} contains colliding public route slugs"
            )
        return sorted(items, key=lambda item: (item["name"].casefold(), item["id"]))

    def get_item(self, slug: str) -> dict[str, Any] | None:
        """Return one current record with its composed rules relationships."""

        for record in self._records():
            record_slug = self._slug(record)
            if record_slug != slug:
                continue
            item = {
                "id": record_slug,
                "slug": record_slug,
                "name": record["name"],
                "description": record["summary"],
                "rules": [deepcopy(record)],
            }
            facts = record.get("facts")
            category = facts.get("category") if isinstance(facts, dict) else None
            if self.domain.record_categories and isinstance(category, str):
                item["category"] = category
                peers = []
                for candidate in self._records():
                    candidate_facts = candidate.get("facts")
                    candidate_category = (
                        candidate_facts.get("category")
                        if isinstance(candidate_facts, dict)
                        else None
                    )
                    if candidate["id"] == record["id"] or candidate_category != category:
                        continue
                    candidate_slug = self._slug(candidate)
                    peers.append(
                        {
                            "id": candidate_slug,
                            "slug": candidate_slug,
                            "name": candidate["name"],
                        }
                    )
                if peers:
                    item["category_peers"] = sorted(
                        peers, key=lambda peer: (peer["name"].casefold(), peer["id"])
                    )
                related_peers = self._related_category_peers(
                    category, exclude_id=str(record["id"])
                )
                if related_peers:
                    item["related_category_peers"] = related_peers
            return item
        return None


class LabelCatalog:
    """Expose the canonical current rules Label vocabulary as a public catalog."""

    def __init__(self, rules_database: RulesDatabase | None) -> None:
        self.rules_database = rules_database
        self._labels_cache: list[dict[str, Any]] | None = None

    def _labels(self) -> list[dict[str, Any]]:
        if self._labels_cache is not None:
            return self._labels_cache
        if self.rules_database is None:
            self._labels_cache = []
            return self._labels_cache

        labels: dict[str, dict[str, Any]] = {}
        for label in self.rules_database.current_labels():
            label_id = str(label["id"])
            existing = labels.get(label_id)
            if existing is not None:
                if (existing["name"], existing["description"]) != (
                    label["name"],
                    label["description"],
                ):
                    raise ValueError(
                        f"Current Label {label_id!r} has conflicting definitions"
                    )
                continue
            labels[label_id] = label
        self._labels_cache = sorted(
            labels.values(), key=lambda item: (str(item["name"]).casefold(), str(item["id"]))
        )
        return self._labels_cache

    def list_items(self) -> list[dict[str, Any]]:
        """Return the canonical current Label vocabulary."""

        return [
            {
                "id": label["id"],
                "slug": label["id"],
                "name": label["name"],
                "description": label["description"],
            }
            for label in self._labels()
        ]

    def get_item(self, slug: str) -> dict[str, Any] | None:
        """Return one canonical current Label definition."""

        for label in self._labels():
            if label["id"] != slug:
                continue
            return {
                "id": label["id"],
                "slug": label["id"],
                "name": label["name"],
                "description": label["description"],
                "collection": deepcopy(label["collection"]),
            }
        return None
