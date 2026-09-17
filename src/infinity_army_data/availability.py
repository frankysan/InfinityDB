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
GENERIC_MATCH_METHOD = "generic_duplicate_key"
GENERIC_UNIT_MATCHES_KEY = "genericUnitMatches"
MERCENARY_MATCH_METHOD = GENERIC_MATCH_METHOD
MERCENARY_UNIT_MATCHES_KEY = "mercenaryUnitMatches"
UNMATCHED_MERCENARY_UNIT_IDS_KEY = "unmatchedMercenaryUnitIds"

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

        # Canonical faction 1 is mercenary source/origin provenance, not an
        # application army/group identity.  Without this exception the generic
        # xx01 resolver would turn it into main_army_id=1 after removal of the
        # legacy 1 -> 901 override.
        if canonical_faction_id == MERCENARY_CANONICAL_FACTION_ID:
            unit["main_army_id"] = None

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

def _generic_duplicate_key(unit: dict[str, Any]) -> tuple[int, str] | None:
    """Return the common source duplicate key used as mercenary matching evidence."""
    unit_id = unit.get("id")
    label = unit.get("isc") or unit.get("name")
    if not isinstance(unit_id, int) or not isinstance(label, str) or not label:
        return None
    return unit_id % 10_000, label.casefold()

def audit_generic_logical_matches(normalized: dict[str, Any]) -> dict[int, int]:
    """Audit and persist generic duplicate source-unit matches.

    The common 10,000-family source-ID relationship is only matching evidence:
    candidates must also share the same ISC/display-name identity.  Mercenary
    variants are excluded because their source-semantic mapping is audited
    separately, and reinforcement-only records remain a separate repository
    matching concern.

    The persisted ``genericUnitMatches`` list is authoritative when present.
    An empty list therefore means that normalization found no generic duplicate
    groups and current repositories must not rediscover any through ID
    arithmetic. Older databases that lack the key retain the legacy fallback.
    """
    tables = normalized.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Normalized data must contain a tables object")

    army_kinds = {
        row.get("id"): row.get("kind")
        for row in tables.get("army_lists", [])
        if isinstance(row.get("id"), int)
    }
    occurrence_armies: dict[int, list[int]] = defaultdict(list)
    for occurrence in tables.get("army_units", []):
        unit_id = occurrence.get("unit_id")
        army_id = occurrence.get("army_id")
        if isinstance(unit_id, int) and isinstance(army_id, int):
            occurrence_armies[unit_id].append(army_id)

    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for unit in tables.get("units", []):
        unit_id = unit.get("id")
        if not isinstance(unit_id, int) or unit.get("source_defined") is False:
            continue
        if unit.get("source_role") != STANDARD_SOURCE_ROLE:
            continue
        armies = occurrence_armies.get(unit_id, ())
        reinforcement_only = bool(armies) and all(
            army_kinds.get(army_id) == "reinforcement" for army_id in armies
        )
        if reinforcement_only:
            continue
        key = _generic_duplicate_key(unit)
        if key is not None:
            groups[key].append(unit_id)

    matches: dict[int, int] = {}
    for source_ids in groups.values():
        if len(source_ids) < 2:
            continue
        representative_id = min(source_ids)
        for source_id in source_ids:
            if source_id != representative_id:
                matches[source_id] = representative_id

    normalized[GENERIC_UNIT_MATCHES_KEY] = [
        {
            "sourceUnitId": source_id,
            "representativeUnitId": representative_id,
            "method": GENERIC_MATCH_METHOD,
        }
        for source_id, representative_id in sorted(matches.items())
    ]
    return matches

def audit_mercenary_logical_matches(
    normalized: dict[str, Any],
) -> tuple[dict[int, int], tuple[int, ...]]:
    """Audit and persist mercenary-variant matches to standard source records.

    This intentionally uses the common 10,000-family ID relationship only as a
    candidate key and also requires the same ISC/display-name identity used by
    the current generic duplicate grouping. Classification remains entirely
    source-semantic. Unmatched variants are reported rather than rejected because
    a future mercenary-only source record could still be valid source data.

    The audit result is persisted as top-level normalized provenance in
    ``mercenaryUnitMatches`` and ``unmatchedMercenaryUnitIds``. Each match records
    the mercenary source ID, the lowest standard source ID in the matching
    generic duplicate group, and the matching method. This does not collapse or
    rewrite any normalized source row.

    Returns ``(matches, unmatched)`` where ``matches`` maps mercenary source IDs
    to the lowest standard source ID in the matching generic duplicate group.
    """
    tables = normalized.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Normalized data must contain a tables object")

    standard_groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    mercenary_units: list[dict[str, Any]] = []
    for unit in tables.get("units", []):
        role = unit.get("source_role")
        if role == STANDARD_SOURCE_ROLE:
            key = _generic_duplicate_key(unit)
            if key is not None:
                standard_groups[key].append(unit["id"])
        elif role == MERCENARY_SOURCE_ROLE:
            mercenary_units.append(unit)

    matches: dict[int, int] = {}
    unmatched: list[int] = []
    for unit in mercenary_units:
        unit_id = unit["id"]
        key = _generic_duplicate_key(unit)
        candidates = standard_groups.get(key, ()) if key is not None else ()
        if candidates:
            matches[unit_id] = min(candidates)
        else:
            unmatched.append(unit_id)

    unmatched_ids = tuple(sorted(unmatched))
    normalized[MERCENARY_UNIT_MATCHES_KEY] = [
        {
            "mercenaryUnitId": mercenary_unit_id,
            "standardUnitId": standard_unit_id,
            "method": MERCENARY_MATCH_METHOD,
        }
        for mercenary_unit_id, standard_unit_id in sorted(matches.items())
    ]
    normalized[UNMATCHED_MERCENARY_UNIT_IDS_KEY] = list(unmatched_ids)

    return matches, unmatched_ids
