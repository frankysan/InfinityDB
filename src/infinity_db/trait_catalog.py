"""Compose raw Army trait usage with curated trait rules references."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.domain_slugs import route_slug_from_typed_domain_id
from infinity_db.rules_database import RulesDatabase


def _record_slug(record: dict[str, Any]) -> str:
    return route_slug_from_typed_domain_id(
        record.get("id"),
        expected_domain="trait",
        context="curated trait id",
    )


def _source_prefixes(record: dict[str, Any]) -> tuple[str, ...]:
    facts = record.get("facts")
    if not isinstance(facts, dict):
        return ()
    source_identity = facts.get("sourceIdentity")
    if not isinstance(source_identity, dict):
        return ()
    prefixes = source_identity.get("prefixes")
    if not isinstance(prefixes, list):
        return ()
    return tuple(str(prefix) for prefix in prefixes if str(prefix).strip())


class TraitCatalog:
    """Resolve Army trait labels through optional curated rules data."""

    def __init__(self, database: Database, rules_database: RulesDatabase | None) -> None:
        self.database = database
        self.rules_database = rules_database
        self._records: list[dict[str, Any]] | None = None
        self._exact: dict[str, dict[str, Any]] | None = None
        self._prefixes: list[tuple[str, dict[str, Any]]] | None = None

    def _ensure_index(self) -> None:
        if self._records is not None:
            return
        records = (
            self.rules_database.records_by_kind("trait")
            if self.rules_database is not None
            else []
        )
        exact: dict[str, dict[str, Any]] = {}
        prefixes: list[tuple[str, dict[str, Any]]] = []
        for record in records:
            for label in [record["name"], *record.get("aliases", [])]:
                key = str(label).strip().casefold()
                if not key:
                    continue
                existing = exact.get(key)
                if existing is not None and existing["id"] != record["id"]:
                    raise ValueError(f"Trait identity {label!r} is defined by multiple records")
                exact[key] = record
            for prefix in _source_prefixes(record):
                prefixes.append((prefix.casefold(), record))
        prefixes.sort(key=lambda item: len(item[0]), reverse=True)
        self._records = records
        self._exact = exact
        self._prefixes = prefixes

    def _record_for_label(self, label: object) -> dict[str, Any] | None:
        text = str(label or "").strip()
        if not text or text.startswith("["):
            return None
        self._ensure_index()
        assert self._exact is not None
        assert self._prefixes is not None
        record = self._exact.get(text.casefold())
        if record is not None:
            return record
        folded = text.casefold()
        matches = [record for prefix, record in self._prefixes if folded.startswith(prefix)]
        if not matches:
            return None
        record_ids = {record["id"] for record in matches}
        if len(record_ids) != 1:
            raise ValueError(f"Trait label {text!r} matches multiple curated prefix identities")
        return matches[0]

    def reference(self, label: object) -> dict[str, Any]:
        """Return the API reference for one raw Army trait label."""
        text = str(label or "").strip()
        if not text or text.startswith("["):
            return {"label": text, "name": None, "slug": None}
        record = self._record_for_label(text)
        if record is None:
            source = next(
                (item for item in self.database.list_traits() if item["name"] == text),
                None,
            )
            return {
                "label": text,
                "name": text,
                "slug": None if source is None else source["slug"],
            }
        return {
            "label": text,
            "name": record["name"],
            "slug": _record_slug(record),
        }

    def _trait_groups(self) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        usage = self.database.trait_usage_index()
        for source in self.database.list_traits():
            record = self._record_for_label(source["name"])
            if record is None:
                slug = source["id"]
                name = source["name"]
                description = None
                rule = None
            else:
                slug = _record_slug(record)
                name = record["name"]
                description = record["summary"]
                rule = record
            group = groups.setdefault(
                slug,
                {
                    "id": slug,
                    "name": name,
                    "description": description,
                    "source_traits": [],
                    "source_items": set(),
                    "rule": rule,
                },
            )
            group["source_traits"].append(source)
            group["source_items"].update(usage.get(source["name"], ()))
        result = []
        for group in groups.values():
            group["use_count"] = len(group.pop("source_items"))
            result.append(group)
        return sorted(result, key=lambda item: (item["name"].casefold(), item["id"]))

    def list_traits(self) -> list[dict[str, Any]]:
        """Return raw Army traits grouped under curated identities when available."""
        return [
            {
                "id": group["id"],
                "slug": group["id"],
                "name": group["name"],
                "use_count": group["use_count"],
                "description": group["description"],
            }
            for group in self._trait_groups()
        ]

    def get_trait(self, item_slug: str) -> dict[str, Any] | None:
        """Return one composed trait with usage from all matching raw source labels."""
        trait = next((item for item in self._trait_groups() if item["id"] == item_slug), None)
        if trait is None:
            return None
        variants_by_item: dict[tuple[str, int], dict[str, Any]] = {}
        for source in trait["source_traits"]:
            detail = self.database.get_trait(source["id"])
            if detail is None:
                continue
            for variant in detail["variants"]:
                key = (variant["catalog"], variant["item_id"])
                existing = variants_by_item.get(key)
                if existing is None:
                    variants_by_item[key] = deepcopy(variant)
                    continue
                units = {unit["id"]: unit for unit in existing["units"]}
                units.update({unit["id"]: unit for unit in variant["units"]})
                existing["units"] = sorted(
                    units.values(), key=lambda unit: (unit["name"].casefold(), unit["id"])
                )
        payload = {
            "id": trait["id"],
            "slug": trait["id"],
            "name": trait["name"],
            "use_count": trait["use_count"],
            "description": trait["description"],
            "variants": sorted(
                variants_by_item.values(), key=lambda item: (item["catalog"], item["item_id"])
            ),
        }
        if trait["rule"] is not None:
            payload["rules"] = [trait["rule"]]
        return payload

    def enrich_catalog_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Add curated trait references to every profile containing raw traits."""
        result = deepcopy(item)

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                traits = value.get("traits")
                if isinstance(traits, list):
                    value["trait_references"] = [self.reference(label) for label in traits]
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(result)
        return result
