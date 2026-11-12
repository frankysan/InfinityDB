"""Shared identity and file-digest helpers for offline Weapon source audits.

These functions identify source rows; they do not imply a curated Weapon
definition, resolve an ambiguous mode, or authorize game-data changes.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path


def weapon_identity(value: str) -> str:
    """Match source/Army Weapon names using the existing NFKC policy."""
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKC", value).casefold())


def weapon_mode_identity(mode: str) -> str:
    """Normalize only the reviewed Anti-Material/Anti-Materiel mode variant."""
    return weapon_identity(mode).replace("antimaterial", "antimateriel")


def printed_name_and_mode(name: str) -> tuple[str, str]:
    """Keep the printed identity separate from an explicit parenthesized mode."""
    match = re.fullmatch(r"(.+?)\s*\(([^()]*)\s+Mode\)", name, re.IGNORECASE)
    if match is None:
        return name, ""
    return match.group(1).strip(), match.group(2).strip() + " Mode"


def source_file_sha256(path: Path) -> str:
    """Hash source bytes without normalizing archive or PDF contents."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
