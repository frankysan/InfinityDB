"""Validated mappings for Equipment encoded through Army presentation characteristics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_config_path
from infinity_db.domain_slugs import require_domain_slug

EQUIPMENT_PRESENTATION_CONFIG_FORMAT = "InfinityDB equipment presentation encodings"
EQUIPMENT_PRESENTATION_CONFIG_VERSION = 1
DEFAULT_EQUIPMENT_PRESENTATION_CONFIG = maintained_config_path(
    "catalogs", "equipment-presentation-encodings.json"
)


class EquipmentConfigError(ValueError):
    """Raised when maintained Equipment presentation mappings are invalid."""


@dataclass(frozen=True)
class EquipmentPresentationEncoding:
    """One source presentation characteristic mapped to canonical Equipment."""

    equipment_id: str
    characteristic: str
    reason: str


def _non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EquipmentConfigError(f"{context} must be a non-empty string")
    return value.strip()


def parse_equipment_presentation_config(
    document: Any,
) -> tuple[EquipmentPresentationEncoding, ...]:
    """Validate the maintained characteristic-to-Equipment mapping."""

    if not isinstance(document, dict):
        raise EquipmentConfigError("equipment presentation config must be an object")
    expected = {"format", "formatVersion", "encodings"}
    if set(document) != expected:
        raise EquipmentConfigError(
            f"equipment presentation config must contain exactly {sorted(expected)}"
        )
    if document.get("format") != EQUIPMENT_PRESENTATION_CONFIG_FORMAT:
        raise EquipmentConfigError(
            "equipment presentation config format must be "
            f"{EQUIPMENT_PRESENTATION_CONFIG_FORMAT!r}"
        )
    if document.get("formatVersion") != EQUIPMENT_PRESENTATION_CONFIG_VERSION:
        raise EquipmentConfigError(
            "equipment presentation config formatVersion must be "
            f"{EQUIPMENT_PRESENTATION_CONFIG_VERSION}"
        )
    raw_items = document.get("encodings")
    if not isinstance(raw_items, list):
        raise EquipmentConfigError("equipment presentation config.encodings must be an array")

    result: list[EquipmentPresentationEncoding] = []
    seen_equipment: set[str] = set()
    seen_characteristics: set[str] = set()
    for index, raw in enumerate(raw_items):
        context = f"equipment presentation config.encodings[{index}]"
        if not isinstance(raw, dict):
            raise EquipmentConfigError(f"{context} must be an object")
        fields = {"equipment_id", "characteristic", "reason"}
        if set(raw) != fields:
            raise EquipmentConfigError(f"{context} must contain exactly {sorted(fields)}")
        try:
            equipment_id = require_domain_slug(
                raw.get("equipment_id"), context=f"{context}.equipment_id"
            )
        except ValueError as exc:
            raise EquipmentConfigError(str(exc)) from exc
        characteristic = _non_empty_string(
            raw.get("characteristic"), f"{context}.characteristic"
        )
        reason = _non_empty_string(raw.get("reason"), f"{context}.reason")
        if equipment_id in seen_equipment:
            raise EquipmentConfigError(f"duplicate Equipment id {equipment_id!r}")
        characteristic_key = characteristic.casefold()
        if characteristic_key in seen_characteristics:
            raise EquipmentConfigError(
                f"duplicate Equipment characteristic {characteristic!r}"
            )
        seen_equipment.add(equipment_id)
        seen_characteristics.add(characteristic_key)
        result.append(
            EquipmentPresentationEncoding(
                equipment_id=equipment_id,
                characteristic=characteristic,
                reason=reason,
            )
        )
    return tuple(result)


def load_equipment_presentation_config(
    path: Path = DEFAULT_EQUIPMENT_PRESENTATION_CONFIG,
) -> tuple[EquipmentPresentationEncoding, ...]:
    """Load and validate maintained Equipment presentation mappings."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EquipmentConfigError(
            f"Cannot read equipment presentation config {path}: {exc}"
        ) from exc
    return parse_equipment_presentation_config(document)
