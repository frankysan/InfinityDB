"""Export staged rules without changing the active release schema or Restrictions."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from infinity_db.deployed_object_builder import build_deployed_objects
from infinity_db.rules_database import RulesDatabase, export_rules_database

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RULES = ROOT / "data/generated/rules.db"
RESTRICTIONS_CHART = ROOT / "config/validation/restrictions-source-chart.json"


def export_release_rules(
    documents: list, destination: Path, *, baseline: Path | None = None,
) -> None:
    """Preserve the active schema and rebuild its reviewed reference model."""
    source = baseline or RELEASE_RULES
    existing = RulesDatabase(source)
    existing.validate()
    with closing(sqlite3.connect(source)) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version not in (8, 9, 10):
        raise ValueError("Cannot stage an unsupported release rules schema")
    manifest = (
        json.loads(RESTRICTIONS_CHART.read_text(encoding="utf-8"))
        if version >= 9 else None
    )
    deployed_objects = None
    if version == 10:
        army = ROOT / "data/generated/infinity.db"
        existing.deployed_objects_payload(army)
        curated_source = next(
            (
                path for path, document in documents
                if document["collection"]["id"] == "n5-core-v5.3"
                and document["collection"]["status"] == "current"
            ),
            None,
        )
        if curated_source is None:
            raise ValueError("Current N5.3 core source required for v10 staging")
        deployed_objects = build_deployed_objects(
            army, curated_source,
            ROOT / "config/validation/deployed-object-delivery-reviews.json",
            ROOT / "config/validation/deployed-object-candidate-reviews.json",
        )
    export_rules_database(
        documents, destination, restrictions_manifest=manifest,
        deployed_objects=deployed_objects,
    )
    staged = RulesDatabase(destination)
    staged.validate()
    with closing(sqlite3.connect(destination)) as connection:
        staged_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if (
        staged_version != version
        or staged.restrictions_payload() != existing.restrictions_payload()
    ):
        raise ValueError("Staging changed release schema or reviewed Restrictions")
