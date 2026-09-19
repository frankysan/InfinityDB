#!/usr/bin/env python3
"""Audit loadout-field semantics and army-context variation in InfinityDB."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REPORT_FORMAT = "InfinityDB loadout semantics audit"
REPORT_FORMAT_VERSION = 1

LOADOUT_KEY = ("army_id", "unit_id", "group_id", "option_id")
SOURCE_LOADOUT_KEY = ("unit_id", "group_id", "option_id")

LOADOUT_FIELDS = (
    "army_id",
    "unit_id",
    "group_id",
    "option_id",
    "position",
    "name",
    "points",
    "swc",
    "minis",
    "disabled",
)
ITEM_FIELDS = ("item_id", "display_order", "quantity", "raw")
CHARACTERISTIC_FIELDS = ("characteristic_id",)
ORDER_FIELDS = ("order_type", "list_count", "total_count", "raw")
INCLUDE_FIELDS = ("target_group_id", "target_option_id", "quantity", "raw")
EXTRA_FIELDS = ("extra_id",)
PERIPHERAL_FIELDS = ("army_id", "id", "position", "name", "mercs")
WEAPON_TEMPLATE_FIELDS = ("id", "item_id", "display_order", "quantity", "raw")

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "loadout_options": LOADOUT_FIELDS,
    "option_characteristics": (*LOADOUT_KEY, "position", *CHARACTERISTIC_FIELDS),
    "option_orders": (*LOADOUT_KEY, "position", *ORDER_FIELDS),
    "option_skills": ("occurrence_id", *LOADOUT_KEY, "position", *ITEM_FIELDS),
    "option_skill_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "option_equipment": ("occurrence_id", *LOADOUT_KEY, "position", *ITEM_FIELDS),
    "option_equipment_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "option_weapons": ("occurrence_id", *LOADOUT_KEY, "position", "template_id"),
    "option_weapon_templates": WEAPON_TEMPLATE_FIELDS,
    "option_weapon_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "option_includes": (*LOADOUT_KEY, "position", *INCLUDE_FIELDS),
    "option_peripherals": ("occurrence_id", *LOADOUT_KEY, "position", *ITEM_FIELDS),
    "peripherals": PERIPHERAL_FIELDS,
    "__infinity_metadata": ("key", "value"),
}

LOADOUT_CLASSIFICATION: dict[str, dict[str, str]] = {
    "army_id": {
        "classification": "source_provenance",
        "reason": "Owning Army occurrence.",
    },
    "unit_id": {
        "classification": "source_provenance",
        "reason": "Source-defined unit identity.",
    },
    "group_id": {
        "classification": "source_provenance",
        "reason": "Source-local profile-group identity.",
    },
    "option_id": {
        "classification": "source_provenance",
        "reason": "Source-local loadout option identity.",
    },
    "position": {
        "classification": "normalization_only",
        "reason": "Generated from source option-array order; literal ordinal is not identity.",
    },
    "name": {
        "classification": "canonical_fact",
        "reason": (
            "Loadout display label; invariant for repeated source-loadout keys in the "
            "audited snapshot."
        ),
    },
    "points": {
        "classification": "contextual_delta",
        "reason": (
            "Player-facing loadout cost with observed army-specific variation for the "
            "same source-loadout key."
        ),
    },
    "swc": {
        "classification": "contextual_delta",
        "reason": (
            "Player-facing SWC cost with observed army-specific variation for the same "
            "source-loadout key."
        ),
    },
    "minis": {
        "classification": "canonical_fact",
        "reason": (
            "Loadout miniature count; invariant for repeated source-loadout keys in the "
            "audited snapshot."
        ),
    },
    "disabled": {
        "classification": "canonical_fact",
        "reason": (
            "Loadout source state; invariant for repeated source-loadout keys in the "
            "audited snapshot."
        ),
    },
}

RELATIONSHIP_CLASSIFICATION: dict[str, dict[str, Any]] = {
    "characteristics": {
        "table": "option_characteristics",
        "classification": "relationship",
        "reason": "Loadout-to-characteristic relationships; absent in the audited snapshot.",
    },
    "orders": {
        "table": "option_orders",
        "classification": "relationship",
        "reason": (
            "Loadout order-generation relationship; one same-source key has meaningful "
            "army-context variation."
        ),
    },
    "skills": {
        "table": "option_skills",
        "extrasTable": "option_skill_extras",
        "classification": "relationship",
        "reason": (
            "Loadout-to-skill relationships and extras; observed same-source differences "
            "remain after representation normalization."
        ),
    },
    "equipment": {
        "table": "option_equipment",
        "extrasTable": "option_equipment_extras",
        "classification": "relationship",
        "reason": (
            "Loadout-to-equipment relationships; the only same-source variation in this "
            "snapshot is representation-only."
        ),
    },
    "weapons": {
        "table": "option_weapons",
        "extrasTable": "option_weapon_extras",
        "classification": "relationship",
        "reason": (
            "Loadout-to-weapon relationships; both presentation differences and unresolved "
            "source-shape differences occur."
        ),
    },
    "includes": {
        "table": "option_includes",
        "classification": "relationship",
        "reason": "Relationship from a loadout to another source-local loadout option.",
    },
    "peripherals": {
        "table": "option_peripherals",
        "classification": "relationship",
        "reason": (
            "Relationship to an army-local peripheral identity. Raw IDs are provenance, "
            "not cross-army semantic identity."
        ),
    },
}

NESTED_FIELD_CLASSIFICATION: dict[str, dict[str, str]] = {
    "parent_source_keys": {
        "classification": "source_provenance",
        "reason": "army_id/unit_id/group_id/option_id locate the source occurrence.",
    },
    "occurrence_id": {
        "classification": "normalization_only",
        "reason": "Generated surrogate for one normalized occurrence.",
    },
    "template_id": {
        "classification": "normalization_only",
        "reason": "Internal reusable option-weapon template identity.",
    },
    "position": {
        "classification": "normalization_only",
        "reason": "Preserves source array order; literal ordinal is not semantic identity.",
    },
    "item_id": {
        "classification": "relationship",
        "reason": (
            "Catalog target identity. Peripheral item_id is army-local and cannot be "
            "compared directly across armies."
        ),
    },
    "display_order": {
        "classification": "presentation_context",
        "reason": "Source presentation ordering; absolute values are not entity identity.",
    },
    "quantity": {
        "classification": "relationship_attribute",
        "reason": "Quantity attached to the referenced item relationship.",
    },
    "raw": {
        "classification": "source_provenance",
        "reason": (
            "Fallback preserving malformed or unmodeled source content; non-null data blocks "
            "destructive canonicalization until understood."
        ),
    },
    "extra_id": {
        "classification": "relationship",
        "reason": "Extra/modifier relationship attached to an item occurrence.",
    },
    "characteristic_id": {
        "classification": "relationship",
        "reason": "Characteristic catalog relationship.",
    },
    "order_fields": {
        "classification": "relationship_attribute",
        "reason": "order_type/list_count/total_count define order-generation meaning.",
    },
    "include_target": {
        "classification": "relationship",
        "reason": "target_group_id/target_option_id identify a source-local included option.",
    },
    "peripheral_definition": {
        "classification": "contextual_relationship_target",
        "reason": (
            "Peripheral IDs are army-local; name and mercs describe the target definition "
            "available in that Army context."
        ),
    },
}


class LoadoutSemanticsAuditError(ValueError):
    """Raised when a database cannot be classified safely."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_raw(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")'))


def _validate_schema(connection: sqlite3.Connection) -> None:
    for table, expected in EXPECTED_COLUMNS.items():
        actual = _columns(connection, table)
        if not actual:
            raise LoadoutSemanticsAuditError(f"Required table is missing: {table}")
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        if missing or unexpected:
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if unexpected:
                details.append(f"unclassified {', '.join(unexpected)}")
            raise LoadoutSemanticsAuditError(
                f"Loadout semantic classification for {table} is stale "
                f"({'; '.join(details)})"
            )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', ("_meta",)
    ).fetchone()
    if row is None:
        return {}
    try:
        value = json.loads(row["value"])
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _row_key(row: Mapping[str, Any], fields: Iterable[str]) -> tuple[Any, ...]:
    return tuple(row[field] for field in fields)


def _value_key(value: Any) -> str:
    return _canonical_json(_decode_raw(value))


def _field_evidence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_row_key(row, SOURCE_LOADOUT_KEY)].append(row)

    result: dict[str, Any] = {}
    for field in LOADOUT_FIELDS:
        values = [row[field] for row in rows]
        variant_groups = 0
        affected_occurrences = 0
        examples: list[dict[str, Any]] = []
        if field not in SOURCE_LOADOUT_KEY:
            for key, group in sorted(groups.items()):
                signatures = {_value_key(row[field]) for row in group}
                if len(signatures) <= 1:
                    continue
                variant_groups += 1
                affected_occurrences += len(group)
                if len(examples) < 5:
                    examples.append(
                        {
                            "sourceKey": list(key),
                            "occurrences": [
                                {"armyId": row["army_id"], "value": _decode_raw(row[field])}
                                for row in group
                            ],
                        }
                    )
        result[field] = {
            **LOADOUT_CLASSIFICATION[field],
            "nonNullCount": sum(value is not None for value in values),
            "distinctNonNullValueCount": len(
                {_value_key(value) for value in values if value is not None}
            ),
            "sameSourceVariantIdentityCount": variant_groups,
            "affectedOccurrenceCount": affected_occurrences,
        }
        if examples:
            result[field]["variantExamples"] = examples
    return result


def _extras_by_occurrence(
    connection: sqlite3.Connection, table: str
) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        f'SELECT * FROM "{table}" ORDER BY occurrence_id, position'
    ):
        item = dict(row)
        result[item["occurrence_id"]].append(item)
    return result


def _relationship_rows(
    connection: sqlite3.Connection, name: str, table: str
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    result: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    if name == "weapons":
        query = """
            SELECT o.occurrence_id, o.army_id, o.unit_id, o.group_id, o.option_id,
                   o.position, o.template_id, t.item_id, t.display_order, t.quantity, t.raw
            FROM option_weapons AS o
            JOIN option_weapon_templates AS t ON t.id = o.template_id
            ORDER BY o.army_id, o.unit_id, o.group_id, o.option_id, o.position
        """
        source = connection.execute(query)
    else:
        source = connection.execute(
            f'SELECT * FROM "{table}" '
            "ORDER BY army_id, unit_id, group_id, option_id, position"
        )
    for row in source:
        item = dict(row)
        result[_row_key(item, LOADOUT_KEY)].append(item)
    return result


def _peripheral_definitions(
    connection: sqlite3.Connection,
) -> dict[tuple[Any, Any], dict[str, Any]]:
    return {
        (row["army_id"], row["id"]): {"name": row["name"], "mercs": row["mercs"]}
        for row in connection.execute(
            "SELECT army_id, id, name, mercs FROM peripherals ORDER BY army_id, id"
        )
    }


def _relationship_payload(
    name: str,
    rows: list[dict[str, Any]],
    *,
    extras: Mapping[Any, list[dict[str, Any]]] | None,
    normalize_representation: bool,
    resolve_peripheral_identity: bool,
    peripheral_definitions: Mapping[tuple[Any, Any], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        if name == "characteristics":
            item = {"characteristic_id": row["characteristic_id"]}
        elif name == "orders":
            item = {
                "order_type": row["order_type"],
                "list_count": row["list_count"],
                "total_count": row["total_count"],
                "raw": _decode_raw(row["raw"]),
            }
        elif name == "includes":
            quantity = row["quantity"]
            if normalize_representation and quantity in (None, 1):
                quantity = 1
            item = {
                "target_group_id": row["target_group_id"],
                "target_option_id": row["target_option_id"],
                "quantity": quantity,
                "raw": _decode_raw(row["raw"]),
            }
        else:
            quantity = row["quantity"]
            if normalize_representation and quantity in (None, 1):
                quantity = 1
            target: Any = row["item_id"]
            if name == "peripherals" and resolve_peripheral_identity:
                definition = peripheral_definitions.get((row["army_id"], row["item_id"]))
                if definition is None:
                    target = {"sourceId": row["item_id"], "unresolved": True}
                else:
                    target = {"name": definition["name"], "mercs": definition["mercs"]}
            item = {
                "item_id": target,
                "quantity": quantity,
                "raw": _decode_raw(row["raw"]),
            }
            if not normalize_representation:
                item["display_order"] = row["display_order"]
            if extras is not None:
                item["extras"] = [
                    extra["extra_id"] for extra in extras.get(row["occurrence_id"], ())
                ]
        payload.append(item)
    return payload


def _relationship_evidence(
    connection: sqlite3.Connection,
    loadouts: list[dict[str, Any]],
) -> tuple[
    dict[str, Any],
    dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]],
    dict[str, Mapping[Any, list[dict[str, Any]]]],
    dict[tuple[Any, Any], dict[str, Any]],
]:
    loadouts_by_source: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in loadouts:
        loadouts_by_source[_row_key(row, SOURCE_LOADOUT_KEY)].append(row)

    peripheral_definitions = _peripheral_definitions(connection)
    all_rows: dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]] = {}
    extras_by_name: dict[str, Mapping[Any, list[dict[str, Any]]]] = {}
    result: dict[str, Any] = {}

    for name, definition in RELATIONSHIP_CLASSIFICATION.items():
        table = definition["table"]
        rows_by_parent = _relationship_rows(connection, name, table)
        all_rows[name] = rows_by_parent
        extras_table = definition.get("extrasTable")
        extras = _extras_by_occurrence(connection, extras_table) if extras_table else None
        extras_by_name[name] = extras or {}
        raw_variant = 0
        normalized_variant = 0
        peripheral_resolved_variant = 0
        peripheral_resolved_normalized_variant = 0
        affected_raw = 0
        affected_normalized = 0
        examples: list[dict[str, Any]] = []

        for source_key, source_loadouts in sorted(loadouts_by_source.items()):
            if len(source_loadouts) < 2:
                continue
            raw_payloads: list[str] = []
            normalized_payloads: list[str] = []
            resolved_payloads: list[str] = []
            resolved_normalized_payloads: list[str] = []
            occurrence_view: list[dict[str, Any]] = []
            for loadout in source_loadouts:
                parent = _row_key(loadout, LOADOUT_KEY)
                source_rows = rows_by_parent.get(parent, [])
                raw_payload = _relationship_payload(
                    name,
                    source_rows,
                    extras=extras,
                    normalize_representation=False,
                    resolve_peripheral_identity=False,
                    peripheral_definitions=peripheral_definitions,
                )
                normalized_payload = _relationship_payload(
                    name,
                    source_rows,
                    extras=extras,
                    normalize_representation=True,
                    resolve_peripheral_identity=False,
                    peripheral_definitions=peripheral_definitions,
                )
                resolved_payload = _relationship_payload(
                    name,
                    source_rows,
                    extras=extras,
                    normalize_representation=False,
                    resolve_peripheral_identity=name == "peripherals",
                    peripheral_definitions=peripheral_definitions,
                )
                resolved_normalized_payload = _relationship_payload(
                    name,
                    source_rows,
                    extras=extras,
                    normalize_representation=True,
                    resolve_peripheral_identity=name == "peripherals",
                    peripheral_definitions=peripheral_definitions,
                )
                raw_payloads.append(_canonical_json(raw_payload))
                normalized_payloads.append(_canonical_json(normalized_payload))
                resolved_payloads.append(_canonical_json(resolved_payload))
                resolved_normalized_payloads.append(
                    _canonical_json(resolved_normalized_payload)
                )
                occurrence_view.append(
                    {"armyId": loadout["army_id"], "payload": raw_payload}
                )

            raw_differs = len(set(raw_payloads)) > 1
            normalized_differs = len(set(normalized_payloads)) > 1
            resolved_differs = len(set(resolved_payloads)) > 1
            resolved_normalized_differs = len(set(resolved_normalized_payloads)) > 1
            if raw_differs:
                raw_variant += 1
                affected_raw += len(source_loadouts)
            if normalized_differs:
                normalized_variant += 1
                affected_normalized += len(source_loadouts)
            if resolved_differs:
                peripheral_resolved_variant += 1
            if resolved_normalized_differs:
                peripheral_resolved_normalized_variant += 1
            if raw_differs and len(examples) < 5:
                examples.append(
                    {
                        "sourceKey": list(source_key),
                        "representationOnly": not normalized_differs,
                        "occurrences": occurrence_view,
                    }
                )

        row_count = sum(len(value) for value in rows_by_parent.values())
        raw_non_null = sum(
            row.get("raw") is not None
            for parent_rows in rows_by_parent.values()
            for row in parent_rows
        )
        relationship_result: dict[str, Any] = {
            "table": table,
            "classification": definition["classification"],
            "reason": definition["reason"],
            "rowCount": row_count,
            "populatedLoadoutOccurrenceCount": len(rows_by_parent),
            "sameSourceRawVariantIdentityCount": raw_variant,
            "sameSourceNormalizedVariantIdentityCount": normalized_variant,
            "representationOnlyVariantIdentityCount": raw_variant - normalized_variant,
            "affectedRawOccurrenceCount": affected_raw,
            "affectedNormalizedOccurrenceCount": affected_normalized,
            "rawFallbackNonNullCount": raw_non_null,
        }
        if extras_table:
            relationship_result["extrasTable"] = extras_table
            relationship_result["extraRowCount"] = sum(
                1 for _ in connection.execute(f'SELECT 1 FROM "{extras_table}"')
            )
        if name == "peripherals":
            relationship_result["sameSourceResolvedIdentityVariantIdentityCount"] = (
                peripheral_resolved_variant
            )
            relationship_result[
                "sameSourceResolvedIdentityAndNormalizedRepresentationVariantIdentityCount"
            ] = peripheral_resolved_normalized_variant
            relationship_result["armyLocalIdOnlyVariantIdentityCount"] = (
                raw_variant - peripheral_resolved_variant
            )
            relationship_result["identityResolution"] = (
                "Diagnostic only: compare army-local peripheral IDs by the referenced "
                "peripheral definition's name and mercs values."
            )
        if examples:
            relationship_result["variantExamples"] = examples
        result[name] = relationship_result
    return result, all_rows, extras_by_name, peripheral_definitions


def _loadout_payload(
    loadout: Mapping[str, Any],
    relationship_rows: Mapping[str, Mapping[tuple[Any, ...], list[dict[str, Any]]]],
    extras: Mapping[str, Mapping[Any, list[dict[str, Any]]]],
    peripheral_definitions: Mapping[tuple[Any, Any], Mapping[str, Any]],
    *,
    normalize_representation: bool,
    resolve_peripheral_identity: bool,
) -> dict[str, Any]:
    parent = _row_key(loadout, LOADOUT_KEY)
    payload = {
        field: loadout[field]
        for field in LOADOUT_FIELDS
        if field not in LOADOUT_KEY and field != "position"
    }
    for name in RELATIONSHIP_CLASSIFICATION:
        payload[name] = _relationship_payload(
            name,
            relationship_rows[name].get(parent, []),
            extras=extras.get(name),
            normalize_representation=normalize_representation,
            resolve_peripheral_identity=resolve_peripheral_identity and name == "peripherals",
            peripheral_definitions=peripheral_definitions,
        )
    return payload


def _variant_identity_count(
    loadouts: list[dict[str, Any]],
    relationship_rows: Mapping[str, Mapping[tuple[Any, ...], list[dict[str, Any]]]],
    extras: Mapping[str, Mapping[Any, list[dict[str, Any]]]],
    peripheral_definitions: Mapping[tuple[Any, Any], Mapping[str, Any]],
    *,
    normalize_representation: bool = False,
    resolve_peripheral_identity: bool = False,
) -> int:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for loadout in loadouts:
        groups[_row_key(loadout, SOURCE_LOADOUT_KEY)].append(loadout)
    count = 0
    for source_loadouts in groups.values():
        if len(source_loadouts) < 2:
            continue
        signatures = {
            _canonical_json(
                _loadout_payload(
                    loadout,
                    relationship_rows,
                    extras,
                    peripheral_definitions,
                    normalize_representation=normalize_representation,
                    resolve_peripheral_identity=resolve_peripheral_identity,
                )
            )
            for loadout in source_loadouts
        }
        if len(signatures) > 1:
            count += 1
    return count


def audit_database(path: Path) -> dict[str, Any]:
    """Return deterministic evidence for classifying loadout canonicalization fields."""
    path = path.resolve()
    if not path.is_file():
        raise LoadoutSemanticsAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_schema(connection)
        loadouts = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM loadout_options "
                "ORDER BY unit_id, group_id, option_id, army_id"
            )
        ]
        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in loadouts:
            groups[_row_key(row, SOURCE_LOADOUT_KEY)].append(row)
        repeated = {key: rows for key, rows in groups.items() if len(rows) > 1}

        relationships, relationship_rows, extras, peripheral_definitions = (
            _relationship_evidence(connection, loadouts)
        )
        baseline = _variant_identity_count(
            loadouts,
            relationship_rows,
            extras,
            peripheral_definitions,
        )
        normalized = _variant_identity_count(
            loadouts,
            relationship_rows,
            extras,
            peripheral_definitions,
            normalize_representation=True,
        )
        resolved = _variant_identity_count(
            loadouts,
            relationship_rows,
            extras,
            peripheral_definitions,
            resolve_peripheral_identity=True,
        )
        resolved_normalized = _variant_identity_count(
            loadouts,
            relationship_rows,
            extras,
            peripheral_definitions,
            normalize_representation=True,
            resolve_peripheral_identity=True,
        )
        metadata = _metadata(connection)
        report = {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "sha256": _sha256_file(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "sourceLoadoutKey": list(SOURCE_LOADOUT_KEY),
            "sourceLoadoutKeyCaveat": (
                "This is an observational comparison key repeated across Army source lists, "
                "not a proposed canonical application identity."
            ),
            "summary": {
                "loadoutOccurrenceCount": len(loadouts),
                "sourceLoadoutIdentityCount": len(groups),
                "repeatedSourceLoadoutIdentityCount": len(repeated),
                "repeatedSourceLoadoutOccurrenceCount": sum(
                    len(rows) for rows in repeated.values()
                ),
                "baselineVariantIdentityCount": baseline,
                "normalizedRepresentationVariantIdentityCount": normalized,
                "resolvedPeripheralIdentityVariantIdentityCount": resolved,
                "resolvedPeripheralIdentityAndNormalizedRepresentationVariantIdentityCount": (
                    resolved_normalized
                ),
            },
            "fields": _field_evidence(loadouts),
            "nestedFieldClassification": NESTED_FIELD_CLASSIFICATION,
            "relationships": relationships,
            "diagnosticNormalization": {
                "representation": (
                    "Treat omitted quantity and explicit quantity 1 as equivalent and ignore "
                    "absolute display_order while preserving source row/extras ordering. This "
                    "is evidence gathering, not yet an application canonicalization rule."
                ),
                "peripheralIdentity": (
                    "Resolve army-local peripheral item_id to the referenced peripheral "
                    "definition's name and mercs values for cross-army comparison. This is "
                    "diagnostic only and does not establish canonical peripheral identity."
                ),
            },
        }
    finally:
        connection.close()
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Frontend infinity.db to audit")
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database)
    except (OSError, sqlite3.Error, LoadoutSemanticsAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    summary = report["summary"]
    print("InfinityDB loadout semantics audit")
    print(
        f"Loadouts: {summary['loadoutOccurrenceCount']} occurrences | "
        f"{summary['sourceLoadoutIdentityCount']} source-loadout keys | "
        f"{summary['repeatedSourceLoadoutIdentityCount']} repeated keys"
    )
    print(
        "Variant repeated keys: "
        f"{summary['baselineVariantIdentityCount']} baseline -> "
        f"{summary['normalizedRepresentationVariantIdentityCount']} representation-normalized "
        "-> "
        f"{summary['resolvedPeripheralIdentityVariantIdentityCount']} peripheral-resolved -> "
        f"{summary['resolvedPeripheralIdentityAndNormalizedRepresentationVariantIdentityCount']} "
        "both"
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
