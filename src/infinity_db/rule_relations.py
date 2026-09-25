"""Canonical semantics for typed rules relationships."""

from __future__ import annotations

from typing import Any

RELATION_GROUPS: dict[str, dict[str, Any]] = {
    "creates-enables": {"label": "Creates & enables", "order": 10},
    "state-interactions": {"label": "State interactions", "order": 20},
    "mods-changes": {"label": "MODs & changes", "order": 30},
    "cancels-restricts": {"label": "Cancels & restricts", "order": 40},
}

# Player-facing semantics live here rather than in the browser. ``None`` marks a
# structural relation that remains available through the API but is intentionally
# omitted from the generic Related rules presentation.
RULE_RELATION_PRESENTATION: dict[str, dict[str, str] | None] = {
    "applies-effects-to": {
        "group": "creates-enables",
        "outbound": "Effects apply to",
        "inbound": "Affected by",
    },
    "controller-eligible-for": {
        "group": "creates-enables",
        "outbound": "Can control",
        "inbound": "Can be controlled by",
    },
    "cancels-state": {
        "group": "state-interactions",
        "outbound": "Cancels state",
        "inbound": "Cancelled by",
    },
    "causes-state": {
        "group": "state-interactions",
        "outbound": "Causes state",
        "inbound": "Caused by",
    },
    "enters-state": {
        "group": "state-interactions",
        "outbound": "Enters state",
        "inbound": "Entered by",
    },
    "enables-use-of": {
        "group": "creates-enables",
        "outbound": "Enables use of",
        "inbound": "Enabled by",
    },
    "equips-with": {
        "group": "creates-enables",
        "outbound": "Equips with",
        "inbound": "Provided by",
    },
    "has-subtype": {
        "group": "creates-enables",
        "outbound": "Includes subtype",
        "inbound": "Subtype of",
    },
    "ignores-modifiers-from": {
        "group": "mods-changes",
        "outbound": "Ignores MODs from",
        "inbound": "MODs ignored by",
    },
    "imposes-modifiers-on": {
        "group": "mods-changes",
        "outbound": "Imposes MODs on",
        "inbound": "MODs imposed by",
    },
    "modifies-rolls-for": {
        "group": "mods-changes",
        "outbound": "Modifies rolls for",
        "inbound": "Rolls modified by",
    },
    "modifies-use-of": {
        "group": "mods-changes",
        "outbound": "Modifies use of",
        "inbound": "Use modified by",
    },
    "negates-effects-of": {
        "group": "cancels-restricts",
        "outbound": "Negates",
        "inbound": "Negated by",
    },
    "overrides-effects-of": {
        "group": "mods-changes",
        "outbound": "Overrides",
        "inbound": "Overridden by",
    },
    "prevents-state-entry": {
        "group": "state-interactions",
        "outbound": "Prevents state entry",
        "inbound": "State entry prevented by",
    },
    "reveals-state": {
        "group": "state-interactions",
        "outbound": "Reveals state",
        "inbound": "Revealed by",
    },
    "reduces-modifiers-from": {
        "group": "mods-changes",
        "outbound": "Reduces MODs from",
        "inbound": "MODs reduced by",
    },
    "restricts-use-of": {
        "group": "cancels-restricts",
        "outbound": "Restricts use of",
        "inbound": "Use restricted by",
    },
    "triggered-by-state-entry": {
        "group": "state-interactions",
        "outbound": "Triggered by entering",
        "inbound": "State entry triggers",
    },
    "uses-effects-of": {
        "group": "creates-enables",
        "outbound": "Uses effects of",
        "inbound": "Effects used by",
    },
    "variant-of": None,
}

RULE_RELATION_TYPES = frozenset(RULE_RELATION_PRESENTATION)

# Relations that positively establish, provide, or enable a condition sort before
# cancellation/restriction/modifier interactions within the same presentation group.
# The browser then sorts by player-facing interaction label and related-record name.
RELATION_ESTABLISHING_TYPES = frozenset(
    {
        "applies-effects-to",
        "controller-eligible-for",
        "causes-state",
        "enters-state",
        "enables-use-of",
        "equips-with",
        "has-subtype",
        "uses-effects-of",
    }
)


def relation_presentation(relation_type: str, direction: str) -> dict[str, Any] | None:
    """Return canonical player-facing metadata for one typed relation direction."""
    if direction not in {"outbound", "inbound"}:
        raise ValueError(f"Unsupported relation direction: {direction!r}")
    semantics = RULE_RELATION_PRESENTATION.get(relation_type)
    if semantics is None:
        if relation_type not in RULE_RELATION_PRESENTATION:
            raise ValueError(f"Unsupported relation type: {relation_type!r}")
        return None
    group = RELATION_GROUPS[semantics["group"]]
    return {
        "group_id": semantics["group"],
        "group_label": group["label"],
        "group_order": group["order"],
        "relation_order": 10 if relation_type in RELATION_ESTABLISHING_TYPES else 20,
        "label": semantics[direction],
    }
