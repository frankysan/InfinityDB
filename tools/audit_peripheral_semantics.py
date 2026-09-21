#!/usr/bin/env python3
"""Audit peripheral identity, availability, and attachment semantics in InfinityDB."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPORT_FORMAT = "InfinityDB peripheral semantics audit"
REPORT_FORMAT_VERSION = 1

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "peripherals": ("army_id", "id", "position", "name", "mercs"),
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
    "profile_payload_occurrences": (
        "army_id",
        "unit_id",
        "group_id",
        "profile_id",
        "profile_payload_id",
    ),
    "loadout_payload_occurrences": (
        "army_id",
        "unit_id",
        "group_id",
        "option_id",
        "loadout_payload_id",
    ),
    "__infinity_metadata": ("key", "value"),
}


class PeripheralSemanticsAuditError(ValueError):
    """Raised when the selected database cannot be audited safely."""


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _validate_schema(connection: sqlite3.Connection) -> None:
    for table, required in REQUIRED_COLUMNS.items():
        present = _columns(connection, table)
        if not present:
            raise PeripheralSemanticsAuditError(f"Missing required table: {table}")
        missing = set(required) - present
        if missing:
            joined = ", ".join(sorted(missing))
            raise PeripheralSemanticsAuditError(f"Table {table} is missing columns: {joined}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_rows(connection: sqlite3.Connection) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for row in connection.execute('SELECT key, value FROM "__infinity_metadata"'):
        try:
            result[row["key"]] = json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            result[row["key"]] = row["value"]
    return result


def _raw_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _definition_key(row: sqlite3.Row) -> tuple[int, Any]:
    return int(row["army_id"]), row["id"]


def _parent_key(row: sqlite3.Row, parent_id: str) -> tuple[int, Any, Any, Any]:
    return (
        int(row["army_id"]),
        row["unit_id"],
        row["group_id"],
        row[parent_id],
    )


def _audit_definitions(
    definitions: list[sqlite3.Row], *, include_details: bool
) -> tuple[dict[str, Any], dict[tuple[int, Any], sqlite3.Row]]:
    by_key = {_definition_key(row): row for row in definitions}
    by_name: dict[Any, list[sqlite3.Row]] = defaultdict(list)
    for row in definitions:
        by_name[row["name"]].append(row)

    repeated_names = {
        name: rows for name, rows in by_name.items() if name is not None and len(rows) > 1
    }
    mercs_variants = {
        name: rows
        for name, rows in repeated_names.items()
        if len({row["mercs"] for row in rows}) > 1
    }
    result: dict[str, Any] = {
        "definitionCount": len(definitions),
        "distinctNameCount": len({row["name"] for row in definitions if row["name"] is not None}),
        "unnamedDefinitionCount": sum(1 for row in definitions if row["name"] is None),
        "namesWithMultipleRawIdentities": len(repeated_names),
        "namesWithMercsVariants": len(mercs_variants),
        "identityCandidate": {
            "fields": ["name"],
            "status": "diagnostic_only",
            "reason": (
                "Peripheral IDs are army-local. Name is audited as a cross-army grouping "
                "candidate; mercs remains separate contextual source data and is not part "
                "of the candidate key."
            ),
        },
    }
    if include_details:
        result["mercsVariants"] = [
            {
                "name": name,
                "rawIdentities": [
                    {
                        "armyId": row["army_id"],
                        "id": row["id"],
                        "mercs": row["mercs"],
                    }
                    for row in sorted(rows, key=lambda item: (item["army_id"], item["id"]))
                ],
            }
            for name, rows in sorted(mercs_variants.items(), key=lambda item: str(item[0]))
        ]
    return result, by_key


def _audit_occurrences(
    rows: Iterable[sqlite3.Row],
    *,
    definitions: dict[tuple[int, Any], sqlite3.Row],
    parent_id: str,
    include_details: bool,
) -> tuple[dict[str, Any], dict[tuple[int, Any], set[str]]]:
    missing = 0
    raw_rows = 0
    referenced: dict[tuple[int, Any], set[str]] = defaultdict(set)
    details: list[dict[str, Any]] = []
    row_list = list(rows)
    for row in row_list:
        definition_key = (int(row["army_id"]), row["item_id"])
        definition = definitions.get(definition_key)
        if definition is None:
            missing += 1
        else:
            referenced[definition_key].add(str(parent_id))
        if _raw_present(row["raw"]):
            raw_rows += 1
        if include_details:
            details.append(
                {
                    "armyId": row["army_id"],
                    "unitId": row["unit_id"],
                    "groupId": row["group_id"],
                    "parentId": row[parent_id],
                    "itemId": row["item_id"],
                    "name": definition["name"] if definition is not None else None,
                    "mercs": definition["mercs"] if definition is not None else None,
                    "position": row["position"],
                    "displayOrder": row["display_order"],
                    "quantity": row["quantity"],
                    "raw": row["raw"],
                }
            )
    result: dict[str, Any] = {
        "rowCount": len(row_list),
        "resolvedDefinitionCount": len(row_list) - missing,
        "missingDefinitionCount": missing,
        "rawFallbackRowCount": raw_rows,
        "referencedDefinitionCount": len(referenced),
        "distinctNameCount": len(
            {
                definitions[key]["name"]
                for key in referenced
                if definitions[key]["name"] is not None
            }
        ),
    }
    if include_details:
        result["rows"] = details
    return result, referenced


def _audit_availability_mechanisms(
    definitions: dict[tuple[int, Any], sqlite3.Row],
    profile_refs: set[tuple[int, Any]],
    option_refs: set[tuple[int, Any]],
    *,
    include_details: bool,
) -> dict[str, Any]:
    all_keys = set(definitions)
    attached = profile_refs | option_refs
    definition_only = all_keys - attached
    profile_only = profile_refs - option_refs
    option_only = option_refs - profile_refs
    both = profile_refs & option_refs

    attached_names = {
        definitions[key]["name"] for key in attached if definitions[key]["name"] is not None
    }
    definition_only_names = {
        definitions[key]["name"]
        for key in definition_only
        if definitions[key]["name"] is not None
    }
    mixed_names = attached_names & definition_only_names

    result: dict[str, Any] = {
        "attachedDefinitionCount": len(attached),
        "profileOnlyDefinitionCount": len(profile_only),
        "loadoutOnlyDefinitionCount": len(option_only),
        "profileAndLoadoutDefinitionCount": len(both),
        "definitionOnlyCount": len(definition_only),
        "attachedNameCount": len(attached_names),
        "definitionOnlyNameCount": len(definition_only_names),
        "namesWithAttachedAndDefinitionOnlyContexts": len(mixed_names),
        "definitionOnlyMeaning": (
            "The peripheral is declared in an Army's peripheral filter but has no "
            "normalized profile/loadout attachment in that Army. This is evidence for "
            "a distinct availability mechanism, not by itself proof of controller eligibility."
        ),
    }
    if include_details:
        result["definitionOnlyDefinitions"] = [
            {
                "armyId": definitions[key]["army_id"],
                "id": definitions[key]["id"],
                "name": definitions[key]["name"],
                "mercs": definitions[key]["mercs"],
            }
            for key in sorted(definition_only, key=lambda item: (item[0], str(item[1])))
        ]
        result["mixedNames"] = sorted(mixed_names, key=str)
    return result


def _semantic_signature(
    rows: Iterable[sqlite3.Row], definitions: dict[tuple[int, Any], sqlite3.Row]
) -> tuple[tuple[Any, Any], ...]:
    values: list[tuple[Any, Any]] = []
    for row in rows:
        definition = definitions.get((int(row["army_id"]), row["item_id"]))
        values.append((definition["name"] if definition is not None else None, row["quantity"]))
    return tuple(sorted(values, key=lambda value: (str(value[0]), str(value[1]))))


def _representation_signature(
    rows: Iterable[sqlite3.Row], definitions: dict[tuple[int, Any], sqlite3.Row]
) -> tuple[tuple[Any, ...], ...]:
    values: list[tuple[Any, ...]] = []
    for row in rows:
        definition = definitions.get((int(row["army_id"]), row["item_id"]))
        values.append(
            (
                definition["name"] if definition is not None else None,
                definition["mercs"] if definition is not None else None,
                row["quantity"],
                row["position"],
                row["display_order"],
            )
        )
    return tuple(sorted(values, key=lambda value: tuple(str(item) for item in value)))


def _audit_parent_stability(
    payload_occurrences: Iterable[sqlite3.Row],
    peripheral_rows: Iterable[sqlite3.Row],
    *,
    payload_id: str,
    parent_id: str,
    definitions: dict[tuple[int, Any], sqlite3.Row],
    include_details: bool,
) -> dict[str, Any]:
    peripherals_by_parent: dict[tuple[int, Any, Any, Any], list[sqlite3.Row]] = defaultdict(list)
    for row in peripheral_rows:
        peripherals_by_parent[_parent_key(row, parent_id)].append(row)

    signatures_by_payload: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in payload_occurrences:
        parent = (
            int(occurrence["army_id"]),
            occurrence["unit_id"],
            occurrence["group_id"],
            occurrence[parent_id],
        )
        rows = peripherals_by_parent.get(parent, [])
        signatures_by_payload[int(occurrence[payload_id])].append(
            {
                "parent": parent,
                "semantic": _semantic_signature(rows, definitions),
                "representation": _representation_signature(rows, definitions),
            }
        )

    repeated_payloads = {
        key: values for key, values in signatures_by_payload.items() if len(values) > 1
    }
    with_attachments = {
        key: values
        for key, values in signatures_by_payload.items()
        if any(value["semantic"] for value in values)
    }
    semantic_variants = {
        key: values
        for key, values in repeated_payloads.items()
        if len({value["semantic"] for value in values}) > 1
    }
    representation_variants = {
        key: values
        for key, values in repeated_payloads.items()
        if len({value["representation"] for value in values}) > 1
    }
    result: dict[str, Any] = {
        "canonicalPayloadCount": len(signatures_by_payload),
        "repeatedCanonicalPayloadCount": len(repeated_payloads),
        "payloadsWithAnyAttachment": len(with_attachments),
        "semanticVariantPayloadCount": len(semantic_variants),
        "representationVariantPayloadCount": len(representation_variants),
        "semanticSignatureFields": ["name", "quantity"],
        "representationSignatureFields": [
            "name",
            "mercs",
            "quantity",
            "position",
            "display_order",
        ],
    }
    if include_details:
        result["semanticVariants"] = [
            {
                "payloadId": key,
                "occurrences": [
                    {
                        "armyId": value["parent"][0],
                        "unitId": value["parent"][1],
                        "groupId": value["parent"][2],
                        "parentId": value["parent"][3],
                        "semanticSignature": [list(item) for item in value["semantic"]],
                        "representationSignature": [
                            list(item) for item in value["representation"]
                        ],
                    }
                    for value in values
                ],
            }
            for key, values in sorted(semantic_variants.items())
        ]
    return result


def _audit_normalization_gaps(metadata: dict[str, Any], *, include_details: bool) -> dict[str, Any]:
    warnings = metadata.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    global_option_warnings = [
        warning
        for warning in warnings
        if isinstance(warning, dict) and warning.get("code") == "global_option_peripheral"
    ]
    result: dict[str, Any] = {
        "globalUnitOptionPeripheralWarningCount": len(global_option_warnings),
        "meaning": (
            "Global unit options cannot resolve army-local peripheral IDs unambiguously. "
            "These warnings identify source relationships that require contextual handling "
            "before they can become canonical application relationships."
        ),
    }
    if include_details:
        result["globalUnitOptionPeripheralWarnings"] = global_option_warnings
    return result


def audit_database(path: Path, *, include_details: bool = False) -> dict[str, Any]:
    if not path.is_file():
        raise PeripheralSemanticsAuditError(f"Database does not exist: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        _validate_schema(connection)
        metadata = _metadata_rows(connection)
        definitions, definition_by_key = _audit_definitions(
            list(connection.execute("SELECT * FROM peripherals")),
            include_details=include_details,
        )
        profile_rows = list(connection.execute("SELECT * FROM profile_peripherals"))
        option_rows = list(connection.execute("SELECT * FROM option_peripherals"))
        profiles, profile_ref_map = _audit_occurrences(
            profile_rows,
            definitions=definition_by_key,
            parent_id="profile_id",
            include_details=include_details,
        )
        loadouts, option_ref_map = _audit_occurrences(
            option_rows,
            definitions=definition_by_key,
            parent_id="option_id",
            include_details=include_details,
        )
        raw_meta = metadata.get("_meta")
        meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "path": str(path),
                "sha256": _sha256(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": meta.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": meta.get("snapshotDownloadedOn"),
            },
            "definitions": definitions,
            "explicitAttachments": {"profile": profiles, "loadout": loadouts},
            "availabilityMechanisms": _audit_availability_mechanisms(
                definition_by_key,
                set(profile_ref_map),
                set(option_ref_map),
                include_details=include_details,
            ),
            "canonicalParentStability": {
                "profile": _audit_parent_stability(
                    connection.execute("SELECT * FROM profile_payload_occurrences"),
                    profile_rows,
                    payload_id="profile_payload_id",
                    parent_id="profile_id",
                    definitions=definition_by_key,
                    include_details=include_details,
                ),
                "loadout": _audit_parent_stability(
                    connection.execute("SELECT * FROM loadout_payload_occurrences"),
                    option_rows,
                    payload_id="loadout_payload_id",
                    parent_id="option_id",
                    definitions=definition_by_key,
                    include_details=include_details,
                ),
            },
            "normalizationGaps": _audit_normalization_gaps(
                metadata, include_details=include_details
            ),
            "controllerEligibility": {
                "status": "not_inferred_from_army_source",
                "reason": (
                    "The normalized Army schema contains peripheral definitions and explicit "
                    "profile/loadout attachments, but no direct peripheral-to-controller-rule "
                    "relationship. Rules-derived eligibility must enter through reviewed curated "
                    "data rather than source normalization or audit heuristics."
                ),
                "curatedDataRequired": True,
            },
        }
    except sqlite3.Error as exc:
        raise PeripheralSemanticsAuditError(f"Could not audit {path}: {exc}") from exc
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit peripheral identity, availability, and attachment semantics."
    )
    parser.add_argument("database", type=Path, help="Path to infinity.db")
    parser.add_argument("--details", action="store_true", help="Include row-level evidence")
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database, include_details=args.details)
    except PeripheralSemanticsAuditError as exc:
        raise SystemExit(str(exc)) from exc
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Peripheral semantics audit written: {args.output}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
