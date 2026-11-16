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

    for logical_id, candidates in grouped.items():
        if scope == "unit":
            # Only already-eligible occurrences of this logical Unit contribute;
            # this never pulls in a different Unit or a Controller target pool.
            union = frozenset().union(*(candidate.properties for candidate in candidates))
            aggregate = MatchContext(logical_id, 0, 0, 0, None, None, union)
            considered = [aggregate]
        else:
            considered = candidates

        if any(
            matches_selected(candidate.properties, selected, and_categories)
            for candidate in considered
        ):
            matches[logical_id] = frozenset(
                (candidate.source_unit_id, candidate.source_army_id, candidate.group_id)
                for candidate in candidates
                if scope == "unit" or matches_selected(
                    candidate.properties, selected, and_categories,
                )
            )

        for category in CATEGORIES:
            remaining = [
                candidate.properties for candidate in considered
                if matches_selected(
                    candidate.properties, selected, and_categories, excluding=category,
                )
            ]
            if not remaining:
                continue
            choices = selected.get(category, ())
            if choices and category not in and_categories:
                # Existing OR match makes *every* added option a no-op for this
                # logical Unit; account for it without enumerating the menu.
                if any(
                    any(not props.isdisjoint(choice) for choice in choices)
                    for props in remaining
                ):
                    or_base[category] += 1
                    continue
            if choices and category in and_categories:
                remaining = [
                    props for props in remaining
                    if all(not props.isdisjoint(choice) for choice in choices)
                ]
            keys = {
                str(value)
                for props in remaining
                for name, value in props
                if name == category
            }
            if category == "equipment":
                keys.update(
                    f"characteristic:{value}"
                    for props in remaining for name, value in props
                    if name == "equipment_characteristics"
                )
            for key in keys:
                additions[category][key] += 1

    for category in CATEGORIES:
        if or_base[category]:
            # The API merges this base into every known displayed option.
            additions[category]["__or_base__"] = or_base[category]
    return matches, {category: dict(values) for category, values in additions.items()}
