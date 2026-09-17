"""Source-semantic availability classification for normalized Army data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

STANDARD_SOURCE_ROLE = "standard"
MERCENARY_SOURCE_ROLE = "mercenary_variant"
STANDARD_AVAILABILITY = "standard"
MERCENARY_AVAILABILITY = "mercenary"
MERCENARY_CANONICAL_FACTION_ID = 1
MERCENARY_SLUG_PREFIX = "merc-"


def annotate_availability_semantics(normalized: dict[str, Any]) -> None:
    """Annotate source unit roles and army occurrences from explicit source markers.

    Corvus Belli currently represents optional mercenary availability with a
    dedicated source-unit variant whose slug starts with ``merc-``, whose
    canonical faction is source ID 1, and whose declared faction list is empty.
    Ordinary records with canonical faction 1 and declared faction memberships
    remain standard source records.

    The common 10,000-offset source-ID pattern is deliberately not used here;
    numeric IDs are provenance/matching evidence, not the availability rule.
    """
    tables = normalized.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Normalized data must contain a tables object")

    faction_ids_by_unit: dict[int, set[int]] = defaultdict(set)
    for membership in tables.get("unit_factions", []):
        unit_id = membership.get("unit_id")
        faction_id = membership.get("faction_id")
        if isinstance(unit_id, int) and isinstance(faction_id, int):
            faction_ids_by_unit[unit_id].add(faction_id)

    source_roles: dict[int, str | None] = {}
    for unit in tables.get("units", []):
        unit_id = unit.get("id")
        if not isinstance(unit_id, int):
            raise ValueError("Normalized unit rows need integer IDs before availability annotation")
        if unit.get("source_defined") is False:
            unit["source_role"] = None
            source_roles[unit_id] = None
            continue

        canonical_faction_id = unit.get("canonical_faction_id")
        slug = unit.get("slug")
        faction_ids = faction_ids_by_unit[unit_id]
        has_mercenary_slug = isinstance(slug, str) and slug.startswith(MERCENARY_SLUG_PREFIX)

        if has_mercenary_slug:
            if canonical_faction_id != MERCENARY_CANONICAL_FACTION_ID:
                raise ValueError(
                    f"Unit {unit_id} uses mercenary slug {slug!r} but canonical faction is "
                    f"{canonical_faction_id!r}; expected {MERCENARY_CANONICAL_FACTION_ID}"
                )
            if faction_ids:
                raise ValueError(
                    f"Unit {unit_id} uses mercenary slug {slug!r} but declares normal faction "
                    f"memberships {sorted(faction_ids)!r}"
                )
            role = MERCENARY_SOURCE_ROLE
        else:
            if canonical_faction_id == MERCENARY_CANONICAL_FACTION_ID and not faction_ids:
                raise ValueError(
                    f"Unit {unit_id} has canonical faction {MERCENARY_CANONICAL_FACTION_ID} and "
                    "no declared faction memberships but does not use the expected mercenary "
                    f"slug prefix {MERCENARY_SLUG_PREFIX!r}; source contract may have changed"
                )
            role = STANDARD_SOURCE_ROLE

        unit["source_role"] = role
        source_roles[unit_id] = role

    for occurrence in tables.get("army_units", []):
        unit_id = occurrence.get("unit_id")
        role = source_roles.get(unit_id)
        if role is None:
            raise ValueError(
                f"Army-unit occurrence references unit {unit_id!r} without a source-defined role"
            )
        occurrence["availability_kind"] = (
            MERCENARY_AVAILABILITY if role == MERCENARY_SOURCE_ROLE else STANDARD_AVAILABILITY
        )
