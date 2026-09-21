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
REPORT_FORMAT_VERSION = 2

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
        }
    except sqlite3.Error as exc:
        raise RelationshipSemanticsAuditError(f"Could not audit {path}: {exc}") from exc
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit deferred include/peripheral relationship semantics, including canonical "
            "include-target resolution and parent-payload invariance."
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
