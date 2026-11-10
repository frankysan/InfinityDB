"""Export staged rules without changing the active release schema or Restrictions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_builder import build_deployed_objects
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.sqlite_comparison import same_logical_rules_contents as same_logical_rules_contents

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RULES = ROOT / "data/generated/rules.db"
RESTRICTIONS_CHART = ROOT / "config/validation/restrictions-source-chart.json"


def load_release_deployed_objects(
    legacy_path: Path, army: Path, rules_path: Path,
) -> dict[str, Any] | None:
    """Read the schema-owned model in the shape used by release comparison tools."""
    rules = RulesDatabase(rules_path)
    rules.validate()
    embedded = rules.deployed_objects_payload(army)
    if embedded is None:
        return load_deployed_object_publication(legacy_path, army, rules_path)
    # This hash is a transient comparison pin, never embedded in rules.db itself.
    return {
        **embedded,
        "sourceSnapshot": {
            **embedded["sourceSnapshot"],
            "rulesDatabaseSha256": hashlib.sha256(rules_path.read_bytes()).hexdigest(),
        },
    }


def release_deployed_object_bytes(path: Path) -> bytes:
    """Serialize the authoritative release model for read-only legacy comparisons.

    v10 reads its embedded model without creating or requiring legacy JSON.
    Standalone JSON fixtures and v8/v9 publications keep their exact file bytes.
    """
    army, rules_path = path.with_name("infinity.db"), path.with_name("rules.db")
    if army.is_file() and rules_path.is_file():
        rules = RulesDatabase(rules_path)
        rules.validate()
        if rules.deployed_objects_payload(army) is not None:
            from tools.build_deployed_object_publication import publication_bytes

            payload = load_release_deployed_objects(path, army, rules_path)
            assert payload is not None
            return publication_bytes(payload)
    return path.read_bytes()


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
