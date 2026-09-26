#!/usr/bin/env python3
"""Audit normalized Army source constructs against application/web presentation."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from infinity_db.database.paths import raw_database_path
from infinity_db.database.schema import METADATA_TABLE, TABLES, quote

FORMAT = "InfinityDB source-to-presentation completeness audit"
FORMAT_VERSION = 1

EXPLICIT = "explicitly_presented"
IMPLICIT = "implicitly_represented"
OPERATIONAL = "operationally_consumed"
REDUNDANT = "redundant_source_representation"
NORMALIZATION = "normalization_only_structure"
UNREPRESENTED = "unrepresented_player_information"

SOURCE_FACT = "source_native_fact"
SOURCE_RELATIONSHIP = "source_native_relationship"
SOURCE_PROVENANCE = "source_provenance_metadata"
NORMALIZATION_ARTIFACT = "normalization_artifact"

DOC_DATA_MODEL = "docs/data-model.md"
DOC_RULES = "docs/rules-semantics.md"


class SourcePresentationAuditError(ValueError):
    """Raised when the maintained completeness policy no longer covers the schema."""


def _policy(status: str, category: str, location: str, reason: str) -> dict[str, str]:
    return {
        "status": status,
        "semanticCategory": category,
        "canonicalDocumentation": location,
        "reason": reason,
    }


TABLE_POLICY: dict[str, dict[str, str]] = {}


def _register(
    names: Sequence[str], status: str, category: str, *, reason: str, location: str = DOC_DATA_MODEL
) -> None:
    for name in names:
        TABLE_POLICY[name] = _policy(status, category, location, reason)


_register(
    [
        "army_lists",
        "units",
        "army_units",
        "profile_groups",
        "profiles",
        "loadout_options",
        "categories",
        "characteristics",
        "troop_types",
        "equipment",
        "skills",
        "weapons",
        "extras",
        "profile_skills",
        "profile_skill_extras",
        "profile_equipment",
        "profile_equipment_extras",
        "profile_weapons",
        "profile_weapon_extras",
        "profile_characteristics",
        "option_skills",
        "option_skill_extras",
        "option_equipment",
        "option_equipment_extras",
        "option_weapons",
        "option_weapon_extras",
        "option_characteristics",
        "option_orders",
        "metadata_ammunitions",
        "metadata_weapons",
    ],
    EXPLICIT,
    SOURCE_FACT,
    reason=(
        "The source construct is represented through the canonical application/profile/loadout "
        "model and has an existing browser presentation."
    ),
)
_register(
    ["fireteams", "fireteam_types", "fireteam_members"],
    EXPLICIT,
    SOURCE_RELATIONSHIP,
    reason=(
        "Army-local Fireteam source relationships are projected into the canonical "
        "application Fireteam model and presented through the Fireteam chart browser."
    ),
)
_register(
    [
        "metadata_hacking_programs",
        "metadata_martial_arts",
        "metadata_metachemistry",
        "metadata_booty",
    ],
    EXPLICIT,
    SOURCE_RELATIONSHIP,
    reason=(
        "Structured rules-reference metadata is projected into maintained application tables "
        "and presented on the existing Hacker, Martial Arts, Booty, and MetaChemistry Skill "
        "detail surfaces."
    ),
    location=DOC_RULES,
)
_register(
    ["profile_includes", "option_includes", "unit_option_includes"],
    EXPLICIT,
    SOURCE_RELATIONSHIP,
    reason=(
        "Profile, Loadout, and shared Unit-option include edges resolve to canonical loadout "
        "targets and are presented on Unit detail surfaces with Army context."
    ),
)
_register(
    ["profile_peripherals", "option_peripherals"],
    EXPLICIT,
    SOURCE_RELATIONSHIP,
    reason=(
        "Peripheral attachments are projected through reviewed application identities and "
        "presented on their owning Profile or Loadout surfaces."
    ),
)
_register(
    ["metadata_factions", "metadata_skills", "metadata_equipment", "ammunition", "peripherals"],
    REDUNDANT,
    SOURCE_PROVENANCE,
    reason=(
        "The source collection is retained for provenance/enrichment but its currently useful "
        "identity/detail is represented by another maintained application or rules layer."
    ),
)
_register(
    [
        "factions",
        "army_categories",
        "army_characteristics",
        "army_troop_types",
        "army_equipment",
        "army_skills",
        "army_weapons",
        "army_ammunition",
        "army_extras",
        "option_weapon_templates",
    ],
    NORMALIZATION,
    NORMALIZATION_ARTIFACT,
    reason=(
        "This structure supports normalization, indexing, or source reconstruction and does not "
        "add an independent player-facing relationship."
    ),
)
_register(
    [
        "unit_factions",
        "unit_options",
        "unit_option_skills",
        "unit_option_skill_extras",
        "unit_option_equipment",
        "unit_option_equipment_extras",
        "unit_option_weapons",
        "unit_option_weapon_extras",
        "unit_option_characteristics",
        "unit_option_orders",
        "relations",
        "relation_units",
        "relation_dependencies",
    ],
    UNREPRESENTED,
    SOURCE_RELATIONSHIP,
    reason=(
        "The source construct contains player-relevant relationship/reference data that is either "
        "not yet materialized as application data or is not yet presented in the browser."
    ),
)

# Source tables whose semantic content is already represented but not necessarily through a
# one-to-one source row. Keep these separate from redundant payload copies.
_register(
    [],
    IMPLICIT,
    SOURCE_FACT,
    reason="Represented indirectly through another maintained application concept.",
)
_register(
    [],
    OPERATIONAL,
    SOURCE_PROVENANCE,
    reason="Consumed for application/build operation rather than exposed as a gameplay fact.",
)

FIELD_OVERRIDES: dict[tuple[str, str], dict[str, str]] = {
    ("army_lists", "version"): _policy(
        OPERATIONAL,
        SOURCE_PROVENANCE,
        DOC_DATA_MODEL,
        "Source version/provenance is operational metadata rather than a gameplay datum.",
    ),
    ("army_lists", "source_file"): _policy(
        OPERATIONAL,
        SOURCE_PROVENANCE,
        DOC_DATA_MODEL,
        "Source filename is build provenance.",
    ),
    ("army_lists", "source_sha256"): _policy(
        OPERATIONAL,
        SOURCE_PROVENANCE,
        DOC_DATA_MODEL,
        "Source hash is build provenance.",
    ),
    ("army_lists", "fireteam_description"): _policy(
        EXPLICIT,
        SOURCE_RELATIONSHIP,
        DOC_DATA_MODEL,
        "Fireteam chart notes are projected into the Army-scoped Fireteam browser.",
    ),
    ("army_lists", "fireteam_spec"): _policy(
        EXPLICIT,
        SOURCE_RELATIONSHIP,
        DOC_DATA_MODEL,
        "Fireteam type limits are projected into the Army-scoped Fireteam browser.",
    ),
    ("army_lists", "legacy_fireteams"): _policy(
        REDUNDANT,
        SOURCE_PROVENANCE,
        DOC_DATA_MODEL,
        "Legacy Fireteam source context is preserved in raw storage; the current chart "
        "projection/browser is authoritative for player-facing Fireteam data.",
    ),
    ("units", "notes"): _policy(
        UNREPRESENTED,
        SOURCE_FACT,
        DOC_DATA_MODEL,
        "Source-attributed Unit notes are preserved but the browser does not render them.",
    ),
    ("units", "spectables"): _policy(
        UNREPRESENTED,
        SOURCE_FACT,
        DOC_DATA_MODEL,
        "Opaque spectables are preserved but require scope/semantic review before presentation.",
    ),
    ("profiles", "notes"): _policy(
        UNREPRESENTED,
        SOURCE_FACT,
        DOC_DATA_MODEL,
        "Profile notes have no current browser representation if the source supplies them.",
    ),
    ("profile_groups", "notes"): _policy(
        UNREPRESENTED,
        SOURCE_FACT,
        DOC_DATA_MODEL,
        "Profile-group notes have no current browser representation if the source supplies them.",
    ),
    ("loadout_options", "minis"): _policy(
        UNREPRESENTED,
        SOURCE_FACT,
        DOC_DATA_MODEL,
        "The API retains loadout miniature count but the Unit UI does not display/interpret it.",
    ),
    ("loadout_options", "disabled"): _policy(
        UNREPRESENTED,
        SOURCE_FACT,
        DOC_DATA_MODEL,
        "The API retains the source disabled flag but the Unit UI does not interpret it.",
    ),
}


CONFIRMED_GAPS: tuple[dict[str, Any], ...] = (
    {
        "id": "selection_dependencies",
        "target": "0.8.x",
        "layer": "repository_api_only",
        "tables": [
            "application_unit_constraints",
            "application_unit_group_dependency_constraints",
        ],
        "reason": (
            "Selection constraints and profile-group dependencies are returned by "
            "get_unit() but not rendered."
        ),
    },
    {
        "id": "reinforcement_parentage",
        "target": "0.8.x",
        "layer": "repository_api_only",
        "tables": ["application_army_reinforcement_parents"],
        "reason": (
            "Reinforcement Section parent relationships are modeled but not exposed "
            "as navigable UI relationships."
        ),
    },
    {
        "id": "declared_faction_membership",
        "target": "0.8.x",
        "layer": "application_database_only",
        "tables": ["unit_factions"],
        "reason": (
            "Broader source-declared faction membership is distinct from Army "
            "availability but is not presented explicitly."
        ),
    },
    {
        "id": "unit_notes",
        "target": "0.9.x",
        "layer": "repository_api_partial",
        "tables": ["logical_unit_notes"],
        "reason": (
            "Source-attributed Unit notes are preserved; the browser renders none "
            "and API detail selects only the representative note."
        ),
    },
    {
        "id": "unit_options",
        "target": "0.9.x",
        "layer": "operational_only",
        "tables": ["unit_options"],
        "reason": (
            "Composite Unit options are used for search/catalog support but their "
            "selectable bundle semantics are not presented."
        ),
    },
)

REVIEW_QUEUE: tuple[dict[str, Any], ...] = (
    {
        "id": "spectables",
        "tables": ["logical_unit_spectables"],
        "reason": (
            "30 preserved opaque spectables occurrences need scope/semantic review "
            "before deciding the 1.0 presentation requirement."
        ),
    },
    {
        "id": "loadout_disabled_and_minis",
        "tables": ["loadout_payloads"],
        "reason": (
            "The source flags are preserved/API-visible but the UI ignores their "
            "semantics; review before classifying the correct presentation behavior."
        ),
    },
)


def _schema_fields() -> dict[str, list[str]]:
    return {name: list(definition.key + definition.fields) for name, definition in TABLES.items()}


def _validate_policy() -> None:
    missing = sorted(set(TABLES) - set(TABLE_POLICY))
    extra = sorted(set(TABLE_POLICY) - set(TABLES))
    unknown_overrides = sorted(
        (table, field)
        for table, field in FIELD_OVERRIDES
        if table not in TABLES or field not in set(TABLES[table].key + TABLES[table].fields)
    )
    if missing or extra or unknown_overrides:
        raise SourcePresentationAuditError(
            f"Source-presentation policy is stale: missing={missing}, extra={extra}, "
            f"unknown_overrides={unknown_overrides}"
        )


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _count(connection: sqlite3.Connection, table: str, where: str | None = None) -> int | None:
    if table not in _table_names(connection):
        return None
    query = f"SELECT COUNT(*) FROM {quote(table)}"
    if where:
        query += f" WHERE {where}"
    return int(connection.execute(query).fetchone()[0])


def _gap_evidence(connection: sqlite3.Connection) -> dict[str, int | None]:
    return {
        "applicationFireteamCount": _count(connection, "application_fireteams"),
        "applicationFireteamMemberCount": _count(connection, "application_fireteam_members"),
        "applicationFireteamFtoLoadoutCount": _count(
            connection, "application_fireteam_member_loadouts"
        ),
        "includeRelationshipCount": sum(
            value or 0
            for value in (
                _count(connection, "profile_occurrence_includes"),
                _count(connection, "loadout_occurrence_includes"),
                _count(connection, "unit_option_include_targets"),
            )
        ),
        "profilePeripheralOccurrenceCount": _count(connection, "profile_peripherals"),
        "loadoutPeripheralOccurrenceCount": _count(connection, "option_peripherals"),
        "controllerTargetCount": _count(connection, "application_peripheral_controller_targets"),
        "selectionConstraintCount": _count(connection, "application_unit_constraints"),
        "groupDependencyConstraintCount": _count(
            connection, "application_unit_group_dependency_constraints"
        ),
        "reinforcementParentCount": _count(connection, "application_army_reinforcement_parents"),
        "declaredFactionMembershipCount": _count(connection, "unit_factions"),
        "unitNoteOccurrenceCount": _count(connection, "logical_unit_notes"),
        "unitOptionCount": _count(connection, "unit_options"),
        "structureProfilePayloadCount": _count(connection, "profile_payloads", "is_structure = 1"),
        "hackingProgramReferenceCount": _count(connection, "application_hacking_programs"),
        "martialArtsReferenceCount": _count(connection, "application_martial_arts_levels"),
        "metachemistryReferenceCount": _count(connection, "application_metachemistry_results"),
        "bootyReferenceCount": _count(connection, "application_booty_results"),
        "spectablesOccurrenceCount": _count(connection, "logical_unit_spectables"),
        "disabledLoadoutPayloadCount": _count(connection, "loadout_payloads", "disabled = 1"),
        "zeroMiniLoadoutPayloadCount": _count(connection, "loadout_payloads", "minis = 0"),
    }


def _raw_evidence(path: Path) -> dict[str, Any]:
    raw_path = raw_database_path(path)
    if not raw_path.is_file():
        return {"status": "not_available", "path": str(raw_path)}
    connection = sqlite3.connect(raw_path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        tables = _table_names(connection)
        return {
            "status": "available",
            "path": str(raw_path),
            "fireteamCount": _count(connection, "fireteams"),
            "fireteamMemberCount": _count(connection, "fireteam_members"),
            "hackingProgramRowCount": _count(connection, "metadata_hacking_programs"),
            "martialArtsRowCount": _count(connection, "metadata_martial_arts"),
            "metachemistryRowCount": _count(connection, "metadata_metachemistry"),
            "bootyRowCount": _count(connection, "metadata_booty"),
            "normalizedTableCount": len(set(TABLES) & tables),
        }
    finally:
        connection.close()


def audit_database(path: Path) -> dict[str, Any]:
    _validate_policy()
    fields = _schema_fields()
    inventory: list[dict[str, Any]] = []
    counts: dict[str, int] = {
        EXPLICIT: 0,
        IMPLICIT: 0,
        OPERATIONAL: 0,
        REDUNDANT: 0,
        NORMALIZATION: 0,
        UNREPRESENTED: 0,
    }
    for table in sorted(TABLES):
        table_policy = TABLE_POLICY[table]
        field_items: list[dict[str, str]] = []
        for field in fields[table]:
            policy = FIELD_OVERRIDES.get((table, field), table_policy)
            counts[policy["status"]] += 1
            field_items.append({"field": field, **policy})
        inventory.append({"table": table, **table_policy, "fields": field_items})

    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = _table_names(connection)
        if METADATA_TABLE not in tables:
            raise SourcePresentationAuditError("Application database is missing metadata")
        evidence = _gap_evidence(connection)
    finally:
        connection.close()

    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "database": str(path),
        "summary": {
            "sourceTableCount": len(TABLES),
            "sourceFieldCount": sum(len(item) for item in fields.values()),
            "confirmedGapCount": len(CONFIRMED_GAPS),
            "reviewQueueCount": len(REVIEW_QUEUE),
            "fieldStatusCounts": counts,
        },
        "inventory": inventory,
        "confirmedGaps": list(CONFIRMED_GAPS),
        "reviewQueue": list(REVIEW_QUEUE),
        "applicationEvidence": evidence,
        "rawEvidence": _raw_evidence(path),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=FORMAT)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit_database(args.database)
    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    print(FORMAT)
    print(
        f"Source schema: {report['summary']['sourceTableCount']} tables | "
        f"{report['summary']['sourceFieldCount']} fields"
    )
    print(
        f"Completeness: {report['summary']['confirmedGapCount']} confirmed gap families | "
        f"{report['summary']['reviewQueueCount']} review items"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
