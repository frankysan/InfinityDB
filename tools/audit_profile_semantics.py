#!/usr/bin/env python3
"""Audit profile-field semantics and army-context variation in InfinityDB."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REPORT_FORMAT = "InfinityDB profile semantics audit"
REPORT_FORMAT_VERSION = 1

PROFILE_KEY = ("army_id", "unit_id", "group_id", "profile_id")
SOURCE_PROFILE_KEY = ("unit_id", "group_id", "profile_id")
PROFILE_GROUP_KEY = ("army_id", "unit_id", "group_id")
SOURCE_PROFILE_GROUP_KEY = ("unit_id", "group_id")

PROFILE_FIELDS = (
    "army_id",
    "unit_id",
    "group_id",
    "profile_id",
    "position",
    "name",
    "logo",
    "type_id",
    "move_1",
    "move_2",
    "cc",
    "bs",
    "ph",
    "wip",
    "arm",
    "bts",
    "vitality",
    "silhouette",
    "ava",
    "is_structure",
    "notes",
)
PROFILE_GROUP_FIELDS = (
    "army_id",
    "unit_id",
    "group_id",
    "position",
    "category_id",
    "isc",
    "notes",
)
ITEM_FIELDS = ("item_id", "display_order", "quantity", "raw")
CHARACTERISTIC_FIELDS = ("characteristic_id",)
INCLUDE_FIELDS = ("target_group_id", "target_option_id", "quantity", "raw")
EXTRA_FIELDS = ("extra_id",)

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "profiles": PROFILE_FIELDS,
    "profile_groups": PROFILE_GROUP_FIELDS,
    "profile_characteristics": (*PROFILE_KEY, "position", *CHARACTERISTIC_FIELDS),
    "profile_skills": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "profile_skill_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "profile_equipment": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "profile_equipment_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "profile_weapons": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "profile_weapon_extras": ("occurrence_id", "position", *EXTRA_FIELDS),
    "profile_includes": (*PROFILE_KEY, "position", *INCLUDE_FIELDS),
    "profile_peripherals": ("occurrence_id", *PROFILE_KEY, "position", *ITEM_FIELDS),
    "__infinity_metadata": ("key", "value"),
}

PROFILE_CLASSIFICATION: dict[str, dict[str, str]] = {
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
    "profile_id": {
        "classification": "source_provenance",
        "reason": "Source-local profile identity.",
    },
    "position": {
        "classification": "normalization_only",
        "reason": "Generated from source array order; literal ordinal is not profile identity.",
    },
    "name": {
        "classification": "canonical_fact",
        "reason": (
            "Profile-scoped display identity; invariant for repeated source-profile keys "
            "in the audited snapshot."
        ),
    },
    "logo": {
        "classification": "contextual_delta",
        "reason": (
            "Source presentation metadata with observed army-specific variation for the same "
            "source-profile key."
        ),
    },
    "type_id": {
        "classification": "relationship",
        "reason": "Relationship to the troop-type catalog.",
    },
    "move_1": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "move_2": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "cc": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "bs": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "ph": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "wip": {
        "classification": "contextual_delta",
        "reason": (
            "Profile gameplay statistic with observed army-specific variation for the same "
            "source-profile key."
        ),
    },
    "arm": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "bts": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "vitality": {
        "classification": "canonical_fact",
        "reason": (
            "Profile wounds/structure value; invariant for repeated source-profile keys in "
            "the audited snapshot."
        ),
    },
    "silhouette": {
        "classification": "canonical_fact",
        "reason": (
            "Profile gameplay statistic; invariant for repeated source-profile keys in the "
            "audited snapshot."
        ),
    },
    "ava": {
        "classification": "contextual_delta",
        "reason": (
            "Availability is explicitly army-contextual and varies widely for the same "
            "source-profile key."
        ),
    },
    "is_structure": {
        "classification": "canonical_fact",
        "reason": (
            "Determines wounds-versus-structure interpretation; invariant for repeated "
            "source-profile keys in the audited snapshot."
        ),
    },
    "notes": {
        "classification": "canonical_fact",
        "reason": (
            "Profile-scoped source field; currently unpopulated, so no invariance conclusion "
            "can be drawn from the snapshot."
        ),
    },
}

PROFILE_GROUP_CLASSIFICATION: dict[str, dict[str, str]] = {
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
    "position": {
        "classification": "normalization_only",
        "reason": "Generated from source group-array order.",
    },
    "category_id": {
        "classification": "relationship",
        "reason": "Relationship to the category/classification catalog.",
    },
    "isc": {
        "classification": "canonical_fact",
        "reason": (
            "Profile-group display label; invariant for repeated source-group keys in the "
            "audited snapshot."
        ),
    },
    "notes": {
        "classification": "canonical_fact",
        "reason": "Profile-group source field; currently unpopulated.",
    },
}

RELATIONSHIP_CLASSIFICATION: dict[str, dict[str, Any]] = {
    "characteristics": {
        "table": "profile_characteristics",
        "classification": "relationship",
        "reason": (
            "Profile-to-characteristic relationships; observed army-context variation is "
            "meaningful."
        ),
    },
    "skills": {
        "table": "profile_skills",
        "extrasTable": "profile_skill_extras",
        "classification": "relationship",
        "reason": (
            "Profile-to-skill relationships and skill extras; both meaningful relationships "
            "and source-encoding variation occur."
        ),
    },
    "equipment": {
        "table": "profile_equipment",
        "extrasTable": "profile_equipment_extras",
        "classification": "relationship",
        "reason": (
            "Profile-to-equipment relationships; current same-profile variation collapses "
            "after presentation/default normalization."
        ),
    },
    "weapons": {
        "table": "profile_weapons",
        "extrasTable": "profile_weapon_extras",
        "classification": "relationship",
        "reason": (
            "Profile-to-weapon relationships; no same-source-profile variation is present "
            "in the audited snapshot."
        ),
    },
    "includes": {
        "table": "profile_includes",
        "classification": "relationship",
        "reason": "Relationship from a profile to an included loadout option.",
    },
    "peripherals": {
        "table": "profile_peripherals",
        "classification": "relationship",
        "reason": (
            "Relationship from a profile to an army-local peripheral; the audited snapshot "
            "contains no profile-level peripheral rows."
        ),
    },
}


class ProfileSemanticsAuditError(ValueError):
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
            raise ProfileSemanticsAuditError(f"Required table is missing: {table}")
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        if missing or unexpected:
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if unexpected:
                details.append(f"unclassified {', '.join(unexpected)}")
            raise ProfileSemanticsAuditError(
                f"Profile semantic classification for {table} is stale ({'; '.join(details)})"
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


def _field_evidence(
    rows: list[dict[str, Any]],
    *,
    fields: tuple[str, ...],
    source_key: tuple[str, ...],
    classifications: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_row_key(row, source_key)].append(row)

    result: dict[str, Any] = {}
    for field in fields:
        values = [row[field] for row in rows]
        variant_groups = 0
        affected_occurrences = 0
        examples: list[dict[str, Any]] = []
        if field not in source_key:
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
                                {"armyId": row.get("army_id"), "value": _decode_raw(row[field])}
                                for row in group
                            ],
                        }
                    )
        result[field] = {
            **classifications[field],
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
    connection: sqlite3.Connection,
    table: str,
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    result: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        f'SELECT * FROM "{table}" ORDER BY army_id, unit_id, group_id, profile_id, position'
    ):
        item = dict(row)
        result[_row_key(item, PROFILE_KEY)].append(item)
    return result


def _relationship_payload(
    name: str,
    rows: list[dict[str, Any]],
    *,
    extras: Mapping[Any, list[dict[str, Any]]] | None,
    normalize_representation: bool,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        if name == "characteristics":
            item = {"characteristic_id": row["characteristic_id"]}
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
            item = {
                "item_id": row["item_id"],
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
    profile_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]]:
    profiles_by_source: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in profile_rows:
        profiles_by_source[_row_key(row, SOURCE_PROFILE_KEY)].append(row)

    all_rows: dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]] = {}
    result: dict[str, Any] = {}
    for name, definition in RELATIONSHIP_CLASSIFICATION.items():
        table = definition["table"]
        rows_by_parent = _relationship_rows(connection, table)
        all_rows[name] = rows_by_parent
        extras_table = definition.get("extrasTable")
        extras = _extras_by_occurrence(connection, extras_table) if extras_table else None
        raw_variant = 0
        normalized_variant = 0
        affected_raw = 0
        affected_normalized = 0
        examples: list[dict[str, Any]] = []
        for source_key, profiles in sorted(profiles_by_source.items()):
            if len(profiles) < 2:
                continue
            raw_payloads = []
            normalized_payloads = []
            occurrence_view = []
            for profile in profiles:
                parent = _row_key(profile, PROFILE_KEY)
                source_rows = rows_by_parent.get(parent, [])
                raw_payload = _relationship_payload(
                    name,
                    source_rows,
                    extras=extras,
                    normalize_representation=False,
                )
                normalized_payload = _relationship_payload(
                    name,
                    source_rows,
                    extras=extras,
                    normalize_representation=True,
                )
                raw_payloads.append(_canonical_json(raw_payload))
                normalized_payloads.append(_canonical_json(normalized_payload))
                occurrence_view.append(
                    {"armyId": profile["army_id"], "payload": raw_payload}
                )
            raw_differs = len(set(raw_payloads)) > 1
            normalized_differs = len(set(normalized_payloads)) > 1
            if raw_differs:
                raw_variant += 1
                affected_raw += len(profiles)
            if normalized_differs:
                normalized_variant += 1
                affected_normalized += len(profiles)
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
            "populatedProfileOccurrenceCount": len(rows_by_parent),
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
        if examples:
            relationship_result["variantExamples"] = examples
        result[name] = relationship_result
    return result, all_rows


def _profile_payload(
    profile: Mapping[str, Any],
    relationship_rows: Mapping[str, Mapping[tuple[Any, ...], list[dict[str, Any]]]],
    extras: Mapping[str, Mapping[Any, list[dict[str, Any]]]],
    *,
    omit_ava: bool,
    omit_logo: bool,
    normalize_representation: bool,
) -> dict[str, Any]:
    parent = _row_key(profile, PROFILE_KEY)
    payload: dict[str, Any] = {}
    for field in PROFILE_FIELDS:
        if field in PROFILE_KEY or field == "position":
            continue
        if omit_ava and field == "ava":
            continue
        if omit_logo and field == "logo":
            continue
        payload[field] = profile[field]
    for name in RELATIONSHIP_CLASSIFICATION:
        payload[name] = _relationship_payload(
            name,
            relationship_rows[name].get(parent, []),
            extras=extras.get(name),
            normalize_representation=normalize_representation,
        )
    return payload


def _variant_identity_count(
    profile_rows: list[dict[str, Any]],
    relationship_rows: Mapping[str, Mapping[tuple[Any, ...], list[dict[str, Any]]]],
    extras: Mapping[str, Mapping[Any, list[dict[str, Any]]]],
    *,
    omit_ava: bool = False,
    omit_logo: bool = False,
    normalize_representation: bool = False,
) -> int:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for profile in profile_rows:
        groups[_row_key(profile, SOURCE_PROFILE_KEY)].append(profile)
    count = 0
    for profiles in groups.values():
        if len(profiles) < 2:
            continue
        signatures = {
            _canonical_json(
                _profile_payload(
                    profile,
                    relationship_rows,
                    extras,
                    omit_ava=omit_ava,
                    omit_logo=omit_logo,
                    normalize_representation=normalize_representation,
                )
            )
            for profile in profiles
        }
        if len(signatures) > 1:
            count += 1
    return count


def _profile_group_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = [dict(row) for row in connection.execute(
        "SELECT * FROM profile_groups ORDER BY army_id, unit_id, group_id"
    )]
    return {
        "rowCount": len(rows),
        "fields": _field_evidence(
            rows,
            fields=PROFILE_GROUP_FIELDS,
            source_key=SOURCE_PROFILE_GROUP_KEY,
            classifications=PROFILE_GROUP_CLASSIFICATION,
        ),
    }


def audit_database(path: Path) -> dict[str, Any]:
    """Return deterministic evidence for classifying profile canonicalization fields."""
    path = path.resolve()
    if not path.is_file():
        raise ProfileSemanticsAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_schema(connection)
        profile_rows = [dict(row) for row in connection.execute(
            "SELECT * FROM profiles ORDER BY army_id, unit_id, group_id, profile_id"
        )]
        source_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in profile_rows:
            source_groups[_row_key(row, SOURCE_PROFILE_KEY)].append(row)
        repeated = [group for group in source_groups.values() if len(group) > 1]

        relationships, relationship_rows = _relationship_evidence(connection, profile_rows)
        extras = {
            "skills": _extras_by_occurrence(connection, "profile_skill_extras"),
            "equipment": _extras_by_occurrence(connection, "profile_equipment_extras"),
            "weapons": _extras_by_occurrence(connection, "profile_weapon_extras"),
        }
        metadata = _metadata(connection)
        staged = {
            "baselineVariantIdentityCount": _variant_identity_count(
                profile_rows, relationship_rows, extras
            ),
            "withoutAvaVariantIdentityCount": _variant_identity_count(
                profile_rows, relationship_rows, extras, omit_ava=True
            ),
            "withoutAvaOrLogoVariantIdentityCount": _variant_identity_count(
                profile_rows, relationship_rows, extras, omit_ava=True, omit_logo=True
            ),
            "withoutAvaOrLogoAndNormalizedRepresentationVariantIdentityCount": (
                _variant_identity_count(
                    profile_rows,
                    relationship_rows,
                    extras,
                    omit_ava=True,
                    omit_logo=True,
                    normalize_representation=True,
                )
            ),
        }

        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "sha256": _sha256_file(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "sourceProfileKey": list(SOURCE_PROFILE_KEY),
            "sourceProfileKeyCaveat": (
                "The source profile key is an observational comparison key across Army "
                "occurrences, not a proposed canonical application identity."
            ),
            "summary": {
                "profileOccurrenceCount": len(profile_rows),
                "sourceProfileIdentityCount": len(source_groups),
                "repeatedSourceProfileIdentityCount": len(repeated),
                "repeatedSourceProfileOccurrenceCount": sum(len(group) for group in repeated),
                **staged,
            },
            "fields": _field_evidence(
                profile_rows,
                fields=PROFILE_FIELDS,
                source_key=SOURCE_PROFILE_KEY,
                classifications=PROFILE_CLASSIFICATION,
            ),
            "profileGroups": _profile_group_evidence(connection),
            "relationships": relationships,
            "representationNormalization": {
                "displayOrder": (
                    "Ignored only in the diagnostic normalized view. Source display_order is "
                    "preserved as context and is not yet discarded by the application model."
                ),
                "quantity": (
                    "The diagnostic normalized view treats omitted quantity and explicit 1 as "
                    "equivalent. This is evidence of source-encoding duplication, not yet a "
                    "canonicalization rule."
                ),
                "relativeOrder": (
                    "Array-relative row and extra ordering remains significant in both views."
                ),
            },
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Frontend infinity.db to audit")
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database)
    except (OSError, sqlite3.Error, ProfileSemanticsAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    summary = report["summary"]
    print("InfinityDB profile semantics audit")
    print(
        f"Profiles: {summary['profileOccurrenceCount']} occurrences | "
        f"{summary['sourceProfileIdentityCount']} source-profile keys | "
        f"{summary['repeatedSourceProfileIdentityCount']} repeated keys"
    )
    print(
        "Variant repeated keys: "
        f"{summary['baselineVariantIdentityCount']} baseline -> "
        f"{summary['withoutAvaVariantIdentityCount']} without AVA -> "
        f"{summary['withoutAvaOrLogoVariantIdentityCount']} without AVA/logo -> "
        f"{summary['withoutAvaOrLogoAndNormalizedRepresentationVariantIdentityCount']} "
        "after representation normalization"
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
