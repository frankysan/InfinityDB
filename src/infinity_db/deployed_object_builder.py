"""Build the reviewed deployed-object model from pinned Army and curated inputs.

This build-time projection belongs in the packaged data layer. Rules SQLite
stores the reviewed model; runtime reads do not require loose JSON files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from infinity_db.deployed_object_inventory import audit_inventory
from infinity_db.deployed_object_reference import project_deployed_references
from infinity_db.deployed_object_usage import attach_reviewed_unit_uses


def build_deployed_objects(
    army_db: Path,
    curated_source: Path,
    delivery_reviews: Path,
    candidate_reviews: Path,
) -> dict[str, Any]:
    """Produce a reviewed model pinned to Army and source evidence, not rules.db bytes."""
    report = audit_inventory(
        army_db, curated_source, delivery_reviews, candidate_reviews,
    )
    model = project_deployed_references(report)
    attach_reviewed_unit_uses(army_db, model)
    model["sourceSnapshot"].update({
        "deliveryReviewSha256": report["deliveryReviewSha256"],
        "candidateReviewSha256": report["candidateReviewSha256"],
    })
    return model
