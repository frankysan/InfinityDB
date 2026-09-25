"""Compose raw Army trait usage with curated trait rules references."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database, accent_insensitive_key
from infinity_db.domain_references import public_slug_for_reference
from infinity_db.domain_slugs import route_slug_from_typed_domain_id
from infinity_db.rules_database import RulesDatabase

_SIGNED_MODIFIER = re.compile(r"^(?P<base>.+?)\s*\((?P<modifier>[+-]\d+)\)$")


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
    """Compose Army profile properties with the canonical Trait vocabulary."""

    def __init__(self, database: Database, rules_database: RulesDatabase | None) -> None:
        self.database = database
        self.rules_database = rules_database
        self._records: list[dict[str, Any]] | None = None
        self._exact: dict[str, dict[str, Any]] | None = None
        self._prefixes: list[tuple[str, dict[str, Any]]] | None = None
        self._labels: dict[str, dict[str, Any]] | None = None
        self._modifier_bases: set[str] | None = None

    def _ensure_index(self) -> None:
        if self._records is not None:
            return
        records = (
            self.rules_database.composed_records_by_kind("trait")
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
        labels: dict[str, dict[str, Any]] = {}
        modifier_bases: set[str] = set()
        if self.rules_database is not None:
            for label in self.rules_database.current_labels():
                key = accent_insensitive_key(label["name"])
                existing = labels.get(key)
                if existing is not None and existing["id"] != label["id"]:
                    raise ValueError(
                        f"Rules label {label['name']!r} resolves to multiple identities"
                    )
                labels[key] = label
            for kind in ("skill", "equipment"):
                for record in self.rules_database.composed_records_by_kind(kind):
                    for label in [record["name"], *record.get("aliases", [])]:
                        key = accent_insensitive_key(label)
                        if key:
                            modifier_bases.add(key)
        self._records = records
        self._exact = exact
        self._prefixes = prefixes
        self._labels = labels
        self._modifier_bases = modifier_bases

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

    def _non_trait_source_property(self, label: object) -> dict[str, str] | None:
        """Classify known Army property text that is not a rules-native Trait."""
        text = str(label or "").strip()
        if not text or self.rules_database is None:
            return None
        self._ensure_index()
        assert self._labels is not None
        assert self._modifier_bases is not None
        rules_label = self._labels.get(accent_insensitive_key(text))
        if rules_label is not None:
            return {"kind": "label", "name": str(rules_label["name"])}
        modifier = _SIGNED_MODIFIER.fullmatch(text)
        if modifier is not None:
            base_key = accent_insensitive_key(modifier.group("base"))
            if base_key in self._modifier_bases:
                return {"kind": "modifier", "name": text}
        return None

    def reference(self, label: object) -> dict[str, Any]:
        """Return the API reference for one raw Army trait label."""
        text = str(label or "").strip()
        if not text or text.startswith("["):
            return {"label": text, "name": None, "slug": None}
        record = self._record_for_label(text)
        if record is None:
            non_trait = self._non_trait_source_property(text)
            if non_trait is not None:
                return {
                    "label": text,
                    "name": non_trait["name"],
                    "slug": None,
                }
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
        self._ensure_index()
        if self.rules_database is not None:
            assert self._records is not None
            for record in self._records:
                slug = _record_slug(record)
                groups[slug] = {
                    "id": slug,
                    "name": record["name"],
                    "description": record["summary"],
                    "source_traits": [],
                    "source_items": set(),
                    "rule": record,
                }
        for source in self.database.list_traits():
            record = self._record_for_label(source["name"])
            if record is None:
                if self._non_trait_source_property(source["name"]) is not None:
                    continue
                slug = source["id"]
                name = source["name"]
                description = None
                rule = None
                existing = groups.get(slug)
                if existing is not None and existing["rule"] is not None:
                    raise ValueError(
                        f"Raw Army property {name!r} collides with curated Trait slug {slug!r}"
                    )
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
        """Return canonical Traits plus unresolved raw properties when necessary."""
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
                    candidate = deepcopy(variant)
                    slug = public_slug_for_reference(
                        self.database, variant["catalog"], variant["item_id"]
                    )
                    if slug is not None:
                        candidate["item_slug"] = slug
                    variants_by_item[key] = candidate
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
