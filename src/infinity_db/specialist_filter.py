"""Source-backed Unit Explorer Specialist qualification filter.

This is a *candidate* match over a Unit's Army Skill occurrences. Actual
Specialist status is established by the selected scenario and profile,
not stored as a permanent Unit attribute.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3

from infinity_db.build_provenance import canonical_bytes
from infinity_db.database import Database
from infinity_db.rules_database import RULES_METADATA_TABLE, RulesDatabase

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

def _specialist_projection_sha256(db: sqlite3.Connection) -> str:
    row = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='searchIndex'"
    ).fetchone()
    if row is None:
        raise ValueError("Specialist candidate projection requires a matching publication scope")
    rows = [tuple(row) for row in db.execute(
        "SELECT context,body FROM specialist_candidates ORDER BY context"
    )]
    return hashlib.sha256(canonical_bytes([json.loads(row[0])["scope"], rows])).hexdigest()


def stage_specialist_projection(
    db: sqlite3.Connection, candidates: dict[str, frozenset[int]],
) -> None:
    db.execute(
        "CREATE TABLE specialist_candidates (context TEXT PRIMARY KEY, body TEXT NOT NULL) "
        "WITHOUT ROWID"
    )
    db.executemany(
        "INSERT INTO specialist_candidates VALUES (?,?)",
        [(context, canonical_bytes(sorted(ids)).decode("utf-8"))
         for context, ids in sorted(candidates.items())],
    )
    db.execute(
        f"INSERT INTO {RULES_METADATA_TABLE} VALUES (?,?)",
        ("specialistProjectionSha256", json.dumps(_specialist_projection_sha256(db))),
    )
    validate_specialist_projection(db)


def validate_specialist_projection(db: sqlite3.Connection) -> None:
    row = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='specialistProjectionSha256'"
    ).fetchone()
    if row is None or json.loads(row[0]) != _specialist_projection_sha256(db):
        raise ValueError("Invalid Specialist candidate projection fingerprint")
    contexts = set()
    for context, raw in db.execute("SELECT context,body FROM specialist_candidates"):
        contexts.add(context)
        ids = json.loads(raw)
        if (not isinstance(ids, list) or any(type(i) is not int or i < 0 for i in ids)
                or ids != sorted(set(ids))):
            raise ValueError("Invalid Specialist candidate projection identities")
    if contexts != SPECIALIST_CONTEXTS:
        raise ValueError("Incomplete Specialist candidate projection contexts")
