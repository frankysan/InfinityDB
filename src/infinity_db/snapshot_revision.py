"""Shared identity for the runtime database pair and Weapon-profile publication."""

from __future__ import annotations

from hashlib import sha256


def runtime_snapshot_revision(
    army_sha256: str, rules_sha256: str | None, weapon_profile_sha256: str | None,
) -> str:
    """Combine the exact runtime artifact fingerprints, including absent publications."""
    parts = (
        army_sha256,
        rules_sha256 if rules_sha256 is not None else "none",
        weapon_profile_sha256 if weapon_profile_sha256 is not None else "none",
    )
    return sha256(":".join(parts).encode("ascii")).hexdigest()
