"""Reusable rules-backed catalogs for simple reference domains."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.application_domains import application_domain
from infinity_db.domain_slugs import route_slug_from_typed_domain_id
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
                else self.rules_database.composed_records_by_kind(self.record_kind)
            )
        return self._records_cache

    def _slug(self, record: dict[str, Any]) -> str:
        return route_slug_from_typed_domain_id(
            record.get("id"),
            expected_domain=self.record_kind,
            context=f"curated {self.domain.singular_name.lower()} id",
        )

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
        return sorted(items, key=lambda item: (item["name"].casefold(), item["id"]))

    def get_item(self, slug: str) -> dict[str, Any] | None:
        """Return one current record with its composed rules relationships."""

        for record in self._records():
            record_slug = self._slug(record)
            if record_slug != slug:
                continue
            return {
                "id": record_slug,
                "slug": record_slug,
                "name": record["name"],
                "description": record["summary"],
                "rules": [deepcopy(record)],
            }
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
