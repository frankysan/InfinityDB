"""Export staged rules without changing the active release schema or Restrictions."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from infinity_db.rules_database import RulesDatabase, export_rules_database

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RULES = ROOT / "data/generated/rules.db"
RESTRICTIONS_CHART = ROOT / "config/validation/restrictions-source-chart.json"


def export_release_rules(
    documents: list, destination: Path, *, baseline: Path | None = None,
) -> None:
    """Preserve the active v8/v9 schema and reviewed Restrictions when staging."""
    source = baseline or RELEASE_RULES
    existing = RulesDatabase(source)
    existing.validate()
    with sqlite3.connect(source) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version not in (8, 9):
        raise ValueError("Cannot stage an unsupported release rules schema")
    manifest = (
        json.loads(RESTRICTIONS_CHART.read_text(encoding="utf-8"))
        if version == 9 else None
    )
    export_rules_database(documents, destination, restrictions_manifest=manifest)
    staged = RulesDatabase(destination)
    staged.validate()
    with sqlite3.connect(destination) as connection:
        staged_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if (
        staged_version != version
        or staged.restrictions_payload() != existing.restrictions_payload()
    ):
        raise ValueError("Staging changed release schema or reviewed Restrictions")
