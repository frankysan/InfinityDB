"""Project current N5 declaration categories into a player-facing reference.

Skills and declarable Equipment own curated declaration types; Hacking Programs
own Army metadata types. The independently reviewed N5.3 p. 191 chart is the
source-parity check, not a parallel runtime list of actions. The projection
is a reference, never a declaration-legality evaluator.
"""
from __future__ import annotations

from typing import Any

from infinity_db.database.repository import Database
from infinity_db.domain_references import rule_record_public_reference
from infinity_db.domain_slugs import assign_domain_slugs
from infinity_db.hacking_program_catalog import hacking_program_declaration_categories
from infinity_db.rules_database import RulesDatabase

DECLARATIONS = (
    ("basic-short-skill", "Basic Short Skills"),
    ("short-skill", "Short Skills"),
    ("long-skill", "Long Skills"),
    ("aro", "AROs"),
)
CATEGORY_IDS = frozenset(key for key, _ in DECLARATIONS)

def _is_core(record: dict[str, Any], collection: str) -> bool:
    return (
        record.get("composition", {}).get("role") == "definition"
        and record.get("collection", {}).get("id") == collection
        and record.get("scope") == {"game": "N5", "seasons": ["current"]}
    )


def _href(database: Database, record: dict[str, Any]) -> str:
    ref = rule_record_public_reference(database, record)
    if ref is None:
        raise ValueError(f"No public declaration reference for {record['id']}")
    href = ref.get("href") or (
        f"/{ref['catalog']}/{ref['id']}" if ref.get("catalog") and ref.get("id") else None
    )
    if not href:
        raise ValueError(f"Unroutable declaration reference: {record['id']}")
    return href


def core_declaration_matrix(
    database: Database,
    rules_database: RulesDatabase,
) -> dict[str, Any]:
    """Project unscoped core definitions without consulting a hard-coded chart."""
    sections: dict[str, list[dict[str, str]]] = {key: [] for key, _ in DECLARATIONS}

    def append(record: dict[str, Any], types: set[str], *, source_type: str) -> None:
        if not types <= CATEGORY_IDS:
            raise ValueError(f"Unknown declaration category: {record['id']}: {types}")
        if not types:
            return
        href = _href(database, record)
        for category in sections:
            if category in types:
                sections[category].append({
                    "record_id": record["id"],
                    "name": record["name"],
                    "owner": record["kind"],
                    "source_type": source_type,
                    "href": href,
                })

    for skill in rules_database.composed_records_by_kind("skill", include_army_links=True):
        if not _is_core(skill, "n5-core-v5.3"):
            continue
        if (skill.get("variant_semantics") or {}).get("inheritance") == "source":
            continue  # A source replacement is not another core declaration.
        category = (skill.get("facts") or {}).get("category")
        if category not in {"common-skill", "special-skill"}:
            continue
        types = {item["id"] for item in skill.get("skill_types", [])}
        # Automatic and Deployment Skills are valid source categories but
        # not declarations in the Order/ARO expenditure sequence.
        unknown = types - CATEGORY_IDS - {"automatic", "deployment-skill"}
        if unknown:
            raise ValueError(f"Unsupported core Skill declaration: {skill['id']}: {types}")
        if not types:
            continue  # Missing categories grant no declaration permission.
        append(
            skill, types & CATEGORY_IDS,
            source_type="Common" if category == "common-skill" else "Special",
        )

    programs = {
        record["id"]: record
        for record in rules_database.composed_records_by_kind(
            "hacking-program", include_army_links=True,
        )
        if _is_core(record, "n5-hacking-programs-v5.3")
    }
    army_programs = database.list_hacking_programs()
    slugs = assign_domain_slugs(
        ((int(item["position"]), item["name"]) for item in army_programs),
        domain="hacking-programs",
    )
    if {f"hacking-program:{slug}" for slug in slugs.values()} != set(programs):
        raise ValueError("Core Hacking Program identity mismatch")
    for item in army_programs:
        record_id = f"hacking-program:{slugs[int(item['position'])]}"
        record = programs[record_id]
        types = {
            category["id"]
            for category in hacking_program_declaration_categories(item["skill_types"])
        }
        append(record, types, source_type="Hacking")

    for record in rules_database.composed_records_by_kind(
        "equipment", include_army_links=True,
    ):
        if not _is_core(record, "n5-core-v5.3"):
            continue
        types = {item["id"] for item in record.get("skill_types", [])}
        unknown = types - CATEGORY_IDS - {"automatic", "deployment-skill"}
        if unknown:
            raise ValueError(
                f"Unsupported core Equipment declaration: {record['id']}: {types}"
            )
        append(record, types & CATEGORY_IDS, source_type="Equipment")

    # The printed Equipment action is owned by the Skill domain.
    for item in sections["short-skill"]:
        if item["record_id"] == "skill:activate-disco-ball":
            item["source_type"] = "Equipment"

    return {
        "scope": "n5-core-current-unscoped",
        "source": {"id": "n5-core-v5.3-pdf", "page": 191},
        "legalityEvaluation": False,
        "sections": [
            {
                "id": category,
                "title": title,
                "items": sorted(
                    sections[category],
                    key=lambda item: (item["name"].casefold(), item["record_id"]),
                ),
            }
            for category, title in DECLARATIONS
        ],
    }
