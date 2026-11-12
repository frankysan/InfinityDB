"""Relational exact-variant occurrences linked to the existing reviewed Rules model."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

from .variant_usage_reference import (
    PUBLICATION_FORMAT,
    PUBLICATION_SCOPE,
    _canonical,
    _validate_publication,
)

VARIANT_USAGE_SCHEMA_VERSION = 11
VARIANT_USAGE_COMPATIBILITY_VERSION = 13
_COUNTS = (
    "uniqueUnits", "uniqueArmyUnits", "distinctContexts", "distinctProfileContexts",
    "distinctLoadoutContexts", "sourceRelationshipRows",
)
_ROW_FIELDS = (
    "catalog", "ownerKind", "occurrenceId", "sourceId", "applicationItemId",
    "armyId", "unitId", "groupId", "parentId", "optionId", "position", "displayOrder",
    "quantity", "raw",
)
_CONTEXT_FIELDS = (
    "applicationArmyId", "logicalUnitId", "sourceUnitId", "payloadSha256",
    "sourceArmyId", "groupId", "parentId", "contextPosition",
)
_SCHEMA = (
    """CREATE TABLE variant_usage_metadata (
        id INTEGER PRIMARY KEY CHECK(id=1), format_version INTEGER NOT NULL CHECK(format_version=1),
        army_archive_sha256 TEXT NOT NULL CHECK(length(army_archive_sha256)=64),
        army_database_sha256 TEXT NOT NULL CHECK(length(army_database_sha256)=64),
        army_export_pair_sha256 TEXT NOT NULL CHECK(length(army_export_pair_sha256)=64),
        group_count INTEGER NOT NULL CHECK(group_count>0),
        row_count INTEGER NOT NULL CHECK(row_count>=0), content_sha256 TEXT NOT NULL
    )""",
    """CREATE TABLE variant_usage_groups (
        id INTEGER PRIMARY KEY, variant_key TEXT NOT NULL UNIQUE,
        collection_id TEXT NOT NULL, record_id TEXT NOT NULL,
        effect_kind TEXT NOT NULL CHECK(effect_kind IN ('source','distance','extra','combination')),
        parameter_position INTEGER, extra_position INTEGER, combination_position INTEGER,
        raw_distance TEXT,
        unique_units INTEGER NOT NULL CHECK(unique_units>=0),
        unique_army_units INTEGER NOT NULL CHECK(unique_army_units>=0),
        distinct_contexts INTEGER NOT NULL CHECK(distinct_contexts>=0),
        distinct_profile_contexts INTEGER NOT NULL CHECK(distinct_profile_contexts>=0),
        distinct_loadout_contexts INTEGER NOT NULL CHECK(distinct_loadout_contexts>=0),
        source_relationship_rows INTEGER NOT NULL CHECK(source_relationship_rows>=0),
        FOREIGN KEY(collection_id, record_id) REFERENCES records(collection_id,id),
        CHECK((effect_kind='source' AND parameter_position IS NULL AND extra_position IS NULL
                   AND combination_position IS NULL AND raw_distance IS NULL)
           OR (effect_kind='distance' AND parameter_position IS NOT NULL AND parameter_position>=0
                   AND extra_position IS NULL
                   AND combination_position IS NULL AND raw_distance IS NOT NULL)
           OR (effect_kind='extra' AND parameter_position IS NOT NULL AND parameter_position>=0
                   AND extra_position IS NOT NULL AND extra_position>=0
                   AND combination_position IS NULL AND raw_distance IS NULL)
           OR (effect_kind='combination' AND combination_position IS NOT NULL
                   AND combination_position>=0 AND parameter_position IS NULL
                   AND extra_position IS NULL AND raw_distance IS NULL))
    )""",
    """CREATE INDEX variant_usage_record ON variant_usage_groups(record_id, variant_key)""",
    """CREATE TABLE variant_usage_source_rows (
        id INTEGER PRIMARY KEY, group_id INTEGER NOT NULL REFERENCES variant_usage_groups(id),
        ordinal INTEGER NOT NULL CHECK(ordinal>=0),
        catalog TEXT NOT NULL CHECK(catalog IN ('skills','equipment')),
        owner_kind TEXT NOT NULL CHECK(owner_kind IN ('profile','option','unit_option')),
        occurrence_id INTEGER NOT NULL CHECK(occurrence_id>0), source_id INTEGER NOT NULL,
        application_item_id INTEGER NOT NULL, army_id INTEGER, unit_id INTEGER NOT NULL,
        group_source_id INTEGER, parent_id INTEGER, option_id INTEGER,
        source_position INTEGER NOT NULL CHECK(source_position>=0), display_order INTEGER,
        quantity INTEGER, raw TEXT,
        application_army_id INTEGER, logical_unit_id INTEGER, source_unit_id INTEGER NOT NULL,
        payload_sha256 TEXT, context_army_id INTEGER, context_group_id INTEGER,
        context_parent_id INTEGER, context_position INTEGER,
        shared_compatible TEXT, shared_disabled INTEGER, shared_raw TEXT,
        parameter_position INTEGER, extra_position INTEGER, combination_position INTEGER,
        UNIQUE(catalog,owner_kind,occurrence_id), UNIQUE(group_id,ordinal),
        CHECK(owner_kind!='unit_option' OR
              (application_army_id IS NULL AND logical_unit_id IS NULL AND payload_sha256 IS NULL))
    )""",
    """CREATE TABLE variant_usage_extras (
        row_id INTEGER NOT NULL REFERENCES variant_usage_source_rows(id),
        ordinal INTEGER NOT NULL CHECK(ordinal>=0), position INTEGER NOT NULL CHECK(position>=0),
        extra_id INTEGER NOT NULL, extra_type TEXT, raw_value TEXT,
        PRIMARY KEY(row_id,ordinal), UNIQUE(row_id,position)
    )""",
)


def _rule_variant(connection: sqlite3.Connection, collection: str, record: str) -> dict[str, Any]:
    from .rules_database import _variant_semantics

    row = connection.execute(
        "SELECT variant_json,kind,composition_role FROM records WHERE collection_id=? AND id=?",
        (collection, record),
    ).fetchone()
    if row is None or row[1] not in {"skill", "equipment"} or row[2] != "definition":
        raise ValueError("Variant usage requires an exact reviewed rule definition")
    return _variant_semantics(row[0]) or {"inheritance": "family"}


def _effect(variant: dict[str, Any], selector: tuple[Any, ...]) -> dict[str, Any]:
    kind, parameter, extra, combination, distance = selector
    positions = (parameter, extra, combination)
    expected = {
        "source": (False, False, False), "distance": (True, False, False),
        "extra": (True, True, False), "combination": (False, False, True),
    }.get(kind)
    if expected is None or any(
        (type(value) is not int or value < 0) if required else value is not None
        for value, required in zip(positions, expected, strict=True)
    ) or (kind != "distance" and distance is not None):
        raise ValueError("Invalid reviewed variant coordinates")
    effect = {"sourceVariant": variant.get("source_variant")}
    try:
        if kind == "combination":
            entry = variant["occurrence_combinations"][combination]
            effect["combinationEffects"] = entry["effects"]
        elif kind in {"distance", "extra"}:
            entry = variant["occurrence_parameters"][parameter]
            if kind == "distance":
                if entry["kind"] != "distance" or not isinstance(distance, str):
                    raise ValueError("Invalid variant distance reference")
                effect.update(parameter=entry, rawDistance=distance)
            else:
                effect.update(parameter=entry["extra_values"][extra], parameterKind=entry["kind"])
        elif kind != "source" or not effect["sourceVariant"]:
            raise ValueError("Invalid variant source reference")
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Variant usage points outside its reviewed rule model") from exc
    return effect


def _signature_matches(
    variant: dict[str, Any], selector: tuple[Any, ...], extras: list[dict[str, Any]],
) -> bool:
    kind, parameter, extra, combination, distance = selector
    signature = [(item["extraId"], item["extraType"], item["rawValue"]) for item in extras]
    if kind == "source":
        return not extras
    if kind == "distance":
        return len(extras) == 1 and extras[0]["extraType"] == "DISTANCE" and (
            extras[0]["rawValue"] == distance
        )
    if kind == "extra":
        values = [variant["occurrence_parameters"][parameter]["extra_values"][extra]]
    else:
        values = variant["occurrence_combinations"][combination]["extras"]
    return signature == [
        (item["extra_id"], item["extra_type"], item["raw_value"]) for item in values
    ]


def _selector(
    variant: dict[str, Any], effect: dict[str, Any], extras: list[dict[str, Any]] | None = None,
) -> tuple[Any, ...]:
    selectors: list[tuple[Any, ...]] = []
    if variant.get("source_variant"):
        selectors.append(("source", None, None, None, None))
    for index, parameter in enumerate(variant.get("occurrence_parameters", [])):
        if parameter["kind"] == "distance" and "rawDistance" in effect:
            selectors.append(("distance", index, None, None, effect["rawDistance"]))
        selectors.extend(
            ("extra", index, extra, None, None)
            for extra in range(len(parameter.get("extra_values", [])))
        )
    selectors.extend(
        ("combination", None, None, index, None)
        for index in range(len(variant.get("occurrence_combinations", [])))
    )
    matches = [selector for selector in selectors if _effect(variant, selector) == effect]
    if extras is not None:
        matches = [
            selector for selector in matches if _signature_matches(variant, selector, extras)
        ]
    # Several reviewed source spellings can share one semantic group. Preserve
    # the exact choice per source row; the group points to equivalent meaning.
    if not matches or (extras is not None and len(matches) != 1):
        raise ValueError("Variant usage effect has no unambiguous reviewed rule reference")
    return matches[0]


def _fingerprint(publication: dict[str, Any]) -> str:
    snapshot = dict(publication["sourceSnapshot"])
    snapshot.pop("rulesDatabaseSha256", None)
    return hashlib.sha256(_canonical({
        **publication, "sourceSnapshot": snapshot,
    }).encode("utf-8")).hexdigest()


def stage_variant_usage(connection: sqlite3.Connection, publication: dict[str, Any]) -> None:
    """Resolve reviewed effect coordinates and insert typed rows in the export transaction."""
    _validate_publication(publication)
    if publication["formatVersion"] != 2 or not publication["variants"]:
        raise ValueError("Embedded variant usage requires a nonempty v2 read model")
    if set(publication["sourceSnapshot"]) != {
        "armyArchiveSha256", "armyDatabaseSha256", "exportPairSha256", "rulesDatabaseSha256",
    }:
        raise ValueError("Unsupported embedded variant source snapshot")
    for statement in _SCHEMA:
        connection.execute(statement)
    row_id = 0
    for group_id, group in enumerate(publication["variants"], 1):
        variant = group["variant"]
        meaning = _rule_variant(connection, variant["collectionId"], variant["recordId"])
        selector = _selector(meaning, variant["effect"])
        connection.execute(
            "INSERT INTO variant_usage_groups VALUES (" + ",".join("?" for _ in range(15)) + ")",
            (group_id, group["variantKey"], variant["collectionId"], variant["recordId"],
             *selector, *(group[key] for key in _COUNTS)),
        )
        for ordinal, row in enumerate(group["sourceRows"]):
            row_id += 1
            context = row["context"]
            shared = row.get("sharedOption", {})
            source_selector = _selector(meaning, variant["effect"], row["extras"])
            values = (
                row_id, group_id, ordinal, *(row.get(key) for key in _ROW_FIELDS),
                *(context.get(key) for key in _CONTEXT_FIELDS),
                *(shared.get(key) for key in ("compatible", "disabled", "raw")),
                *source_selector[1:4],
            )
            connection.execute(
                "INSERT INTO variant_usage_source_rows VALUES ("
                + ",".join("?" for _ in values) + ")", values,
            )
            connection.executemany(
                "INSERT INTO variant_usage_extras VALUES (?,?,?,?,?,?)",
                [(row_id, index, extra["position"], extra["extraId"],
                  extra["extraType"], extra["rawValue"])
                 for index, extra in enumerate(row["extras"])],
            )
    snapshot = publication["sourceSnapshot"]
    connection.execute(
        "INSERT INTO variant_usage_metadata VALUES (1,1,?,?,?,?,?,?)",
        (snapshot["armyArchiveSha256"], snapshot["armyDatabaseSha256"],
         snapshot["exportPairSha256"],
         len(publication["variants"]), row_id, _fingerprint(publication)),
    )
    actual = _read_publication(connection)
    if _fingerprint(actual) != _fingerprint(publication):
        raise ValueError("Variant usage lost source structure during relational export")


def _read_publication(connection: sqlite3.Connection) -> dict[str, Any]:
    metadata = connection.execute("SELECT * FROM variant_usage_metadata WHERE id=1").fetchone()
    if metadata is None or metadata[1] != 1:
        raise ValueError("Missing or unsupported embedded variant metadata")
    extras: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for extra_row in connection.execute(
        "SELECT row_id,position,extra_id,extra_type,raw_value "
        "FROM variant_usage_extras ORDER BY row_id,ordinal"
    ):
        extras[extra_row[0]].append(dict(zip(
            ("position", "extraId", "extraType", "rawValue"), extra_row[1:], strict=True,
        )))
    rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    total_rows = 0
    for stored in connection.execute(
        "SELECT * FROM variant_usage_source_rows ORDER BY group_id,ordinal"
    ):
        values = tuple(stored)
        row: dict[str, Any] = dict(zip(_ROW_FIELDS, values[3:17], strict=True))
        context: dict[str, Any] = dict(zip(_CONTEXT_FIELDS, values[17:25], strict=True))
        owner = row["ownerKind"]
        context["ownerKind"] = owner
        row["sourceKey"] = [row["catalog"], owner, row["occurrenceId"]]
        row["ownerPathKey"] = (
            [row["unitId"], row["optionId"]] if owner == "unit_option"
            else [row["armyId"], row["unitId"], row["groupId"], row["parentId"]]
        )
        if owner == "unit_option":
            shared = dict(zip(("compatible", "disabled", "raw"), values[25:28], strict=True))
            row["sharedOption"] = shared
            context = {key: context[key] for key in (
                "applicationArmyId", "logicalUnitId", "sourceUnitId", "payloadSha256", "ownerKind",
            )}
            context.update(optionId=row["optionId"], compatibility={
                "status": "source-only-unverified", "source": shared,
                "policy": "excluded from Army, Unit and profile/loadout totals",
            })
        row.update(context=context, extras=extras.pop(values[0], []))
        row["_reviewedSelector"] = values[28:]
        rows[values[1]].append(row)
        total_rows += 1
    if extras:
        raise ValueError("Embedded variant extras have no source row")
    groups = []
    for stored in connection.execute("SELECT * FROM variant_usage_groups ORDER BY variant_key"):
        group_id, key, collection, record, *rest = tuple(stored)
        selector, counts = tuple(rest[:5]), rest[5:]
        meaning = _rule_variant(connection, collection, record)
        effect = _effect(meaning, selector)
        source_rows = rows.pop(group_id, [])
        for source in source_rows:
            source_selector = (selector[0], *source.pop("_reviewedSelector"), selector[4])
            if _effect(meaning, source_selector) != effect or not _signature_matches(
                meaning, source_selector, source["extras"],
            ):
                raise ValueError("Variant source extras do not match their reviewed rule reference")
        groups.append({
            "variantKey": key,
            "variant": {"collectionId": collection, "recordId": record, "effect": effect},
            **dict(zip(_COUNTS, counts, strict=True)), "sourceRows": source_rows,
        })
    if rows or len(groups) != metadata[5] or total_rows != metadata[6]:
        raise ValueError("Embedded variant usage row/group inventory differs")
    publication = {
        "format": PUBLICATION_FORMAT, "formatVersion": 2, "scope": PUBLICATION_SCOPE,
        "sourceSnapshot": {
            "armyArchiveSha256": metadata[2], "armyDatabaseSha256": metadata[3],
            "exportPairSha256": metadata[4], "rulesDatabaseSha256": "0" * 64,
        },
        "variants": groups,
    }
    _validate_publication(publication)
    if _fingerprint(publication) != metadata[7]:
        raise ValueError("Embedded variant usage content fingerprint differs")
    return publication


def validate_variant_usage_snapshot(connection: sqlite3.Connection) -> None:
    """Validate the complete relational projection without raw files or runtime sidecars."""
    _read_publication(connection)


def read_variant_usage(connection: sqlite3.Connection, army: Path) -> dict[str, Any]:
    from .build_provenance import file_sha256
    from .database.publication import EXPORT_PAIR_SHA256_KEY
    from .database.schema import METADATA_TABLE

    publication = _read_publication(connection)
    snapshot = publication["sourceSnapshot"]
    if snapshot["armyDatabaseSha256"] != file_sha256(army):
        raise ValueError("Embedded variant usage does not match the selected Army database")
    with closing(sqlite3.connect(army.resolve().as_uri() + "?mode=ro", uri=True)) as selected:
        metadata = {key: json.loads(value) for key, value in selected.execute(
            f"SELECT key,value FROM {METADATA_TABLE} WHERE key IN (?,?)",
            ("_meta", EXPORT_PAIR_SHA256_KEY),
        )}
    if (
        metadata.get(EXPORT_PAIR_SHA256_KEY) != snapshot["exportPairSha256"]
        or metadata.get("_meta", {}).get("snapshotArchiveSha256") != snapshot["armyArchiveSha256"]
    ):
        raise ValueError("Embedded variant usage has a different Army source generation")
    return publication
