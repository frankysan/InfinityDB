"""Supplemental Army source corrections."""

from __future__ import annotations

from .weapon_config import load_weapon_override_config

_SOURCE_CORRECTIONS = load_weapon_override_config()


def weapon_profile_override(weapon_id: int) -> str | None:
    """Return a maintained profile correction for incomplete Army source metadata."""

    return _SOURCE_CORRECTIONS.profile_overrides.get(weapon_id)


def weapon_name_override(weapon_id: int) -> str | None:
    """Return a corrected display name for a known Army source naming anomaly."""

    return _SOURCE_CORRECTIONS.name_overrides.get(weapon_id)
