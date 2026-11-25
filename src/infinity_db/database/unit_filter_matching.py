"""Scope-aware Unit Explorer matching and prospective option counts.

The evaluator is independent of SQL and operates on source-supported contexts.
Every property is kept with its owner until the requested scope aggregates it.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

Token = tuple[str, int | str]
CATEGORIES = ("skills", "equipment", "weapons", "troop_types", "classifications", "characteristics")


@dataclass(frozen=True)
class MatchContext:
    logical_id: int
    source_unit_id: int
    source_army_id: int
    group_id: int
    option_id: int | None
    profile_id: int | None
    properties: frozenset[Token]
    ava_values: tuple[int, ...] = ()
    points: int | None = None
    swc: str | None = None


def matches_selected(
    properties: frozenset[Token],
    selected: Mapping[str, tuple[frozenset[Token], ...]],
    and_categories: frozenset[str],
    *,
    excluding: str | None = None,
) -> bool:
    """True when the provided source-owned properties satisfy all selections."""
    for category, choices in selected.items():
        if category == excluding or not choices:
            continue
        checks = (not properties.isdisjoint(choice) for choice in choices)
        if not (all(checks) if category in and_categories else any(checks)):
            return False
    return True


def evaluate(
    contexts: Iterable[MatchContext],
    selected: Mapping[str, tuple[frozenset[Token], ...]],
    and_categories: frozenset[str],
    scope: str,
) -> tuple[dict[int, frozenset[tuple[int, int, int]]], dict[str, dict[str, int]]]:
    """Evaluate results and adding each option in one pass, counting logical Units.

    Selected choices always show the current matching total. For unselected AND
    options, only currently compatible contexts contribute. OR additions can
    rescue a Unit that does not match the current category, but not one failing
    another category. These are *prospective* counts, not raw usage counts.
    """
    if scope not in {"profile", "loadout", "unit"}:
        raise ValueError("Invalid matching scope")
    grouped: dict[int, list[MatchContext]] = defaultdict(list)
    for context in contexts:
        grouped[context.logical_id].append(context)

    matches: dict[int, frozenset[tuple[int, int, int]]] = {}
    additions: dict[str, dict[str, int]] = {category: defaultdict(int) for category in CATEGORIES}
    or_base = defaultdict(int)
    active = [
        (category, choices, category in and_categories)
        for category, choices in selected.items() if choices
    ]
    active_or = {
        category for category, _, is_and in active if not is_and and category in CATEGORIES
    }
    # Many source occurrences share identical properties. Cache the outcome
    # only for this query; never merge occurrence identities or numeric facts.
    outcomes: dict[frozenset[Token], str | None] = {}

    def classify(properties: frozenset[Token]) -> str | None:
        # None: matches all categories; one category: rescuable OR failure;
        # empty string: no single added option can rescue this context.
        if properties not in outcomes:
            failed = None
            for category, choices, is_and in active:
                checks = (not properties.isdisjoint(choice) for choice in choices)
                matched = all(checks) if is_and else any(checks)
                if matched:
                    continue
                if is_and or failed is not None or category not in active_or:
                    failed = ""
                    break
                failed = category
            outcomes[properties] = failed
        return outcomes[properties]

    for logical_id, candidates in grouped.items():
        if scope == "unit":
            # Only already-eligible occurrences of this logical Unit contribute.
            union = frozenset().union(*(candidate.properties for candidate in candidates))
            considered = [MatchContext(logical_id, 0, 0, 0, None, None, union)]
        else:
            considered = candidates

        matching_properties: set[Token] = set()
        rescued: dict[str, set[str]] = defaultdict(set)
        matching_occurrences: set[tuple[int, int, int]] = set()
        for candidate in considered:
            failure = classify(candidate.properties)
            if failure is None:
                matching_properties.update(candidate.properties)
                matching_occurrences.add((
                    candidate.source_unit_id, candidate.source_army_id, candidate.group_id,
                ))
            elif failure:
                # Only this failed OR category could be rescued by an addition.
                for name, value in candidate.properties:
                    if name == failure:
                        rescued[failure].add(str(value))
                    elif failure == "equipment" and name == "equipment_characteristics":
                        rescued[failure].add(f"characteristic:{value}")

        if matching_occurrences:
            matches[logical_id] = frozenset(
                (candidate.source_unit_id, candidate.source_army_id, candidate.group_id)
                for candidate in candidates
            ) if scope == "unit" else frozenset(matching_occurrences)
            # Every added OR option retains a Unit that already matches.
            for category in active_or:
                or_base[category] += 1
            # Scan the union once, not every property set for every category.
            keys_by_category: dict[str, set[str]] = defaultdict(set)
            for name, value in matching_properties:
                if name == "equipment_characteristics":
                    if "equipment" not in active_or:
                        keys_by_category["equipment"].add(f"characteristic:{value}")
                elif name in additions and name not in active_or:
                    keys_by_category[name].add(str(value))
            for category, keys in keys_by_category.items():
                for key in keys:
                    additions[category][key] += 1
        else:
            for category, keys in rescued.items():
                for key in keys:
                    additions[category][key] += 1

    for category in CATEGORIES:
        if or_base[category]:
            # The API merges this base into every known displayed option.
            additions[category]["__or_base__"] = or_base[category]
    return matches, {category: dict(values) for category, values in additions.items()}
