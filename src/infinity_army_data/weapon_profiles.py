"""Supplemental corrections for incomplete or inconsistent Army weapon metadata."""

from __future__ import annotations

from typing import Any

# Keep source omissions explicit and easy to update as new snapshots are imported.
WEAPON_PROFILE_OVERRIDES: dict[int, str] = {
    62: "ARM=0, BTS=0, STR=1, S=1",  # Monofilament Mine
    63: "ARM=0, BTS=0, STR=1, S=1",  # Viral Mine
    196: "ARM=0, BTS=0, STR=1, S=1",  # Shock Mine
    197: "ARM=0, BTS=0, STR=1, S=1",  # E/M Mine
    199: "ARM=0, BTS=0, STR=1, S=1",  # AP Mine
    220: "ARM=0, BTS=0, STR=1, S=1",  # PARA Mine
}

# Keep source naming anomalies explicit, so regenerated catalogs retain the
# conventional display name used by the rest of the weapon list.
WEAPON_NAME_OVERRIDES: dict[int, str] = {
    217: "MULTI Spitfire",
}


def weapon_profile_override(weapon_id: int) -> str | None:
    """Return a manually maintained profile for a weapon missing one at source."""
    return WEAPON_PROFILE_OVERRIDES.get(weapon_id)


def weapon_name_override(weapon_id: int) -> str | None:
    """Return a corrected display name for a known source naming anomaly."""
    return WEAPON_NAME_OVERRIDES.get(weapon_id)


# Some weapons act as a battlefield model and have rules data outside the Army
# weapon catalog. Keep these exceptional profiles declarative and local.
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
