"""Source-backed Unit Explorer Specialist qualification filter.

This is a *candidate* match over a Unit's Army Skill occurrences. Actual
Specialist status is established by the selected scenario and profile,
not stored as a permanent Unit attribute.
"""

from __future__ import annotations

from infinity_db.database import Database
from infinity_db.rules_database import RulesDatabase

SPECIALIST_RULE_ID = "rule:specialist-troops:standard"
SPECIALIST_CONTEXTS = frozenset({"standard", "domination", "supplies", "firefight"})


def _qualifying_skills(rules: RulesDatabase, context: str) -> tuple[str, ...]:
    if context not in SPECIALIST_CONTEXTS:
        raise ValueError("Unknown Specialist Troops filter context")
    if context == "standard":
        record = rules.composed_record(SPECIALIST_RULE_ID)
    else:
        publication = rules.scenario_reference(context)
        record = next(
            (rule for rule in publication["rules"] if rule["id"] == SPECIALIST_RULE_ID),
            None,
        ) if publication is not None else None
    if record is None:
        raise ValueError(f"Missing reviewed Specialist Troops rule for {context}")
    qualifiers = record.get("facts", {}).get("specialists", {}).get("anyOfSkills")
    if not isinstance(qualifiers, list) or not qualifiers:
        raise ValueError(f"Missing reviewed Specialist Troops qualifiers for {context}")
    if any(not isinstance(value, str) or not value.startswith("skill:") for value in qualifiers):
        raise ValueError("Invalid reviewed Specialist Troops Skill identities")
    return tuple(qualifiers)


def _non_specialist_chain_variant(variant: dict) -> bool:
    """N5 Chain of Command (Non Specialist) cannot qualify by itself."""
    labels = [str(variant.get("skill_name", ""))]
    labels.extend(str(extra.get("name", "")) for extra in variant.get("extras", []))
    return any("non specialist" in label.casefold() for label in labels)


def candidate_unit_ids(
    database: Database, rules: RulesDatabase, context: str,
) -> frozenset[int]:
    """Return logical Units with any qualifying Skill occurrence.

    An occurrence can be a profile, loadout, or Unit option. This does
    not assert every profile/loadout qualifies in every Army. A Unit with
    another qualifying Skill remains a candidate even if its Chain of
    Command occurrence is the Non Specialist variant.
    """
    unit_ids: set[int] = set()
    for skill_id in _qualifying_skills(rules, context):
        skill = database.get_skill(skill_id.removeprefix("skill:"))
        if skill is None:
            raise ValueError(f"Specialist Skill has no Army catalog identity: {skill_id}")
        for variant in skill["variants"]:
            if skill_id == "skill:chain-of-command" and _non_specialist_chain_variant(variant):
                continue
            unit_ids.update(int(unit["id"]) for unit in variant["units"])
    return frozenset(unit_ids)
