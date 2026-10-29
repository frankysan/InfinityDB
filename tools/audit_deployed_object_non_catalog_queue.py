"""Read-only discovery of non-catalog rules that mention deployed game elements.

The existing deployed-object review only scans Weapon/Equipment definitions.
Skills, rules, traits, terms and states can describe additional battlefield
elements or placement methods. Keyword matches are investigation leads, not
object identities or authority to add delivery edges or Unit uses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KINDS = frozenset({"skill", "rule", "trait", "term", "state"})
FIELDS = ("requirements", "effects", "restrictions", "clarifications", "sourceNotes")
TERMS = re.compile(r"\b(?:deployables?|tokens?|scenery elements?)\b", re.IGNORECASE)
# These are source-reviewed decisions, not a generic classification heuristic.
# Adding another decision requires explicit review of its exact source clause.
CLASSIFICATIONS = {
    "skill:minelayer": ("skill", "skill-deployment-method-not-object"),
    "skill:place-deployable": ("skill", "skill-delivery-method-not-object"),
    "skill:request-speedball": ("skill", "support-state-token-not-standard-deployable"),
    "skill:request-specball": ("skill", "support-state-token-not-standard-deployable"),
    "skill:remdriver": ("skill", "assignment-token-not-independent-object"),
    "skill:pick-up-supply-boxes": ("skill", "scenario-interaction-not-object-identity"),
    "rule:peripheral-type:ancillary": ("rule", "deployed-peripheral-trooper-separate-domain"),
    "rule:scenario:carrying-supply-boxes": ("rule", "scenario-object-outside-weapon-equipment"),
    "term:token": ("term", "game-element-type-not-instance"),
    "term:state-token": ("term", "state-indicator-type-not-object-profile"),
    "term:deployable-equipment": ("term", "game-element-type-not-instance"),
    "term:deployable-weapon": ("term", "game-element-type-not-instance"),
    "term:scenery-element": ("term", "game-element-type-not-instance"),
}


def candidate_mentions(curated: dict[str, Any]) -> list[dict[str, Any]]:
    """Retain exact maintained text and citations for conservative manual review."""
    candidates: list[dict[str, Any]] = []
    for record in curated["records"]:
        if record.get("kind") not in KINDS:
            continue
        if (record.get("composition") or {}).get("role") != "definition":
            continue
        summary = record.get("summary", "")
        if not isinstance(summary, str):
            continue
        facts = record.get("facts") or {}
        if not isinstance(facts, dict):
            continue
        details: dict[str, list[str]] = {}
        for key in FIELDS:
            values = facts.get(key, [])
            if not isinstance(values, list):
                continue
            found = [value for value in values if isinstance(value, str) and TERMS.search(value)]
            if found:
                details[key] = found
        if not TERMS.search(summary) and not details:
            continue
        candidates.append({
            "recordId": record["id"],
            "kind": record["kind"],
            "summary": summary,
            "summaryMatches": bool(TERMS.search(summary)),
            "details": details,
            "citations": [
                {"sourceId": cite["sourceId"], "page": cite.get("page")}
                for cite in record.get("citations", [])
            ],
        })
    return sorted(candidates, key=lambda row: row["recordId"])


def validate_reviews(
    manifest: dict[str, Any],
    curated: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate narrow negative/exception classifications against cited source text."""
    if manifest.get("formatVersion") != 1:
        raise ValueError("Unsupported non-catalog game-element review format")
    indexed = {record["id"]: record for record in curated["records"]}
    candidate_ids = {entry["recordId"] for entry in candidates}
    decisions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for decision in manifest["reviews"]:
        record_id = decision["recordId"]
        if record_id in seen:
            raise ValueError(f"Duplicate non-catalog candidate review: {record_id}")
        seen.add(record_id)
        if record_id not in candidate_ids:
            raise ValueError(f"No current non-catalog candidate mention: {record_id}")
        record = indexed[record_id]
        if (record.get("kind"), decision["classification"]) != CLASSIFICATIONS.get(record_id):
            raise ValueError(f"Unsupported non-catalog classification: {record_id}")
        summary = record.get("summary", "")
        if not decision["summaryEvidence"] or decision["summaryEvidence"] not in summary:
            raise ValueError(f"Non-catalog summary evidence drift: {record_id}")
        facts = record.get("facts") or {}
        detail = "\n".join(
            text for key in FIELDS for text in facts.get(key, [])
            if isinstance(text, str)
        )
        evidence = decision["factsEvidence"]
        # Glossary definitions have cited summaries but no structured
        # Requirements/Effects clauses. Other decisions must pin both.
        if not isinstance(evidence, list) or (
            not evidence and record["kind"] != "term"
        ) or any(not isinstance(text, str) or not text or text not in detail for text in evidence):
            raise ValueError(f"Non-catalog detailed evidence drift: {record_id}")
        pages = {
            cite.get("page") for cite in record.get("citations", [])
            if cite.get("sourceId") == "n5-core-v5.3-pdf"
        }
        if not decision["sourcePages"] or not set(decision["sourcePages"]) <= pages:
            raise ValueError(f"Missing exact N5.3 non-catalog citation: {record_id}")
        if not decision.get("caveat") or decision.get("objectProfile") is not None:
            raise ValueError(f"Invalid non-catalog review scope: {record_id}")
        decisions.append(decision)
    return decisions


def audit_non_catalog_candidates(curated_source: Path, reviews_source: Path) -> dict[str, Any]:
    """Report current rule-domain discovery and reviewed classification boundaries."""
    curated_bytes = curated_source.read_bytes()
    curated = json.loads(curated_bytes)
    candidates = candidate_mentions(curated)
    reviews = validate_reviews(
        json.loads(reviews_source.read_text(encoding="utf-8")), curated, candidates,
    )
    reviewed_ids = {item["recordId"] for item in reviews}
    return {
        "scope": "non-catalog-keyword-discovery-not-object-inventory",
        "curatedSourceSha256": hashlib.sha256(curated_bytes).hexdigest(),
        "reviewedCount": len(reviewed_ids),
        "candidateCount": len(candidates),
        "candidates": [
            {**candidate, "reviewed": candidate["recordId"] in reviewed_ids}
            for candidate in candidates
        ],
        "unreviewed": [
            candidate for candidate in candidates if candidate["recordId"] not in reviewed_ids
        ],
        "reviews": reviews,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--curated-source", type=Path, default=ROOT / "data/curated/rules/n5-core-v5.3.json",
    )
    parser.add_argument(
        "--reviews", type=Path,
        default=ROOT / "config/validation/deployed-object-non-catalog-reviews.json",
    )
    parser.add_argument("--json", action="store_true", help="Print all candidate evidence")
    args = parser.parse_args()
    report = audit_non_catalog_candidates(args.curated_source, args.reviews)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Candidate definitions: {report['candidateCount']}")
        print(f"Reviewed classifications: {report['reviewedCount']}")
        print(f"Awaiting manual review: {len(report['unreviewed'])}")
        for entry in report["unreviewed"]:
            print(f"  {entry['recordId']}: {', '.join(entry['details']) or 'summary'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
