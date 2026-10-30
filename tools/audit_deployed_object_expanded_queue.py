"""Audit named battlefield elements missed by the first non-catalog keyword scan.

This is an additional *read-only* discovery pass, not a release inventory.
Scenario objectives, deployed-device interactions, and Marker/decoy
representations must not be conflated with independent Weapon/Equipment
identities or their Army carrier relationships.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from tools.audit_deployed_object_non_catalog_queue import FIELDS, KINDS, candidate_mentions

ROOT = Path(__file__).resolve().parents[1]
# Deliberately distinct from the original Deployable/Token/Scenery Element
# terms; review new terms before broadening this bounded scan.
EXPANDED_TERMS = re.compile(
    r"\b(?:consoles?|supply boxes?|disco balls?|seed-embryos?|"
    r"decoys?|holoecho(?:es)?|markers?)\b",
    re.IGNORECASE,
)
CLASSIFICATIONS = {
    "term:marker": ("term", "representation-type-not-object-identity"),
    "rule:scenario:consoles": ("rule", "scenario-object-separate-domain"),
    "rule:scenario:supply-boxes": ("rule", "scenario-object-separate-domain"),
    "rule:scenario:controlling-supply-boxes": (
        "rule", "scenario-control-not-object-identity",
    ),
    "skill:hack-consoles": ("skill", "scenario-interaction-not-object-identity"),
    "skill:activate-disco-ball": ("skill", "reviewed-object-interaction-not-identity"),
    "skill:decoy": ("skill", "trooper-replica-deployment-not-device"),
    "state:holoecho": ("state", "interactive-trooper-replicas-not-device"),
    "state:hidden-deployment": ("state", "unplaced-trooper-position-not-object"),
    "state:impersonation-1": ("state", "trooper-disguise-marker-not-device"),
    "state:impersonation-2": ("state", "trooper-disguise-marker-not-device"),
    "skill:discover": ("skill", "reveals-existing-marker-not-device"),
    "skill:surprise-attack": ("skill", "marker-attack-modifier-not-device"),
    "skill:sensor": ("skill", "reveals-existing-game-elements-not-device"),
    "trait:indiscriminate": ("trait", "targeting-exception-not-object-identity"),
    "skill:look-out": ("skill", "marker-targeted-aro-not-object"),
    "skill:chain-of-command": ("skill", "existing-trooper-role-transfer-not-object"),
    "skill:morpho-scan": ("skill", "existing-model-attribute-copy-not-object"),
    "rule:scenario:killing": ("rule", "scenario-trooper-scoring-not-object"),
    "rule:scenario:reinforced-tactical-link": (
        "rule", "scenario-lieutenant-representation-not-object",
    ),
    "state:decoy": ("state", "static-trooper-replicas-not-device"),
    "trait:concealed": ("trait", "existing-weapon-equipment-representation"),
    "skill:mnemonica": ("skill", "existing-trooper-host-transfer-not-object"),
    "skill:tactical-awareness": ("skill", "order-marker-not-object"),
    "skill:explode": ("skill", "trooper-centered-template-not-object"),
}

# Read-only N5.3 PDF review evidence for definitions whose maintained source
# currently provides Wiki citations only. Do not publish these as rule cites
# without rebuilding the tracked rules database and dependent fingerprints.
PDF_ONLY_REVIEWS = {
    "state:decoy": (159, "replicas do not hide a Trooper"),
    "trait:concealed": (175, "Camouflage Markers concealing a"),
    "skill:mnemonica": (103, "You must identify the Model or Marker"),
    "skill:tactical-awareness": (115, "a Model or Marker"),
    "skill:explode": (92, "Template Attacks that affect allied Models or Markers"),
}


def expanded_mentions(curated: dict[str, Any]) -> list[dict[str, Any]]:
    """Surface additional leads, preserving exact matched clauses and citations."""
    existing_ids = {row["recordId"] for row in candidate_mentions(curated)}
    candidates: list[dict[str, Any]] = []
    for record in curated["records"]:
        if (
            record.get("kind") not in KINDS
            or (record.get("composition") or {}).get("role") != "definition"
            or record.get("id") in existing_ids
        ):
            continue
        summary = record.get("summary")
        facts = record.get("facts") or {}
        if not isinstance(summary, str) or not isinstance(facts, dict):
            continue
        matched: dict[str, list[str]] = {}
        if EXPANDED_TERMS.search(summary):
            matched["summary"] = [summary]
        for field in FIELDS:
            items = facts.get(field, [])
            if not isinstance(items, list):
                continue
            excerpts = [
                item for item in items
                if isinstance(item, str) and EXPANDED_TERMS.search(item)
            ]
            if excerpts:
                matched[field] = excerpts
        if not matched:
            continue
        candidates.append({
            "recordId": record["id"],
            "kind": record["kind"],
            "matched": matched,
            "citations": [
                {"sourceId": citation["sourceId"], "page": citation.get("page")}
                for citation in record.get("citations", [])
            ],
        })
    return sorted(candidates, key=lambda row: row["recordId"])


def validate_reviews(
    manifest: dict[str, Any],
    curated: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fail closed on unsupported review IDs, source drift or identity claims."""
    if manifest.get("formatVersion") != 1:
        raise ValueError("Unsupported expanded candidate review format")
    source = {item["id"]: item for item in curated["records"]}
    ids = {item["recordId"] for item in candidates}
    seen: set[str] = set()
    accepted: list[dict[str, Any]] = []
    for review in manifest["reviews"]:
        record_id = review["recordId"]
        if record_id in seen:
            raise ValueError(f"Duplicate expanded review: {record_id}")
        seen.add(record_id)
        if record_id not in ids:
            raise ValueError(f"Missing expanded candidate: {record_id}")
        record = source[record_id]
        if (record["kind"], review["classification"]) != CLASSIFICATIONS.get(record_id):
            raise ValueError(f"Unsupported expanded classification: {record_id}")
        if (
            not isinstance(review.get("summaryEvidence"), str)
            or not review["summaryEvidence"]
            or review["summaryEvidence"] not in record["summary"]
        ):
            raise ValueError(f"Expanded summary evidence drift: {record_id}")
        clauses = "\n".join(
            item for field in FIELDS for item in (record.get("facts") or {}).get(field, [])
            if isinstance(item, str)
        )
        evidence = review.get("factsEvidence")
        if (
            not isinstance(evidence, list)
            or (not evidence and bool(clauses.strip()))
            or any(
                not isinstance(item, str) or not item or item not in clauses
                for item in evidence
            )
        ):
            raise ValueError(f"Expanded detail evidence drift: {record_id}")
        pages = {
            cite.get("page") for cite in record.get("citations", [])
            if cite.get("sourceId") == "n5-core-v5.3-pdf"
        }
        claimed = review.get("sourcePages")
        pdf_only = PDF_ONLY_REVIEWS.get(record_id)
        if pdf_only is None:
            if (
                review.get("citationStatus") is not None
                or review.get("pdfExcerpt") is not None
                or not isinstance(claimed, list)
                or not claimed
                or not set(claimed) <= pages
            ):
                raise ValueError(f"Expanded source citation drift: {record_id}")
        elif (
            pages
            or claimed != [pdf_only[0]]
            or review.get("citationStatus") != "pdf-verified-manifest-only"
            or review.get("pdfExcerpt") != pdf_only[1]
        ):
            raise ValueError(f"Expanded PDF-only provenance drift: {record_id}")
        if not review.get("caveat") or review.get("objectProfile") is not None:
            raise ValueError(f"Expanded review must remain audit-only: {record_id}")
        accepted.append(review)
    return accepted


def audit_expanded_candidates(curated_source: Path, reviews_source: Path) -> dict[str, Any]:
    """Return a deterministic, open manual queue independent of publication."""
    raw = curated_source.read_bytes()
    curated = json.loads(raw)
    candidates = expanded_mentions(curated)
    reviews = validate_reviews(
        json.loads(reviews_source.read_text(encoding="utf-8")), curated, candidates,
    )
    reviewed = {decision["recordId"] for decision in reviews}
    missing_maintained_pdf = [
        row for row in candidates if not any(
            cite["sourceId"] == "n5-core-v5.3-pdf"
            and isinstance(cite["page"], int)
            for cite in row["citations"]
        )
    ]
    reviewed_pdf_only = [
        decision for decision in reviews
        if decision["recordId"] in PDF_ONLY_REVIEWS
    ]
    return {
        "scope": "expanded-lexical-discovery-not-object-completeness",
        "curatedSourceSha256": hashlib.sha256(raw).hexdigest(),
        "candidateCount": len(candidates),
        "reviewedCount": len(reviewed),
        "unreviewed": [r for r in candidates if r["recordId"] not in reviewed],
        "reviewedPdfOnly": reviewed_pdf_only,
        "missingMaintainedN5Citation": missing_maintained_pdf,
        "candidates": [
            {**r, "reviewed": r["recordId"] in reviewed} for r in candidates
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
        default=ROOT / "config/validation/deployed-object-expanded-reviews.json",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_expanded_candidates(args.curated_source, args.reviews)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Additional candidate definitions: {report['candidateCount']}")
        print(f"Reviewed distinctions: {report['reviewedCount']}")
        print(f"Open additional candidates: {len(report['unreviewed'])}")
        print(f"Reviewed with audit-only PDF evidence: {len(report['reviewedPdfOnly'])}")
        print(
            "Definitions missing maintained N5.3 PDF citations: "
            f"{len(report['missingMaintainedN5Citation'])}"
        )
        for item in report["unreviewed"]:
            print(f"  {item['recordId']}: {', '.join(item['matched'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
