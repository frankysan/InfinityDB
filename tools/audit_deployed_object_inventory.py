"""Read-only 1.0 inventory of source profiles and potential deployed objects.

An Army metadata row and a curated rule mention do not establish a deployed
object's canonical identity, carrier, delivery mode or gameplay equivalence.
This audit exposes evidence for manual review; it creates no runtime records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

# The 14 *printed* N5.3 supplementary chart profiles, keyed by the Army
# catalog identity and exact source mode.  This is evidence, not object IDs.
CHART_AUXILIARY: tuple[tuple[str, str | None, str, int], ...] = (
    ("AP Mine", None, "weapon", 181),
    ("Cybermine", None, "weapon", 181),
    ("Drop Bears", "Deployable Mode", "weapon", 181),
    ("E/M Mine", None, "weapon", 181),
    ("Monofilament Mine", None, "weapon", 181),
    ("PARA Mine", None, "weapon", 181),
    ("Shock Mine", None, "weapon", 181),
    ("Viral Mine", None, "weapon", 181),
    ("WildParrot", None, "weapon", 181),
    ("Crazykoala", None, "weapon", 186),
    ("Dazer", None, "equipment", 186),
    ("Deployable Repeater", None, "equipment", 186),
    ("Disco Baller", "Disco Ball", "weapon", 186),
    ("FastPanda", None, "equipment", 186),
)

# Manual source-backed classification of examples beyond those 14 profiles.
# A delivery relationship is evidence for a future model, NOT a roster-use
# relation or authorization to equate a launcher with its deployed object.
REVIEW_CASES = (
    ("weapon:armed-turret", "curated-special-profile"),
    ("equipment:deployable-cover", "nonstandard-scenery"),
    ("weapon:pitcher", "delivery-not-object"),
)

# A separate, intentionally broad lead finder for source-domain clauses
# missed by the original summary-only Deployable/Token/Scenery scan.
# Matches are evidence to inspect, NOT deployable-object identities.
CLAUSE_FIELDS = ("requirements", "effects", "restrictions", "clarifications", "sourceNotes")
SOURCE_DOMAIN_CLAUSE_RE = re.compile(
    r"\b(?:deploy(?:s|ed|ment|ing)?|plac(?:e|ed|es|ing|ement)|"
    r"creat(?:e|ed|es|ing)|generat(?:e|es|ed|ing)|spawn(?:s|ed)|"
    r"set up|representation|marker|miniature|independent|"
    r"remains? on the (?:game )?table)\b",
    re.IGNORECASE,
)


def source_domain_clause_leads(
    records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Surface exact clauses absent from the earlier summary-keyword scan."""
    leads: list[dict[str, Any]] = []
    for record_id, record in sorted(records.items()):
        if (
            record.get("kind") not in {"weapon", "equipment"}
            or (record.get("composition") or {}).get("role") != "definition"
        ):
            continue
        summary = record.get("summary", "")
        if not isinstance(summary, str) or any(
            term.casefold() in summary.casefold()
            for term in ("Deployable", "Token", "Scenery Element")
        ):
            continue
        facts = record.get("facts") or {}
        clauses = {"summary": [summary]}
        for field in CLAUSE_FIELDS:
            clauses[field] = facts.get(field, []) if isinstance(facts, dict) else []
        matches = {
            field: [
                item for item in items
                if isinstance(item, str) and SOURCE_DOMAIN_CLAUSE_RE.search(item)
            ]
            for field, items in clauses.items()
        }
        matches = {field: items for field, items in matches.items() if items}
        if matches:
            leads.append({
                "recordId": record_id,
                "kind": record["kind"],
                "matchedClauses": matches,
                "citations": _citation_summary(record),
            })
    return leads


def _identity(row: dict[str, Any]) -> tuple[str, str | None, str]:
    catalog = "equipment" if row["type"] == "EQUIPMENT" else "weapon"
    return (row["name"].casefold(), row["mode"] or None, catalog)


def _profile_stats(raw: str) -> dict[str, int] | None:
    """Parse only complete conventional four-attribute object profiles."""
    cells = re.findall(r"\b(ARM|BTS|STR|S)\s*=\s*(\d+)\b", raw)
    if len(cells) != 4 or len(set(key for key, _ in cells)) != 4:
        return None
    return {key: int(value) for key, value in cells}


def _citation_summary(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"sourceId": cite["sourceId"], "page": cite.get("page"),
         "member": cite.get("member")}
        for cite in record.get("citations", [])
    ]


def validate_delivery_reviews(
    reviews: dict[str, Any],
    records: dict[str, dict[str, Any]],
    source_profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve reviewed source evidence, never create canonical object identities."""
    if reviews.get("formatVersion") != 1:
        raise ValueError("Unsupported deployed-object delivery review format")
    profile_index: dict[tuple[str, str, str | None], list[dict[str, Any]]] = {}
    for profile in source_profiles:
        key = (profile["catalog"], profile["name"], profile["mode"])
        profile_index.setdefault(key, []).append(profile)
    accepted = []
    seen: set[tuple[str, str]] = set()
    for entry in reviews["reviewedDeliveryPaths"]:
        origin = entry["originRecordId"]
        key = (origin, entry["delivery"])
        if key in seen:
            raise ValueError(f"Duplicate delivered-object source path: {key}")
        seen.add(key)
        record = records.get(origin)
        if record is None or entry["summaryEvidence"] not in record.get("summary", ""):
            raise ValueError(f"Unverified delivery summary evidence: {key}")
        citation_pages = {
            cite["page"] for cite in record.get("citations", [])
            if cite["sourceId"] == "n5-core-v5.3-pdf" and cite.get("page") is not None
        }
        if not set(entry["sourcePages"]) <= citation_pages:
            raise ValueError(f"Unverified N5.3 delivery citations: {key}")

        rules_owner = entry["objectRulesRecordId"]
        if rules_owner is not None and rules_owner not in records:
            raise ValueError(f"Missing object rules owner: {rules_owner}")
        profile_source = entry["sourceProfile"]
        matching: list[dict[str, Any]] = []
        if profile_source is not None:
            selector = (
                profile_source["catalog"],
                profile_source["name"],
                profile_source["mode"],
            )
            matching = profile_index.get(selector, [])
            if len(matching) != 1:
                raise ValueError(f"Unresolved/ambiguous source profile: {key}: {selector}")
        accepted.append({
            **entry,
            "sourceProfileEvidence": matching[0] if matching else None,
            "reviewStatus": "source-backed-audit-only",
        })
    return accepted


def validate_candidate_reviews(
    manifest: dict[str, Any],
    records: dict[str, dict[str, Any]],
    source_profiles: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Fail closed on reviewed nonstandard/profile-less object classifications."""
    if manifest.get("formatVersion") != 1:
        raise ValueError("Unsupported deployed-object candidate review format")
    shapes_for_classification = {
        "deployed-scenery-s-only": "s-only-scenery",
        "deployed-object-curated-trooper-profile": "curated-special-profile",
        "user-tool-not-deployed-object": "none",
        "assignable-single-use-not-deployed-object": "none",
        "deployed-object-army-source-profile": "army-source-profile",
        "variant-family-not-canonical-object": "none",
        "immediate-charge-not-persistent-object": "none",
        "automatic-equipment-not-deployed-object": "none",
        "non-targetable-state-token-not-deployed-object": "none",
    }
    reviewed = []
    seen: set[str] = set()
    for entry in manifest["reviews"]:
        record_id = entry["recordId"]
        if record_id in seen:
            raise ValueError(f"Duplicate candidate decision: {record_id}")
        seen.add(record_id)
        record = records.get(record_id)
        if record is None or (record.get("composition") or {}).get("role") != "definition":
            raise ValueError(f"Missing candidate definition: {record_id}")
        classification = entry["classification"]
        shape = entry["profileShape"]
        if shapes_for_classification.get(classification) != shape:
            raise ValueError(f"Unsupported candidate classification/shape: {record_id}")
        if entry["summaryEvidence"] not in record.get("summary", ""):
            raise ValueError(f"Candidate summary evidence drift: {record_id}")
        facts = record.get("facts") or {}
        detail = "\n".join(
            str(fragment)
            for key in ("requirements", "effects", "restrictions", "clarifications", "sourceNotes")
            for fragment in facts.get(key, [])
        )
        if any(fragment not in detail for fragment in entry["factsEvidence"]):
            raise ValueError(f"Candidate detailed evidence drift: {record_id}")
        pages = {
            cite["page"] for cite in record.get("citations", [])
            if cite.get("sourceId") == "n5-core-v5.3-pdf" and cite.get("page") is not None
        }
        if not entry["sourcePages"] or not set(entry["sourcePages"]) <= pages:
            raise ValueError(f"Candidate N5.3 citation drift: {record_id}")
        attributes = entry["knownAttributes"]
        unknown = entry["unreportedAttributes"]
        if len(unknown) != len(set(unknown)) or set(attributes) & set(unknown):
            raise ValueError(f"Duplicate or conflicting candidate attribute claims: {record_id}")
        if not set(attributes) | set(unknown) <= {"ARM", "BTS", "STR", "S"}:
            raise ValueError(f"Unexpected candidate attribute: {record_id}")
        special = facts.get("specialProfile")
        if shape == "curated-special-profile":
            if not isinstance(special, dict):
                raise ValueError(f"Missing curated object profile: {record_id}")
            source_stats = dict(special["stats"])
            if any(source_stats.get(name) != value for name, value in attributes.items()):
                raise ValueError(f"Curated object profile drift: {record_id}")
            if set(attributes) != {"ARM", "BTS", "STR", "S"} or unknown:
                raise ValueError(f"Unreviewed special-profile attribute shape: {record_id}")
        elif shape == "army-source-profile":
            selector = entry.get("sourceProfile")
            if special is not None or not isinstance(selector, dict) or unknown:
                raise ValueError(f"Invalid Army profile claim: {record_id}")
            matching = [
                row for row in (source_profiles or [])
                if all(row.get(field) == selector.get(field)
                       for field in ("catalog", "name", "mode"))
            ]
            if len(matching) != 1 or matching[0]["attributes"] is None:
                raise ValueError(f"Missing exact Army source profile: {record_id}")
            actual = {key: str(value) for key, value in matching[0]["attributes"].items()}
            if attributes != actual:
                raise ValueError(f"Army source profile drift: {record_id}")
        elif shape == "s-only-scenery":
            if special is not None or attributes != {"S": "3"} or set(unknown) != {
                "ARM", "BTS", "STR"
            }:
                raise ValueError(f"Unsupported scenery profile shape: {record_id}")
            if "Silhouette S3" not in detail:
                raise ValueError(f"Missing explicit scenery Silhouette: {record_id}")
        elif special is not None or attributes or unknown:
            raise ValueError(f"False missing-profile or non-object claim: {record_id}")
        if shape != "army-source-profile" and entry.get("sourceProfile") is not None:
            raise ValueError(f"Non-source candidate contains Army selector: {record_id}")
        reviewed.append({**entry, "reviewStatus": "source-backed-audit-only"})
    return reviewed


def audit_inventory(
    army_db: Path,
    curated_source: Path,
    delivery_reviews: Path | None = None,
    candidate_reviews: Path | None = None,
) -> dict[str, Any]:
    with sqlite3.connect(f"{army_db.resolve().as_uri()}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        source = [
            dict(row) for row in conn.execute(
                "SELECT position, id, type, name, mode, profile "
                "FROM metadata_weapons ORDER BY position"
            )
            if isinstance(row["profile"], str) and row["profile"].strip()
        ]
    groups: dict[tuple[str, str | None, str], list[dict[str, Any]]] = {}
    for row in source:
        groups.setdefault(_identity(row), []).append(row)

    chart_profiles: list[dict[str, Any]] = []
    known_positions: set[int] = set()
    for name, mode, catalog, page in CHART_AUXILIARY:
        matches = groups.get((name.casefold(), mode, catalog), [])
        if len(matches) != 1:
            raise ValueError(f"Expected one source profile for {name} ({mode}): {len(matches)}")
        row = matches[0]
        known_positions.add(row["position"])
        chart_profiles.append({
            "sourceId": row["id"], "name": name, "mode": mode,
            "catalog": catalog, "sourceProfile": row["profile"],
            "attributes": _profile_stats(row["profile"]),
            "pdfPage": page,
        })

    additional_profiles = [
        {
            "sourceId": row["id"], "name": row["name"],
            "mode": row["mode"], "catalog": _identity(row)[2],
            "sourceProfile": row["profile"],
            "attributes": _profile_stats(row["profile"]),
        }
        for row in source if row["position"] not in known_positions
    ]
    document = json.loads(curated_source.read_text(encoding="utf-8"))
    records = {
        record["id"]: record
        for record in document["records"]
        if record.get("kind") in {"weapon", "equipment"}
    }

    reviewed_examples = []
    for record_id, category in REVIEW_CASES:
        record = records.get(record_id)
        if record is None:
            raise ValueError(f"Missing reviewed source record: {record_id}")
        reviewed_examples.append({
            "recordId": record_id, "category": category,
            "hasCuratedSpecialProfile": isinstance(
                (record.get("facts") or {}).get("specialProfile"), dict
            ),
            "citations": _citation_summary(record),
        })

    # Deliberately broad discovery queue: mere words cannot create object
    # identities. Keep raw evidence for the next manual review batch.
    candidates = []
    for record_id, record in sorted(records.items()):
        if (record.get("composition") or {}).get("role") != "definition":
            continue
        text = record.get("summary", "")
        indicators = [
            token for token in ("Deployable", "Token", "Scenery Element")
            if token.casefold() in text.casefold()
        ]
        if not indicators:
            continue
        candidates.append({
            "recordId": record_id, "indicators": indicators,
            "reviewStatus": "identity-not-inferred",
            "citations": _citation_summary(record),
        })

    decisions = (
        validate_candidate_reviews(
            json.loads(candidate_reviews.read_text(encoding="utf-8")),
            records, chart_profiles + additional_profiles,
        )
        if candidate_reviews is not None else []
    )
    decided_ids = {decision["recordId"] for decision in decisions}
    reviewed_paths = (
        validate_delivery_reviews(
            json.loads(delivery_reviews.read_text(encoding="utf-8")),
            records, chart_profiles + additional_profiles,
        )
        if delivery_reviews is not None else []
    )
    delivery_origins = {path["originRecordId"] for path in reviewed_paths}
    source_clause_leads = [
        {
            **row,
            "reviewStatus": (
                "candidate-reviewed" if row["recordId"] in decided_ids
                else "delivery-reviewed" if row["recordId"] in delivery_origins
                else "manual-review-required"
            ),
        }
        for row in source_domain_clause_leads(records)
    ]

    return {
        "formatVersion": 1,
        "scope": "candidate-inventory-not-canonical-object-model",
        "curatedWeaponEquipmentDefinitions": sum(
            (record.get("composition") or {}).get("role") == "definition"
            for record in records.values()
        ),
        "additionalCuratedClauseLeads": source_clause_leads,
        "unreviewedCuratedClauseLeads": [
            row for row in source_clause_leads
            if row["reviewStatus"] == "manual-review-required"
        ],
        "armyDatabaseSha256": hashlib.sha256(army_db.read_bytes()).hexdigest(),
        "curatedSourceSha256": hashlib.sha256(curated_source.read_bytes()).hexdigest(),
        "chartProfiles": chart_profiles,
        "additionalSourceProfiles": additional_profiles,
        "reviewedExamples": reviewed_examples,
        "curatedCandidateMentions": candidates,
        "deliveryReviewSha256": (
            hashlib.sha256(delivery_reviews.read_bytes()).hexdigest()
            if delivery_reviews is not None else None
        ),
        "reviewedDeliveryPaths": reviewed_paths,
        "candidateReviewSha256": (
            hashlib.sha256(candidate_reviews.read_bytes()).hexdigest()
            if candidate_reviews is not None else None
        ),
        "reviewedCandidateDecisions": decisions,
        "deliveryCoveredCandidateMentions": [
            row for row in candidates if row["recordId"] in delivery_origins
        ],
        "remainingCuratedCandidateMentions": [
            row for row in candidates
            if row["recordId"] not in decided_ids | delivery_origins
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument(
        "--curated-source", type=Path,
        default=Path("data/curated/rules/n5-core-v5.3.json"),
    )
    parser.add_argument(
        "--delivery-reviews", type=Path,
        default=Path("config/validation/deployed-object-delivery-reviews.json"),
    )
    parser.add_argument(
        "--candidate-reviews", type=Path,
        default=Path("config/validation/deployed-object-candidate-reviews.json"),
    )
    parser.add_argument("--json-output", type=Path)
    arguments = parser.parse_args()
    report = audit_inventory(
        arguments.army_db, arguments.curated_source,
        arguments.delivery_reviews, arguments.candidate_reviews,
    )
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.json_output is not None:
        arguments.json_output.write_text(result, encoding="utf-8", newline="\n")
    else:
        print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
