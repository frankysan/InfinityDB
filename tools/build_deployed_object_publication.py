"""Build the pinned deployed-object reference JSON for release packaging.

Developer/release build only. Production consumes the generated artifact
without reading the raw Army normalized tables or working-tree curated JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_reference import project_deployed_references
from infinity_db.deployed_object_usage import attach_reviewed_unit_uses
from tools.audit_deployed_object_inventory import audit_inventory

ROOT = Path(__file__).resolve().parents[1]


def _digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def build_publication(
    army_db: Path,
    rules_db: Path,
    curated_source: Path,
    delivery_reviews: Path,
    candidate_reviews: Path,
) -> dict[str, Any]:
    """Project only validated review evidence; pin both shipped databases."""
    report = audit_inventory(army_db, curated_source, delivery_reviews, candidate_reviews)
    publication = project_deployed_references(report)
    attach_reviewed_unit_uses(army_db, publication)
    publication["sourceSnapshot"]["rulesDatabaseSha256"] = _digest(rules_db)
    publication["sourceSnapshot"]["deliveryReviewSha256"] = report["deliveryReviewSha256"]
    publication["sourceSnapshot"]["candidateReviewSha256"] = report["candidateReviewSha256"]
    return publication


def publication_bytes(publication: dict[str, Any]) -> bytes:
    return (json.dumps(
        publication, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ) + "\n").encode("utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=ROOT / "data/generated/infinity.db")
    parser.add_argument("--rules-db", type=Path, default=ROOT / "data/generated/rules.db")
    parser.add_argument(
        "--curated-source", type=Path,
        default=ROOT / "data/curated/rules/n5-core-v5.3.json",
    )
    parser.add_argument(
        "--delivery-reviews", type=Path,
        default=ROOT / "config/validation/deployed-object-delivery-reviews.json",
    )
    parser.add_argument(
        "--candidate-reviews", type=Path,
        default=ROOT / "config/validation/deployed-object-candidate-reviews.json",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/generated/deployed-objects.json"
    )
    parser.add_argument("--check", action="store_true", help="Verify an existing artifact only")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    publication = build_publication(
        args.army_db, args.rules_db, args.curated_source,
        args.delivery_reviews, args.candidate_reviews,
    )
    expected = publication_bytes(publication)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != expected:
            raise SystemExit("Deployed-object publication missing or stale; rebuild it")
        print(f"Deployed-object publication verified: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(expected)
        print(f"Deployed-object publication built: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
