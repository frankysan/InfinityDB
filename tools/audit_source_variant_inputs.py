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
) -> bool:
    """Accept only single extras; reviewed values do not certify combinations."""
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
    reviewed_extras = rules.skill_reviewed_extra_semantics()
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
                    reviewed_extras.get(source_id)
                    or (reviewed_extras.get(slug) if slug else None)
                ) if catalog == "skills" else None
                reviewed_values = {
                    (item["extra_id"], item["extra_type"], item["raw_value"])
                    for semantics in (numeric, typed) if semantics is not None
                    for item in semantics["extra_values"]
                }

                def reviewed_signature(
                    items: list[tuple[int, int, str, str]],
                    allowed_values: set[tuple[int, str, str]] = reviewed_values,
                    distance_allowed: bool = distance is not None,
                ) -> bool:
                    return reviewed_extra_signature(
                        items,
                        reviewed_values=allowed_values,
                        distance_allowed=distance_allowed,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument("--raw", type=Path, default=Path("data/generated/infinity.raw.db"))
    parser.add_argument("--rules", type=Path, default=Path("data/generated/rules.db"))
    args = parser.parse_args()
    print(json.dumps(inventory_source_variants(args.application, args.raw, args.rules), indent=2))


if __name__ == "__main__":
    main()
