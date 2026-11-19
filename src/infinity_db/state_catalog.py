"""Expose curated game States as a lightweight rules-backed catalog."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.domain_slugs import route_slug_from_typed_domain_id
from infinity_db.publication_registry import PublicationRegistry
from infinity_db.rules_database import RulesDatabase


def _record_slug(record: dict[str, Any]) -> str:
    return route_slug_from_typed_domain_id(
        record.get("id"), expected_domain="state", context="curated state id"
    )


def _route_slug(record: dict[str, Any]) -> str:
    return str(record.get("_routeSlug") or _record_slug(record))


class StateCatalog:
    """Expose current curated State definitions independently of Army source tables."""

    def __init__(
        self, rules_database: RulesDatabase | None,
        publication_registry: PublicationRegistry | None = None,
    ) -> None:
        self.rules_database = rules_database
        self.publication_registry = publication_registry
        self._records_cache: list[dict[str, Any]] | None = None

    def _records(self) -> list[dict[str, Any]]:
        if self._records_cache is None:
            records = (
                []
                if self.rules_database is None
                else self.rules_database.composed_records_by_kind("state")
            )
            if self.publication_registry is not None:
                core_slugs = {_record_slug(record) for record in records}
                known = set(core_slugs)

                def season_sort_key(entry: dict[str, Any]) -> tuple[int, str]:
                    number = entry["collection"].removeprefix("its-")
                    return (int(number) if number.isdecimal() else -1, entry["revision"])

                # Newest season owns the unqualified route. A historical
                # source-local State must keep its own independently cited card.
                for entry in sorted(
                    self.publication_registry.season_state_entries(),
                    key=season_sort_key, reverse=True,
                ):
                    record = deepcopy(entry["record"])
                    slug = _record_slug(record)
                    if slug in core_slugs:
                        raise ValueError(f"ITS State identity collides with a core State: {slug}")
                    route = slug if slug not in known else f"{entry['collection']}-{slug}"
                    if route in known:
                        raise ValueError(f"ITS State route collision: {route}")
                    known.add(route)
                    record["_routeSlug"] = route
                    record["citations"] = deepcopy(entry["citations"])
                    record["season"] = {
                        "collection": entry["collection"], "revision": entry["revision"],
                    }
                    records.append(record)
            self._records_cache = records
        return self._records_cache

    def list_states(self) -> list[dict[str, Any]]:
        """Return player-facing State identities available in the current rules DB."""
        items = [
            {
                "id": _route_slug(record),
                "slug": _route_slug(record),
                "name": record["name"],
                "description": record["summary"],
                **({"season": deepcopy(record["season"])}
                   if "season" in record else {}),
            }
            for record in self._records()
        ]
        return sorted(items, key=lambda item: (item["name"].casefold(), item["id"]))

    def get_state(self, state_slug: str) -> dict[str, Any] | None:
        """Return one current curated State with its bidirectional rule relations."""
        for record in self._records():
            slug = _route_slug(record)
            if slug != state_slug:
                continue
            published = deepcopy(record)
            published.pop("_routeSlug", None)
            return {
                "id": slug,
                "slug": slug,
                "name": record["name"],
                "description": record["summary"],
                "rules": [published],
                **({"season": deepcopy(record["season"])}
                   if "season" in record else {}),
            }
        return None
