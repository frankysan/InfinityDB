"""Player-facing Army overview projection from canonical Army relationships."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict


class ArmyOverviewGroup(TypedDict):
    """Canonical overview grouping with a stable integer identity."""

    id: int
    name: str


def army_overview_group(
    army: dict[str, Any],
    *,
    armies_by_id: dict[int, dict[str, Any]],
) -> ArmyOverviewGroup:
    """Return the canonical overview group for one Army."""

    role = army.get("role")
    if role in {"sectorial", "non_aligned"}:
        group_id = army.get("group_id")
        parent = armies_by_id.get(group_id) if type(group_id) is int else None
        return {
            "id": group_id if type(group_id) is int else int(army["id"]),
            "name": str(army.get("group_name") or (parent or {}).get("name") or army["name"]),
        }

    if role == "reinforcement":
        for reference in army.get("parent_armies") or []:
            parent_id = reference.get("id") if isinstance(reference, dict) else None
            parent = armies_by_id.get(parent_id) if type(parent_id) is int else None
            if parent is not None and parent.get("role") in {"main", "grouping"}:
                return {"id": int(parent["id"]), "name": str(parent["name"])}

    return {"id": int(army["id"]), "name": str(army["name"])}


def army_overview_out_of_catalog(
    army: dict[str, Any],
    *,
    armies_by_id: dict[int, dict[str, Any]],
) -> bool:
    """Return the player-facing catalog status for one current Army identity."""

    if army.get("legacy"):
        return False
    if army.get("role") != "reinforcement":
        return bool(army.get("discontinued"))

    group = army_overview_group(army, armies_by_id=armies_by_id)
    parent = armies_by_id.get(group["id"])
    return bool((parent or {}).get("discontinued"))


def army_overview_description(
    army: dict[str, Any],
    *,
    armies_by_id: dict[int, dict[str, Any]],
    summaries: Mapping[str, str] | None = None,
) -> str:
    """Return maintained Army summary copy, with a structural fallback."""

    slug = str(army.get("public_slug") or army.get("slug") or "")
    if summaries is not None and (summary := summaries.get(slug)):
        return summary

    name = str(army.get("name") or "This Army")
    role = army.get("role")
    kind = army.get("kind")
    group_name = army.get("group_name")

    if army.get("legacy"):
        return f"{name} is a legacy Army list from an earlier edition and is not playable in N5."
    if role == "main":
        return f"The main {name} army list, drawing on the faction's broad current roster."
    if role == "sectorial":
        parent = str(group_name or "its parent faction")
        return f"A {parent} Sectorial with its own focused army list."
    if role == "non_aligned":
        return "A Non-Aligned Army with its own independent roster."
    if role == "reinforcement" or kind == "reinforcement":
        group = army_overview_group(army, armies_by_id=armies_by_id)
        if group["id"] != army.get("id"):
            return (
                f"The Reinforcements group shared by {group['name']} and its related "
                "army lists."
            )
        return "A Reinforcements group shared by its related army lists."

    return f"Browse the current {name} roster in Unit Explorer."
