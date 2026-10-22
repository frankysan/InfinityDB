"""Read-only candidate discovery in detailed curated Weapon/Equipment rules.

The deployed-object inventory currently reviews summary-keyword candidates.
This companion audit also scans structured Requirements, Effects,
Restrictions, Clarifications and source notes for mentions absent from the
summary scan. Mentions are NOT object identities or delivery assertions.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tools.audit_deployed_object_inventory import audit_inventory

_TERMS = re.compile(r"\b(?:deployables?|tokens?|scenery elements?)\b", re.IGNORECASE)
_FIELDS = ("requirements", "effects", "restrictions", "clarifications", "sourceNotes")


def detail_candidates(
    curated: dict[str, Any],
    *,
    reviewed_ids: set[str],
) -> list[dict[str, Any]]:
    """Find Weapon/Equipment definitions mentioning deployment in detailed facts."""
    found: list[dict[str, Any]] = []
    for record in curated["records"]:
        if record.get("kind") not in {"weapon", "equipment"}:
            continue
        if (record.get("composition") or {}).get("role") != "definition":
            continue
        summary = record.get("summary", "")
        if not isinstance(summary, str):
            continue
        facts = record.get("facts") or {}
        if not isinstance(facts, dict):
            continue
        fields: dict[str, list[str]] = {}
        for name in _FIELDS:
            values = facts.get(name, [])
            if not isinstance(values, list):
                continue
            matches = [
                value for value in values
                if isinstance(value, str) and _TERMS.search(value)
            ]
            if matches:
                fields[name] = matches
        if not fields:
            continue
        found.append({
            "recordId": record["id"],
            "summary": summary,
            "summaryMatches": bool(_TERMS.search(summary)),
            "reviewed": record["id"] in reviewed_ids,
            "details": fields,
            "citations": [
                {"sourceId": citation["sourceId"], "page": citation.get("page")}
                for citation in record.get("citations", [])
            ],
        })
    return sorted(found, key=lambda row: row["recordId"])


def audit_detail_candidates(
    army_db: Path,
    curated_source: Path,
    delivery_reviews: Path,
    candidate_reviews: Path,
) -> dict[str, Any]:
    """Retain evidence and review status, never create or assign an object."""
    inventory = audit_inventory(
        army_db, curated_source, delivery_reviews, candidate_reviews,
    )
    reviewed_ids = {
        row["recordId"] for row in inventory["reviewedCandidateDecisions"]
    } | {
        row["originRecordId"] for row in inventory["reviewedDeliveryPaths"]
    }
    records = json.loads(curated_source.read_text(encoding="utf-8"))
    mentions = detail_candidates(records, reviewed_ids=reviewed_ids)
    return {
        "scope": "detail-keyword-discovery-not-complete-source-inventory",
        "sourceSha256": inventory["curatedSourceSha256"],
        "mentions": mentions,
        "unreviewed": [item for item in mentions if not item["reviewed"]],
        "detailsOnly": [item for item in mentions if not item["summaryMatches"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--army-db", type=Path, default=root / "data/generated/infinity.db"
    )
    parser.add_argument(
        "--curated-source", type=Path,
        default=root / "data/curated/rules/n5-core-v5.3.json",
    )
    parser.add_argument(
        "--delivery-reviews", type=Path,
        default=root / "config/validation/deployed-object-delivery-reviews.json",
    )
    parser.add_argument(
        "--candidate-reviews", type=Path,
        default=root / "config/validation/deployed-object-candidate-reviews.json",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print all evidence and review states"
    )
    args = parser.parse_args()
    report = audit_detail_candidates(
        args.army_db, args.curated_source, args.delivery_reviews, args.candidate_reviews,
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Curated source SHA-256: {report['sourceSha256']}")
        print(f"Detailed-rule candidates: {len(report['mentions'])}")
        print(f"Detail-only candidates: {len(report['detailsOnly'])}")
        print(f"Unreviewed candidates: {len(report['unreviewed'])}")
        for item in report["unreviewed"]:
            print(f"  {item['recordId']}: {', '.join(item['details'])}")
    return 1 if report["unreviewed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
