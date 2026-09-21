"""Supplemental Army source corrections."""

from __future__ import annotations

from .weapon_config import WeaponOverrideConfig, load_weapon_override_config

_SOURCE_CORRECTIONS = load_weapon_override_config()


def weapon_profile_override(
    weapon_id: int, *, config: WeaponOverrideConfig = _SOURCE_CORRECTIONS
) -> str | None:
    """Return a maintained profile correction for incomplete Army source metadata."""

    return config.profile_overrides.get(weapon_id)


def weapon_name_override(
    weapon_id: int, *, config: WeaponOverrideConfig = _SOURCE_CORRECTIONS
) -> str | None:
    """Return a corrected display name for a known Army source naming anomaly."""

    return config.name_overrides.get(weapon_id)


def weapon_metadata_profile_suppressed(
    weapon_id: int,
    name: object,
    mode: object,
    *,
    config: WeaponOverrideConfig = _SOURCE_CORRECTIONS,
) -> bool:
    """Whether one Army metadata weapon row is configured as non-display metadata."""

    suppressions = config.metadata_profile_suppressions.get(weapon_id, ())
    source_name = str(name or "").strip()
    source_mode = None if mode is None else str(mode).strip()
    return any(
        suppression.name == source_name and suppression.mode == source_mode
        for suppression in suppressions
    )
