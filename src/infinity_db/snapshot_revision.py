"""Shared identity for the runtime database pair and Weapon-profile publication."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256


def database_set_snapshot_revision(fingerprints: Mapping[str, str]) -> str:
    """Bind cache identity to sorted active filenames and exact database bytes."""
    if not fingerprints:
        raise ValueError("Runtime database fingerprints are required")
    value = json.dumps(sorted(fingerprints.items()), separators=(",", ":"), ensure_ascii=True)
    return sha256(b"InfinityDB runtime database set v1\x00" + value.encode("ascii")).hexdigest()


def runtime_snapshot_revision(
    army_sha256: str, rules_sha256: str | None, weapon_profile_sha256: str | None,
    *, army_filename: str = "army.db", rules_filename: str = "rules_n5.db",
) -> str:
    """Use named database hashes, with explicit sidecars only for low-level fixtures."""
    fingerprints = {army_filename: army_sha256}
    if rules_sha256 is not None:
        fingerprints[rules_filename] = rules_sha256
    if weapon_profile_sha256 is not None and weapon_profile_sha256 != rules_sha256:
        fingerprints["weapon-profile-sources.json"] = weapon_profile_sha256
    return database_set_snapshot_revision(fingerprints)
