"""Read-only inventory of source Skill/Equipment variants for the 1.0 usage index.

The inventory is deliberately conservative: source extras are evidence, not
reviewed rule semantics. This module does not perform Unit usage aggregation.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from infinity_db.rules_database import RulesDatabase

CATEGORIES = ("skills", "equipment")
OWNERS = ("profile", "option", "unit_option")


def reviewed_extra_signature(
    items: list[tuple[int, int, str, str]],
    *,
    reviewed_values: set[tuple[int, str, str]],
    distance_allowed: bool,
    reviewed_combinations: set[tuple[tuple[int, str, str], ...]] | None = None,
) -> bool:
    """Review whole ordered signatures, including singleton compound TEXT extras."""
    signature = tuple((extra_id, kind, raw) for _pos, extra_id, kind, raw in items)
    if signature in (reviewed_combinations or set()):
        return True
    if len(items) != 1:
        return False
    _position, extra_id, extra_type, extra_name = items[0]
    return (
        (extra_id, extra_type, extra_name) in reviewed_values
        or (extra_type == "DISTANCE" and distance_allowed)
    )


def inventory_source_variants(
    application_path: Path, raw_path: Path, rules_path: Path
) -> dict[str, Any]:
    """Inventory pinned direct source occurrences and their review boundaries."""
    rules = RulesDatabase(rules_path)
    reviewed = {
        "skills": rules.catalog_source_variant_semantics("skill"),
        "equipment": rules.catalog_source_variant_semantics("equipment"),
    }
    distance_parameters = rules.skill_parameter_semantics()
    numeric_mods = rules.skill_numeric_mod_semantics()
    reviewed_extras = {
        "skills": rules.skill_reviewed_extra_semantics(),
        "equipment": rules.equipment_reviewed_extra_semantics(),
    }
    # Army Skill 254 represents a target-side PH override on Equipment GizmoKit.
    # Retain its source catalog while keeping only one canonical game-rule owner.
    cross_catalog = rules.skill_source_equipment_overrides()
    for source_id, semantics in cross_catalog.items():
        if source_id in reviewed_extras["skills"]:
            raise ValueError(f"Conflicting Skill source override: {source_id}")
        reviewed_extras["skills"][source_id] = semantics
    reviewed_combinations = {
        "skills": rules.skill_reviewed_combination_semantics(),
        "equipment": rules.equipment_reviewed_combination_semantics(),
    }
    report: dict[str, Any] = {"catalogs": {}}

    application_uri = application_path.resolve().as_uri() + "?mode=ro"
    raw_uri = raw_path.resolve().as_uri() + "?mode=ro"
    with (
        sqlite3.connect(application_uri, uri=True) as application,
        sqlite3.connect(raw_uri, uri=True) as raw,
    ):
        for catalog in CATEGORIES:
            sources = {
                int(source_id): {
                    "applicationId": int(application_id),
                    "name": str(name),
                }
                for source_id, application_id, name in application.execute(
                    "SELECT source_item_id, application_item_id, source_name "
                    "FROM application_catalog_sources WHERE catalog = ?",
                    (catalog,),
                )
            }
            slugs = {
                int(application_id): str(slug)
                for application_id, slug in application.execute(
                    "SELECT application_id, slug FROM application_domain_slugs "
                    "WHERE domain = ? AND status = 'resolved'",
                    (catalog,),
                )
            }
            records: dict[int, dict[str, Any]] = {}
            suffix = "skill" if catalog == "skills" else catalog
            for owner in OWNERS:
                rows = raw.execute(
                    f"SELECT o.item_id, o.occurrence_id, o.raw, e.position, "
                    "x.id, x.type, x.name "
                    f"FROM {owner}_{catalog} AS o "
                    f"LEFT JOIN {owner}_{suffix}_extras AS e "
                    "ON e.occurrence_id = o.occurrence_id "
                    "LEFT JOIN extras AS x ON x.id = e.extra_id "
                    "ORDER BY o.item_id, o.occurrence_id, e.position"
                )
                for source_id, occurrence_id, raw_value, pos, extra_id, kind, name in rows:
                    source_id = int(source_id)
                    entry = records.setdefault(
                        source_id, {"occurrences": {}, "extraTypes": set(), "rawValues": set()}
                    )
                    key = (owner, int(occurrence_id))
                    occurrence = entry["occurrences"].setdefault(key, [])
                    if extra_id is not None:
                        occurrence.append((int(pos), int(extra_id), str(kind), str(name)))
                        entry["extraTypes"].add(str(kind))
                    if raw_value is not None and str(raw_value).strip():
                        entry["rawValues"].add(str(raw_value))

            rows = []
            status_counts: Counter[str] = Counter()
            for source_id in sorted(set(sources) | set(records)):
                source = sources.get(source_id)
                record = records.get(source_id)
                extras = record["occurrences"] if record else {}
                extra_types = sorted(record["extraTypes"]) if record else []
                raw_values = sorted(record["rawValues"]) if record else []
                source_variant = reviewed[catalog].get(source_id)
                slug = slugs.get(source["applicationId"]) if source else None
                distance = (
                    distance_parameters.get(source_id)
                    or (distance_parameters.get(slug) if slug else None)
                ) if catalog == "skills" else None
                numeric = (
                    numeric_mods.get(source_id)
                    or (numeric_mods.get(slug) if slug else None)
                ) if catalog == "skills" else None
                typed = (
                    reviewed_extras[catalog].get(source_id)
                    or (reviewed_extras[catalog].get(slug) if slug else None)
                )
                reviewed_values = {
                    (item["extra_id"], item["extra_type"], item["raw_value"])
                    for semantics in (numeric, typed) if semantics is not None
                    for item in semantics["extra_values"]
                }
                combination_registry = reviewed_combinations[catalog]
                combinations = (
                    combination_registry.get(source_id)
                    or (combination_registry.get(slug) if slug else None)
                )
                exact_combinations = {
                    tuple(
                        (entry["extra_id"], entry["extra_type"], entry["raw_value"])
                        for entry in combination["extras"]
                    )
                    for combination in (combinations or [])
                }

                def reviewed_signature(
                    items: list[tuple[int, int, str, str]],
                    allowed_values: set[tuple[int, str, str]] = reviewed_values,
                    distance_allowed: bool = distance is not None,
                    reviewed_combinations: set[tuple[tuple[int, str, str], ...]] = (
                        exact_combinations
                    ),
                ) -> bool:
                    return reviewed_extra_signature(
                        items,
                        reviewed_values=allowed_values,
                        distance_allowed=distance_allowed,
                        reviewed_combinations=reviewed_combinations,
                    )

                unresolved = (
                    bool(raw_values)
                    or any(not reviewed_signature(items) for items in extras.values() if items)
                )
                if source is None:
                    status = "not-in-published-catalog"
                elif not extras:
                    status = "catalog-only"
                elif extra_types or raw_values:
                    if not unresolved and typed is not None:
                        status = "reviewed-extra-parameter"
                    elif not unresolved and combinations is not None:
                        status = "reviewed-combination-parameter"
                    elif not unresolved and numeric is not None:
                        status = "reviewed-numeric-parameter"
                    elif not unresolved and distance is not None:
                        status = "reviewed-distance-parameter"
                    else:
                        status = "unresolved-occurrence-parameter"
                elif source_variant is not None:
                    status = "reviewed-exact-source"
                else:
                    status = "family-only"
                status_counts[status] += 1
                rows.append(
                    {
                        "id": source_id,
                        "name": source["name"] if source else None,
                        "applicationId": source["applicationId"] if source else None,
                        "status": status,
                        "reviewedVariant": source_variant,
                        "reviewedDistance": distance,
                        "reviewedNumericMod": numeric,
                        "reviewedExtra": typed,
                        "reviewedCombinations": combinations,
                        "occurrences": len(extras),
                        "extraTypes": extra_types,
                        "extraSignatures": [
                            {
                                "extras": [list(v[1:]) for v in signature],
                                "reviewed": reviewed_signature(list(signature)),
                                "count": sum(
                                    tuple(items) == signature
                                    for items in extras.values()
                                ),
                            }
                            for signature in sorted(
                                {tuple(items) for items in extras.values() if items}
                            )
                        ],
                        "rawValues": raw_values[:10],
                        "rawValueDistinctCount": len(raw_values),
                    }
                )
            report["catalogs"][catalog] = {
                "summary": {
                    "publishedSourceIds": len(sources),
                    "sourceIdsWithDirectRows": len(records),
                    "directSourceRows": sum(len(e["occurrences"]) for e in records.values()),
                    "reviewedExactSourceIds": len(set(reviewed[catalog]) & set(sources)),
                    "statuses": dict(sorted(status_counts.items())),
                    "extraTypes": dict(sorted(Counter(
                        value for entry in records.values() for value in entry["extraTypes"]
                    ).items())),
                },
                "items": rows,
            }
    return report


def source_extra_owner_context(
    raw_path: Path, *, catalog: str, source_id: int, extra_id: int
) -> list[dict[str, Any]]:
    """Find exact direct source owners; do not infer logical or cross-Army Unit use."""
    if catalog not in CATEGORIES or source_id <= 0 or extra_id <= 0:
        raise ValueError("Owner lookup requires a valid source catalog and positive IDs")
    suffix = "skill" if catalog == "skills" else "equipment"
    results: list[dict[str, Any]] = []
    uri = raw_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as raw:
        raw.row_factory = sqlite3.Row
        for owner in OWNERS:
            parent_table = {
                "profile": "profiles",
                "option": "loadout_options",
                "unit_option": "unit_options",
            }[owner]
            parent_keys = (
                ("unit_id", "option_id") if owner == "unit_option"
                else ("army_id", "unit_id", "group_id",
                      "profile_id" if owner == "profile" else "option_id")
            )
            join = " AND ".join(f"p.{key} = o.{key}" for key in parent_keys)
            army_join = (
                "LEFT JOIN army_lists AS a ON a.id = o.army_id"
                if owner != "unit_option" else ""
            )
            army_columns = (
                "o.army_id AS army_id, a.name AS army_name, "
                "a.source_file AS army_source_file, o.group_id AS group_id, "
                if owner != "unit_option"
                else "NULL AS army_id, NULL AS army_name, "
                     "NULL AS army_source_file, NULL AS group_id, "
            )
            key = "profile_id" if owner == "profile" else "option_id"
            query = (
                f"SELECT o.occurrence_id, o.unit_id, u.name AS unit_name, "
                f"u.slug AS unit_slug, {army_columns} "
                f"o.{key} AS parent_id, p.name AS parent_name, "
                f"o.position AS source_position, o.raw AS source_raw, "
                f"e.position AS extra_position, x.id AS extra_id, "
                f"x.type AS extra_type, x.name AS extra_raw "
                f"FROM {owner}_{catalog} AS o "
                f"JOIN {owner}_{suffix}_extras AS e "
                "ON e.occurrence_id = o.occurrence_id "
                "JOIN extras AS x ON x.id = e.extra_id "
                "JOIN units AS u ON u.id = o.unit_id "
                f"JOIN {parent_table} AS p ON {join} "
                f"{army_join} "
                "WHERE o.item_id = ? AND e.extra_id = ? "
                "ORDER BY o.unit_id, o.occurrence_id, e.position"
            )
            for row in raw.execute(query, (source_id, extra_id)):
                results.append({"owner": owner, **dict(row)})
    return sorted(results, key=lambda r: (
        r["owner"], r["unit_id"], r["occurrence_id"], r["extra_position"]
    ))


def select_source_variants(
    report: dict[str, Any], catalog: str, source_ids: list[int] | None = None
) -> dict[str, Any]:
    """Select exact source IDs without relabeling full-catalog summary counts."""
    if catalog not in CATEGORIES:
        raise ValueError(f"unsupported source catalog: {catalog}")
    source = report["catalogs"][catalog]
    items = source["items"]
    if source_ids:
        selected = set(source_ids)
        available = {item["id"] for item in items}
        missing = sorted(selected - available)
        if missing:
            raise ValueError(f"source IDs absent from {catalog}: {missing}")
        items = [item for item in items if item["id"] in selected]
    return {
        "catalog": catalog,
        "fullCatalogSummary": source["summary"],
        "selectedSourceIds": [item["id"] for item in items],
        "items": items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument("--raw", type=Path, default=Path("data/generated/infinity.raw.db"))
    parser.add_argument("--rules", type=Path, default=Path("data/generated/rules.db"))
    parser.add_argument("--catalog", choices=CATEGORIES, help="limit output to one source catalog")
    parser.add_argument(
        "--source-id", type=int, action="append", default=[],
        help="select an exact source ID (repeatable; requires --catalog)",
    )
    parser.add_argument(
        "--owner-extra-id", type=int,
        help="show direct source owners of an exact extra; requires one source ID and catalog",
    )
    args = parser.parse_args()
    if args.source_id and not args.catalog:
        parser.error("--source-id requires --catalog")
    if args.owner_extra_id is not None and (
        not args.catalog or len(args.source_id) != 1 or args.owner_extra_id <= 0
    ):
        parser.error("--owner-extra-id requires one --source-id, --catalog and positive ID")
    report = inventory_source_variants(args.application, args.raw, args.rules)
    if args.catalog:
        try:
            report = select_source_variants(report, args.catalog, args.source_id)
        except ValueError as exc:
            parser.error(str(exc))
    if args.owner_extra_id is not None:
        report["occurrenceOwners"] = source_extra_owner_context(
            args.raw, catalog=args.catalog,
            source_id=args.source_id[0], extra_id=args.owner_extra_id,
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
