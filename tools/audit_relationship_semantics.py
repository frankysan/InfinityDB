#!/usr/bin/env python3
"""Audit deferred include/peripheral relationship semantics in InfinityDB.

Include analysis resolves canonical targets and tests whether relationships are
invariant across source occurrences that share one canonical parent payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPORT_FORMAT = "InfinityDB relationship semantics audit"
REPORT_FORMAT_VERSION = 4

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "profile_includes": (
        "army_id",
        "unit_id",
        "group_id",
        "profile_id",
        "position",
        "target_group_id",
        "target_option_id",
        "quantity",
        "raw",
    ),
    "option_includes": (
        "army_id",
        "unit_id",
        "group_id",
        "option_id",
        "position",
        "target_group_id",
        "target_option_id",
        "quantity",
        "raw",
    ),
    "unit_option_includes": (
        "unit_id",
        "option_id",
        "position",
        "target_group_id",
        "target_option_id",
        "quantity",
        "raw",
    ),
    "profile_peripherals": (
        "occurrence_id",
        "army_id",
        "unit_id",
        "group_id",
        "profile_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "option_peripherals": (
        "occurrence_id",
        "army_id",
        "unit_id",
        "group_id",
        "option_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "peripherals": ("army_id", "id", "position", "name", "mercs"),
    "loadout_payload_occurrences": (
        "army_id",
        "unit_id",
        "group_id",
        "option_id",
        "loadout_payload_id",
        "position",
        "points",
        "swc",
    ),
    "profile_payload_occurrences": (
        "army_id",
        "unit_id",
        "group_id",
        "profile_id",
        "profile_payload_id",
        "position",
        "ava",
        "logo",
    ),
    "loadout_payloads": ("id", "logical_unit_id", "payload_sha256", "name", "minis", "disabled"),
    "logical_unit_sources": ("source_unit_id", "logical_unit_id"),

    "relations": ("army_id", "relation_id", "position", "min_count", "max_count", "is_group"),
    "relation_units": (
        "army_id", "relation_id", "relation_unit_id", "position", "unit_id", "profile_id", "per_parent"
    ),
    "relation_dependencies": (
        "army_id", "relation_id", "relation_unit_id", "dependency_id", "position",
        "unit_id", "profile_id", "group_id", "min_count", "min_dependant", "options", "raw",
    ),
    "units": ("id", "name", "source_defined", "source_role"),
    "army_lists": ("id", "name", "kind", "reinforcement_id"),
    "application_armies": ("id", "name", "role", "playable"),
    "application_army_sources": ("application_army_id", "source_army_id"),
    "application_army_reinforcement_parents": ("reinforcement_army_id", "parent_army_id"),
    "__infinity_metadata": ("key", "value"),
}


class RelationshipSemanticsAuditError(ValueError):
    """Raised when the selected database cannot be audited safely."""


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _validate_schema(connection: sqlite3.Connection) -> None:
    for table, required in REQUIRED_COLUMNS.items():
        present = _columns(connection, table)
        if not present:
            raise RelationshipSemanticsAuditError(f"Missing required table: {table}")
        missing = set(required) - present
        if missing:
            joined = ", ".join(sorted(missing))
            raise RelationshipSemanticsAuditError(f"Table {table} is missing columns: {joined}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', ("_meta",)
    ).fetchone()
    if row is None:
        return {}
    try:
        value = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _raw_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _fetch_rows(connection: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return list(connection.execute(f'SELECT * FROM "{table}"'))


def _payload_targets(
    connection: sqlite3.Connection,
) -> dict[tuple[int, int, int, int], tuple[int, int]]:
    rows = connection.execute(
        """
        SELECT o.army_id, o.unit_id, o.group_id, o.option_id,
               o.loadout_payload_id, p.logical_unit_id
        FROM loadout_payload_occurrences AS o
        JOIN loadout_payloads AS p ON p.id = o.loadout_payload_id
        """
    )
    return {
        (row["army_id"], row["unit_id"], row["group_id"], row["option_id"]): (
            row["loadout_payload_id"],
            row["logical_unit_id"],
        )
        for row in rows
    }


def _profile_payload_parents(
    connection: sqlite3.Connection,
) -> dict[tuple[int, int, int, int], int]:
    return {
        (row["army_id"], row["unit_id"], row["group_id"], row["profile_id"]): row[
            "profile_payload_id"
        ]
        for row in connection.execute(
            "SELECT army_id, unit_id, group_id, profile_id, profile_payload_id "
            "FROM profile_payload_occurrences"
        )
    }


def _loadout_payload_parents(
    connection: sqlite3.Connection,
) -> dict[tuple[int, int, int, int], int]:
    return {
        (row["army_id"], row["unit_id"], row["group_id"], row["option_id"]): row[
            "loadout_payload_id"
        ]
        for row in connection.execute(
            "SELECT army_id, unit_id, group_id, option_id, loadout_payload_id "
            "FROM loadout_payload_occurrences"
        )
    }


def _source_logical_units(connection: sqlite3.Connection) -> dict[int, int]:
    return {
        row["source_unit_id"]: row["logical_unit_id"]
        for row in connection.execute(
            "SELECT source_unit_id, logical_unit_id FROM logical_unit_sources"
        )
    }


def _audit_contextual_includes(
    rows: Iterable[sqlite3.Row],
    *,
    parent_id_field: str,
    targets: dict[tuple[int, int, int, int], tuple[int, int]],
    source_logical: dict[int, int],
    include_details: bool,
) -> dict[str, Any]:
    row_count = 0
    missing_targets = 0
    cross_logical_targets = 0
    raw_rows = 0
    payload_ids: set[int] = set()
    details: list[dict[str, Any]] = []
    for row in rows:
        row_count += 1
        target_key = (
            row["army_id"],
            row["unit_id"],
            row["target_group_id"],
            row["target_option_id"],
        )
        target = targets.get(target_key)
        if target is None:
            missing_targets += 1
            target_payload_id = None
            target_logical_id = None
        else:
            target_payload_id, target_logical_id = target
            payload_ids.add(target_payload_id)
            parent_logical_id = source_logical.get(row["unit_id"])
            if parent_logical_id is not None and target_logical_id != parent_logical_id:
                cross_logical_targets += 1
        if _raw_present(row["raw"]):
            raw_rows += 1
        if include_details:
            details.append(
                {
                    "armyId": row["army_id"],
                    "unitId": row["unit_id"],
                    "groupId": row["group_id"],
                    "parentId": row[parent_id_field],
                    "position": row["position"],
                    "targetGroupId": row["target_group_id"],
                    "targetOptionId": row["target_option_id"],
                    "targetPayloadId": target_payload_id,
                    "targetLogicalUnitId": target_logical_id,
                    "quantity": row["quantity"],
                    "raw": row["raw"],
                }
            )
    result: dict[str, Any] = {
        "rowCount": row_count,
        "resolvedTargetCount": row_count - missing_targets,
        "missingTargetCount": missing_targets,
        "distinctCanonicalTargetPayloads": len(payload_ids),
        "crossLogicalTargetCount": cross_logical_targets,
        "rawFallbackRowCount": raw_rows,
    }
    if include_details:
        result["rows"] = details
    return result


def _include_signature_item(
    row: sqlite3.Row,
    *,
    targets: dict[tuple[int, int, int, int], tuple[int, int]],
) -> tuple[Any, ...]:
    target = targets.get(
        (
            row["army_id"],
            row["unit_id"],
            row["target_group_id"],
            row["target_option_id"],
        )
    )
    target_payload_id = target[0] if target is not None else None
    return (row["position"], target_payload_id, row["quantity"], row["raw"])


def _audit_parent_payload_invariance(
    rows: Iterable[sqlite3.Row],
    *,
    parent_payloads: dict[tuple[int, int, int, int], int],
    parent_id_field: str,
    targets: dict[tuple[int, int, int, int], tuple[int, int]],
    include_details: bool,
) -> dict[str, Any]:
    rows_by_parent: dict[tuple[int, int, int, int], list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        rows_by_parent[
            (
                row["army_id"],
                row["unit_id"],
                row["group_id"],
                row[parent_id_field],
            )
        ].append(row)

    affected_payload_ids = {
        parent_payloads[parent_key]
        for parent_key in rows_by_parent
        if parent_key in parent_payloads
    }
    unmapped_parent_rows = sum(
        len(parent_rows)
        for parent_key, parent_rows in rows_by_parent.items()
        if parent_key not in parent_payloads
    )
    signatures_by_payload: dict[int, dict[tuple[Any, ...], list[tuple[int, int, int, int]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    unresolved_target_rows = 0
    for parent_key, payload_id in parent_payloads.items():
        if payload_id not in affected_payload_ids:
            continue
        parent_rows = sorted(rows_by_parent.get(parent_key, ()), key=lambda row: row["position"])
        signature_items = tuple(
            _include_signature_item(row, targets=targets) for row in parent_rows
        )
        unresolved_target_rows += sum(1 for item in signature_items if item[1] is None)
        signatures_by_payload[payload_id][signature_items].append(parent_key)

    payloads_with_multiple_occurrences = 0
    variant_payload_ids: list[int] = []
    for payload_id, signatures in signatures_by_payload.items():
        occurrence_count = sum(len(keys) for keys in signatures.values())
        if occurrence_count > 1:
            payloads_with_multiple_occurrences += 1
        if len(signatures) > 1:
            variant_payload_ids.append(payload_id)

    result: dict[str, Any] = {
        "status": (
            "unresolved_parents"
            if unmapped_parent_rows
            else "unresolved_targets"
            if unresolved_target_rows
            else "contextual_variants"
            if variant_payload_ids
            else "payload_invariant"
        ),
        "affectedCanonicalParentPayloadCount": len(signatures_by_payload),
        "affectedCanonicalParentPayloadsWithMultipleOccurrences": (
            payloads_with_multiple_occurrences
        ),
        "variantCanonicalParentPayloadCount": len(variant_payload_ids),
        "unmappedParentRowCount": unmapped_parent_rows,
        "unresolvedTargetRowCount": unresolved_target_rows,
    }
    if include_details:
        variants: list[dict[str, Any]] = []
        for payload_id in sorted(variant_payload_ids):
            signatures = signatures_by_payload[payload_id]
            variant_signatures: list[dict[str, Any]] = []
            for signature, parent_keys in sorted(
                signatures.items(), key=lambda item: repr(item[0])
            ):
                variant_signatures.append(
                    {
                        "signature": [
                            {
                                "position": item[0],
                                "targetPayloadId": item[1],
                                "quantity": item[2],
                                "raw": item[3],
                            }
                            for item in signature
                        ],
                        "occurrences": [
                            {
                                "armyId": key[0],
                                "unitId": key[1],
                                "groupId": key[2],
                                "parentId": key[3],
                            }
                            for key in sorted(parent_keys)
                        ],
                    }
                )
            variants.append(
                {
                    "parentPayloadId": payload_id,
                    "variants": variant_signatures,
                }
            )
        result["variantParentPayloads"] = variants
    return result


def _audit_shared_includes(
    rows: Iterable[sqlite3.Row],
    *,
    targets: dict[tuple[int, int, int, int], tuple[int, int]],
    source_logical: dict[int, int],
    include_details: bool,
) -> dict[str, Any]:
    by_source_target: dict[tuple[int, int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for (army_id, unit_id, group_id, option_id), (payload_id, logical_id) in targets.items():
        by_source_target[(unit_id, group_id, option_id)].append((army_id, payload_id, logical_id))

    row_count = 0
    missing_targets = 0
    multi_payload_targets = 0
    multi_logical_targets = 0
    cross_logical_targets = 0
    raw_rows = 0
    details: list[dict[str, Any]] = []
    for row in rows:
        row_count += 1
        candidates = by_source_target.get(
            (row["unit_id"], row["target_group_id"], row["target_option_id"]), []
        )
        payload_ids = {candidate[1] for candidate in candidates}
        logical_ids = {candidate[2] for candidate in candidates}
        if not candidates:
            missing_targets += 1
        if len(payload_ids) > 1:
            multi_payload_targets += 1
        if len(logical_ids) > 1:
            multi_logical_targets += 1
        parent_logical_id = source_logical.get(row["unit_id"])
        if parent_logical_id is not None and any(
            logical_id != parent_logical_id for logical_id in logical_ids
        ):
            cross_logical_targets += 1
        if _raw_present(row["raw"]):
            raw_rows += 1
        if include_details:
            details.append(
                {
                    "unitId": row["unit_id"],
                    "optionId": row["option_id"],
                    "position": row["position"],
                    "targetGroupId": row["target_group_id"],
                    "targetOptionId": row["target_option_id"],
                    "targetArmyIds": sorted(candidate[0] for candidate in candidates),
                    "targetPayloadIds": sorted(payload_ids),
                    "targetLogicalUnitIds": sorted(logical_ids),
                    "quantity": row["quantity"],
                    "raw": row["raw"],
                }
            )
    result: dict[str, Any] = {
        "rowCount": row_count,
        "resolvedTargetCount": row_count - missing_targets,
        "missingTargetCount": missing_targets,
        "multiPayloadTargetCount": multi_payload_targets,
        "multiLogicalTargetCount": multi_logical_targets,
        "crossLogicalTargetCount": cross_logical_targets,
        "rawFallbackRowCount": raw_rows,
    }
    if include_details:
        result["rows"] = details
    return result


def _candidate_peripheral_key(row: sqlite3.Row) -> tuple[Any, Any]:
    return row["name"], row["mercs"]


def _audit_peripherals(
    connection: sqlite3.Connection, *, include_details: bool
) -> dict[str, Any]:
    definitions = _fetch_rows(connection, "peripherals")
    definition_by_id = {(row["army_id"], row["id"]): row for row in definitions}
    identities_by_candidate: dict[tuple[Any, Any], set[tuple[int, int]]] = defaultdict(set)
    for row in definitions:
        identities_by_candidate[_candidate_peripheral_key(row)].add((row["army_id"], row["id"]))

    occurrence_results: dict[str, Any] = {}
    total_missing = 0
    total_raw = 0
    for table, parent_key in (
        ("profile_peripherals", ("unit_id", "group_id", "profile_id", "position")),
        ("option_peripherals", ("unit_id", "group_id", "option_id", "position")),
    ):
        rows = _fetch_rows(connection, table)
        candidates_by_parent: dict[tuple[Any, ...], set[tuple[Any, Any]]] = defaultdict(set)
        missing = 0
        raw_rows = 0
        details: list[dict[str, Any]] = []
        for row in rows:
            definition = definition_by_id.get((row["army_id"], row["item_id"]))
            if definition is None:
                missing += 1
            else:
                candidate = _candidate_peripheral_key(definition)
                candidates_by_parent[tuple(row[field] for field in parent_key)].add(candidate)
            if _raw_present(row["raw"]):
                raw_rows += 1
            if include_details:
                details.append(
                    {
                        "armyId": row["army_id"],
                        "unitId": row["unit_id"],
                        "groupId": row["group_id"],
                        "parentId": row[parent_key[2]],
                        "position": row["position"],
                        "itemId": row["item_id"],
                        "name": definition["name"] if definition is not None else None,
                        "mercs": definition["mercs"] if definition is not None else None,
                        "quantity": row["quantity"],
                        "raw": row["raw"],
                    }
                )
        contextual_variants = sum(1 for values in candidates_by_parent.values() if len(values) > 1)
        result: dict[str, Any] = {
            "rowCount": len(rows),
            "resolvedDefinitionCount": len(rows) - missing,
            "missingDefinitionCount": missing,
            "sameSourceContextVariantCount": contextual_variants,
            "rawFallbackRowCount": raw_rows,
        }
        if include_details:
            result["rows"] = details
        occurrence_results[table.removesuffix("_peripherals")] = result
        total_missing += missing
        total_raw += raw_rows

    candidate_details = [
        {
            "name": key[0],
            "mercs": key[1],
            "rawIdentities": [
                {"armyId": army_id, "id": peripheral_id}
                for army_id, peripheral_id in sorted(identities)
            ],
        }
        for key, identities in sorted(
            identities_by_candidate.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
        )
        if len(identities) > 1
    ]

    result = {
        "candidateIdentity": {
            "fields": ["name", "mercs"],
            "status": "diagnostic_only",
            "reason": (
                "Peripheral IDs are army-local. Exact name + mercs is useful for measuring "
                "cross-army repetition but is not yet an accepted canonical identity."
            ),
        },
        "definitionCount": len(definitions),
        "candidateDefinitionCount": len(identities_by_candidate),
        "candidateDefinitionsWithMultipleRawIds": sum(
            1 for identities in identities_by_candidate.values() if len(identities) > 1
        ),
        "missingDefinitionCount": total_missing,
        "rawFallbackRowCount": total_raw,
        "occurrences": occurrence_results,
    }
    if include_details:
        result["repeatedCandidateDefinitions"] = candidate_details
    return result


def _relation_shape_key(row: sqlite3.Row, member_count: int, dependency_count: int) -> tuple[Any, ...]:
    return (
        row["min_count"],
        row["max_count"],
        row["is_group"],
        member_count,
        dependency_count,
    )


def _relation_cardinality_kind(min_count: int | None, max_count: int | None) -> str:
    if min_count == 1 and max_count == 1:
        return "exactly-one"
    if max_count is None:
        return "minimum-only"
    if min_count == max_count:
        return "exact-count"
    return "bounded-range"


def _relation_semantic_family(
    relation: sqlite3.Row,
    members: list[sqlite3.Row],
    dependencies_by_member: dict[tuple[int, int, int], list[sqlite3.Row]],
    logical_ids: list[int | None],
    dependency_logical_ids: list[int | None],
) -> str:
    endpoints = logical_ids + dependency_logical_ids
    if any(value is None for value in endpoints):
        return "unresolved-source-endpoint"

    distinct_logical_ids = {value for value in endpoints if value is not None}
    if len(distinct_logical_ids) > 1:
        return "cross-logical-shared-cardinality"

    has_selectors_or_dependencies = False
    for member in members:
        key = (member["army_id"], member["relation_id"], member["relation_unit_id"])
        if (
            member["profile_id"] is not None
            or member["per_parent"] is not None
            or dependencies_by_member[key]
        ):
            has_selectors_or_dependencies = True
            break

    source_unit_ids = {member["unit_id"] for member in members}
    if (
        len(members) >= 2
        and len(source_unit_ids) >= 2
        and not has_selectors_or_dependencies
        and not relation["is_group"]
        and relation["min_count"] == 1
        and relation["max_count"] == 1
    ):
        return "same-logical-cross-context-exclusive"
    if has_selectors_or_dependencies:
        return "single-logical-profile-dependency"
    return "single-logical-cardinality"


def _selector_candidate_domains(
    selector: int | None,
    unit_id: int,
    *,
    group_ids_by_unit: dict[int, set[int]],
    profile_ids_by_unit: dict[int, set[int]],
    option_ids_by_unit: dict[int, set[int]],
) -> list[str]:
    if selector is None:
        return []
    domains: list[str] = []
    if selector in group_ids_by_unit.get(unit_id, set()):
        domains.append("profile-group-id")
    if selector in profile_ids_by_unit.get(unit_id, set()):
        domains.append("profile-id")
    if selector in option_ids_by_unit.get(unit_id, set()):
        domains.append("option-id")
    return domains


def _selector_domain_key(domains: list[str]) -> str:
    return "+".join(domains) if domains else "no-coordinate-match"


def _audit_relation_structures(
    connection: sqlite3.Connection,
    *,
    source_logical: dict[int, int],
    include_details: bool,
) -> dict[str, Any]:
    relation_rows = _fetch_rows(connection, "relations")
    member_rows = _fetch_rows(connection, "relation_units")
    dependency_rows = _fetch_rows(connection, "relation_dependencies")
    unit_rows = {row["id"]: row for row in _fetch_rows(connection, "units")}
    army_names = {row["id"]: row["name"] for row in _fetch_rows(connection, "army_lists")}
    group_ids_by_unit: dict[int, set[int]] = defaultdict(set)
    profile_ids_by_unit: dict[int, set[int]] = defaultdict(set)
    option_ids_by_unit: dict[int, set[int]] = defaultdict(set)
    for row in _fetch_rows(connection, "profile_payload_occurrences"):
        group_ids_by_unit[row["unit_id"]].add(row["group_id"])
        profile_ids_by_unit[row["unit_id"]].add(row["profile_id"])
    for row in _fetch_rows(connection, "loadout_payload_occurrences"):
        option_ids_by_unit[row["unit_id"]].add(row["option_id"])

    members_by_relation: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
    for row in member_rows:
        members_by_relation[(row["army_id"], row["relation_id"])].append(row)
    dependencies_by_member: dict[tuple[int, int, int], list[sqlite3.Row]] = defaultdict(list)
    for row in dependency_rows:
        dependencies_by_member[
            (row["army_id"], row["relation_id"], row["relation_unit_id"])
        ].append(row)

    unresolved_member_rows = [row for row in member_rows if row["unit_id"] not in source_logical]
    unresolved_dependency_rows = [
        row for row in dependency_rows if row["unit_id"] not in source_logical
    ]
    source_placeholder_member_rows = [
        row
        for row in member_rows
        if row["unit_id"] in unit_rows and not unit_rows[row["unit_id"]]["source_defined"]
    ]

    shape_counts: dict[tuple[Any, ...], int] = defaultdict(int)
    fully_resolved = 0
    unresolved_relations = 0
    single_logical = 0
    cross_logical = 0
    details: list[dict[str, Any]] = []
    signatures: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    semantic_family_counts: dict[str, int] = defaultdict(int)
    cardinality_kind_counts: dict[str, int] = defaultdict(int)
    member_selector_domain_counts: dict[str, int] = defaultdict(int)
    dependency_selector_domain_counts: dict[str, int] = defaultdict(int)
    selector_free_resolved = 0
    selector_bearing_resolved = 0

    for relation in relation_rows:
        key = (relation["army_id"], relation["relation_id"])
        members = sorted(members_by_relation.get(key, ()), key=lambda row: row["position"] or 0)
        dependency_count = sum(
            len(dependencies_by_member[(row["army_id"], row["relation_id"], row["relation_unit_id"])])
            for row in members
        )
        shape_counts[_relation_shape_key(relation, len(members), dependency_count)] += 1
        logical_ids = [source_logical.get(row["unit_id"]) for row in members]
        dependency_logical_ids = [
            source_logical.get(dep["unit_id"])
            for member in members
            for dep in dependencies_by_member[
                (member["army_id"], member["relation_id"], member["relation_unit_id"])
            ]
        ]
        resolved = all(value is not None for value in logical_ids + dependency_logical_ids)
        semantic_family = _relation_semantic_family(
            relation, members, dependencies_by_member, logical_ids, dependency_logical_ids
        )
        cardinality_kind = _relation_cardinality_kind(
            relation["min_count"], relation["max_count"]
        )
        semantic_family_counts[semantic_family] += 1
        cardinality_kind_counts[cardinality_kind] += 1
        relation_has_selectors = any(
            member["profile_id"] is not None
            or member["per_parent"] is not None
            or dependencies_by_member[
                (member["army_id"], member["relation_id"], member["relation_unit_id"])
            ]
            for member in members
        )
        if resolved and relation_has_selectors:
            selector_bearing_resolved += 1
        elif resolved:
            selector_free_resolved += 1
        if resolved:
            fully_resolved += 1
            distinct = set(logical_ids + dependency_logical_ids)
            if len(distinct) == 1:
                single_logical += 1
            elif len(distinct) > 1:
                cross_logical += 1
        else:
            unresolved_relations += 1

        signature_members: list[tuple[Any, ...]] = []
        detail_members: list[dict[str, Any]] = []
        for member in members:
            member_key = (member["army_id"], member["relation_id"], member["relation_unit_id"])
            deps = sorted(dependencies_by_member[member_key], key=lambda row: row["position"] or 0)
            canonical_unit = source_logical.get(member["unit_id"])
            member_selector_domains = _selector_candidate_domains(
                member["profile_id"],
                member["unit_id"],
                group_ids_by_unit=group_ids_by_unit,
                profile_ids_by_unit=profile_ids_by_unit,
                option_ids_by_unit=option_ids_by_unit,
            )
            if member["profile_id"] is not None:
                member_selector_domain_counts[_selector_domain_key(member_selector_domains)] += 1
            signature_deps = tuple(
                (
                    source_logical.get(dep["unit_id"]),
                    dep["unit_id"] if source_logical.get(dep["unit_id"]) is None else None,
                    dep["profile_id"],
                    dep["group_id"],
                    dep["min_count"],
                    dep["min_dependant"],
                    dep["options"],
                    dep["raw"],
                )
                for dep in deps
            )
            signature_members.append(
                (
                    canonical_unit,
                    member["unit_id"] if canonical_unit is None else None,
                    member["profile_id"],
                    member["per_parent"],
                    signature_deps,
                )
            )
            for dep in deps:
                if dep["profile_id"] is not None:
                    dependency_selector_domains = _selector_candidate_domains(
                        dep["profile_id"],
                        dep["unit_id"],
                        group_ids_by_unit=group_ids_by_unit,
                        profile_ids_by_unit=profile_ids_by_unit,
                        option_ids_by_unit=option_ids_by_unit,
                    )
                    dependency_selector_domain_counts[
                        _selector_domain_key(dependency_selector_domains)
                    ] += 1
            if include_details:
                unit = unit_rows.get(member["unit_id"])
                detail_members.append(
                    {
                        "relationUnitId": member["relation_unit_id"],
                        "sourceUnitId": member["unit_id"],
                        "sourceUnitName": unit["name"] if unit is not None else None,
                        "sourceDefined": bool(unit["source_defined"]) if unit is not None else None,
                        "logicalUnitId": canonical_unit,
                        "profileSelector": member["profile_id"],
                        "profileSelectorCandidateDomains": member_selector_domains,
                        "perParent": member["per_parent"],
                        "dependencies": [
                            {
                                "sourceUnitId": dep["unit_id"],
                                "logicalUnitId": source_logical.get(dep["unit_id"]),
                                "profileSelector": dep["profile_id"],
                                "profileSelectorCandidateDomains": _selector_candidate_domains(
                                    dep["profile_id"],
                                    dep["unit_id"],
                                    group_ids_by_unit=group_ids_by_unit,
                                    profile_ids_by_unit=profile_ids_by_unit,
                                    option_ids_by_unit=option_ids_by_unit,
                                ),
                                "groupSelector": dep["group_id"],
                                "minCount": dep["min_count"],
                                "minDependant": dep["min_dependant"],
                                "options": dep["options"],
                                "raw": dep["raw"],
                            }
                            for dep in deps
                        ],
                    }
                )
        signatures[
            (relation["min_count"], relation["max_count"], relation["is_group"], tuple(signature_members))
        ].add(relation["army_id"])
        if include_details:
            details.append(
                {
                    "armyId": relation["army_id"],
                    "armyName": army_names.get(relation["army_id"]),
                    "relationId": relation["relation_id"],
                    "minCount": relation["min_count"],
                    "maxCount": relation["max_count"],
                    "isGroup": bool(relation["is_group"]),
                    "resolution": "complete" if resolved else "unresolved_source_endpoint",
                    "semanticFamily": semantic_family,
                    "cardinalityKind": cardinality_kind,
                    "canonicalLogicalUnitIds": sorted(
                        value
                        for value in set(logical_ids + dependency_logical_ids)
                        if value is not None
                    ),
                    "members": detail_members,
                }
            )

    repeated_signatures = [armies for armies in signatures.values() if len(armies) > 1]
    result: dict[str, Any] = {
        "relationCount": len(relation_rows),
        "memberCount": len(member_rows),
        "dependencyCount": len(dependency_rows),
        "fullyResolvedRelationCount": fully_resolved,
        "unresolvedRelationCount": unresolved_relations,
        "singleLogicalEndpointSetRelationCount": single_logical,
        "crossLogicalEndpointSetRelationCount": cross_logical,
        "memberEndpointResolution": {
            "resolvedCount": len(member_rows) - len(unresolved_member_rows),
            "unresolvedCount": len(unresolved_member_rows),
            "unresolvedSourceUnitIds": sorted({row["unit_id"] for row in unresolved_member_rows}),
            "sourcePlaceholderRowCount": len(source_placeholder_member_rows),
        },
        "dependencyEndpointResolution": {
            "resolvedCount": len(dependency_rows) - len(unresolved_dependency_rows),
            "unresolvedCount": len(unresolved_dependency_rows),
            "unresolvedSourceUnitIds": sorted(
                {row["unit_id"] for row in unresolved_dependency_rows}
            ),
        },
        "semanticClassification": {
            "classifiedResolvedRelationCount": sum(
                count
                for family, count in semantic_family_counts.items()
                if family != "unresolved-source-endpoint"
            ),
            "unresolvedRelationCount": semantic_family_counts.get(
                "unresolved-source-endpoint", 0
            ),
            "selectorFreeResolvedRelationCount": selector_free_resolved,
            "selectorBearingResolvedRelationCount": selector_bearing_resolved,
            "familyCounts": dict(sorted(semantic_family_counts.items())),
            "cardinalityKindCounts": dict(sorted(cardinality_kind_counts.items())),
            "interpretation": (
                "Resolved source relations separate into four application-semantic families: "
                "same-logical cross-context exclusivity, cross-logical shared cardinality, "
                "single-logical profile/dependency constraints, and single-logical cardinality "
                "constraints. Selectors remain contextual fields on the relation/member rather "
                "than facts on the logical Unit. Unresolved source endpoints remain a fifth "
                "explicit state and are not classified by inference."
            ),
        },
        "profileSelectorCoordinateCandidates": {
            "member": dict(sorted(member_selector_domain_counts.items())),
            "dependency": dict(sorted(dependency_selector_domain_counts.items())),
            "interpretation": (
                "Army's source field is named profile, but its numeric values do not map to one "
                "stable normalized coordinate domain. The audit therefore reports mechanical "
                "matches against known profile-group, profile, and option IDs without choosing "
                "one interpretation. These candidates are diagnostic only."
            ),
        },
        "selectors": {
            "memberProfileSelectorCount": sum(row["profile_id"] is not None for row in member_rows),
            "memberPerParentCount": sum(row["per_parent"] is not None for row in member_rows),
            "dependencyProfileSelectorCount": sum(
                row["profile_id"] is not None for row in dependency_rows
            ),
            "dependencyGroupSelectorCount": sum(
                row["group_id"] is not None for row in dependency_rows
            ),
            "dependencyMinCountCount": sum(
                row["min_count"] is not None for row in dependency_rows
            ),
            "dependencyMinDependantCount": sum(
                row["min_dependant"] is not None for row in dependency_rows
            ),
            "dependencyOptionsCount": sum(row["options"] is not None for row in dependency_rows),
            "dependencyRawFallbackCount": sum(_raw_present(row["raw"]) for row in dependency_rows),
        },
        "shapeCounts": [
            {
                "minCount": key[0],
                "maxCount": key[1],
                "isGroup": bool(key[2]),
                "memberCount": key[3],
                "dependencyCount": key[4],
                "relationCount": value,
            }
            for key, value in sorted(shape_counts.items(), key=lambda item: repr(item[0]))
        ],
        "canonicalSignatureCount": len(signatures),
        "canonicalSignaturesRepeatedAcrossArmies": len(repeated_signatures),
        "interpretation": (
            "Relation rows are source-context selection/composition constraints. Canonicalizing "
            "member Unit identities does not make a relation redundant: same-logical endpoint "
            "sets can still constrain ordinary versus Reinforcement occurrences or profile-level "
            "forms. The semantic-family classification is structural and preserves every source "
            "selector; it does not promote profile/group/options/perParent/min/minDependant fields "
            "to logical-Unit facts."
        ),
    }
    if include_details:
        result["relations"] = details
    return result


def _audit_reinforcement_sections(
    connection: sqlite3.Connection, *, include_details: bool
) -> dict[str, Any]:
    army_rows = _fetch_rows(connection, "army_lists")
    application_armies = {row["id"]: row for row in _fetch_rows(connection, "application_armies")}
    source_to_application = {
        row["source_army_id"]: row["application_army_id"]
        for row in _fetch_rows(connection, "application_army_sources")
    }
    materialized = {
        (row["reinforcement_army_id"], row["parent_army_id"])
        for row in _fetch_rows(connection, "application_army_reinforcement_parents")
    }
    expected: set[tuple[int, int]] = set()
    unresolved: list[dict[str, int]] = []
    details: list[dict[str, Any]] = []
    for row in army_rows:
        reinforcement_source = row["reinforcement_id"]
        if row["kind"] == "reinforcement" or reinforcement_source is None:
            continue
        parent_application = source_to_application.get(row["id"])
        reinforcement_application = source_to_application.get(reinforcement_source)
        if parent_application is None or reinforcement_application is None:
            unresolved.append(
                {"parentSourceArmyId": row["id"], "reinforcementSourceArmyId": reinforcement_source}
            )
            continue
        edge = (reinforcement_application, parent_application)
        expected.add(edge)
        if include_details:
            details.append(
                {
                    "parentSourceArmyId": row["id"],
                    "parentApplicationArmyId": parent_application,
                    "reinforcementSourceArmyId": reinforcement_source,
                    "reinforcementApplicationArmyId": reinforcement_application,
                    "materialized": edge in materialized,
                }
            )
    missing = expected - materialized
    unexpected = materialized - expected
    reinforcement_apps = [row for row in application_armies.values() if row["role"] == "reinforcement"]
    role_mismatch = [
        row["id"]
        for row in reinforcement_apps
        if not row["playable"]
    ]
    result: dict[str, Any] = {
        "sourceReinforcementSectionCount": sum(row["kind"] == "reinforcement" for row in army_rows),
        "applicationReinforcementSectionCount": len(reinforcement_apps),
        "sourceParentLinkCount": sum(
            row["kind"] != "reinforcement" and row["reinforcement_id"] is not None
            for row in army_rows
        ),
        "expectedCanonicalParentLinkCount": len(expected),
        "materializedCanonicalParentLinkCount": len(materialized),
        "missingCanonicalParentLinkCount": len(missing),
        "unexpectedCanonicalParentLinkCount": len(unexpected),
        "unresolvedSourceMappingCount": len(unresolved),
        "nonSelectableReinforcementApplicationCount": len(role_mismatch),
        "interpretation": (
            "Application role=reinforcement represents a selectable Reinforcement Section/pool "
            "attached to one or more ordinary Army contexts, not an independently legal Army "
            "List. Source list/profile/AVA occurrences remain contextual evidence."
        ),
    }
    if include_details:
        result["parentLinks"] = details
        result["missingCanonicalParentLinks"] = [
            {"reinforcementArmyId": edge[0], "parentArmyId": edge[1]}
            for edge in sorted(missing)
        ]
        result["unexpectedCanonicalParentLinks"] = [
            {"reinforcementArmyId": edge[0], "parentArmyId": edge[1]}
            for edge in sorted(unexpected)
        ]
        result["unresolvedSourceMappings"] = unresolved
    return result


def audit_database(path: Path, *, include_details: bool = False) -> dict[str, Any]:
    if not path.is_file():
        raise RelationshipSemanticsAuditError(f"Database does not exist: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        _validate_schema(connection)
        targets = _payload_targets(connection)
        source_logical = _source_logical_units(connection)
        profile_rows = _fetch_rows(connection, "profile_includes")
        loadout_rows = _fetch_rows(connection, "option_includes")
        profile_parents = _profile_payload_parents(connection)
        loadout_parents = _loadout_payload_parents(connection)
        includes = {
            "profile": _audit_contextual_includes(
                profile_rows,
                parent_id_field="profile_id",
                targets=targets,
                source_logical=source_logical,
                include_details=include_details,
            ),
            "loadout": _audit_contextual_includes(
                loadout_rows,
                parent_id_field="option_id",
                targets=targets,
                source_logical=source_logical,
                include_details=include_details,
            ),
            "unitOption": _audit_shared_includes(
                _fetch_rows(connection, "unit_option_includes"),
                targets=targets,
                source_logical=source_logical,
                include_details=include_details,
            ),
        }
        includes["profile"]["parentPayloadInvariance"] = _audit_parent_payload_invariance(
            profile_rows,
            parent_payloads=profile_parents,
            parent_id_field="profile_id",
            targets=targets,
            include_details=include_details,
        )
        includes["loadout"]["parentPayloadInvariance"] = _audit_parent_payload_invariance(
            loadout_rows,
            parent_payloads=loadout_parents,
            parent_id_field="option_id",
            targets=targets,
            include_details=include_details,
        )
        metadata = _metadata(connection)
        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "path": str(path),
                "sha256": _sha256(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "includes": includes,
            "peripherals": _audit_peripherals(connection, include_details=include_details),
            "relations": _audit_relation_structures(
                connection, source_logical=source_logical, include_details=include_details
            ),
            "reinforcementSections": _audit_reinforcement_sections(
                connection, include_details=include_details
            ),
        }
    except sqlite3.Error as exc:
        raise RelationshipSemanticsAuditError(f"Could not audit {path}: {exc}") from exc
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit deferred relationship semantics, including canonical include-target resolution, "
            "relation/dependency endpoint resolution, and Reinforcement-section context."
        )
    )
    parser.add_argument("database", type=Path, help="Path to infinity.db")
    parser.add_argument("--details", action="store_true", help="Include row-level evidence")
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database, include_details=args.details)
    except RelationshipSemanticsAuditError as exc:
        raise SystemExit(str(exc)) from exc
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Relationship audit written: {args.output}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
