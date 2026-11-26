"""Canonical catalog summaries and deduplicated Army detail usage projections."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from .build_provenance import canonical_bytes
from .database.repository import Database
from .equipment_catalog import EquipmentCatalog
from .publication_registry import PublicationRegistry
from .rules_database import (
    CATALOG_SCHEMA_VERSION,
    REFERENCE_TARGET_SCHEMA_VERSION,
    RULES_METADATA_TABLE,
    SPECIALIST_SCHEMA_VERSION,
    RulesDatabase,
)
from .scenario_catalog import ScenarioCatalog
from .skill_catalog import SkillCatalog

CATALOGS = ("skills", "equipment", "weapons")
SUMMARY_KEYS = tuple(
    (catalog, view)
    for catalog in CATALOGS
    for view in (
        ("army", "army-filter", "public", "public-filter")
        if catalog != "weapons" else ("army", "army-filter")
    )
)


def _encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


@dataclass
class CatalogRows:
    summaries: list[tuple[str, str, str]]
    details: list[tuple[str, int, str]]
    units: dict[int, str]


def collect_catalog_projection(
    database: Database, rules: RulesDatabase, registry: PublicationRegistry,
) -> CatalogRows:
    """Use canonical composers; store logical Unit display data only once."""
    skills = SkillCatalog(database, rules, ScenarioCatalog(rules, registry))
    equipment = EquipmentCatalog(database, rules)
    summary_rows: list[tuple[str, str, str]] = []
    detail_rows: list[tuple[str, int, str]] = []
    units: dict[int, str] = {}
    for catalog in CATALOGS:
        summaries = database.list_catalog_items(catalog)
        views = {
            "army": summaries,
            "army-filter": database.list_catalog_filter_items(catalog),
        }
        if catalog == "skills":
            views.update(public=skills.list_skills(),
                         **{"public-filter": skills.list_skills(filter_only=True)})
        elif catalog == "equipment":
            views.update(public=equipment.list_equipment(),
                         **{"public-filter": equipment.list_equipment(filter_only=True)})
        summary_rows.extend(
            (catalog, view, _encode(items)) for view, items in sorted(views.items())
        )
        for item in summaries:
            item_id = int(item["id"])
            detail = (database.get_skill(item_id) if catalog == "skills"
                      else database.get_catalog_item(catalog, item_id))
            if detail is not None:
                variants = []
                for variant in detail["variants"]:
                    unit_ids = []
                    for unit in variant["units"]:
                        unit_id = int(unit["id"])
                        body = _encode(unit)
                        if units.setdefault(unit_id, body) != body:
                            raise ValueError(f"Conflicting catalog usage Unit {unit_id}")
                        unit_ids.append(unit_id)
                    variants.append({**variant, "units": unit_ids})
                detail = {**detail, "variants": variants}
            detail_rows.append((catalog, item_id, _encode(detail)))
    return CatalogRows(summary_rows, detail_rows, units)


def stage_catalog_projection(db: sqlite3.Connection, rows: CatalogRows) -> None:
    db.execute(
        "CREATE TABLE catalog_summaries (catalog TEXT NOT NULL, view TEXT NOT NULL, "
        "body TEXT NOT NULL, PRIMARY KEY(catalog,view)) WITHOUT ROWID"
    )
    db.execute(
        "CREATE TABLE catalog_usage_units (unit_id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE catalog_details (catalog TEXT NOT NULL, item_id INTEGER NOT NULL, "
        "body TEXT NOT NULL, PRIMARY KEY(catalog,item_id)) WITHOUT ROWID"
    )
    db.executemany("INSERT INTO catalog_summaries VALUES (?,?,?)", rows.summaries)
    db.executemany("INSERT INTO catalog_details VALUES (?,?,?)", rows.details)
    db.executemany("INSERT INTO catalog_usage_units VALUES (?,?)", sorted(rows.units.items()))


def _projection_sha256(db: sqlite3.Connection) -> str:
    scope_row = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='searchIndex'"
    ).fetchone()
    if scope_row is None:
        raise ValueError("Catalog projection requires global search scope")
    scope = json.loads(scope_row[0])["scope"]
    rows = [
        [tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY {order}")]
        for table, order in (
            ("catalog_summaries", "catalog,view"),
            ("catalog_details", "catalog,item_id"),
            ("catalog_usage_units", "unit_id"),
        )
    ]
    return hashlib.sha256(canonical_bytes([scope, rows])).hexdigest()


def record_catalog_projection(db: sqlite3.Connection) -> None:
    db.execute(
        f"INSERT INTO {RULES_METADATA_TABLE} VALUES (?,?)",
        ("catalogProjectionSha256", _encode(_projection_sha256(db))),
    )
    validate_catalog_projection(db)


def validate_catalog_projection(db: sqlite3.Connection) -> None:
    """Check coverage and integrity of the scope-bound summary and usage projection."""
    row = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='catalogProjectionSha256'"
    ).fetchone()
    if row is None or json.loads(row[0]) != _projection_sha256(db):
        raise ValueError("Invalid catalog projection fingerprint")
    summaries = {
        (catalog, view): json.loads(body)
        for catalog, view, body in db.execute("SELECT catalog,view,body FROM catalog_summaries")
    }
    if set(summaries) != set(SUMMARY_KEYS):
        raise ValueError("Incomplete catalog projection summaries")
    expected = {
        (catalog, item["id"]) for catalog in CATALOGS for item in summaries[catalog, "army"]
    }
    actual = set()
    referenced = set()
    for catalog, item_id, raw in db.execute("SELECT catalog,item_id,body FROM catalog_details"):
        actual.add((catalog, item_id))
        detail = json.loads(raw)
        if detail is not None:
            if detail["id"] != item_id:
                raise ValueError("Invalid catalog projection detail identity")
            referenced.update(
                unit for variant in detail["variants"] for unit in variant["units"]
            )
    units = set()
    for unit_id, raw in db.execute("SELECT unit_id,body FROM catalog_usage_units"):
        if json.loads(raw)["id"] != unit_id:
            raise ValueError("Invalid catalog projection Unit identity")
        units.add(unit_id)
    if actual != expected or units != referenced:
        raise ValueError("Incomplete catalog projection usage coverage")


@dataclass(frozen=True)
class CatalogProjection:
    path: Path

    @classmethod
    def select(cls, path: Path) -> CatalogProjection | None:
        """Only select after global search has established the matching publication scope."""
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA user_version").fetchone()[0] < CATALOG_SCHEMA_VERSION:
                return None
        return cls(path)

    @cached_property
    def reference_targets(self) -> dict[str, Any] | None:
        """Load once per selected immutable application, not once per text value."""
        from .maintained_text_references import read_reference_targets

        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA user_version").fetchone()[0] < REFERENCE_TARGET_SCHEMA_VERSION:
                return None
            return read_reference_targets(db)

    def specialist_candidates(self, context: str) -> frozenset[int] | None:
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA user_version").fetchone()[0] < SPECIALIST_SCHEMA_VERSION:
                return None
            row = db.execute(
                "SELECT body FROM specialist_candidates WHERE context=?", (context,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Missing Specialist candidate projection: {context}")
        return frozenset(json.loads(row[0]))

    def summary(self, catalog: str, view: str) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            row = db.execute(
                "SELECT body FROM catalog_summaries WHERE catalog=? AND view=?",
                (catalog, view),
            ).fetchone()
        if row is None:
            raise ValueError(f"Missing catalog projection: {catalog}/{view}")
        return json.loads(row[0])

    def detail(self, catalog: str, item_id: int) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            row = db.execute(
                "SELECT body FROM catalog_details WHERE catalog=? AND item_id=?",
                (catalog, item_id),
            ).fetchone()
            if row is None:
                raise ValueError(f"Missing catalog detail projection: {catalog}/{item_id}")
            detail = json.loads(row[0])
            if detail is None:
                return None
            ids = sorted({unit for variant in detail["variants"] for unit in variant["units"]})
            units = {}
            if ids:
                placeholders = ",".join("?" for _ in ids)
                units = {
                    unit_id: json.loads(body) for unit_id, body in db.execute(
                        "SELECT unit_id,body FROM catalog_usage_units "
                        f"WHERE unit_id IN ({placeholders})",
                        ids,
                    )
                }
            for variant in detail["variants"]:
                variant["units"] = [units[unit_id] for unit_id in variant["units"]]
        return detail
