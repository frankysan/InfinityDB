"""Read-only, source-bound cross-Army Skill/Equipment variant usage projection.

The projection is not a roster builder. All source rows remain distinguishable;
only whole reviewed signatures enter exact-variant counts. Includes and Peripheral
relationships are provenance, never synthetic direct Skill/Equipment usage.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import _variant_semantics

CATALOGS = ("skills", "equipment")
OWNERS = ("profile", "option", "unit_option")
OWNER_FIELDS = {
    "profile": ("army_id", "unit_id", "group_id", "profile_id"),
    "option": ("army_id", "unit_id", "group_id", "option_id"),
    "unit_option": ("unit_id", "option_id"),
}
PAYLOADS = {
    "profile": ("profile_payload_occurrences", "profile_payloads", "profile_payload_skills",
                "profile_payload_equipment"),
    "option": ("loadout_payload_occurrences", "loadout_payloads", "loadout_payload_skills",
               "loadout_payload_equipment"),
}


def _connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"Missing variant usage database: {path}")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def _snapshot(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT value FROM __infinity_metadata WHERE key = '_meta'"
    ).fetchone()
    try:
        metadata = json.loads(row[0]) if row is not None else None
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid Army source provenance") from exc
    value = metadata.get("snapshotArchiveSha256") if isinstance(metadata, dict) else None
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError("Missing pinned Army snapshot hash")
    return value


def _source_mapping(
    application: sqlite3.Connection, rules: sqlite3.Connection,
) -> dict[tuple[str, int], dict[str, Any]]:
    rows = rules.execute(
        "SELECT l.entity, l.external_id, r.id, r.collection_id, r.variant_json "
        "FROM record_army_links AS l JOIN records AS r "
        "ON r.collection_id = l.collection_id AND r.id = l.record_id "
        "JOIN collections AS c ON c.id = r.collection_id "
        "WHERE c.status = 'current' AND r.composition_role = 'definition' "
        "AND r.kind IN ('skill', 'equipment') "
        "AND l.entity IN ('skill', 'equipment') AND l.external_id IS NOT NULL "
        "ORDER BY r.id, l.external_id"
    ).fetchall()
    linked: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        variant = _variant_semantics(row["variant_json"]) or {"inheritance": "family"}
        linked[(row["entity"], row["external_id"])][row["id"]] = {
            "recordId": row["id"], "collectionId": row["collection_id"],
            "variant": variant,
        }
    mapping = {}
    for source in application.execute(
        "SELECT s.catalog, s.source_item_id, s.application_item_id, d.slug "
        "FROM application_catalog_sources AS s "
        "LEFT JOIN application_domain_slugs AS d "
        "ON d.domain = s.catalog AND d.application_id = s.application_item_id "
        "AND d.status = 'resolved' WHERE s.catalog IN ('skills','equipment') "
        "ORDER BY s.catalog, s.source_item_id"
    ):
        entity = "skill" if source["catalog"] == "skills" else "equipment"
        direct = linked.get((entity, str(source["source_item_id"])), {})
        fallback = linked.get((entity, source["slug"]), {}) if source["slug"] else {}
        candidates = direct if direct else fallback
        key = (source["catalog"], source["source_item_id"])
        if key in mapping:
            # The source catalog ID must not pick an arbitrary application
            # identity when several canonical catalog entries claim it.
            mapping[key] = {
                "applicationItemId": None, "slug": None, "rules": None,
                "ambiguous": True, "duplicateSourceMapping": True,
            }
            continue
        mapping[key] = {
            "applicationItemId": source["application_item_id"],
            "slug": source["slug"],
            "rules": next(iter(candidates.values())) if len(candidates) == 1 else None,
            "ambiguous": len(candidates) > 1,
        }
    return mapping


def _resolve_effect(
    variant: dict[str, Any],
    extras: list[dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    """Only whole source-reviewed extra signatures can enter typed usage."""
    if not extras:
        source_variant = variant.get("source_variant")
        return ("exact", {"sourceVariant": source_variant}) if source_variant else (
            "family", None
        )
    signature = [(x["extraId"], x["extraType"], x["rawValue"]) for x in extras]
    for combination in variant.get("occurrence_combinations", []):
        if signature == [
            (x["extra_id"], x["extra_type"], x["raw_value"])
            for x in combination["extras"]
        ]:
            return "exact", {
                "sourceVariant": variant.get("source_variant"),
                "combinationEffects": combination["effects"],
            }
    if len(signature) != 1:
        return "unresolved", None
    for parameter in variant.get("occurrence_parameters", []):
        if parameter["kind"] == "distance":
            if extras[0]["extraType"] == "DISTANCE":
                return "exact", {
                    "sourceVariant": variant.get("source_variant"),
                    "parameter": parameter,
                    "rawDistance": extras[0]["rawValue"],
                }
            continue
        for entry in parameter.get("extra_values", []):
            if signature[0] == (
                entry["extra_id"], entry["extra_type"], entry["raw_value"]
            ):
                return "exact", {
                    "sourceVariant": variant.get("source_variant"),
                    "parameterKind": parameter["kind"],
                    "parameter": entry,
                }
    return "unresolved", None


def _published_extras_match(
    application: sqlite3.Connection, row: dict[str, Any], owner: str,
    payload_id: int | None = None,
) -> bool:
    suffix = "skill" if row["catalog"] == "skills" else "equipment"
    table = (
        f"unit_option_{suffix}_extras" if owner == "unit_option"
        else f"{'profile' if owner == 'profile' else 'loadout'}_payload_{suffix}_extras"
    )
    if owner == "unit_option":
        query = (
            f"SELECT e.position, x.id, x.type, x.name FROM {table} AS e "
            "JOIN extras AS x ON x.id = e.extra_id "
            "WHERE e.occurrence_id = ? ORDER BY e.position"
        )
        values = (row["occurrenceId"],)
    else:
        parent_key = "profile_payload_id" if owner == "profile" else "loadout_payload_id"
        query = (
            f"SELECT e.position, x.id, x.type, x.name FROM {table} AS e "
            "JOIN extras AS x ON x.id = e.extra_id "
            f"WHERE e.{parent_key} = ? AND e.occurrence_position = ? "
            "ORDER BY e.position"
        )
        values = (payload_id, row["position"])
    published = [
        (item["position"], item["id"], item["type"], item["name"])
        for item in application.execute(query, values)
    ]
    raw = [
        (item["position"], item["extraId"], item["extraType"], item["rawValue"])
        for item in row["extras"]
    ]
    return published == raw


def _direct_context(
    application: sqlite3.Connection, row: dict[str, Any], owner: str,
) -> dict[str, Any] | None:
    """Validate the actual published source occurrence and its payload position."""
    if owner == "unit_option":
        matches = application.execute(
            f"SELECT item_id, position, display_order, quantity, raw FROM "
            f"unit_option_{row['catalog']} WHERE occurrence_id = ? "
            "AND unit_id = ? AND option_id = ?",
            (row["occurrenceId"], row["unitId"], row["optionId"]),
        ).fetchall()
        if len(matches) != 1:
            return None
        match = matches[0]
        if any(match[field] != row[key] for field, key in (
            ("item_id", "sourceId"), ("position", "position"),
            ("display_order", "displayOrder"), ("quantity", "quantity"),
            ("raw", "raw"),
        )) or not _published_extras_match(application, row, owner):
            return None
        # Shared Unit options have no globally valid Army or profile attribution.
        return {"ownerKind": owner, "sourceUnitId": row["unitId"],
                "optionId": row["optionId"], "applicationArmyId": None,
                "logicalUnitId": None, "payloadSha256": None}
    (occurrence_table, payload_table, skill_table, equipment_table) = PAYLOADS[owner]
    table = skill_table if row["catalog"] == "skills" else equipment_table
    id_field = "profile_id" if owner == "profile" else "option_id"
    payload_field = "profile_payload_id" if owner == "profile" else "loadout_payload_id"
    result = application.execute(
        f"SELECT o.{payload_field} AS payload_id, p.payload_sha256, "
        "o.position AS context_position, t.item_id, t.display_order, "
        "t.quantity, t.raw, "
        "a.application_army_id, l.logical_unit_id "
        f"FROM {occurrence_table} AS o "
        f"JOIN {table} AS t ON t.{payload_field} = o.{payload_field} "
        f"JOIN {payload_table} AS p ON p.id = o.{payload_field} "
        "JOIN application_army_sources AS a ON a.source_army_id = o.army_id "
        "JOIN army_units AS u ON u.army_id = o.army_id AND u.unit_id = o.unit_id "
        "JOIN logical_unit_sources AS l ON l.source_unit_id = o.unit_id "
        f"WHERE o.army_id = ? AND o.unit_id = ? AND o.group_id = ? "
        f"AND o.{id_field} = ? AND t.position = ?",
        (row["armyId"], row["unitId"], row["groupId"], row["parentId"],
         row["position"]),
    ).fetchall()
    # Do not silently pick one published owner if the path joins ambiguously.
    if len(result) != 1:
        return None
    match = result[0]
    if (match["item_id"] != row["sourceId"]
            or match["display_order"] != row["displayOrder"]
            or match["quantity"] != row["quantity"]
            or match["raw"] != row["raw"]
            or not _published_extras_match(
                application, row, owner, match["payload_id"]
            )):
        return None
    return {
        "ownerKind": owner,
        "applicationArmyId": match["application_army_id"],
        "logicalUnitId": match["logical_unit_id"],
        "sourceArmyId": row["armyId"], "sourceUnitId": row["unitId"],
        "groupId": row["groupId"], "parentId": row["parentId"],
        "payloadSha256": match["payload_sha256"],
        "contextPosition": match["context_position"],
    }


def _source_rows(raw: sqlite3.Connection, catalog: str, owner: str) -> list[dict[str, Any]]:
    fields = OWNER_FIELDS[owner]
    projection = ", ".join(fields)
    suffix = "skill" if catalog == "skills" else "equipment"
    rows = raw.execute(
        f"SELECT occurrence_id, item_id, position, display_order, quantity, raw, "
        f"{projection} FROM {owner}_{catalog} ORDER BY occurrence_id"
    ).fetchall()
    extras: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for extra in raw.execute(
        f"SELECT e.occurrence_id, e.position, x.id, x.type, x.name "
        f"FROM {owner}_{suffix}_extras AS e JOIN extras AS x ON x.id = e.extra_id "
        "ORDER BY e.occurrence_id, e.position"
    ):
        extras[extra["occurrence_id"]].append({
            "position": extra["position"], "extraId": extra["id"],
            "extraType": extra["type"], "rawValue": extra["name"],
        })
    result = []
    seen_keys: set[tuple[str, str, int]] = set()
    for item in rows:
        source_key = (catalog, owner, item["occurrence_id"])
        if item["occurrence_id"] is None:
            raise ValueError(f"Missing variant source-row identity: {catalog}/{owner}")
        if source_key in seen_keys:
            raise ValueError(f"Duplicate variant source-row key: {source_key!r}")
        seen_keys.add(source_key)
        owner_path = tuple(item[field] for field in fields)
        if any(value is None for value in owner_path):
            raise ValueError(f"Incomplete variant source owner path: {source_key!r}")
        parent = dict(zip(fields, owner_path, strict=True))
        result.append({
            "catalog": catalog, "ownerKind": owner,
            "sourceKey": list(source_key), "ownerPathKey": list(owner_path),
            "occurrenceId": item["occurrence_id"], "sourceId": item["item_id"],
            "position": item["position"], "displayOrder": item["display_order"],
            "quantity": item["quantity"], "raw": item["raw"],
            "armyId": parent.get("army_id"), "unitId": parent["unit_id"],
            "groupId": parent.get("group_id"),
            "parentId": parent.get("profile_id", parent.get("option_id")),
            "optionId": parent.get("option_id"),
            "extras": extras.pop(item["occurrence_id"], []),
        })
    if extras:
        raise ValueError(f"Orphan source extras: {catalog}/{owner}")
    return result


def _assert_complete_owner_rows(
    application: sqlite3.Connection, catalog: str, owner: str,
    source_count: int,
) -> None:
    """A truncated raw archive must not silently remove published usage."""
    if owner == "unit_option":
        statement = f"SELECT COUNT(*) FROM unit_option_{catalog}"
    else:
        (occurrence_table, _payload_table, skill_table, equipment_table) = PAYLOADS[owner]
        table = skill_table if catalog == "skills" else equipment_table
        payload_key = "profile_payload_id" if owner == "profile" else "loadout_payload_id"
        statement = (
            f"SELECT COUNT(*) FROM {occurrence_table} AS o "
            f"JOIN {table} AS t ON t.{payload_key} = o.{payload_key}"
        )
    published_count = application.execute(statement).fetchone()[0]
    if source_count != published_count:
        raise ValueError(
            f"Variant raw/published relationship count differs for {catalog}/{owner}: "
            f"{source_count} != {published_count}"
        )


def _include_peripheral_provenance(
    application: sqlite3.Connection,
) -> dict[str, Any]:
    """Expose only relationship edges, never copied Skill/Equipment memberships."""
    includes: list[dict[str, Any]] = []
    for table in (
        "profile_occurrence_includes", "loadout_occurrence_includes",
        "unit_option_include_targets",
    ):
        for row in application.execute(f"SELECT * FROM {table}"):
            includes.append({"kind": table, "owner": dict(row)})
    includes.sort(key=lambda item: _canonical(item))
    peripheral: list[dict[str, Any]] = []
    for row in application.execute(
        "SELECT a.id AS access_id, a.source_id, a.controller_kind, "
        "a.army_id, a.unit_id, a.group_id, a.parent_id, "
        "t.target_logical_unit_id "
        "FROM application_peripheral_controller_access AS a "
        "JOIN application_peripheral_controller_targets AS t ON t.access_id = a.id "
        "ORDER BY a.id, t.target_logical_unit_id"
    ):
        peripheral.append(dict(row))
    return {"includes": includes, "peripheralControllerEdges": peripheral,
            "policy": "context-only; never counted as direct rule ownership"}


def build_variant_usage_projection(
    application_path: Path,
    raw_path: Path,
    rules_path: Path,
    publication_path: Path,
) -> dict[str, Any]:
    """Create an immutable in-memory projection from one verified release pair.

    No writes, and no URL/API exposure. Unresolved inputs are diagnostic-only.
    """
    verified = load_deployed_object_publication(publication_path, application_path,
                                                rules_path)
    if verified is None:
        raise ValueError("Variant usage requires a matched deployed-object publication")
    with (
        closing(_connect(application_path)) as application,
        closing(_connect(raw_path)) as raw,
        closing(_connect(rules_path)) as rules,
    ):
        snapshot = _snapshot(application)
        if _snapshot(raw) != snapshot:
            raise ValueError("Variant usage Army raw archive does not match application snapshot")
        mapping = _source_mapping(application, rules)
        variants: dict[str, dict[str, Any]] = {}
        diagnostics: dict[str, int] = defaultdict(int)
        unresolved: list[dict[str, Any]] = []
        family: dict[str, set[int]] = defaultdict(set)
        for catalog in CATALOGS:
            for owner in OWNERS:
                source_rows = _source_rows(raw, catalog, owner)
                _assert_complete_owner_rows(
                    application, catalog, owner, len(source_rows)
                )
                for row in source_rows:
                    source = mapping.get((catalog, row["sourceId"]))
                    if source is not None and source.get("duplicateSourceMapping"):
                        reason = "ambiguous-source-catalog"
                    elif source is None or source["rules"] is None:
                        reason = "unmapped-or-ambiguous-rule"
                    else:
                        reason = ""
                    context = _direct_context(application, row, owner)
                    if context is None:
                        raise ValueError(
                            f"Variant source row has no identical published owner: "
                            f"{catalog}/{owner}/{row['occurrenceId']}"
                        )
                    if source is not None and source["rules"] is not None:
                        state, effect = _resolve_effect(source["rules"]["variant"],
                                                        row["extras"])
                        if row["raw"] not in (None, ""):
                            state, effect = "unresolved", None
                        if state == "unresolved":
                            reason = "unreviewed-signature"
                        elif state == "family":
                            if context["logicalUnitId"] is not None:
                                family[source["rules"]["recordId"]].add(
                                    context["logicalUnitId"]
                                )
                            continue
                        else:
                            assert effect is not None
                            variant = {
                                "recordId": source["rules"]["recordId"],
                                "collectionId": source["rules"]["collectionId"],
                                "effect": effect,
                            }
                            key = _canonical(variant)
                            entry = variants.setdefault(key, {
                                "variant": variant, "sourceRows": [],
                            })
                            entry["sourceRows"].append({
                                **row, "context": context,
                                "applicationItemId": source["applicationItemId"],
                            })
                            continue
                    diagnostics[reason] += 1
                    unresolved.append({
                        "reason": reason, "catalog": catalog,
                        "ownerKind": owner, "occurrenceId": row["occurrenceId"],
                        "sourceId": row["sourceId"], "extras": row["extras"],
                    })
        ordered = []
        for key, entry in sorted(variants.items()):
            rows = entry["sourceRows"]
            rows.sort(key=lambda row: (
                row["context"]["applicationArmyId"] or -1,
                row["context"]["logicalUnitId"] or -1,
                row["armyId"] or -1, row["unitId"], OWNERS.index(row["ownerKind"]),
                row["groupId"] or -1, row["context"].get("contextPosition") or -1,
                row["displayOrder"] or -1, row["position"], row["occurrenceId"],
            ))
            direct = [r for r in rows if r["context"]["applicationArmyId"] is not None]
            unit_keys = {r["context"]["logicalUnitId"] for r in direct}
            army_keys = {(r["context"]["applicationArmyId"],
                          r["context"]["logicalUnitId"]) for r in direct}
            context_keys = {
                (r["context"]["applicationArmyId"], r["context"]["logicalUnitId"],
                 r["ownerKind"], r["context"]["payloadSha256"])
                for r in direct
            }
            ordered.append({
                "variantKey": key, "variant": entry["variant"],
                "uniqueUnits": len(unit_keys),
                "uniqueArmyUnits": len(army_keys),
                "distinctContexts": len(context_keys),
                "sourceRelationshipRows": len(rows),
                "sourceRows": rows,
            })
        unresolved.sort(key=lambda x: (
            x["catalog"], OWNERS.index(x["ownerKind"]), x["occurrenceId"]
        ))
        return {
            "format": "infinitydb-rule-variant-usage", "formatVersion": 1,
            "scope": "read-only-candidate-not-published",
            "sourceSnapshot": {
                "armyArchiveSha256": snapshot,
                "armyDatabaseSha256": _digest(application_path),
                "rawDatabaseSha256": _digest(raw_path),
                "rulesDatabaseSha256": _digest(rules_path),
            },
            "variants": ordered,
            "familyOnlyUniqueUnitCounts": {
                name: len(units) for name, units in sorted(family.items())
            },
            "diagnosticCounts": dict(sorted(diagnostics.items())),
            "unresolvedSourceRows": unresolved,
            "relationships": _include_peripheral_provenance(application),
        }
