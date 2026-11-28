"""Transport projection for the current Unit comparison view."""

from __future__ import annotations

from typing import Any

IDENTITY_FIELDS = ("id", "slug", "public_slug", "name")
ARMY_FIELDS = (
    *IDENTITY_FIELDS, "availability_flags", "availability_badges", "presentation_visible",
)
PROFILE_FIELDS = (
    "group_id", "profile_id", "profile_identity", "name", "display_name",
    "move_1", "move_2", "cc", "bs", "ph", "wip", "arm", "bts",
    "vitality", "is_structure", "silhouette", "ava", "type_label", "classification",
)
LOADOUT_FIELDS = ("group_id", "option_id", "name", "points", "swc")
ITEM_FIELDS = ("id", "slug", "name", "quantity", "loadout_payload_id", "parameter_semantics")
ITEM_LISTS = ("skills", "equipment", "weapons", "includes", "peripherals", "characteristics")


def _fields(record: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: record[key] for key in keys if key in record}


def _item(record: dict[str, Any]) -> dict[str, Any]:
    result = _fields(record, ITEM_FIELDS)
    if "extras" in record:
        result["extras"] = [
            _fields(extra, ("id", "name", "is_distance"))
            for extra in record["extras"]
        ] if record["extras"] is not None else None
    return result


def _occurrence(record: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    result = _fields(record, keys)
    for key in ITEM_LISTS:
        if key in record:
            result[key] = [
                _item(item) for item in record[key]
            ] if record[key] is not None else None
    return result


def comparison_unit(unit: dict[str, Any]) -> dict[str, Any]:
    """Keep only the comparison client contract, preserving canonical occurrence order."""
    return {
        **_fields(unit, IDENTITY_FIELDS),
        "armies": [
            {
                **_fields(army, ARMY_FIELDS),
                "profiles": [
                    _occurrence(profile, PROFILE_FIELDS) for profile in army.get("profiles", ())
                ],
                "loadouts": [
                    _occurrence(loadout, LOADOUT_FIELDS) for loadout in army.get("loadouts", ())
                ],
            }
            for army in unit.get("armies", ())
        ],
    }
