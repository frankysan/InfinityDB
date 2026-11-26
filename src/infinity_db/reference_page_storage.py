"""Publish bounded reference read models without duplicating resolved previews."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from .build_provenance import canonical_bytes
from .database.repository import Database
from .declaration_matrix import core_declaration_matrix, core_scenario_declaration_extension
from .glossary_catalog import GlossaryCatalog
from .rules_database import RULES_METADATA_TABLE, RulesDatabase
from .scenario_catalog import ScenarioCatalog


def collect_reference_pages(database: Database, rules: RulesDatabase) -> dict[str, Any]:
    pages = {
        "glossary": GlossaryCatalog(database, rules).entries(),
        "orders-aros": core_declaration_matrix(database, rules),
    }
    for scenario in ScenarioCatalog(rules).list_scenarios():
        slug = scenario["slug"]
        pages[f"orders-aros:{slug}"] = core_scenario_declaration_extension(rules, slug)
    return pages


def _fingerprint(db: sqlite3.Connection, rows: list[tuple[str, str]]) -> str:
    scope = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='searchIndex'"
    ).fetchone()
    if scope is None:
        raise ValueError("Reference pages require publication scope")
    return hashlib.sha256(canonical_bytes([json.loads(scope[0])["scope"], rows])).hexdigest()


def stage_reference_pages(db: sqlite3.Connection, pages: dict[str, Any]) -> None:
    rows = [(key, canonical_bytes(value).decode("utf-8")) for key, value in sorted(pages.items())]
    db.execute(
        "CREATE TABLE reference_pages (page TEXT PRIMARY KEY, body TEXT NOT NULL) WITHOUT ROWID"
    )
    db.executemany("INSERT INTO reference_pages VALUES (?,?)", rows)
    db.execute(
        f"INSERT INTO {RULES_METADATA_TABLE} VALUES (?,?)",
        ("referencePagesSha256", json.dumps(_fingerprint(db, rows))),
    )
    validate_reference_pages(db)


def validate_reference_pages(db: sqlite3.Connection) -> None:
    rows = [tuple(row) for row in db.execute("SELECT page,body FROM reference_pages ORDER BY page")]
    digest = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='referencePagesSha256'"
    ).fetchone()
    if digest is None or json.loads(digest[0]) != _fingerprint(db, rows):
        raise ValueError("Invalid reference page projection fingerprint")
    expected = {"glossary", "orders-aros"} | {
        f"orders-aros:{record_id.removeprefix('scenario:')}"
        for (record_id,) in db.execute(
            "SELECT record_id FROM composed_rule_records WHERE kind='scenario' AND scenario_id=''"
        )
    }
    if {key for key, _ in rows} != expected:
        raise ValueError("Incomplete reference page projection coverage")
    for key, body in rows:
        value = json.loads(body)
        if key == "glossary":
            if not isinstance(value, list):
                raise ValueError("Invalid reference page projection Glossary")
        elif not isinstance(value, dict) or not isinstance(value.get("sections"), list):
            raise ValueError("Invalid reference page projection declarations")
