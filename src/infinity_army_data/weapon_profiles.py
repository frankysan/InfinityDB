"""Supplemental Army source corrections and special weapon rules data."""

from __future__ import annotations

from typing import Any

from .weapon_config import load_weapon_override_config

_SOURCE_CORRECTIONS = load_weapon_override_config()


def weapon_profile_override(weapon_id: int) -> str | None:
    """Return a maintained profile correction for incomplete Army source metadata."""

    return _SOURCE_CORRECTIONS.profile_overrides.get(weapon_id)


def weapon_name_override(weapon_id: int) -> str | None:
    """Return a corrected display name for a known Army source naming anomaly."""

    return _SOURCE_CORRECTIONS.name_overrides.get(weapon_id)


# Some weapons act as a battlefield model and have rules data outside the Army
# weapon catalog. These are game-rule facts rather than source corrections and
# remain here until they move into cited curated rules data.
SPECIAL_WEAPON_DETAILS: dict[int, dict[str, Any]] = {
    226: {
        "stats": [
            ["MOV", "--"],
            ["CC", "5"],
            ["BS", "10"],
            ["PH", "--"],
            ["WIP", "--"],
            ["ARM", "2"],
            ["BTS", "3"],
            ["STR", "1"],
            ["S", "2"],
        ],
        "equipment": ["360º Visor"],
        "skills": ["Total Reaction"],
        "cc_weapon": "PARA CC Weapon (-3)",
    },
}


def special_weapon_detail(weapon_id: int) -> dict[str, Any] | None:
    """Return supplemental pseudo-unit information for a special weapon."""

    return SPECIAL_WEAPON_DETAILS.get(weapon_id)
