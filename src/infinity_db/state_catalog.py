"""Expose curated game States as a lightweight rules-backed catalog."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.domain_slugs import route_slug_from_typed_domain_id
from infinity_db.rules_database import RulesDatabase


def _record_slug(record: dict[str, Any]) -> str:
    return route_slug_from_typed_domain_id(
        record.get("id"), expected_domain="state", context="curated state id"
    )


class StateCatalog:
    """Expose current curated State definitions independently of Army source tables."""

    def __init__(self, rules_database: RulesDatabase | None) -> None:
        self.rules_database = rules_database
        self._records_cache: list[dict[str, Any]] | None = None

    def _records(self) -> list[dict[str, Any]]:
        if self._records_cache is None:
            self._records_cache = (
                []
                if self.rules_database is None
                else self.rules_database.composed_records_by_kind("state")
            )
        return self._records_cache

    def list_states(self) -> list[dict[str, Any]]:
        """Return player-facing State identities available in the current rules DB."""
        items = [
            {
                "id": _record_slug(record),
                "slug": _record_slug(record),
                "name": record["name"],
                "description": record["summary"],
            }
            for record in self._records()
        ]
        return sorted(items, key=lambda item: (item["name"].casefold(), item["id"]))

    def get_state(self, state_slug: str) -> dict[str, Any] | None:
        """Return one current curated State with its bidirectional rule relations."""
        for record in self._records():
            slug = _record_slug(record)
            if slug != state_slug:
                continue
            return {
                "id": slug,
                "slug": slug,
                "name": record["name"],
                "description": record["summary"],
                "rules": [deepcopy(record)],
            }
        return None
