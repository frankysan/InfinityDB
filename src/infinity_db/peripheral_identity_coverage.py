"""Coverage checks for reviewed Army-local Peripheral identity mappings."""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from .peripheral_identities import PeripheralIdentityCurated, PeripheralIdentityError

COVERAGE_FORMAT = "InfinityDB Peripheral identity coverage"
COVERAGE_FORMAT_VERSION = 1


def _normalized_review_name(value: str) -> str:
    """Normalize names only for deterministic review grouping, never identity."""
    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


def _require_peripheral_schema(connection: sqlite3.Connection) -> None:
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    for table in ("__infinity_metadata", "peripherals"):
        if table not in tables:
            raise PeripheralIdentityError(
                f"Peripheral identity coverage requires table {table!r}"
            )
    columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(peripherals)").fetchall()
    }
    required = {"army_id", "id", "name", "mercs"}
    missing = sorted(required - columns)
    if missing:
        raise PeripheralIdentityError(
            "Peripheral identity coverage peripherals table is missing column(s): "
            + ", ".join(missing)
        )


def _database_snapshot_sha256(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', ("_meta",)
    ).fetchone()
    try:
        metadata = json.loads(row[0]) if row is not None else None
    except (json.JSONDecodeError, TypeError) as exc:
        raise PeripheralIdentityError(
            f"Could not read Peripheral identity coverage database provenance: {exc}"
        ) from exc
    value = metadata.get("snapshotArchiveSha256") if isinstance(metadata, dict) else None
    if not isinstance(value, str) or len(value) != 64:
        raise PeripheralIdentityError(
            "Peripheral identity coverage database has no valid snapshotArchiveSha256"
        )
    return value.lower()


def _source_for_snapshot(document: dict[str, Any], snapshot_sha256: str) -> dict[str, Any]:
    sources = document.get("sources")
    if not isinstance(sources, list):
        raise PeripheralIdentityError("Peripheral identity curated sources are unavailable")
    matches = [
        source
        for source in sources
        if isinstance(source, dict)
        and isinstance(source.get("sha256"), str)
        and source["sha256"].lower() == snapshot_sha256
    ]
    if len(matches) != 1:
        raise PeripheralIdentityError(
            "Peripheral identity curated data must declare exactly one source matching "
            f"database snapshot {snapshot_sha256}"
        )
    return matches[0]


def audit_peripheral_identity_coverage(
    curated: PeripheralIdentityCurated,
    database: Path,
    *,
    include_details: bool = True,
) -> dict[str, Any]:
    """Compare reviewed mappings with one exact Army database snapshot."""
    database = Path(database)
    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        try:
            _require_peripheral_schema(connection)
            snapshot_sha256 = _database_snapshot_sha256(connection)
            schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            rows = [
                {
                    "armyId": int(row["army_id"]),
                    "peripheralId": int(row["id"]),
                    "sourceName": str(row["name"]),
                    "mercs": row["mercs"],
                }
                for row in connection.execute(
                    "SELECT army_id, id, name, mercs FROM peripherals ORDER BY army_id, id"
                )
            ]
        finally:
            connection.close()
    except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
        raise PeripheralIdentityError(
            f"Could not audit Peripheral identity coverage from {database}: {exc}"
        ) from exc

    document = curated.document
    source = _source_for_snapshot(document, snapshot_sha256)
    source_id = source.get("id")
    if not isinstance(source_id, str):
        raise PeripheralIdentityError("Matched Peripheral identity source has no valid id")

    definitions = {(row["armyId"], row["peripheralId"]): row for row in rows}
    mappings_value = document.get("mappings")
    mappings = mappings_value if isinstance(mappings_value, list) else []
    current_mappings = [
        mapping
        for mapping in mappings
        if isinstance(mapping, dict) and mapping.get("sourceId") == source_id
    ]
    mapping_by_key = {
        (int(mapping["armyId"]), int(mapping["peripheralId"])): mapping
        for mapping in current_mappings
    }

    stale_mappings: list[dict[str, Any]] = []
    source_name_drift: list[dict[str, Any]] = []
    for key, mapping in sorted(mapping_by_key.items()):
        definition = definitions.get(key)
        if definition is None:
            stale_mappings.append(
                {
                    "mappingId": mapping.get("id"),
                    "armyId": key[0],
                    "peripheralId": key[1],
                    "sourceName": mapping.get("sourceName"),
                }
            )
            continue
        if mapping.get("sourceName") != definition["sourceName"]:
            source_name_drift.append(
                {
                    "mappingId": mapping.get("id"),
                    "armyId": key[0],
                    "peripheralId": key[1],
                    "expectedSourceName": mapping.get("sourceName"),
                    "actualSourceName": definition["sourceName"],
                }
            )

    mapped_keys = set(mapping_by_key) & set(definitions)
    unmapped_rows = [row for key, row in definitions.items() if key not in mapped_keys]

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_normalized_review_name(row["sourceName"])].append(row)

    review_queue: list[dict[str, Any]] = []
    repeated_name_group_count = 0
    normalized_name_collision_count = 0
    for normalized_name, group_rows in sorted(groups.items()):
        if len(group_rows) > 1:
            repeated_name_group_count += 1
        source_names = sorted({row["sourceName"] for row in group_rows})
        if len(source_names) > 1:
            normalized_name_collision_count += 1
        unmapped = [
            row
            for row in group_rows
            if (row["armyId"], row["peripheralId"]) not in mapped_keys
        ]
        if not unmapped:
            continue
        reviewed_targets = sorted(
            {
                (
                    str(mapping_by_key[(row["armyId"], row["peripheralId"])].get("entityId")),
                    str(
                        mapping_by_key[(row["armyId"], row["peripheralId"])].get(
                            "profileId", ""
                        )
                    ),
                )
                for row in group_rows
                if (row["armyId"], row["peripheralId"]) in mapping_by_key
            }
        )
        entry: dict[str, Any] = {
            "normalizedName": normalized_name,
            "sourceNames": source_names,
            "definitionCount": len(group_rows),
            "unmappedDefinitionCount": len(unmapped),
            "mercsValues": sorted(
                {row["mercs"] for row in group_rows}, key=lambda value: str(value)
            ),
            "nameCollision": len(source_names) > 1,
            "reviewedTargets": [
                {
                    "entityId": entity_id,
                    **({"profileId": profile_id} if profile_id else {}),
                }
                for entity_id, profile_id in reviewed_targets
            ],
        }
        if include_details:
            entry["unmappedDefinitions"] = unmapped
        review_queue.append(entry)

    entities_value = document.get("entities")
    entities = entities_value if isinstance(entities_value, list) else []
    profiles_value = document.get("profiles")
    profiles = profiles_value if isinstance(profiles_value, list) else []
    mapped_entity_ids = {
        str(mapping.get("entityId"))
        for mapping in current_mappings
        if (int(mapping["armyId"]), int(mapping["peripheralId"])) in definitions
    }
    mapped_profile_ids = {
        str(mapping.get("profileId"))
        for mapping in current_mappings
        if "profileId" in mapping
        and (int(mapping["armyId"]), int(mapping["peripheralId"])) in definitions
    }
    curated_only_entities = sorted(
        str(entity.get("id"))
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("id")) not in mapped_entity_ids
    )
    curated_only_profiles = sorted(
        str(profile.get("id"))
        for profile in profiles
        if isinstance(profile, dict) and str(profile.get("id")) not in mapped_profile_ids
    )

    invalid_count = len(stale_mappings) + len(source_name_drift)
    unmapped_count = len(unmapped_rows)
    definition_count = len(rows)
    status = "invalid" if invalid_count else ("complete" if unmapped_count == 0 else "needs-review")
    coverage_percent = 100.0 if definition_count == 0 else round(
        (len(mapped_keys) / definition_count) * 100.0, 2
    )

    report: dict[str, Any] = {
        "format": COVERAGE_FORMAT,
        "formatVersion": COVERAGE_FORMAT_VERSION,
        "status": status,
        "database": {
            "path": str(database),
            "schemaVersion": schema_version,
            "snapshotArchiveSha256": snapshot_sha256,
            "sourceId": source_id,
        },
        "definitions": {
            "definitionCount": definition_count,
            "mappedDefinitionCount": len(mapped_keys),
            "unmappedDefinitionCount": unmapped_count,
            "coveragePercent": coverage_percent,
            "reviewGroupCount": len(groups),
            "unmappedReviewGroupCount": len(review_queue),
            "repeatedNameGroupCount": repeated_name_group_count,
            "normalizedNameCollisionCount": normalized_name_collision_count,
        },
        "curated": {
            "entityCount": curated.entity_count,
            "profileCount": curated.profile_count,
            "mappingCount": curated.mapping_count,
            "currentSnapshotMappingCount": len(current_mappings),
            "curatedOnlyEntityCount": len(curated_only_entities),
            "curatedOnlyProfileCount": len(curated_only_profiles),
        },
        "validation": {
            "staleMappingCount": len(stale_mappings),
            "sourceNameDriftCount": len(source_name_drift),
            "status": "valid" if invalid_count == 0 else "invalid",
        },
        "reviewQueue": review_queue,
    }
    if include_details:
        report["validation"]["staleMappings"] = stale_mappings
        report["validation"]["sourceNameDrift"] = source_name_drift
        report["curated"]["curatedOnlyEntities"] = curated_only_entities
        report["curated"]["curatedOnlyProfiles"] = curated_only_profiles
    return report
