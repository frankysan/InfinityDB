#!/usr/bin/env python3
"""Audit logical-unit field semantics and source-variant evidence in InfinityDB."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from infinity_db.identities import (
    IdentityConfig,
    normalized_unit_identity,
    parse_identity_config,
    strip_reinforcement_prefix,
)

REPORT_FORMAT = "InfinityDB logical-unit semantics audit"
REPORT_FORMAT_VERSION = 3

UNIT_FIELDS = (
    "id",
    "id_army",
    "canonical_faction_id",
    "main_army_id",
    "display_army_id",
    "isc",
    "isc_abbr",
    "name",
    "slug",
    "notes",
    "spectables",
    "source_defined",
    "source_role",
    "relation_reference_count",
)

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "units": UNIT_FIELDS,
    "logical_units": (
        "id",
        "representative_unit_id",
        "name",
        "isc",
        "isc_abbr",
        "slug",
        "canonical_faction_id",
        "main_army_id",
        "display_army_id",
    ),
    "logical_unit_sources": ("source_unit_id", "logical_unit_id"),
    "logical_unit_aliases": ("logical_unit_id", "source_unit_id", "field", "value"),
    "logical_unit_notes": ("logical_unit_id", "source_unit_id", "note"),
    "logical_unit_spectables": ("logical_unit_id", "source_unit_id", "spectables"),
    "unit_factions": ("unit_id", "faction_id", "position"),
    "army_lists": (
        "id",
        "name",
        "slug",
        "kind",
        "version",
        "reinforcement_id",
        "source_file",
        "source_sha256",
        "resume",
        "teamops",
        "legacy_fireteams",
        "filter_attrs",
        "filter_points",
        "filter_swc",
        "fireteam_description",
        "fireteam_spec",
    ),
    "army_units": ("army_id", "unit_id", "position", "filters", "availability_kind"),
    "unit_options": (
        "unit_id",
        "option_id",
        "position",
        "name",
        "points",
        "swc",
        "minis",
        "disabled",
        "compatible",
        "habilities",
        "raw",
    ),
    "unit_option_characteristics": (
        "unit_id",
        "option_id",
        "position",
        "characteristic_id",
    ),
    "unit_option_orders": (
        "unit_id",
        "option_id",
        "position",
        "order_type",
        "list_count",
        "total_count",
        "raw",
    ),
    "unit_option_skills": (
        "occurrence_id",
        "unit_id",
        "option_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "unit_option_skill_extras": ("occurrence_id", "position", "extra_id"),
    "unit_option_equipment": (
        "occurrence_id",
        "unit_id",
        "option_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "unit_option_equipment_extras": ("occurrence_id", "position", "extra_id"),
    "unit_option_weapons": (
        "occurrence_id",
        "unit_id",
        "option_id",
        "position",
        "item_id",
        "display_order",
        "quantity",
        "raw",
    ),
    "unit_option_weapon_extras": ("occurrence_id", "position", "extra_id"),
    "unit_option_includes": (
        "unit_id",
        "option_id",
        "position",
        "target_group_id",
        "target_option_id",
        "quantity",
        "raw",
    ),
    "__infinity_metadata": ("key", "value"),
}

UNIT_FIELD_CLASSIFICATION: dict[str, dict[str, str]] = {
    "id": {
        "classification": "source_provenance",
        "reason": (
            "Original source-unit identity. logical_units.id is a separate application "
            "identity even while it currently equals the representative source ID."
        ),
    },
    "id_army": {
        "classification": "source_provenance",
        "reason": "Source idArmy value; it varies across matched source-unit representations.",
    },
    "canonical_faction_id": {
        "classification": "relationship",
        "reason": (
            "Source-unit relationship to canonical faction identity. Reinforcement and "
            "mercenary representations can legitimately differ inside one logical unit."
        ),
    },
    "main_army_id": {
        "classification": "relationship",
        "reason": (
            "Derived source-unit ownership relationship. A logical-unit display value may "
            "follow the representative rule, but source-specific derivations remain context."
        ),
    },
    "display_army_id": {
        "classification": "presentation_context",
        "reason": (
            "Derived display relationship. Current logical presentation follows the "
            "representative source while source-specific values remain traceable."
        ),
    },
    "isc": {
        "classification": "canonical_fact",
        "reason": (
            "Canonical display value governed by the existing representative-source "
            "rule; alternate source labels remain search/provenance context."
        ),
    },
    "isc_abbr": {
        "classification": "canonical_fact",
        "reason": (
            "Canonical abbreviated display value governed by the representative-source "
            "rule; source-specific abbreviations remain context."
        ),
    },
    "name": {
        "classification": "canonical_fact",
        "reason": (
            "Canonical display name governed by the existing representative-source "
            "rule; alternate source names remain search/provenance context."
        ),
    },
    "slug": {
        "classification": "canonical_fact",
        "reason": (
            "Canonical representative slug. Every repeated logical unit has raw "
            "slug variation, so source slugs must remain searchable/traceable context."
        ),
    },
    "notes": {
        "classification": "contextual_delta",
        "reason": (
            "Player-facing notes have genuine source-specific variation inside logical units; "
            "a representative note cannot replace those deltas losslessly."
        ),
    },
    "spectables": {
        "classification": "canonical_candidate",
        "reason": (
            "Player-facing unit data and a logical payload candidate, but the audited snapshot "
            "contains it only on singleton logical units, so cross-source invariance is not "
            "yet demonstrated."
        ),
    },
    "source_defined": {
        "classification": "source_provenance",
        "reason": "Distinguishes imported source units from normalization placeholders.",
    },
    "source_role": {
        "classification": "source_provenance",
        "reason": (
            "Records standard versus mercenary-variant source representation; this is "
            "occurrence provenance, not logical-unit identity."
        ),
    },
    "relation_reference_count": {
        "classification": "relationship_summary",
        "reason": (
            "Derived count of source relationship references. Underlying relationships are "
            "audited separately and the count is not a canonical unit fact."
        ),
    },
}

RELATIONSHIP_CLASSIFICATION: dict[str, dict[str, str]] = {
    "unit_factions": {
        "classification": "relationship",
        "reason": (
            "Source-declared faction memberships vary for every repeated logical unit and "
            "must remain attached to source identity/context."
        ),
    },
    "army_units": {
        "classification": "contextual_relationship",
        "reason": (
            "Army membership, filters, position, and availability kind describe source/Army "
            "occurrences and remain contextual after logical identity resolution."
        ),
    },
    "unit_options": {
        "classification": "contextual_payload",
        "reason": (
            "Top-level unit options are source-unit payloads. The audited snapshot contains "
            "both exact repeats and a genuine points difference inside logical units."
        ),
    },
}

UNIT_OPTION_FIELDS = (
    "position",
    "name",
    "points",
    "swc",
    "minis",
    "disabled",
    "compatible",
    "habilities",
    "raw",
)

UNIT_OPTION_FIELD_CLASSIFICATION: dict[str, dict[str, str]] = {
    "position": {
        "classification": "normalization_only",
        "reason": "Preserves source option-array order; the literal ordinal is not identity.",
    },
    "name": {
        "classification": "contextual_payload_fact",
        "reason": "Display label belonging to the source-unit option payload.",
    },
    "points": {
        "classification": "contextual_delta",
        "reason": "Player-facing cost with an observed logical-unit source variation.",
    },
    "swc": {
        "classification": "contextual_delta",
        "reason": "Player-facing SWC cost; keep source context even when currently equal.",
    },
    "minis": {
        "classification": "contextual_payload_fact",
        "reason": "Miniature count attached to the source-unit option payload.",
    },
    "disabled": {
        "classification": "contextual_payload_fact",
        "reason": "Source option state attached to the source-unit option payload.",
    },
    "compatible": {
        "classification": "contextual_payload_fact",
        "reason": "Source compatibility payload retained exactly until its semantics are modeled.",
    },
    "habilities": {
        "classification": "contextual_payload_fact",
        "reason": "Source abilities payload retained exactly until its semantics are modeled.",
    },
    "raw": {
        "classification": "source_provenance",
        "reason": (
            "Fallback preserving unmodeled source fields; non-null data blocks "
            "lossful merging."
        ),
    },
}

UNIT_OPTION_RELATION_TABLES = (
    "unit_option_characteristics",
    "unit_option_orders",
    "unit_option_skills",
    "unit_option_equipment",
    "unit_option_weapons",
    "unit_option_includes",
)

UNIT_OPTION_EXTRA_TABLES = {
    "unit_option_skills": "unit_option_skill_extras",
    "unit_option_equipment": "unit_option_equipment_extras",
    "unit_option_weapons": "unit_option_weapon_extras",
}

JSON_VALUE_FIELDS = {"spectables", "compatible", "habilities", "raw", "filters"}


class UnitSemanticsAuditError(ValueError):
    """Raised when a database cannot be classified safely."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_json_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _display_value(field: str, value: Any) -> Any:
    return _decode_json_text(value) if field in JSON_VALUE_FIELDS else value


def _value_key(field: str, value: Any) -> str:
    return _canonical_json(_display_value(field, value))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_value(connection: sqlite3.Connection, key: str) -> Any:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', (key,)
    ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row["value"])
    except (TypeError, json.JSONDecodeError):
        return None


def _snapshot_metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    value = _metadata_value(connection, "_meta")
    return value if isinstance(value, dict) else {}


def _identity_config(connection: sqlite3.Connection) -> IdentityConfig:
    value = _metadata_value(connection, "identityConfig")
    if value is None:
        raise UnitSemanticsAuditError("Database does not contain pinned identityConfig metadata")
    try:
        return parse_identity_config(value)
    except ValueError as exc:
        raise UnitSemanticsAuditError(
            f"Database identityConfig metadata is invalid: {exc}"
        ) from exc


def _validate_schema(connection: sqlite3.Connection) -> None:
    for table, expected in EXPECTED_COLUMNS.items():
        actual = tuple(
            row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')
        )
        if actual != expected:
            details: list[str] = []
            missing = [column for column in expected if column not in actual]
            extra = [column for column in actual if column not in expected]
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            if not missing and not extra:
                details.append("column order changed")
            raise UnitSemanticsAuditError(
                f"Logical-unit semantic classification for {table} is stale "
                f"({'; '.join(details)})"
            )


def _logical_groups(
    connection: sqlite3.Connection,
    units: Mapping[int, Mapping[str, Any]],
) -> tuple[dict[int, int], dict[int, list[int]]]:
    representatives = {
        row["id"]: row["representative_unit_id"]
        for row in connection.execute(
            "SELECT id, representative_unit_id FROM logical_units ORDER BY id"
        )
    }
    groups: dict[int, list[int]] = defaultdict(list)
    seen_sources: set[int] = set()
    for row in connection.execute(
        "SELECT source_unit_id, logical_unit_id FROM logical_unit_sources "
        "ORDER BY logical_unit_id, source_unit_id"
    ):
        source_id = row["source_unit_id"]
        logical_id = row["logical_unit_id"]
        if source_id not in units:
            raise UnitSemanticsAuditError(
                f"logical_unit_sources references non-source unit {source_id}"
            )
        if source_id in seen_sources:
            raise UnitSemanticsAuditError(f"Source unit {source_id} maps more than once")
        seen_sources.add(source_id)
        groups[logical_id].append(source_id)

    if seen_sources != set(units):
        missing = sorted(set(units) - seen_sources)
        raise UnitSemanticsAuditError(
            "Source-defined units missing logical mappings: " + ", ".join(map(str, missing))
        )
    if set(groups) != set(representatives):
        raise UnitSemanticsAuditError("logical_units and logical_unit_sources disagree")
    for logical_id, source_ids in groups.items():
        representative = representatives[logical_id]
        if representative not in source_ids:
            raise UnitSemanticsAuditError(
                f"Logical unit {logical_id} representative {representative} is not a source"
            )
    return representatives, dict(groups)


def _reinforcement_source_ids(connection: sqlite3.Connection) -> set[int]:
    kinds = {
        row["id"]: row["kind"]
        for row in connection.execute("SELECT id, kind FROM army_lists ORDER BY id")
    }
    memberships: dict[int, list[int]] = defaultdict(list)
    for row in connection.execute("SELECT army_id, unit_id FROM army_units ORDER BY unit_id"):
        memberships[row["unit_id"]].append(row["army_id"])
    return {
        unit_id
        for unit_id, army_ids in memberships.items()
        if army_ids and all(kinds.get(army_id) == "reinforcement" for army_id in army_ids)
    }


def _field_evidence(
    units: Mapping[int, Mapping[str, Any]],
    groups: Mapping[int, list[int]],
) -> dict[str, Any]:
    repeated = {logical_id: ids for logical_id, ids in groups.items() if len(ids) > 1}
    result: dict[str, Any] = {}
    for field in UNIT_FIELDS:
        values = [row[field] for row in units.values()]
        supported_groups = 0
        invariant_supported_groups = 0
        variant_groups = 0
        affected_sources = 0
        examples: list[dict[str, Any]] = []
        for logical_id, source_ids in sorted(repeated.items()):
            group_values = [units[source_id][field] for source_id in source_ids]
            if any(value is not None for value in group_values):
                supported_groups += 1
            signatures = {_value_key(field, value) for value in group_values}
            if len(signatures) <= 1:
                if any(value is not None for value in group_values):
                    invariant_supported_groups += 1
                continue
            variant_groups += 1
            affected_sources += len(source_ids)
            if len(examples) < 5:
                examples.append(
                    {
                        "logicalUnitId": logical_id,
                        "sources": [
                            {
                                "sourceUnitId": source_id,
                                "value": _display_value(field, units[source_id][field]),
                            }
                            for source_id in source_ids
                        ],
                    }
                )
        result[field] = {
            **UNIT_FIELD_CLASSIFICATION[field],
            "nonNullSourceUnitCount": sum(value is not None for value in values),
            "repeatedLogicalUnitSupportCount": supported_groups,
            "invariantRepeatedLogicalUnitCount": invariant_supported_groups,
            "variantLogicalUnitCount": variant_groups,
            "variantSourceUnitCount": affected_sources,
            "examples": examples,
        }
    return result


def _label_normalization_evidence(
    units: Mapping[int, Mapping[str, Any]],
    groups: Mapping[int, list[int]],
    config: IdentityConfig,
) -> dict[str, Any]:
    repeated = {logical_id: ids for logical_id, ids in groups.items() if len(ids) > 1}
    evidence: dict[str, Any] = {}
    for field in ("name", "isc", "isc_abbr"):
        raw_variants = 0
        prefix_variants = 0
        identity_variants = 0
        examples: list[dict[str, Any]] = []
        for logical_id, source_ids in sorted(repeated.items()):
            raw_values = [units[source_id][field] for source_id in source_ids]
            if len({_value_key(field, value) for value in raw_values}) <= 1:
                continue
            raw_variants += 1
            prefix_values = [strip_reinforcement_prefix(value, config) for value in raw_values]
            if len(set(prefix_values)) > 1:
                prefix_variants += 1
            identity_values = [normalized_unit_identity(value, config) for value in raw_values]
            if len(set(identity_values)) > 1:
                identity_variants += 1
                if len(examples) < 5:
                    examples.append(
                        {
                            "logicalUnitId": logical_id,
                            "sourceUnitIds": source_ids,
                            "raw": raw_values,
                            "normalizedIdentity": identity_values,
                        }
                    )
        evidence[field] = {
            "rawVariantLogicalUnitCount": raw_variants,
            "afterReinforcementPrefixRemovalVariantLogicalUnitCount": prefix_variants,
            "afterIdentityNormalizationVariantLogicalUnitCount": identity_variants,
            "remainingExamples": examples,
        }
    return evidence


def _representative_evidence(
    units: Mapping[int, Mapping[str, Any]],
    representatives: Mapping[int, int],
    groups: Mapping[int, list[int]],
    reinforcement_ids: set[int],
) -> dict[str, Any]:
    repeated = {logical_id: ids for logical_id, ids in groups.items() if len(ids) > 1}
    representative_ids = set(representatives.values())
    non_representatives = set(units) - representative_ids
    mercenary_ids = {
        unit_id
        for unit_id, unit in units.items()
        if unit["source_role"] == "mercenary_variant"
    }
    unexpected = sorted(non_representatives - reinforcement_ids - mercenary_ids)
    invalid_representatives = sorted(
        unit_id
        for unit_id in representative_ids
        if unit_id in reinforcement_ids or units[unit_id]["source_role"] != "standard"
    )

    alternate_label_groups = 0
    alternate_label_count = 0
    for logical_id, source_ids in repeated.items():
        representative = representatives[logical_id]
        representative_terms = {
            units[representative][field]
            for field in ("name", "isc", "isc_abbr", "slug")
            if units[representative][field]
        }
        all_terms = {
            units[source_id][field]
            for source_id in source_ids
            for field in ("name", "isc", "isc_abbr", "slug")
            if units[source_id][field]
        }
        alternate = all_terms - representative_terms
        if alternate:
            alternate_label_groups += 1
            alternate_label_count += len(alternate)

    hidden_note_groups: list[dict[str, Any]] = []
    for logical_id, source_ids in sorted(repeated.items()):
        representative = representatives[logical_id]
        representative_note = units[representative]["notes"]
        hidden = [
            {
                "sourceUnitId": source_id,
                "note": units[source_id]["notes"],
            }
            for source_id in source_ids
            if source_id != representative
            and units[source_id]["notes"]
            and units[source_id]["notes"] != representative_note
        ]
        if hidden:
            hidden_note_groups.append(
                {
                    "logicalUnitId": logical_id,
                    "representativeUnitId": representative,
                    "representativeNote": representative_note,
                    "sourceDeltas": hidden,
                }
            )

    return {
        "logicalUnitCount": len(groups),
        "representativeCount": len(representative_ids),
        "representativeReinforcementOrNonStandardCount": len(invalid_representatives),
        "representativeReinforcementOrNonStandardIds": invalid_representatives,
        "nonRepresentativeSourceCount": len(non_representatives),
        "nonRepresentativeReinforcementCount": len(non_representatives & reinforcement_ids),
        "nonRepresentativeMercenaryVariantCount": len(non_representatives & mercenary_ids),
        "nonRepresentativeOtherCount": len(unexpected),
        "nonRepresentativeOtherIds": unexpected,
        "repeatedLogicalUnitsWithAlternateGeneralLabels": alternate_label_groups,
        "alternateGeneralLabelCount": alternate_label_count,
        "logicalUnitsWithNonRepresentativeNoteDeltas": len(hidden_note_groups),
        "nonRepresentativeNoteDeltaSourceCount": sum(
            len(item["sourceDeltas"]) for item in hidden_note_groups
        ),
        "nonRepresentativeNoteDeltaExamples": hidden_note_groups[:10],
    }


def _faction_evidence(
    connection: sqlite3.Connection,
    groups: Mapping[int, list[int]],
) -> dict[str, Any]:
    memberships: dict[int, list[int]] = defaultdict(list)
    for row in connection.execute(
        "SELECT unit_id, faction_id FROM unit_factions ORDER BY unit_id, position"
    ):
        memberships[row["unit_id"]].append(row["faction_id"])
    repeated = {logical_id: ids for logical_id, ids in groups.items() if len(ids) > 1}
    variants = 0
    examples: list[dict[str, Any]] = []
    for logical_id, source_ids in sorted(repeated.items()):
        values = [tuple(memberships[source_id]) for source_id in source_ids]
        if len(set(values)) <= 1:
            continue
        variants += 1
        if len(examples) < 5:
            examples.append(
                {
                    "logicalUnitId": logical_id,
                    "sources": [
                        {
                            "sourceUnitId": source_id,
                            "factionIds": memberships[source_id],
                        }
                        for source_id in source_ids
                    ],
                }
            )
    return {
        **RELATIONSHIP_CLASSIFICATION["unit_factions"],
        "rowCount": sum(len(values) for values in memberships.values()),
        "sourceUnitCount": sum(bool(values) for values in memberships.values()),
        "variantRepeatedLogicalUnitCount": variants,
        "repeatedLogicalUnitCount": len(repeated),
        "examples": examples,
    }


def _strip_source_keys(row: Mapping[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: _display_value(field, row[field]) for field in fields}


def _unit_option_relationship_rows(
    connection: sqlite3.Connection,
) -> dict[str, dict[tuple[int, int], list[dict[str, Any]]]]:
    extras_by_table: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for parent_table, extra_table in UNIT_OPTION_EXTRA_TABLES.items():
        extras: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in connection.execute(
            f'SELECT * FROM "{extra_table}" ORDER BY occurrence_id, position'
        ):
            extras[row["occurrence_id"]].append(
                {"position": row["position"], "extra_id": row["extra_id"]}
            )
        extras_by_table[parent_table] = dict(extras)

    result: dict[str, dict[tuple[int, int], list[dict[str, Any]]]] = {}
    for table in UNIT_OPTION_RELATION_TABLES:
        grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        columns = EXPECTED_COLUMNS[table]
        payload_fields = tuple(
            column
            for column in columns
            if column not in {"unit_id", "option_id", "occurrence_id"}
        )
        query = f'SELECT * FROM "{table}" ORDER BY unit_id, option_id, position'
        for row in connection.execute(query):
            payload = _strip_source_keys(row, payload_fields)
            if table in UNIT_OPTION_EXTRA_TABLES:
                payload["extras"] = extras_by_table[table].get(row["occurrence_id"], [])
            grouped[(row["unit_id"], row["option_id"])].append(payload)
        result[table] = dict(grouped)
    return result


def _unit_option_evidence(
    connection: sqlite3.Connection,
    groups: Mapping[int, list[int]],
) -> dict[str, Any]:
    logical_by_source = {
        source_id: logical_id
        for logical_id, source_ids in groups.items()
        for source_id in source_ids
    }
    rows = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM unit_options ORDER BY unit_id, position, option_id"
        )
    ]
    relations = _unit_option_relationship_rows(connection)

    by_observational_key: dict[tuple[int, Any], list[dict[str, Any]]] = defaultdict(list)
    source_units_with_options: set[int] = set()
    logical_units_with_options: set[int] = set()
    for row in rows:
        source_id = row["unit_id"]
        source_units_with_options.add(source_id)
        try:
            logical_id = logical_by_source[source_id]
        except KeyError as exc:
            raise UnitSemanticsAuditError(
                f"Unit option references source unit {source_id} without logical identity"
            ) from exc
        logical_units_with_options.add(logical_id)
        by_observational_key[(logical_id, row["option_id"])].append(row)

    repeated_keys = {
        key: values for key, values in by_observational_key.items() if len(values) > 1
    }
    fields: dict[str, Any] = {}
    for field in UNIT_OPTION_FIELDS:
        variant_keys = 0
        examples: list[dict[str, Any]] = []
        for (logical_id, option_id), occurrences in sorted(repeated_keys.items()):
            values = [occurrence[field] for occurrence in occurrences]
            if len({_value_key(field, value) for value in values}) <= 1:
                continue
            variant_keys += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "logicalUnitId": logical_id,
                        "optionId": option_id,
                        "sources": [
                            {
                                "sourceUnitId": occurrence["unit_id"],
                                "value": _display_value(field, occurrence[field]),
                            }
                            for occurrence in occurrences
                        ],
                    }
                )
        fields[field] = {
            **UNIT_OPTION_FIELD_CLASSIFICATION[field],
            "variantRepeatedObservationalKeyCount": variant_keys,
            "examples": examples,
        }

    relationship_variants: dict[str, Any] = {}
    for table in UNIT_OPTION_RELATION_TABLES:
        variant_keys = 0
        row_count = 0
        examples: list[dict[str, Any]] = []
        for (logical_id, option_id), occurrences in sorted(repeated_keys.items()):
            payloads = []
            for occurrence in occurrences:
                payload = relations[table].get((occurrence["unit_id"], occurrence["option_id"]), [])
                row_count += len(payload)
                payloads.append(payload)
            if len({_canonical_json(payload) for payload in payloads}) <= 1:
                continue
            variant_keys += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "logicalUnitId": logical_id,
                        "optionId": option_id,
                        "sources": [
                            {
                                "sourceUnitId": occurrence["unit_id"],
                                "rows": payload,
                            }
                            for occurrence, payload in zip(occurrences, payloads, strict=True)
                        ],
                    }
                )
        relationship_variants[table] = {
            "variantRepeatedObservationalKeyCount": variant_keys,
            "repeatedKeyRowCount": row_count,
            "examples": examples,
        }

    collection_fingerprints: dict[int, str] = {}
    rows_by_source: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_source[row["unit_id"]].append(row)
    for source_id, options in rows_by_source.items():
        collection: list[dict[str, Any]] = []
        for option in options:
            option_id = option["option_id"]
            collection.append(
                {
                    "optionId": option_id,
                    "fields": _strip_source_keys(option, UNIT_OPTION_FIELDS),
                    "relationships": {
                        table: relations[table].get((source_id, option_id), [])
                        for table in UNIT_OPTION_RELATION_TABLES
                    },
                }
            )
        collection_fingerprints[source_id] = hashlib.sha256(
            _canonical_json(collection).encode("utf-8")
        ).hexdigest()

    repeated_logical_with_options = 0
    variant_collections = 0
    for _logical_id, source_ids in groups.items():
        source_ids_with_options = [
            source_id for source_id in source_ids if source_id in rows_by_source
        ]
        if len(source_ids_with_options) <= 1:
            continue
        repeated_logical_with_options += 1
        if len({collection_fingerprints[source_id] for source_id in source_ids_with_options}) > 1:
            variant_collections += 1

    return {
        **RELATIONSHIP_CLASSIFICATION["unit_options"],
        "rowCount": len(rows),
        "sourceUnitCount": len(source_units_with_options),
        "logicalUnitCount": len(logical_units_with_options),
        "repeatedLogicalUnitWithOptionsCount": repeated_logical_with_options,
        "variantRepeatedLogicalUnitCollectionCount": variant_collections,
        "observationalKey": ["logical_unit_id", "option_id"],
        "observationalKeyCaveat": (
            "option_id is source-local. The key is used only to compare current repeated "
            "source representations; it is not a proposed canonical option identity."
        ),
        "repeatedObservationalKeyCount": len(repeated_keys),
        "fields": fields,
        "relationships": relationship_variants,
    }



def _candidate_model_evidence(
    units: Mapping[int, Mapping[str, Any]],
    representatives: Mapping[int, int],
    groups: Mapping[int, list[int]],
    unit_options: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe the accepted logical-unit payload/context boundary from audited evidence."""
    canonical_fields = (
        "name",
        "isc",
        "isc_abbr",
        "slug",
        "canonical_faction_id",
        "main_army_id",
        "display_army_id",
    )
    alias_fields = ("name", "isc", "isc_abbr", "slug")

    aliases: list[tuple[int, int, str, Any]] = []
    note_occurrences: list[tuple[int, int, Any]] = []
    spectable_occurrences: list[tuple[int, int, Any]] = []
    for logical_id, source_ids in sorted(groups.items()):
        representative_id = representatives[logical_id]
        representative = units[representative_id]
        for source_id in source_ids:
            source = units[source_id]
            if source_id != representative_id:
                for field in alias_fields:
                    if field == "name":
                        value = source[field] or f"Unit {source_id}"
                        representative_value = (
                            representative[field] or f"Unit {representative_id}"
                        )
                    else:
                        value = source[field]
                        representative_value = representative[field]
                    if value and value != representative_value:
                        aliases.append((logical_id, source_id, field, value))
            if source["notes"]:
                note_occurrences.append((logical_id, source_id, source["notes"]))
            if source["spectables"]:
                spectable_occurrences.append(
                    (logical_id, source_id, source["spectables"])
                )

    return {
        "canonicalLogicalUnit": {
            "table": "logical_units",
            "rowCount": len(groups),
            "fields": list(canonical_fields),
            "sourcePolicy": (
                "Copy canonical display/general values from the existing deterministic "
                "representative source. Representative selection governs the application "
                "value but does not erase other source occurrences."
            ),
            "notesExcluded": True,
            "spectablesExcluded": True,
        },
        "sourceLinks": {
            "table": "logical_unit_sources",
            "rowCount": sum(len(source_ids) for source_ids in groups.values()),
            "policy": (
                "Retain every source-unit mapping as the provenance and source-occurrence "
                "bridge. Canonical logical-unit identity is not source occurrence identity."
            ),
        },
        "aliases": {
            "table": "logical_unit_aliases",
            "fields": ["logical_unit_id", "source_unit_id", "field", "value"],
            "sourceFields": list(alias_fields),
            "occurrenceCount": len(aliases),
            "distinctLogicalValueCount": len(
                {(logical_id, value) for logical_id, _source_id, _field, value in aliases}
            ),
            "logicalUnitCount": len({logical_id for logical_id, *_rest in aliases}),
            "policy": (
                "Store non-representative search/display values that differ from the canonical "
                "field. Missing source names retain their existing derived 'Unit <id>' fallback; "
                "keep field and source attribution so every search alias remains traceable."
            ),
        },
        "notes": {
            "table": "logical_unit_notes",
            "fields": ["logical_unit_id", "source_unit_id", "note"],
            "occurrenceCount": len(note_occurrences),
            "logicalUnitCount": len(
                {logical_id for logical_id, _source_id, _note in note_occurrences}
            ),
            "distinctLogicalValueCount": len(
                {(logical_id, note) for logical_id, _source_id, note in note_occurrences}
            ),
            "policy": (
                "Keep every non-empty source note attached to its source occurrence. Do not "
                "promote one representative note to a universal logical-unit fact."
            ),
        },
        "spectables": {
            "table": "logical_unit_spectables",
            "fields": ["logical_unit_id", "source_unit_id", "spectables"],
            "occurrenceCount": len(spectable_occurrences),
            "logicalUnitCount": len(
                {logical_id for logical_id, _source_id, _payload in spectable_occurrences}
            ),
            "policy": (
                "Preserve exact source payloads as opaque source-context data. Current "
                "singleton-only evidence is insufficient to declare spectables canonical."
            ),
        },
        "unitOptions": {
            "currentTable": "unit_options",
            "rowCount": unit_options["rowCount"],
            "sourceUnitCount": unit_options["sourceUnitCount"],
            "logicalUnitCount": unit_options["logicalUnitCount"],
            "policy": (
                "Keep top-level unit options and nested relationships as source-context "
                "payloads. Do not fold them into the canonical logical-unit row or infer "
                "cross-source option identity from source-local option_id."
            ),
        },
        "deferredRelationshipContext": [
            "source canonical/main/display faction relationships",
            "unit_factions",
            "army_units including filters and availability_kind",
        ],
    }


def _army_unit_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        "SELECT COUNT(*) AS row_count, COUNT(DISTINCT unit_id) AS unit_count FROM army_units"
    ).fetchone()
    availability = {
        value: count
        for value, count in connection.execute(
            "SELECT availability_kind, COUNT(*) FROM army_units "
            "GROUP BY availability_kind ORDER BY availability_kind"
        )
    }
    return {
        **RELATIONSHIP_CLASSIFICATION["army_units"],
        "rowCount": row["row_count"],
        "sourceUnitCount": row["unit_count"],
        "availabilityKindCounts": availability,
    }


def audit_database(path: Path) -> dict[str, Any]:
    """Return deterministic evidence for logical-unit canonicalization decisions."""
    path = path.resolve()
    if not path.is_file():
        raise UnitSemanticsAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_schema(connection)
        config = _identity_config(connection)
        units = {
            row["id"]: dict(row)
            for row in connection.execute(
                "SELECT * FROM units WHERE source_defined = 1 ORDER BY id"
            )
        }
        representatives, groups = _logical_groups(connection, units)
        repeated = {logical_id: ids for logical_id, ids in groups.items() if len(ids) > 1}
        reinforcement_ids = _reinforcement_source_ids(connection)
        metadata = _snapshot_metadata(connection)
        group_sizes = Counter(len(source_ids) for source_ids in groups.values())

        unit_options = _unit_option_evidence(connection, groups)
        report = {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "sha256": _sha256_file(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "summary": {
                "sourceUnitCount": len(units),
                "logicalUnitCount": len(groups),
                "repeatedLogicalUnitCount": len(repeated),
                "repeatedSourceUnitCount": sum(len(ids) for ids in repeated.values()),
                "singletonLogicalUnitCount": group_sizes.get(1, 0),
                "logicalUnitSourceCountDistribution": {
                    str(size): count for size, count in sorted(group_sizes.items())
                },
                "reinforcementOnlySourceUnitCount": len(reinforcement_ids),
                "mercenaryVariantSourceUnitCount": sum(
                    unit["source_role"] == "mercenary_variant" for unit in units.values()
                ),
            },
            "fields": _field_evidence(units, groups),
            "diagnosticLabelNormalization": {
                "policy": (
                    "Uses the database-pinned reinforcement-prefix and unit-identity "
                    "normalization rules only as comparison evidence. It does not rewrite "
                    "canonical display labels."
                ),
                "fields": _label_normalization_evidence(units, groups, config),
            },
            "representativeRule": _representative_evidence(
                units, representatives, groups, reinforcement_ids
            ),
            "relationships": {
                "unit_factions": _faction_evidence(connection, groups),
                "army_units": _army_unit_evidence(connection),
                "unit_options": unit_options,
            },
            "candidateModel": _candidate_model_evidence(
                units,
                representatives,
                groups,
                unit_options,
            ),
            "promotionConstraints": {
                "representativeBackedDisplayFields": [
                    "name",
                    "isc",
                    "isc_abbr",
                    "slug",
                    "canonical_faction_id",
                    "main_army_id",
                    "display_army_id",
                ],
                "sourceContextThatMustRemainTraceable": [
                    "source unit IDs and idArmy",
                    "alternate source names/ISC/abbreviations/slugs",
                    "source canonical/main/display faction relationships",
                    "source role",
                    "unit_factions",
                    "army_units including filters and availability_kind",
                    "source-specific notes",
                    "unit_options and nested relationships",
                ],
                "unprovenSingletonOnlyCandidateFields": ["spectables"],
                "relationshipSummaryFields": ["relation_reference_count"],
                "rule": (
                    "Do not promote a varying source field merely because a representative "
                    "exists. A canonical logical-unit value may follow the already-reviewed "
                    "representative-source rule only when source variants remain recoverable "
                    "and any distinct player-relevant deltas stay explicit."
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
    except (OSError, sqlite3.Error, UnitSemanticsAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    summary = report["summary"]
    representative = report["representativeRule"]
    options = report["relationships"]["unit_options"]
    print("InfinityDB logical-unit semantics audit")
    print(
        f"Units: {summary['sourceUnitCount']} source -> {summary['logicalUnitCount']} logical | "
        f"{summary['repeatedLogicalUnitCount']} multi-source logical units"
    )
    print(
        "Representative rule: "
        f"{representative['representativeReinforcementOrNonStandardCount']} invalid "
        "representatives | "
        f"{representative['nonRepresentativeReinforcementCount']} reinforcement + "
        f"{representative['nonRepresentativeMercenaryVariantCount']} mercenary variants"
    )
    print(
        "Source deltas: "
        f"{representative['repeatedLogicalUnitsWithAlternateGeneralLabels']} logical units "
        "with alternate general labels | "
        f"{representative['logicalUnitsWithNonRepresentativeNoteDeltas']} with "
        "non-representative note deltas"
    )
    print(
        "Unit options: "
        f"{options['rowCount']} rows across {options['logicalUnitCount']} logical units | "
        f"{options['variantRepeatedLogicalUnitCollectionCount']} repeated logical unit "
        "collection(s) vary"
    )
    candidate = report["candidateModel"]
    print(
        "Candidate model: "
        f"{candidate['canonicalLogicalUnit']['rowCount']} canonical rows | "
        f"{candidate['aliases']['occurrenceCount']} alias occurrences | "
        f"{candidate['notes']['occurrenceCount']} note occurrences | "
        f"{candidate['spectables']['occurrenceCount']} spectables occurrences"
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
