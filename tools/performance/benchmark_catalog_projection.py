"""Compare compact catalog projection reads to canonical runtime composition."""

from __future__ import annotations

import argparse
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from statistics import median
from time import perf_counter

from infinity_db.catalog_projection import (
    CATALOGS,
    CatalogProjection,
    collect_catalog_projection,
    stage_catalog_projection,
)
from infinity_db.database.repository import Database
from infinity_db.database_set import SEASON_DATABASE_SOURCES
from infinity_db.equipment_catalog import EquipmentCatalog
from infinity_db.publication_registry import PublicationRegistry
from infinity_db.rules_database import RulesDatabase
from infinity_db.scenario_catalog import ScenarioCatalog
from infinity_db.skill_catalog import SkillCatalog


def services(directory: Path):
    db = Database(directory / "army.db")
    rules = RulesDatabase(directory / "rules_n5.db", immutable_snapshot=True)
    registry = PublicationRegistry(rules, {
        season: directory / filename for season, (filename, _) in SEASON_DATABASE_SOURCES.items()
    })
    return db, rules, registry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "catalog.db"
        database, rules, registry = services(args.db_dir)
        started = perf_counter()
        with closing(sqlite3.connect(path)) as db, db:
            stage_catalog_projection(db, collect_catalog_projection(database, rules, registry))
        print(f"Projection: {path.stat().st_size:,} bytes; build {perf_counter()-started:.3f}s",
              flush=True)
        projection = CatalogProjection(path)
        for catalog in CATALOGS:
            summaries, indexed, warm, filter_times, filter_indexed, details, detail_indexed = (
                [], [], [], [], [], [], [],
            )
            with closing(sqlite3.connect(path)) as db:
                count = db.execute(
                    "SELECT COUNT(*) FROM catalog_details WHERE catalog=?", (catalog,)
                ).fetchone()[0]
            for _ in range(args.iterations):
                database, rules, registry = services(args.db_dir)
                skill = SkillCatalog(database, rules, ScenarioCatalog(rules, registry))
                equipment = EquipmentCatalog(database, rules)
                if catalog == "skills":
                    list_items, view = skill.list_skills, "public"
                elif catalog == "equipment":
                    list_items, view = equipment.list_equipment, "public"
                else:
                    list_items, view = None, "army"
                started = perf_counter()
                expected = (list_items() if list_items else database.list_catalog_items(catalog))
                summaries.append(perf_counter() - started)
                started = perf_counter()
                assert projection.summary(catalog, view) == expected
                indexed.append(perf_counter() - started)
                started = perf_counter()
                repeated = list_items() if list_items else database.list_catalog_items(catalog)
                assert repeated == expected
                warm.append(perf_counter() - started)
                started = perf_counter()
                expected_filter = (
                    list_items(filter_only=True) if list_items
                    else database.list_catalog_filter_items(catalog)
                )
                filter_times.append(perf_counter() - started)
                started = perf_counter()
                assert projection.summary(catalog, view + "-filter") == expected_filter
                filter_indexed.append(perf_counter() - started)
                # Most-used raw Army item: avoid timing unrelated catalog preparation.
                item = max(database.list_catalog_items(catalog), key=lambda x: x["use_count"])
                database = Database(args.db_dir / "army.db")
                started = perf_counter()
                detail = (database.get_skill(item["id"]) if catalog == "skills"
                          else database.get_catalog_item(catalog, item["id"]))
                details.append(perf_counter() - started)
                started = perf_counter()
                assert projection.detail(catalog, item["id"]) == detail
                detail_indexed.append(perf_counter() - started)
            def ms(values):
                return f"{median(values)*1000:.2f}"

            print(
                f"{catalog}: {count} Army items; "
                f"cold summary {ms(summaries)}/{ms(indexed)} ms, "
                f"repeat composed {ms(warm)} ms, "
                f"filter {ms(filter_times)}/{ms(filter_indexed)} ms, "
                f"detail {ms(details)}/{ms(detail_indexed)} ms",
                flush=True,
            )


if __name__ == "__main__":
    main()
