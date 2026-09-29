"""Validated maintained identities for historical Armies absent from current Army data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_curated_path

LEGACY_ARMY_FORMAT = "InfinityDB curated legacy armies"
LEGACY_ARMY_FORMAT_VERSION = 1
DEFAULT_LEGACY_ARMIES = maintained_curated_path("identities", "legacy-armies.json")
_ALLOWED_ROLES = frozenset({"main", "sectorial", "non_aligned"})


class LegacyArmyError(ValueError):
    """Raised when maintained legacy-Army data is invalid."""


@dataclass(frozen=True)
class LegacyArmy:
    """One historical Army identity intentionally retained for player-facing reference."""

    id: int
    name: str
    slug: str
    role: str
    group_id: int | None
    group_name: str | None
    group_slug: str | None
    logo: str
    reason: str

    def as_api_item(self) -> dict[str, Any]:
        """Return the application-facing shape shared with current Army rows."""

        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "kind": "legacy",
            "role": self.role,
            "playable": False,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "group_slug": self.group_slug,
            "parent_army_ids": [],
            "parent_armies": [],
            "reinforcement_sections": [],
            "unit_count": None,
            "discontinued": False,
            "out_of_catalog": False,
            "legacy": True,
        }


def _nonempty_string(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LegacyArmyError(f"{context} must be a non-empty string")
    return value.strip()


def parse_legacy_armies(document: object) -> tuple[LegacyArmy, ...]:
    """Validate and compile maintained historical Army identities."""

    if not isinstance(document, dict):
        raise LegacyArmyError("legacy Army data must be an object")
    if set(document) != {"format", "formatVersion", "armies"}:
        raise LegacyArmyError("legacy Army data must contain format, formatVersion, and armies")
    if document.get("format") != LEGACY_ARMY_FORMAT:
        raise LegacyArmyError(f"legacy Army data must declare format {LEGACY_ARMY_FORMAT!r}")
    if document.get("formatVersion") != LEGACY_ARMY_FORMAT_VERSION:
        raise LegacyArmyError(
            f"legacy Army data formatVersion must be {LEGACY_ARMY_FORMAT_VERSION}"
        )

    rows = document.get("armies")
    if not isinstance(rows, list):
        raise LegacyArmyError("legacy Army data.armies must be an array")

    result: list[LegacyArmy] = []
    ids: set[int] = set()
    slugs: set[str] = set()
    for index, row in enumerate(rows):
        context = f"legacy Army data.armies[{index}]"
        if not isinstance(row, dict):
            raise LegacyArmyError(f"{context} must be an object")
        expected = {
            "id",
            "name",
            "slug",
            "role",
            "groupId",
            "groupName",
            "groupSlug",
            "logo",
            "reason",
        }
        if set(row) != expected:
            raise LegacyArmyError(f"{context} must contain exactly {sorted(expected)!r}")

        army_id = row.get("id")
        if type(army_id) is not int or army_id <= 0:
            raise LegacyArmyError(f"{context}.id must be a positive integer")
        if army_id in ids:
            raise LegacyArmyError(f"{context}.id is duplicated: {army_id}")
        ids.add(army_id)

        slug = _nonempty_string(row.get("slug"), context=f"{context}.slug")
        if slug in slugs:
            raise LegacyArmyError(f"{context}.slug is duplicated: {slug!r}")
        slugs.add(slug)

        role = _nonempty_string(row.get("role"), context=f"{context}.role")
        if role not in _ALLOWED_ROLES:
            raise LegacyArmyError(
                f"{context}.role must be one of {sorted(_ALLOWED_ROLES)!r}"
            )
        group_id = row.get("groupId")
        if group_id is not None and (type(group_id) is not int or group_id <= 0):
            raise LegacyArmyError(f"{context}.groupId must be a positive integer or null")
        group_name = row.get("groupName")
        group_slug = row.get("groupSlug")
        if role in {"sectorial", "non_aligned"}:
            if group_id is None:
                raise LegacyArmyError(f"{context}.groupId is required for role {role!r}")
            group_name = _nonempty_string(group_name, context=f"{context}.groupName")
            group_slug = _nonempty_string(group_slug, context=f"{context}.groupSlug")
        elif group_id is not None or group_name is not None or group_slug is not None:
            raise LegacyArmyError(
                f"{context}.groupId, groupName, and groupSlug must be null for a main Army"
            )

        logo = _nonempty_string(row.get("logo"), context=f"{context}.logo")
        if not logo.startswith("https://assets.corvusbelli.net/army/img/") or not logo.endswith(
            ".svg"
        ):
            raise LegacyArmyError(f"{context}.logo must be a Corvus Belli Army SVG URL")

        result.append(
            LegacyArmy(
                id=army_id,
                name=_nonempty_string(row.get("name"), context=f"{context}.name"),
                slug=slug,
                role=role,
                group_id=group_id,
                group_name=group_name,
                group_slug=group_slug,
                logo=logo,
                reason=_nonempty_string(row.get("reason"), context=f"{context}.reason"),
            )
        )
    return tuple(sorted(result, key=lambda army: army.id))


def load_legacy_armies(path: Path = DEFAULT_LEGACY_ARMIES) -> tuple[LegacyArmy, ...]:
    """Load the maintained historical Army identity file."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LegacyArmyError(f"Could not load legacy Army data {path}: {exc}") from exc
    return parse_legacy_armies(document)
