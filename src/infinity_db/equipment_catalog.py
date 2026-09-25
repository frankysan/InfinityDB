"""Compose textual Army Equipment with presentation-encoded Equipment identities."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.catalog_slugs import attach_public_catalog_slug
from infinity_db.database.repository import Database
from infinity_db.domain_slugs import route_slug_from_typed_domain_id
from infinity_db.equipment_config import (
    EquipmentPresentationEncoding,
    load_equipment_presentation_config,
)
from infinity_db.rules_database import RulesDatabase


class EquipmentCatalog:
    """Expose canonical Equipment regardless of how Army presents its occurrence."""

    def __init__(self, database: Database, rules_database: RulesDatabase | None) -> None:
        self.database = database
        self.rules_database = rules_database
        self._encodings = load_equipment_presentation_config()

    def _records_by_slug(self) -> dict[str, dict[str, Any]]:
        if self.rules_database is None:
            return {}
        records: dict[str, dict[str, Any]] = {}
        for record in self.rules_database.composed_records_by_kind("equipment"):
            if (record.get("variant_semantics") or {}).get("inheritance") == "source":
                continue
            slug = route_slug_from_typed_domain_id(
                record.get("id"),
                expected_domain="equipment",
                context="curated equipment id",
            )
            records[slug] = record
        return records

    def _encoding_by_slug(self) -> dict[str, EquipmentPresentationEncoding]:
        return {item.equipment_id: item for item in self._encodings}

    def _encoding_by_characteristic(self) -> dict[str, EquipmentPresentationEncoding]:
        return {item.characteristic.casefold(): item for item in self._encodings}

    def _units_for_encoding(
        self,
        encoding: EquipmentPresentationEncoding,
        *,
        include_all_optional: bool,
    ) -> list[dict[str, Any]]:
        logical_ids = self.database.logical_unit_ids_for_characteristic(
            encoding.characteristic
        )
        if not logical_ids:
            return []
        flags = {
            "mercs": include_all_optional,
            "specops": True,
            "teamops": include_all_optional,
            "reinforcement": include_all_optional,
        }
        payload = self.database.list_units(
            limit=10_000,
            _unbounded=True,
            **flags,
        )
        return [item for item in payload["items"] if item["id"] in logical_ids]

    def list_equipment(self) -> list[dict[str, Any]]:
        """Return textual Army Equipment plus reviewed presentation-encoded identities."""

        items = deepcopy(self.database.list_catalog_items("equipment"))
        represented_slugs: set[str] = set()
        for item in items:
            attach_public_catalog_slug(self.database, "equipment", item)
            slug = item.get("slug")
            if isinstance(slug, str):
                represented_slugs.add(slug)

        records = self._records_by_slug()
        for encoding in self._encodings:
            if encoding.equipment_id in represented_slugs:
                continue
            record = records.get(encoding.equipment_id)
            if record is None:
                continue
            items.append(
                {
                    "id": encoding.equipment_id,
                    "slug": encoding.equipment_id,
                    "name": record["name"],
                    "wiki": None,
                    "source_ids": [],
                    "use_count": len(
                        self._units_for_encoding(
                            encoding,
                            include_all_optional=False,
                        )
                    ),
                }
            )
        return sorted(items, key=lambda item: (str(item["name"]).casefold(), str(item["id"])))

    def get_equipment(self, item_ref: int | str) -> dict[str, Any] | None:
        """Return textual or presentation-encoded Equipment with canonical usage."""

        source_item = self.database.get_catalog_item("equipment", item_ref)
        if source_item is not None:
            attach_public_catalog_slug(self.database, "equipment", source_item)
            return source_item
        if not isinstance(item_ref, str):
            return None
        encoding = self._encoding_by_slug().get(item_ref)
        record = self._records_by_slug().get(item_ref)
        if encoding is None or record is None:
            return None
        units = self._units_for_encoding(encoding, include_all_optional=True)
        return {
            "id": item_ref,
            "slug": item_ref,
            "name": record["name"],
            "wiki": None,
            "source_ids": [],
            "variants": [
                {
                    "item_id": item_ref,
                    "item_name": record["name"],
                    "extras": [],
                    "units": units,
                }
            ] if units else [],
            "profiles": [],
        }

    def logical_unit_ids_for_filter(self, item_ref: int | str | None) -> frozenset[int] | None:
        """Resolve a presentation-encoded Equipment filter to logical Unit identities."""

        if not isinstance(item_ref, str):
            return None
        if self.database.application_catalog_id("equipment", item_ref) is not None:
            return None
        encoding = self._encoding_by_slug().get(item_ref)
        if encoding is None:
            return None
        return self.database.logical_unit_ids_for_characteristic(encoding.characteristic)

    def enrich_unit(self, unit: dict[str, Any]) -> dict[str, Any]:
        """Link presentation characteristics to their canonical Equipment identity."""

        result = deepcopy(unit)
        records = self._records_by_slug()
        encodings = self._encoding_by_characteristic()

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                characteristics = value.get("characteristics")
                if isinstance(characteristics, list):
                    for characteristic in characteristics:
                        if not isinstance(characteristic, dict):
                            continue
                        name = characteristic.get("name")
                        if not isinstance(name, str):
                            continue
                        encoding = encodings.get(name.casefold())
                        if encoding is None:
                            continue
                        record = records.get(encoding.equipment_id)
                        if record is None:
                            continue
                        characteristic["equipment_reference"] = {
                            "id": encoding.equipment_id,
                            "slug": encoding.equipment_id,
                            "name": record["name"],
                        }
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(result)
        return result
