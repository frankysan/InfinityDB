"""Compose Army, presentation-encoded, and curated-only Equipment identities."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from infinity_db.catalog_slugs import attach_public_catalog_slug
from infinity_db.database.repository import Database, instance_lru_cache
from infinity_db.domain_slugs import route_slug_from_typed_domain_id
from infinity_db.equipment_config import (
    CURATED_ONLY_EQUIPMENT_SLUGS,
    EquipmentPresentationEncoding,
    load_equipment_presentation_config,
)
from infinity_db.rules_database import RulesDatabase

if TYPE_CHECKING:
    from infinity_db.catalog_projection import CatalogProjection


class EquipmentCatalog:
    """Expose canonical Equipment regardless of how Army presents its occurrence."""

    def __init__(
        self, database: Database, rules_database: RulesDatabase | None,
        *, projection: CatalogProjection | None = None,
    ) -> None:
        self.database = database
        self.rules_database = rules_database
        self._projection = projection
        embedded = database.equipment_presentation_encodings()
        self._encodings = (
            embedded if embedded is not None else load_equipment_presentation_config()
        )

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

    @instance_lru_cache(maxsize=1)
    def _presentation_equipment_names(self) -> dict[str, str]:
        """Cache the immutable name lookup needed by characteristic enrichment."""
        records = self._records_by_slug()
        return {
            encoding.equipment_id: records[encoding.equipment_id]["name"]
            for encoding in self._encodings if encoding.equipment_id in records
        }

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
        payload = self.database.list_units(
            limit=10_000,
            mercs=include_all_optional,
            specops=True,
            teamops=include_all_optional,
            reinforcement=include_all_optional,
            _unbounded=True,
        )
        return [item for item in payload["items"] if item["id"] in logical_ids]

    def list_equipment(self, *, filter_only: bool = False) -> list[dict[str, Any]]:
        """Return Army, presentation-encoded, and curated-only Equipment."""

        if self._projection is not None:
            return self._projection.summary(
                "equipment", "public-filter" if filter_only else "public",
            )
        items = deepcopy(
            self.database.list_catalog_filter_items("equipment") if filter_only
            else self.database.list_catalog_items("equipment")
        )
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
                    **({} if filter_only else {
                        "use_count": len(self._units_for_encoding(
                            encoding, include_all_optional=False,
                        )),
                    }),
                }
            )
            represented_slugs.add(encoding.equipment_id)
        # Rules-only Equipment (such as Firewall) has no Army source identity.
        # Publish its curated definition instead of creating a fictitious Army link.
        for slug in sorted(CURATED_ONLY_EQUIPMENT_SLUGS):
            record = records.get(slug)
            if slug in represented_slugs or record is None or record.get("army_links"):
                continue
            items.append(
                {
                    "id": slug,
                    "slug": slug,
                    "name": record["name"],
                    "wiki": None,
                    "source_ids": [],
                    "use_count": 0,
                }
            )
        for item in items:
            record = records.get(str(item.get("slug", "")))
            if record and record.get("aliases"):
                item["aliases"] = list(record["aliases"])
        return sorted(items, key=lambda item: (str(item["name"]).casefold(), str(item["id"])))

    def get_equipment(
        self, item_ref: int | str, *, expand_usage: bool = True,
    ) -> dict[str, Any] | None:
        """Return textual or presentation-encoded Equipment with canonical usage."""

        source_item = self.database.get_catalog_item(
            "equipment", item_ref, expand_usage=expand_usage,
        )
        if source_item is not None:
            attach_public_catalog_slug(self.database, "equipment", source_item)
            return source_item
        if not isinstance(item_ref, str):
            return None
        encoding = self._encoding_by_slug().get(item_ref)
        record = self._records_by_slug().get(item_ref)
        if record is None:
            return None
        if encoding is None and (
            item_ref not in CURATED_ONLY_EQUIPMENT_SLUGS or record.get("army_links")
        ):
            return None
        units = (
            self._units_for_encoding(encoding, include_all_optional=True)
            if encoding is not None
            else []
        )
        result = {
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
        if encoding is None:
            result["rules"] = [record]
        return result

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

    def presentation_equipment_characteristic_ids(self) -> dict[str, int]:
        """Map presentation-only Equipment slugs to source Characteristic IDs."""

        result: dict[str, int] = {}
        for encoding in self._encodings:
            source_id = self.characteristic_filter_id_for_equipment(encoding.equipment_id)
            if source_id is not None:
                result[encoding.equipment_id] = source_id
        return result

    def characteristic_filter_id_for_equipment(self, item_ref: int | str) -> int | None:
        """Return the source Characteristic backing presentation-only Equipment."""

        if not isinstance(item_ref, str):
            return None
        if self.database.application_catalog_id("equipment", item_ref) is not None:
            return None
        encoding = self._encoding_by_slug().get(item_ref)
        if encoding is None:
            return None
        characteristic = encoding.characteristic.casefold()
        return next(
            (
                int(item["id"])
                for item in self.database.list_unit_filter_values()["characteristics"]
                if item["name"].casefold() == characteristic
            ),
            None,
        )

    def enrich_unit(
        self, unit: dict[str, Any], *, in_place: bool = False,
    ) -> dict[str, Any]:
        """Link presentation characteristics to their canonical Equipment identity."""

        result = unit if in_place else deepcopy(unit)
        names = self._presentation_equipment_names()
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
                        equipment_name = names.get(encoding.equipment_id)
                        if equipment_name is None:
                            continue
                        characteristic["equipment_reference"] = {
                            "id": encoding.equipment_id,
                            "slug": encoding.equipment_id,
                            "name": equipment_name,
                        }
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(result)
        return result
