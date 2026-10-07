"""Backend-owned Unit presentation semantics for browser/API consumers."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any
from urllib.parse import quote

from infinity_db.unit_filter_config import load_unit_filter_config

OPTIONAL_AVAILABILITY_FLAGS = ("mercs", "specops", "teamops", "reinforcement")

_TROOP_TYPE_LABELS = {
    "LI": "Light Infantry",
    "MI": "Medium Infantry",
    "HI": "Heavy Infantry",
    "REM": "Remote",
    "TAG": "Tactical Armored Gear",
    "WB": "Warband",
    "SK": "Skirmisher",
    "VH": "Vehicle",
}

_DEVELOPER_ONLY_CHARACTERISTICS = frozenset({"no cube", "non hackable", "not impetuous"})

_SYMBOL_PRESENTATION = {
    "regular": {
        "symbol_path": "orders/regular.svg",
        "label": "Regular Order",
        "help_key": "training-orders",
    },
    "irregular": {
        "symbol_path": "orders/irregular.svg",
        "label": "Irregular Order",
        "help_key": "training-orders",
    },
    "peripheral": {
        "symbol_path": "characteristics/peripheral.svg",
        "label": "Peripheral",
        "help_key": "peripheral",
    },
    "impetuous": {
        "symbol_path": "orders/impetuous.svg",
        "label": "Impetuous",
    },
    "tactical": {
        "symbol_path": "orders/tactical.svg",
        "label": "Tactical Awareness",
        "help_key": "training-orders",
    },
    "lieutenant": {
        "symbol_path": "orders/lieutenant.svg",
        "label": "Lieutenant Order",
        "help_key": "training-orders",
    },
    "hackable": {
        "symbol_path": "characteristics/hackable.svg",
        "label": "Hackable",
        "help_key": "hackable",
    },
    "cube": {
        "symbol_path": "characteristics/cube.svg",
        "label": "Cube",
    },
    "cube-2": {
        "symbol_path": "characteristics/cube-2.svg",
        "label": "Cube 2.0",
    },
}

_CHARACTERISTIC_SYMBOL_TYPES = {
    "regular": "regular",
    "irregular": "irregular",
    "impetuous": "impetuous",
    "peripheral": "peripheral",
    "hackable": "hackable",
    "cube": "cube",
    "cube 2.0": "cube-2",
}

_PERIPHERAL_TYPE_LABELS = {
    "rule:peripheral-type:servant": "Servant",
    "rule:peripheral-type:synchronized": "Synchronized",
    "rule:peripheral-type:control": "Control",
    "rule:peripheral-type:ancillary": "Ancillary",
    "rule:peripheral-type:cyberplug": "Cyberplug",
}

_STAT_PROPERTIES = {
    "CC": "cc",
    "BS": "bs",
    "PH": "ph",
    "WIP": "wip",
    "ARM": "arm",
    "BTS": "bts",
    "VITA": "vitality",
    "S": "silhouette",
}


def troop_type_label(value: Any) -> Any:
    """Return the player-facing long label for a source troop-type abbreviation."""

    return _TROOP_TYPE_LABELS.get(value, value)


def _normalized_name(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _symbol_descriptor(symbol_type: str, *, href: str | None = None) -> dict[str, Any]:
    descriptor = {"type": symbol_type, **_SYMBOL_PRESENTATION[symbol_type]}
    if href:
        descriptor["href"] = href
    return descriptor


def characteristic_presentation(characteristic: Any) -> dict[str, Any]:
    """Return one backend-owned presentation descriptor for a characteristic."""

    if isinstance(characteristic, dict):
        name = str(characteristic.get("name") or "")
        equipment_reference = characteristic.get("equipment_reference")
    else:
        name = str(characteristic or "")
        equipment_reference = None
    normalized = _normalized_name(name)
    descriptor: dict[str, Any] = {
        "name": name,
        "developer_only": normalized in _DEVELOPER_ONLY_CHARACTERISTICS,
    }
    symbol_type = _CHARACTERISTIC_SYMBOL_TYPES.get(normalized)
    if symbol_type is None:
        return descriptor
    href = None
    if isinstance(equipment_reference, dict):
        slug = equipment_reference.get("slug")
        if slug:
            href = f"/equipment/{quote(str(slug), safe='')}"
    descriptor["symbol"] = _symbol_descriptor(symbol_type, href=href)
    return descriptor


def _item_identity(item: dict[str, Any]) -> tuple[Any, ...]:
    quantity = item.get("quantity")
    if quantity is None or int(quantity) == 1:
        quantity = None
    extras = tuple(
        sorted((extra.get("id") for extra in item.get("extras", ())), key=lambda value: str(value))
    )
    return item.get("id"), quantity, extras


def _unique_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        identity = _item_identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(item)
    return result


def _common_items(profiles: list[dict[str, Any]], property_name: str) -> list[dict[str, Any]]:
    if not profiles:
        return []
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in profiles[0].get(property_name, ()):
        identity = _item_identity(item)
        if identity in seen:
            continue
        if all(
            any(
                _item_identity(candidate) == identity
                for candidate in profile.get(property_name, ())
            )
            for profile in profiles
        ):
            seen.add(identity)
            result.append(item)
    return result


def _general_profile_skills(
    profiles: list[dict[str, Any]], loadouts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    skills = list(_common_items(profiles, "skills"))
    if len(loadouts) != 1:
        return skills
    identities = {_item_identity(item) for item in skills}
    for skill in loadouts[0].get("skills", ()):
        identity = _item_identity(skill)
        if identity not in identities:
            identities.add(identity)
            skills.append(skill)
    return skills


def _without_shared(
    items: Iterable[dict[str, Any]], shared_items: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    shared = {_item_identity(item) for item in shared_items}
    return [item for item in items if _item_identity(item) not in shared]


def _most_common(items: Iterable[dict[str, Any]], property_name: str) -> Any:
    counts: dict[Any, int] = {}
    selected = None
    highest_count = 0
    for item in items:
        value = item.get(property_name)
        if value is None or value == "":
            continue
        counts[value] = counts.get(value, 0) + 1
        if counts[value] > highest_count:
            selected = value
            highest_count = counts[value]
    return selected


def _general_stats(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "move_1": _most_common(profiles, "move_1"),
        "move_2": _most_common(profiles, "move_2"),
        "is_structure": _most_common(profiles, "is_structure"),
        **{
            property_name: _most_common(profiles, property_name)
            for property_name in _STAT_PROPERTIES.values()
        },
    }


def _stat_difference_labels(
    profiles: list[dict[str, Any]], general: dict[str, Any]
) -> list[str]:
    result: list[str] = []
    if any(
        profile.get("move_1") != general.get("move_1")
        or profile.get("move_2") != general.get("move_2")
        for profile in profiles
    ):
        result.append("MOV")
    for label, property_name in _STAT_PROPERTIES.items():
        differs = any(
            profile.get(property_name) != general.get(property_name)
            for profile in profiles
        )
        if label == "VITA":
            differs = differs or any(
                bool(profile.get("is_structure")) != bool(general.get("is_structure"))
                for profile in profiles
            )
        if differs:
            result.append(label)
    return result


def _statline_key(profile: dict[str, Any]) -> tuple[Any, ...]:
    stats = profile["stats"]
    return (
        stats.get("move_1"),
        stats.get("move_2"),
        stats.get("cc"),
        stats.get("bs"),
        stats.get("ph"),
        stats.get("wip"),
        stats.get("arm"),
        stats.get("bts"),
        stats.get("vitality"),
        stats.get("silhouette"),
        bool(stats.get("is_structure")),
    )


def _annotate_general_profile_visibility(profiles: list[dict[str, Any]]) -> None:
    for profile in profiles:
        profile["presentation_visible"] = not any(
            candidate is not profile
            and candidate["display_name"] == profile["display_name"]
            and _statline_key(candidate) == _statline_key(profile)
            and (
                (profile["reinforcement_only"] and not candidate["reinforcement_only"])
                or (
                    profile["reinforcement_only"] == candidate["reinforcement_only"]
                    and candidate["occurrence_count"] > profile["occurrence_count"]
                )
            )
            for candidate in profiles
        )


def _prominent_order_type(loadouts: Iterable[dict[str, Any]]) -> str | None:
    counts = {"regular": 0, "irregular": 0}
    for loadout in loadouts:
        for order in loadout.get("orders", ()):
            order_type = _normalized_name(order.get("type"))
            if order_type not in counts:
                continue
            count = int(order.get("list") or order.get("total") or 1)
            counts[order_type] += count
    prominent = "regular" if counts["regular"] >= counts["irregular"] else "irregular"
    return prominent if counts[prominent] else None


def _skill_matches(skill: dict[str, Any], name: str) -> bool:
    target = _normalized_name(name)
    slug = _normalized_name(skill.get("slug")).replace(" ", "-")
    return slug == target.replace(" ", "-") or _normalized_name(skill.get("name")) == target


def _has_skill(items: Iterable[dict[str, Any]], name: str) -> bool:
    return any(
        _skill_matches(skill, name)
        for item in items
        for skill in item.get("skills", ())
    )


def _lieutenant_skills(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        skill
        for item in items
        for skill in item.get("skills", ())
        if _normalized_name(skill.get("name")).startswith("lieutenant")
    ]


def _has_lieutenant_plus_one(items: Iterable[dict[str, Any]]) -> bool:
    return any(
        _normalized_name(skill.get("name")) == "lieutenant (+1 order)"
        or (
            _normalized_name(skill.get("name")) == "lieutenant"
            and any(
                _normalized_name(extra.get("name")) == "+1 order"
                for extra in skill.get("extras", ())
            )
        )
        for skill in _lieutenant_skills(items)
    )


def _lieutenant_order_count(items: Iterable[dict[str, Any]]) -> int:
    materialized = list(items)
    skills = _lieutenant_skills(materialized)
    if not skills:
        return 0
    return 2 if _has_lieutenant_plus_one(materialized) else 1


def _general_lieutenant_order_count(
    profiles: list[dict[str, Any]], loadouts: list[dict[str, Any]]
) -> int:
    if _has_lieutenant_plus_one(profiles):
        return 2
    if _lieutenant_skills(profiles):
        return 1
    if loadouts and all(_lieutenant_skills([loadout]) for loadout in loadouts):
        return 1
    return 0


def _general_order_type(
    profiles: list[dict[str, Any]], loadouts: list[dict[str, Any]]
) -> str | None:
    if _has_skill(loadouts, "regular"):
        return "irregular"
    order_type = _prominent_order_type(loadouts)
    if order_type:
        return order_type
    return (
        "peripheral"
        if any(
            _normalized_name(skill.get("name")).startswith("peripheral")
            for item in [*profiles, *loadouts]
            for skill in item.get("skills", ())
        )
        else None
    )


def _characteristic_symbols(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    characteristics: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        for characteristic in profile.get("characteristics", ()):
            if not isinstance(characteristic, dict):
                continue
            normalized = _normalized_name(characteristic.get("name"))
            if normalized and normalized not in characteristics:
                characteristics[normalized] = characteristic
    result: list[dict[str, Any]] = []
    for name in ("hackable", "cube", "cube 2.0"):
        characteristic = characteristics.get(name)
        if characteristic is None:
            continue
        presentation = characteristic_presentation(characteristic)
        symbol = presentation.get("symbol")
        if symbol:
            result.append(symbol)
    return result


def _symbol_descriptors(
    profiles: list[dict[str, Any]], loadouts: list[dict[str, Any]], order_type: str | None
) -> list[dict[str, Any]]:
    symbol_types: list[str] = []
    if order_type:
        symbol_types.append(order_type)
    if _has_skill([*profiles, *loadouts], "impetuous"):
        symbol_types.append("impetuous")
    if _has_skill([*profiles, *loadouts], "tactical awareness"):
        symbol_types.append("tactical")
    symbol_types.extend(
        ["lieutenant"] * _general_lieutenant_order_count(profiles, loadouts)
    )
    descriptors = [_symbol_descriptor(symbol_type) for symbol_type in symbol_types]
    descriptors.extend(_characteristic_symbols(profiles))
    return descriptors


def _army_requested(army: dict[str, Any], requested_army: str | None) -> bool:
    if not requested_army:
        return False
    return requested_army in {
        str(army.get("id") or ""),
        str(army.get("slug") or ""),
        str(army.get("public_slug") or ""),
    }


def _army_enabled(army: dict[str, Any], optional_filters: dict[str, bool]) -> bool:
    return all(optional_filters.get(flag, True) for flag in army.get("availability_flags", ()))


def _annotate_peripheral_presentations(value: Any) -> None:
    if isinstance(value, dict):
        type_id = value.get("type_id")
        if type_id in _PERIPHERAL_TYPE_LABELS:
            value["type_label"] = _PERIPHERAL_TYPE_LABELS[type_id]
        for child in value.values():
            _annotate_peripheral_presentations(child)
    elif isinstance(value, list):
        for child in value:
            _annotate_peripheral_presentations(child)


def _annotate_composite_option_presentations(armies: Iterable[dict[str, Any]]) -> None:
    for army in armies:
        for option in army.get("composite_options", ()):
            presentations = []
            for order in option.get("orders", ()):
                symbol_type = _normalized_name(order.get("type"))
                presentation = _SYMBOL_PRESENTATION.get(symbol_type)
                presentations.append(
                    {
                        "label": presentation["label"],
                        "symbol_descriptor": _symbol_descriptor(symbol_type),
                    }
                    if presentation
                    else None
                )
            option["order_presentations"] = presentations


def enrich_unit_filter_presentation(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach player-facing Unit-filter labels and reviewed vocabulary overlays."""

    result = deepcopy(payload)
    config = load_unit_filter_config()
    for item in result.get("troop_types", ()):
        item["display_name"] = troop_type_label(item.get("name"))
    result["characteristics"] = [
        item
        for item in result.get("characteristics", ())
        if item.get("slug") not in config.hidden_characteristics
    ]
    combined_classifications = {
        membership.source_classification
        for membership in config.classification_memberships
    }
    result["classifications"] = [
        item
        for item in result.get("classifications", ())
        if item.get("slug") not in combined_classifications
    ]
    return result


def enrich_unit_list_presentation(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach backend-owned labels/symbol roles to extended Unit-list profiles."""

    for unit in items:
        for profile in unit.get("profiles", ()):
            profile["type_label"] = troop_type_label(profile.get("type"))
            profile["characteristic_presentations"] = [
                characteristic_presentation(characteristic)
                for characteristic in profile.get("characteristics", ())
            ]
    return items


def enrich_unit_presentation(
    unit: dict[str, Any],
    *,
    optional_filters: dict[str, bool] | None = None,
    requested_army: str | None = None,
) -> dict[str, Any]:
    """Compose General-profile and Unit-detail presentation semantics in the backend.

    The underlying Army occurrences remain intact. ``general_profiles`` reflects the same optional
    availability selection the Unit page is rendering, while the source/profile/loadout rows retain
    their provenance and receive only explicit presentation annotations.
    """

    optional_filters = {
        flag: True for flag in OPTIONAL_AVAILABILITY_FLAGS
    } | (optional_filters or {})
    armies = [army for army in unit.get("armies", ()) if isinstance(army, dict)]
    unit["peripheral_types"] = [
        {"id": type_id, "label": _PERIPHERAL_TYPE_LABELS.get(type_id, str(type_id))}
        for type_id in unit.get("peripheral_type_ids", ())
    ]
    _annotate_peripheral_presentations(unit)
    for army in armies:
        army["availability_badges"] = [
            {
                "flag": flag,
                "label": {
                    "mercs": "Mercenary",
                    "specops": "Spec-Ops",
                    "teamops": "Team Operations",
                    "reinforcement": "Reinforcements",
                }[flag],
            }
            for flag in army.get("availability_flags", ())
            if flag in OPTIONAL_AVAILABILITY_FLAGS
        ]
        for profile in army.get("profiles", ()):
            profile["type_label"] = troop_type_label(profile.get("type"))
            profile["characteristic_presentations"] = [
                characteristic_presentation(characteristic)
                for characteristic in profile.get("characteristics", ())
            ]
    _annotate_composite_option_presentations(armies)

    for army in armies:
        army["presentation_requested"] = _army_requested(army, requested_army)
        army["presentation_visible"] = (
            _army_enabled(army, optional_filters) or army["presentation_requested"]
        )
    selected_armies = [army for army in armies if army["presentation_visible"]]
    profiles_by_identity: dict[str, dict[str, Any]] = {}
    profile_order: list[str] = []
    for army in selected_armies:
        for profile in army.get("profiles", ()):
            identity = str(profile.get("profile_identity") or "")
            if identity not in profiles_by_identity:
                profiles_by_identity[identity] = {
                    "display_name": str(
                        profile.get("display_name") or profile.get("name") or ""
                    ).strip(),
                    "profiles": [],
                    "contexts": [],
                    "reinforcement_flags": [],
                }
                profile_order.append(identity)
            profiles_by_identity[identity]["profiles"].append(profile)
            profiles_by_identity[identity]["contexts"].append(
                (army.get("id"), profile.get("group_id"))
            )
            profiles_by_identity[identity]["reinforcement_flags"].append(
                "reinforcement" in army.get("availability_flags", ())
            )

    general_profiles: list[dict[str, Any]] = []
    general_by_identity: dict[str, dict[str, Any]] = {}
    for identity in profile_order:
        group = profiles_by_identity[identity]
        matching_profiles = group["profiles"]
        context_keys = set(group["contexts"])
        matching_loadouts = [
            loadout
            for army in selected_armies
            for loadout in army.get("loadouts", ())
            if (army.get("id"), loadout.get("group_id")) in context_keys
        ]
        stats = _general_stats(matching_profiles)
        order_type = _general_order_type(matching_profiles, matching_loadouts)
        shared_items = {
            "skills": _general_profile_skills(matching_profiles, matching_loadouts),
            "equipment": _common_items(matching_profiles, "equipment"),
            "weapons": _common_items(matching_loadouts, "weapons"),
        }
        general = {
            "profile_identity": identity,
            "display_name": group["display_name"],
            "stats": stats,
            "order_type": order_type,
            "type": _most_common(matching_profiles, "type"),
            "classification": _most_common(matching_profiles, "classification"),
            "occurrence_count": len(matching_profiles),
            "reinforcement_only": all(group["reinforcement_flags"]),
            "symbol_path": next(
                (
                    profile.get("symbol_path")
                    for profile in matching_profiles
                    if profile.get("symbol_path")
                ),
                None,
            ),
            "shared_items": shared_items,
            "different_stat_labels": _stat_difference_labels(matching_profiles, stats),
            "symbol_descriptors": _symbol_descriptors(
                matching_profiles, matching_loadouts, order_type
            ),
        }
        general["type_label"] = troop_type_label(general["type"])
        general_profiles.append(general)
        general_by_identity[identity] = general

    _annotate_general_profile_visibility(general_profiles)
    unit["general_profiles"] = general_profiles

    for army in selected_armies:
        profiles_by_group: dict[Any, list[dict[str, Any]]] = {}
        loadouts_by_group: dict[Any, list[dict[str, Any]]] = {}
        for profile in army.get("profiles", ()):
            profiles_by_group.setdefault(profile.get("group_id"), []).append(profile)
            general = general_by_identity.get(str(profile.get("profile_identity") or ""))
            if general is None:
                continue
            profile["specific_items"] = {
                property_name: _without_shared(
                    profile.get(property_name, ()), general["shared_items"][property_name]
                )
                for property_name in ("skills", "equipment", "weapons")
            }
        for loadout in army.get("loadouts", ()):
            loadouts_by_group.setdefault(loadout.get("group_id"), []).append(loadout)
        for group_id, loadouts in loadouts_by_group.items():
            group_profiles = profiles_by_group.get(group_id, [])
            general_rows = [
                general_by_identity.get(str(profile.get("profile_identity") or ""))
                for profile in group_profiles
            ]
            general_rows = [general for general in general_rows if general is not None]
            shared_by_property = {
                property_name: _unique_items(
                    item
                    for general in general_rows
                    for item in general["shared_items"][property_name]
                )
                for property_name in ("skills", "equipment", "weapons")
            }
            general_order_type = general_rows[0]["order_type"] if general_rows else None
            for loadout in loadouts:
                loadout["specific_items"] = {
                    property_name: _without_shared(
                        loadout.get(property_name, ()), shared_by_property[property_name]
                    )
                    for property_name in ("skills", "equipment", "weapons")
                }
                loadout_order_type = _prominent_order_type([loadout])
                symbol_types: list[str] = []
                if loadout_order_type and loadout_order_type != general_order_type:
                    symbol_types.append(loadout_order_type)
                if _has_skill([loadout], "impetuous"):
                    symbol_types.append("impetuous")
                if _has_skill([loadout], "tactical awareness"):
                    symbol_types.append("tactical")
                symbol_types.extend(["lieutenant"] * _lieutenant_order_count([loadout]))
                loadout["symbol_descriptors"] = [
                    _symbol_descriptor(symbol_type) for symbol_type in symbol_types
                ]
    return unit
