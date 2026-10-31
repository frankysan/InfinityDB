"""Typed, source-scoped restrictions for finite reviewed rule charts.

This is a negative constraint graph, deliberately separate from the unqualified
curated ``relations`` graph. Its subject may be a source-only Troop Type
selector, and its operation may be a terrain traversal or a role-selection
decision rather than a canonical Skill invocation. It never evaluates legality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# The target is an optional navigation reference, not an assertion that the
# operation is universally equivalent to invoking the target record.
ACTION_OPERATIONS: dict[str, tuple[str, str | None, dict[str, str]]] = {
    "enter-prone": ("state-entry", "state:prone", {}),
    "declare-cautious-movement": (
        "skill-declaration", "skill:cautious-movement", {},
    ),
    "declare-climb": ("skill-declaration", "skill:climb", {}),
    "use-ladders": ("terrain-traversal", None, {"terrain": "ladders"}),
    "upward-jump": (
        "directional-skill-movement", "skill:jump", {"direction": "upward"},
    ),
    "lieutenant-selection": (
        "army-role-selection", "skill:lieutenant", {"role": "lieutenant"},
    ),
}

SUBJECT_SELECTORS: dict[str, tuple[str, str | None]] = {
    "TAG": ("troop-type", None),
    "Motorcycle": ("equipment-while-mounted", "equipment:motorcycle"),
    "Aerial": ("skill", "skill:aerial"),
    "VH": ("troop-type", None),
    "REM": ("troop-type", None),
    "Irregular": ("training", "training:irregular"),
}
# A scope is specific to both the subject's condition and the operation:
# a direction on Jump must not convert into a universal restriction on Jump.
CONDITION_SCOPES: dict[str, dict[str, str]] = {
    "TAG": {
        "enter-prone": "all",
        "declare-cautious-movement": "all",
    },
    "Motorcycle": {
        "enter-prone": "while-mounted",
        "declare-cautious-movement": "while-mounted",
        "declare-climb": "while-mounted",
        "use-ladders": "while-mounted",
        "upward-jump": "while-mounted-upwards-only",
    },
    "Aerial": {
        "enter-prone": "aerial-active",
        "declare-cautious-movement": "aerial-active",
    },
    "VH": {
        "enter-prone": "all",
        "declare-cautious-movement": "all",
    },
    "REM": {
        "declare-cautious-movement": "all",
        "lieutenant-selection": "army-selection-only",
    },
    "Irregular": {
        "lieutenant-selection": "army-selection-only",
    },
}


@dataclass(frozen=True)
class RestrictionConstraint:
    """One reviewed, negative condition, never a positive permission assertion."""

    subject: str
    subject_kind: str
    owner_record_id: str | None
    action: str
    operation_kind: str
    target_record_id: str | None
    scope: str
    qualifier: dict[str, str]

    def publication_operation(self) -> dict[str, Any]:
        """Typed relationship shape alongside the legacy public chart fields."""
        return {
            "kind": self.operation_kind,
            "qualifier": self.qualifier,
        }


def compile_restriction_conditions(
    source: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> list[RestrictionConstraint]:
    """Resolve exact negative relations without making up missing endpoints.

    A new/mismatched source action or context fails closed rather than silently
    becoming a generic `restricts-use-of` relation. The source chart audit
    additionally verifies its pinned wording and PDF.
    """
    if (source.get("sourceId"), source.get("sourcePage")) != ("n5-core-v5.3-pdf", 194):
        raise ValueError("Restrictions model requires the reviewed N5.3 p. 194 chart")
    classification = source.get("classification")
    if not isinstance(classification, dict) or classification.get("action") != (
        "negative-prohibition-not-positive-permission"
    ):
        raise ValueError("Restrictions model requires negative-only source authority")
    rows = source.get("rows")
    if not isinstance(rows, list) or (
        [row.get("subject") for row in rows if isinstance(row, dict)]
        != list(SUBJECT_SELECTORS)
    ):
        raise ValueError("Restrictions model subject selectors/order drift")
    if len(rows) != len(SUBJECT_SELECTORS):
        raise ValueError("Restrictions model missing source subjects")
    compiled: list[RestrictionConstraint] = []
    for row in rows:
        subject = row["subject"]
        subject_kind, owner_record_id = SUBJECT_SELECTORS[subject]
        if (row.get("subjectKind"), row.get("ownerRecordId")) != (
            subject_kind, owner_record_id
        ):
            raise ValueError(f"Restrictions model source identity drift: {subject}")
        if owner_record_id:
            if owner_record_id not in records:
                raise ValueError(f"Restrictions model missing owner: {owner_record_id}")
            if records[owner_record_id].get("kind") != owner_record_id.split(":", 1)[0]:
                raise ValueError(f"Restrictions model invalid owner kind: {owner_record_id}")
        expected = CONDITION_SCOPES[subject]
        conditions = row.get("restrictions")
        if not isinstance(conditions, list) or len(conditions) != len(expected):
            raise ValueError(f"Restrictions model condition count drift: {subject}")
        seen: set[str] = set()
        for entry in conditions:
            if not isinstance(entry, dict) or set(entry) != {
                "action", "targetRecordId", "scope",
            }:
                raise ValueError(f"Restrictions model malformed operation: {subject}")
            action = entry["action"]
            if not isinstance(action, str) or action not in expected or action in seen:
                raise ValueError(f"Restrictions model unknown/repeated action: {subject} {action}")
            seen.add(action)
            kind, target, qualifier = ACTION_OPERATIONS[action]
            if entry["targetRecordId"] != target or entry["scope"] != expected[action]:
                raise ValueError(
                    f"Restrictions model action target/scope drift: {subject} {action}"
                )
            if target is not None:
                if target not in records:
                    raise ValueError(f"Restrictions model missing target: {target}")
                if records[target].get("kind") != target.split(":", 1)[0]:
                    raise ValueError(f"Restrictions model invalid target kind: {target}")
            compiled.append(RestrictionConstraint(
                subject=subject,
                subject_kind=subject_kind,
                owner_record_id=owner_record_id,
                action=action,
                operation_kind=kind,
                target_record_id=target,
                scope=entry["scope"],
                qualifier=dict(qualifier),
            ))
        if seen != set(expected):
            raise ValueError(f"Restrictions model source action coverage drift: {subject}")
    if len(compiled) != 14:
        raise ValueError("Restrictions model expected 14 source-negative conditions")
    return compiled
