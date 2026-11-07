"""Audit delivery-evidence gaps for currently published deployed-object profiles.

A same-source Army catalog alias is a search lead, NEVER a delivery edge.
Only entries from validated delivery reviews authorize runtime relationships.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_reference import project_deployed_references
from tools.audit_deployed_object_inventory import audit_inventory

ROOT = Path(__file__).resolve().parents[1]


def audit_delivery_coverage(
    army_db: Path,
    curated_source: Path,
    delivery_reviews: Path,
    candidate_reviews: Path,
) -> dict[str, Any]:
    inventory = audit_inventory(army_db, curated_source, delivery_reviews, candidate_reviews)
    publication = project_deployed_references(inventory)
    rows: list[dict[str, Any]] = []
    with sqlite3.connect(f"{army_db.resolve().as_uri()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        for obj in publication["objects"]:
            profile = obj["sourceProfile"]
            aliases: list[dict[str, Any]] = []
            if profile is not None:
                domain = "weapons" if profile["catalog"] == "weapon" else "equipment"
                matches = db.execute(
                    "SELECT d.slug, s.application_item_id "
                    "FROM application_domain_slugs AS d "
                    "JOIN application_catalog_sources AS s "
                    "ON s.catalog = d.domain AND s.application_item_id = d.application_id "
                    "WHERE d.domain = ? AND s.source_item_id = ? "
                    "ORDER BY d.slug, s.application_item_id",
                    (domain, profile["sourceId"]),
                )
                aliases = [
                    {"recordId": f"{profile['catalog']}:{row['slug']}",
                     "applicationId": row["application_item_id"]}
                    for row in matches
                ]
            rows.append({
                "objectId": obj["id"],
                "name": obj["name"],
                "sourceProfile": (
                    {"catalog": profile["catalog"], "sourceId": profile["sourceId"],
                     "mode": profile["mode"]} if profile is not None else None
                ),
                "originRuleId": obj["originRuleId"],
                "reviewedDeliverySources": [
                    {"recordId": edge["recordId"], "method": edge["method"]}
                    for edge in obj["deliverySources"]
                ],
                "sameSourceCatalogCandidates": aliases,
            })
    pending = [row for row in rows if not row["reviewedDeliverySources"]]
    return {
        "scope": "delivery-review-queue-not-inferred-object-ownership",
        "armyDatabaseSha256": inventory["armyDatabaseSha256"],
        "curatedSourceSha256": inventory["curatedSourceSha256"],
        "reviewedObjectCount": len(rows),
        "withReviewedDelivery": len(rows) - len(pending),
        "withoutReviewedDelivery": pending,
        "objects": rows,
        "unresolvedDeliveryOrigins": publication["unresolvedDeliveries"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=ROOT / "data/generated/infinity.db")
    parser.add_argument(
        "--curated-source", type=Path, default=ROOT / "data/curated/rules/n5-core-v5.3.json",
    )
    parser.add_argument(
        "--delivery-reviews", type=Path,
        default=ROOT / "config/validation/deployed-object-delivery-reviews.json",
    )
    parser.add_argument(
        "--candidate-reviews", type=Path,
        default=ROOT / "config/validation/deployed-object-candidate-reviews.json",
    )
    parser.add_argument("--json", action="store_true", help="Print full review queue")
    args = parser.parse_args()
    report = audit_delivery_coverage(
        args.army_db, args.curated_source, args.delivery_reviews, args.candidate_reviews,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"Reviewed objects: {report['reviewedObjectCount']}; "
            f"with reviewed delivery: {report['withReviewedDelivery']}; "
            f"without: {len(report['withoutReviewedDelivery'])}"
        )
        for item in report["withoutReviewedDelivery"]:
            candidate_ids = ", ".join(
                row["recordId"] for row in item["sameSourceCatalogCandidates"]
            )
            print(f"  {item['name']} [{item['objectId']}]: candidate aliases: "
                  f"{candidate_ids or '(none)'}")
        print(f"Unresolved reviewed delivery origins: {len(report['unresolvedDeliveryOrigins'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
