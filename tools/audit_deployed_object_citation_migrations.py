"""Preflight the audit-only N5.3 citations pending coordinated publication.

Reconciles three independently reviewed manifests against the current curated
source, without editing source data, rules.db, or deployment fingerprints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools import audit_deployed_object_expanded_queue as expanded_audit
from tools import audit_deployed_object_non_catalog_queue as non_catalog_audit
from tools.audit_deployed_object_inventory import (
    SOURCE_DOMAIN_PDF_ONLY,
    source_domain_clause_leads,
    validate_source_domain_clause_reviews,
)

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
MANIFEST_PATHS = {
    "non-catalog": ROOT / "config/validation/deployed-object-non-catalog-reviews.json",
    "expanded": ROOT / "config/validation/deployed-object-expanded-reviews.json",
    "source-domain": ROOT / "config/validation/deployed-object-source-domain-clause-reviews.json",
}
SOURCE_PDF = "n5-core-v5.3-pdf"
STATUS = "pdf-verified-manifest-only"


def build_citation_migration_plan(
    curated: dict[str, Any], manifests: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Fail closed before any persistent citation and fingerprint migration."""
    records = {record["id"]: record for record in curated["records"]}
    if len(records) != len(curated["records"]):
        raise ValueError("Duplicate curated rule ID")
    weapon_equipment = {
        key: record for key, record in records.items()
        if record.get("kind") in {"weapon", "equipment"}
    }
    sources = (
        (
            "non-catalog", non_catalog_audit.PDF_ONLY_REVIEWS,
            non_catalog_audit.validate_reviews(
                manifests["non-catalog"], curated, non_catalog_audit.candidate_mentions(curated),
            ),
        ),
        (
            "expanded", expanded_audit.PDF_ONLY_REVIEWS,
            expanded_audit.validate_reviews(
                manifests["expanded"], curated, expanded_audit.expanded_mentions(curated),
            ),
        ),
        (
            "source-domain", SOURCE_DOMAIN_PDF_ONLY,
            validate_source_domain_clause_reviews(
                manifests["source-domain"], weapon_equipment,
                source_domain_clause_leads(weapon_equipment),
            ),
        ),
    )
    seen: set[str] = set()
    pending: list[dict[str, Any]] = []
    migrated: list[dict[str, Any]] = []
    for manifest_name, pinned, reviews in sources:
        found = {row["recordId"] for row in reviews if row["recordId"] in pinned}
        if found != set(pinned):
            raise ValueError(f"PDF-only review inventory changed: {manifest_name}")
        for decision in reviews:
            record_id = decision["recordId"]
            if record_id not in pinned:
                continue
            if record_id in seen:
                raise ValueError(f"Duplicate cross-manifest migration: {record_id}")
            seen.add(record_id)
            record = records[record_id]
            page, excerpt = pinned[record_id]
            if (
                decision["sourcePages"] != [page]
                or record.get("composition", {}).get("role") != "definition"
            ):
                raise ValueError(f"Stale PDF-only source evidence: {record_id}")
            entry = {
                "recordId": record_id,
                "kind": record["kind"],
                "name": record["name"],
                "reviewManifest": manifest_name,
                "pdfExcerpt": excerpt,
                "proposedCitation": {"sourceId": SOURCE_PDF, "page": page},
            }
            if decision.get("citationStatus") == STATUS:
                if (
                    decision.get("pdfExcerpt") != excerpt
                    or any(
                        item.get("sourceId") == SOURCE_PDF
                        for item in record.get("citations", [])
                    )
                ):
                    raise ValueError(f"Stale pending migration: {record_id}")
                pending.append(entry)
            else:
                if (
                    "citationStatus" in decision or "pdfExcerpt" in decision
                    or [
                        item for item in record.get("citations", [])
                        if item.get("sourceId") == SOURCE_PDF
                    ] != [entry["proposedCitation"]]
                ):
                    raise ValueError(f"Stale migrated citation: {record_id}")
                migrated.append(entry)
    expected = sum(len(pinned) for _, pinned, _ in sources)
    if len(pending) + len(migrated) != expected or (pending and migrated):
        raise ValueError("Incomplete or partial cross-manifest citation migration")
    return {
        "scope": "citation-preflight-only-no-source-or-runtime-modification",
        "source": SOURCE_PDF,
        "pendingCount": len(pending),
        "migratedCount": len(migrated),
        "countsByManifest": {name: len(pinned) for name, pinned, _ in sources},
        "pending": sorted(pending, key=lambda row: row["recordId"]),
        "migrated": sorted(migrated, key=lambda row: row["recordId"]),
    }


def verify_pdf_excerpts(plan: dict[str, Any], pdf_path: Path) -> str:
    """Optionally check pinned excerpt text against the exact local PDF pages."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF excerpt verification requires PyMuPDF") from exc
    source = pdf_path.read_bytes()
    with pymupdf.open(stream=source, filetype="pdf") as document:
        page_text: dict[int, str] = {}
        for row in plan["pending"] + plan["migrated"]:
            page = row["proposedCitation"]["page"]
            if page > len(document) or page <= 0:
                raise ValueError(f"Source PDF lacks page {page}")
            if page not in page_text:
                extracted = document[page - 1].get_text("text", sort=False)
                if not isinstance(extracted, str):
                    raise ValueError(f"Source PDF page {page} has no text")
                page_text[page] = " ".join(extracted.split()).casefold()
            if " ".join(row["pdfExcerpt"].split()).casefold() not in page_text[page]:
                raise ValueError(
                    f"PDF excerpt not found on page {page}: {row['recordId']}"
                )
    return hashlib.sha256(source).hexdigest()


def audit_citations(
    curated_path: Path = CURATED,
    manifest_paths: dict[str, Path] | None = None,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    """Validate manifests, attach stable source hashes, and optionally check PDF."""
    paths = MANIFEST_PATHS if manifest_paths is None else manifest_paths
    raw = curated_path.read_bytes()
    manifest_raw = {name: path.read_bytes() for name, path in paths.items()}
    plan = build_citation_migration_plan(
        json.loads(raw),
        {name: json.loads(data) for name, data in manifest_raw.items()},
    )
    return {
        **plan,
        "curatedSourceSha256": hashlib.sha256(raw).hexdigest(),
        "reviewManifestSha256": {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(manifest_raw.items())
        },
        "verifiedPdfSha256": (
            verify_pdf_excerpts(plan, pdf_path) if pdf_path is not None else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curated-source", type=Path, default=CURATED)
    parser.add_argument("--pdf", type=Path, help="Verify excerpts in pinned English N5.3 PDF")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    plan = audit_citations(args.curated_source, pdf_path=args.pdf)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"Audit-only citations pending migration: {plan['pendingCount']}")
        print(f"Verified maintained citations migrated: {plan['migratedCount']}")
        for name, count in plan["countsByManifest"].items():
            print(f"  {name}: {count}")
        for row in plan["pending"]:
            print(f"  {row['recordId']}: N5.3 p. {row['proposedCitation']['page']}")
        print("No curated sources, generated databases or publication fingerprints changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
