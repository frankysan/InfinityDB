"""Audit the Army/faction semantic boundary used by current InfinityDB runtime paths."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database, identity_config_from_connection

FORMAT = "InfinityDB army/faction semantic audit"
FORMAT_VERSION = 1

REQUIRED_FIELDS: dict[str, set[str]] = {
    "factions": {
        "id",
        "has_army_list",
        "canonical_reference_count",
        "unit_membership_reference_count",
    },
    "army_lists": {"id", "name", "slug", "kind", "reinforcement_id"},
    "metadata_factions": {"id", "parent", "name", "slug", "discontinued", "logo"},
    "army_units": {"army_id", "unit_id", "availability_kind"},
    "unit_factions": {"unit_id", "faction_id"},
    "units": {"id", "canonical_faction_id", "source_defined", "source_role"},
}

FIELD_CLASSIFICATION: dict[str, dict[str, dict[str, str]]] = {
    "army_lists": {
        "id": {
            "role": "source_list_identity",
            "reason": (
                "Concrete Infinity Army list/document identity. Canonical application "
                "army identity "
                "may collapse reviewed source aliases without erasing this source ID."
            ),
        },
        "name": {
            "role": "canonical_candidate",
            "reason": (
                "Player-facing list identity label normalized from Army metadata; current "
                "metadata_factions rows therefore duplicate it exactly."
            ),
        },
        "slug": {
            "role": "canonical_candidate",
            "reason": (
                "Player-facing list identity slug. Current metadata_factions rows "
                "duplicate it exactly."
            ),
        },
        "kind": {
            "role": "source_shape_context",
            "reason": (
                "Derived ordinary-list versus reinforcement-file shape; not a "
                "main/sectorial taxonomy."
            ),
        },
        "reinforcement_id": {
            "role": "relationship",
            "reason": (
                "Explicit ordinary-list to reinforcement-list relationship and stronger "
                "evidence than "
                "reinforcement metadata parent numbers."
            ),
        },
    },
    "metadata_factions": {
        "id": {
            "role": "source_metadata_identity",
            "reason": (
                "Metadata identity that currently overlaps every imported Army list ID "
                "but remains a "
                "separate source construct."
            ),
        },
        "parent": {
            "role": "hierarchy_context",
            "reason": (
                "Useful for ordinary main/sectorial/Non-Aligned grouping. Reinforcement metadata "
                "parents are not the application reinforcement ownership relationship."
            ),
        },
        "name": {
            "role": "duplicate_identity_metadata",
            "reason": "Current snapshot duplicates army_lists.name exactly for every shared ID.",
        },
        "slug": {
            "role": "duplicate_identity_metadata",
            "reason": "Current snapshot duplicates army_lists.slug exactly for every shared ID.",
        },
        "discontinued": {
            "role": "metadata_context",
            "reason": "Game-wide source metadata; not equivalent to current list playability.",
        },
        "logo": {
            "role": "metadata_context",
            "reason": "Source presentation metadata attached to the metadata faction identity.",
        },
    },
    "army_units": {
        "army_id": {
            "role": "army_local_occurrence",
            "reason": (
                "Concrete Infinity Army roster occurrence. InfinityDB preserves it as "
                "list-specific "
                "availability context while comparing the same logical unit across armies."
            ),
        },
        "unit_id": {
            "role": "army_local_occurrence",
            "reason": "Source unit participating in one concrete Army list occurrence.",
        },
        "availability_kind": {
            "role": "availability_context",
            "reason": "Explicit standard versus optional-mercenary availability provenance.",
        },
    },
    "unit_factions": {
        "unit_id": {
            "role": "game_wide_relationship",
            "reason": "Source unit participating in a declared faction-membership relationship.",
        },
        "faction_id": {
            "role": "game_wide_relationship",
            "reason": (
                "Declared cross-army faction membership. It can include historical/reference-only "
                "factions with no current Army list, so it must not be reduced to army_units."
            ),
        },
    },
    "units": {
        "canonical_faction_id": {
            "role": "source_origin_context",
            "reason": (
                "Source-specific canonical faction/origin relationship. It is not list membership, "
                "playability, or application ownership; IDs can exist without Army lists."
            ),
        },
    },
    "factions": {
        "id": {
            "role": "game_wide_identity_registry",
            "reason": (
                "Union identity registry for list, canonical-faction, and declared-membership "
                "references; "
                "not every identity is a current playable/list force."
            ),
        },
    },
}


class ArmyFactionAuditError(ValueError):
    """Raised when the audited schema or semantic invariants are stale."""


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _check_schema(connection: sqlite3.Connection) -> None:
    for table, required in REQUIRED_FIELDS.items():
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        missing = required - columns
        if missing:
            raise ArmyFactionAuditError(
                f"Audit schema drift: {table} is missing {', '.join(sorted(missing))}"
            )


def _rows(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]


def audit_database(path: Path) -> dict[str, Any]:
    """Return a deterministic semantic report for the current Army/faction boundary."""
    path = Path(path)
    Database(path).validate()
    with _connect(path) as connection:
        _check_schema(connection)
        identity_config = identity_config_from_connection(connection)
        army_lists = {row["id"]: row for row in _rows(connection, "army_lists")}
        metadata = {row["id"]: row for row in _rows(connection, "metadata_factions")}
        faction_rows = _rows(connection, "factions")
        army_units = _rows(connection, "army_units")
        unit_factions = _rows(connection, "unit_factions")
        units = [row for row in _rows(connection, "units") if row["source_defined"] == 1]

    army_ids = set(army_lists)
    metadata_ids = set(metadata)
    shared_ids = army_ids & metadata_ids
    identity_mismatches = [
        {
            "id": army_id,
            "armyList": {"name": army_lists[army_id]["name"], "slug": army_lists[army_id]["slug"]},
            "metadataFaction": {
                "name": metadata[army_id]["name"],
                "slug": metadata[army_id]["slug"],
            },
        }
        for army_id in sorted(shared_ids)
        if (army_lists[army_id]["name"], army_lists[army_id]["slug"])
        != (metadata[army_id]["name"], metadata[army_id]["slug"])
    ]

    aliases = [
        {"sourceId": source_id, "canonicalId": canonical_id}
        for source_id, canonical_id in sorted(identity_config.army_aliases.items())
        if source_id != canonical_id
    ]
    canonical_source_ids = {
        identity_config.canonical_army_id(army_id) for army_id in army_ids
    }

    application_armies = Database(path).list_armies()
    role_counts = Counter(army["role"] for army in application_armies)
    playable_counts = Counter(bool(army["playable"]) for army in application_armies)

    reinforcement_rows = [row for row in army_lists.values() if row["kind"] == "reinforcement"]
    reinforcement_parent_missing = [
        row["id"]
        for row in reinforcement_rows
        if not isinstance(metadata.get(row["id"], {}).get("parent"), int)
        or metadata[row["id"]]["parent"] not in metadata_ids
    ]
    ordinary_reinforcement_links = [
        row for row in army_lists.values() if row["reinforcement_id"] is not None
    ]

    registry_ids = {row["id"] for row in faction_rows}
    registry_without_list = sorted(registry_ids - army_ids)
    membership_ids = {row["faction_id"] for row in unit_factions}
    membership_without_list = sorted(membership_ids - army_ids)
    canonical_ids = {
        row["canonical_faction_id"]
        for row in units
        if isinstance(row["canonical_faction_id"], int)
    }
    canonical_without_list = sorted(canonical_ids - army_ids)

    standard_by_unit: dict[int, set[int]] = defaultdict(set)
    mercenary_by_unit: dict[int, set[int]] = defaultdict(set)
    for row in army_units:
        target = mercenary_by_unit if row["availability_kind"] == "mercenary" else standard_by_unit
        target[row["unit_id"]].add(row["army_id"])
    memberships_by_unit: dict[int, set[int]] = defaultdict(set)
    for row in unit_factions:
        memberships_by_unit[row["unit_id"]].add(row["faction_id"])

    declared_extra_references: Counter[int] = Counter()
    standard_missing_references: Counter[int] = Counter()
    differing_units = 0
    for unit_id in sorted(set(standard_by_unit) | set(memberships_by_unit)):
        declared = memberships_by_unit[unit_id]
        standard = standard_by_unit[unit_id]
        extra = declared - standard
        missing = standard - declared
        if extra or missing:
            differing_units += 1
        declared_extra_references.update(extra)
        standard_missing_references.update(missing)

    availability_counts = Counter(row["availability_kind"] for row in army_units)
    null_availability = sum(row["availability_kind"] is None for row in army_units)

    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "database": path.name,
        "summary": {
            "sourceArmyListCount": len(army_lists),
            "metadataFactionCount": len(metadata),
            "sharedArmyMetadataIdentityCount": len(shared_ids),
            "armyMetadataNameSlugMismatchCount": len(identity_mismatches),
            "applicationArmyIdentityCount": len(application_armies),
            "canonicalizedSourceArmyIdentityCount": len(canonical_source_ids),
            "ordinarySourceListCount": sum(row["kind"] == "army" for row in army_lists.values()),
            "reinforcementSourceListCount": len(reinforcement_rows),
            "playableApplicationArmyCount": playable_counts[True],
            "nonPlayableApplicationArmyCount": playable_counts[False],
            "factionIdentityRegistryCount": len(registry_ids),
            "factionIdentityWithoutArmyListCount": len(registry_without_list),
            "armyUnitOccurrenceCount": len(army_units),
            "declaredUnitFactionMembershipCount": len(unit_factions),
            "unitsWithMembershipBeyondStandardOccurrencesCount": differing_units,
            "extraDeclaredMembershipReferenceCount": sum(declared_extra_references.values()),
            "standardOccurrenceMissingDeclaredMembershipCount": sum(
                standard_missing_references.values()
            ),
            "sourceCanonicalFactionWithoutArmyListCount": len(canonical_without_list),
            "nullAvailabilityKindCount": null_availability,
        },
        "applicationRoles": {
            role: role_counts[role]
            for role in ("main", "sectorial", "non_aligned", "grouping", "reinforcement", "unknown")
        },
        "sourceIdentityOverlap": {
            "armyOnlyIds": sorted(army_ids - metadata_ids),
            "metadataOnlyIds": sorted(metadata_ids - army_ids),
            "nameSlugMismatches": identity_mismatches,
            "configuredArmyAliases": aliases,
        },
        "hierarchy": {
            "ordinaryListsWithReinforcementLinkCount": len(ordinary_reinforcement_links),
            "distinctCanonicalReinforcementIds": sorted(
                {
                    identity_config.canonical_army_id(row["reinforcement_id"])
                    for row in ordinary_reinforcement_links
                }
            ),
            "reinforcementMetadataParentsWithoutMetadataIdentity": sorted(
                reinforcement_parent_missing
            ),
        },
        "gameWideFactionContext": {
            "identityRegistryWithoutArmyList": registry_without_list,
            "declaredMembershipFactionIdsWithoutArmyList": membership_without_list,
            "sourceCanonicalFactionIdsWithoutArmyList": canonical_without_list,
            "declaredMembershipExtrasByFaction": [
                {"factionId": faction_id, "referenceCount": count}
                for faction_id, count in sorted(declared_extra_references.items())
            ],
            "standardOccurrencesMissingFromDeclaredMembershipByFaction": [
                {"factionId": faction_id, "referenceCount": count}
                for faction_id, count in sorted(standard_missing_references.items())
            ],
            "availabilityKindCounts": {
                str(kind): count
                for kind, count in sorted(
                    availability_counts.items(), key=lambda item: str(item[0])
                )
            },
        },
        "fieldClassification": FIELD_CLASSIFICATION,
        "conclusions": [
            (
                "Infinity Army list identity is army-local source context; InfinityDB application "
                "identity is game-wide and may collapse reviewed source aliases while "
                "retaining every "
                "source list occurrence."
            ),
            (
                "army_lists and metadata_factions overlap exactly on current ID/name/slug "
                "identity, "
                "but list-roster/reinforcement semantics and metadata hierarchy/"
                "discontinued metadata "
                "remain separate source facts."
            ),
            (
                "army_units is concrete list availability, while unit_factions is a broader "
                "declared "
                "cross-army membership relation and cannot be reconstructed from current "
                "list rosters."
            ),
            (
                "units.canonical_faction_id is source origin/context, not ownership, "
                "playability, or "
                "availability."
            ),
            (
                "Application role/playability is a derived whole-game view: current source "
                "lists reduce "
                "to one canonical application army identity per reviewed alias group, with "
                "hierarchy "
                "and reinforcement relationships attached explicitly."
            ),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit_database(args.database)
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
