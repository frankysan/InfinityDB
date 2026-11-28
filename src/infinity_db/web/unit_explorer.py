"""Transport projection for Extended Unit Explorer profiles."""
from __future__ import annotations

from typing import Any

PROFILE_FIELDS = ("display_name", "type", "type_label", "classification", "different_stat_labels")
STAT_FIELDS = (
    "move_1", "move_2", "cc", "bs", "ph", "wip", "arm", "bts",
    "is_structure", "vitality", "silhouette",
)
ITEM_FIELDS = ("name", "quantity", "parameter_semantics")


def _fields(record: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: record[key] for key in keys if key in record}


def _item(item: dict[str, Any]) -> dict[str, Any]:
    result = _fields(item, ITEM_FIELDS)
    if "extras" in item:
        result["extras"] = [
            _fields(extra, ("name", "is_distance")) for extra in item["extras"] or []
        ]
    return result


def explorer_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Preserve the fields rendered by unit-list.js, without provenance or variants."""
    return {
        **_fields(profile, PROFILE_FIELDS),
        "stats": _fields(profile.get("stats") or {}, STAT_FIELDS),
        "availability": [
            _fields(entry, ("army_id", "ava")) for entry in profile.get("availability") or []
        ],
        "symbol_descriptors": [
            _fields(entry, ("label", "symbol_path"))
            for entry in profile.get("symbol_descriptors") or []
        ],
        "shared_items": {
            key: [_item(item) for item in (profile.get("shared_items") or {}).get(key) or []]
            for key in ("skills", "equipment", "weapons")
        },
    }


def explorer_unit(unit: dict[str, Any]) -> dict[str, Any]:
    """Keep the Extended row renderer's inputs and complete matching evidence."""
    return {
        **_fields(unit, ("id", "public_slug", "name", "symbol_path", "source_ids",
                         "matching_contexts")),
        "display_faction": _fields(unit.get("display_faction") or {}, ("slug",)),
        "armies": [
            _fields(army, ("id", "public_slug", "slug", "name", "symbol_path"))
            for army in unit["armies"]
        ],
        "general_profiles": [explorer_profile(profile) for profile in unit["general_profiles"]],
    }
