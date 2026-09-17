"""Build-time materialization of application logical-unit identity."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from infinity_army_data.availability import (
    GENERIC_MATCH_METHOD,
    GENERIC_UNIT_MATCHES_KEY,
    MERCENARY_MATCH_METHOD,
    MERCENARY_SOURCE_ROLE,
    MERCENARY_UNIT_MATCHES_KEY,
    STANDARD_SOURCE_ROLE,
    UNMATCHED_MERCENARY_UNIT_IDS_KEY,
)

from ..identities import IdentityConfig, unit_match_identities


@dataclass(frozen=True)
class LogicalUnitResolution:
    """Resolved frontend identity rows plus persisted reinforcement evidence."""

    logical_units: tuple[dict[str, int], ...]
    logical_unit_sources: tuple[dict[str, int], ...]
    reinforcement_matches: Mapping[int, int]


class _DisjointSet:
    def __init__(self, values: set[int]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: int) -> int:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, first: int, second: int) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root == second_root:
            return
        if first_root < second_root:
            self.parent[second_root] = first_root
        else:
            self.parent[first_root] = second_root


def _source_units(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        row["id"]: row
        for row in data["tables"].get("units", [])
        if row.get("source_defined") is True and isinstance(row.get("id"), int)
    }


def _reinforcement_source_ids(
    data: dict[str, Any], units: Mapping[int, dict[str, Any]]
) -> set[int]:
    army_kinds = {
        row.get("id"): row.get("kind")
        for row in data["tables"].get("army_lists", [])
        if isinstance(row.get("id"), int)
    }
    memberships: dict[int, list[int]] = {unit_id: [] for unit_id in units}
    for row in data["tables"].get("army_units", []):
        unit_id = row.get("unit_id")
        army_id = row.get("army_id")
        if unit_id in memberships and isinstance(army_id, int):
            memberships[unit_id].append(army_id)
    return {
        unit_id
        for unit_id, army_ids in memberships.items()
        if army_ids and all(army_kinds.get(army_id) == "reinforcement" for army_id in army_ids)
    }


def _generic_matches(
    data: dict[str, Any], units: Mapping[int, dict[str, Any]]
) -> dict[int, int] | None:
    raw_matches = data.get(GENERIC_UNIT_MATCHES_KEY)
    if raw_matches is None:
        return None
    if not isinstance(raw_matches, list):
        raise ValueError("Normalized data has invalid generic unit identity metadata")

    matches: dict[int, int] = {}
    for item in raw_matches:
        if not isinstance(item, dict) or set(item) != {
            "sourceUnitId",
            "representativeUnitId",
            "method",
        }:
            raise ValueError("Normalized data has invalid generic unit identity metadata")
        source_id = item["sourceUnitId"]
        representative_id = item["representativeUnitId"]
        if (
            type(source_id) is not int
            or source_id <= 0
            or type(representative_id) is not int
            or representative_id <= 0
            or source_id == representative_id
            or item["method"] != GENERIC_MATCH_METHOD
            or source_id in matches
        ):
            raise ValueError("Normalized data has invalid generic unit identity metadata")
        matches[source_id] = representative_id

    if set(matches) & set(matches.values()):
        raise ValueError("Normalized generic unit identity metadata contains chained matches")
    if any(
        units.get(source_id, {}).get("source_role") != STANDARD_SOURCE_ROLE
        or units.get(representative_id, {}).get("source_role") != STANDARD_SOURCE_ROLE
        for source_id, representative_id in matches.items()
    ):
        raise ValueError(
            "Normalized generic unit identity metadata references invalid source roles"
        )
    return matches


def _mercenary_identity(
    data: dict[str, Any], units: Mapping[int, dict[str, Any]]
) -> tuple[dict[int, int], frozenset[int]] | None:
    has_matches = MERCENARY_UNIT_MATCHES_KEY in data
    has_unmatched = UNMATCHED_MERCENARY_UNIT_IDS_KEY in data
    if not has_matches and not has_unmatched:
        return None
    if has_matches != has_unmatched:
        raise ValueError("Normalized data has incomplete mercenary identity metadata")

    raw_matches = data[MERCENARY_UNIT_MATCHES_KEY]
    raw_unmatched = data[UNMATCHED_MERCENARY_UNIT_IDS_KEY]
    if not isinstance(raw_matches, list) or not isinstance(raw_unmatched, list):
        raise ValueError("Normalized data has invalid mercenary identity metadata")

    matches: dict[int, int] = {}
    for item in raw_matches:
        if not isinstance(item, dict) or set(item) != {
            "mercenaryUnitId",
            "standardUnitId",
            "method",
        }:
            raise ValueError("Normalized data has invalid mercenary identity metadata")
        mercenary_id = item["mercenaryUnitId"]
        standard_id = item["standardUnitId"]
        if (
            type(mercenary_id) is not int
            or mercenary_id <= 0
            or type(standard_id) is not int
            or standard_id <= 0
            or item["method"] != MERCENARY_MATCH_METHOD
            or mercenary_id in matches
        ):
            raise ValueError("Normalized data has invalid mercenary identity metadata")
        matches[mercenary_id] = standard_id

    unmatched: set[int] = set()
    for unit_id in raw_unmatched:
        if type(unit_id) is not int or unit_id <= 0 or unit_id in unmatched:
            raise ValueError("Normalized data has invalid mercenary identity metadata")
        unmatched.add(unit_id)
    if set(matches) & unmatched:
        raise ValueError("Normalized data has conflicting mercenary identity metadata")

    mercenary_ids = {
        unit_id
        for unit_id, unit in units.items()
        if unit.get("source_role") == MERCENARY_SOURCE_ROLE
    }
    if mercenary_ids != set(matches) | unmatched:
        raise ValueError(
            "Normalized mercenary identity metadata does not cover every mercenary source unit"
        )
    if any(
        units.get(mercenary_id, {}).get("source_role") != MERCENARY_SOURCE_ROLE
        or units.get(standard_id, {}).get("source_role") != STANDARD_SOURCE_ROLE
        for mercenary_id, standard_id in matches.items()
    ):
        raise ValueError(
            "Normalized mercenary identity metadata references invalid source roles"
        )
    return matches, frozenset(unmatched)


def reinforcement_unit_matches(
    data: dict[str, Any], identity_config: IdentityConfig
) -> dict[int, int]:
    """Audit unambiguous reinforcement-only source units against standard groups."""
    units = _source_units(data)
    reinforcement_ids = _reinforcement_source_ids(data, units)
    generic_matches = _generic_matches(data, units)

    def standard_group_key(unit_id: int) -> tuple[object, ...]:
        if unit_id in identity_config.unit_aliases:
            return ("configured", identity_config.canonical_unit_id(unit_id))
        if generic_matches is not None:
            return ("persisted", generic_matches.get(unit_id, unit_id))
        unit = units[unit_id]
        label = unit.get("isc") or unit.get("name") or ""
        return ("legacy", unit_id % 10_000, str(label).casefold())

    standard_groups: dict[tuple[object, ...], list[int]] = {}
    for unit_id, unit in sorted(units.items()):
        if unit_id in reinforcement_ids or unit.get("source_role") == MERCENARY_SOURCE_ROLE:
            continue
        standard_groups.setdefault(standard_group_key(unit_id), []).append(unit_id)

    identities_by_group: dict[tuple[object, ...], set[str]] = {}
    representative_by_group: dict[tuple[object, ...], int] = {}
    for key, source_ids in standard_groups.items():
        representative_by_group[key] = min(source_ids)
        identities = identities_by_group.setdefault(key, set())
        for source_id in source_ids:
            identities.update(unit_match_identities(units[source_id], identity_config))

    reinforcement_groups: dict[str, list[int]] = {}
    reinforcement_identities: dict[str, set[str]] = {}
    for reinforcement_id in sorted(reinforcement_ids):
        identities = unit_match_identities(units[reinforcement_id], identity_config)
        base_identity = min(identities, default="")
        reinforcement_groups.setdefault(base_identity, []).append(reinforcement_id)
        reinforcement_identities.setdefault(base_identity, set()).update(identities)

    matches: dict[int, int] = {}
    for base_identity, source_ids in reinforcement_groups.items():
        identities = reinforcement_identities[base_identity]
        candidates = [
            key
            for key, standard_identities in identities_by_group.items()
            if identities & standard_identities
        ]
        if len(candidates) == 1:
            standard_id = representative_by_group[candidates[0]]
            matches.update({source_id: standard_id for source_id in source_ids})
    return matches


def _legacy_duplicate_groups(
    units: Mapping[int, dict[str, Any]],
    *,
    excluded_ids: set[int],
) -> list[list[int]]:
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for unit_id, unit in units.items():
        if unit_id in excluded_ids:
            continue
        label = unit.get("isc") or unit.get("name")
        if not isinstance(label, str) or not label:
            continue
        groups[(unit_id % 10_000, label.casefold())].append(unit_id)
    return [source_ids for source_ids in groups.values() if len(source_ids) > 1]


def resolve_logical_unit_identity(
    data: dict[str, Any],
    identity_config: IdentityConfig,
    *,
    reinforcement_matches: Mapping[int, int] | None = None,
) -> LogicalUnitResolution:
    """Resolve every source-defined unit to one materialized application identity."""
    units = _source_units(data)
    source_ids = set(units)
    generic_matches = _generic_matches(data, units)
    mercenary_identity = _mercenary_identity(data, units)
    reinforcement_ids = _reinforcement_source_ids(data, units)
    resolved_reinforcement_matches = dict(
        reinforcement_matches
        if reinforcement_matches is not None
        else reinforcement_unit_matches(data, identity_config)
    )

    if any(
        source_id not in reinforcement_ids
        or standard_id not in units
        or standard_id in reinforcement_ids
        or units[standard_id].get("source_role") == MERCENARY_SOURCE_ROLE
        for source_id, standard_id in resolved_reinforcement_matches.items()
    ):
        raise ValueError("Reinforcement identity mapping references invalid source units")

    mercenary_matches: dict[int, int] = {}
    unmatched_mercenary_ids: frozenset[int] = frozenset()
    mercenary_contract_present = mercenary_identity is not None
    if mercenary_identity is not None:
        mercenary_matches, unmatched_mercenary_ids = mercenary_identity

    unmatched_reinforcement_ids = reinforcement_ids - set(resolved_reinforcement_matches)
    blocked_ids = set(unmatched_mercenary_ids) | unmatched_reinforcement_ids

    sets = _DisjointSet(source_ids)

    alias_groups: dict[int, list[int]] = defaultdict(list)
    for source_id, canonical_id in identity_config.unit_aliases.items():
        if source_id in units and source_id not in blocked_ids:
            alias_groups[canonical_id].append(source_id)
    for members in alias_groups.values():
        for source_id in members[1:]:
            sets.union(members[0], source_id)

    if generic_matches is not None:
        for source_id, representative_id in generic_matches.items():
            sets.union(source_id, representative_id)
    else:
        legacy_excluded = set(reinforcement_ids) | set(identity_config.unit_aliases)
        if mercenary_contract_present:
            legacy_excluded.update(
                unit_id
                for unit_id, unit in units.items()
                if unit.get("source_role") == MERCENARY_SOURCE_ROLE
            )
        for members in _legacy_duplicate_groups(units, excluded_ids=legacy_excluded):
            for source_id in members[1:]:
                sets.union(members[0], source_id)

    for mercenary_id, standard_id in mercenary_matches.items():
        sets.union(mercenary_id, standard_id)
    for reinforcement_id, standard_id in resolved_reinforcement_matches.items():
        sets.union(reinforcement_id, standard_id)

    components: dict[int, set[int]] = defaultdict(set)
    for source_id in sorted(source_ids):
        components[sets.find(source_id)].add(source_id)

    logical_units: list[dict[str, int]] = []
    logical_unit_sources: list[dict[str, int]] = []
    used_representatives: set[int] = set()
    generic_representatives = (
        set(generic_matches.values()) if generic_matches is not None else set()
    )

    for members in components.values():
        configured_canonicals = {
            identity_config.unit_aliases[source_id]
            for source_id in members
            if source_id in identity_config.unit_aliases
            and identity_config.unit_aliases[source_id] in members
        }
        if len(configured_canonicals) > 1:
            raise ValueError(
                "Logical unit identity evidence connects multiple configured canonical unit IDs: "
                + ", ".join(map(str, sorted(configured_canonicals)))
            )

        ordinary = sorted(
            source_id
            for source_id in members
            if source_id not in reinforcement_ids
            and units[source_id].get("source_role") != MERCENARY_SOURCE_ROLE
        )
        if configured_canonicals:
            representative_id = next(iter(configured_canonicals))
        else:
            persisted_representatives = sorted(generic_representatives & members)
            if len(persisted_representatives) > 1:
                raise ValueError(
                    "Logical unit identity evidence connects multiple persisted representatives: "
                    + ", ".join(map(str, persisted_representatives))
                )
            if persisted_representatives:
                representative_id = persisted_representatives[0]
            elif ordinary:
                representative_id = ordinary[0]
            else:
                representative_id = min(members)

        if representative_id not in members or representative_id in used_representatives:
            raise ValueError("Logical unit identity resolution produced an invalid representative")
        used_representatives.add(representative_id)
        logical_units.append(
            {"id": representative_id, "representative_unit_id": representative_id}
        )
        logical_unit_sources.extend(
            {"source_unit_id": source_id, "logical_unit_id": representative_id}
            for source_id in sorted(members)
        )

    mapped_sources = {row["source_unit_id"] for row in logical_unit_sources}
    if mapped_sources != source_ids or len(logical_unit_sources) != len(source_ids):
        raise ValueError("Every source-defined unit must resolve to exactly one logical unit")

    logical_units.sort(key=lambda row: row["id"])
    logical_unit_sources.sort(key=lambda row: row["source_unit_id"])
    return LogicalUnitResolution(
        logical_units=tuple(logical_units),
        logical_unit_sources=tuple(logical_unit_sources),
        reinforcement_matches=dict(sorted(resolved_reinforcement_matches.items())),
    )
